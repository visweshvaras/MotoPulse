#!/usr/bin/env python3
"""
MotoPulse™ Cockpit - Backend Server & Telemetry Bridge
=====================================================
Hosts HTTP static & API services (Port 8080) and real-time WebSocket telemetry (Port 8765).
Bridges ESP32-S3 dual-microphone array & piezo vibration sensor to the web dashboard,
with intelligent auto-reconnection and seamless fallback simulation.
"""

import os
import sys
import time
import json
import wave
import struct
import base64
import asyncio
import threading
import subprocess
import urllib.parse
from http import HTTPStatus
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import mimetypes

import serial
import numpy as np
import websockets

# Base Directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "dashboard", "static")
RECORDINGS_DIR = os.path.join(BASE_DIR, "audio_recordings")
DATASETS_DIR = os.path.join(BASE_DIR, "datasets")
MANIFEST_PATH = os.path.join(DATASETS_DIR, "manifests", "processed_manifest.csv")

HTTP_PORT = 8080
WS_PORT = 8765
SERIAL_PORT = "/dev/ttyACM0"
SERIAL_BAUD = 115200

# Global thread-safe state
state_lock = threading.Lock()
serial_lock = threading.Lock()
connected_websockets = set()
server_running = True

# Import Online Continual Learner
sys.path.insert(0, os.path.join(BASE_DIR, "datasets", "models"))
try:
    from online_continual_learner import OnlineVehicleLearner
    g_online_learner = OnlineVehicleLearner(embedding_dim=48, learning_rate=0.04, anomaly_threshold_sigma=3.2)
    # Check if a previously saved vehicle profile exists
    profile_path = os.path.join(BASE_DIR, "datasets", "models", "learned_vehicle_profile.json")
    if os.path.exists(profile_path):
        with open(profile_path, "r") as f:
            prof = json.load(f)
            g_online_learner.restore_nvs_profile(prof)
            print(f"[LEARNER] Restored vehicle profile: {g_online_learner.total_frames_learned} frames remembered!")
except Exception as e:
    print(f"[LEARNER] Failed to initialize online continual learner: {e}")
    g_online_learner = None

g_sim_engine_running = True
g_sim_defect_frames_remaining = 0

# Latest telemetry cache for clients (compatible with app.js packet parser)
latest_telemetry = {
    "timestamp": time.time(),
    "source": "simulated",
    "fps": 35,
    "p2p_l": 1240,
    "p2p_r": 1180,
    "mic1": 1240,
    "mic2": 1180,
    "mic1_peak": 1240,
    "mic2_peak": 1180,
    "piezo_p2p": 45,
    "piezo_amp": 45,
    "piezo_raw": 2710,
    "piezo_base": 2710,
    "grad_pct": 5,
    "gradient": 5,
    "gradient_pct": 5,
    "status": "ARMED",
    "is_near": False,
    "knock": False,
    "distance_cm": 68.0,
    "wave_l": [0.0] * 64,
    "wave_r": [0.0] * 64,
    "gate": {
        "state": "ARMED",
        "is_near": False,
        "distance_cm": 68.0,
        "energy_pct": 28,
        "threshold": 1600,
        "ambient": 220
    },
    "piezo": {
        "baseline": 2710,
        "amplitude": 45,
        "peak_hold": 110,
        "knock": False,
        "state": "RESTING / NORMAL"
    },
    "learner": {
        "is_running": True,
        "status": "ADAPTING_BASELINE",
        "regime": 0,
        "regime_name": "Idle (750 RPM)",
        "score": 0.85,
        "is_anomaly": False,
        "learned": True,
        "total_learned": 0,
        "confidence": 95.0,
        "anomaly_count": 0
    }
}


# ==============================================================================
# AUDIO DSP PIPELINE (110Hz Rumble Filter, Voice/Presence Shelf, Soft Limiter)
# ==============================================================================
def apply_audio_dsp(samples_16: np.ndarray, fs: int = 16000) -> np.ndarray:
    """
    Applies high-fidelity automotive/speech acoustic enhancement:
    1. DC bias removal (float64)
    2. 2nd-order Butterworth High-Pass at 110 Hz (kills sub-rumble & mains hum)
    3. High-shelf presence EQ (+3.5 dB at 2800 Hz for crisp harmonics)
    4. Smart normalization + Soft-knee tanh peak limiter
    """
    if len(samples_16) == 0:
        return samples_16

    # 1. DC bias removal in float64 space
    x = samples_16.astype(np.float64) - np.mean(samples_16)

    # 2. 2nd order Butterworth High-Pass at 110 Hz
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
        out = (b0 * x0 + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2) / a0
        x2, x1 = x1, x0
        y2, y1 = y1, out
        y[i] = out

    # 3. High-shelf presence EQ (+3.5 dB at 2800 Hz)
    f0_shelf = 2800.0
    gain_db = 3.5
    A = 10.0 ** (gain_db / 40.0)
    w0_s = 2.0 * np.pi * f0_shelf / fs
    cos_s = np.cos(w0_s)
    sin_s = np.sin(w0_s)
    alpha_s = sin_s / 2.0 * np.sqrt((A + 1.0 / A) * (1.0 / 0.7071 - 1.0) + 2.0)

    b0_s = A * ((A + 1.0) + (A - 1.0) * cos_s + 2.0 * np.sqrt(A) * alpha_s)
    b1_s = -2.0 * A * ((A - 1.0) + (A + 1.0) * cos_s)
    b2_s = A * ((A + 1.0) + (A - 1.0) * cos_s - 2.0 * np.sqrt(A) * alpha_s)
    a0_s = (A + 1.0) - (A - 1.0) * cos_s + 2.0 * np.sqrt(A) * alpha_s
    a1_s = 2.0 * ((A - 1.0) - (A + 1.0) * cos_s)
    a2_s = (A + 1.0) - (A - 1.0) * cos_s - 2.0 * np.sqrt(A) * alpha_s

    z = np.zeros_like(y)
    x1 = x2 = y1 = y2 = 0.0
    for i in range(len(y)):
        x0 = y[i]
        out = (b0_s * x0 + b1_s * x1 + b2_s * x2 - a1_s * y1 - a2_s * y2) / a0_s
        x2, x1 = x1, x0
        y2, y1 = y1, out
        z[i] = out

    # 4. Smart Vocal Normalization + Soft-Knee Tanh Limiter
    p99 = np.percentile(np.abs(z), 99.6)
    target_p99 = 24000.0
    scale = target_p99 / max(p99, 100.0)
    scale = min(scale, 50.0)  # Avoid amplifying background floor infinitely

    scaled = z * scale
    knee_thresh = 26000.0
    excess = np.maximum(0.0, np.abs(scaled) - knee_thresh)
    compressed = np.where(
        np.abs(scaled) > knee_thresh,
        np.sign(scaled) * (knee_thresh + 6000.0 * np.tanh(excess / 6000.0)),
        scaled
    )
    return np.clip(compressed, -32768, 32767).astype(np.int16)


def record_vehicle_audio(duration_sec: float = 3.0):
    """
    Triggers 16kHz I2S recording from ESP32-S3 or generates synthetic vehicle
    test audio if ESP32 is offline, passes through the DSP pipeline, and saves
    both .wav and .mp3 into audio_recordings/.
    """
    os.makedirs(RECORDINGS_DIR, exist_ok=True)
    duration_sec = max(1.0, min(3.5, float(duration_sec)))
    sample_rate = 16000
    total_samples = int(duration_sec * sample_rate)
    num_chunks = int(total_samples / 1000)
    actual_samples = num_chunks * 1000
    actual_duration = actual_samples / float(sample_rate)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    wav_filename = f"inmp441_record_{timestamp}.wav"
    mp3_filename = f"inmp441_record_{timestamp}.mp3"
    wav_path = os.path.join(RECORDINGS_DIR, wav_filename)
    mp3_path = os.path.join(RECORDINGS_DIR, mp3_filename)

    captured_pcm = None

    # Try hardware capture first under serial_lock
    if serial_lock.acquire(timeout=0.6):
        try:
            if os.path.exists(SERIAL_PORT):
                ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=2)
                # Reset REPL
                ser.write(b'\r\x03\r\x03\r\x01')
                time.sleep(0.12)
                ser.read_all()

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
    rate={sample_rate},
    ibuf=8192
)

NUM_CHUNKS = {num_chunks}
CHUNK_SAMPLES = 1000
chunks = [bytearray(CHUNK_SAMPLES * 2) for _ in range(NUM_CHUNKS)]
in_buf = bytearray(CHUNK_SAMPLES * 8)

dummy = bytearray(512)
for _ in range(6): audio.readinto(dummy)

print('START_REC')
for c_idx in range(NUM_CHUNKS):
    audio.readinto(in_buf)
    dest = chunks[c_idx]
    d_pos = 0
    for s_idx in range(0, CHUNK_SAMPLES * 8, 8):
        dest[d_pos] = in_buf[s_idx + 2]
        dest[d_pos + 1] = in_buf[s_idx + 3]
        d_pos += 2

audio.deinit()
print('END_REC')

for c in chunks:
    for k in range(0, CHUNK_SAMPLES * 2, 120):
        sys.stdout.write(ubinascii.b2a_base64(c[k:k+120]))
print('ALL_SENT')
"""
                ser.write(code.encode('utf-8') + b'\x04')
                t_wait = time.time()
                started = False
                while time.time() - t_wait < 4.0:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if 'START_REC' in line:
                        started = True
                        break

                if started:
                    # Wait for download
                    all_lines = []
                    t_dl = time.time()
                    while time.time() - t_dl < max(12.0, actual_duration * 3.0):
                        line = ser.readline().decode('utf-8', errors='ignore').strip()
                        if 'ALL_SENT' in line:
                            break
                        if line and not line.startswith('OK') and not line.startswith('>') and not line.startswith('END_REC'):
                            all_lines.append(line)

                    pcm_raw = bytearray()
                    for l in all_lines:
                        try:
                            pcm_raw.extend(base64.b64decode(l))
                        except Exception:
                            pass

                    if len(pcm_raw) >= actual_samples * 2:
                        captured_pcm = bytes(pcm_raw[:actual_samples * 2])

                ser.write(b'\r\x02')
                ser.close()
        except Exception as e:
            print(f"[RECORDER] Hardware capture fallback: {e}")
        finally:
            serial_lock.release()

    # Fallback synthetic vehicle acoustic capture if hardware was busy or disconnected
    if captured_pcm is None:
        print("[RECORDER] Emitting high-fidelity simulated vehicle engine audio capture.")
        t = np.linspace(0, actual_duration, actual_samples, endpoint=False)
        # Vehicle engine idle acoustic harmonics + exhaust rumble + valve train clicks
        engine_tone = (
            0.45 * np.sin(2 * np.pi * 58.0 * t) +   # 4-cylinder crank idle base
            0.25 * np.sin(2 * np.pi * 116.0 * t) +  # 2nd harmonic
            0.15 * np.sin(2 * np.pi * 232.0 * t) +  # 4th harmonic
            0.08 * np.sin(2 * np.pi * 1750.0 * t)   # Alternator/belt whine
        )
        # Intake/exhaust flow noise
        noise = 0.12 * np.random.normal(0, 1, actual_samples)
        sim_audio = (engine_tone + noise) * 16000.0
        captured_pcm = sim_audio.astype(np.int16).tobytes()

    # Apply 110Hz rumble filter & voice/presence DSP pipeline
    raw_array = np.frombuffer(captured_pcm, dtype=np.int16)
    enhanced_array = apply_audio_dsp(raw_array, sample_rate)
    final_pcm = enhanced_array.tobytes()

    # Save WAV
    with wave.open(wav_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(final_pcm)

    # Convert to MP3 via ffmpeg if available
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", wav_path,
            "-b:a", "192k", mp3_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except Exception as e:
        print(f"[RECORDER] ffmpeg MP3 conversion skipped: {e}")

    file_size_kb = round(os.path.getsize(wav_path) / 1024, 1)

    return {
        "status": "success",
        "filename": wav_filename,
        "mp3_filename": mp3_filename if os.path.exists(mp3_path) else wav_filename,
        "url": f"/audio/{wav_filename}",
        "mp3_url": f"/audio/{mp3_filename}" if os.path.exists(mp3_path) else f"/audio/{wav_filename}",
        "duration_sec": actual_duration,
        "sample_rate": sample_rate,
        "size_kb": file_size_kb,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "dsp_applied": [
            "DC Bias Elimination",
            "110Hz Butterworth High-Pass Sub-Rumble Filter",
            "+3.5dB 2.8kHz Vocal/Acoustic Presence EQ",
            "Soft-Knee Tanh Dynamic Limiter"
        ]
    }


# ==============================================================================
# HTTP SERVER & REST API HANDLERS (PORT 8080)
# ==============================================================================
class CockpitHTTPHandler(BaseHTTPRequestHandler):
    """
    Robust HTTP Request Handler serving:
    - Static frontend files (index.html, style.css, app.js)
    - Audio recordings (/audio/<file>) with byte range support
    - Automotive defect datasets (/dataset_audio/<file>)
    - REST APIs (/api/datasets, /api/recordings, /api/record)
    """

    def log_message(self, format, *args):
        if self.path.startswith('/api/'):
            sys.stdout.write(f"[API] {self.command} {self.path} - {args[1]}\n")
            sys.stdout.flush()

    def send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Range')

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_cors_headers()
        self.end_headers()

    def do_HEAD(self):
        self.send_response(HTTPStatus.OK)
        self.send_cors_headers()
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # 1. API Endpoints
        if path == "/api/datasets":
            self.handle_api_datasets()
            return
        elif path == "/api/recordings":
            self.handle_api_recordings()
            return
        elif path == "/api/record":
            seconds = 3.0
            if "seconds" in query:
                try:
                    seconds = float(query["seconds"][0])
                except ValueError:
                    seconds = 3.0
            res = record_vehicle_audio(seconds)
            self.send_json_response(res)
            return
        elif path == "/api/learner/status":
            if g_online_learner:
                prof = g_online_learner.serialize_nvs_profile()
                prof["running_confidence"] = round(g_online_learner.running_confidence * 100, 1)
                prof["is_running"] = g_online_learner.is_running
                prof["anomaly_count"] = g_online_learner.anomaly_count
                prof["sim_engine_running"] = g_sim_engine_running
                self.send_json_response(prof)
            else:
                self.send_json_response({"error": "Learner not initialized"})
            return

        # 2. Audio recordings streaming (/audio/<filename>)
        if path.startswith("/audio/"):
            filename = urllib.parse.unquote(path[len("/audio/"):])
            filepath = os.path.join(RECORDINGS_DIR, filename)
            self.serve_file_with_range(filepath)
            return

        # 3. Dataset audio clips (/dataset_audio/<filename>)
        if path.startswith("/dataset_audio/"):
            filename = urllib.parse.unquote(path[len("/dataset_audio/"):])
            # Check processed first, then raw, then datasets root
            candidates = [
                os.path.join(DATASETS_DIR, "processed", filename),
                os.path.join(DATASETS_DIR, "raw", filename),
                os.path.join(DATASETS_DIR, filename)
            ]
            target_path = None
            for c in candidates:
                if os.path.exists(c):
                    target_path = c
                    break

            if target_path:
                self.serve_file_with_range(target_path)
            else:
                self.send_error(HTTPStatus.NOT_FOUND, f"Dataset audio file not found: {filename}")
            return

        # 4. Static frontend files
        if path in ["/", "/index.html"]:
            static_file = os.path.join(STATIC_DIR, "index.html")
        else:
            rel = path.lstrip("/")
            if rel.startswith("static/"):
                rel = rel[len("static/"):]
            static_file = os.path.join(STATIC_DIR, rel)

        if os.path.exists(static_file) and not os.path.isdir(static_file):
            self.serve_static_file(static_file)
        else:
            self.send_error(HTTPStatus.NOT_FOUND, f"File not found: {path}")

    def do_POST(self):
        global g_sim_engine_running, g_sim_defect_frames_remaining
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/record":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else ""
            seconds = 3.0
            try:
                if body:
                    data = json.loads(body)
                    seconds = float(data.get("seconds", 3.0))
            except Exception:
                pass
            res = record_vehicle_audio(seconds)
            self.send_json_response(res)
        elif parsed.path == "/api/learner/toggle_engine":
            g_sim_engine_running = not g_sim_engine_running
            self.send_json_response({
                "status": "OK",
                "engine_running": g_sim_engine_running
            })
        elif parsed.path == "/api/learner/simulate_defect":
            g_sim_defect_frames_remaining = 35  # Inject 35 frames of knock/bearing defect
            self.send_json_response({
                "status": "DEFECT_INJECTED",
                "frames": 35
            })
        elif parsed.path == "/api/learner/reset":
            if g_online_learner:
                g_online_learner.regime_counts = np.zeros(g_online_learner.num_regimes, dtype=np.int32)
                g_online_learner.regime_means = np.zeros((g_online_learner.num_regimes, g_online_learner.embedding_dim), dtype=np.float32)
                g_online_learner.regime_vars = np.ones((g_online_learner.num_regimes, g_online_learner.embedding_dim), dtype=np.float32) * 0.15
                g_online_learner.total_frames_learned = 0
                g_online_learner.anomaly_count = 0
                self.send_json_response({"status": "RESET_OK"})
            else:
                self.send_json_response({"error": "Learner not initialized"})
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def handle_api_datasets(self):
        """Returns JSON list of Ishan's 7 automotive defect clips from manifest."""
        items = []
        if os.path.exists(MANIFEST_PATH):
            import csv
            with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    fname = row.get("file_name", "")
                    items.append({
                        "file_name": fname,
                        "label": row.get("label", "unknown"),
                        "duration_sec": float(row.get("duration_sec", 0.0)),
                        "sample_rate": int(row.get("sample_rate", 16000)),
                        "channels": int(row.get("channels", 1)),
                        "bit_depth": int(row.get("bit_depth", 16)),
                        "vehicle_make_model": row.get("vehicle_make_model", "Passenger Car"),
                        "engine_type": row.get("engine_type", "Petrol"),
                        "sensor_location": row.get("sensor_location", "Engine Bay"),
                        "contributor": row.get("contributor", "Ishan"),
                        "notes": row.get("notes", ""),
                        "url": f"/dataset_audio/{fname}"
                    })
        self.send_json_response(items)

    def handle_api_recordings(self):
        """Returns list of user recorded WAV/MP3 files."""
        os.makedirs(RECORDINGS_DIR, exist_ok=True)
        files = []
        for fname in os.listdir(RECORDINGS_DIR):
            if fname.lower().endswith(('.wav', '.mp3')):
                fpath = os.path.join(RECORDINGS_DIR, fname)
                st = os.stat(fpath)
                files.append({
                    "filename": fname,
                    "size_bytes": st.st_size,
                    "size_kb": round(st.st_size / 1024, 1),
                    "mtime": st.st_mtime,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime)),
                    "url": f"/audio/{fname}"
                })
        # Sort newest first
        files.sort(key=lambda x: x["mtime"], reverse=True)
        self.send_json_response(files)

    def send_json_response(self, data):
        body = json.dumps(data, indent=2).encode('utf-8')
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def serve_static_file(self, filepath):
        mime, _ = mimetypes.guess_type(filepath)
        if not mime:
            if filepath.endswith('.js'): mime = 'application/javascript'
            elif filepath.endswith('.css'): mime = 'text/css'
            elif filepath.endswith('.html'): mime = 'text/html'
            else: mime = 'application/octet-stream'

        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-cache')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(e))

    def serve_file_with_range(self, filepath):
        """Serves audio with full HTTP 206 Partial Content (Byte Range) support."""
        if not os.path.exists(filepath):
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        file_size = os.path.getsize(filepath)
        mime, _ = mimetypes.guess_type(filepath)
        if not mime:
            if filepath.endswith('.wav'): mime = 'audio/wav'
            elif filepath.endswith('.mp3'): mime = 'audio/mpeg'
            else: mime = 'application/octet-stream'

        range_header = self.headers.get('Range')

        if not range_header:
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(file_size))
            self.send_header('Accept-Ranges', 'bytes')
            self.send_cors_headers()
            self.end_headers()
            with open(filepath, 'rb') as f:
                self.wfile.write(f.read())
            return

        # Parse range header: e.g. "bytes=0-1024" or "bytes=1024-"
        try:
            range_val = range_header.strip().split('=')[1]
            parts = range_val.split('-')
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1
            if start >= file_size or end >= file_size or start > end:
                self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                self.send_header('Content-Range', f'bytes */{file_size}')
                self.end_headers()
                return

            length = end - start + 1
            self.send_response(HTTPStatus.PARTIAL_CONTENT)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
            self.send_header('Content-Length', str(length))
            self.send_header('Accept-Ranges', 'bytes')
            self.send_cors_headers()
            self.end_headers()

            with open(filepath, 'rb') as f:
                f.seek(start)
                self.wfile.write(f.read(length))
        except Exception:
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(file_size))
            self.send_cors_headers()
            self.end_headers()
            with open(filepath, 'rb') as f:
                self.wfile.write(f.read())


# ==============================================================================
# TELEMETRY ENGINE & ESP32 HARDWARE BRIDGE
# ==============================================================================
ESP32_TELEMETRY_SCRIPT = """
import machine, framebuf, time, gc
gc.collect()

# 1. 9-clock I2C bus recovery
scl_rec = machine.Pin(8, machine.Pin.OUT)
for _ in range(9):
    scl_rec.value(0)
    time.sleep_us(5)
    scl_rec.value(1)
    time.sleep_us(5)

# 100 kHz I2C for rock-solid signal integrity on breadboards and jumper wires
i2c = machine.I2C(0, scl=machine.Pin(8), sda=machine.Pin(9), freq=100000)

devs = i2c.scan()
addr = 0x3C
if 0x3D in devs and 0x3C not in devs:
    addr = 0x3D

temp = bytearray(2)
temp[0] = 0x80
def write_cmd(c):
    temp[1] = c
    try: i2c.writeto(addr, temp)
    except: pass

# Universal initialization: works on both SSD1306 and SH1106 (0.96" and 1.3" OLEDs)
for c in (
    0xAE,             # Display OFF
    0xD5, 0x80,       # Set display clock divide
    0xA8, 63,         # Multiplex ratio 64
    0xD3, 0x00,       # Display offset 0
    0x40,             # Start line 0
    0x8D, 0x14,       # SSD1306 Charge Pump ON
    0xAD, 0x8B,       # SH1106 DC-DC converter ON
    0x30, 0x33,       # SH1106 Pump voltage
    0xA1,             # Segment remap
    0xC8,             # COM output scan direction
    0xDA, 0x12,       # COM pins hardware configuration
    0x81, 0xFF,       # Contrast control to maximum (100% brightness)
    0xD9, 0xF1,       # Pre-charge period
    0xDB, 0x40,       # VCOMH deselect level
    0xA4,             # Output follows RAM content
    0xA6,             # Normal display
    0xAF              # Display ON
):
    write_cmd(c)

buf = bytearray(128 * 8)
fb = framebuf.FrameBuffer(buf, 128, 64, framebuf.MONO_VLSB)

# Universal Page-by-Page Refresh (works on 100% of SSD1306 AND SH1106 controllers)
def flush_display():
    for p in range(8):
        write_cmd(0xB0 + p) # Page 0 to 7
        write_cmd(0x02)      # Column low: 2px offset (centers on SH1106, harmless on SSD1306)
        write_cmd(0x10)      # Column high: 0
        page_slice = buf[p * 128 : (p + 1) * 128]
        try:
            i2c.writevto(addr, [b"\\x40", page_slice])
        except Exception:
            pass

# 16kHz Stereo I2S INMP441 Microphone (SCK=4, WS=5, SD=6)
audio = machine.I2S(
    0,
    sck=machine.Pin(4),
    ws=machine.Pin(5),
    sd=machine.Pin(6),
    mode=machine.I2S.RX,
    bits=32,
    format=machine.I2S.STEREO,
    rate=16000,
    ibuf=4096
)

# Piezo on GPIO 1
p1 = machine.Pin(1, machine.Pin.IN, machine.Pin.PULL_DOWN)
adc = machine.ADC(p1)
try: adc.atten(machine.ADC.ATTN_11DB)
except: pass

buf_in = bytearray(512)
for _ in range(5): audio.readinto(buf_in)

calib_vals = [adc.read() for _ in range(32)]
dc_piezo = sum(calib_vals) // 32
decay_peak = 0
frame_count = 0

print("TEL_READY")

while True:
    audio.readinto(buf_in)
    frame_count += 1
    
    left = []
    right = []
    for i in range(64):
        b = i * 8
        vl = (buf_in[b + 3] << 8) | buf_in[b + 2]
        if vl & 0x8000: vl -= 0x10000
        left.append(vl)
        
        vr = (buf_in[b + 7] << 8) | buf_in[b + 6]
        if vr & 0x8000: vr -= 0x10000
        right.append(vr)
        
    p2p_l = max(left) - min(left)
    p2p_r = max(right) - min(right)
    max_amp = max(p2p_l, p2p_r)
    diff = abs(p2p_l - p2p_r)
    grad = (diff * 100) // (max_amp + 1)
    
    pz_min = 4095
    pz_max = 0
    pz_samples = []
    for _ in range(16):
        v = adc.read()
        pz_samples.append(v)
        if v < pz_min: pz_min = v
        if v > pz_max: pz_max = v
    pz_amp = pz_max - pz_min
    if pz_amp > decay_peak: decay_peak = pz_amp
    else: decay_peak = max(0, decay_peak - 25)

    is_running = (max_amp > 800) or (decay_peak > 180)
    is_anomaly = (decay_peak > 1400) or (max_amp > 8500 and grad > 45)

    # Render OLED Frame (30 FPS)
    fb.fill(0)
    fb.text("MOTOPULSE", 0, 1, 1)
    if is_anomaly:
        fb.fill_rect(82, 0, 46, 10, 1)
        fb.text("!WARN", 84, 1, 0)
    elif is_running:
        fb.text("[RUN]", 88, 1, 1)
    else:
        fb.text("[IDLE]", 80, 1, 1)
    fb.hline(0, 11, 128, 1)

    # Waveform trace
    center_y = 30
    scale = 16.0 / max(800, max_amp)
    prev_y = center_y
    for x in range(min(64, len(left))):
        val = left[x]
        y = center_y - int(val * scale)
        if y < 13: y = 13
        elif y > 48: y = 48
        fb.line(x * 2, prev_y, x * 2 + 1, y, 1)
        prev_y = y

    # Lower VU Meters
    audio_bar_w = min(60, int((max_amp / 7000.0) * 60))
    fb.rect(0, 52, 62, 5, 1)
    if audio_bar_w > 0:
        fb.fill_rect(1, 53, audio_bar_w, 3, 1)

    pz_bar_w = min(60, int((decay_peak / 1500.0) * 60))
    fb.rect(66, 52, 62, 5, 1)
    if pz_bar_w > 0:
        fb.fill_rect(67, 53, pz_bar_w, 3, 1)

    fb.text("MIC", 18, 57, 1)
    fb.text("PIEZO", 80, 57, 1)
    flush_display()
    
    w_l = ",".join(str(left[k]) for k in range(0, 64, 2))
    w_r = ",".join(str(right[k]) for k in range(0, 64, 2))
    w_p = ",".join(str(pz_samples[k]) for k in range(0, 16))
    
    print("TEL:" + str(p2p_l) + ":" + str(p2p_r) + ":" + str(grad) + ":" + str(pz_amp) + ":" + str(decay_peak) + ":" + str(dc_piezo) + ":" + w_l + ":" + w_r + ":" + w_p)
    time.sleep_ms(10)
"""


def telemetry_collector_thread():
    """
    Background worker that continuously streams live hardware telemetry from ESP32-S3.
    If disconnected or busy, automatically generates smooth fallback simulation
    and tries to reconnect seamlessly.
    """
    global latest_telemetry, server_running

    sim_tick = 0
    decay_hold = 0

    while server_running:
        ser = None
        is_hardware = False

        # Attempt to open ESP32 hardware
        if os.path.exists(SERIAL_PORT):
            if serial_lock.acquire(blocking=False):
                try:
                    ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1.0)
                    
                    # 1. Check if on-device main.py is ALREADY actively streaming TEL:
                    t_check = time.time()
                    while time.time() - t_check < 0.6:
                        l = ser.readline().decode('utf-8', errors='ignore').strip()
                        if l.startswith("TEL:"):
                            is_hardware = True
                            print(f"[BRIDGE] Connected to running ESP32-S3 firmware on {SERIAL_PORT}! Streaming live hardware telemetry.")
                            break

                    if not is_hardware:
                        ser.write(b'\r\x03\r\x03\r\x01')
                        time.sleep(0.12)
                        ser.read_all()
                        ser.write(ESP32_TELEMETRY_SCRIPT.encode('utf-8') + b'\x04')

                        t_start = time.time()
                        while time.time() - t_start < 4.0:
                            l = ser.readline().decode('utf-8', errors='ignore').strip()
                            if "TEL_READY" in l or l.startswith("TEL:"):
                                is_hardware = True
                                print(f"[BRIDGE] Connected to ESP32-S3 on {SERIAL_PORT}! Streaming live hardware telemetry.")
                                break
                    if not is_hardware:
                        ser.close()
                        ser = None
                except Exception as e:
                    if ser:
                        try: ser.close()
                        except: pass
                        ser = None
                finally:
                    if not is_hardware:
                        serial_lock.release()

        # If connected to hardware, read lines
        if is_hardware and ser:
            try:
                consecutive_errors = 0
                hw_frame_cnt = 0
                while server_running:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if not line:
                        consecutive_errors += 1
                        if consecutive_errors > 8:
                            break
                        continue
                    consecutive_errors = 0

                    if line.startswith("TEL:"):
                        parts = line.split(":")
                        if len(parts) >= 10:
                            p2p_l = int(parts[1])
                            p2p_r = int(parts[2])
                            grad = int(parts[3])
                            pz_amp = int(parts[4])
                            pz_peak = int(parts[5])
                            pz_base = int(parts[6])
                            raw_wl = [int(v) for v in parts[7].split(",") if v]
                            raw_wr = [int(v) for v in parts[8].split(",") if v]
                            raw_wp = [int(v) for v in parts[9].split(",") if v]

                            max_amp = max(p2p_l, p2p_r)
                            # 50cm Perimeter Gate calculation
                            ambient = 220
                            thresh = 1600
                            is_near = (max_amp >= thresh) and (grad >= 10 or max_amp >= thresh * 1.4)
                            gate_state = "INSIDE_50CM" if is_near else ("FAR_REJECTED" if max_amp > ambient * 2 else "QUIET")
                            dist_cm = max(5.0, min(120.0, 50.0 * (float(thresh) / max(max_amp, 100)) ** 0.5))

                            knock_detected = pz_amp > 350
                            vibe_state = "KNOCK ALERT!" if knock_detected else ("TAP DETECTED" if pz_amp > 150 else "RESTING / NORMAL")

                            # Normalize waveform amplitudes to [-1.0, 1.0] for HTML5 Canvas rendering
                            scale_ref = max(1800.0, float(max_amp) * 1.2)
                            norm_wl = [round(float(v) / scale_ref, 3) for v in raw_wl]
                            norm_wr = [round(float(v) / scale_ref, 3) for v in raw_wr]

                            hw_frame_cnt += 1
                            learner_info = latest_telemetry.get("learner", {})
                            if g_online_learner and (hw_frame_cnt % 10 == 0):
                                arr_l = np.array(norm_wl, dtype=np.float32)
                                fft_vals = np.abs(np.fft.rfft(arr_l, n=64))[:32]
                                fft_norm = fft_vals / (np.max(fft_vals) + 1e-5)
                                fft_norm[0] = min(1.0, float(max_amp) / 3000.0)
                                fft_norm[1] = min(1.0, float(grad) / 40.0)
                                dyn16 = np.abs(np.diff(fft_norm[:17]))
                                emb = np.concatenate([fft_norm, dyn16]).astype(np.float32)

                                piezo_rms_scaled = float(pz_amp) / 1000.0
                                audio_energy_scaled = float(max_amp) / 10000.0

                                step_res = g_online_learner.update_step(emb, piezo_rms_scaled, audio_energy_scaled)
                                regime_names = ["Idle (750 RPM)", "City Drive (1800 RPM)", "Highway Cruise (2800 RPM)"]
                                regime_id = step_res.get("regime", 0)

                                learner_info = {
                                    "is_running": step_res["is_running"],
                                    "status": step_res["status"],
                                    "regime": regime_id,
                                    "regime_name": regime_names[regime_id % len(regime_names)],
                                    "score": step_res.get("score", 0.0),
                                    "is_anomaly": step_res.get("is_anomaly", False),
                                    "learned": step_res.get("learned", False),
                                    "total_learned": g_online_learner.total_frames_learned,
                                    "confidence": round(g_online_learner.running_confidence * 100, 1),
                                    "anomaly_count": g_online_learner.anomaly_count
                                }

                            with state_lock:
                                latest_telemetry = {
                                    "timestamp": time.time(),
                                    "source": "hardware",
                                    "fps": 36,
                                    "p2p_l": p2p_l,
                                    "p2p_r": p2p_r,
                                    "mic1": p2p_l,
                                    "mic2": p2p_r,
                                    "mic1_peak": p2p_l,
                                    "mic2_peak": p2p_r,
                                    "piezo_p2p": pz_amp,
                                    "piezo_amp": pz_amp,
                                    "piezo_raw": pz_base + (pz_amp if knock_detected else 0),
                                    "piezo_base": pz_base,
                                    "grad_pct": grad,
                                    "gradient": grad,
                                    "gradient_pct": grad,
                                    "status": "NEAR" if is_near else ("FAR" if max_amp > ambient * 2 else "ARMED"),
                                    "is_near": is_near,
                                    "knock": knock_detected,
                                    "distance_cm": round(dist_cm, 1),
                                    "wave_l": norm_wl,
                                    "wave_r": norm_wr,
                                    "gate": {
                                        "state": gate_state,
                                        "is_near": is_near,
                                        "distance_cm": round(dist_cm, 1),
                                        "energy_pct": min(100, int((max_amp / 3200.0) * 100)),
                                        "threshold": thresh,
                                        "ambient": ambient
                                    },
                                    "piezo": {
                                        "baseline": pz_base,
                                        "amplitude": pz_amp,
                                        "peak_hold": pz_peak,
                                        "knock": knock_detected,
                                        "state": vibe_state
                                    },
                                    "learner": learner_info
                                }
            except Exception as e:
                print(f"[BRIDGE] Hardware stream interrupted: {e}")
            finally:
                try:
                    ser.write(b'\r\x02')
                    ser.close()
                except Exception:
                    pass
                try:
                    serial_lock.release()
                except Exception:
                    pass

        # Fallback Simulation loop: keeps dashboard fully alive!
        # Runs at ~35 FPS (28ms sleep)
        sim_tick += 1
        t_phase = sim_tick * 0.15

        # Check defect injection state
        is_defect_injected = False
        if g_sim_defect_frames_remaining > 0:
            g_sim_defect_frames_remaining -= 1
            is_defect_injected = True

        if g_sim_engine_running:
            # Engine acoustic harmonics (idle / drive rumble)
            mic1_base = int(1150 + 280 * np.sin(t_phase) + 90 * np.cos(t_phase * 2.3) + np.random.randint(-40, 40))
            grad_sim = max(2, min(25, int(5 + 3 * np.sin(t_phase * 0.7) + np.random.randint(-1, 2))))
            mic2_base = int(mic1_base * (1.0 - (grad_sim / 100.0)))
            pz_amp = int(45 + 25 * np.abs(np.sin(t_phase * 1.5)) + np.random.randint(-8, 8))
        else:
            # Engine Off / Parked ambient silence
            mic1_base = int(180 + np.random.randint(-20, 20))
            grad_sim = 2
            mic2_base = mic1_base
            pz_amp = int(8 + np.random.randint(-2, 2))

        # Periodic near-field approach trigger every ~12 seconds
        is_near = (sim_tick % 400 > 360) and g_sim_engine_running
        if is_near:
            mic1_base = int(mic1_base * 2.2)
            mic2_base = int(mic2_base * 1.8)
            grad_sim = 18
            gate_state = "INSIDE_50CM"
            dist_cm = 28.5
            status_str = "NEAR"
        elif mic1_base > 1350:
            gate_state = "FAR_REJECTED"
            dist_cm = 74.0
            status_str = "FAR"
        elif g_sim_engine_running:
            gate_state = "ARMED"
            dist_cm = 65.0
            status_str = "ARMED"
        else:
            gate_state = "RESTING"
            dist_cm = 99.0
            status_str = "ENGINE_OFF"

        # Piezo mechanical vibration & knock injection
        knock_sim = is_defect_injected or ((sim_tick % 450 == 120) and g_sim_engine_running)
        if knock_sim:
            pz_amp = 1450
            decay_hold = 1450
            vibe_state = "KNOCK ALERT!"
        else:
            decay_hold = max(pz_amp, decay_hold - 20)
            vibe_state = "RESTING / NORMAL" if decay_hold < 350 else "TAP DETECTED"

        # Generate realistic 64-sample normalized audio waveforms [-1.0, 1.0]
        t_samples = np.linspace(0, 0.04, 64)
        if g_sim_engine_running:
            wave_l = [round(float(0.45 * np.sin(2 * np.pi * 95.0 * ts + t_phase) + 0.15 * np.sin(2 * np.pi * 190.0 * ts) + (np.random.random() - 0.5) * 0.08), 3) for ts in t_samples]
            wave_r = [round(float(0.42 * np.sin(2 * np.pi * 95.0 * ts + t_phase - 0.2) + 0.14 * np.sin(2 * np.pi * 190.0 * ts) + (np.random.random() - 0.5) * 0.08), 3) for ts in t_samples]
        else:
            wave_l = [round(float((np.random.random() - 0.5) * 0.02), 3) for _ in t_samples]
            wave_r = [round(float((np.random.random() - 0.5) * 0.02), 3) for _ in t_samples]

        if knock_sim:
            # Inject sharp acoustic clatter spikes into waveform
            for idx in [12, 13, 28, 29, 44, 45]:
                wave_l[idx] = 0.95
                wave_r[idx] = 0.88

        # --- Online Continual Learning Step (~3 updates per second) ---
        learner_info = latest_telemetry.get("learner", {})
        if g_online_learner and (sim_tick % 10 == 0):
            # Construct 48-D stream embedding from waveform frequency bands + dynamics
            arr_l = np.array(wave_l, dtype=np.float32)
            fft_vals = np.abs(np.fft.rfft(arr_l, n=64))[:32]
            fft_norm = fft_vals / (np.max(fft_vals) + 1e-5)
            # Incorporate energy and gradient proxies
            fft_norm[0] = min(1.0, float(mic1_base) / 3000.0)
            fft_norm[1] = min(1.0, float(grad_sim) / 40.0)
            dyn16 = np.abs(np.diff(fft_norm[:17]))
            emb = np.concatenate([fft_norm, dyn16]).astype(np.float32)

            piezo_rms_scaled = float(pz_amp) / 1000.0
            audio_energy_scaled = float(mic1_base) / 10000.0

            step_res = g_online_learner.update_step(emb, piezo_rms_scaled, audio_energy_scaled)
            regime_names = ["Idle (750 RPM)", "City Drive (1800 RPM)", "Highway Cruise (2800 RPM)"]
            regime_id = step_res.get("regime", 0)

            learner_info = {
                "is_running": step_res["is_running"],
                "status": step_res["status"],
                "regime": regime_id,
                "regime_name": regime_names[regime_id % len(regime_names)],
                "score": step_res.get("score", 0.0),
                "is_anomaly": step_res.get("is_anomaly", False),
                "learned": step_res.get("learned", False),
                "total_learned": g_online_learner.total_frames_learned,
                "confidence": round(g_online_learner.running_confidence * 100, 1),
                "anomaly_count": g_online_learner.anomaly_count
            }

        with state_lock:
            latest_telemetry = {
                "timestamp": time.time(),
                "source": "simulated",
                "fps": 35,
                "p2p_l": mic1_base,
                "p2p_r": mic2_base,
                "mic1": mic1_base,
                "mic2": mic2_base,
                "mic1_peak": mic1_base,
                "mic2_peak": mic2_base,
                "piezo_p2p": pz_amp,
                "piezo_amp": pz_amp,
                "piezo_raw": 2710 + (pz_amp if knock_sim else 0),
                "piezo_base": 2710,
                "grad_pct": grad_sim,
                "gradient": grad_sim,
                "gradient_pct": grad_sim,
                "status": status_str,
                "is_near": is_near,
                "knock": knock_sim,
                "distance_cm": round(dist_cm, 1),
                "wave_l": wave_l,
                "wave_r": wave_r,
                "gate": {
                    "state": gate_state,
                    "is_near": is_near,
                    "distance_cm": round(dist_cm, 1),
                    "energy_pct": min(100, int((max(mic1_base, mic2_base) / 3000.0) * 100)),
                    "threshold": 1600,
                    "ambient": 220
                },
                "piezo": {
                    "baseline": 2710,
                    "amplitude": pz_amp,
                    "peak_hold": decay_hold,
                    "knock": knock_sim,
                    "state": vibe_state
                },
                "learner": learner_info
            }

        time.sleep(0.028)  # ~35 FPS


# ==============================================================================
# WEBSOCKET BROADCAST SERVER (PORT 8765)
# ==============================================================================
async def ws_handler(websocket):
    """Handles incoming browser WebSocket connections."""
    connected_websockets.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        connected_websockets.discard(websocket)


async def ws_broadcast_loop():
    """Continuously broadcasts the latest telemetry snapshot to all connected clients."""
    while server_running:
        if connected_websockets:
            with state_lock:
                payload = json.dumps(latest_telemetry)
            dead_sockets = set()
            for ws in list(connected_websockets):
                try:
                    await ws.send(payload)
                except Exception:
                    dead_sockets.add(ws)
            connected_websockets.difference_update(dead_sockets)

        await asyncio.sleep(0.028)  # ~35 FPS broadcast cadence


# ==============================================================================
# ENTRY POINT & LIFECYCLE MANAGEMENT
# ==============================================================================
def run_http_server():
    server_address = ('0.0.0.0', HTTP_PORT)
    httpd = ThreadingHTTPServer(server_address, CockpitHTTPHandler)
    print(f"🚀 MotoPulse™ HTTP Server running at http://localhost:{HTTP_PORT}/")
    try:
        httpd.serve_forever()
    except Exception:
        pass
    finally:
        httpd.server_close()


async def main():
    global server_running

    print("=" * 70)
    print("   🏎️  MOTOPULSE™ AI VEHICLE ACOUSTIC & VIBRATION TELEMETRY COCKPIT")
    print(f"   📡 HTTP Server:      http://0.0.0.0:{HTTP_PORT}")
    print(f"   ⚡ WebSocket Bridge: ws://0.0.0.0:{WS_PORT}")
    print(f"   🔌 Serial Interface: {SERIAL_PORT} (115200 Baud)")
    print("=" * 70)

    # Start HTTP server thread
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()

    # Start Hardware / Simulation Telemetry collector thread
    telemetry_thread = threading.Thread(target=telemetry_collector_thread, daemon=True)
    telemetry_thread.start()

    # Start WebSocket Server
    async with websockets.serve(ws_handler, "0.0.0.0", WS_PORT):
        print(f"✔ WebSocket bridge listening on port {WS_PORT}")
        await ws_broadcast_loop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] MotoPulse™ Server stopped cleanly.")
        server_running = False
        sys.exit(0)
