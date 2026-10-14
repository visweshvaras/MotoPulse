/*
 * ESP32-S3 Electret Microphone Circuit Test Sketch
 * 
 * Target: ESP32-S3 (N16R8)
 * Analog Input Pin: GPIO 1 (ADC1_CH0)
 * 
 * Features:
 * 1. 50ms window Peak-to-Peak amplitude detection
 * 2. Visual ASCII Volume Bar in Serial Monitor
 * 3. Formatted output compatible with Arduino Serial Plotter (Ctrl+Shift+L)
 * 4. DC bias baseline monitor (verifies ~1.65V / ~2048 ADC)
 */

#define MIC_PIN 1              // GPIO 1 connected to Breadboard Column 18-C
#define SAMPLE_WINDOW_MS 50    // 50ms sample window (20 updates per second)
#define NOISE_THRESHOLD 35     // Ambient background noise threshold in ADC counts

void setup() {
  Serial.begin(115200);
  delay(1500); // Allow USB Serial to enumerate on ESP32-S3
  
  Serial.println("\n==================================================");
  Serial.println("  ESP32-S3 Electret Mic Test (LM358 Preamp)      ");
  Serial.println("==================================================");
  Serial.println("Reading audio from GPIO 1 (ADC1_CH0)...");
  Serial.println("Tip: Open Tools -> Serial Plotter (115200 baud) for live waveform!\n");

  // Configure ADC resolution
  analogReadResolution(12); // 0 - 4095 (12-bit)
}

void loop() {
  unsigned long startMillis = millis();
  unsigned int peakToPeak = 0;
  unsigned int signalMax = 0;
  unsigned int signalMin = 4095;
  unsigned long signalSum = 0;
  unsigned int sampleCount = 0;

  // Sample microphone for 50 milliseconds
  while (millis() - startMillis < SAMPLE_WINDOW_MS) {
    int sample = analogRead(MIC_PIN);
    signalSum += sample;
    sampleCount++;

    if (sample < 4096) {
      if (sample > signalMax) signalMax = sample;
      if (sample < signalMin) signalMin = sample;
    }
  }

  peakToPeak = signalMax - signalMin;
  float dcBiasVolts = ((float)signalSum / sampleCount) * (3.3 / 4095.0);
  float p2pMillivolts = peakToPeak * (3300.0 / 4095.0);

  // Generate ASCII VU Meter Bar (25 blocks wide)
  int barLength = map(peakToPeak, 0, 1500, 0, 25);
  if (barLength > 25) barLength = 25;
  if (barLength < 0) barLength = 0;

  String bar = "[";
  for (int i = 0; i < 25; i++) {
    if (i < barLength) bar += "=";
    else bar += " ";
  }
  bar += "]";

  // Print results to Serial Monitor
  Serial.print("VU: ");
  Serial.print(bar);
  Serial.print(" | P2P: ");
  Serial.print((int)p2pMillivolts);
  Serial.print(" mV (ADC: ");
  Serial.print(peakToPeak);
  Serial.print(") | DC Bias: ");
  Serial.print(dcBiasVolts, 2);
  Serial.print("V");

  // Activity Status
  if (peakToPeak > 500) {
    Serial.println("  🔥🔥 LOUD SOUND!");
  } else if (peakToPeak > 120) {
    Serial.println("  🗣️ SPEAKING / VOICE");
  } else if (peakToPeak > NOISE_THRESHOLD) {
    Serial.println("  🎵 Soft Sound");
  } else {
    Serial.println("  🤫 Quiet / Ambient");
  }

  // Small delay for smooth terminal output
  delay(10);
}
