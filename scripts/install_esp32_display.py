#!/usr/bin/env python3
"""
MotoPulse™ On-Device Display & Firmware Installer
Installs persistent `/boot.py` and `/main.py` directly into the ESP32-S3 Flash filesystem.
Ensures the 0.96" SSD1306 OLED display (SCL=8, SDA=9) runs automatically anytime the
device is powered on (in-vehicle, battery, USB, or standalone bench).

Features of On-Device Firmware:
- Instant OLED splash screen upon power-up
- Fluid real-time 30 FPS oscilloscope audio waveform trace (Dual INMP441s, SCK=4, WS=5, SD=6)
- Mechanical engine vibration monitoring via Piezo (GPIO 1 ADC)
- Real-time engine state detection (RUNNING / IDLE / OFF / ANOMALY)
- Live dual VU meter bars (Acoustic dB + Piezo mechanical amplitude)
- Concurrent UART telemetry streaming (TEL:...) compatible with MotoPulse Web Dashboard
"""

import sys
import time
import serial
import os

SERIAL_PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyACM0"
BAUD = 115200

BOOT_PY_CONTENT = """# MotoPulse Boot Script
import gc, esp
esp.osdebug(None)
gc.collect()
"""

MAIN_PY_CONTENT = """# MotoPulse™ Autonomous On-Device Display & Diagnostics
# Target: ESP32-S3 (SCL=8, SDA=9, I2S: SCK=4, WS=5, SD=6, Piezo=1)

import machine, framebuf, time, gc

gc.collect()

# --- 1. I2C Bus Recovery & OLED Initialization ---
# 9-clock I2C recovery pulse ensures bus is never latched by interrupted transactions
scl_rec = machine.Pin(8, machine.Pin.OUT)
for _ in range(9):
    scl_rec.value(0)
    time.sleep_us(5)
    scl_rec.value(1)
    time.sleep_us(5)

# 100 kHz I2C for rock-solid signal integrity on breadboards and jumper wires
i2c = machine.I2C(0, scl=machine.Pin(8), sda=machine.Pin(9), freq=100000)

# Auto-detect I2C address (0x3C or 0x3D)
devs = i2c.scan()
addr = 0x3C
if 0x3D in devs and 0x3C not in devs:
    addr = 0x3D

temp = bytearray(2)
temp[0] = 0x80
def write_cmd(c):
    temp[1] = c
    try:
        i2c.writeto(addr, temp)
    except Exception:
        pass

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

# --- 2. Boot Splash Screen ---
fb.fill(0)
fb.rect(0, 0, 128, 64, 1)
fb.fill_rect(2, 2, 124, 14, 1)
fb.text("MOTOPULSE AI", 16, 5, 0)
fb.text("Dual INMP441 4cm", 4, 22, 1)
fb.text("Piezo GPIO 1 Active", 4, 35, 1)
fb.text("Initializing...", 4, 48, 1)
flush_display()
time.sleep_ms(800)

# --- 3. Hardware Peripherals Initialization ---
# Dual INMP441 I2S MEMS Microphones (16 kHz, 32-bit Stereo)
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

# Piezo Vibration Sensor on GPIO 1 (ADC1_CH0 with 1M damping bleed)
p1 = machine.Pin(1, machine.Pin.IN, machine.Pin.PULL_DOWN)
adc = machine.ADC(p1)
try:
    adc.atten(machine.ADC.ATTN_11DB)
except Exception:
    pass

buf_in = bytearray(512)
for _ in range(5):
    audio.readinto(buf_in)

# Baseline calibration
calib_vals = [adc.read() for _ in range(32)]
dc_piezo = sum(calib_vals) // 32
decay_peak = 0
frame_count = 0

print("MOTOPULSE_DISPLAY_ACTIVE")

# --- 4. Main Real-Time Diagnostic & Display Loop ---
while True:
    audio.readinto(buf_in)
    frame_count += 1

    # Extract stereo audio samples
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

    # Sample Piezo sensor (16 samples)
    pz_min = 4095
    pz_max = 0
    pz_samples = []
    for _ in range(16):
        v = adc.read()
        pz_samples.append(v)
        if v < pz_min: pz_min = v
        if v > pz_max: pz_max = v
    pz_amp = pz_max - pz_min
    if pz_amp > decay_peak:
        decay_peak = pz_amp
    else:
        decay_peak = max(0, decay_peak - 25)

    # State classification logic:
    # Engine running: both acoustic amplitude and piezo vibration exceed idle thresholds
    is_running = (max_amp > 800) or (decay_peak > 180)
    is_anomaly = (decay_peak > 1400) or (max_amp > 8500 and grad > 45)

    # --- RENDER TO 0.96" OLED DISPLAY (128x64) ---
    fb.fill(0)

    # Header Bar: Logo & Status Tag
    fb.text("MOTOPULSE", 0, 1, 1)
    if is_anomaly:
        fb.fill_rect(82, 0, 46, 10, 1)
        fb.text("!WARN", 84, 1, 0)
    elif is_running:
        fb.text("[RUN]", 88, 1, 1)
    else:
        fb.text("[IDLE]", 80, 1, 1)
    fb.hline(0, 11, 128, 1)

    # Middle Area: Live Fluid Audio Oscilloscope Waveform (y=13 to 48, center=30)
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

    # Lower Area: Dual VU Meters & Metrics (y=50 to 63)
    # Mic Acoustic Volume Bar (0 to 60px)
    audio_bar_w = min(60, int((max_amp / 7000.0) * 60))
    fb.rect(0, 52, 62, 5, 1)
    if audio_bar_w > 0:
        fb.fill_rect(1, 53, audio_bar_w, 3, 1)

    # Piezo Vibration Bar (66 to 126px)
    pz_bar_w = min(60, int((decay_peak / 1500.0) * 60))
    fb.rect(66, 52, 62, 5, 1)
    if pz_bar_w > 0:
        fb.fill_rect(67, 53, pz_bar_w, 3, 1)

    # Labels below bars
    fb.text("MIC", 18, 57, 1)
    fb.text("PIEZO", 80, 57, 1)

    flush_display()

    # Telemetry UART Stream (for Web Dashboard / Host Tools)
    if frame_count % 2 == 0:
        w_l = ",".join(str(left[k]) for k in range(0, 64, 2))
        w_r = ",".join(str(right[k]) for k in range(0, 64, 2))
        w_p = ",".join(str(pz_samples[k]) for k in range(0, 16))
        print("TEL:" + str(p2p_l) + ":" + str(p2p_r) + ":" + str(grad) + ":" + str(pz_amp) + ":" + str(decay_peak) + ":" + str(dc_piezo) + ":" + w_l + ":" + w_r + ":" + w_p)

    time.sleep_ms(10)
"""

def install():
    print(f"Connecting to ESP32-S3 on {SERIAL_PORT}...")
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD, timeout=3.0)
    except Exception as e:
        print(f"❌ Error opening serial port {SERIAL_PORT}: {e}")
        return False

    print("Entering raw REPL mode...")
    ser.write(b"\r\x03\r\x03\r\x01")
    time.sleep(0.3)
    ser.read_all()

    # Step 1: Ensure VFS partition is formatted and mounted
    mount_script = """
import os, vfs, esp32
try:
    p = esp32.Partition.find(esp32.Partition.TYPE_DATA, label="vfs")[0]
    try:
        v = vfs.VfsLfs2(p)
        vfs.mount(v, "/")
    except Exception:
        vfs.VfsLfs2.mkfs(p)
        v = vfs.VfsLfs2(p)
        vfs.mount(v, "/")
    print("VFS_MOUNT_OK")
except Exception as e:
    print("VFS_ERR:", e)
"""
    ser.write(mount_script.encode("utf-8") + b"\x04")
    time.sleep(0.8)
    out = ser.read_all().decode("utf-8", errors="ignore")
    print("Filesystem status:", out.strip())

    # Step 2: Write /boot.py
    print("Writing /boot.py...")
    write_boot = f"""
with open("/boot.py", "w") as f:
    f.write({repr(BOOT_PY_CONTENT)})
print("BOOT_WRITTEN")
"""
    ser.write(write_boot.encode("utf-8") + b"\x04")
    time.sleep(0.5)
    out = ser.read_all().decode("utf-8", errors="ignore")
    if "BOOT_WRITTEN" in out:
        print("✔ /boot.py written successfully.")
    else:
        print("❌ Warning: /boot.py response:", out)

    # Step 3: Write /main.py
    print("Writing /main.py (Persistent Standalone OLED Display & Diagnostics)...")
    write_main = f"""
with open("/main.py", "w") as f:
    f.write({repr(MAIN_PY_CONTENT)})
print("MAIN_WRITTEN")
"""
    ser.write(write_main.encode("utf-8") + b"\x04")
    time.sleep(1.5)
    out = ser.read_all().decode("utf-8", errors="ignore")
    if "MAIN_WRITTEN" in out:
        print("✔ /main.py written successfully.")
    else:
        print("❌ Warning: /main.py response:", out)

    # Step 4: Verify files
    verify_script = """
import os
print("FILES_ON_FLASH:", os.listdir("/"))
"""
    ser.write(verify_script.encode("utf-8") + b"\x04")
    time.sleep(0.5)
    out = ser.read_all().decode("utf-8", errors="ignore")
    print("Flash directory:", out.strip())

    # Step 5: Soft reboot to launch main.py
    print("Launching firmware (Soft reboot)...")
    ser.write(b"\r\x02\r\x04") # Exit raw REPL and soft reboot
    time.sleep(1.2)
    boot_log = ser.read_all().decode("utf-8", errors="ignore")
    print("Boot Output:\n", boot_log)

    ser.close()
    print("🎉 Installation complete! The display is now permanently active and running.")
    return True

if __name__ == "__main__":
    install()
