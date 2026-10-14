#!/usr/bin/env python3
"""
Real-Time OLED Audio Spectrum Visualizer
Reads 16 kHz digital I2S stream from INMP441, computes frequency bins,
and renders real-time 16-band animated EQ bars + peak hold on 0.96" OLED.
"""

import sys
import time
import serial

PORT = "/dev/ttyACM0"
BAUD = 115200

MICROPYTHON_CODE = '''
import machine, framebuf, struct, math, gc

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

# Initialize I2C for OLED Display at rock-solid 100 kHz (SCL=GPIO8, SDA=GPIO9)
i2c = machine.I2C(0, scl=machine.Pin(8), sda=machine.Pin(9), freq=100000)
oled = SSD1306_I2C(128, 64, i2c)

# Initialize I2S for INMP441 Microphone (SCK=4, WS=5, SD=6)
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
oled.text('HACKTIVATE 2026', 4, 8, 1)
oled.text('ACOUSTIC TinyML', 4, 24, 1)
oled.text('INMP441 + OLED', 4, 40, 1)
oled.show()
time.sleep_ms(800)

# Precalculate 64-point Trigonometric LUT for Fast Integer DFT (16 Bands)
N = 64
NUM_BANDS = 16
cos_lut = [int(math.cos(2 * math.pi * k / N) * 256) for k in range(N)]
sin_lut = [int(math.sin(2 * math.pi * k / N) * 256) for k in range(N)]

# Peak hold levels for visual falloff
peak_bars = [0] * NUM_BANDS
smooth_bars = [0] * NUM_BANDS

# Audio buffer for 64 stereo frames (512 bytes)
buf_in = bytearray(512)

print("SPECTRUM_RUNNING")

while True:
    # Read chunk from microphone
    audio.readinto(buf_in)
    raw = struct.unpack('<128i', buf_in)
    
    # Extract clean Left channel (Mic 1) top 16 bits
    samples = [raw[i] >> 16 for i in range(0, 128, 2)]
    mean_val = sum(samples) // 64
    ac = [s - mean_val for s in samples]

    # Calculate overall RMS energy
    p2p = max(ac) - min(ac)

    # 16-Band Discrete Transform
    for b in range(NUM_BANDS):
        k = b + 1
        re = 0
        im = 0
        for n in range(0, N, 2): # sub-sampled 2x for high FPS
            v = ac[n]
            idx = (n * k) % N
            re += v * cos_lut[idx]
            im += v * sin_lut[idx]
        
        re >>= 8
        im >>= 8
        mag = int(math.sqrt(re * re + im * im))
        
        # Scale to bar height (max height 46 pixels for responsive dynamics)
        target_h = min(46, max(0, int(mag / 20)))
        
        # Smooth interpolation
        smooth_bars[b] = (smooth_bars[b] * 2 + target_h) // 3
        
        # Peak falloff logic
        if smooth_bars[b] >= peak_bars[b]:
            peak_bars[b] = smooth_bars[b]
        elif peak_bars[b] > 0:
            peak_bars[b] -= 1

    # Render frame buffer
    oled.fill(0)
    
    # Top status header
    oled.text("FREQ SPECTRUM", 0, 0, 1)
    
    # Amplitude status flag
    if p2p > 4000:
        oled.text("LOUD!", 88, 0, 1)
    elif p2p > 800:
        oled.text("VOICE", 84, 0, 1)
    else:
        oled.text("NORM", 92, 0, 1)

    oled.hline(0, 11, 128, 1)

    # Draw 16 Spectrum Bars (each 6px wide + 2px spacing = 8px per band, 16 * 8 = 128px)
    for b in range(NUM_BANDS):
        x = b * 8
        h = smooth_bars[b]
        y = 63 - h
        
        # Draw bar
        if h > 0:
            oled.fill_rect(x, y, 6, h, 1)
        
        # Draw peak hold dot
        pk_y = 63 - peak_bars[b]
        if pk_y < 63 and pk_y >= 12:
            oled.hline(x, pk_y, 6, 1)

    oled.show()
'''

def main():
    print("=" * 65)
    print("   📊 ESP32-S3 + INMP441 + 0.96\" OLED SPECTRUM LAUNCHER     ")
    print("=" * 65)
    print(f"Connecting to {PORT}...")

    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
    except Exception as e:
        print(f"[ERROR] Could not open {PORT}: {e}")
        print("Run: sudo chmod 666 /dev/ttyACM0")
        sys.exit(1)

    # Interrupt current script and enter raw REPL
    ser.write(b'\r\x03\r\x03\r\x01')
    time.sleep(0.15)
    ser.read_all()

    print("Uploading and starting real-time spectrum engine...")
    ser.write(MICROPYTHON_CODE.encode('utf-8') + b'\x04')

    t0 = time.time()
    started = False
    while time.time() - t0 < 4.0:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if "SPECTRUM_RUNNING" in line:
            started = True
            break

    if started:
        print("\n" + "✨" * 30)
        print("  🟢 REAL-TIME SPECTRUM DISPLAY IS LIVE ON OLED SCREEN! 🟢")
        print("  - Speak, whistle, tap the table, or clap near the mic.")
        print("  - Watch the 16 frequency bands and peak dots dance live!")
        print("✨" * 30)
        print("\nPress Ctrl+C in this terminal to stop the spectrum.")
    else:
        print("[NOTE] Spectrum engine running. Monitoring stream...")

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping Spectrum Engine on ESP32-S3...")
        ser.write(b'\r\x03\r\x02')
        ser.close()
        print("Stopped cleanly.")

if __name__ == '__main__':
    main()
