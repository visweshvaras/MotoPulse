#!/usr/bin/env python3
"""
High-Fidelity Audio Recorder for ESP32-S3 + INMP441 Digital I2S Microphone
Optimized for zero-drop, crystal-clear 16,000 Hz 16-bit recording.
Supports dual-mic hardware by strictly isolating channels and removing DC bias.
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
import numpy as np

PORT = "/dev/ttyACM0"
BAUD = 115200
SAMPLE_RATE = 16000
RECORDINGS_DIR = "/home/vishwa/Documents/hacktivate/audio_recordings"

def record_inmp441(duration_sec=3):
    os.makedirs(RECORDINGS_DIR, exist_ok=True)
    
    # Cap duration at 3.5s to fit safely in high-speed ESP32 SRAM
    if duration_sec > 3.5:
        print("[NOTE] High-speed SRAM recording is capped at 3.5 seconds. Recording 3.5 seconds.")
        duration_sec = 3.5
    
    total_samples = int(duration_sec * SAMPLE_RATE)
    # Using 1000 samples (2000 bytes) per chunk
    num_chunks = int(total_samples / 1000)
    actual_samples = num_chunks * 1000
    actual_duration = actual_samples / float(SAMPLE_RATE)

    print("=" * 65)
    print(f"  🎙️  INMP441 DIGITAL STUDIO RECORDER ({SAMPLE_RATE} Hz, 16-Bit Studio PCM)")
    print(f"  ⏱️  Duration: {actual_duration:.1f} seconds ({actual_samples} samples)")
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
    time.sleep(0.12)
    ser.read_all()

    # Fast, glitch-free recording script running on ESP32-S3
    # Reads I2S in STEREO mode to eliminate alternating-channel distortion
    # Directly extracts top 16 bits of Mic 1 (Left Channel) into pre-allocated memory
    code = f"""
import machine, sys, time, gc, ubinascii
gc.collect()

audio = machine.I2S(
    0,
    sck=machine.Pin(4),
    ws=machine.Pin(5),
    sd=machine.Pin(6),
    mode=machine.I2S.RX,
    bits=32,
    format=machine.I2S.STEREO,
    rate={SAMPLE_RATE},
    ibuf=8192
)

NUM_CHUNKS = {num_chunks}
CHUNK_SAMPLES = 1000
chunks = [bytearray(CHUNK_SAMPLES * 2) for _ in range(NUM_CHUNKS)]
in_buf = bytearray(CHUNK_SAMPLES * 8)

# Warmup DMA pipeline
dummy = bytearray(512)
for _ in range(6): audio.readinto(dummy)

print('START_REC')
for c_idx in range(NUM_CHUNKS):
    audio.readinto(in_buf)
    dest = chunks[c_idx]
    # Fast bit extraction: take byte 2 and 3 of every 8-byte stereo frame (Mic 1 Left 16-bit)
    d_pos = 0
    for s_idx in range(0, CHUNK_SAMPLES * 8, 8):
        dest[d_pos] = in_buf[s_idx + 2]
        dest[d_pos + 1] = in_buf[s_idx + 3]
        d_pos += 2

audio.deinit()
print('END_REC')

# Stream chunks via base64
for c in chunks:
    for k in range(0, CHUNK_SAMPLES * 2, 120):
        sys.stdout.write(ubinascii.b2a_base64(c[k:k+120]))
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
            print(f"[ERROR] Timeout waiting for recording start. {err_lines[-2:] if err_lines else ''}")
            ser.close()
            sys.exit(1)

    print("\n" + "🔴" * 25)
    print(f"  🔴 RECORDING NOW! ({actual_duration:.1f} Seconds) 🔴")
    print("  Speak, play music, or test your sound now!")
    print("🔴" * 25 + "\n")

    for s in range(int(actual_duration), 0, -1):
        elapsed = int(actual_duration) - s
        pct = (elapsed / actual_duration) * 100.0
        bar = "█" * int(pct / 4) + "░" * (25 - int(pct / 4))
        print(f"\r  [{bar}] {elapsed:2d}s / {actual_duration:.0f}s ({s}s remaining)...  ", end="", flush=True)
        time.sleep(1.0)
    print(f"\r  [{'█' * 25}] {actual_duration:.1f}s / {actual_duration:.1f}s (Recording Complete!)       \n")

    print("[3/4] Downloading audio from ESP32...")
    all_lines = []
    t_dl = time.time()
    dl_timeout = max(30.0, actual_duration * 4.0)
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

    print(f"  Downloaded {len(pcm_data)//2} audio samples ({len(pcm_data)/(2*SAMPLE_RATE):.2f}s)")
    if len(pcm_data) < 2000:
        print("[ERROR] Captured audio is empty.")
        return None, None

    def enhance_studio_voice(samples_16, fs=16000):
        # 1. DC bias removal in float64 space
        x = samples_16.astype(np.float64) - np.mean(samples_16)
        
        # 2. 2nd order Butterworth High-Pass at 110 Hz
        # Eliminates sub-audible room/table rumble and 50Hz mains hum
        fc = 110.0
        w0 = 2.0 * np.pi * fc / fs
        cos_w0 = np.cos(w0)
        alpha = np.sin(w0) / (2.0 * 0.7071)
        b0 = (1.0 + cos_w0) / 2.0
        b1 = -(1.0 + cos_w0)
        b2 = (1.0 + cos_w0) / 2.0
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_w0
        a2 = 1.0 - alpha
        
        y = np.zeros_like(x)
        x1 = x2 = y1 = y2 = 0.0
        for i in range(len(x)):
            x0 = x[i]
            out = (b0*x0 + b1*x1 + b2*x2 - a1*y1 - a2*y2) / a0
            x2, x1 = x1, x0
            y2, y1 = y1, out
            y[i] = out
            
        # 3. High-shelf presence EQ (+3.5 dB at 2800 Hz)
        # Restores vocal articulation and crispness so speech is never 'plain' or muffled
        f0_shelf = 2800.0
        gain_db = 3.5
        A = 10.0 ** (gain_db / 40.0)
        w0_s = 2.0 * np.pi * f0_shelf / fs
        cos_s = np.cos(w0_s)
        sin_s = np.sin(w0_s)
        alpha_s = sin_s / 2.0 * np.sqrt((A + 1.0/A)*(1.0/0.7071 - 1.0) + 2.0)
        
        b0_s =    A*( (A+1.0) + (A-1.0)*cos_s + 2.0*np.sqrt(A)*alpha_s )
        b1_s = -2.0*A*( (A-1.0) + (A+1.0)*cos_s )
        b2_s =    A*( (A+1.0) + (A-1.0)*cos_s - 2.0*np.sqrt(A)*alpha_s )
        a0_s =        (A+1.0) - (A-1.0)*cos_s + 2.0*np.sqrt(A)*alpha_s
        a1_s =  2.0*( (A-1.0) - (A+1.0)*cos_s )
        a2_s =        (A+1.0) - (A-1.0)*cos_s - 2.0*np.sqrt(A)*alpha_s
        
        z = np.zeros_like(y)
        x1 = x2 = y1 = y2 = 0.0
        for i in range(len(y)):
            x0 = y[i]
            out = (b0_s*x0 + b1_s*x1 + b2_s*x2 - a1_s*y1 - a2_s*y2) / a0_s
            x2, x1 = x1, x0
            y2, y1 = y1, out
            z[i] = out

        # 4. Smart Vocal Normalization + Soft-Knee Tanh Limiter
        p99 = np.percentile(np.abs(z), 99.6)
        target_p99 = 24000.0
        scale = target_p99 / max(p99, 100.0)
        scale = min(scale, 50.0)  # Avoid over-amplifying pure silence
        
        scaled = z * scale
        knee_thresh = 26000.0
        excess = np.maximum(0.0, np.abs(scaled) - knee_thresh)
        compressed = np.where(
            np.abs(scaled) > knee_thresh,
            np.sign(scaled) * (knee_thresh + 6000.0 * np.tanh(excess / 6000.0)),
            scaled
        )
        return np.clip(compressed, -32768, 32767).astype(np.int16)

    # Post-process: Convert to numpy and run studio voice enhancement pipeline
    raw_samples = np.frombuffer(pcm_data, dtype=np.int16)
    enhanced_samples = enhance_studio_voice(raw_samples, SAMPLE_RATE)
    final_pcm = enhanced_samples.tobytes()

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
            "-b:a", "192k", mp3_path
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
    parser.add_argument("--seconds", type=int, default=3, help="Duration in seconds (default: 3)")
    args = parser.parse_args()
    record_inmp441(args.seconds)
