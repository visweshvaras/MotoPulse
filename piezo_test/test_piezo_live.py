#!/usr/bin/env python3
"""
Real-Time Piezoelectric Vibration & Knock Sensor Monitor for ESP32-S3
Reads contact vibration from a Piezo element on ADC Pin GPIO 1 (0-3.3V, 12-Bit).
Displays live vibration amplitude, peak transient hold, and knock detection.
"""

import sys
import time
import serial

PORT = "/dev/ttyACM0"
BAUD = 115200

FIRMWARE = """
import machine, time

# ADC on GPIO 1 (11dB attenuation = full 0 to 3.3V range, 12-bit: 0..4095)
adc = machine.ADC(machine.Pin(1))
try:
    adc.atten(machine.ADC.ATTN_11DB)
except Exception:
    pass

# Initial baseline calibration (average of 100 resting samples)
calib_sum = 0
for _ in range(100):
    calib_sum += adc.read()
    time.sleep_us(100)
baseline = calib_sum // 100

print("PIEZO_READY:" + str(baseline))

decay_peak = 0

while True:
    # Sample window of 64 readings (~3ms) to capture fast mechanical transients
    mn = 4095
    mx = 0
    for _ in range(64):
        v = adc.read()
        if v < mn: mn = v
        if v > mx: mx = v
    
    p2p = mx - mn
    
    # Peak decay hold
    if p2p > decay_peak:
        decay_peak = p2p
    else:
        decay_peak = max(0, decay_peak - 25)
        
    print("V:" + str(p2p) + ":" + str(decay_peak) + ":" + str(mx))
    time.sleep_ms(30)
"""

def main():
    print("=" * 68)
    print("   ⚡ ESP32-S3 PIEZO VIBRATION & KNOCK SENSOR LIVE MONITOR   ")
    print("   Reads Structure-Borne Mechanical Shock / Knock on GPIO 1 ")
    print("=" * 68)
    print(f"Connecting to ESP32-S3 on {PORT}...")

    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
    except Exception as e:
        print(f"[ERROR] Cannot open {PORT}: {e}")
        print("Run: sudo chmod 666 /dev/ttyACM0")
        sys.exit(1)

    # Clean interrupt and enter raw REPL
    ser.write(b'\r\x03\r\x03\r\x01')
    time.sleep(0.15)
    ser.read_all()

    print("Arming Piezo ADC sampler on ESP32-S3 (GPIO 1)...")
    ser.write(FIRMWARE.encode('utf-8') + b'\x04')

    t0 = time.time()
    baseline = 0
    while time.time() - t0 < 4.0:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if line.startswith("PIEZO_READY:"):
            baseline = int(line.split(":")[1])
            break

    print(f"✔ Piezo ADC Armed! Resting Baseline: {baseline} / 4095 (~{(baseline/4095)*3.3:.2f}V)")
    print("\n" + "=" * 68)
    print("  📋 Tap the piezo disc or place it on a vibrating surface!")
    print("  (Press Ctrl+C to stop monitor)")
    print("=" * 68 + "\n")

    try:
        while True:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line.startswith("V:"):
                parts = line.split(":")
                p2p = int(parts[1])
                peak = int(parts[2])
                raw_v = int(parts[3])

                # Visual vibration bar (25 characters)
                bar_len = min(25, max(0, int(p2p / 100)))
                bar = "█" * bar_len + "░" * (25 - bar_len)

                if p2p > 2200:
                    badge = "💥💥 HARD KNOCK / SHOCK IMPACT!"
                elif p2p > 800:
                    badge = "⚡ VIBRATION / TAP DETECTED"
                elif p2p > 250:
                    badge = "〰️  Mild Vibration"
                else:
                    badge = "🛡️  Resting / Normal"

                print(f"\r  [{bar}] Vib Amp: {p2p:4d} | Peak: {peak:4d} | {badge:<30}", end="", flush=True)

    except KeyboardInterrupt:
        print("\n\nStopping Piezo monitor...")
        ser.write(b'\r\x03\r\x02')
        ser.close()
        print("Done.")

if __name__ == '__main__':
    main()
