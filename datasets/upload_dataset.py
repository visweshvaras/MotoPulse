#!/usr/bin/env python3
"""
MotoPulse Dataset Ingestion & Annotation Tool
Helps teammates ingest and annotate raw car acoustic audio samples into datasets/raw/
and automatically updates datasets/dataset_manifest.csv.
"""

import os
import sys
import csv
import shutil
import argparse
import wave

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "raw")
MANIFEST_PATH = os.path.join(BASE_DIR, "dataset_manifest.csv")

VALID_CLASSES = [
    "normal_idle",
    "engine_knocking",
    "bearing_wear",
    "valve_ticking",
    "belt_slippage",
    "exhaust_leak",
    "alternator_whine",
    "other_defect"
]

def check_wav_format(file_path):
    """Verify file is a valid 16-bit PCM WAV."""
    try:
        with wave.open(file_path, "rb") as wf:
            channels = wf.getnchannels()
            sample_rate = wf.getframerate()
            sample_width = wf.getsampwidth()
            frames = wf.getnframes()
            duration = frames / float(sample_rate)
            return True, {
                "channels": channels,
                "sample_rate": sample_rate,
                "bit_depth": sample_width * 8,
                "duration_sec": round(duration, 2)
            }
    except Exception as e:
        return False, str(e)

def main():
    parser = argparse.ArgumentParser(description="MotoPulse Automotive Acoustic Dataset Uploader")
    parser.add_argument("--file", help="Path to input audio file (.wav)")
    args = parser.parse_args()

    print("=" * 60)
    print("🚗 MotoPulse Automotive Acoustic Dataset Uploader")
    print("=" * 60)

    input_file = args.file
    if not input_file:
        input_file = input("Enter path to recording (.wav): ").strip().strip("'\"")

    if not os.path.isfile(input_file):
        print(f"❌ Error: File not found: {input_file}")
        sys.exit(1)

    # Check WAV
    valid, info = check_wav_format(input_file)
    if not valid:
        print(f"❌ Error: Invalid WAV file: {info}")
        sys.exit(1)

    print(f"✓ WAV Validated: {info['sample_rate']} Hz, {info['bit_depth']}-bit, {info['channels']} channel(s), {info['duration_sec']}s")

    # Select Defect Class
    print("\nSelect Defect Class:")
    for idx, c in enumerate(VALID_CLASSES, 1):
        print(f"  [{idx}] {c}")
    
    choice = input(f"Choice [1-{len(VALID_CLASSES)}]: ").strip()
    try:
        c_idx = int(choice) - 1
        label = VALID_CLASSES[c_idx]
    except Exception:
        label = "normal_idle"
    print(f"-> Selected label: {label}")

    vehicle = input("Vehicle Make & Model (e.g. Maruti Swift 1.3 DDiS): ").strip() or "Unknown Vehicle"
    engine_type = input("Engine Type (Petrol / Diesel / EV / Hybrid): ").strip() or "Petrol"
    rpm = input("Engine RPM (e.g. 850, 1500, 2500): ").strip() or "Idle"
    distance = input("Distance from Mic in cm (e.g. 20, 50): ").strip() or "30"
    location = input("Sensor Placement (e.g. Engine Block, Alternator, Hood): ").strip() or "Engine Bay"
    contributor = input("Your Name (e.g. Ishan, Visweshwara): ").strip() or "Contributor"
    notes = input("Additional Notes / Symptoms: ").strip() or "Acoustic diagnostic recording"

    # Destination filename
    base_name = os.path.basename(input_file).replace(" ", "_")
    target_name = f"{label}_{base_name}"
    dest_path = os.path.join(RAW_DIR, target_name)

    # Copy to raw/
    shutil.copy2(input_file, dest_path)
    print(f"✓ Copied file to: datasets/raw/{target_name}")

    # Append to manifest
    file_exists = os.path.isfile(MANIFEST_PATH)
    with open(MANIFEST_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists or os.path.getsize(MANIFEST_PATH) == 0:
            writer.writerow([
                "file_name", "label", "vehicle_make_model", "engine_type",
                "rpm", "distance_cm", "sensor_location", "recorded_by", "notes"
            ])
        writer.writerow([
            target_name, label, vehicle, engine_type,
            rpm, distance, location, contributor, notes
        ])

    print(f"✓ Manifest updated: {MANIFEST_PATH}")
    print("\n🎉 Sample successfully added! Ready to commit:")
    print("   git add datasets/")
    print(f'   git commit -m "feat(datasets): add {label} sample for {vehicle}"')
    print("   git push origin main")

if __name__ == "__main__":
    main()
