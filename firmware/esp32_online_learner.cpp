/**
 * @file esp32_online_learner.cpp
 * @brief Implementation of MotoPulse™ ESP32-S3 Online Continual Self-Learning Engine
 * 
 * @author Visweshwara & Ishan Kumar (@ishannvn)
 * @date 2026-10-14
 */

#include "esp32_online_learner.h"
#include <math.h>
#include <string.h>

#if defined(ESP_PLATFORM)
#include "esp_log.h"
#include "nvs_flash.h"
#include "nvs.h"
static const char* TAG = "OnlineLearner";
#elif defined(ARDUINO)
#include <Arduino.h>
#include <Preferences.h>
#else
#include <stdio.h>
#endif

#define NVS_MAGIC_HEADER 0x4D504C53  // "MPLS"
#define NVS_SCHEMA_VER   1

ESP32OnlineVehicleLearner::ESP32OnlineVehicleLearner(
    float learning_rate,
    float anomaly_threshold_sigma,
    float piezo_run_thresh,
    float audio_run_thresh
) : m_alpha(learning_rate),
    m_threshold_sigma(anomaly_threshold_sigma),
    m_piezo_run_thresh(piezo_run_thresh),
    m_audio_run_thresh(audio_run_thresh),
    m_is_running(false),
    m_running_confidence(0.0f),
    m_total_frames_learned(0),
    m_anomaly_count(0),
    m_current_regime(REGIME_IDLE)
{
    resetToFactoryDefaults();
}

ESP32OnlineVehicleLearner::~ESP32OnlineVehicleLearner() {
    // Optionally commit on destruction
    if (m_total_frames_learned > 0) {
        saveProfileToNVS();
    }
}

void ESP32OnlineVehicleLearner::resetToFactoryDefaults() {
    for (int r = 0; r < LEARNER_NUM_REGIMES; ++r) {
        m_regime_counts[r] = 0;
        for (int i = 0; i < LEARNER_EMBEDDING_DIM; ++i) {
            m_regime_means[r][i] = 0.0f;
            m_regime_vars[r][i]  = 0.15f; // initial baseline variance
        }
    }
    m_is_running = false;
    m_running_confidence = 0.0f;
    m_total_frames_learned = 0;
    m_anomaly_count = 0;
    m_current_regime = REGIME_IDLE;
}

bool ESP32OnlineVehicleLearner::begin() {
    // Try restoring profile from NVS Flash
    bool restored = loadProfileFromNVS();
    if (restored) {
#if defined(ESP_PLATFORM)
        ESP_LOGI(TAG, "Restored learned vehicle baseline (%lu frames accumulated)", (unsigned long)m_total_frames_learned);
#elif defined(ARDUINO)
        Serial.printf("[OnlineLearner] Restored vehicle baseline (%u frames accumulated)\n", m_total_frames_learned);
#endif
    } else {
#if defined(ESP_PLATFORM)
        ESP_LOGI(TAG, "No NVS profile found. Starting factory calibration.");
#elif defined(ARDUINO)
        Serial.println("[OnlineLearner] Starting factory calibration.");
#endif
    }
    return restored;
}

bool ESP32OnlineVehicleLearner::detectEngineRunning(float piezo_rms, float audio_energy) {
    // Multi-sensor physical gating:
    // Requires both structural vibration on GPIO 1 and broadband acoustic energy on INMP441s
    bool running_evidence = (piezo_rms > m_piezo_run_thresh) && (audio_energy > m_audio_run_thresh);

    if (running_evidence) {
        m_running_confidence += 0.25f;
        if (m_running_confidence > 1.0f) m_running_confidence = 1.0f;
    } else {
        m_running_confidence -= 0.15f;
        if (m_running_confidence < 0.0f) m_running_confidence = 0.0f;
    }

    m_is_running = (m_running_confidence >= 0.75f);
    return m_is_running;
}

VehicleRegime_t ESP32OnlineVehicleLearner::classifyRegime(const float* embedding) {
    // Assign to closest initialized operational regime by Euclidean distance
    int active_regimes = 0;
    float best_dist = 1e12f;
    int best_regime = 0;

    for (int r = 0; r < LEARNER_NUM_REGIMES; ++r) {
        if (m_regime_counts[r] > 0) {
            active_regimes++;
            float dist_sq = 0.0f;
            for (int i = 0; i < LEARNER_EMBEDDING_DIM; ++i) {
                float d = embedding[i] - m_regime_means[r][i];
                dist_sq += d * d;
            }
            if (dist_sq < best_dist) {
                best_dist = dist_sq;
                best_regime = r;
            }
        }
    }

    if (active_regimes == 0) {
        return REGIME_IDLE;
    }
    return (VehicleRegime_t)best_regime;
}

float ESP32OnlineVehicleLearner::computeAnomalyScore(
    const float* embedding,
    VehicleRegime_t regime,
    float piezo_rms,
    bool* out_is_anomaly
) {
    if (m_regime_counts[regime] < 5) {
        // Bootstrapping warmup period
        *out_is_anomaly = false;
        return 0.0f;
    }

    float z_scores[LEARNER_EMBEDDING_DIM];
    float sum_sq = 0.0f;

    for (int i = 0; i < LEARNER_EMBEDDING_DIM; ++i) {
        float var = m_regime_vars[regime][i];
        if (var < 1e-4f) var = 1e-4f;
        float z = fabsf(embedding[i] - m_regime_means[regime][i]) / sqrtf(var);
        z_scores[i] = z;
        sum_sq += z * z;
    }

    float rms_z = sqrtf(sum_sq / LEARNER_EMBEDDING_DIM);

    // Partial selection sort for top-8 resonant bands (mechanical defect spikes)
    float top8_sum = 0.0f;
    for (int k = 0; k < 8; ++k) {
        int max_idx = k;
        for (int j = k + 1; j < LEARNER_EMBEDDING_DIM; ++j) {
            if (z_scores[j] > z_scores[max_idx]) {
                max_idx = j;
            }
        }
        float tmp = z_scores[k];
        z_scores[k] = z_scores[max_idx];
        z_scores[max_idx] = tmp;
        top8_sum += z_scores[k];
    }
    float top8_z = top8_sum / 8.0f;

    // Fused acoustic anomaly score
    float acoustic_metric = (0.6f * top8_z) + (0.4f * rms_z);

    // Structure-borne mechanical shock alert (e.g. rod knock or severe misfire impact)
    bool piezo_shock = (piezo_rms > 0.080f);

    *out_is_anomaly = (acoustic_metric > m_threshold_sigma) || piezo_shock;

    float final_score = acoustic_metric;
    if (piezo_shock) {
        float pz_score = piezo_rms / 0.025f;
        if (pz_score > final_score) final_score = pz_score;
    }
    return final_score;
}

void ESP32OnlineVehicleLearner::updateStep(
    const float* embedding,
    float piezo_rms,
    float audio_energy,
    LearnerStepResult_t* out_result
) {
    if (!out_result) return;

    // 1. Engine Running Verification Gating
    bool running = detectEngineRunning(piezo_rms, audio_energy);
    out_result->is_engine_running = running;
    out_result->running_confidence = m_running_confidence;
    out_result->total_learned_frames = m_total_frames_learned;

    if (!running) {
        out_result->status = LEARNER_STATUS_ENGINE_OFF;
        out_result->regime = REGIME_IDLE;
        out_result->anomaly_score = 0.0f;
        out_result->is_anomaly = false;
        out_result->baseline_updated = false;
        return;
    }

    // 2. Operational Driving Regime Classification
    VehicleRegime_t regime = classifyRegime(embedding);
    m_current_regime = regime;
    out_result->regime = regime;

    // 3. Anomaly Scoring
    bool is_anomaly = false;
    float score = computeAnomalyScore(embedding, regime, piezo_rms, &is_anomaly);
    out_result->anomaly_score = score;
    out_result->is_anomaly = is_anomaly;

    // 4. ANOMALY DRIFT GUARD:
    // If an acoustic or vibration defect is detected, FREEZE baseline adaptation!
    // This protects the healthy manifold from ever learning mechanical damage.
    if (is_anomaly) {
        m_anomaly_count++;
        out_result->status = LEARNER_STATUS_ANOMALY_DETECTED;
        out_result->baseline_updated = false;
        return;
    }

    // 5. STREAMING ADAPTATION (Welford Exponential Moving Average):
    if (m_regime_counts[regime] == 0) {
        // Cold-start regime seeding
        for (int i = 0; i < LEARNER_EMBEDDING_DIM; ++i) {
            m_regime_means[regime][i] = embedding[i];
            m_regime_vars[regime][i]  = 0.10f;
        }
        out_result->status = LEARNER_STATUS_BOOTSTRAPPING;
    } else {
        // Continual online adaptation to steady healthy vehicle profile
        for (int i = 0; i < LEARNER_EMBEDDING_DIM; ++i) {
            float diff = embedding[i] - m_regime_means[regime][i];
            m_regime_means[regime][i] += m_alpha * diff;
            m_regime_vars[regime][i]   = (1.0f - m_alpha) * m_regime_vars[regime][i] + m_alpha * (diff * diff);
        }
        out_result->status = LEARNER_STATUS_ADAPTING_BASELINE;
    }

    m_regime_counts[regime]++;
    m_total_frames_learned++;
    out_result->baseline_updated = true;
    out_result->total_learned_frames = m_total_frames_learned;

    // Periodically save to Flash (e.g. every 300 seconds of driving)
    if (m_total_frames_learned % 300 == 0) {
        saveProfileToNVS();
    }
}

uint32_t ESP32OnlineVehicleLearner::calculateCRC32(const uint8_t* data, size_t length) {
    uint32_t crc = 0xFFFFFFFF;
    for (size_t i = 0; i < length; ++i) {
        crc ^= data[i];
        for (int j = 0; j < 8; ++j) {
            crc = (crc >> 1) ^ (0xEDB88320 & (-(crc & 1)));
        }
    }
    return ~crc;
}

bool ESP32OnlineVehicleLearner::saveProfileToNVS() {
    VehicleProfileNVS_t profile;
    profile.magic = NVS_MAGIC_HEADER;
    profile.version = NVS_SCHEMA_VER;
    profile.embedding_dim = LEARNER_EMBEDDING_DIM;
    profile.total_frames_learned = m_total_frames_learned;

    memcpy(profile.regime_counts, m_regime_counts, sizeof(m_regime_counts));
    memcpy(profile.regime_means, m_regime_means, sizeof(m_regime_means));
    memcpy(profile.regime_vars, m_regime_vars, sizeof(m_regime_vars));

    size_t data_len = offsetof(VehicleProfileNVS_t, crc32);
    profile.crc32 = calculateCRC32((const uint8_t*)&profile, data_len);

#if defined(ESP_PLATFORM)
    nvs_handle_t handle;
    esp_err_t err = nvs_open(LEARNER_NVS_NAMESPACE, NVS_READWRITE, &handle);
    if (err != ESP_OK) return false;

    err = nvs_set_blob(handle, LEARNER_NVS_KEY, &profile, sizeof(profile));
    if (err == ESP_OK) {
        nvs_commit(handle);
    }
    nvs_close(handle);
    return (err == ESP_OK);
#elif defined(ARDUINO)
    Preferences prefs;
    if (!prefs.begin(LEARNER_NVS_NAMESPACE, false)) return false;
    size_t written = prefs.putBytes(LEARNER_NVS_KEY, &profile, sizeof(profile));
    prefs.end();
    return (written == sizeof(profile));
#else
    // Host simulation fallback: save to local binary file
    FILE* f = fopen("motopulse_vehicle_profile.bin", "wb");
    if (!f) return false;
    fwrite(&profile, 1, sizeof(profile), f);
    fclose(f);
    return true;
#endif
}

bool ESP32OnlineVehicleLearner::loadProfileFromNVS() {
    VehicleProfileNVS_t profile;
    bool loaded = false;

#if defined(ESP_PLATFORM)
    nvs_handle_t handle;
    esp_err_t err = nvs_open(LEARNER_NVS_NAMESPACE, NVS_READONLY, &handle);
    if (err != ESP_OK) return false;

    size_t required_size = sizeof(profile);
    err = nvs_get_blob(handle, LEARNER_NVS_KEY, &profile, &required_size);
    nvs_close(handle);
    if (err == ESP_OK && required_size == sizeof(profile)) {
        loaded = true;
    }
#elif defined(ARDUINO)
    Preferences prefs;
    if (!prefs.begin(LEARNER_NVS_NAMESPACE, true)) return false;
    size_t read_bytes = prefs.getBytes(LEARNER_NVS_KEY, &profile, sizeof(profile));
    prefs.end();
    if (read_bytes == sizeof(profile)) {
        loaded = true;
    }
#else
    FILE* f = fopen("motopulse_vehicle_profile.bin", "rb");
    if (f) {
        size_t n = fread(&profile, 1, sizeof(profile), f);
        fclose(f);
        if (n == sizeof(profile)) loaded = true;
    }
#endif

    if (!loaded) return false;

    // Validate Magic and Schema Version
    if (profile.magic != NVS_MAGIC_HEADER || profile.version != NVS_SCHEMA_VER) {
        return false;
    }

    // Validate CRC32
    size_t data_len = offsetof(VehicleProfileNVS_t, crc32);
    uint32_t expected_crc = calculateCRC32((const uint8_t*)&profile, data_len);
    if (expected_crc != profile.crc32) {
        return false;
    }

    m_total_frames_learned = profile.total_frames_learned;
    memcpy(m_regime_counts, profile.regime_counts, sizeof(m_regime_counts));
    memcpy(m_regime_means, profile.regime_means, sizeof(m_regime_means));
    memcpy(m_regime_vars, profile.regime_vars, sizeof(m_regime_vars));

    return true;
}
