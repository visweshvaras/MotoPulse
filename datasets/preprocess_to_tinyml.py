#!/usr/bin/env python3
"""
MotoPulse Dataset Preprocessor for ESP32-S3 TinyML
Converts all uploaded raw automotive audio (MP3, WAV, stereo, 44.1k/48k)
into standardized 16,000 Hz, 16-Bit Mono PCM WAV format.
"""

import os
import sys
import csv
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")
MANIFEST_IN = os.path.join(BASE_DIR, "dataset_manifest.csv")
MANIFEST_OUT = os.path.join(BASE_DIR, "manifests", "processed_manifest.csv")

TARGET_SAMPLE_RATE = 16000
TARGET_CHANNELS = 1

def main():
    print("=" * 68)
    print("   🚗 MotoPulse TinyML Dataset Preprocessor (16 kHz 16-Bit PCM)  ")
    print("=" * 68)

    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "manifests"), exist_ok=True)

    # Read manifest mappings
    manifest_map = {}
    if os.path.isfile(MANIFEST_IN):
        with open(MANIFEST_IN, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                fname = row.get("file_name", "").strip()
                if fname:
                    manifest_map[fname] = row

    raw_files = sorted([f for f in os.listdir(RAW_DIR) if f.lower().endswith((".wav", ".mp3", ".flac", ".ogg", ".m4a"))])
    if not raw_files:
        print("[INFO] No raw audio files found in datasets/raw/.")
        return

    print(f"Found {len(raw_files)} raw audio files. Converting to 16,000 Hz Mono PCM...\n")

    processed_rows = []

    for f in raw_files:
        in_path = os.path.join(RAW_DIR, f)
        
        # Standardize output filename: label_cleanName.wav
        meta = manifest_map.get(f, {})
        label = meta.get("label", "unknown_defect")
        
        clean_base = os.path.splitext(f)[0]
        # Clean special chars
        clean_base = clean_base.replace(" ", "_").replace("(", "").replace(")", "").replace("[", "").replace("]", "")
        if not clean_base.startswith(label):
            out_name = f"{label}_{clean_base}.wav"
        else:
            out_name = f"{clean_base}.wav"

        out_path = os.path.join(PROCESSED_DIR, out_name)

        # Run ffmpeg to convert to 16kHz Mono 16-bit PCM WAV
        cmd = [
            "ffmpeg", "-y", "-i", in_path,
            "-ac", str(TARGET_CHANNELS),
            "-ar", str(TARGET_SAMPLE_RATE),
            "-c:a", "pcm_s16le",
            out_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0:
            size_kb = os.path.getsize(out_path) / 1024
            dur_cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", out_path]
            dur_res = subprocess.run(dur_cmd, capture_output=True, text=True)
            dur_sec = float(dur_res.stdout.strip() or 0)

            print(f"  ✔ [DONE] {out_name[:48]:<48} | {dur_sec:5.1f}s | {size_kb:6.1f} KB")

            row_out = {
                "file_name": out_name,
                "label": label,
                "duration_sec": round(dur_sec, 2),
                "sample_rate": TARGET_SAMPLE_RATE,
                "channels": TARGET_CHANNELS,
                "bit_depth": 16,
                "vehicle_make_model": meta.get("vehicle_make_model", "Passenger Car"),
                "engine_type": meta.get("engine_type", "Petrol"),
                "sensor_location": meta.get("sensor_location", "Engine Bay"),
                "contributor": meta.get("recorded_by", "Ishan"),
                "notes": meta.get("notes", "")
            }
            processed_rows.append(row_out)
        else:
            print(f"  ❌ [FAIL] Could not process {f}")

    # Write processed manifest
    fieldnames = [
        "file_name", "label", "duration_sec", "sample_rate", "channels",
        "bit_depth", "vehicle_make_model", "engine_type", "sensor_location",
        "contributor", "notes"
    ]
    with open(MANIFEST_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(processed_rows)

    print("\n" + "=" * 68)
    print(f"🎉 Preprocessing complete! {len(processed_rows)} files ready in datasets/processed/")
    print(f"📋 Manifest updated: datasets/manifests/processed_manifest.csv")
    print("=" * 68)

if __name__ == "__main__":
    main()
