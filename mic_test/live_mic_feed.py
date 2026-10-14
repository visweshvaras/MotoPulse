#!/usr/bin/env python3
"""
Real-Time Live Microphone Feed for ESP32-S3 + INMP441
Streams low-latency audio from ESP32 directly to PC speakers / headphones
while rendering a real-time responsive VU volume meter in the terminal.
"""

import sys
import os
import time
import serial
import subprocess
import shutil

PORT = "/dev/ttyACM0"
BAUD = 115200

ESP32_FIRMWARE = """
import machine, sys, time

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

buf_in = bytearray(512)
buf_out = bytearray(32)

# Calibrate DC bias on startup
calib_sum = 0
for _ in range(25):
    audio.readinto(buf_in)
    b_high = int(buf_in[3])
    b_low = int(buf_in[2])
    v = (b_high << 8) | b_low
    if v >= 32768: v -= 65536
    calib_sum += v
dc = calib_sum // 25

@micropython.viper
def process_and_extract_8k(src: ptr8, dst: ptr8, n_stereo: int, dc_val: int, gain: int):
    out_idx = 0
    for i in range(0, n_stereo, 2):
        base = i * 8
        b_low = int(src[base + 2])
        b_high = int(src[base + 3])
        s16 = (b_high << 8) | b_low
        if s16 >= 32768:
            s16 -= 65536
        ac = s16 - dc_val
        val = (ac * gain) >> 8
        if val > 127: val = 127
        elif val < -128: val = -128
        dst[out_idx] = val + 128
        out_idx += 1

print('FEED_READY')
while True:
    audio.readinto(buf_in)
    process_and_extract_8k(buf_in, buf_out, 64, dc, 8)
    sys.stdout.buffer.write(buf_out)
"""

def main():
    print("=" * 68)
    print("   🎧 ESP32-S3 + INMP441 REAL-TIME LIVE MIC FEED MONITOR    ")
    print("   Streams live audio to PC speakers & renders live VU meter ")
    print("=" * 68)

    # Check for aplay or alternative audio player
    has_aplay = shutil.which("aplay") is not None
    if not has_aplay:
        print("[WARNING] 'aplay' not found. Only terminal visualizer will run.")

    print(f"Connecting to ESP32-S3 on {PORT}...")
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
    except Exception as e:
        print(f"[ERROR] Cannot open {PORT}: {e}")
        print("Run: sudo chmod 666 /dev/ttyACM0")
        sys.exit(1)

    # Enter raw REPL cleanly
    ser.write(b'\r\x03\r\x03\r\x01')
    time.sleep(0.12)
    ser.read_all()

    print("Arming live audio stream on ESP32-S3...")
    ser.write(ESP32_FIRMWARE.encode('utf-8') + b'\x04')

    t0 = time.time()
    ready = False
    while time.time() - t0 < 4.0:
        line = ser.readline()
        if b'FEED_READY' in line:
            ready = True
            break

    if not ready:
        print("[ERROR] ESP32 did not respond with ready signal.")
        ser.write(b'\r\x03\r\x02')
        ser.close()
        sys.exit(1)

    print("✔ Live stream armed! Initializing audio pipeline...")
    player = None
    if has_aplay:
        try:
            player = subprocess.Popen(
                ["aplay", "-q", "-f", "U8", "-r", "8000", "-c", "1", "-B", "100000"],
                stdin=subprocess.PIPE,
                stderr=subprocess.DEVNULL
            )
            print("🔊 Live speaker playback: ACTIVE (8000 Hz, 8-Bit Low-Latency)")
        except Exception as e:
            print(f"[WARNING] Could not start audio player: {e}")

    print("\n" + "=" * 68)
    print("  🎙️  SPEAK INTO THE MICROPHONE NOW! (Press Ctrl+C to Stop) ")
    print("=" * 68 + "\n")

    chunk_size = 128
    peak_hold = 0
    decay_counter = 0

    try:
        while True:
            chunk = ser.read(chunk_size)
            if not chunk:
                continue

            # Stream chunk to PC speakers
            if player and player.stdin:
                try:
                    player.stdin.write(chunk)
                    player.stdin.flush()
                except Exception:
                    pass

            # Calculate amplitude from unsigned 8-bit samples (center is 128)
            amps = [abs(b - 128) for b in chunk]
            p2p = max(amps) * 256  # scale to match 16-bit range

            if p2p > peak_hold:
                peak_hold = p2p
                decay_counter = 0
            else:
                decay_counter += 1
                if decay_counter > 3:
                    peak_hold = max(0, peak_hold - 250)

            # Visual volume bar (30 characters)
            bar_len = min(30, max(0, int(p2p / 160)))
            bar = "█" * bar_len + "░" * (30 - bar_len)

            if p2p > 4500:
                badge = "🔥🔥 CLAP / LOUD SOUND"
            elif p2p > 1200:
                badge = "🗣️  VOICE DETECTED"
            elif p2p > 400:
                badge = "🎵 Soft Sound"
            else:
                badge = "🤫 Quiet / Ambient"

            print(f"\r  [{bar}] Peak: {p2p:5d} | {badge:<22}", end="", flush=True)

    except KeyboardInterrupt:
        print("\n\nStopping live mic monitor...")
    finally:
        if player:
            try:
                if player.stdin:
                    player.stdin.close()
                player.terminate()
            except Exception:
                pass
        ser.write(b'\r\x03\r\x02')
        time.sleep(0.1)
        ser.close()
        print("Live feed closed cleanly.")

if __name__ == '__main__':
    main()
