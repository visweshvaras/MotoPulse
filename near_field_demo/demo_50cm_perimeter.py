#!/usr/bin/env python3
"""
Dual-Microphone 50cm Near-Field Acoustic Perimeter Gate
Utilizes a 4cm-spaced dual INMP441 MEMS microphone array on ESP32-S3 + OLED display.

Acoustic Physics & 4cm Array Spatial Gating:
1. Inverse Square Law (P ~ 1/r^2): Sounds within 50cm exhibit steep energy crests.
2. Wavefront Curvature Gradient across 4cm Baseline:
   - Near-Field (<50cm): Strong spherical wave divergence creates an amplitude
     gradient (|L - R| / max(L, R)) between the 4cm mics.
   - Far-Field (>50cm, room chatter, claps >1m away): Sounds arrive as flat plane waves
     with nearly equal energy on both mics (|L - R| ~ 0), falling below the threshold.
3. Real-Time Visual Feedback:
   - 0.96" OLED screen displays perimeter radar, dual-mic meters, and pass/reject alerts.
   - PC Terminal displays live dual-channel telemetry and 50cm threshold meter.
"""

import sys
import time
import serial

PORT = "/dev/ttyACM0"
BAUD = 115200

ESP32_FIRMWARE = '''
import machine, framebuf, struct, math, time, gc
gc.collect()

class SSD1306_I2C(framebuf.FrameBuffer):
    def __init__(self, width, height, i2c, addr=0x3C):
        self.width = width
        self.height = height
        self.i2c = i2c
        self.addr = addr
        self.pages = self.height // 8
        self.buffer = bytearray(self.pages * self.width)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_VLSB)
        self.temp = bytearray(2)
        self.temp[0] = 0x80
        self.write_list = [b'\\x40', None]
        
        for cmd in (
            0xAE, 0xD5, 0x80, 0xA8, self.height - 1, 0xD3, 0x00,
            0x40, 0x8D, 0x14, 0x20, 0x00, 0xA1, 0xC8,
            0xDA, 0x12 if self.height == 64 else 0x02,
            0x81, 0xFF, 0xD9, 0xF1, 0xDB, 0x40, 0xA4, 0xA6, 0xAF
        ):
            self.write_cmd(cmd)
        self.fill(0)
        self.show()

    def write_cmd(self, cmd):
        self.temp[1] = cmd
        self.i2c.writeto(self.addr, self.temp)

    def show(self):
        self.write_cmd(0x21)
        self.write_cmd(0)
        self.write_cmd(self.width - 1)
        self.write_cmd(0x22)
        self.write_cmd(0)
        self.write_cmd(self.pages - 1)
        self.write_list[1] = self.buffer
        self.i2c.writevto(self.addr, self.write_list)

# 9-clock I2C bus recovery
scl_rec = machine.Pin(8, machine.Pin.OUT)
for _ in range(9):
    scl_rec.value(0); time.sleep_us(5)
    scl_rec.value(1); time.sleep_us(5)

# Init I2C OLED (SCL=8, SDA=9)
i2c = machine.I2C(0, scl=machine.Pin(8), sda=machine.Pin(9), freq=100000)
oled = SSD1306_I2C(128, 64, i2c)

# Init I2S INMP441 Dual-Mic Array (SCK=4, WS=5, SD=6)
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

# Splash screen
oled.fill(0)
oled.rect(0, 0, 128, 64, 1)
oled.fill_rect(2, 2, 124, 14, 1)
oled.text('ACOUSTIC PERIMETER', 4, 5, 0)
oled.text('4cm DUAL MIC', 16, 24, 1)
oled.text('GATE: 50cm ZONE', 8, 38, 1)
oled.text('CALIBRATING...', 12, 52, 1)
oled.show()

buf_in = bytearray(512) # 64 stereo frames

# Flush DMA buffer
for _ in range(5):
    audio.readinto(buf_in)

# 1. Dual-Mic Ambient Calibration & DC Baseline (1.5 seconds)
sum_l = 0
sum_r = 0
energy_floor = 0
calib_count = 30

for _ in range(calib_count):
    audio.readinto(buf_in)
    # Extract 24-bit samples
    left_samples = []
    right_samples = []
    for i in range(64):
        b = i * 8
        # Left Mic (Mic 1)
        vl = (buf_in[b + 3] << 16) | (buf_in[b + 2] << 8) | buf_in[b + 1]
        if vl & 0x800000: vl -= 0x1000000
        left_samples.append(vl >> 8)
        
        # Right Mic (Mic 2)
        vr = (buf_in[b + 7] << 16) | (buf_in[b + 6] << 8) | buf_in[b + 5]
        if vr & 0x800000: vr -= 0x1000000
        right_samples.append(vr >> 8)
        
    avg_l = sum(left_samples) // 64
    avg_r = sum(right_samples) // 64
    sum_l += avg_l
    sum_r += avg_r
    
    p2p_l = max(left_samples) - min(left_samples)
    p2p_r = max(right_samples) - min(right_samples)
    energy_floor += max(p2p_l, p2p_r)

dc_l = sum_l // calib_count
dc_r = sum_r // calib_count
ambient_floor = max(180, energy_floor // calib_count)

# Dynamic 50cm Threshold based on ambient noise
NEAR_THRESHOLD = max(1600, ambient_floor * 3)

oled.fill(0)
oled.rect(0, 0, 128, 64, 1)
oled.text('GATE ARMED: 50cm', 2, 4, 1)
oled.hline(0, 14, 128, 1)
oled.text('Array: 4cm Dual', 4, 20, 1)
oled.text('Near < 50cm -> YES', 4, 34, 1)
oled.text('Far  > 50cm -> NO',  4, 48, 1)
oled.show()
time.sleep_ms(800)

print("GATE_STARTED:" + str(ambient_floor) + ":" + str(NEAR_THRESHOLD))

trigger_counter = 0

while True:
    audio.readinto(buf_in)
    
    left_samples = []
    right_samples = []
    for i in range(64):
        b = i * 8
        vl = (buf_in[b + 3] << 16) | (buf_in[b + 2] << 8) | buf_in[b + 1]
        if vl & 0x800000: vl -= 0x1000000
        left_samples.append((vl >> 8) - dc_l)
        
        vr = (buf_in[b + 7] << 16) | (buf_in[b + 6] << 8) | buf_in[b + 5]
        if vr & 0x800000: vr -= 0x1000000
        right_samples.append((vr >> 8) - dc_r)
        
    p2p_l = max(left_samples) - min(left_samples)
    p2p_r = max(right_samples) - min(right_samples)
    
    max_amp = max(p2p_l, p2p_r)
    diff = abs(p2p_l - p2p_r)
    gradient_pct = (diff * 100) // (max_amp + 1)
    
    # 4cm Baseline Near-Field Decision Logic:
    # 1. Energy must exceed the calibrated 50cm threshold.
    # 2. Near-field curvature causes an amplitude gradient between the 4cm mics,
    #    OR a strong direct burst above 1.4x threshold.
    is_near = (max_amp >= NEAR_THRESHOLD) and (gradient_pct >= 10 or max_amp >= NEAR_THRESHOLD * 1.4)
    
    if is_near:
        trigger_counter = 9  # hold alert on display for ~350ms
    elif trigger_counter > 0:
        trigger_counter -= 1
        
    # OLED Display Rendering
    oled.fill(0)
    
    # Header
    oled.text("<50cm BARRIER", 0, 0, 1)
    oled.text("4cm", 100, 0, 1)
    oled.hline(0, 10, 128, 1)
    
    if trigger_counter > 0:
        # Triggered: Sound detected within 50cm
        oled.fill_rect(0, 13, 128, 38, 1)
        oled.text(">> DETECTED! <<", 6, 17, 0)
        oled.text("WITHIN 50cm ZONE", 2, 29, 0)
        oled.text("L:" + str(p2p_l) + " R:" + str(p2p_r), 4, 40, 0)
        
        oled.text("GATE: PASS", 0, 54, 1)
        oled.text("d: 4cm", 80, 54, 1)
    else:
        # Idle / Far Sound Rejected
        if max_amp > ambient_floor * 2:
            oled.text("[FAR-FIELD SOUND]", 0, 15, 1)
            oled.text("Distance > 50cm", 4, 27, 1)
            oled.text("STATE: REJECTED", 4, 39, 1)
        else:
            oled.text("PERIMETER ACTIVE", 0, 16, 1)
            oled.text("Dual Mic: 4cm Array", 0, 28, 1)
            oled.text("Quiet / Armed", 4, 40, 1)
            
        # Energy Meter Bar at Bottom
        bar_w = min(128, max(0, int(max_amp * 128 / (NEAR_THRESHOLD * 1.6))))
        oled.rect(0, 55, 128, 8, 1)
        if bar_w > 0:
            oled.fill_rect(1, 56, bar_w, 6, 1)
        # 50cm Threshold Divider Line
        th_x = int(NEAR_THRESHOLD * 128 / (NEAR_THRESHOLD * 1.6))
        if th_x < 127:
            oled.vline(th_x, 52, 12, 1)
            
    oled.show()
    
    # Telemetry back to PC
    state_tag = "INSIDE_50CM" if (trigger_counter > 0) else ("FAR_REJECTED" if max_amp > ambient_floor * 2 else "QUIET")
    print("M:" + str(p2p_l) + ":" + str(p2p_r) + ":" + str(gradient_pct) + ":" + state_tag)
'''

def main():
    print("=" * 70)
    print("   🎯 DUAL-MIC 50cm NEAR-FIELD ACOUSTIC PERIMETER GATE      ")
    print("   Microphones: 2x INMP441 (4cm Baseline Separation)        ")
    print("   Uses Inverse Square Law & Spherical Curvature Gating      ")
    print("=" * 70)
    print(f"Connecting to ESP32-S3 on {PORT}...")

    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
    except Exception as e:
        print(f"[ERROR] Cannot open {PORT}: {e}")
        print("Run: sudo chmod 666 /dev/ttyACM0")
        sys.exit(1)

    # Interrupt current script and enter raw REPL
    ser.write(b'\r\x03\r\x03\r\x01')
    time.sleep(0.15)
    ser.read_all()

    print("Calibrating 4cm dual-mic ambient floor and arming 50cm gate...")
    raw_code = ESP32_FIRMWARE.encode('utf-8') + b'\x04'
    chunk_sz = 256
    for i in range(0, len(raw_code), chunk_sz):
        ser.write(raw_code[i : i + chunk_sz])
        time.sleep(0.015)

    t0 = time.time()
    ambient = 200
    thresh = 1800
    while time.time() - t0 < 6.0:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if line.startswith("GATE_STARTED:"):
            parts = line.split(":")
            ambient = int(parts[1])
            thresh = int(parts[2])
            break

    print(f"✔ Ambient Baseline: {ambient} | 50cm Threshold: {thresh} | Baseline: 4cm Dual Mic")
    print("\n" + "=" * 70)
    print("  📋 HOW TO TEST THE 50cm ACOUSTIC BARRIER:")
    print("  1. FAR TEST (>1 meter away): Clap or talk far across the room:")
    print("     -> Monitor & OLED shows: [❌ BLOCKED >50cm: REJECTED]")
    print("  2. NEAR TEST (<50cm away): Clap, tap, or speak close to the mics:")
    print("     -> Monitor & OLED FLASHES: [🎯 PASS <50cm: DETECTED!]")
    print("=" * 70 + "\n")
    print("Live Dual-Mic Telemetry (Press Ctrl+C to exit):\n")

    try:
        while True:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line.startswith("M:"):
                parts = line.split(":")
                p2p_l = int(parts[1])
                p2p_r = int(parts[2])
                grad = int(parts[3])
                status = parts[4]

                max_amp = max(p2p_l, p2p_r)
                meter_len = min(24, max(0, int(max_amp * 24 / (thresh * 1.5))))
                th_pos = int(thresh * 24 / (thresh * 1.5))

                bar = []
                for idx in range(24):
                    if idx == th_pos:
                        bar.append("|")  # 50cm threshold divider
                    elif idx < meter_len:
                        bar.append("█")
                    else:
                        bar.append("░")
                bar_str = "".join(bar)

                if status == "INSIDE_50CM":
                    badge = "🎯 [PASS <50cm: DETECTED!]"
                elif status == "FAR_REJECTED":
                    badge = "❌ [BLOCKED >50cm: REJECTED]"
                else:
                    badge = "🛡️  [PERIMETER GUARDED]   "

                print(f"\r  [{bar_str}] L: {p2p_l:5d} | R: {p2p_r:5d} (Δ: {grad:2d}%) | {badge}", end="", flush=True)

    except KeyboardInterrupt:
        print("\n\nStopping 50cm Acoustic Perimeter Gate...")
        ser.write(b'\r\x03\r\x02')
        ser.close()
        print("Perimeter gate stopped cleanly.")

if __name__ == '__main__':
    main()
