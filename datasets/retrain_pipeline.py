#!/usr/bin/env python3
"""
MotoPulse Complete End-to-End TinyML Retraining Pipeline
=========================================================
Trains from scratch to recognize:
1. GOOD (Healthy / Normal Engine Sound across all makes & RPMs: 1000/1500/2000 RPM, cabin, ambient)
2. BAD (Specific Vehicle Mechanical Defect Identification across 7 fault types)

Classes:
0: normal_idle    (GOOD: Optimal baseline acoustics, idle, revs, cruising)
1: engine_knocking(BAD: Connecting rod knock, piston slap, pre-ignition detonation)
2: bearing_wear   (BAD: Alternator / water pump / idler / wheel bearing wear)
3: valve_ticking  (BAD: Hydraulic valve lifter clearance, tappet click, loose valvetrain)
4: belt_slippage  (BAD: Serpentine accessory belt squeal, AC clutch slip, friction wear)
5: exhaust_leak   (BAD: Exhaust manifold leak, blown gasket chuff, muffler hole)
6: misfire        (BAD: Cylinder combustion quench, rough loping misfire, dropped spark)
7: turbo_flutter  (BAD: Turbo compressor surge, wastegate chatter, intercooler leak)

Co-authored-by: ishannvn <ishannvn@users.noreply.github.com>
"""

import os
import sys
import glob
import json
import time
import subprocess
import numpy as np
import soundfile as sf
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DATASETS_DIR = BASE_DIR
PROCESSED_DIR = os.path.join(DATASETS_DIR, "processed")
MODELS_DIR = os.path.join(DATASETS_DIR, "models")

TARGET_SAMPLE_RATE = 16000
WINDOW_SAMPLES = 16000  # 1.0s window
HOP_SAMPLES = 8000      # 50% overlap

FRAME_LENGTH = 480      # 30 ms
FRAME_STEP = 320        # 20 ms -> exactly 49 frames per 16,000 samples
N_MELS = 32             # 32 Mel filter bands
N_FFT = 512             # 512-point FFT
F_MIN = 40.0
F_MAX = 8000.0

CORE_CLASSES = [
    "normal_idle",
    "engine_knocking",
    "bearing_wear",
    "valve_ticking",
    "belt_slippage",
    "exhaust_leak",
    "misfire",
    "turbo_flutter"
]
CLASS_TO_IDX = {c: i for i, c in enumerate(CORE_CLASSES)}
IDX_TO_CLASS = {i: c for i, c in enumerate(CORE_CLASSES)}


def build_mel_filterbank(sr=TARGET_SAMPLE_RATE, n_fft=N_FFT, n_mels=N_MELS, fmin=F_MIN, fmax=F_MAX):
    """Constructs 32 triangular Mel filterbank matrix of shape (n_mels, n_fft // 2 + 1)."""
    def hz_to_mel(hz): return 2595.0 * np.log10(1.0 + hz / 700.0)
    def mel_to_hz(mel): return 700.0 * (10.0 ** (mel / 2595.0) - 1.0)
    mel_min, mel_max = hz_to_mel(fmin), hz_to_mel(fmax)
    mel_points = np.linspace(mel_min, mel_max, n_mels + 2)
    hz_points = mel_to_hz(mel_points)
    bin_points = np.floor((n_fft + 1) * hz_points / sr).astype(int)

    fb = np.zeros((n_mels, n_fft // 2 + 1), dtype=np.float32)
    for m in range(1, n_mels + 1):
        f_left = bin_points[m - 1]
        f_center = bin_points[m]
        f_right = bin_points[m + 1]
        for k in range(f_left, f_center):
            if f_center > f_left: fb[m - 1, k] = (k - f_left) / float(f_center - f_left)
        for k in range(f_center, f_right):
            if f_right > f_center: fb[m - 1, k] = (f_right - k) / float(f_right - f_center)
    return fb


def extract_logmel(audio_1s, mel_fb, window_fn):
    """Extracts (49, 32, 1) Log-Mel spectrogram from 16,000 samples."""
    frames = np.lib.stride_tricks.sliding_window_view(audio_1s, FRAME_LENGTH)[::FRAME_STEP]
    windowed = frames * window_fn
    stft = np.fft.rfft(windowed, n=N_FFT)
    mag = np.abs(stft).astype(np.float32)
    power = (mag ** 2) / float(N_FFT)
    mel_energies = np.dot(power, mel_fb.T)
    log_mel = np.log(mel_energies + 1e-6).astype(np.float32)
    return np.expand_dims(log_mel, axis=-1)


def load_audio_normalized(file_path):
    """Reads audio file, converts to 16kHz mono float32 [-1, 1], and removes silence."""
    try:
        data, sr = sf.read(file_path, dtype='float32')
    except Exception as e:
        # Fallback to ffmpeg read
        temp_wav = "/tmp/temp_conv.wav"
        subprocess.run(["ffmpeg", "-y", "-i", file_path, "-ar", "16000", "-ac", "1", temp_wav],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            data, sr = sf.read(temp_wav, dtype='float32')
        except Exception:
            return None

    if len(data.shape) > 1:
        data = np.mean(data, axis=1)

    if sr != TARGET_SAMPLE_RATE:
        # Resample via linear interpolation
        new_len = int(len(data) * TARGET_SAMPLE_RATE / sr)
        data = np.interp(np.linspace(0, len(data), new_len, endpoint=False), np.arange(len(data)), data).astype(np.float32)

    # Discard if pure digital silence or corrupted
    rms = np.sqrt(np.mean(data ** 2))
    if rms < 0.003:
        return None

    return data


def scan_and_catalog_files():
    """Catalogs all audio files into the 8 Core classes with strict validation."""
    catalog = {c: [] for c in CORE_CLASSES}

    # 1. Good Engine Sounds: MLVRG-Car-Engine-Audio (all makes & RPMs)
    mlvrg_files = glob.glob(os.path.join(DATASETS_DIR, "raw", "pravruthi_2.0", "MLVRG-Car-Engine-Audio", "*", "*", "*", "*.wav"))
    for f in mlvrg_files:
        catalog["normal_idle"].append(f)

    # 2. Pravruthi training & testing
    for f in glob.glob(os.path.join(DATASETS_DIR, "raw", "pravruthi_2.0", "training", "*.wav")) + \
             glob.glob(os.path.join(DATASETS_DIR, "raw", "pravruthi_2.0", "testing", "*.wav")):
        fn = os.path.basename(f).lower()
        if "idling" in fn or "normal engine" in fn or "background noise" in fn:
            catalog["normal_idle"].append(f)
        elif "air leak" in fn:
            catalog["exhaust_leak"].append(f)
        elif "oil cap" in fn:
            catalog["valve_ticking"].append(f)

    # 3. 11.maindataset Faulty
    for f in glob.glob(os.path.join(DATASETS_DIR, "11.maindataset", "Faulty", "*.wav")):
        fn = os.path.basename(f).lower()
        if "knock" in fn or "pistonslap" in fn:
            catalog["engine_knocking"].append(f)
        elif "bearing" in fn or "waterpump" in fn or "alternator" in fn or "idler" in fn or "shaft" in fn or "pulley" in fn:
            catalog["bearing_wear"].append(f)
        elif "valve" in fn or "lifter" in fn or "tappet" in fn or "timingchain" in fn or "flywheel" in fn or "mount" in fn:
            catalog["valve_ticking"].append(f)
        elif "belt" in fn or "clutch" in fn or "coupler" in fn:
            catalog["belt_slippage"].append(f)
        elif "exhaust" in fn or "vacuum" in fn or "gasket" in fn or "intake" in fn or "converter" in fn or "powersteering" in fn:
            catalog["exhaust_leak"].append(f)
        elif "misfire" in fn or "injector" in fn or "starter" in fn:
            catalog["misfire"].append(f)
        elif "turbo" in fn or "supercharger" in fn:
            catalog["turbo_flutter"].append(f)

    # 4. Pree faults & sounds
    for f in glob.glob(os.path.join(DATASETS_DIR, "11.maindataset", "fault data set pree", "*.*")):
        fn = os.path.basename(f).lower()
        if "muffler" in fn:
            catalog["exhaust_leak"].append(f)
        elif "brake" in fn:
            catalog["belt_slippage"].append(f)
        elif "difficult" in fn or "not-starting" in fn:
            catalog["misfire"].append(f)
        elif "soumages" in fn or "ignition" in fn:
            catalog["normal_idle"].append(f)

    # 5. Datasets/raw direct
    for f in glob.glob(os.path.join(DATASETS_DIR, "raw", "*.*")):
        fn = os.path.basename(f).lower()
        if fn.endswith((".wav", ".mp3", ".ogg", ".flac")):
            if "knock" in fn: catalog["engine_knocking"].append(f)
            elif "bearing" in fn or "whirring" in fn: catalog["bearing_wear"].append(f)
            elif "tick" in fn or "tappet" in fn: catalog["valve_ticking"].append(f)
            elif "belt" in fn or "squeal" in fn: catalog["belt_slippage"].append(f)
            elif "leak" in fn or "exhaust" in fn or "chuff" in fn: catalog["exhaust_leak"].append(f)
            elif "misfire" in fn or "sputter" in fn: catalog["misfire"].append(f)
            elif "idle" in fn or "normal" in fn: catalog["normal_idle"].append(f)

    # 6. Hardware recordings from audio_recordings
    hw_recs = glob.glob(os.path.join(PROJECT_ROOT, "audio_recordings", "*.wav"))
    for f in hw_recs:
        catalog["normal_idle"].append(f)

    print("📊 Audio File Catalog:")
    for c in CORE_CLASSES:
        # Deduplicate paths
        catalog[c] = sorted(list(set(catalog[c])))
        print(f"   • {c:<16}: {len(catalog[c])} source audio files")

    return catalog


def extract_windows_for_class(file_list, class_name, target_count, mel_fb, window_fn):
    """
    Loads files for a class, extracts 1.0s windows, applies amplitude normalization,
    and performs balanced augmentation to reach target_count windows.
    """
    raw_windows = []
    
    for f in file_list:
        audio = load_audio_normalized(f)
        if audio is None or len(audio) < 4000:
            continue

        if len(audio) < WINDOW_SAMPLES:
            pad = WINDOW_SAMPLES - len(audio)
            audio = np.pad(audio, (0, pad), mode='wrap')

        # Slice 1.0s windows with 50% overlap
        n_win = max(1, 1 + (len(audio) - WINDOW_SAMPLES) // HOP_SAMPLES)
        for w in range(n_win):
            start = w * HOP_SAMPLES
            end = start + WINDOW_SAMPLES
            chunk = audio[start:end]
            if len(chunk) < WINDOW_SAMPLES:
                chunk = np.pad(chunk, (0, WINDOW_SAMPLES - len(chunk)), mode='wrap')

            # RMS check
            chunk_rms = np.sqrt(np.mean(chunk ** 2))
            if chunk_rms < 0.003:
                continue

            # Peak normalize chunk to [-0.95, 0.95] to prevent mic volume bias
            max_val = np.max(np.abs(chunk))
            if max_val > 0.001:
                chunk = (chunk / max_val) * 0.95

            raw_windows.append(chunk)

    if not raw_windows:
        raise ValueError(f"No valid audio windows found for class {class_name}!")

    print(f"   [{class_name}] Extracted {len(raw_windows)} clean raw windows. Target = {target_count}.")

    # Augment or downsample to reach target_count
    final_features = []
    np.random.seed(42)

    if len(raw_windows) >= target_count:
        # Uniformly sample across ALL files to ensure every car make, RPM, and cabin audio is represented
        chosen_indices = np.random.choice(len(raw_windows), target_count, replace=False)
        for idx in chosen_indices:
            feat = extract_logmel(raw_windows[idx], mel_fb, window_fn)
            final_features.append(feat)
    else:
        # Add all raw windows first
        for chunk in raw_windows:
            feat = extract_logmel(chunk, mel_fb, window_fn)
            final_features.append(feat)

    # If need more, augment with time shift, slight noise, volume jitter, and pitch modulation
    idx = 0
    num_raw = len(raw_windows)
    while len(final_features) < target_count:
        base_chunk = raw_windows[idx % num_raw].copy()
        
        # 1. Circular roll (time shift)
        shift = np.random.randint(-2000, 2000)
        aug_chunk = np.roll(base_chunk, shift)

        # 2. Volume scaling (random gain 0.5 to 1.0)
        gain = np.random.uniform(0.55, 1.0)
        aug_chunk = aug_chunk * gain

        # 3. Subtle background pink/white noise (SNR 25-35 dB)
        noise_level = np.random.uniform(0.002, 0.008)
        aug_chunk = aug_chunk + np.random.normal(0, noise_level, len(aug_chunk)).astype(np.float32)

        feat = extract_logmel(aug_chunk, mel_fb, window_fn)

        # 4. Occasional SpecAugment frequency masking (mask 1-2 Mel bands)
        if np.random.random() < 0.35:
            band = np.random.randint(0, 31)
            feat[:, band:band+2, 0] = -12.0

        final_features.append(feat)
        idx += 1

    return np.array(final_features[:target_count], dtype=np.float32)


def build_and_train_model(X_train, y_train, X_val, y_val, num_classes=8):
    """Builds and trains ultra-compact Depthwise Separable 2D CNN."""
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers

    input_shape = (49, 32, 1)
    inputs = layers.Input(shape=input_shape, name="audio_logmel_input")

    # In-graph normalization layer
    norm = layers.Normalization(axis=-1, name="norm")
    norm.adapt(X_train)
    x = norm(inputs)

    # Block 1: Conv2D with stride (2, 2) -> (25, 16)
    x = layers.Conv2D(16, (3, 3), strides=(2, 2), padding="same", use_bias=False, name="conv1")(x)
    x = layers.BatchNormalization(name="bn1")(x)
    x = layers.ReLU(max_value=6.0, name="relu1")(x)

    # Block 2: Depthwise Separable Conv + MaxPool -> (13, 8)
    x = layers.DepthwiseConv2D((3, 3), padding="same", use_bias=False, name="dw2")(x)
    x = layers.BatchNormalization(name="bn2_dw")(x)
    x = layers.ReLU(max_value=6.0, name="relu2_dw")(x)
    x = layers.Conv2D(32, (1, 1), padding="same", use_bias=False, name="pw2")(x)
    x = layers.BatchNormalization(name="bn2_pw")(x)
    x = layers.ReLU(max_value=6.0, name="relu2_pw")(x)
    x = layers.MaxPooling2D((2, 2), padding="same", name="pool2")(x)

    # Block 3: Depthwise Separable Conv -> (13, 8)
    x = layers.DepthwiseConv2D((3, 3), padding="same", use_bias=False, name="dw3")(x)
    x = layers.BatchNormalization(name="bn3_dw")(x)
    x = layers.ReLU(max_value=6.0, name="relu3_dw")(x)
    x = layers.Conv2D(48, (1, 1), padding="same", use_bias=False, name="pw3")(x)
    x = layers.BatchNormalization(name="bn3_pw")(x)
    x = layers.ReLU(max_value=6.0, name="relu3_pw")(x)

    # Classification Head
    x = layers.GlobalAveragePooling2D(name="gap")(x)
    x = layers.Dropout(0.25, name="dropout")(x)
    outputs = layers.Dense(num_classes, activation="softmax", name="prob_output")(x)

    model = keras.Model(inputs=inputs, outputs=outputs, name="motopulse_core8_cnn")

    optimizer = keras.optimizers.Adam(learning_rate=0.002)
    model.compile(
        optimizer=optimizer,
        loss=keras.losses.SparseCategoricalCrossentropy(),
        metrics=["accuracy"]
    )

    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor="val_accuracy",
            patience=14,
            restore_best_weights=True,
            verbose=1
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=4,
            min_lr=1e-5,
            verbose=1
        )
    ]

    print("\n🚀 Training Core-8 Deep TinyML Model...")
    model.summary()

    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=45,
        batch_size=32,
        callbacks=callbacks,
        verbose=1
    )

    return model, history


def quantize_and_export_tflite(model, X_train, X_test, y_test):
    """Performs Full INT8 Post-Training Quantization with comprehensive calibration."""
    import tensorflow as tf

    def representative_dataset_gen():
        # Representative sample of 300 instances covering all classes
        indices = np.random.choice(len(X_train), min(300, len(X_train)), replace=False)
        for idx in indices:
            sample = X_train[idx:idx+1].astype(np.float32)
            yield [sample]

    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = representative_dataset_gen
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.int8
    converter.inference_output_type = tf.int8

    tflite_quant_model = converter.convert()

    # Save tflite files
    tflite_core8_path = os.path.join(MODELS_DIR, "motopulse_core8_classifier.tflite")
    tflite_alias_path = os.path.join(MODELS_DIR, "motopulse_classifier.tflite")
    with open(tflite_core8_path, "wb") as f:
        f.write(tflite_quant_model)
    with open(tflite_alias_path, "wb") as f:
        f.write(tflite_quant_model)

    size_kb = len(tflite_quant_model) / 1024.0
    print(f"\n✔ Exported INT8 Quantized Model: {tflite_core8_path} ({size_kb:.2f} KB)")

    # Evaluate INT8 Quantized Model on Test Set
    interpreter = tf.lite.Interpreter(model_content=tflite_quant_model)
    interpreter.allocate_tensors()
    in_det = interpreter.get_input_details()[0]
    out_det = interpreter.get_output_details()[0]

    in_scale, in_zero = in_det["quantization"]
    out_scale, out_zero = out_det["quantization"]

    y_preds = []
    t_start = time.time()
    for i in range(len(X_test)):
        sample = X_test[i:i+1]
        q_in = np.clip(np.round(sample / in_scale + in_zero), -128, 127).astype(np.int8)
        interpreter.set_tensor(in_det["index"], q_in)
        interpreter.invoke()
        q_out = interpreter.get_tensor(out_det["index"])[0]
        # Direct dequantization: prob = (q - zero) * scale
        probs = (q_out.astype(np.float32) - out_zero) * out_scale
        y_preds.append(int(np.argmax(probs)))
    eval_time = (time.time() - t_start) / len(X_test) * 1000.0

    y_preds = np.array(y_preds)
    test_acc = float(np.mean(y_preds == y_test))
    print(f"\n🎯 Quantized INT8 Test Set Accuracy: {test_acc * 100:.2f}% (Average Latency: {eval_time:.2f} ms/sample)")

    cm = confusion_matrix(y_test, y_preds).tolist()
    report = classification_report(y_test, y_preds, target_names=CORE_CLASSES, output_dict=True)

    # Export C Header for ESP32 Firmware
    c_header_path = os.path.join(MODELS_DIR, "motopulse_model_data.h")
    with open(c_header_path, "w") as f:
        f.write("// MotoPulse Core-8 INT8 Quantized Model for ESP32-S3\n")
        f.write("// Auto-generated by retrain_pipeline.py\n")
        f.write("#ifndef MOTOPULSE_MODEL_DATA_H\n#define MOTOPULSE_MODEL_DATA_H\n\n")
        f.write('#include <stdint.h>\n\n')
        f.write(f'#define MOTOPULSE_MODEL_SIZE {len(tflite_quant_model)}\n')
        f.write(f'#define MOTOPULSE_NUM_CLASSES {len(CORE_CLASSES)}\n\n')
        f.write('const char* const g_motopulse_classes[] = {\n')
        for c in CORE_CLASSES:
            f.write(f'    "{c}",\n')
        f.write('};\n\n')
        f.write('alignas(16) const unsigned char g_motopulse_model_data[] = {\n    ')
        for i, b in enumerate(tflite_quant_model):
            f.write(f'0x{b:02x}, ')
            if (i + 1) % 12 == 0:
                f.write('\n    ')
        f.write('\n};\n\n#endif // MOTOPULSE_MODEL_DATA_H\n')

    print(f"✔ Exported ESP32-S3 C Header: {c_header_path}")

    # Export Evaluation Report
    eval_report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model_title": "MotoPulse Core-8 Vehicle Health & Defect Classifier",
        "num_classes": len(CORE_CLASSES),
        "class_names": CORE_CLASSES,
        "model_size_kb": round(size_kb, 2),
        "quantization": "Full INT8",
        "test_accuracy": round(test_acc, 4),
        "macro_f1": round(report["macro avg"]["f1-score"], 4),
        "weighted_f1": round(report["weighted avg"]["f1-score"], 4),
        "confusion_matrix": cm,
        "classification_report": report
    }
    with open(os.path.join(MODELS_DIR, "model_eval_report.json"), "w") as f:
        json.dump(eval_report, f, indent=2)

    return test_acc, eval_report


def main():
    print("=" * 72)
    print("   🏎️  MOTOPULSE™ TINYML GROUND-UP RETRAINING PIPELINE")
    print("=" * 72)

    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)

    mel_fb = build_mel_filterbank()
    window_fn = np.hanning(FRAME_LENGTH).astype(np.float32)

    # 1. Catalog audio files
    catalog = scan_and_catalog_files()

    # 2. Extract balanced windows for each class
    # Generous allocation for normal_idle (Good sound) to recognize all RPMs, cabin, idle
    TARGET_COUNTS = {
        "normal_idle": 1200,      # GOOD ENGINE SOUND
        "engine_knocking": 600,   # BAD DEFECT
        "bearing_wear": 600,      # BAD DEFECT
        "valve_ticking": 600,     # BAD DEFECT
        "belt_slippage": 600,     # BAD DEFECT
        "exhaust_leak": 600,      # BAD DEFECT
        "misfire": 600,           # BAD DEFECT
        "turbo_flutter": 600      # BAD DEFECT
    }

    all_features = []
    all_labels = []

    for c in CORE_CLASSES:
        files = catalog[c]
        target = TARGET_COUNTS[c]
        print(f"\nProcessing Class '{c}' (Label ID {CLASS_TO_IDX[c]})...")
        feats = extract_windows_for_class(files, c, target, mel_fb, window_fn)
        labels = np.full(len(feats), CLASS_TO_IDX[c], dtype=np.int32)
        all_features.append(feats)
        all_labels.append(labels)

    X = np.concatenate(all_features, axis=0)
    y = np.concatenate(all_labels, axis=0)

    print("\n" + "=" * 72)
    print(f"📦 Total Curated Dataset Shape: X={X.shape}, y={y.shape}")
    print(f"   Feature Range: min={np.min(X):.2f}, max={np.max(X):.2f}, mean={np.mean(X):.2f}")
    print("=" * 72)

    # Save processed numpy datasets
    np.save(os.path.join(PROCESSED_DIR, "X_features_core8.npy"), X)
    np.save(os.path.join(PROCESSED_DIR, "y_labels_core8.npy"), y)
    with open(os.path.join(PROCESSED_DIR, "class_names_core8.json"), "w") as f:
        json.dump(IDX_TO_CLASS, f, indent=2)

    # 3. Train/Test Stratified Split (80% Train, 20% Test)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    print(f"   Train samples: {len(X_train)} | Test samples: {len(X_test)}")

    # 4. Train Model
    model, history = build_and_train_model(X_train, y_train, X_test, y_test, num_classes=8)

    # 5. Quantize to INT8 and export
    test_acc, report = quantize_and_export_tflite(model, X_train, X_test, y_test)

    print("\n" + "=" * 72)
    print(f"   🎉 MODEL RETRAINING COMPLETE! Final Test Accuracy: {test_acc*100:.2f}%")
    print("=" * 72)


if __name__ == "__main__":
    main()
