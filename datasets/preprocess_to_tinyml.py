#!/usr/bin/env python3
"""
MotoPulse Dataset Preprocessor & TinyML Feature Extractor
Converts raw automotive acoustic recordings into standardized 16,000 Hz, 16-Bit Mono PCM WAV,
segments audio into 1.0s windows (16,000 samples) with 50% overlap,
extracts 32-band Log-Mel Spectrograms (49, 32, 1),
pairs with vibration RMS and spectral centroid features for Piezo contact sensing,
and exports X_features.npy, y_labels.npy, and class_names.json for ESP32-S3 TinyML deployment.
"""

import os
import sys
import csv
import json
import subprocess
import numpy as np
import soundfile as sf

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")
MANIFEST_IN = os.path.join(BASE_DIR, "dataset_manifest.csv")
MANIFEST_OUT = os.path.join(BASE_DIR, "manifests", "processed_manifest.csv")

TARGET_SAMPLE_RATE = 16000
TARGET_CHANNELS = 1
WINDOW_SECONDS = 1.0
WINDOW_SAMPLES = int(TARGET_SAMPLE_RATE * WINDOW_SECONDS)  # 16,000 samples
HOP_OVERLAP = 0.50  # 50% overlap
HOP_SAMPLES = int(WINDOW_SAMPLES * (1.0 - HOP_OVERLAP))  # 8,000 samples

FRAME_LENGTH = 480   # 30 ms at 16 kHz
FRAME_STEP = 320     # 20 ms at 16 kHz (49 frames in 16,000 samples)
N_MELS = 32          # 32 Mel filter bands
N_FFT = 512          # 512-point FFT (257 real frequency bins)
F_MIN = 40.0         # Lower frequency cutoff in Hz
F_MAX = 8000.0       # Upper frequency cutoff (Nyquist)


def build_mel_filterbank(sr=TARGET_SAMPLE_RATE, n_fft=N_FFT, n_mels=N_MELS, fmin=F_MIN, fmax=F_MAX):
    """Constructs 32 triangular Mel filterbank matrix of shape (n_mels, n_fft // 2 + 1)."""
    def hz_to_mel(hz):
        return 2595.0 * np.log10(1.0 + hz / 700.0)

    def mel_to_hz(mel):
        return 700.0 * (10.0 ** (mel / 2595.0) - 1.0)

    mel_min = hz_to_mel(fmin)
    mel_max = hz_to_mel(fmax)
    mel_points = np.linspace(mel_min, mel_max, n_mels + 2)
    hz_points = mel_to_hz(mel_points)
    bin_points = np.floor((n_fft + 1) * hz_points / sr).astype(int)

    filterbank = np.zeros((n_mels, n_fft // 2 + 1), dtype=np.float32)
    for m in range(1, n_mels + 1):
        f_left = bin_points[m - 1]
        f_center = bin_points[m]
        f_right = bin_points[m + 1]

        for k in range(f_left, f_center):
            if f_center > f_left:
                filterbank[m - 1, k] = (k - f_left) / float(f_center - f_left)
        for k in range(f_center, f_right):
            if f_right > f_center:
                filterbank[m - 1, k] = (f_right - k) / float(f_right - f_center)

    return filterbank


def extract_window_features(audio_segment, mel_fb, window_fn):
    """
    Extracts 32-band Log-Mel Spectrogram and paired vibration features from a 16,000-sample window.
    Returns:
        log_mel: (49, 32, 1) float32
        vibration_features: (49, 2) float32 [frame_rms, frame_spectral_centroid]
        summary_vibration: (2,) float32 [window_rms, mean_spectral_centroid]
    """
    assert len(audio_segment) == WINDOW_SAMPLES, f"Expected {WINDOW_SAMPLES} samples, got {len(audio_segment)}"

    # Window RMS
    win_rms = float(np.sqrt(np.mean(audio_segment ** 2)))

    # Frame slicing
    frames = np.lib.stride_tricks.sliding_window_view(audio_segment, FRAME_LENGTH)[::FRAME_STEP]
    num_frames = frames.shape[0]  # Exactly 49 frames

    # Frame RMS
    frame_rms = np.sqrt(np.mean(frames ** 2, axis=1)).astype(np.float32)

    # Windowed FFT
    windowed_frames = frames * window_fn
    stft = np.fft.rfft(windowed_frames, n=N_FFT)  # (49, 257)
    magnitude = np.abs(stft).astype(np.float32)
    power_spectrum = (magnitude ** 2) / N_FFT

    # Spectral centroid calculation
    freqs = np.fft.rfftfreq(N_FFT, 1.0 / TARGET_SAMPLE_RATE).astype(np.float32)  # (257,)
    mag_sum = np.sum(magnitude, axis=1) + 1e-9
    spectral_centroids = (np.sum(magnitude * freqs, axis=1) / mag_sum).astype(np.float32)  # (49,)
    mean_centroid = float(np.mean(spectral_centroids))

    # Log-Mel Spectrogram
    mel_energies = np.dot(power_spectrum, mel_fb.T)  # (49, 32)
    log_mel = np.log(mel_energies + 1e-6).astype(np.float32)

    # Add channel dimension: (49, 32, 1)
    log_mel_tensor = np.expand_dims(log_mel, axis=-1)

    # Vibration representation: (49, 2) per frame [RMS, Centroid normalized]
    # Normalize centroid to [0, 1] relative to Nyquist (8000 Hz)
    vibration_tensor = np.stack([frame_rms, spectral_centroids / (TARGET_SAMPLE_RATE / 2.0)], axis=-1)
    summary_vibration = np.array([win_rms, mean_centroid], dtype=np.float32)

    return log_mel_tensor, vibration_tensor, summary_vibration


def main():
    print("=" * 72)
    print("   🚗 MotoPulse TinyML Dataset Preprocessor & Feature Extraction   ")
    print("=" * 72)

    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "manifests"), exist_ok=True)

    # Read master manifest mappings
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

    print(f"[STAGE 1] Standardizing {len(raw_files)} audio files to 16,000 Hz 16-bit Mono PCM WAV...\n")

    processed_rows = []
    processed_audio_paths = []

    for f in raw_files:
        in_path = os.path.join(RAW_DIR, f)
        meta = manifest_map.get(f, {})
        label = meta.get("label", "unknown_defect")

        clean_base = os.path.splitext(f)[0]
        clean_base = clean_base.replace(" ", "_").replace("(", "").replace(")", "").replace("[", "").replace("]", "")
        if not clean_base.startswith(label):
            out_name = f"{label}_{clean_base}.wav"
        else:
            out_name = f"{clean_base}.wav"

        out_path = os.path.join(PROCESSED_DIR, out_name)

        # Standardize using ffmpeg
        cmd = [
            "ffmpeg", "-y", "-i", in_path,
            "-ac", str(TARGET_CHANNELS),
            "-ar", str(TARGET_SAMPLE_RATE),
            "-c:a", "pcm_s16le",
            out_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0:
            size_kb = os.path.getsize(out_path) / 1024.0
            dur_cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", out_path]
            dur_res = subprocess.run(dur_cmd, capture_output=True, text=True)
            dur_sec = float(dur_res.stdout.strip() or 0.0)

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
            processed_audio_paths.append((out_path, label, out_name))
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

    print(f"\n[INFO] Manifest generated: {MANIFEST_OUT} ({len(processed_rows)} entries)")

    # STAGE 2: Feature Extraction & Segmentation
    print("\n" + "=" * 72)
    print(f"[STAGE 2] Segmenting & Extracting TinyML Features (1.0s window, 50% overlap)...")
    print(f"          32-band Log-Mel Spectrogram -> (49, 32, 1)")
    print(f"          Paired Piezo Vibration -> (49, 2) [RMS, Centroid]")
    print("=" * 72)

    # Prepare Mel filterbank and window function
    mel_fb = build_mel_filterbank()
    window_fn = np.hanning(FRAME_LENGTH).astype(np.float32)

    # Class indexing
    unique_labels = sorted(list(set(item[1] for item in processed_audio_paths)))
    class_to_idx = {name: idx for idx, name in enumerate(unique_labels)}
    idx_to_class = {idx: name for idx, name in enumerate(unique_labels)}

    # Save class_names.json
    class_names_path = os.path.join(PROCESSED_DIR, "class_names.json")
    with open(class_names_path, "w", encoding="utf-8") as f:
        json.dump(idx_to_class, f, indent=2)
    print(f"[INFO] Saved class names mapping to {class_names_path}")
    print(f"[INFO] Discovered {len(unique_labels)} target classes: {', '.join(unique_labels)}\n")

    X_features_list = []
    y_labels_list = []
    X_vibration_list = []
    vibration_summary_list = []
    sample_metadata = []

    class_counts = {c: 0 for c in unique_labels}
    file_count = 0

    for path, label, name in processed_audio_paths:
        try:
            audio, sr = sf.read(path, dtype="float32")
        except Exception as e:
            print(f"  ❌ Error reading {path}: {e}")
            continue

        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)  # Ensure mono

        total_samples = len(audio)
        if total_samples < WINDOW_SAMPLES:
            # Pad short audio clips to 1.0s with zero-padding
            pad_width = WINDOW_SAMPLES - total_samples
            audio = np.pad(audio, (0, pad_width), mode="constant")
            total_samples = WINDOW_SAMPLES

        # 50% overlapping windows
        num_windows = 1 + (total_samples - WINDOW_SAMPLES) // HOP_SAMPLES
        file_count += 1

        for w_idx in range(num_windows):
            start = w_idx * HOP_SAMPLES
            end = start + WINDOW_SAMPLES
            chunk = audio[start:end]

            log_mel_tensor, vib_tensor, vib_summary = extract_window_features(chunk, mel_fb, window_fn)

            X_features_list.append(log_mel_tensor)
            y_labels_list.append(class_to_idx[label])
            X_vibration_list.append(vib_tensor)
            vibration_summary_list.append(vib_summary)
            sample_metadata.append({
                "source_file": name,
                "label": label,
                "label_idx": class_to_idx[label],
                "window_idx": w_idx,
                "start_time_sec": round(start / TARGET_SAMPLE_RATE, 3),
                "end_time_sec": round(end / TARGET_SAMPLE_RATE, 3)
            })
            class_counts[label] += 1

    # Convert to numpy arrays
    X_features = np.array(X_features_list, dtype=np.float32)
    y_labels = np.array(y_labels_list, dtype=np.int64)
    X_vibration = np.array(X_vibration_list, dtype=np.float32)
    vibration_summary = np.array(vibration_summary_list, dtype=np.float32)

    # Save outputs
    x_features_path = os.path.join(PROCESSED_DIR, "X_features.npy")
    y_labels_path = os.path.join(PROCESSED_DIR, "y_labels.npy")
    x_vibration_path = os.path.join(PROCESSED_DIR, "X_vibration.npy")
    vib_summary_path = os.path.join(PROCESSED_DIR, "vibration_summary.npy")

    np.save(x_features_path, X_features)
    np.save(y_labels_path, y_labels)
    np.save(x_vibration_path, X_vibration)
    np.save(vib_summary_path, vibration_summary)

    # Save comprehensive summary json
    summary_data = {
        "total_audio_files": len(processed_audio_paths),
        "total_windows": len(y_labels),
        "sample_rate_hz": TARGET_SAMPLE_RATE,
        "window_duration_sec": WINDOW_SECONDS,
        "overlap_percentage": HOP_OVERLAP * 100,
        "feature_shapes": {
            "X_features": list(X_features.shape),
            "y_labels": list(y_labels.shape),
            "X_vibration": list(X_vibration.shape),
            "vibration_summary": list(vibration_summary.shape)
        },
        "classes": unique_labels,
        "num_classes": len(unique_labels),
        "class_distribution_windows": class_counts
    }

    # Core-8 standardized subset (as highlighted in Hacktivate specifications)
    core_classes = [
        "normal_idle",
        "engine_knocking",
        "bearing_wear",
        "valve_ticking",
        "belt_slippage",
        "exhaust_leak",
        "misfire",
        "turbo_flutter"
    ]
    core_class_to_idx = {c: i for i, c in enumerate(core_classes)}
    core_idx_to_class = {i: c for i, c in enumerate(core_classes)}

    mask_core = [idx_to_class[y] in core_class_to_idx for y in y_labels]
    mask_core = np.array(mask_core)
    X_core = X_features[mask_core]
    vib_core = X_vibration[mask_core]
    y_core = np.array([core_class_to_idx[idx_to_class[y]] for y in y_labels[mask_core]], dtype=np.int64)

    # Save Core-8 files
    np.save(os.path.join(PROCESSED_DIR, "X_features_core8.npy"), X_core)
    np.save(os.path.join(PROCESSED_DIR, "y_labels_core8.npy"), y_core)
    np.save(os.path.join(PROCESSED_DIR, "X_vibration_core8.npy"), vib_core)
    with open(os.path.join(PROCESSED_DIR, "class_names_core8.json"), "w", encoding="utf-8") as f:
        json.dump(core_idx_to_class, f, indent=2)

    summary_data["core8"] = {
        "classes": core_classes,
        "num_classes": len(core_classes),
        "total_windows": len(y_core),
        "feature_shape": list(X_core.shape)
    }

    summary_json_path = os.path.join(PROCESSED_DIR, "dataset_summary.json")
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    print("\n" + "=" * 72)
    print("                     🎉 DATASET PROCESSING SUMMARY")
    print("=" * 72)
    print(f" Total Audio Clips Processed : {len(processed_audio_paths)}")
    print(f" Total 1.0s Window Samples   : {X_features.shape[0]}")
    print(f" X_features Tensor Shape     : {X_features.shape}  (Log-Mel: Time, Mels, Channel)")
    print(f" y_labels Tensor Shape       : {y_labels.shape}  (Discrete integer class IDs)")
    print(f" X_vibration Tensor Shape    : {X_vibration.shape}  (Piezo: Time, [RMS, Centroid])")
    print(f" Core-8 Subset Tensor Shape  : {X_core.shape}  (8 Standard Automotive Faults)")
    print(f" Number of Target Classes    : {len(unique_labels)}")
    print("-" * 72)
    print(f" {'Class Label':<28} | {'Window Samples':<15} | {'Percentage':<10}")
    print("-" * 72)
    for c in unique_labels:
        cnt = class_counts[c]
        pct = (cnt / len(y_labels)) * 100.0
        print(f" {c:<28} | {cnt:<15} | {pct:6.2f}%")
    print("-" * 72)
    print(f" Files Created in {PROCESSED_DIR}:")
    print(f"   ✔ X_features.npy          ({os.path.getsize(x_features_path) / (1024*1024):.2f} MB)")
    print(f"   ✔ y_labels.npy            ({os.path.getsize(y_labels_path) / 1024:.2f} KB)")
    print(f"   ✔ X_vibration.npy         ({os.path.getsize(x_vibration_path) / (1024*1024):.2f} MB)")
    print(f"   ✔ X_features_core8.npy    ({os.path.getsize(os.path.join(PROCESSED_DIR, 'X_features_core8.npy')) / (1024*1024):.2f} MB)")
    print(f"   ✔ y_labels_core8.npy      ({os.path.getsize(os.path.join(PROCESSED_DIR, 'y_labels_core8.npy')) / 1024:.2f} KB)")
    print(f"   ✔ class_names.json        ({os.path.getsize(class_names_path)} bytes)")
    print(f"   ✔ class_names_core8.json  ({os.path.getsize(os.path.join(PROCESSED_DIR, 'class_names_core8.json'))} bytes)")
    print(f"   ✔ dataset_summary.json    ({os.path.getsize(summary_json_path)} bytes)")
    print("=" * 72)


if __name__ == "__main__":
    main()
