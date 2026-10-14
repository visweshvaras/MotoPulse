#!/usr/bin/env python3
"""
Real-Time Piezoelectric Vibration & Knock Sensor Monitor for ESP32-S3
Direct 2-Wire Connection (Red -> GPIO 1, Black -> GND) with Internal Pull-Down.
Features dynamic noise-floor auto-calibration, peak hold, and mechanical shock detection.
"""

import sys
import time
import serial

PORT = "/dev/ttyACM0"
BAUD = 115200

FIRMWARE = """
import machine, time

# Configure GPIO 1 with internal Pull-Down resistor (~45k)
# Allows DIRECT connection of raw 2-wire piezo discs without external resistors!
pin1 = machine.Pin(1, machine.Pin.IN, machine.Pin.PULL_DOWN)
adc = machine.ADC(pin1)
try:
    adc.atten(machine.ADC.ATTN_11DB)
except Exception:
    pass

# Auto-calibrate resting baseline & circuit noise floor
calib_vals = [adc.read() for _ in range(128)]
baseline = sum(calib_vals) // 128
noise_floor = max(calib_vals) - min(calib_vals)

thresh_tap = max(500, int(noise_floor * 1.4))
thresh_knock = max(1100, int(noise_floor * 2.5))
thresh_hard = max(2000, int(noise_floor * 4.0))

print("PIEZO_READY:" + str(baseline) + ":" + str(noise_floor) + ":" + str(thresh_tap) + ":" + str(thresh_knock) + ":" + str(thresh_hard))

decay_peak = 0

while True:
    # 64 consecutive readings (~3ms) to capture transient mechanical shockwaves
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
        decay_peak = max(0, decay_peak - 30)
        
    print("V:" + str(p2p) + ":" + str(decay_peak) + ":" + str(mx))
    time.sleep_ms(25)
"""

def main():
    print("=" * 70)
    print("   ⚡ ESP32-S3 PIEZOELECTRIC VIBRATION & KNOCK SENSOR MONITOR   ")
    print("   Direct 2-Wire Connection: Red -> GPIO 1 | Black -> GND   ")
    print("   Measures Structure-Borne Mechanical Shock Waves on 12-Bit ADC ")
    print("=" * 70)
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

    print("Calibrating resting piezo baseline and noise floor on GPIO 1...")
    raw_code = FIRMWARE.encode('utf-8') + b'\x04'
    chunk_sz = 256
    for i in range(0, len(raw_code), chunk_sz):
        ser.write(raw_code[i : i + chunk_sz])
        time.sleep(0.015)

    t0 = time.time()
    baseline = 2700
    noise_floor = 350
    thresh_tap = 550
    thresh_knock = 1100
    thresh_hard = 2000

    while time.time() - t0 < 5.0:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if line.startswith("PIEZO_READY:"):
            parts = line.split(":")
            baseline = int(parts[1])
            noise_floor = int(parts[2])
            thresh_tap = int(parts[3])
            thresh_knock = int(parts[4])
            thresh_hard = int(parts[5])
            break

    print(f"✔ Calibration Complete:")
    print(f"  • Resting Baseline : {baseline} / 4095 (~{(baseline/4095)*3.3:.2f}V)")
    print(f"  • Ambient Noise Floor: {noise_floor} counts")
    print(f"  • Tap Threshold     : {thresh_tap} counts")
    print(f"  • Knock Threshold   : {thresh_knock} counts")
    print("\n" + "=" * 70)
    print("  📋 Tap the piezo disc, flick it, or tap the table to test!")
    print("  (Press Ctrl+C to stop monitor)")
    print("=" * 70 + "\n")

    try:
        while True:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line.startswith("V:"):
                parts = line.split(":")
                p2p = int(parts[1])
                peak = int(parts[2])
                raw_v = int(parts[3])

                # Visual vibration bar (25 characters)
                bar_len = min(25, max(0, int(p2p * 25 / (thresh_knock * 1.8))))
                bar = "█" * bar_len + "░" * (25 - bar_len)

                if p2p >= thresh_hard:
                    badge = "💥💥 HARD KNOCK / SHOCK IMPACT!"
                elif p2p >= thresh_knock:
                    badge = "⚡ HEAVY TAP / KNOCK DETECTED"
                elif p2p >= thresh_tap:
                    badge = "〰️  VIBRATION / LIGHT TAP"
                else:
                    badge = "🛡️  Resting / Normal"

                print(f"\r  [{bar}] Vib: {p2p:4d} | Peak: {peak:4d} | {badge:<30}", end="", flush=True)

    except KeyboardInterrupt:
        print("\n\nStopping Piezo monitor...")
        ser.write(b'\r\x03\r\x02')
        ser.close()
        print("Piezo monitor stopped cleanly.")

if __name__ == '__main__':
    main()
