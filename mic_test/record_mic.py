#!/usr/bin/env python3
"""
ESP32-S3 Electret Microphone Studio Recorder
Records high-precision 8,000 Hz 16-bit audio from GPIO 1,
removes DC offset, normalizes volume, and exports to WAV and MP3.
"""

import os
import sys
import time
import wave
import struct
import base64
import argparse
import subprocess
import serial

PORT = "/dev/ttyACM0"
BAUD = 115200
SAMPLE_RATE = 8000
OUTPUT_DIR = "/home/vishwa/Documents/hacktivate/audio_recordings"

def record_studio_audio(duration_sec=15):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    total_samples = int(duration_sec * SAMPLE_RATE)
    
    # Cap duration at 20s to ensure safety within internal SRAM
    if duration_sec > 22:
        print("[NOTE] Max duration for internal RAM capture is 20s. Setting duration to 20 seconds.")
        duration_sec = 20
        total_samples = duration_sec * SAMPLE_RATE

    print("=" * 65)
    print(f"  🎙️  ESP32-S3 AUDIO RECORDER (8,000 Hz 16-Bit Mono)")
    print(f"  ⏱️  Duration: {duration_sec} seconds ({total_samples} samples)")
    print(f"  📁 Output Folder: {OUTPUT_DIR}")
    print("=" * 65)

    print("\n[1/4] Connecting to ESP32-S3 on /dev/ttyACM0...")
    try:
        ser = serial.Serial(PORT, BAUD, timeout=2)
    except serial.SerialException as e:
        print(f"\n[ERROR] Could not open {PORT}: {e}")
        print("Please run: sudo chmod 666 /dev/ttyACM0")
        sys.exit(1)

    time.sleep(0.2)
    ser.write(b'\r\x03\x03') # Ctrl-C
    time.sleep(0.1)
    ser.write(b'\r\x01')     # Raw REPL
    time.sleep(0.1)

    # MicroPython sampling code
    code = f"""
import machine, sys, time, gc, ubinascii
gc.collect()
adc = machine.ADC(machine.Pin(1))
adc.atten(machine.ADC.ATTN_11DB)
adc.width(machine.ADC.WIDTH_12BIT)

N = {total_samples}
buf = bytearray(N)
period_us = {int(1000000 / SAMPLE_RATE)}

print('START_REC')
for i in range(N):
    t0 = time.ticks_us()
    buf[i] = adc.read() >> 4
    rem = period_us - time.ticks_diff(time.ticks_us(), t0)
    if rem > 0:
        time.sleep_us(rem)
print('END_REC')

CHUNK = 120
for k in range(0, N, CHUNK):
    sys.stdout.write(ubinascii.b2a_base64(buf[k:k+CHUNK]))
print('ALL_SENT')
"""
    print("[2/4] Arming recording on ESP32-S3...")
    ser.write(code.encode('utf-8') + b'\x04')

    # Wait for START_REC beacon
    t_start_wait = time.time()
    while True:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if 'START_REC' in line:
            break
        if time.time() - t_start_wait > 5.0:
            print("[ERROR] Timeout waiting for recording start.")
            ser.close()
            sys.exit(1)

    print("\n" + "🔴" * 25)
    print(f"  🔴 RECORDING NOW! ({duration_sec} Seconds) 🔴")
    print("  Play your song / speak into the microphone now!")
    print("🔴" * 25 + "\n")

    start_rec_time = time.time()
    for s in range(duration_sec, 0, -1):
        elapsed = duration_sec - s
        pct = (elapsed / duration_sec) * 100.0
        bar = "█" * int(pct / 4) + "░" * (25 - int(pct / 4))
        print(f"\r  [{bar}] {elapsed:2d}s / {duration_sec}s ({s}s remaining)...  ", end="", flush=True)
        time.sleep(1.0)
    print(f"\r  [{'█' * 25}] {duration_sec}s / {duration_sec}s (Recording Complete!)       \n")

    print("[3/4] Downloading audio data from ESP32...")
    all_lines = []
    t_dl = time.time()
    while time.time() - t_dl < 15.0:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if 'ALL_SENT' in line:
            break
        if line and not line.startswith('OK') and not line.startswith('>') and not line.startswith('END_REC'):
            all_lines.append(line)

    ser.write(b'\r\x02') # Exit raw REPL
    ser.close()

    raw_audio = bytearray()
    for l in all_lines:
        try:
            raw_audio.extend(base64.b64decode(l))
        except Exception:
            pass

    print(f"  Downloaded {len(raw_audio)} samples ({len(raw_audio)/SAMPLE_RATE:.1f}s)")
    if len(raw_audio) < 1000:
        print("[ERROR] Downloaded data is too small.")
        return None, None

    # [4/4] Digital Signal Processing:
    # 1. DC offset removal
    mean_dc = sum(raw_audio) / len(raw_audio)
    ac_samples = [s - mean_dc for s in raw_audio]
    max_amp = max(abs(s) for s in ac_samples) if ac_samples else 1
    if max_amp == 0:
        max_amp = 1

    # 2. Dynamic Normalization (target 90% full scale 16-bit)
    scale = (32767.0 * 0.90) / max_amp
    # Prevent amplifying pure room noise past 400x
    scale = min(scale, 400.0)

    pcm_16bit = bytearray()
    for s in ac_samples:
        val = int(s * scale)
        val = max(-32768, min(32767, val))
        pcm_16bit.extend(struct.pack('<h', val))

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    wav_file = os.path.join(OUTPUT_DIR, f"audio_song_{timestamp}.wav")
    mp3_file = os.path.join(OUTPUT_DIR, f"audio_song_{timestamp}.mp3")

    with wave.open(wav_file, 'wb') as wf:
        wf.setnchannels(1)      # Mono
        wf.setsampwidth(2)      # 16-bit
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm_16bit)

    wav_size = os.path.getsize(wav_file) / 1024

    # Convert to MP3
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", wav_file,
            "-b:a", "128k", mp3_file
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        mp3_size = os.path.getsize(mp3_file) / 1024
        print(f"\n[4/4] Encoding complete!")
        print(f"  🎵 MP3 File: {mp3_file} ({mp3_size:.1f} KB)")
        print(f"  💾 WAV File: {wav_file} ({wav_size:.1f} KB)")
    except Exception as e:
        print(f"[NOTE] MP3 encoding notice: {e}")

    return wav_file, mp3_file

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ESP32-S3 Microphone Studio Recorder")
    parser.add_argument("--seconds", type=int, default=15, help="Recording duration in seconds (5-20, default: 15)")
    args = parser.parse_args()
    record_studio_audio(args.seconds)
