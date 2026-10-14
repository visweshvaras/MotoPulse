#!/usr/bin/env python3
"""
MotoPulse Live Microphone Passthrough (Hear Yourself Live!)
Streams real-time digital audio from the INMP441 MEMS microphone(s)
directly into your PC's speakers or headphones with near-zero latency.
Supports:
- Mono (Mic 1)
- Stereo 3D (Mic 1 in Left Ear, Mic 2 in Right Ear!)
"""

import sys
import time
import struct
import argparse
import subprocess
import serial

PORT = "/dev/ttyACM0"
BAUD = 115200
SAMPLE_RATE = 16000

def main():
    parser = argparse.ArgumentParser(description="MotoPulse Live Mic Passthrough")
    parser.add_argument("--stereo", action="store_true", help="Enable stereo mode (Mic 1 Left, Mic 2 Right)")
    parser.add_argument("--gain", type=float, default=1.5, help="Software digital gain multiplier (default: 1.5)")
    args = parser.parse_args()

    channels = 2 if args.stereo else 1
    gain = max(0.2, min(args.gain, 5.0))

    print("=" * 70)
    print("   🎧 MOTO-PULSE LIVE MICROPHONE PASSTHROUGH (REAL-TIME MONITOR)  ")
    print("=" * 70)
    print(f"  • Mode:        {'Stereo 3D (Mic 1 Left, Mic 2 Right)' if args.stereo else 'Mono (Mic 1)'}")
    print(f"  • Sample Rate: {SAMPLE_RATE} Hz (16-bit PCM)")
    print(f"  • Gain:        {gain:.1f}x")
    print(f"  • Destination: PC Audio Output (Speakers / Headphones via aplay)")
    print("=" * 70)

    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
    except Exception as e:
        print(f"\n[ERROR] Cannot open {PORT}: {e}")
        print("Please run: sudo chmod 666 /dev/ttyACM0")
        sys.exit(1)

    # Interrupt and reset MicroPython REPL
    for _ in range(3):
        ser.write(b'\r\x03')
        time.sleep(0.04)
    ser.read_all()
    ser.write(b'\r\x01')  # Raw REPL
    time.sleep(0.08)
    ser.read_all()

    # Launch aplay subprocess for low-latency PCM playback
    try:
        player = subprocess.Popen(
            ["aplay", "-r", str(SAMPLE_RATE), "-f", "S16_LE", "-c", str(channels), "-q", "-B", "20000"],
            stdin=subprocess.PIPE,
            bufsize=1024
        )
    except FileNotFoundError:
        print("\n[ERROR] 'aplay' not found. Trying ffplay...")
        player = subprocess.Popen(
            ["ffplay", "-nodisp", "-autoexit", "-f", "s16le", "-ar", str(SAMPLE_RATE), "-ac", str(channels), "-"],
            stdin=subprocess.PIPE,
            bufsize=1024
        )

    # MicroPython script running on the ESP32-S3
    fmt = "machine.I2S.STEREO" if args.stereo else "machine.I2S.MONO"
    chunk_samples = 256
    raw_chunk_bytes = chunk_samples * 4 * (2 if args.stereo else 1)

    code = f"""
import machine, sys

audio = machine.I2S(
    0,
    sck=machine.Pin(4),
    ws=machine.Pin(5),
    sd=machine.Pin(6),
    mode=machine.I2S.RX,
    bits=32,
    format={fmt},
    rate={SAMPLE_RATE},
    ibuf=4096
)

buf = bytearray({raw_chunk_bytes})

# Continuous high-speed streaming loop
while True:
    audio.readinto(buf)
    sys.stdout.buffer.write(buf)
"""
    ser.write(code.encode('utf-8') + b'\x04')
    time.sleep(0.15)

    print("\n🟢 LIVE PASSTHROUGH ACTIVE!")
    print("👉 Speak into the microphone — you should hear your voice in real-time!")
    if args.stereo:
        print("👉 Tap Mic 1 to hear in your LEFT ear, tap Mic 2 to hear in your RIGHT ear!")
    print("Press Ctrl+C to stop listening.\n")

    max_bar = 25
    words_per_chunk = chunk_samples * channels

    try:
        while True:
            # Read exact raw chunk from ESP32
            raw = ser.read(raw_chunk_bytes)
            if len(raw) < raw_chunk_bytes:
                continue

            words = struct.unpack(f'<{words_per_chunk}i', raw)

            if args.stereo:
                # Interleaved Left and Right
                out_pcm = bytearray(chunk_samples * 2 * 2)
                pos = 0
                max_l = 0
                max_r = 0

                for i in range(0, words_per_chunk, 2):
                    l_val = int((words[i] >> 14) * gain)
                    r_val = int((words[i+1] >> 14) * gain)

                    # Clamp to signed 16-bit
                    l_val = max(-32768, min(32767, l_val))
                    r_val = max(-32768, min(32767, r_val))

                    struct.pack_into('<hh', out_pcm, pos, l_val, r_val)
                    pos += 4

                    abs_l = abs(l_val)
                    abs_r = abs(r_val)
                    if abs_l > max_l: max_l = abs_l
                    if abs_r > max_r: max_r = abs_r

                # Stream to speakers
                try:
                    player.stdin.write(out_pcm)
                    player.stdin.flush()
                except (BrokenPipeError, IOError):
                    break

                # Live terminal visualizer
                b_l = min(max_bar, max_l // 600)
                b_r = min(max_bar, max_r // 600)
                bar_left = "█" * b_l + "░" * (max_bar - b_l)
                bar_right = "█" * b_r + "░" * (max_bar - b_r)
                sys.stdout.write(f"\r🎧 [LEFT MIC 1]: |{bar_left}| {max_l:5d}   [RIGHT MIC 2]: |{bar_right}| {max_r:5d}  ")
                sys.stdout.flush()

            else:
                # Mono
                out_pcm = bytearray(chunk_samples * 2)
                max_val = 0
                for i in range(chunk_samples):
                    val = int((words[i] >> 14) * gain)
                    val = max(-32768, min(32767, val))
                    struct.pack_into('<h', out_pcm, i * 2, val)
                    abs_v = abs(val)
                    if abs_v > max_val: max_val = abs_v

                try:
                    player.stdin.write(out_pcm)
                    player.stdin.flush()
                except (BrokenPipeError, IOError):
                    break

                b = min(max_bar * 2, max_val // 400)
                bar = "█" * b + "░" * (max_bar * 2 - b)
                sys.stdout.write(f"\r🎤 [LIVE MIC]: |{bar}| {max_val:5d}  ")
                sys.stdout.flush()

    except KeyboardInterrupt:
        print("\n\nStopping live passthrough...")
    finally:
        try:
            player.stdin.close()
            player.terminate()
        except Exception:
            pass
        ser.write(b'\r\x03')
        ser.close()
        print("Done. Microphones released.")

if __name__ == "__main__":
    main()
