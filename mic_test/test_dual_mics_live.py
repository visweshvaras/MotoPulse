#!/usr/bin/env python3
"""
Dual INMP441 Digital I2S Microphone Live Stereo Sound Meter
Tests both microphones simultaneously:
- Mic 1 (Left Channel: L/R -> GND)
- Mic 2 (Right Channel: L/R -> 3.3V)
"""

import sys
import time
import serial

PORT = "/dev/ttyACM0"
BAUD = 115200

def main():
    print("=" * 70)
    print("   🎙️🎙️  DUAL INMP441 STEREO MICROPHONE LIVE TEST PANEL       ")
    print("   Mic 1: Left Channel (L/R -> GND)                            ")
    print("   Mic 2: Right Channel (L/R -> 3.3V)                          ")
    print("   Shared Bus: SCK (GPIO 4), WS (GPIO 5), SD (GPIO 6)          ")
    print("=" * 70)

    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
    except Exception as e:
        print(f"\n[ERROR] Cannot open {PORT}: {e}")
        print("Please run in your terminal: sudo chmod 666 /dev/ttyACM0")
        sys.exit(1)

    # Interrupt any running MicroPython loop
    for _ in range(3):
        ser.write(b'\r\x03')
        time.sleep(0.05)
    ser.read_all()
    ser.write(b'\r\x01')  # Enter Raw REPL
    time.sleep(0.1)
    ser.read_all()

    # MicroPython script running natively on ESP32-S3
    code = """
import machine, time, struct

# Initialize I2S in STEREO mode to capture both Left & Right channels simultaneously
audio = machine.I2S(
    0,
    sck=machine.Pin(4),
    ws=machine.Pin(5),
    sd=machine.Pin(6),
    mode=machine.I2S.RX,
    bits=32,
    format=machine.I2S.STEREO,
    rate=16000,
    ibuf=4096
)

# 1024 bytes = 256 32-bit words (128 Left samples, 128 Right samples)
buf = bytearray(1024)

while True:
    audio.readinto(buf)
    # Unpack 256 signed 32-bit integers: L0, R0, L1, R1, L2, R2...
    words = struct.unpack('<256i', buf)
    
    # Scale down by 14 bits (INMP441 delivers 24-bit audio in upper bits of 32-bit slot)
    left_samples = [words[i] >> 14 for i in range(0, 256, 2)]
    right_samples = [words[i] >> 14 for i in range(1, 256, 2)]
    
    p2p_left = max(left_samples) - min(left_samples)
    p2p_right = max(right_samples) - min(right_samples)
    
    print(f"STEREO:{p2p_left},{p2p_right}")
"""
    ser.write(code.encode('utf-8') + b'\x04')
    time.sleep(0.2)

    print("\n✓ ESP32-S3 Stereo I2S Initialized!")
    print("Testing both mics in real-time... (Tap or speak near each mic)\n")
    print("Press Ctrl+C to exit.\n")

    max_bar = 30
    scale = 300  # Sensitivity scale

    try:
        while True:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line.startswith("STEREO:"):
                try:
                    parts = line.split(":")[1].split(",")
                    val_left = int(parts[0])
                    val_right = int(parts[1])

                    bar_left_len = min(max_bar, val_left // scale)
                    bar_right_len = min(max_bar, val_right // scale)

                    bar_left = "█" * bar_left_len + "░" * (max_bar - bar_left_len)
                    bar_right = "█" * bar_right_len + "░" * (max_bar - bar_right_len)

                    # Dynamic status message
                    if val_left > 3000 and val_right > 3000:
                        status = "🔊 BOTH MICS ACTIVE"
                    elif val_left > 3000:
                        status = "👈 LEFT MIC DETECTED"
                    elif val_right > 3000:
                        status = "👉 RIGHT MIC DETECTED"
                    else:
                        status = "🤫 QUIET"

                    sys.stdout.write(
                        f"\r[MIC 1 LEFT ]: |{bar_left}| {val_left:5d}  "
                        f"[MIC 2 RIGHT]: |{bar_right}| {val_right:5d}  {status:<22}"
                    )
                    sys.stdout.flush()
                except Exception:
                    pass
    except KeyboardInterrupt:
        print("\n\nStopping test...")
        ser.write(b'\r\x03')
        ser.close()
        print("Done.")

if __name__ == "__main__":
    main()
