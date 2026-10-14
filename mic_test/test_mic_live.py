#!/usr/bin/env python3
"""
Live ESP32-S3 Microphone Tester & VU Meter
Runs via MicroPython REPL over /dev/ttyACM0
"""

import sys
import time
import serial

PORT = "/dev/ttyACM0"
BAUD = 115200

def main():
    print("=" * 60)
    print("  ESP32-S3 Electret Microphone Live Tester")
    print("  Connecting to /dev/ttyACM0...")
    print("=" * 60)

    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
    except serial.SerialException as e:
        print(f"\n[ERROR] Could not open {PORT}: {e}")
        print("Please run: sudo chmod 666 /dev/ttyACM0")
        sys.exit(1)

    time.sleep(0.5)
    # Interrupt any running code and enter raw REPL
    ser.write(b'\r\x03\x03') # Ctrl-C twice
    time.sleep(0.2)
    ser.write(b'\r\x01')    # Ctrl-A (Raw REPL)
    time.sleep(0.2)

    # MicroPython code to sample GPIO 1 and stream data
    script = """
import machine, time
adc = machine.ADC(machine.Pin(1))
adc.atten(machine.ADC.ATTN_11DB)
adc.width(machine.ADC.WIDTH_12BIT)

while True:
    sig_min = 4095
    sig_max = 0
    total = 0
    count = 0
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < 50:
        val = adc.read()
        total += val
        count += 1
        if val < sig_min: sig_min = val
        if val > sig_max: sig_max = val
    p2p = sig_max - sig_min
    avg_v = (total / count) * 3.3 / 4095
    p2p_mv = p2p * 3300 // 4095
    print(f"DATA:{p2p_mv}:{avg_v:.2f}:{p2p}")
"""
    ser.write(script.encode('utf-8') + b'\x04') # Ctrl-D to execute
    time.sleep(0.2)

    print("\nListening to microphone on GPIO 1 (ADC1_CH0)...")
    print("Speak, tap the mic, or clap your hands!\n")

    try:
        while True:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line.startswith("DATA:"):
                parts = line.split(":")
                if len(parts) >= 4:
                    p2p_mv = int(parts[1])
                    bias_v = float(parts[2])
                    raw_p2p = int(parts[3])

                    bar_len = min(30, p2p_mv // 25)
                    bar = "=" * bar_len + " " * (30 - bar_len)

                    status = "🤫 Quiet"
                    if p2p_mv > 600:
                        status = "🔥🔥 LOUD / CLAP!"
                    elif p2p_mv > 150:
                        status = "🗣️ VOICE DETECTED"
                    elif p2p_mv > 40:
                        status = "🎵 Soft Audio"

                    print(f"\rVU: [{bar}] | {p2p_mv:4d} mV | Bias: {bias_v:.2f}V | {status}   ", end="", flush=True)
    except KeyboardInterrupt:
        print("\n\nStopped by user.")
        ser.write(b'\r\x02') # Ctrl-B to exit raw REPL
        ser.close()

if __name__ == "__main__":
    main()
