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

        // Update shared telemetry state for Core 0 OLED display task
        s_latest_result = result;
        s_latest_piezo_rms = piezo_rms;
        s_latest_audio_energy = mean_audio_energy;

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

// ==============================================================================
// SSD1306 REAL-TIME OLED DISPLAY DRIVER & FREERTOS TASK (CORE 0)
// ==============================================================================
static uint8_t s_oled_buf[128 * 8]; // 1024-byte display framebuffer

// Compact 5x7 ASCII font table (ASCII 32 ' ' to 90 'Z')
static const uint8_t PROGMEM FONT_5X7[] = {
    0x00, 0x00, 0x00, 0x00, 0x00, // Space (32)
    0x00, 0x00, 0x5F, 0x00, 0x00, // !
    0x00, 0x07, 0x00, 0x07, 0x00, // "
    0x14, 0x7F, 0x14, 0x7F, 0x14, // #
    0x24, 0x2A, 0x7F, 0x2A, 0x12, // $
    0x23, 0x13, 0x08, 0x64, 0x62, // %
    0x36, 0x49, 0x55, 0x22, 0x50, // &
    0x00, 0x05, 0x03, 0x00, 0x00, // '
    0x00, 0x1C, 0x22, 0x41, 0x00, // (
    0x00, 0x41, 0x22, 0x1C, 0x00, // )
    0x14, 0x08, 0x3E, 0x08, 0x14, // *
    0x08, 0x08, 0x3E, 0x08, 0x08, // +
    0x00, 0x50, 0x30, 0x00, 0x00, // ,
    0x08, 0x08, 0x08, 0x08, 0x08, // -
    0x00, 0x60, 0x60, 0x00, 0x00, // .
    0x20, 0x10, 0x08, 0x04, 0x02, // /
    0x3E, 0x51, 0x49, 0x45, 0x3E, // 0
    0x00, 0x42, 0x7F, 0x40, 0x00, // 1
    0x42, 0x61, 0x51, 0x49, 0x46, // 2
    0x21, 0x41, 0x45, 0x4B, 0x31, // 3
    0x18, 0x14, 0x12, 0x7F, 0x10, // 4
    0x27, 0x45, 0x45, 0x45, 0x39, // 5
    0x3C, 0x4A, 0x49, 0x49, 0x30, // 6
    0x01, 0x71, 0x09, 0x05, 0x03, // 7
    0x36, 0x49, 0x49, 0x49, 0x36, // 8
    0x06, 0x49, 0x49, 0x29, 0x1E, // 9
    0x00, 0x36, 0x36, 0x00, 0x00, // :
    0x00, 0x56, 0x36, 0x00, 0x00, // ;
    0x08, 0x14, 0x22, 0x41, 0x00, // <
    0x14, 0x14, 0x14, 0x14, 0x14, // =
    0x00, 0x41, 0x22, 0x14, 0x08, // >
    0x02, 0x01, 0x51, 0x09, 0x06, // ?
    0x32, 0x49, 0x79, 0x41, 0x3E, // @
    0x7E, 0x11, 0x11, 0x11, 0x7E, // A
    0x7F, 0x49, 0x49, 0x49, 0x36, // B
    0x3E, 0x41, 0x41, 0x41, 0x22, // C
    0x7F, 0x41, 0x41, 0x22, 0x1C, // D
    0x7F, 0x49, 0x49, 0x49, 0x41, // E
    0x7F, 0x09, 0x09, 0x09, 0x01, // F
    0x3E, 0x41, 0x49, 0x49, 0x7A, // G
    0x7F, 0x08, 0x08, 0x08, 0x7F, // H
    0x00, 0x41, 0x7F, 0x41, 0x00, // I
    0x20, 0x40, 0x41, 0x3F, 0x01, // J
    0x7F, 0x08, 0x14, 0x22, 0x41, // K
    0x7F, 0x40, 0x40, 0x40, 0x40, // L
    0x7F, 0x02, 0x0C, 0x02, 0x7F, // M
    0x7F, 0x04, 0x08, 0x10, 0x7F, // N
    0x3E, 0x41, 0x41, 0x41, 0x3E, // O
    0x7F, 0x09, 0x09, 0x09, 0x06, // P
    0x3E, 0x41, 0x51, 0x21, 0x5E, // Q
    0x7F, 0x09, 0x19, 0x29, 0x46, // R
    0x46, 0x49, 0x49, 0x49, 0x31, // S
    0x01, 0x01, 0x7F, 0x01, 0x01, // T
    0x3F, 0x40, 0x40, 0x40, 0x3F, // U
    0x1F, 0x20, 0x40, 0x20, 0x1F, // V
    0x7F, 0x20, 0x18, 0x20, 0x7F, // W
    0x63, 0x14, 0x08, 0x14, 0x63, // X
    0x07, 0x08, 0x70, 0x08, 0x07, // Y
    0x61, 0x51, 0x49, 0x45, 0x43  // Z
};

static void oledSendCmd(uint8_t c) {
    Wire.beginTransmission(OLED_I2C_ADDR);
    Wire.write(0x80);
    Wire.write(c);
    Wire.endTransmission();
}

static void oledSetPixel(int x, int y, uint8_t color) {
    if (x < 0 || x >= 128 || y < 0 || y >= 64) return;
    int page = y / 8;
    int bit = y % 8;
    int idx = page * 128 + x;
    if (color) s_oled_buf[idx] |= (1 << bit);
    else       s_oled_buf[idx] &= ~(1 << bit);
}

static void oledDrawHLine(int x, int y, int w, uint8_t color) {
    for (int i = 0; i < w; ++i) oledSetPixel(x + i, y, color);
}

static void oledFillRect(int x, int y, int w, int h, uint8_t color) {
    for (int j = 0; j < h; ++j) {
        for (int i = 0; i < w; ++i) {
            oledSetPixel(x + i, y + j, color);
        }
    }
}

static void oledDrawChar(int x, int y, char c, uint8_t color) {
    char up = (c >= 'a' && c <= 'z') ? (c - 32) : c;
    if (up < 32 || up > 90) up = 32;
    int offset = (up - 32) * 5;
    for (int col = 0; col < 5; ++col) {
        uint8_t line_bits = pgm_read_byte(&FONT_5X7[offset + col]);
        for (int row = 0; row < 7; ++row) {
            if ((line_bits >> row) & 0x01) {
                oledSetPixel(x + col, y + row, color);
            }
        }
    }
}

static void oledDrawString(int x, int y, const char* str, uint8_t color) {
    int cur_x = x;
    while (*str) {
        oledDrawChar(cur_x, y, *str++, color);
        cur_x += 6;
        if (cur_x >= 124) break;
    }
}

static void oledFlush() {
    for (int page = 0; page < 8; ++page) {
        oledSendCmd(0xB0 + page);
        oledSendCmd(0x02); // 2px column offset: centers SH1106 and fully compatible with SSD1306
        oledSendCmd(0x10);
        Wire.beginTransmission(OLED_I2C_ADDR);
        Wire.write(0x40);
        Wire.write(&s_oled_buf[page * 128], 128);
        Wire.endTransmission();
    }
}

static void initOLED() {
    // 9-clock I2C bus recovery
    pinMode(OLED_SCL_PIN, OUTPUT);
    for (int i = 0; i < 9; ++i) {
        digitalWrite(OLED_SCL_PIN, LOW);
        delayMicroseconds(5);
        digitalWrite(OLED_SCL_PIN, HIGH);
        delayMicroseconds(5);
    }

    // 100 kHz I2C for rock-solid signal integrity
    Wire.begin(OLED_SDA_PIN, OLED_SCL_PIN, 100000);

    const uint8_t init_seq[] = {
        0xAE,             // Display OFF
        0xD5, 0x80,       // Clock divide
        0xA8, 63,         // Multiplex 64
        0xD3, 0x00,       // Offset 0
        0x40,             // Start line 0
        0x8D, 0x14,       // SSD1306 Charge Pump ON
        0xAD, 0x8B,       // SH1106 DC-DC Converter ON
        0x30, 0x33,       // SH1106 pump voltage
        0xA1,             // Remap
        0xC8,             // Scan direction
        0xDA, 0x12,       // COM pins configuration
        0x81, 0xFF,       // Contrast 100%
        0xD9, 0xF1,       // Pre-charge
        0xDB, 0x40,       // VCOMH
        0xA4,             // Output follows RAM
        0xA6,             // Normal display
        0xAF              // Display ON
    };
    for (size_t i = 0; i < sizeof(init_seq); ++i) {
        oledSendCmd(init_seq[i]);
    }

    memset(s_oled_buf, 0, sizeof(s_oled_buf));
    oledDrawString(16, 12, "MOTOPULSE AI", 1);
    oledDrawString(8, 28, "Vehicle Learner", 1);
    oledDrawString(12, 44, "Starting Up...", 1);
    oledFlush();
    delay(600);
}

void vDisplayTask(void* pvParameters) {
    (void)pvParameters;
    char text_buf[32];

    while (true) {
        memset(s_oled_buf, 0, sizeof(s_oled_buf));

        // Header: "MOTOPULSE" + Status Tag
        oledDrawString(0, 1, "MOTOPULSE", 1);
        if (s_latest_result.is_anomaly) {
            oledFillRect(82, 0, 46, 10, 1);
            oledDrawString(84, 1, "!WARN", 0);
        } else if (s_latest_result.is_engine_running) {
            oledDrawString(88, 1, "[RUN]", 1);
        } else {
            oledDrawString(80, 1, "[IDLE]", 1);
        }
        oledDrawHLine(0, 11, 128, 1);

        // Status Line: Regime and Z-Score
        const char* reg_names[] = {"IDLE", "CITY", "HIGH"};
        int reg_idx = (int)s_latest_result.regime;
        if (reg_idx < 0 || reg_idx > 2) reg_idx = 0;

        snprintf(text_buf, sizeof(text_buf), "REG:%s Z:%.1f", reg_names[reg_idx], s_latest_result.anomaly_score);
        oledDrawString(0, 16, text_buf, 1);

        // Learned Frames Counter
        snprintf(text_buf, sizeof(text_buf), "FRAMES:%lu SEC", (unsigned long)s_latest_result.total_learned_frames);
        oledDrawString(0, 28, text_buf, 1);

        // Anomaly Status
        if (s_latest_result.is_anomaly) {
            oledDrawString(0, 40, "STATUS: DEFECT ALERT", 1);
        } else {
            oledDrawString(0, 40, "STATUS: HEALTHY OK", 1);
        }

        // Dual VU Meters on Bottom (y=52 to 58)
        // Mic Volume Bar (0 to 60px)
        int mic_bar = (int)(s_latest_audio_energy * 300.0f);
        if (mic_bar > 60) mic_bar = 60;
        if (mic_bar < 0) mic_bar = 0;
        oledFillRect(0, 52, 62, 5, 0); // outline
        for (int i = 0; i < 62; ++i) oledSetPixel(i, 52, 1);
        for (int i = 0; i < 62; ++i) oledSetPixel(i, 56, 1);
        oledSetPixel(0, 53, 1); oledSetPixel(0, 54, 1); oledSetPixel(0, 55, 1);
        oledSetPixel(61, 53, 1); oledSetPixel(61, 54, 1); oledSetPixel(61, 55, 1);
        if (mic_bar > 0) oledFillRect(1, 53, mic_bar, 3, 1);

        // Piezo Vibration Bar (66 to 126px)
        int pz_bar = (int)(s_latest_piezo_rms * 400.0f);
        if (pz_bar > 60) pz_bar = 60;
        if (pz_bar < 0) pz_bar = 0;
        for (int i = 66; i < 127; ++i) oledSetPixel(i, 52, 1);
        for (int i = 66; i < 127; ++i) oledSetPixel(i, 56, 1);
        oledSetPixel(66, 53, 1); oledSetPixel(66, 54, 1); oledSetPixel(66, 55, 1);
        oledSetPixel(126, 53, 1); oledSetPixel(126, 54, 1); oledSetPixel(126, 55, 1);
        if (pz_bar > 0) oledFillRect(67, 53, pz_bar, 3, 1);

        oledDrawString(16, 58, "MIC", 1);
        oledDrawString(82, 58, "PIEZO", 1);

        oledFlush();
        vTaskDelay(pdMS_TO_TICKS(40)); // ~25 FPS
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
    initOLED();

    // Start continual learner with NVS restoration
    g_learner.begin();

    // Pin OLED display rendering task to Core 0
    xTaskCreatePinnedToCore(
        vDisplayTask,
        "OLEDDisplayTask",
        4096,
        NULL,
        1,
        NULL,
        0
    );

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

    Serial.println("✔ MotoPulse hardware, OLED display, and online continual learning initialized.");
}

void loop() {
    // Keep main thread alive for watchdog and serial events
    vTaskDelay(pdMS_TO_TICKS(1000));
}
