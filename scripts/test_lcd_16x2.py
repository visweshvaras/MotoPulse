#!/usr/bin/env python3
"""
MotoPulse™ 16x2 I2C LCD Diagnostic & Verification Script for ESP32-S3
Scans I2C bus on SCL=GPIO 8, SDA=GPIO 9.
Tests standard PCF8574 I2C backpack addresses (0x27, 0x3F, 0x20..0x26).
Initializes HD44780 4-bit mode and displays live MotoPulse telemetry.
"""

import sys
import time
import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyACM0"
BAUD = 115200

TEST_SCRIPT = """
import machine, time

# 1. I2C Bus Initialization (SCL=8, SDA=9)
scl_rec = machine.Pin(8, machine.Pin.OUT)
for _ in range(9):
    scl_rec.value(0)
    time.sleep_us(5)
    scl_rec.value(1)
    time.sleep_us(5)

i2c = machine.I2C(0, scl=machine.Pin(8), sda=machine.Pin(9), freq=100000)
devs = i2c.scan()
print("I2C_SCAN:" + str([hex(d) for d in devs]))

lcd_addr = None
for candidate in [0x27, 0x3F, 0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x38, 0x39, 0x3A, 0x3B]:
    if candidate in devs:
        lcd_addr = candidate
        break

if not lcd_addr:
    print("NO_LCD_DETECTED")
    raise SystemExit

print("LCD_FOUND:" + hex(lcd_addr))

# HD44780 I2C PCF8574 Backpack Driver
class I2cLcd1602:
    def __init__(self, i2c, addr):
        self.i2c = i2c
        self.addr = addr
        self.backlight = 0x08  # Bit 3 = Backlight ON
        self.init_lcd()

    def write_nibble(self, nibble, rs=0):
        val = (nibble << 4) | self.backlight | rs
        # Pulse E (Enable = Bit 2) HIGH then LOW
        self.i2c.writeto(self.addr, bytearray([val | 0x04]))
        time.sleep_us(400)
        self.i2c.writeto(self.addr, bytearray([val & ~0x04]))
        time.sleep_us(100)

    def write_byte(self, byte, rs=0):
        self.write_nibble((byte >> 4) & 0x0F, rs)
        self.write_nibble(byte & 0x0F, rs)

    def cmd(self, c):
        self.write_byte(c, rs=0)
        if c in (0x01, 0x02):
            time.sleep_ms(2)

    def write_char(self, c):
        self.write_byte(ord(c), rs=1)

    def init_lcd(self):
        time.sleep_ms(50)
        # 4-bit standard HD44780 boot handshake
        for _ in range(3):
            self.write_nibble(0x03)
            time.sleep_ms(5)
        self.write_nibble(0x02) # Set 4-bit mode
        time.sleep_ms(2)

        self.cmd(0x28) # 2 lines, 5x8 dots
        self.cmd(0x0C) # Display ON, Cursor OFF
        self.cmd(0x06) # Auto increment
        self.clear()

    def clear(self):
        self.cmd(0x01)
        time.sleep_ms(2)

    def set_cursor(self, col, row):
        offsets = [0x00, 0x40]
        self.cmd(0x80 | (col + offsets[row % 2]))

    def print_str(self, s):
        for ch in s[:16]:
            self.write_char(ch)

    def set_line(self, row, text):
        self.set_cursor(0, row)
        # Pad to exactly 16 chars to clear trailing text
        padded = (text + " " * 16)[:16]
        self.print_str(padded)

lcd = I2cLcd1602(i2c, lcd_addr)
lcd.set_line(0, "MOTOPULSE AI")
lcd.set_line(1, "16x2 LCD ACTIVE!")
print("TEST_DISPLAY_OK")

# Run a brief test counter for 10 seconds
for sec in range(10):
    time.sleep_ms(1000)
    lcd.set_line(0, "MOTOPULSE  [RUN]")
    lcd.set_line(1, "HEALTH:GOOD " + str(sec) + "s")

lcd.set_line(0, "MOTOPULSE [IDLE]")
lcd.set_line(1, "DIAGNOSTIC READY")
"""

def main():
    print("=" * 70)
    print("   📟 MOTOPULSE™ 16x2 I2C LCD HARDWARE VERIFICATION")
    print("   Wiring: GND->GND | VCC->5V | SDA->GPIO 9 | SCL->GPIO 8")
    print("=" * 70)
    print(f"Connecting to ESP32-S3 on {PORT}...")

    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
    except Exception as e:
        print(f"[ERROR] Cannot open {PORT}: {e}")
        print("Run: sudo chmod 666 /dev/ttyACM0")
        sys.exit(1)

    # Enter raw REPL
    ser.write(b'\r\x03\r\x03\r\x01')
    time.sleep(0.2)
    ser.read_all()

    print("Injecting HD44780 I2C 16x2 LCD test sequence...")
    ser.write(TEST_SCRIPT.encode('utf-8') + b'\x04')

    t0 = time.time()
    while time.time() - t0 < 6.0:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if not line:
            continue
        print(f"ESP32 >> {line}")
        if "NO_LCD_DETECTED" in line:
            print("\n❌ NO 16x2 LCD DETECTED ON I2C BUS!")
            print("Please check wiring:")
            print("  • GND -> ESP32 GND")
            print("  • VCC -> ESP32 5V (or VIN) pin (16x2 LCDs need 5V for backlight/contrast)")
            print("  • SDA -> ESP32 GPIO 9")
            print("  • SCL -> ESP32 GPIO 8")
            print("  • If backlight turns ON but screen is blank: TURN THE BLUE POTENTIOMETER on the back of the LCD with a small screwdriver to adjust contrast!")
            break
        elif "TEST_DISPLAY_OK" in line:
            print("\n🎉 SUCCESS! 16x2 I2C LCD is working and displaying live MotoPulse text!")
            break

    ser.close()

if __name__ == "__main__":
    main()
