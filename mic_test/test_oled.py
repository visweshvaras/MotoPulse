#!/usr/bin/env python3
"""
Interactive OLED Display Diagnostic & Mode Selector for ESP32-S3
Tests:
1. Standard SSD1306 128x64 (0.96" standard)
2. SH1106 128x64 (Common 1.3" and clone 0.96" with 2px offset)
3. SSD1306 128x32 (0.91" narrow display)
4. Screen Blink & All-White Flash Test
"""

import sys
import time
import serial

PORT = "/dev/ttyACM0"
BAUD = 115200

def get_code(mode="ssd1306_64"):
    return f"""
import machine, framebuf, time

i2c = machine.I2C(0, scl=machine.Pin(8), sda=machine.Pin(9), freq=100000)
devices = i2c.scan()
if 0x3C not in devices and 0x3D not in devices:
    print("NO_I2C_DEVICE")
    raise SystemExit

addr = 0x3C if 0x3C in devices else 0x3D
temp = bytearray(2)
temp[0] = 0x80

def write_cmd(c):
    temp[1] = c
    i2c.writeto(addr, temp)

mode = "{mode}"

if mode == "ssd1306_64":
    # Standard 128x64 SSD1306
    width, height = 128, 64
    pages = 8
    buf = bytearray(pages * width)
    fb = framebuf.FrameBuffer(buf, width, height, framebuf.MONO_VLSB)
    for c in (0xAE, 0xD5, 0x80, 0xA8, 63, 0xD3, 0x00, 0x40, 0x8D, 0x14,
              0x20, 0x00, 0xA1, 0xC8, 0xDA, 0x12, 0x81, 0xFF, 0xD9, 0xF1,
              0xDB, 0x40, 0xA4, 0xA6, 0xAF):
        write_cmd(c)
    
    # Draw content
    fb.fill(0)
    fb.rect(0, 0, 128, 64, 1)
    fb.fill_rect(2, 2, 124, 14, 1)
    fb.text("SSD1306 128x64", 8, 5, 0)
    fb.text("STATUS: SUCCESS", 4, 22, 1)
    fb.text("Contrast: 100%", 4, 36, 1)
    fb.text("I2C: 100 kHz", 4, 50, 1)
    
    write_cmd(0x21); write_cmd(0); write_cmd(127)
    write_cmd(0x22); write_cmd(0); write_cmd(7)
    write_list = [b'\\x40', buf]
    i2c.writevto(addr, write_list)
    print("MODE_RENDERED:ssd1306_64")

elif mode == "sh1106":
    # SH1106 128x64 (Page by page with 2px column offset)
    width, height = 128, 64
    pages = 8
    buf = bytearray(pages * width)
    fb = framebuf.FrameBuffer(buf, width, height, framebuf.MONO_VLSB)
    for c in (0xAE, 0xD5, 0x80, 0xA8, 63, 0xD3, 0x00, 0x40, 0xAD, 0x8B,
              0x30, 0x33, 0xA1, 0xC8, 0xDA, 0x12, 0x81, 0xFF, 0xD9, 0x22,
              0xDB, 0x40, 0xA4, 0xA6, 0xAF):
        write_cmd(c)
        
    fb.fill(0)
    fb.rect(0, 0, 128, 64, 1)
    fb.fill_rect(2, 2, 124, 14, 1)
    fb.text("SH1106 128x64", 12, 5, 0)
    fb.text("Page-by-Page Mode", 4, 22, 1)
    fb.text("Offset: 2px", 4, 36, 1)
    fb.text("Status: ONLINE", 4, 50, 1)
    
    # Write page by page (SH1106 RAM is 132x64, screen starts at column 2)
    for p in range(8):
        write_cmd(0xB0 + p)
        write_cmd(0x02) # column low = 2
        write_cmd(0x10) # column high = 0
        page_slice = buf[p * 128 : (p + 1) * 128]
        i2c.writevto(addr, [b'\\x40', page_slice])
    print("MODE_RENDERED:sh1106")

elif mode == "ssd1306_32":
    # 128x32 Narrow Display
    width, height = 128, 32
    pages = 4
    buf = bytearray(pages * width)
    fb = framebuf.FrameBuffer(buf, width, height, framebuf.MONO_VLSB)
    for c in (0xAE, 0xD5, 0x80, 0xA8, 31, 0xD3, 0x00, 0x40, 0x8D, 0x14,
              0x20, 0x00, 0xA1, 0xC8, 0xDA, 0x02, 0x81, 0xFF, 0xD9, 0xF1,
              0xDB, 0x40, 0xA4, 0xA6, 0xAF):
        write_cmd(c)
        
    fb.fill(0)
    fb.rect(0, 0, 128, 32, 1)
    fb.text("SSD1306 128x32", 8, 4, 1)
    fb.text("Narrow Screen OK", 4, 18, 1)
    
    write_cmd(0x21); write_cmd(0); write_cmd(127)
    write_cmd(0x22); write_cmd(0); write_cmd(3)
    write_list = [b'\\x40', buf]
    i2c.writevto(addr, write_list)
    print("MODE_RENDERED:ssd1306_32")

elif mode == "flash_all":
    # Light up every pixel white for 1 second, then invert
    for c in (0xAE, 0xD5, 0x80, 0xA8, 63, 0x8D, 0x14, 0x81, 0xFF, 0xA5, 0xAF):
        write_cmd(c)
    time.sleep(1.0)
    write_cmd(0xA4) # back to RAM
    print("MODE_RENDERED:flash_all")
"""

def run_test(mode):
    print(f"\n[Testing OLED mode: {mode}]...")
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
        ser.write(b'\r\x03\r\x03\r\x01')
        time.sleep(0.1)
        ser.read_all()
        
        code = get_code(mode)
        ser.write(code.encode() + b'\x04')
        time.sleep(0.4)
        out = ser.read_all().decode(errors='ignore')
        ser.write(b'\r\x02')
        ser.close()
        
        if "MODE_RENDERED:" in out:
            print(f"✔ Successfully sent '{mode}' test pattern to display.")
        elif "NO_I2C_DEVICE" in out:
            print("❌ No I2C display detected. Check GND, VCC, SCL (Pin 8), SDA (Pin 9).")
        else:
            print(f"Response: {out.strip()}")
    except Exception as e:
        print(f"Error: {e}")

def main():
    print("=" * 65)
    print("   📺 ESP32-S3 OLED DISPLAY DIAGNOSTIC & CALIBRATOR        ")
    print("   Finds the exact driver settings for your specific OLED   ")
    print("=" * 65)
    print("  1) Test Standard SSD1306 (128x64 - Standard 0.96\")")
    print("  2) Test SH1106 (128x64 - Common 1.3\" or Clone 0.96\")")
    print("  3) Test SSD1306 (128x32 - Narrow 0.91\")")
    print("  4) All-Pixels Hardware Flash Test (Forces all pixels white)")
    print("  5) Cycle through all 4 tests with 3s pauses")
    print("  6) Exit")
    print("=" * 65)
    
    choice = input("Select an option [1-6]: ").strip()
    if choice == "1":
        run_test("ssd1306_64")
    elif choice == "2":
        run_test("sh1106")
    elif choice == "3":
        run_test("ssd1306_32")
    elif choice == "4":
        run_test("flash_all")
    elif choice == "5":
        for m in ["flash_all", "ssd1306_64", "sh1106", "ssd1306_32"]:
            run_test(m)
            print("Look at the screen! Pausing 3 seconds...")
            time.sleep(3)
    else:
        print("Done.")

if __name__ == '__main__':
    main()
