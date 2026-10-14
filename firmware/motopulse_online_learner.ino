/*
 * MotoPulse™ Autonomous Continual Self-Learning ESP32-S3 Firmware
 * ===============================================================
 * Target: ESP32-S3-DevKitC-1-N16R8 (16MB Flash, 8MB Octal PSRAM)
 * 
 * Carrier Board Pinout:
 *   - Dual INMP441s: SCK=GPIO 4, WS=GPIO 5, SD=GPIO 6 (4.0cm spaced array)
 *   - Piezo Sensor:  GPIO 1 (ADC1_CH0 with 1MΩ damping bleed resistor)
 *   - SSD1306 OLED:  SCL=GPIO 8, SDA=GPIO 9 (128x64 Fast I2C)
 * 
 * Autonomous Continual Learning:
 *   - Engine Running Gating: Fuses Piezo RMS vibration + I2S acoustic energy.
 *   - Streaming Welford EMA Manifold Tracker: Adapts to this vehicle's healthy baseline.
 *   - Anomaly Drift Guard: Automatically freezes baseline updates when defects occur.
 *   - NVS Flash Persistence: Keeps vehicle learned profile across ignition cycles.
 * 
 * Co-authored-by: ishannvn <ishannvn@users.noreply.github.com>
 */

#include <Arduino.h>
#include <Wire.h>
#include <driver/i2s.h>
#include <driver/adc.h>
#include <esp_adc_cal.h>
#include "esp32_online_learner.h"
#include "../datasets/models/motopulse_model_data.h"

// Hardware Pin Configuration
#define I2S_SCK_PIN     4
#define I2S_WS_PIN      5
#define I2S_SD_PIN      6
#define I2S_PORT        I2S_NUM_0

#define PIEZO_ADC_PIN   1
#define PIEZO_ADC_CH    ADC1_CHANNEL_0

#define OLED_SCL_PIN    8
#define OLED_SDA_PIN    9
#define OLED_I2C_ADDR   0x3C

// Audio Sampling Settings
#define SAMPLE_RATE     16000
#define SAMPLES_PER_SEC 16000
#define DMA_BUF_COUNT   8
#define DMA_BUF_LEN     512

// Global Instances
ESP32OnlineVehicleLearner g_learner(0.04f, 3.2f, 0.015f, 0.020f);
TaskHandle_t xLearningTaskHandle = NULL;

// Ring buffer for audio & piezo processing
static int16_t s_audio_window[SAMPLES_PER_SEC];
static float   s_embedding[LEARNER_EMBEDDING_DIM];

void initI2S() {
    i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = SAMPLE_RATE,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
        .channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = DMA_BUF_COUNT,
        .dma_buf_len = DMA_BUF_LEN,
        .use_apll = false,
        .tx_desc_auto_clear = false,
        .fixed_mclk = 0
    };

    i2s_pin_config_t pin_config = {
        .bck_io_num = I2S_SCK_PIN,
        .ws_io_num = I2S_WS_PIN,
        .data_out_num = I2S_PIN_NO_CHANGE,
        .data_in_num = I2S_SD_PIN
    };

    i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
    i2s_set_pin(I2S_PORT, &pin_config);
    i2s_set_clk(I2S_PORT, SAMPLE_RATE, I2S_BITS_PER_SAMPLE_32BIT, I2S_CHANNEL_STEREO);
}

void initPiezoADC() {
    pinMode(PIEZO_ADC_PIN, INPUT_PULLDOWN);
    analogReadResolution(12);
}

void extractTinyMLEmbedding(const int16_t* pcm, size_t length, float* out_embedding) {
    // 32-band Log Energy + 16 temporal derivative dynamic features
    // In full deployment, this is the penultimate dense layer output of g_motopulse_model
    float band_energies[32] = {0};
    int stride = length / 32;

    for (int b = 0; b < 32; ++b) {
        float sum = 0.0f;
        for (int i = 0; i < stride; ++i) {
            float val = (float)pcm[b * stride + i] / 32768.0f;
            sum += val * val;
        }
        band_energies[b] = logf(sum / stride + 1e-6f);
        out_embedding[b] = band_energies[b];
    }

    for (int k = 0; k < 16; ++k) {
        out_embedding[32 + k] = fabsf(band_energies[k * 2 + 1] - band_energies[k * 2]);
    }
}

void vOnlineLearnerTask(void* pvParameters) {
    uint8_t dma_read_buf[1024];
    size_t bytes_read = 0;
    
    Serial.println("[LearnerTask] Continuous vehicle self-training task started on Core 1.");

    while (true) {
        float audio_energy_sum = 0.0f;
        int pcm_idx = 0;

        // Collect 1.0 second window (16,000 samples @ 16kHz)
        while (pcm_idx < SAMPLES_PER_SEC) {
            i2s_read(I2S_PORT, dma_read_buf, sizeof(dma_read_buf), &bytes_read, portMAX_DELAY);
            int32_t* samples32 = (int32_t*)dma_read_buf;
            int count = bytes_read / 8; // 2 channels x 4 bytes

            for (int i = 0; i < count && pcm_idx < SAMPLES_PER_SEC; ++i) {
                int16_t left_sample = (int16_t)(samples32[i * 2] >> 16);
                s_audio_window[pcm_idx++] = left_sample;
                audio_energy_sum += fabsf((float)left_sample / 32768.0f);
            }
        }

        float mean_audio_energy = audio_energy_sum / SAMPLES_PER_SEC;

        // Sample Piezo mechanical vibration on GPIO 1
        uint32_t pz_min = 4095, pz_max = 0;
        float pz_sum_sq = 0.0f;
        for (int p = 0; p < 64; ++p) {
            int val = analogRead(PIEZO_ADC_PIN);
            if (val < (int)pz_min) pz_min = val;
            if (val > (int)pz_max) pz_max = val;
            float norm = (float)val / 4095.0f;
            pz_sum_sq += norm * norm;
            delayMicroseconds(50);
        }
        float piezo_rms = sqrtf(pz_sum_sq / 64.0f);

        // Feature extraction
        extractTinyMLEmbedding(s_audio_window, SAMPLES_PER_SEC, s_embedding);

        // Execute Online Self-Training Step
        LearnerStepResult_t result;
        g_learner.updateStep(s_embedding, piezo_rms, mean_audio_energy, &result);

        // Emit Serial Telemetry
        Serial.printf(
            "LEARN:run=%d:regime=%d:status=%d:score=%.2f:anomaly=%d:frames=%lu:conf=%.2f\n",
            result.is_engine_running ? 1 : 0,
            (int)result.regime,
            (int)result.status,
            result.anomaly_score,
            result.is_anomaly ? 1 : 0,
            (unsigned long)result.total_learned_frames,
            result.running_confidence
        );

        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

void setup() {
    Serial.begin(115200);
    delay(1000);

    Serial.println("\n========================================================");
    Serial.println("   🏎️  MotoPulse™ ESP32-S3 Online Continual Learner    ");
    Serial.println("========================================================");
    Serial.printf("TFLite Model Flash Footprint: %u bytes\n", (unsigned int)g_motopulse_model_len);

    initPiezoADC();
    initI2S();

    // Start continual learner with NVS restoration
    g_learner.begin();

    // Pin FreeRTOS learning task to Core 1
    xTaskCreatePinnedToCore(
        vOnlineLearnerTask,
        "OnlineLearnerTask",
        8192,
        NULL,
        2,
        &xLearningTaskHandle,
        1
    );

    Serial.println("✔ MotoPulse hardware and online continual learning initialized.");
}

void loop() {
    // Keep main thread alive for watchdog and serial events
    vTaskDelay(pdMS_TO_TICKS(1000));
}
