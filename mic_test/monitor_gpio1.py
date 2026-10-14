#!/usr/bin/env python3
"""
Continuous Live Pin Probe
Monitors GPIO 1 in real time (20 updates/sec)
"""

import sys
import time
import serial

PORT = "/dev/ttyACM0"

def main():
    try:
        ser = serial.Serial(PORT, 115200, timeout=1)
    except Exception as e:
        print(f"Error: {e}")
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
    vals = [adc.read() for _ in range(30)]
    mn = min(vals)
    mx = max(vals)
    avg = sum(vals) // len(vals)
    p2p = mx - mn
    v = (avg * 3.3) / 4095.0
    print(f"PROBE:{avg}:{p2p}:{v:.2f}")
    time.sleep_ms(50)
"""
    ser.write(code.encode() + b'\x04')
    time.sleep(0.2)

    print("Live probe running... (Press Ctrl+C to stop)")
    print(f"{'RAW ADC':>10} | {'VOLTAGE':>10} | {'P2P NOISE':>10} | STATUS")
    print("-" * 55)

    try:
        while True:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line.startswith("PROBE:"):
                parts = line.split(":")
                if len(parts) >= 4:
                    avg = int(parts[1])
                    p2p = int(parts[2])
                    v = float(parts[3])

                    if p2p > 300:
                        status = "⚡ FINGER TOUCH / AC HUM DETECTED!"
                    elif avg < 200:
                        status = "⚠️ TIED TO GROUND (0.1V)"
                    elif avg > 3800:
                        status = "⚠️ TIED TO 3.3V"
                    elif 1800 < avg < 2400:
                        status = "✅ PERFECT BIAS (1.6V - 1.9V)"
                    else:
                        status = "🟡 Sitting steady"

                    print(f"{avg:10d} | {v:9.2f}V | {p2p:10d} | {status}")
    except KeyboardInterrupt:
        ser.write(b'\r\x02')
        ser.close()

if __name__ == "__main__":
    main()
