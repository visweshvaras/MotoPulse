#!/usr/bin/env python3
"""
Live Sound Visualizer for ESP32-S3 + INMP441 Digital I2S Microphone
Displays real-time VU meter with clean channel separation and zero DC distortion.
"""

import sys
import time
import serial

PORT = "/dev/ttyACM0"
BAUD = 115200

def main():
    print("=" * 65)
    print("   🎙️  INMP441 DIGITAL I2S MICROPHONE LIVE SOUND METER      ")
    print("   Sample Rate: 16,000 Hz | Zero-Distortion AC Filtered     ")
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
    ser.write(b'\r\x01')  # Raw REPL
    time.sleep(0.1)
    ser.read_all()

    # Fast MicroPython loop with STEREO I2S to prevent cross-channel chatter
    code = """
import machine, time, struct

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

buf = bytearray(512)
while True:
    audio.readinto(buf)
    # Unpack 128 32-bit words: alternating Left and Right
    words = struct.unpack('<128i', buf)
    
    # Extract Left channel (Mic 1)
    left = [words[i] >> 16 for i in range(0, 128, 2)]
    # Extract Right channel (Mic 2)
    right = [words[i] >> 16 for i in range(1, 128, 2)]
    
    # AC peak-to-peak amplitude
    p2p_l = max(left) - min(left)
    p2p_r = max(right) - min(right)
    
    print(f"VU:{p2p_l}:{p2p_r}")
"""
    ser.write(code.encode('utf-8') + b'\x04')
    time.sleep(0.2)

    print("\nListening to INMP441 on I2S (GPIO 4, 5, 6)...")
    print("Speak, snap fingers, or play music! (Press Ctrl+C to stop)\n")

    try:
        while True:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line.startswith("VU:"):
                parts = line.split(":")
                p2p = int(parts[1])
                p2p_r = int(parts[2]) if len(parts) > 2 else 0
                
                # Dynamic visual meter (0 to 30 chars)
                bar_len = min(30, max(0, int(p2p / 120)))
                bar = "=" * bar_len + " " * (30 - bar_len)

                status = "🤫 Quiet / Ambient"
                if p2p > 3000:
                    status = "🔥🔥 LOUD SOUND / CLAP!"
                elif p2p > 600:
                    status = "🗣️ VOICE DETECTED"
                elif p2p > 150:
                    status = "🎵 Soft Audio"

                # If secondary mic is active, show both
                if p2p_r > 300:
                    r_bar_len = min(15, max(0, int(p2p_r / 200)))
                    r_bar = "=" * r_bar_len + " " * (15 - r_bar_len)
                    print(f"\rVU [Mic1]: [{bar}] {p2p:5d} | [Mic2]: [{r_bar}] {p2p_r:5d} | {status:<20}", end="", flush=True)
                else:
                    print(f"\rVU: [{bar}] | Peak: {p2p:6d} | {status:<25}", end="", flush=True)
    except KeyboardInterrupt:
        print("\n\nStopped by user.")
        ser.write(b'\r\x03')
        time.sleep(0.1)
        ser.write(b'audio.deinit()\r\x04')
        ser.close()

if __name__ == "__main__":
    main()
