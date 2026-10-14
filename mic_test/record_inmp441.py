#!/usr/bin/env python3
"""
High-Fidelity Audio Recorder for ESP32-S3 + INMP441 Digital I2S Microphone
Supports:
- Arbitrary recording duration (5s, 10s, 30s, 60s, or press Enter to stop)
- Mono and Stereo (dual-mic) recording modes
- Live recording progress and volume VU meter
- Exports to studio-grade WAV (16 kHz, 16-bit PCM) and MP3
"""

import os
import sys
import time
import wave
import struct
import argparse
import subprocess
import threading
import serial

PORT = "/dev/ttyACM0"
BAUD = 115200
SAMPLE_RATE = 16000
RECORDINGS_DIR = "/home/vishwa/Documents/hacktivate/audio_recordings"

def record_audio(duration_sec=10, stereo=False, manual_stop=False):
    os.makedirs(RECORDINGS_DIR, exist_ok=True)
    channels = 2 if stereo else 1
    
    print("=" * 70)
    print("   🎙️  INMP441 HIGH-FIDELITY STUDIO AUDIO RECORDER")
    print("=" * 70)
    print(f"  • Mode:        {'Stereo (2 Channels)' if stereo else 'Mono (1 Channel)'}")
    print(f"  • Sample Rate: {SAMPLE_RATE} Hz (16-bit Linear PCM)")
    if manual_stop:
        print(f"  • Duration:    Manual (Press Enter to finish recording)")
    else:
        print(f"  • Duration:    {duration_sec} seconds")
    print(f"  • Output Dir:  {RECORDINGS_DIR}")
    print("=" * 70)

    print("\n[1/4] Connecting to ESP32-S3 on /dev/ttyACM0...")
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
    except serial.SerialException as e:
        print(f"[ERROR] Could not open {PORT}: {e}")
        print("Please run: sudo chmod 666 /dev/ttyACM0")
        sys.exit(1)

    # Interrupt any running MicroPython code and enter raw REPL
    for _ in range(3):
        ser.write(b'\r\x03')
        time.sleep(0.04)
    ser.read_all()
    ser.write(b'\r\x01')  # Raw REPL
    time.sleep(0.08)
    ser.read_all()

    fmt = "machine.I2S.STEREO" if stereo else "machine.I2S.MONO"
    chunk_samples = 256
    raw_chunk_bytes = chunk_samples * 4 * channels

    # MicroPython streaming loop
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
print('READY_TO_STREAM')

while True:
    audio.readinto(buf)
    sys.stdout.buffer.write(buf)
"""
    ser.write(code.encode('utf-8') + b'\x04')
    time.sleep(0.15)

    # Prepare output filename
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    mode_tag = "stereo" if stereo else "mono"
    wav_path = os.path.join(RECORDINGS_DIR, f"rec_{mode_tag}_{timestamp}.wav")
    mp3_path = os.path.join(RECORDINGS_DIR, f"rec_{mode_tag}_{timestamp}.mp3")

    wav_file = wave.open(wav_path, "wb")
    wav_file.setnchannels(channels)
    wav_file.setsampwidth(2)  # 16-bit
    wav_file.setframerate(SAMPLE_RATE)

    # Prepare manual stop flag if needed
    stop_event = threading.Event()
    if manual_stop:
        def wait_for_enter():
            input("\n🔴 Recording... Press [ENTER] to stop recording anytime: ")
            stop_event.set()
        t = threading.Thread(target=wait_for_enter, daemon=True)
        t.start()

    print("\n[2/4] 🔴 RECORDING NOW! Speak or play sounds...")
    start_time = time.time()
    total_frames = 0
    words_per_chunk = chunk_samples * channels

    try:
        while True:
            elapsed = time.time() - start_time
            if not manual_stop and elapsed >= duration_sec:
                break
            if manual_stop and stop_event.is_set():
                break

            raw = ser.read(raw_chunk_bytes)
            if len(raw) < raw_chunk_bytes:
                continue

            words = struct.unpack(f'<{words_per_chunk}i', raw)
            out_pcm = bytearray(chunk_samples * 2 * channels)

            max_v = 0
            if stereo:
                pos = 0
                for i in range(0, words_per_chunk, 2):
                    l_val = words[i] >> 14
                    r_val = words[i+1] >> 14
                    l_val = max(-32768, min(32767, l_val))
                    r_val = max(-32768, min(32767, r_val))
                    struct.pack_into('<hh', out_pcm, pos, l_val, r_val)
                    pos += 4
                    v = max(abs(l_val), abs(r_val))
                    if v > max_v: max_v = v
            else:
                for i in range(chunk_samples):
                    val = words[i] >> 14
                    val = max(-32768, min(32767, val))
                    struct.pack_into('<h', out_pcm, i * 2, val)
                    abs_v = abs(val)
                    if abs_v > max_v: max_v = abs_v

            wav_file.writeframes(out_pcm)
            total_frames += chunk_samples

            # Progress display
            bar_len = 20
            v_bar = min(bar_len, max_v // 800)
            meter = "█" * v_bar + "░" * (bar_len - v_bar)
            if manual_stop:
                sys.stdout.write(f"\r⏱️  Elapsed: {elapsed:5.1f}s | Level: |{meter}| {max_v:5d}  ")
            else:
                prog = min(1.0, elapsed / duration_sec)
                pct = int(prog * 100)
                sys.stdout.write(f"\r⏱️  [{pct:3d}%] {elapsed:4.1f}/{duration_sec:4.1f}s | Level: |{meter}| {max_v:5d}  ")
            sys.stdout.flush()

    except KeyboardInterrupt:
        print("\n[INFO] Recording interrupted by user.")
    finally:
        wav_file.close()
        ser.write(b'\r\x03')
        ser.close()

    actual_duration = total_frames / float(SAMPLE_RATE)
    print(f"\n\n[3/4] ✓ Recording Complete! ({actual_duration:.2f} seconds captured)")
    print(f"      Saved WAV: {wav_path}")

    # Convert to MP3
    print("\n[4/4] Converting to MP3...")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", wav_path, "-b:a", "192k", mp3_path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
        )
        print(f"      Saved MP3: {mp3_path}")
    except Exception:
        print("      (ffmpeg conversion skipped)")

    print("\n" + "=" * 70)
    print("🎉 SUCCESS! Your recording is ready.")
    print("=" * 70)

    # Offer immediate playback
    choice = input("\n▶️ Would you like to play this recording now? (Y/n): ").strip().lower()
    if choice != 'n':
        print(f"Playing {os.path.basename(wav_path)}...")
        try:
            subprocess.run(["aplay", wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            subprocess.run(["ffplay", "-nodisp", "-autoexit", wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main():
    parser = argparse.ArgumentParser(description="MotoPulse High-Fidelity Audio Recorder")
    parser.add_argument("--seconds", type=float, default=10.0, help="Duration in seconds (default: 10s)")
    parser.add_argument("--stereo", action="store_true", help="Record in stereo using both microphones")
    parser.add_argument("--manual", action="store_true", help="Record until you press Enter")
    args = parser.parse_args()

    record_audio(duration_sec=args.seconds, stereo=args.stereo, manual_stop=args.manual)

if __name__ == "__main__":
    main()
