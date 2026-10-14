# MicroPython SSD1306 OLED driver, I2C and SPI interfaces
import time
import framebuf

class SSD1306(framebuf.FrameBuffer):
    def __init__(self, width, height, external_vcc):
        self.width = width
        self.height = height
        self.external_vcc = external_vcc
        self.pages = self.height // 8
        self.buffer = bytearray(self.pages * self.width)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_VLSB)
        self.init_display()

    def init_display(self):
        for cmd in (
            0xAE,        # SET_DISP: off
            0xD5, 0x80,  # SET_DISP_CLK_DIV
            0xA8, self.height - 1, # SET_MUX_RATIO
            0xD3, 0x00,  # SET_DISP_OFFSET
            0x40,        # SET_DISP_START_LINE
            0x8D, 0x14 if not self.external_vcc else 0x10, # SET_CHARGE_PUMP
            0x20, 0x00,  # SET_MEM_ADDR: horizontal
            0xA1,        # SET_SEG_REMAP: col 127 mapped to SEG0
            0xC8,        # SET_COM_OUT_DIR: remapped
            0xDA, 0x12 if self.height == 64 else 0x02, # SET_COM_PIN_CFG
            0x81, 0xCF if not self.external_vcc else 0x9F, # SET_CONTRAST
            0xD9, 0xF1 if not self.external_vcc else 0x22, # SET_PRECHARGE
            0xDB, 0x40,  # SET_VCOM_DESEL
            0xA4,        # DISP_ALLON_RESUME
            0xA6,        # SET_NORM_INV: normal
            0xAF         # SET_DISP: on
        ):
            self.write_cmd(cmd)
        self.fill(0)
        self.show()

    def poweroff(self):
        self.write_cmd(0xAE)

    def poweron(self):
        self.write_cmd(0xAF)

    def contrast(self, contrast):
        self.write_cmd(0x81)
        self.write_cmd(contrast)

    def invert(self, invert):
        self.write_cmd(0xA7 if invert else 0xA6)

class SSD1306_I2C(SSD1306):
    def __init__(self, width, height, i2c, addr=0x3C, external_vcc=False):
        self.i2c = i2c
        self.addr = addr
        self.temp = bytearray(2)
        self.write_list = [b'\x40', None]
        super().__init__(width, height, external_vcc)

    def write_cmd(self, cmd):
        self.temp[0] = 0x80
        self.temp[1] = cmd
        self.i2c.writeto(self.addr, self.temp)

    def write_data(self, buf):
        self.write_list[1] = buf
        self.i2c.writevto(self.addr, self.write_list)

    def show(self):
        x0 = 0
        x1 = self.width - 1
        if self.width == 64:
            x0 += 32
            x1 += 32
        self.write_cmd(0x21)
        self.write_cmd(x0)
        self.write_cmd(x1)
        self.write_cmd(0x22)
        self.write_cmd(0)
        self.write_cmd(self.pages - 1)
        self.write_data(self.buffer)
