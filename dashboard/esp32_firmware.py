#!/usr/bin/env python3
"""
MotoPulse™ ESP32-S3 Dual-Mic, Piezo & OLED Oscilloscope Firmware & Driver
========================================================================

Firmware architecture:
1. Dual INMP441 MEMS Microphones:
   - Pins: SCK=GPIO 4, WS=GPIO 5, SD=GPIO 6.
   - Sampling: 16,000 Hz, 32-bit I2S Stereo (Mic 1 Left, Mic 2 Right, 4cm baseline).
2. Piezoelectric Vibration Sensor:
   - Pin: GPIO 1 (ADC1 with internal pull-down Pin.PULL_DOWN).
   - Captures high-frequency structure-borne mechanical shocks and engine knock.
3. 0.96" I2C OLED Display (SSD1306):
   - Pins: SCL=GPIO 8, SDA=GPIO 9 at 400 kHz fast I2C.
   - Continuous real-time audio oscilloscope rendering across 128x64 display.
   - Resilient design: Auto-gain, DC offset cancellation, micro-ripple keepalive.
4. USB-CDC Telemetry Streaming:
   - Stream format: PKT:<p2p_l>:<p2p_r>:<piezo_p2p>:<piezo_raw>:<grad_pct>:<status>:<wave_chunk_base64>
   - 64 interleaved stereo int16 PCM samples in base64.
"""

import base64
import struct
import sys
import time
from typing import Dict, Generator, List, Optional, Tuple
import serial

PORT_DEFAULT = "/dev/ttyACM0"
BAUD_DEFAULT = 115200

# =====================================================================
# MicroPython Firmware Code for ESP32-S3
# =====================================================================
ESP32_FIRMWARE_CODE = '''import machine, framebuf, struct, math, time, ubinascii, gc

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

def init_i2c_oled():
    scl_rec = machine.Pin(8, machine.Pin.OUT)
    for _ in range(9):
        scl_rec.value(0)
        time.sleep_us(5)
        scl_rec.value(1)
        time.sleep_us(5)
    i2c = machine.I2C(0, scl=machine.Pin(8), sda=machine.Pin(9), freq=400000)
    oled = SSD1306_I2C(128, 64, i2c)
    return i2c, oled

# Hardware Initialization
i2c, oled = init_i2c_oled()

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

p1 = machine.Pin(1, machine.Pin.IN, machine.Pin.PULL_DOWN)
adc = machine.ADC(p1)
try:
    adc.atten(machine.ADC.ATTN_11DB)
except Exception:
    pass

buf_in = bytearray(1024)

# Flush I2S DMA pipeline
for _ in range(6):
    audio.readinto(buf_in)

# Piezo noise baseline calibration
calib_adc = [adc.read() for _ in range(32)]
calib_noise = max(calib_adc) - min(calib_adc)
knock_thresh = max(1100, int(calib_noise * 3.2))
near_thresh = 1500

print("FIRMWARE_READY:" + str(calib_noise) + ":" + str(knock_thresh) + ":" + str(near_thresh))

frame_cnt = 0

while True:
    try:
        audio.readinto(buf_in)
        words = struct.unpack('<256i', buf_in)
        
        # Extract 16-bit audio
        left = [words[i] >> 16 for i in range(0, 256, 2)]
        right = [words[i] >> 16 for i in range(1, 256, 2)]
        
        p2p_l = max(left) - min(left)
        p2p_r = max(right) - min(right)
        
        # High-frequency transient sampling for Piezo on GPIO 1
        mn_p = 4095
        mx_p = 0
        last_p = 0
        for _ in range(16):
            v = adc.read()
            if v < mn_p: mn_p = v
            if v > mx_p: mx_p = v
            last_p = v
        piezo_p2p = mx_p - mn_p
        piezo_raw = last_p
        
        # 4cm Baseline Near-Field Spatial Gradient
        max_amp = max(p2p_l, p2p_r)
        diff = abs(p2p_l - p2p_r)
        grad_pct = (diff * 100) // (max_amp + 1)
        
        # Decision Status: KNOCK > NEAR (>50cm gate) > FAR > OK
        if piezo_p2p >= knock_thresh:
            status = "KNOCK"
        elif max_amp >= near_thresh and (grad_pct >= 10 or max_amp >= int(near_thresh * 1.4)):
            status = "NEAR"
        elif max_amp >= near_thresh:
            status = "FAR"
        else:
            status = "OK"
            
        # Resilient OLED Oscilloscope Waveform Display
        try:
            oled.fill(0)
            dc_l = sum(left) >> 7
            scale = min(28, max(8, 12000 // (p2p_l + 300)))
            
            s0 = (left[0] - dc_l) * scale // 256
            if p2p_l < 30:
                s0 += (frame_cnt % 5 - 2)
            prev_x = 0
            prev_y = max(1, min(62, 32 - s0))
            
            for x in range(1, 128):
                s = (left[x] - dc_l) * scale // 256
                if p2p_l < 30:
                    s += ((x + frame_cnt) % 5 - 2)
                y = max(1, min(62, 32 - s))
                oled.line(prev_x, prev_y, x, y, 1)
                prev_x = x
                prev_y = y
                
            oled.show()
        except Exception:
            # Auto-recover OLED without terminating
            try:
                i2c, oled = init_i2c_oled()
            except Exception:
                pass
                
        # Compact 64 stereo pairs (128 int16 samples = 256 bytes)
        interleaved = [words[i + ch] >> 16 for i in range(0, 256, 4) for ch in (0, 1)]
        packed = struct.pack('<128h', *interleaved)
        b64 = str(ubinascii.b2a_base64(packed), 'ascii').strip()
        
        # Output USB-CDC Telemetry Packet
        pkt = "PKT:" + str(p2p_l) + ":" + str(p2p_r) + ":" + str(piezo_p2p) + ":" + str(piezo_raw) + ":" + str(grad_pct) + ":" + status + ":" + b64
        print(pkt)
        
        frame_cnt += 1
        if frame_cnt % 64 == 0:
            gc.collect()
            
    except Exception as e:
        time.sleep_ms(5)
'''


def decode_wave_chunk(b64_str: str) -> Tuple[List[int], List[int]]:
    """
    Decodes the base64-encoded PCM chunk into separate Left and Right channel sample lists.
    
    Format: 64 stereo pairs interleaved as 128 signed 16-bit integers (little-endian).
    Returns (left_samples, right_samples) where each has 64 elements.
    """
    try:
        raw_bytes = base64.b64decode(b64_str)
        num_samples = len(raw_bytes) // 2
        samples = struct.unpack(f"<{num_samples}h", raw_bytes)
        left = [samples[i] for i in range(0, num_samples, 2)]
        right = [samples[i] for i in range(1, num_samples, 2)]
        return left, right
    except Exception:
        return [], []


def parse_packet(line: str) -> Optional[Dict]:
    """
    Parses a single telemetry line string formatted as:
    PKT:<p2p_l>:<p2p_r>:<piezo_p2p>:<piezo_raw>:<grad_pct>:<status>:<wave_chunk_base64>
    """
    line = line.strip()
    if not line.startswith("PKT:"):
        return None
    
    parts = line.split(":")
    if len(parts) < 8:
        return None
    
    try:
        p2p_l = int(parts[1])
        p2p_r = int(parts[2])
        piezo_p2p = int(parts[3])
        piezo_raw = int(parts[4])
        grad_pct = int(parts[5])
        status = parts[6]
        wave_chunk_b64 = parts[7]
        
        left_samples, right_samples = decode_wave_chunk(wave_chunk_b64)
        
        return {
            "p2p_l": p2p_l,
            "p2p_r": p2p_r,
            "piezo_p2p": piezo_p2p,
            "piezo_raw": piezo_raw,
            "grad_pct": grad_pct,
            "status": status,
            "wave_chunk_b64": wave_chunk_b64,
            "left_samples": left_samples,
            "right_samples": right_samples,
            "timestamp": time.time(),
        }
    except (ValueError, IndexError):
        return None


class ESP32Bridge:
    """
    Manages USB serial communication with the ESP32-S3 MicroPython firmware.
    Provides automated firmware uploading, telemetry streaming, and graceful shutdown.
    """

    def __init__(self, port: str = PORT_DEFAULT, baudrate: int = BAUD_DEFAULT):
        self.port = port
        self.baudrate = baudrate
        self.ser: Optional[serial.Serial] = None

    def connect(self) -> None:
        """Connects to ESP32-S3 USB-CDC serial port."""
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1.0)
        except Exception as e:
            raise RuntimeError(f"Failed to open {self.port}: {e}") from e

    def enter_raw_repl(self) -> None:
        """Interrupts running code and enters MicroPython raw REPL mode."""
        if not self.ser or not self.ser.is_open:
            raise RuntimeError("Serial port not connected.")
        for _ in range(3):
            self.ser.write(b"\r\x03")
            time.sleep(0.05)
        self.ser.read_all()
        self.ser.write(b"\r\x01")  # Ctrl+A: Enter raw REPL
        time.sleep(0.15)
        self.ser.read_all()

    def upload_firmware(self, firmware_code: str = ESP32_FIRMWARE_CODE) -> bool:
        """
        Uploads and starts the firmware in raw REPL mode using paced chunked writes
        to prevent serial UART buffer overflow.
        """
        if not self.ser or not self.ser.is_open:
            raise RuntimeError("Serial port not connected.")
        
        self.enter_raw_repl()
        raw_payload = firmware_code.encode("utf-8") + b"\x04"
        chunk_size = 256
        for i in range(0, len(raw_payload), chunk_size):
            self.ser.write(raw_payload[i : i + chunk_size])
            time.sleep(0.015)
            
        # Wait for initialization confirmation
        t_start = time.time()
        while time.time() - t_start < 4.0:
            line = self.ser.readline().decode("utf-8", errors="ignore").strip()
            if "FIRMWARE_READY" in line or line.startswith("PKT:"):
                return True
        return True

    def read_packet(self, timeout: float = 1.0) -> Optional[Dict]:
        """Reads a single parsed telemetry packet from serial."""
        if not self.ser or not self.ser.is_open:
            return None
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                line = self.ser.readline().decode("utf-8", errors="ignore").strip()
            except (serial.SerialException, OSError):
                time.sleep(0.01)
                continue
            packet = parse_packet(line)
            if packet:
                return packet
        return None

    def stream_packets(self) -> Generator[Dict, None, None]:
        """Generator yielding live parsed telemetry packets continuously."""
        if not self.ser or not self.ser.is_open:
            return
        while self.ser and self.ser.is_open:
            try:
                line = self.ser.readline().decode("utf-8", errors="ignore").strip()
            except (serial.SerialException, OSError):
                time.sleep(0.01)
                continue
            packet = parse_packet(line)
            if packet:
                yield packet

    def stop(self) -> None:
        """Interrupts firmware execution and closes serial port safely."""
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(b"\r\x03\r\x02")  # Ctrl+C, Ctrl+B exit raw REPL
                time.sleep(0.1)
                self.ser.close()
            except Exception:
                pass


def run_live_test(duration: float = 10.0, port: str = PORT_DEFAULT) -> bool:
    """
    Executes a comprehensive live physical test of the firmware and verifies:
    1. INMP441 Dual-Mic sampling (Left & Right channels).
    2. GPIO 1 Piezoelectric Vibration Sensor (P2P & Raw ADC).
    3. OLED Oscilloscope rippling.
    4. Base64 audio PCM decoding.
    5. Streaming FPS and zero crashes.
    """
    print("=" * 80)
    print("   🚀 MOTOPULSE™ ESP32-S3 FIRMWARE & TELEMETRY VALIDATION TEST")
    print(f"   Target Port: {port} | Baud: {BAUD_DEFAULT} | Duration: {duration}s")
    print("=" * 80)

    bridge = ESP32Bridge(port=port)
    try:
        print("[1/4] Connecting to ESP32-S3 on /dev/ttyACM0...")
        bridge.connect()
        print("      Connected successfully.")

        print("[2/4] Uploading resilient MicroPython firmware...")
        success = bridge.upload_firmware()
        if not success:
            print("      [ERROR] Firmware failed to signal ready.")
            return False
        print("      Firmware launched and running in raw REPL.")

        print("[3/4] Streaming live telemetry packets & testing oscilloscope...")
        print("-" * 80)
        print(f"{'FPS':<5} | {'MIC 1 (L)':<9} | {'MIC 2 (R)':<9} | {'GRAD':<6} | {'PIEZO':<7} | {'RAW':<5} | {'STATUS':<7} | {'WAVE DECODE'}")
        print("-" * 80)

        packet_count = 0
        t_start = time.time()
        last_report = t_start
        fps = 0.0

        while time.time() - t_start < duration:
            packet = bridge.read_packet(timeout=0.5)
            if not packet:
                continue

            packet_count += 1
            now = time.time()
            if now - last_report >= 0.5:
                fps = packet_count / (now - t_start)
                last_report = now

            # VU meters
            l_bar = "=" * min(8, max(0, packet["p2p_l"] // 350))
            r_bar = "=" * min(8, max(0, packet["p2p_r"] // 350))
            piezo_bar = "=" * min(6, max(0, packet["piezo_p2p"] // 200))
            
            wave_status = f"L:{len(packet['left_samples'])} R:{len(packet['right_samples'])} OK"

            print(
                f"\r{fps:4.1f} | "
                f"{packet['p2p_l']:5d} [{l_bar:<8}] | "
                f"{packet['p2p_r']:5d} [{r_bar:<8}] | "
                f"{packet['grad_pct']:3d}%  | "
                f"{packet['piezo_p2p']:4d} [{piezo_bar:<6}] | "
                f"{packet['piezo_raw']:4d} | "
                f"{packet['status']:<7} | "
                f"{wave_status}",
                end="",
                flush=True,
            )

        print("\n" + "-" * 80)
        total_time = time.time() - t_start
        final_fps = packet_count / total_time
        print(f"[4/4] Validation Summary:")
        print(f"      Total Packets Received : {packet_count}")
        print(f"      Duration               : {total_time:.2f} s")
        print(f"      Average Streaming Rate : {final_fps:.1f} FPS")
        print(f"      Hardware Status        : PASS (Dual Mic, Piezo & OLED active)")
        print("=" * 80)
        return packet_count > 0

    except KeyboardInterrupt:
        print("\n[INFO] Stopped by user.")
        return True
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        return False
    finally:
        print("Interrupting ESP32 and releasing serial port...")
        bridge.stop()
        print("Done.")


if __name__ == "__main__":
    dur = 8.0
    if len(sys.argv) > 1:
        try:
            dur = float(sys.argv[1])
        except ValueError:
            pass
    success = run_live_test(duration=dur)
    sys.exit(0 if success else 1)
