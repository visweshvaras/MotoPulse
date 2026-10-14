/**
 * @file esp32_online_learner.h
 * @brief MotoPulse™ ESP32-S3 Autonomous On-Device Continual Self-Learning Engine
 * 
 * Target MCU: ESP32-S3 (Xtensa Dual-Core LX7 @ 240 MHz, N16R8)
 * Hardware Carrier Mapping:
 *   - I2S Digital Mics: SCK=GPIO 4, WS=GPIO 5, SD=GPIO 6 (Dual INMP441s @ 4.0cm)
 *   - Piezo Knock ADC: GPIO 1 (ADC1_CH0, with 1MΩ damping bleed resistor)
 *   - OLED Display:    SCL=GPIO 8, SDA=GPIO 9 (SSD1306 128x64 @ 400kHz Fast I2C)
 * 
 * Features:
 *   1. Engine Running State Gating (Fusion of Piezo RMS + Broadband Audio Energy)
 *   2. Streaming Welford EMA Manifold Tracking (Multi-Regime: Idle, City, Cruise)
 *   3. Anomaly Drift Guard (Freezes baseline updates during defects to prevent learning faults)
 *   4. Zero-Allocation Xtensa SIMD / Fast Math execution (<1.2 ms per 1.0s window)
 *   5. Non-Volatile Storage (NVS) Flash Persistence across ignition cycles
 * 
 * @author Visweshwara & Ishan Kumar (@ishannvn)
 * @date 2026-10-14
 */

#ifndef ESP32_ONLINE_LEARNER_H
#define ESP32_ONLINE_LEARNER_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define LEARNER_EMBEDDING_DIM     48
#define LEARNER_NUM_REGIMES       3      // 0: Idle, 1: City Drive, 2: Highway Cruise
#define LEARNER_NVS_NAMESPACE     "motopulse_ml"
#define LEARNER_NVS_KEY           "veh_profile"

// Operating Regime Labels
typedef enum {
    REGIME_IDLE = 0,        // 600 - 1000 RPM (Low acoustic amplitude, low vibration)
    REGIME_CITY_DRIVE = 1,   // 1200 - 2500 RPM (Moderate amplitude, dynamic harmonics)
    REGIME_HIGHWAY = 2      // 2500 - 4500 RPM (High broadband air flow & road rumble)
} VehicleRegime_t;

// Learning & Diagnostics Status
typedef enum {
    LEARNER_STATUS_ENGINE_OFF = 0,
    LEARNER_STATUS_BOOTSTRAPPING = 1,
    LEARNER_STATUS_ADAPTING_BASELINE = 2,
    LEARNER_STATUS_ANOMALY_DETECTED = 3
} LearnerStatus_t;

// Learned Vehicle Acoustic Profile for NVS Flash Persistence
typedef struct __attribute__((packed)) {
    uint32_t magic;                                                 // 0x4D504C53 ("MPLS")
    uint16_t version;                                               // Profile schema version
    uint16_t embedding_dim;                                         // 48
    uint32_t total_frames_learned;                                  // Total seconds adapted
    uint32_t regime_counts[LEARNER_NUM_REGIMES];                    // Samples per regime
    float    regime_means[LEARNER_NUM_REGIMES][LEARNER_EMBEDDING_DIM]; // Learned center
    float    regime_vars[LEARNER_NUM_REGIMES][LEARNER_EMBEDDING_DIM];  // Learned variance
    uint32_t crc32;                                                 // Data integrity check
} VehicleProfileNVS_t;

// Per-frame Online Learning Result
typedef struct {
    LearnerStatus_t status;
    bool            is_engine_running;
    VehicleRegime_t regime;
    float           anomaly_score;       // Mahalanobis / Z-score distance
    bool            is_anomaly;          // Triggered when score > threshold_sigma
    bool            baseline_updated;    // True if model adapted this frame
    uint32_t        total_learned_frames;// Cumulative seconds learned
    float           running_confidence;  // 0.0 to 1.0 engine detection score
} LearnerStepResult_t;

#ifdef __cplusplus
}

/**
 * @class ESP32OnlineVehicleLearner
 * @brief Self-contained continual learning engine for ESP32-S3
 */
class ESP32OnlineVehicleLearner {
public:
    ESP32OnlineVehicleLearner(
        float learning_rate = 0.04f,
        float anomaly_threshold_sigma = 3.2f,
        float piezo_run_thresh = 0.015f,
        float audio_run_thresh = 0.020f
    );

    ~ESP32OnlineVehicleLearner();

    /**
     * @brief Initializes learner and attempts to restore learned vehicle profile from NVS Flash
     * @return true if restored from NVS, false if bootstrapped from factory baseline
     */
    bool begin();

    /**
     * @brief Core 1-second online learning step. Call periodically after audio/piezo capture.
     * @param embedding 48-element float array (32 Mel energies + 16 temporal dynamics)
     * @param piezo_rms Root-Mean-Square structural vibration measured on GPIO 1
     * @param audio_energy Mean absolute broadband acoustic energy from INMP441s
     * @param out_result Pointer to struct filled with step results and diagnostic flags
     */
    void updateStep(
        const float* embedding,
        float piezo_rms,
        float audio_energy,
        LearnerStepResult_t* out_result
    );

    /**
     * @brief Persists the current learned vehicle acoustic profile into ESP32 NVS Flash
     * @return true on success
     */
    bool saveProfileToNVS();

    /**
     * @brief Restores learned vehicle profile from ESP32 NVS Flash
     * @return true on success
     */
    bool loadProfileFromNVS();

    /**
     * @brief Resets all learned regimes back to factory uncalibrated state
     */
    void resetToFactoryDefaults();

    // Diagnostics Getters
    bool isEngineRunning() const { return m_is_running; }
    uint32_t getTotalLearnedFrames() const { return m_total_frames_learned; }
    uint32_t getAnomalyCount() const { return m_anomaly_count; }
    VehicleRegime_t getCurrentRegime() const { return m_current_regime; }
    const float* getRegimeMean(int regime) const { return m_regime_means[regime]; }
    const float* getRegimeVar(int regime) const { return m_regime_vars[regime]; }

private:
    float m_alpha;                  // EMA adaptation rate (e.g. 0.04)
    float m_threshold_sigma;        // Anomaly trigger limit (e.g. 3.2 sigma)
    float m_piezo_run_thresh;
    float m_audio_run_thresh;

    float m_regime_means[LEARNER_NUM_REGIMES][LEARNER_EMBEDDING_DIM];
    float m_regime_vars[LEARNER_NUM_REGIMES][LEARNER_EMBEDDING_DIM];
    uint32_t m_regime_counts[LEARNER_NUM_REGIMES];

    bool m_is_running;
    float m_running_confidence;
    uint32_t m_total_frames_learned;
    uint32_t m_anomaly_count;
    VehicleRegime_t m_current_regime;

    bool detectEngineRunning(float piezo_rms, float audio_energy);
    VehicleRegime_t classifyRegime(const float* embedding);
    float computeAnomalyScore(const float* embedding, VehicleRegime_t regime, float piezo_rms, bool* out_is_anomaly);
    uint32_t calculateCRC32(const uint8_t* data, size_t length);
};

#endif // __cplusplus

#endif // ESP32_ONLINE_LEARNER_H
