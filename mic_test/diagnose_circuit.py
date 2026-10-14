#!/usr/bin/env python3
"""
ESP32-S3 Hardware Circuit Diagnostic Tool
Performs fast 100-sample bursts to detect:
1. DC bias stability
2. Peak-to-peak signal activity (touch hum vs true audio vs dead line)
3. Frequency response to identify open lines or rail saturation
"""

import sys
import time
import serial

PORT = "/dev/ttyACM0"

def main():
    print("=" * 65)
    print("      🔍  ESP32-S3 CIRCUIT HARDWARE DIAGNOSTIC TOOL       ")
    print("=" * 65)

    try:
        ser = serial.Serial(PORT, 115200, timeout=1)
    except Exception as e:
        print(f"[ERROR] Cannot open {PORT}: {e}")
        sys.exit(1)

    time.sleep(0.1)
    ser.write(b'\r\x03\x03\r\x01')
    time.sleep(0.1)

    code = """
import machine, time
adc = machine.ADC(machine.Pin(1))
adc.atten(machine.ADC.ATTN_11DB)
adc.width(machine.ADC.WIDTH_12BIT)

while True:
    samples = []
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < 100:
        samples.append(adc.read())
    
    if samples:
        mn = min(samples)
        mx = max(samples)
        avg = sum(samples) // len(samples)
        p2p = mx - mn
        print(f"DIAG:{mn}:{mx}:{avg}:{p2p}:{len(samples)}")
    time.sleep_ms(20)
"""
    ser.write(code.encode() + b'\x04')
    time.sleep(0.2)

    print("\nReading live hardware metrics from GPIO 1 (every 100ms)...")
    print("Press Ctrl+C to stop.\n")
    print(f"{'MIN':>6} | {'MAX':>6} | {'AVG':>6} | {'VOLTS':>7} | {'P2P':>5} | STATUS & DIAGNOSIS")
    print("-" * 65)

    try:
        while True:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line.startswith("DIAG:"):
                parts = line.split(":")
                if len(parts) >= 6:
                    mn = int(parts[1])
                    mx = int(parts[2])
                    avg = int(parts[3])
                    p2p = int(parts[4])
                    volts = avg * (3.3 / 4095.0)

                    # Diagnostic classification
                    if avg > 4050:
                        status = "⚠️ SHORT TO 3.3V (Railed to VCC!)"
                    elif avg < 50:
                        status = "⚠️ SHORT TO GND (Railed to 0V!)"
                    elif p2p < 8:
                        status = "❌ FLATLINE DC (No audio passing through)"
                    elif p2p > 800:
                        status = "⚡ HIGH SIGNAL / TOUCH HUM DETECTED!"
                    elif p2p > 80:
                        status = "🟢 AUDIO DETECTED! (Mic responding)"
                    else:
                        status = "🟡 Ambient electrical noise"

                    print(f"{mn:6d} | {mx:6d} | {avg:6d} | {volts:6.2f}V | {p2p:5d} | {status}")
    except KeyboardInterrupt:
        print("\n\nDiagnostic stopped.")
        ser.write(b'\r\x02')
        ser.close()

if __name__ == "__main__":
    main()
