#!/usr/bin/env python3
"""
High-Fidelity Audio Recorder for ESP32-S3 + INMP441 Digital I2S Microphone
Records 16,000 Hz 16-bit studio audio, normalizes, and exports to WAV and MP3.
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
SAMPLE_RATE = 16000
RECORDINGS_DIR = "/home/vishwa/Documents/hacktivate/audio_recordings"

def record_inmp441(duration_sec=3):
    os.makedirs(RECORDINGS_DIR, exist_ok=True)
    
    # Cap duration at 3.5s to fit comfortably in SRAM
    if duration_sec > 3.5:
        print("[NOTE] Max single-shot duration in high-speed SRAM is 3.5 seconds. Recording 3.5 seconds.")
        duration_sec = 3.5
    total_samples = int(duration_sec * SAMPLE_RATE)

    print("=" * 65)
    print(f"  🎙️  INMP441 DIGITAL STUDIO RECORDER ({SAMPLE_RATE} Hz, 16-Bit Mono)")
    print(f"  ⏱️  Duration: {duration_sec} seconds ({total_samples} samples)")
    print(f"  📁 Output Folder: {RECORDINGS_DIR}")
    print("=" * 65)

    print("\n[1/4] Connecting to ESP32-S3 on /dev/ttyACM0...")
    try:
        ser = serial.Serial(PORT, BAUD, timeout=2)
    except serial.SerialException as e:
        print(f"[ERROR] Could not open {PORT}: {e}")
        print("Run: sudo chmod 666 /dev/ttyACM0")
        sys.exit(1)

    # Clean interrupt and enter raw REPL
    ser.write(b'\r\x03\r\x03\r\x01')
    time.sleep(0.15)
    ser.read_all()

    code = f"""
import machine, sys, time, gc, struct, ubinascii
gc.collect()

CHUNK_BYTES = 2048
N_TOTAL_BYTES = {total_samples} * 2
NUM_CHUNKS = (N_TOTAL_BYTES + CHUNK_BYTES - 1) // CHUNK_BYTES
chunks = [bytearray(CHUNK_BYTES) for _ in range(NUM_CHUNKS)]

audio = machine.I2S(
    0,
    sck=machine.Pin(4),
    ws=machine.Pin(5),
    sd=machine.Pin(6),
    mode=machine.I2S.RX,
    bits=32,
    format=machine.I2S.MONO,
    rate={SAMPLE_RATE},
    ibuf=2048
)

temp_in = bytearray(512)
audio.readinto(temp_in)
audio.readinto(temp_in)

print('START_REC')
total_bytes_stored = 0
cur_chunk = 0
cur_pos = 0

while total_bytes_stored < N_TOTAL_BYTES and cur_chunk < NUM_CHUNKS:
    n = audio.readinto(temp_in)
    count = n // 4
    for j in range(count):
        if total_bytes_stored >= N_TOTAL_BYTES:
            break
        s = struct.unpack_from('<i', temp_in, j * 4)[0]
        val16 = s >> 14
        if val16 > 32767: val16 = 32767
        elif val16 < -32768: val16 = -32768
        struct.pack_into('<h', chunks[cur_chunk], cur_pos, val16)
        cur_pos += 2
        total_bytes_stored += 2
        if cur_pos >= CHUNK_BYTES:
            cur_pos = 0
            cur_chunk += 1
            if cur_chunk >= NUM_CHUNKS:
                break

audio.deinit()
print('END_REC')

for c_i in range(cur_chunk if cur_pos == 0 else cur_chunk + 1):
    c_data = chunks[c_i]
    limit = cur_pos if (c_i == cur_chunk and cur_pos > 0) else CHUNK_BYTES
    for k in range(0, limit, 120):
        sys.stdout.write(ubinascii.b2a_base64(c_data[k:k+120]))
print('ALL_SENT')
"""
    print("[2/4] Arming recording on ESP32-S3...")
    ser.write(code.encode('utf-8') + b'\x04')

    t_wait = time.time()
    err_lines = []
    while True:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if 'START_REC' in line:
            break
        if line:
            err_lines.append(line)
        if time.time() - t_wait > 5.0:
            print(f"[ERROR] Timeout waiting for recording start. Diagnostic: {err_lines[-3:] if err_lines else 'No response'}")
            ser.close()
            sys.exit(1)

    print("\n" + "🔴" * 25)
    print(f"  🔴 RECORDING NOW! ({duration_sec} Seconds) 🔴")
    print("  Speak, play music, or test your sound now!")
    print("🔴" * 25 + "\n")

    for s in range(duration_sec, 0, -1):
        elapsed = duration_sec - s
        pct = (elapsed / duration_sec) * 100.0
        bar = "█" * int(pct / 4) + "░" * (25 - int(pct / 4))
        print(f"\r  [{bar}] {elapsed:2d}s / {duration_sec}s ({s}s remaining)...  ", end="", flush=True)
        time.sleep(1.0)
    print(f"\r  [{'█' * 25}] {duration_sec}s / {duration_sec}s (Recording Complete!)       \n")

    print("[3/4] Downloading audio from ESP32...")
    all_lines = []
    t_dl = time.time()
    dl_timeout = max(30.0, duration_sec * 4.0)
    while time.time() - t_dl < dl_timeout:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if 'ALL_SENT' in line:
            break
        if line and not line.startswith('OK') and not line.startswith('>') and not line.startswith('END_REC'):
            all_lines.append(line)

    ser.write(b'\r\x02')
    ser.close()

    pcm_data = bytearray()
    for l in all_lines:
        try:
            pcm_data.extend(base64.b64decode(l))
        except Exception:
            pass

    print(f"  Downloaded {len(pcm_data)//2} audio samples ({len(pcm_data)/(2*SAMPLE_RATE):.1f}s)")
    if len(pcm_data) < 2000:
        print("[ERROR] Captured audio is empty.")
        return None, None

    # Post-process: Remove any remaining DC offset & Normalize
    num_samples = len(pcm_data) // 2
    samples_16 = list(struct.unpack(f'<{num_samples}h', pcm_data))
    
    mean_dc = sum(samples_16) / len(samples_16)
    ac_samples = [s - mean_dc for s in samples_16]
    max_val = max(abs(s) for s in ac_samples) if ac_samples else 1
    if max_val == 0: max_val = 1

    scale = (32767.0 * 0.90) / max_val
    scale = min(scale, 50.0) # avoid over-amplifying silence

    final_pcm = bytearray()
    for s in ac_samples:
        val = int(s * scale)
        val = max(-32768, min(32767, val))
        final_pcm.extend(struct.pack('<h', val))

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    wav_path = os.path.join(RECORDINGS_DIR, f"inmp441_record_{timestamp}.wav")
    mp3_path = os.path.join(RECORDINGS_DIR, f"inmp441_record_{timestamp}.mp3")

    with wave.open(wav_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(final_pcm)

    wav_size = os.path.getsize(wav_path) / 1024

    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", wav_path,
            "-b:a", "128k", mp3_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        mp3_size = os.path.getsize(mp3_path) / 1024
        print(f"\n[4/4] Encoding complete!")
        print(f"  🎵 MP3 File: {mp3_path} ({mp3_size:.1f} KB)")
        print(f"  💾 WAV File: {wav_path} ({wav_size:.1f} KB)")
    except Exception as e:
        print(f"[NOTE] MP3 encoding notice: {e}")

    return wav_path, mp3_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Record studio audio with INMP441 I2S")
    parser.add_argument("--seconds", type=int, default=10, help="Duration in seconds (default: 10)")
    args = parser.parse_args()
    record_inmp441(args.seconds)
