# 🚗🔊 MotoPulse Automotive Acoustic Datasets

Welcome to the **MotoPulse Acoustic Data Hub**! This directory is the collaborative repository for automotive acoustic recordings collected by the team for training and evaluating Edge AI predictive maintenance models.

---

## 👥 Authors & Maintainers
- **Visweshwara S** ([@visweshvaras](https://github.com/visweshvaras))
- **Ishan** ([@ishannvn](https://github.com/ishannvn)) — *Co-Author & Core Contributor*

---

## 📂 Directory Structure

```
datasets/
├── README.md                  # This dataset guide & contribution documentation
├── dataset_manifest.csv       # Master metadata index for all uploaded audio samples
├── upload_dataset.py          # Interactive CLI helper for uploading & annotating recordings
├── raw/                       # Raw 16 kHz 16-bit PCM WAV audio recordings
│   └── .gitkeep
├── processed/                 # Spectrograms, FFT bins & normalized feature tensors
│   └── .gitkeep
└── manifests/                 # Sub-dataset manifests, train/test splits & labels
    └── .gitkeep
```

---

## 🎯 Target Acoustic Defect Classes

When recording car audio samples, categorize them under one of the standard failure classes:

| Class Label | Description | Common Causes | Typical Frequency Range |
|:---|:---|:---|:---|
| `normal_idle` | Baseline engine operating sound | Balanced combustion, smooth idle | Broad low-frequency rumble (<500 Hz) |
| `engine_knocking` | Sharp metallic clatter or pinging | Detonation, rod bearing clearance, pre-ignition | Sharp transients (2 kHz – 6 kHz) |
| `bearing_wear` | Continuous rhythmic rumbling/grinding | Wheel hub, water pump, or alternator bearing pitting | Mid-frequency roar (500 Hz – 2.5 kHz) |
| `valve_ticking` | Fast repetitive tapping synced with RPM | Loose tappets, hydraulic lifter bleed-down | High-frequency clicks (1 kHz – 5 kHz) |
| `belt_slippage` | High-pitched squeal or chirping | Serpentine / alternator belt glaze, loose tensioner | High-frequency screech (3 kHz – 8 kHz) |
| `exhaust_leak` | Chuffing, sputtering, or ticking puff | Manifold gasket leak, cracked header pipe | Low-to-mid rhythmic puffs (200 Hz – 1.5 kHz) |
| `alternator_whine` | Pitch-varying whine tracking engine RPM | Rectifier diode fault, stator winding issue | Pure tone tracking RPM (1 kHz – 4 kHz) |

---

## 🎙️ Recording Standards

To ensure dataset uniformity across all teammates:
1. **Audio Format:** Linear PCM WAV (`.wav`), 16-bit Uncompressed.
2. **Sample Rate:** **16,000 Hz (16 kHz)** (matches the native INMP441 MEMS DMA sampling rate).
3. **Channels:** 
   - **Mono (1 Channel):** Primary microphone recording.
   - **Stereo (2 Channels):** Dual-mic spatial beamforming / near-field perimeter recording (Left: Mic 1, Right: Mic 2).
4. **Duration:** 3 to 10 seconds per sample clip.
5. **Distance & Sensor Placement:** Note the physical distance (e.g. 10 cm, 30 cm, 50 cm) and location (Engine Hood, Alternator, Wheel Well, Exhaust Tip).

---

## 📝 Master Manifest Format (`dataset_manifest.csv`)

Every recorded clip must be logged in `dataset_manifest.csv` with the following columns:

```csv
file_name,label,vehicle_make_model,engine_type,rpm,distance_cm,sensor_location,recorded_by,notes
knocking_honda_city_001.wav,engine_knocking,Honda City 1.5 i-VTEC,Petrol,1200,30,Engine Block Top,Ishan,Cold start rod knock
bearing_swift_diesel_002.wav,bearing_wear,Maruti Swift DDiS,Diesel,850,20,Alternator Belt Pulley,Visweshwara,Worn tensioner bearing
idle_hyundai_i20_003.wav,normal_idle,Hyundai i20 1.2,Petrol,780,50,Closed Hood Center,Ishan,Healthy engine baseline
```

---

## 🚀 How to Add & Upload Your Recordings

### Option A: Using the Interactive Upload Script (Recommended)
Run the built-in dataset helper to import audio and update metadata automatically:
```bash
python3 datasets/upload_dataset.py --file /path/to/my_recording.wav
```
The script will prompt you for:
- Defect label (select from menu)
- Vehicle make & model (e.g., Maruti Swift, Tata Nexon, Honda City)
- Estimated engine RPM
- Microphone distance (in cm)
- Contributor name (e.g., Ishan, Visweshwara)

It will validate the sample rate (16 kHz), copy the file into `datasets/raw/`, and append the entry into `dataset_manifest.csv`.

### Option B: Manual Upload via Git
1. Copy your `.wav` file into `datasets/raw/` with a descriptive filename:
   ```bash
   cp /path/to/recording.wav datasets/raw/<class>_<vehicle>_<number>.wav
   ```
2. Open `datasets/dataset_manifest.csv` and add a new row with the metadata.
3. Commit and push:
   ```bash
   git add datasets/
   git commit -m "feat(datasets): add <class> recording for <vehicle>"
   git push origin main
   ```
