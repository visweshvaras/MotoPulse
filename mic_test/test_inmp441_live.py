#!/usr/bin/env python3
"""
Live Sound Visualizer for ESP32-S3 + INMP441 Digital I2S Microphone
Displays real-time VU meter and detects speaking/clapping live!
"""

import sys
import time
import serial

PORT = "/dev/ttyACM0"
BAUD = 115200

def main():
    print("=" * 65)
    print("   🎙️  INMP441 DIGITAL I2S MICROPHONE LIVE SOUND METER      ")
    print("   Sample Rate: 16,000 Hz | 24-Bit Digital Audio            ")
    print("=" * 65)

    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
    except Exception as e:
        print(f"\n[ERROR] Cannot open {PORT}: {e}")
        print("Run: sudo chmod 666 /dev/ttyACM0")
        sys.exit(1)

    for _ in range(3):
        ser.write(b'\r\x03')
        time.sleep(0.05)
    ser.read_all()
    ser.write(b'\r\x01') # Raw REPL
    time.sleep(0.1)
    ser.read_all()

    code = """
import machine, time, struct

audio = machine.I2S(
    0,
    sck=machine.Pin(4),
    ws=machine.Pin(5),
    sd=machine.Pin(6),
    mode=machine.I2S.RX,
    bits=32,
    format=machine.I2S.MONO,
    rate=16000,
    ibuf=2048
)

buf = bytearray(512)
while True:
    audio.readinto(buf)
    samples = struct.unpack('<128i', buf)
    scaled = [s >> 14 for s in samples]
    mn = min(scaled)
    mx = max(scaled)
    p2p = mx - mn
    print(f"VU:{p2p}")
"""
    ser.write(code.encode('utf-8') + b'\x04')
    time.sleep(0.2)

    print("\nListening to INMP441 on I2S (GPIO 4, 5, 6)...")
    print("Speak, snap fingers, or play music! (Press Ctrl+C to stop)\n")

    try:
        while True:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line.startswith("VU:"):
                p2p = int(line.split(":")[1])
                
                # Dynamic log scaling for visual meter (0 to 30 chars)
                bar_len = min(30, max(0, int(p2p / 150)))
                bar = "=" * bar_len + " " * (30 - bar_len)

                status = "🤫 Quiet / Ambient"
                if p2p > 4000:
                    status = "🔥🔥 LOUD SOUND / CLAP!"
                elif p2p > 800:
                    status = "🗣️ VOICE DETECTED"
                elif p2p > 250:
                    status = "🎵 Soft Audio"

                print(f"\rVU: [{bar}] | Peak: {p2p:6d} | {status}   ", end="", flush=True)
    except KeyboardInterrupt:
        print("\n\nStopped by user.")
        ser.write(b'\r\x03')
        time.sleep(0.1)
        ser.write(b'audio.deinit()\r\x04')
        ser.close()

if __name__ == "__main__":
    main()
