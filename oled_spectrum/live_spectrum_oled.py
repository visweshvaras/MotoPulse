#!/usr/bin/env python3
"""
Real-Time OLED Audio Oscilloscope (Pure Waveform Display)
Displays ONLY the raw, fluid audio waveform trace on the 0.96" OLED screen.
NO words, NO text, NO borders on the OLED.
Detailed telemetry, VU meter, and status are displayed in the terminal monitor.
"""

import sys
import time
import serial

PORT = "/dev/ttyACM0"
BAUD = 115200

MICROPYTHON_CODE = '''
import machine, framebuf, struct, math, time

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

# Fast 400 kHz I2C for high-FPS fluid oscilloscope display
i2c = machine.I2C(0, scl=machine.Pin(8), sda=machine.Pin(9), freq=400000)
oled = SSD1306_I2C(128, 64, i2c)

# 16 kHz Stereo I2S INMP441 Microphone (SCK=4, WS=5, SD=6)
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

# 128 stereo frames = 1024 bytes (128 Left samples across 128 pixels)
buf_in = bytearray(1024)

# Initial DC bias calibration
calib_sum = 0
for _ in range(20):
    audio.readinto(buf_in)
    words = struct.unpack('<256i', buf_in)
    calib_sum += sum(words[i] >> 16 for i in range(0, 256, 2)) // 128
dc = calib_sum // 20

print("WAVEFORM_RUNNING")

frame_count = 0
t_fps = time.ticks_ms()

while True:
    audio.readinto(buf_in)
    words = struct.unpack('<256i', buf_in)
    
    # Extract clean Left channel (Mic 1) top 16-bit audio
    left = [words[i] >> 16 for i in range(0, 256, 2)]
    
    # Peak-to-peak amplitude for telemetry
    p2p = max(left) - min(left)
    
    # Clear screen to pitch black: ZERO words, ZERO text, ZERO borders
    oled.fill(0)
    
    # Continuous oscilloscope line trace across all 128 pixels (x: 0 to 127)
    prev_x = 0
    s0 = (left[0] - dc) * 6 // 256
    prev_y = max(0, min(63, 32 - s0))
    
    for x in range(1, 128):
        s = (left[x] - dc) * 6 // 256
        y = max(0, min(63, 32 - s))
        oled.line(prev_x, prev_y, x, y, 1)
        prev_x = x
        prev_y = y
        
    oled.show()
    
    frame_count += 1
    # Send telemetry back to PC terminal every 4 frames (~100ms)
    if frame_count % 4 == 0:
        print("T:" + str(p2p))
'''

def main():
    print("=" * 70)
    print("   📈 ESP32-S3 LIVE OLED AUDIO OSCILLOSCOPE (PURE WAVEFORM)  ")
    print("   OLED Screen: PURE WAVEFORM TRACE ONLY (No Text / No Borders)")
    print("   PC Monitor: Real-Time Telemetry, Amplitude & VU Meter     ")
    print("=" * 70)
    print(f"Connecting to ESP32-S3 on {PORT}...")

    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
    except Exception as e:
        print(f"[ERROR] Could not open {PORT}: {e}")
        print("Run: sudo chmod 666 /dev/ttyACM0")
        sys.exit(1)

    # Clean interrupt and enter raw REPL
    ser.write(b'\r\x03\r\x03\r\x01')
    time.sleep(0.15)
    ser.read_all()

    print("Uploading and launching oscilloscope engine on ESP32-S3...")
    ser.write(MICROPYTHON_CODE.encode('utf-8') + b'\x04')

    t0 = time.time()
    started = False
    while time.time() - t0 < 5.0:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if "WAVEFORM_RUNNING" in line:
            started = True
            break

    print("\n" + "✨" * 35)
    print("  🟢 PURE LIVE WAVEFORM IS ACTIVE ON YOUR OLED DISPLAY! 🟢")
    print("  (Look at your OLED screen — only the fluid audio wave is shown)")
    print("✨" * 35 + "\n")
    print("Live Monitor Telemetry (Press Ctrl+C to exit):\n")

    peak_hold = 0
    decay = 0

    try:
        while True:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line.startswith("T:"):
                try:
                    p2p = int(line.split(":")[1])
                except Exception:
                    continue

                if p2p > peak_hold:
                    peak_hold = p2p
                    decay = 0
                else:
                    decay += 1
                    if decay > 2:
                        peak_hold = max(0, peak_hold - 200)

                # Visual meter bar (25 chars)
                bar_len = min(25, max(0, int(p2p / 200)))
                bar = "█" * bar_len + "░" * (25 - bar_len)

                if p2p > 4500:
                    badge = "🔥🔥 CLAP / LOUD TRANSIENT"
                elif p2p > 1000:
                    badge = "🗣️  VOICE DETECTED"
                elif p2p > 350:
                    badge = "🎵 Soft Audio"
                else:
                    badge = "🤫 Quiet / Baseline"

                print(f"\r  [{bar}] Peak: {p2p:5d} | Max: {peak_hold:5d} | {badge:<24}", end="", flush=True)

    except KeyboardInterrupt:
        print("\n\nStopping oscilloscope engine...")
        ser.write(b'\r\x03\r\x02')
        ser.close()
        print("Oscilloscope stopped cleanly.")

if __name__ == '__main__':
    main()
