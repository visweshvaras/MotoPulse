# 🚗🔊 MotoPulse: Automotive Acoustic Predictive Maintenance & Edge AI System

An Edge AI acoustic monitoring system powered by the **ESP32-S3 (N16R8)**, **INMP441 Digital I2S MEMS Microphone**, and a **0.96" SSD1306 OLED Display**.

Built for automotive failure prediction (engine knocking, bearing wear, valve ticking, belt slippage) and industrial machinery health monitoring.

---

## 🌟 Key Features

1. **Digital Audio Acquisition (INMP441 I2S):**
   - High-fidelity 16 kHz 16-bit PCM digital streaming via native ESP32-S3 I2S interface.
   - Eliminates analog breadboard noise, split-rail saturation, and component tolerances.
2. **16-Band Real-Time OLED Spectrum Analyzer:**
   - On-device 64-point Integer Discrete Fourier Transform (DFT) with trigonometric LUT.
   - Real-time animated 16-bar graphic equalizer with peak-hold dot falloff rendered at ~30+ FPS on a 128x64 I2C OLED.
3. **50cm Near-Field Acoustic Perimeter Gate:**
   - Single-microphone spatial discrimination utilizing the Acoustic Inverse Square Law ($I \propto 1/r^2$).
   - Rejects ambient room noise / far-field sounds (>50 cm) while accurately triggering on near-field acoustic events (<50 cm).
4. **Hardware KiCad PCB Designs:**
   - Complete KiCad schematics, PCB layout, Gerber outputs, BOM, and wiring diagrams for a custom modular pre-amplifier / breakout board.
5. **Market Research & Business Case:**
   - Comprehensive market validation report on automotive maintenance compliance and the predictive AI opportunity in India.

---

## 📐 Hardware Wiring

### 1. INMP441 Digital Microphone -> ESP32-S3 (I2S Interface)
| INMP441 Pin | ESP32-S3 Pin | Function |
| :--- | :--- | :--- |
| **VDD** | **3V3** | 3.3V Power Supply |
| **GND** | **GND** | Common Ground |
| **L/R** | **GND** | Left Channel Select |
| **SCK** | **GPIO 4** | I2S Continuous Serial Clock (BCLK) |
| **WS** | **GPIO 5** | I2S Word Select / Frame Sync (LRCLK) |
| **SD** | **GPIO 6** | I2S Serial Data Output |

### 2. 0.96" SSD1306 OLED Display -> ESP32-S3 (I2C Interface)
| OLED Pin | ESP32-S3 Pin | Function |
| :--- | :--- | :--- |
| **VCC** | **3V3** | 3.3V Power Supply |
| **GND** | **GND** | Common Ground |
| **SCL** | **GPIO 8** | I2C Clock (400 kHz) |
| **SDA** | **GPIO 9** | I2C Data |

---

## 🚀 Quick Start Guide

### 1. Requirements
- Linux / macOS / Windows with Python 3.8+
- Python packages:
  ```bash
  pip install pyserial numpy
  ```
- Optional (for MP3 conversion): `ffmpeg`

### 2. Launching the Interactive Control Panel
Connect the ESP32-S3 via USB and run:
```bash
./mic_test/run_test.sh
```

You can choose any of the options:
- **`1` - Live Volume Meter:** Real-time terminal VU visualizer.
- **`2` - Live OLED Spectrum Analyzer:** 16-band animated frequency visualizer running live on the OLED.
- **`3` - 50cm Near-Field Perimeter Demo:** Demonstrates spatial acoustic gating (<50 cm acceptance, >50 cm rejection).
- **`4` - Record Audio Clip:** Captures 3-second pristine digital audio to WAV and MP3.
- **`5` - Open Recordings Folder:** View saved audio samples in file manager.
- **`6` - Play Latest Recording:** Plays the last captured audio clip.

---

## 📂 Repository Structure

```
├── datasets/                        # Car Acoustic Dataset Hub
│   ├── README.md                    # Dataset specifications & annotation guide
│   ├── dataset_manifest.csv         # Master metadata manifest of all recorded samples
│   ├── upload_dataset.py            # CLI helper to ingest & label new audio samples
│   ├── raw/                         # Raw 16 kHz 16-bit PCM WAV recordings
│   ├── processed/                   # Extracted FFT features & spectrogram tensors
│   └── manifests/                   # Train/validation/test splits
├── motopulse_kicad/                 # KiCad 10 Hardware Design Package
│   ├── motopulse.kicad_sch          # Schematic (0 ERC Errors)
│   ├── motopulse.kicad_pcb          # PCB Layout (0 DRC Errors, 0 Unconnected)
│   ├── motopulse_schematic.pdf      # Vector Schematic PDF
│   ├── motopulse_pcb.pdf            # Complete Multipage PCB Layout PDF
│   ├── motopulse_bom.csv            # Bill of Materials
│   ├── motopulse_gerbers.zip        # Standard RS-274X Gerbers & Drill files
│   └── README.md                    # Hardware specifications & verification report
├── near_field_demo/
│   └── demo_50cm_perimeter.py       # Single-mic 50cm spatial gating simulator
├── oled_spectrum/
│   ├── live_spectrum_oled.py        # Real-time 16-band OLED spectrum engine
│   └── ssd1306.py                   # Lightweight MicroPython OLED driver
├── mic_test/
│   ├── run_test.sh                  # Interactive CLI control panel
│   ├── record_inmp441.py            # High-fidelity audio recorder (WAV/MP3)
│   └── test_inmp441_live.py         # Terminal VU meter
├── india_car_maintenance_research/
│   └── car_maintenance_india_research_report.md # Indian automotive predictive AI report
└── audio_recordings/                # Sample test audio recordings (WAV/MP3)
```

---

## 📊 Car Acoustic Dataset Hub

The [`datasets/`](./datasets/) folder is set up for collaborative recording and labeling of automotive acoustic datasets:
- **7 Target Failure Classes:** `normal_idle`, `engine_knocking`, `bearing_wear`, `valve_ticking`, `belt_slippage`, `exhaust_leak`, and `alternator_whine`.
- **Master Manifest:** [`datasets/dataset_manifest.csv`](./datasets/dataset_manifest.csv) logs vehicle make, RPM, sensor position, and failure notes.
- **Easy Uploader Tool:** Teammates can upload and label audio files using `python3 datasets/upload_dataset.py`.

---

## 📐 Hardware Schematics & PCB (KiCad Package)

The complete hardware package is available in the [`motopulse_kicad/`](./motopulse_kicad/) directory:
- **Schematic:** [`motopulse_schematic.pdf`](./motopulse_kicad/motopulse_schematic.pdf) / [`motopulse.kicad_sch`](./motopulse_kicad/motopulse.kicad_sch) — Passes ERC with **0 errors, 0 warnings**.
- **PCB Layout:** [`motopulse_pcb.pdf`](./motopulse_kicad/motopulse_pcb.pdf) / [`motopulse.kicad_pcb`](./motopulse_kicad/motopulse.kicad_pcb) — Passes DRC with **0 errors, 0 unconnected items**.
- **Bill of Materials:** [`motopulse_bom.csv`](./motopulse_kicad/motopulse_bom.csv).
- **Manufacturing Files:** [`motopulse_gerbers.zip`](./motopulse_kicad/motopulse_gerbers.zip) (Gerbers + Excellon drill files).

---

## 👥 Authors & Collaborators

- **Visweshwara S** ([@visweshvaras](https://github.com/visweshvaras)) — *Lead Author & Hardware/Firmware Architect*
- **Ishan** ([@ishannvn](https://github.com/ishannvn)) — *Co-Author & Core Contributor (Datasets & Vehicle Testing)*

Developed for **IEEE RUAS - Hacktivate 2026**. Feel free to fork, contribute datasets, and test edge AI vibration and acoustic models!

