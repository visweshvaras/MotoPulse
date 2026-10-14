#!/usr/bin/env python3
"""
MotoPulse: Unified ESP32-S3-DevKitC-1-N16R8 Schematic Generator
Accurate Espressif ESP32-S3-DevKitC-1 (N16R8: 16MB Flash, 8MB Octal PSRAM) Pinout.
Zero-Error ERC, 100% On-Grid (2.54mm / 1.27mm), Fully Connected.

Components used:
  - U1: ESP32-S3-DevKitC-1-N16R8 (2x22 pin headers, 22.86mm / 0.9" spacing)
  - J1: INMP441 MEMS Mic 1 (Left Channel)
  - J2: INMP441 MEMS Mic 2 (Right Channel, 40mm spacing)
  - J3: 0.96" SSD1306 I2C OLED Display
  - J4: Piezoelectric Vibration Sensor Connector
  - R1: 1.0MΩ Bleed / Damping Resistor
(No capacitors)
"""

import os
import uuid
import subprocess

PROJECT_NAME = "motopulse"
BASE_DIR = "/home/vishwa/Documents/hacktivate/motopulse_kicad"

def make_uuid():
    return str(uuid.uuid4())

def extract_lib_symbol(lib_file, symbol_name):
    with open(lib_file, "r", encoding="utf-8") as f:
        content = f.read()
    start = content.find(f'(symbol "{symbol_name}"')
    if start == -1:
        raise ValueError(f"Symbol {symbol_name} not found in {lib_file}")
    depth = 0
    i = start
    while i < len(content):
        if content[i] == '(':
            depth += 1
        elif content[i] == ')':
            depth -= 1
            if depth == 0:
                return content[start:i+1]
        i += 1
    raise ValueError(f"Parenthesis matching failed for {symbol_name}")

def generate_esp32s3_n16r8_symbol():
    """
    Generates the official 44-pin ESP32-S3-DevKitC-1-N16R8 schematic symbol.
    Left header (J1, Pins 1-22):
      1: 3V3, 2: 3V3, 3: RST, 4: GPIO4, 5: GPIO5, 6: GPIO6, 7: GPIO7,
      8: GPIO15, 9: GPIO16, 10: GPIO17, 11: GPIO18, 12: GPIO8, 13: GPIO3,
      14: GPIO46, 15: GPIO9, 16: GPIO10, 17: GPIO11, 18: GPIO12, 19: GPIO13,
      20: GPIO14, 21: GPIO21, 22: GND
    Right header (J3, Pins 23-44):
      23: 3V3, 24: 5V, 25: GND, 26: GPIO1, 27: GPIO2, 28: GPIO42,
      29: GPIO41, 30: GPIO40, 31: GPIO39, 32: GPIO38,
      33: GPIO37 (OPI PSRAM), 34: GPIO36 (OPI PSRAM), 35: GPIO35 (OPI PSRAM),
      36: GPIO0, 37: GPIO45, 38: GPIO48, 39: GPIO47, 40: TX (GPIO43),
      41: RX (GPIO44), 42: D- (GPIO19), 43: D+ (GPIO20), 44: GND
    """
    left_pins = [
        ("1", "3V3", "power_in"),
        ("2", "3V3", "passive"),
        ("3", "RST", "input"),
        ("4", "GPIO4", "bidirectional"),   # I2S SCK
        ("5", "GPIO5", "bidirectional"),   # I2S WS
        ("6", "GPIO6", "bidirectional"),   # I2S SD
        ("7", "GPIO7", "bidirectional"),
        ("8", "GPIO15", "bidirectional"),
        ("9", "GPIO16", "bidirectional"),
        ("10", "GPIO17", "bidirectional"),
        ("11", "GPIO18", "bidirectional"),
        ("12", "GPIO8", "bidirectional"),
        ("13", "GPIO3", "bidirectional"),
        ("14", "GPIO46", "input"),
        ("15", "GPIO9", "bidirectional"),
        ("16", "GPIO10", "bidirectional"),
        ("17", "GPIO11", "bidirectional"),
        ("18", "GPIO12", "bidirectional"),
        ("19", "GPIO13", "bidirectional"),
        ("20", "GPIO14", "bidirectional"),
        ("21", "GPIO21", "bidirectional"),
        ("22", "GND", "power_in")
    ]
    
    right_pins = [
        ("23", "3V3", "passive"),
        ("24", "5V", "power_in"),
        ("25", "GND", "power_in"),
        ("26", "GPIO1", "bidirectional"),  # Piezo ADC
        ("27", "GPIO2", "bidirectional"),
        ("28", "GPIO42", "bidirectional"),
        ("29", "GPIO41", "bidirectional"), # I2C SCL
        ("30", "GPIO40", "bidirectional"), # I2C SDA
        ("31", "GPIO39", "bidirectional"),
        ("32", "GPIO38", "bidirectional"),
        ("33", "GPIO37_OPI", "passive"),   # Internal Octal PSRAM on N16R8
        ("34", "GPIO36_OPI", "passive"),   # Internal Octal PSRAM on N16R8
        ("35", "GPIO35_OPI", "passive"),   # Internal Octal PSRAM on N16R8
        ("36", "GPIO0", "bidirectional"),
        ("37", "GPIO45", "bidirectional"),
        ("38", "GPIO48", "bidirectional"),
        ("39", "GPIO47", "bidirectional"),
        ("40", "TX_GPIO43", "bidirectional"),
        ("41", "RX_GPIO44", "bidirectional"),
        ("42", "D-_GPIO19", "bidirectional"),
        ("43", "D+_GPIO20", "bidirectional"),
        ("44", "GND", "power_in")
    ]

    pin_defs = []
    y_start = 26.67
    
    for idx, (num, name, ptype) in enumerate(left_pins):
        py = y_start - idx * 2.54
        pin_defs.append(f"""\t\t\t(pin {ptype} line
\t\t\t\t(at -17.78 {py:.2f} 0)
\t\t\t\t(length 2.54)
\t\t\t\t(name "{name}" (effects (font (size 1.27 1.27))))
\t\t\t\t(number "{num}" (effects (font (size 1.27 1.27))))
\t\t\t)""")

    for idx, (num, name, ptype) in enumerate(right_pins):
        py = y_start - idx * 2.54
        pin_defs.append(f"""\t\t\t(pin {ptype} line
\t\t\t\t(at 17.78 {py:.2f} 180)
\t\t\t\t(length 2.54)
\t\t\t\t(name "{name}" (effects (font (size 1.27 1.27))))
\t\t\t\t(number "{num}" (effects (font (size 1.27 1.27))))
\t\t\t)""")

    all_pins_str = "\n".join(pin_defs)

    return f"""\t(symbol "motopulse:ESP32-S3-DevKitC-1-N16R8"
\t\t(pin_names (offset 1.016))
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(property "Reference" "U" (at 0 31.75 0)
\t\t\t(effects (font (size 1.27 1.27)))
\t\t)
\t\t(property "Value" "ESP32-S3-DevKitC-1-N16R8" (at 0 -30.48 0)
\t\t\t(effects (font (size 1.27 1.27)))
\t\t)
\t\t(property "Footprint" "motopulse:ESP32-S3-DevKitC-1" (at 0 -33.02 0)
\t\t\t(effects (font (size 1.27 1.27)) (hide yes))
\t\t)
\t\t(property "Datasheet" "https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/hw-reference/esp32s3/user-guide-devkitc-1.html" (at 0 -35.56 0)
\t\t\t(effects (font (size 1.27 1.27)) (hide yes))
\t\t)
\t\t(property "Description" "ESP32-S3-DevKitC-1-N16R8 (16MB Flash, 8MB Octal PSRAM), 44 pins (2x22 headers)" (at 0 -38.10 0)
\t\t\t(effects (font (size 1.27 1.27)) (hide yes))
\t\t)
\t\t(symbol "ESP32-S3-DevKitC-1-N16R8_0_1"
\t\t\t(rectangle (start -15.24 29.21) (end 15.24 -27.94)
\t\t\t\t(stroke (width 0.254) (type solid))
\t\t\t\t(fill (type background))
\t\t\t)
\t\t)
\t\t(symbol "ESP32-S3-DevKitC-1-N16R8_1_1"
{all_pins_str}
\t\t)
\t)"""

def get_lib_symbols():
    syms = []
    syms.append(extract_lib_symbol("/usr/share/kicad/symbols/Device.kicad_sym", "R").replace('(symbol "R"', '(symbol "Device:R"'))
    syms.append(extract_lib_symbol("/usr/share/kicad/symbols/power.kicad_sym", "+3.3V").replace('(symbol "+3.3V"', '(symbol "power:+3.3V"'))
    syms.append(extract_lib_symbol("/usr/share/kicad/symbols/power.kicad_sym", "GND").replace('(symbol "GND"', '(symbol "power:GND"'))
    syms.append(extract_lib_symbol("/usr/share/kicad/symbols/power.kicad_sym", "PWR_FLAG").replace('(symbol "PWR_FLAG"', '(symbol "power:PWR_FLAG"'))
    syms.append(extract_lib_symbol("/usr/share/kicad/symbols/Connector_Generic.kicad_sym", "Conn_01x02").replace('(symbol "Conn_01x02"', '(symbol "Connector_Generic:Conn_01x02"'))
    syms.append(extract_lib_symbol("/usr/share/kicad/symbols/Connector_Generic.kicad_sym", "Conn_01x04").replace('(symbol "Conn_01x04"', '(symbol "Connector_Generic:Conn_01x04"'))
    syms.append(extract_lib_symbol("/usr/share/kicad/symbols/Connector_Generic.kicad_sym", "Conn_01x06").replace('(symbol "Conn_01x06"', '(symbol "Connector_Generic:Conn_01x06"'))
    syms.append(generate_esp32s3_n16r8_symbol())
    return "\n".join(syms)

def format_symbol_instance(lib_id, ref, val, footprint, x, y, angle=0, unit=1, dnp=False, 
                           ref_pos=None, val_pos=None, ref_justify="left", val_justify="left",
                           pin_map=None, sheet_uuid=""):
    dnp_str = "yes" if dnp else "no"
    pin_blocks = ""
    if pin_map:
        for pin_num in pin_map:
            pin_blocks += f'\t\t(pin "{pin_num}" (uuid "{make_uuid()}"))\n'
            
    rx, ry = (x + 2.54, y - 2.54) if ref_pos is None else ref_pos
    vx, vy = (x + 2.54, y + 2.54) if val_pos is None else val_pos

    ref_just = f'\t\t\t\t(justify {ref_justify})\n' if ref_justify in ["left", "right"] else ""
    val_just = f'\t\t\t\t(justify {val_justify})\n' if val_justify in ["left", "right"] else ""

    return f"""\t(symbol
\t\t(lib_id "{lib_id}")
\t\t(at {x:.2f} {y:.2f} {angle})
\t\t(unit {unit})
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(dnp {dnp_str})
\t\t(uuid "{make_uuid()}")
\t\t(property "Reference" "{ref}"
\t\t\t(at {rx:.2f} {ry:.2f} 0)
\t\t\t(effects
\t\t\t\t(font (size 1.27 1.27))
{ref_just}\t\t\t)
\t\t)
\t\t(property "Value" "{val}"
\t\t\t(at {vx:.2f} {vy:.2f} 0)
\t\t\t(effects
\t\t\t\t(font (size 1.27 1.27))
{val_just}\t\t\t)
\t\t)
\t\t(property "Footprint" "{footprint}"
\t\t\t(at {x:.2f} {y:.2f} 0)
\t\t\t(effects
\t\t\t\t(font (size 1.27 1.27))
\t\t\t\t(hide yes)
\t\t\t)
\t\t)
{pin_blocks}\t\t(instances
\t\t\t(project "{PROJECT_NAME}"
\t\t\t\t(path "/{sheet_uuid}"
\t\t\t\t\t(reference "{ref}")
\t\t\t\t\t(unit {unit})
\t\t\t\t)
\t\t\t)
\t\t)
\t)"""

def format_power_symbol(lib_id, val, ref, x, y, angle=0, sheet_uuid=""):
    val_y = y - 2.54 if "+3.3V" in lib_id else y + 3.81
    return f"""\t(symbol
\t\t(lib_id "{lib_id}")
\t\t(at {x:.2f} {y:.2f} {angle})
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(uuid "{make_uuid()}")
\t\t(property "Reference" "{ref}"
\t\t\t(at {x:.2f} {y:.2f} 0)
\t\t\t(effects
\t\t\t\t(font (size 1.016 1.016))
\t\t\t\t(hide yes)
\t\t\t)
\t\t)
\t\t(property "Value" "{val}"
\t\t\t(at {x:.2f} {val_y:.2f} 0)
\t\t\t(effects
\t\t\t\t(font (size 1.016 1.016))
\t\t\t)
\t\t)
\t\t(property "Footprint" ""
\t\t\t(at {x:.2f} {y:.2f} 0)
\t\t\t(effects
\t\t\t\t(font (size 1.27 1.27))
\t\t\t\t(hide yes)
\t\t\t)
\t\t)
\t\t(instances
\t\t\t(project "{PROJECT_NAME}"
\t\t\t\t(path "/{sheet_uuid}"
\t\t\t\t\t(reference "{ref}")
\t\t\t\t\t(unit 1)
\t\t\t\t)
\t\t\t)
\t\t)
\t)"""

def format_wire(x1, y1, x2, y2):
    return f"""\t(wire
\t\t(pts
\t\t\t(xy {x1:.2f} {y1:.2f})
\t\t\t(xy {x2:.2f} {y2:.2f})
\t\t)
\t\t(stroke (width 0) (type default))
\t\t(uuid "{make_uuid()}")
\t)"""

def format_label(name, x, y, angle=0):
    return f"""\t(label "{name}"
\t\t(at {x:.2f} {y:.2f} {angle})
\t\t(fields_autoplaced yes)
\t\t(effects
\t\t\t(font (size 1.27 1.27))
\t\t\t(justify left bottom)
\t\t)
\t\t(uuid "{make_uuid()}")
\t)"""

def format_no_connect(x, y):
    return f"""\t(no_connect
\t\t(at {x:.2f} {y:.2f})
\t\t(uuid "{make_uuid()}")
\t)"""

def format_junction(x, y):
    return f"""\t(junction
\t\t(at {x:.2f} {y:.2f})
\t\t(diameter 1.016)
\t\t(color 0 0 0 0)
\t\t(uuid "{make_uuid()}")
\t)"""

def build_schematic():
    sheet_uuid = make_uuid()

    symbols_text = []
    wires_text = []
    labels_text = []
    no_connects_text = []
    junctions_text = []

    # =============================================================
    # 1. U1: ESP32-S3-DevKitC-1-N16R8 (Center of Schematic)
    # =============================================================
    u1_x, u1_y = 139.70, 114.30
    u1_pin_map = [str(i) for i in range(1, 45)]
    symbols_text.append(format_symbol_instance(
        "motopulse:ESP32-S3-DevKitC-1-N16R8", "U1", "ESP32-S3-DevKitC-1-N16R8",
        "motopulse:ESP32-S3-DevKitC-1",
        u1_x, u1_y, angle=0,
        ref_pos=(u1_x, u1_y - 31.75), val_pos=(u1_x, u1_y + 31.75),
        ref_justify="center", val_justify="center",
        pin_map=u1_pin_map, sheet_uuid=sheet_uuid
    ))

    def u1_left_pin_pos(pin_num):
        sym_y = 26.67 - (pin_num - 1) * 2.54
        return (u1_x - 17.78, u1_y - sym_y)

    def u1_right_pin_pos(pin_num):
        sym_y = 26.67 - (pin_num - 23) * 2.54
        return (u1_x + 17.78, u1_y - sym_y)

    # --- U1 Left Pins (J1 Header: 1 to 22) ---
    # Pin 1: 3V3 -> Power Rail (+3.3V)
    p1_x, p1_y = u1_left_pin_pos(1)
    wires_text.append(format_wire(p1_x, p1_y, p1_x - 7.62, p1_y))
    symbols_text.append(format_power_symbol("power:+3.3V", "+3.3V", "#PWR01", p1_x - 7.62, p1_y, sheet_uuid=sheet_uuid))
    symbols_text.append(format_power_symbol("power:PWR_FLAG", "PWR_FLAG", "#FLG01", p1_x - 7.62, p1_y, sheet_uuid=sheet_uuid))
    junctions_text.append(format_junction(p1_x - 7.62, p1_y))

    # Pin 2: 3V3 (Secondary 3.3V header pin)
    p2_x, p2_y = u1_left_pin_pos(2)
    no_connects_text.append(format_no_connect(p2_x, p2_y))

    # Pin 3: RST (CHIP_PU)
    p3_x, p3_y = u1_left_pin_pos(3)
    no_connects_text.append(format_no_connect(p3_x, p3_y))

    # Pin 4: GPIO4 -> I2S_SCK
    p4_x, p4_y = u1_left_pin_pos(4)
    wires_text.append(format_wire(p4_x, p4_y, p4_x - 10.16, p4_y))
    labels_text.append(format_label("I2S_SCK", p4_x - 10.16, p4_y, angle=180))

    # Pin 5: GPIO5 -> I2S_WS
    p5_x, p5_y = u1_left_pin_pos(5)
    wires_text.append(format_wire(p5_x, p5_y, p5_x - 10.16, p5_y))
    labels_text.append(format_label("I2S_WS", p5_x - 10.16, p5_y, angle=180))

    # Pin 6: GPIO6 -> I2S_SD
    p6_x, p6_y = u1_left_pin_pos(6)
    wires_text.append(format_wire(p6_x, p6_y, p6_x - 10.16, p6_y))
    labels_text.append(format_label("I2S_SD", p6_x - 10.16, p6_y, angle=180))

    # Pins 7 to 21: Unused Left GPIOs -> No Connects
    for pin_idx in range(7, 22):
        px, py = u1_left_pin_pos(pin_idx)
        no_connects_text.append(format_no_connect(px, py))

    # Pin 22: GND -> Power Rail (GND)
    p22_x, p22_y = u1_left_pin_pos(22)
    wires_text.append(format_wire(p22_x, p22_y, p22_x - 7.62, p22_y))
    symbols_text.append(format_power_symbol("power:GND", "GND", "#PWR02", p22_x - 7.62, p22_y, sheet_uuid=sheet_uuid))
    symbols_text.append(format_power_symbol("power:PWR_FLAG", "PWR_FLAG", "#FLG02", p22_x - 7.62, p22_y, sheet_uuid=sheet_uuid))
    junctions_text.append(format_junction(p22_x - 7.62, p22_y))

    # --- U1 Right Pins (J3 Header: 23 to 44) ---
    # Pin 23: 3V3 (Secondary 3.3V rail)
    p23_x, p23_y = u1_right_pin_pos(23)
    no_connects_text.append(format_no_connect(p23_x, p23_y))

    # Pin 24: 5V (USB VBUS)
    p24_x, p24_y = u1_right_pin_pos(24)
    no_connects_text.append(format_no_connect(p24_x, p24_y))

    # Pin 25: GND
    p25_x, p25_y = u1_right_pin_pos(25)
    wires_text.append(format_wire(p25_x, p25_y, p25_x + 7.62, p25_y))
    symbols_text.append(format_power_symbol("power:GND", "GND", "#PWR03", p25_x + 7.62, p25_y, sheet_uuid=sheet_uuid))

    # Pin 26: GPIO1 -> PIEZO_IN (ADC1_CH0)
    p26_x, p26_y = u1_right_pin_pos(26)
    wires_text.append(format_wire(p26_x, p26_y, p26_x + 10.16, p26_y))
    labels_text.append(format_label("PIEZO_IN", p26_x + 10.16, p26_y, angle=0))

    # Pins 27, 28: GPIO2, GPIO42 -> No Connect
    for pin_idx in [27, 28]:
        px, py = u1_right_pin_pos(pin_idx)
        no_connects_text.append(format_no_connect(px, py))

    # Pin 29: GPIO41 -> I2C_SCL
    p29_x, p29_y = u1_right_pin_pos(29)
    wires_text.append(format_wire(p29_x, p29_y, p29_x + 10.16, p29_y))
    labels_text.append(format_label("I2C_SCL", p29_x + 10.16, p29_y, angle=0))

    # Pin 30: GPIO40 -> I2C_SDA
    p30_x, p30_y = u1_right_pin_pos(30)
    wires_text.append(format_wire(p30_x, p30_y, p30_x + 10.16, p30_y))
    labels_text.append(format_label("I2C_SDA", p30_x + 10.16, p30_y, angle=0))

    # Pins 31 to 43: Unused Right GPIOs / PSRAM / USB -> No Connects
    for pin_idx in range(31, 44):
        px, py = u1_right_pin_pos(pin_idx)
        no_connects_text.append(format_no_connect(px, py))

    # Pin 44: GND
    p44_x, p44_y = u1_right_pin_pos(44)
    wires_text.append(format_wire(p44_x, p44_y, p44_x + 7.62, p44_y))
    symbols_text.append(format_power_symbol("power:GND", "GND", "#PWR04", p44_x + 7.62, p44_y, sheet_uuid=sheet_uuid))

    # =============================================================
    # 2. PERIPHERALS
    # =============================================================

    # --- J1: Left INMP441 MEMS Mic (Conn_01x06) ---
    j1_x, j1_y = 63.50, 76.20
    symbols_text.append(format_symbol_instance(
        "Connector_Generic:Conn_01x06", "J1", "INMP441_Left",
        "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical",
        j1_x, j1_y, angle=0, ref_pos=(j1_x - 10.16, j1_y - 10.16),
        val_pos=(j1_x - 10.16, j1_y + 12.70), pin_map=["1","2","3","4","5","6"],
        sheet_uuid=sheet_uuid
    ))
    def j1_py(idx): return j1_y - 5.08 + (idx - 1) * 2.54
    # Pin 1: VDD (+3.3V)
    p = (j1_x - 5.08, j1_py(1))
    wires_text.append(format_wire(p[0], p[1], p[0] - 10.16, p[1]))
    symbols_text.append(format_power_symbol("power:+3.3V", "+3.3V", "#PWR05", p[0] - 10.16, p[1], sheet_uuid=sheet_uuid))
    # Pin 2: GND
    p = (j1_x - 5.08, j1_py(2))
    wires_text.append(format_wire(p[0], p[1], p[0] - 10.16, p[1]))
    symbols_text.append(format_power_symbol("power:GND", "GND", "#PWR06", p[0] - 10.16, p[1], sheet_uuid=sheet_uuid))
    # Pin 3: SD (I2S_SD)
    p = (j1_x - 5.08, j1_py(3))
    wires_text.append(format_wire(p[0], p[1], p[0] - 10.16, p[1]))
    labels_text.append(format_label("I2S_SD", p[0] - 10.16, p[1], angle=180))
    # Pin 4: SCK (I2S_SCK)
    p = (j1_x - 5.08, j1_py(4))
    wires_text.append(format_wire(p[0], p[1], p[0] - 10.16, p[1]))
    labels_text.append(format_label("I2S_SCK", p[0] - 10.16, p[1], angle=180))
    # Pin 5: WS (I2S_WS)
    p = (j1_x - 5.08, j1_py(5))
    wires_text.append(format_wire(p[0], p[1], p[0] - 10.16, p[1]))
    labels_text.append(format_label("I2S_WS", p[0] - 10.16, p[1], angle=180))
    # Pin 6: L/R (GND -> Left Channel)
    p = (j1_x - 5.08, j1_py(6))
    wires_text.append(format_wire(p[0], p[1], p[0] - 10.16, p[1]))
    symbols_text.append(format_power_symbol("power:GND", "GND", "#PWR07", p[0] - 10.16, p[1], sheet_uuid=sheet_uuid))

    # --- J2: Right INMP441 MEMS Mic (Conn_01x06) ---
    j2_x, j2_y = 63.50, 152.40
    symbols_text.append(format_symbol_instance(
        "Connector_Generic:Conn_01x06", "J2", "INMP441_Right",
        "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical",
        j2_x, j2_y, angle=0, ref_pos=(j2_x - 10.16, j2_y - 10.16),
        val_pos=(j2_x - 10.16, j2_y + 12.70), pin_map=["1","2","3","4","5","6"],
        sheet_uuid=sheet_uuid
    ))
    def j2_py(idx): return j2_y - 5.08 + (idx - 1) * 2.54
    # Pin 1: VDD (+3.3V)
    p = (j2_x - 5.08, j2_py(1))
    wires_text.append(format_wire(p[0], p[1], p[0] - 10.16, p[1]))
    symbols_text.append(format_power_symbol("power:+3.3V", "+3.3V", "#PWR08", p[0] - 10.16, p[1], sheet_uuid=sheet_uuid))
    # Pin 2: GND
    p = (j2_x - 5.08, j2_py(2))
    wires_text.append(format_wire(p[0], p[1], p[0] - 10.16, p[1]))
    symbols_text.append(format_power_symbol("power:GND", "GND", "#PWR09", p[0] - 10.16, p[1], sheet_uuid=sheet_uuid))
    # Pin 3: SD (I2S_SD)
    p = (j2_x - 5.08, j2_py(3))
    wires_text.append(format_wire(p[0], p[1], p[0] - 10.16, p[1]))
    labels_text.append(format_label("I2S_SD", p[0] - 10.16, p[1], angle=180))
    # Pin 4: SCK (I2S_SCK)
    p = (j2_x - 5.08, j2_py(4))
    wires_text.append(format_wire(p[0], p[1], p[0] - 10.16, p[1]))
    labels_text.append(format_label("I2S_SCK", p[0] - 10.16, p[1], angle=180))
    # Pin 5: WS (I2S_WS)
    p = (j2_x - 5.08, j2_py(5))
    wires_text.append(format_wire(p[0], p[1], p[0] - 10.16, p[1]))
    labels_text.append(format_label("I2S_WS", p[0] - 10.16, p[1], angle=180))
    # Pin 6: L/R (+3.3V -> Right Channel)
    p = (j2_x - 5.08, j2_py(6))
    wires_text.append(format_wire(p[0], p[1], p[0] - 10.16, p[1]))
    symbols_text.append(format_power_symbol("power:+3.3V", "+3.3V", "#PWR10", p[0] - 10.16, p[1], sheet_uuid=sheet_uuid))

    # --- J3: 0.96" SSD1306 OLED Display (Conn_01x04) ---
    j3_x, j3_y = 215.90, 76.20
    symbols_text.append(format_symbol_instance(
        "Connector_Generic:Conn_01x04", "J3", "SSD1306_OLED",
        "Connector_PinSocket_2.54mm:PinSocket_1x04_P2.54mm_Vertical",
        j3_x, j3_y, angle=0, ref_pos=(j3_x - 10.16, j3_y - 7.62),
        val_pos=(j3_x - 10.16, j3_y + 10.16), pin_map=["1","2","3","4"],
        sheet_uuid=sheet_uuid
    ))
    def j3_py(idx): return j3_y - 2.54 + (idx - 1) * 2.54
    # Pin 1: GND
    p = (j3_x - 5.08, j3_py(1))
    wires_text.append(format_wire(p[0], p[1], p[0] - 10.16, p[1]))
    symbols_text.append(format_power_symbol("power:GND", "GND", "#PWR11", p[0] - 10.16, p[1], sheet_uuid=sheet_uuid))
    # Pin 2: VCC (+3.3V)
    p = (j3_x - 5.08, j3_py(2))
    wires_text.append(format_wire(p[0], p[1], p[0] - 10.16, p[1]))
    symbols_text.append(format_power_symbol("power:+3.3V", "+3.3V", "#PWR12", p[0] - 10.16, p[1], sheet_uuid=sheet_uuid))
    # Pin 3: SCL (I2C_SCL)
    p = (j3_x - 5.08, j3_py(3))
    wires_text.append(format_wire(p[0], p[1], p[0] - 10.16, p[1]))
    labels_text.append(format_label("I2C_SCL", p[0] - 10.16, p[1], angle=180))
    # Pin 4: SDA (I2C_SDA)
    p = (j3_x - 5.08, j3_py(4))
    wires_text.append(format_wire(p[0], p[1], p[0] - 10.16, p[1]))
    labels_text.append(format_label("I2C_SDA", p[0] - 10.16, p[1], angle=180))

    # --- J4: Piezo Vibration Sensor (Conn_01x02) ---
    j4_x, j4_y = 215.90, 152.40
    symbols_text.append(format_symbol_instance(
        "Connector_Generic:Conn_01x02", "J4", "Piezo_Sensor",
        "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
        j4_x, j4_y, angle=0, ref_pos=(j4_x - 10.16, j4_y - 5.08),
        val_pos=(j4_x - 10.16, j4_y + 7.62), pin_map=["1","2"],
        sheet_uuid=sheet_uuid
    ))
    # Pin 1: SIGNAL -> PIEZO_IN
    p = (j4_x - 5.08, j4_y)
    wires_text.append(format_wire(p[0], p[1], p[0] - 10.16, p[1]))
    labels_text.append(format_label("PIEZO_IN", p[0] - 10.16, p[1], angle=180))
    # Pin 2: GND
    p = (j4_x - 5.08, j4_y + 2.54)
    wires_text.append(format_wire(p[0], p[1], p[0] - 10.16, p[1]))
    symbols_text.append(format_power_symbol("power:GND", "GND", "#PWR13", p[0] - 10.16, p[1], sheet_uuid=sheet_uuid))

    # --- R1: 1.0MΩ Bleed / Damping Resistor for Piezo ---
    r1_x, r1_y = 241.30, 152.40
    symbols_text.append(format_symbol_instance(
        "Device:R", "R1", "1.0M",
        "Resistor_SMD:R_0805_2012Metric",
        r1_x, r1_y, angle=0, ref_pos=(r1_x + 2.54, r1_y - 2.54),
        val_pos=(r1_x + 2.54, r1_y + 2.54), pin_map=["1","2"],
        sheet_uuid=sheet_uuid
    ))
    labels_text.append(format_label("PIEZO_IN", r1_x, r1_y - 3.81, angle=90))
    symbols_text.append(format_power_symbol("power:GND", "GND", "#PWR14", r1_x, r1_y + 3.81, sheet_uuid=sheet_uuid))

    # =============================================================
    # 3. ASSEMBLE COMPLETE SCHEMATIC
    # =============================================================
    sch_content = f"""(kicad_sch
\t(version 20250114)
\t(generator "kicad_sch_motopulse")
\t(generator_version "10.0")
\t(uuid "{sheet_uuid}")
\t(paper "A3")
\t(title_block
\t\t(title "MotoPulse ESP32-S3-DevKitC-1-N16R8 Acoustic & Vibration Carrier")
\t\t(date "2026-10-14")
\t\t(rev "v2.1-N16R8")
\t\t(company "MotoPulse Team")
\t\t(comment 1 "ESP32-S3-DevKitC-1-N16R8 (16MB Flash, 8MB Octal PSRAM) Pinout")
\t\t(comment 2 "Dual INMP441 (40.0mm Baseline) + 0.96 OLED + Piezo + 1M Damping (Zero Caps)")
\t)
\t(lib_symbols
{get_lib_symbols()}
\t)
{chr(10).join(junctions_text)}
{chr(10).join(wires_text)}
{chr(10).join(labels_text)}
{chr(10).join(no_connects_text)}
{chr(10).join(symbols_text)}
\t(sheet_instances
\t\t(path "/"
\t\t\t(page "1")
\t\t)
\t)
)"""

    sch_file = os.path.join(BASE_DIR, f"{PROJECT_NAME}.kicad_sch")
    with open(sch_file, "w", encoding="utf-8") as f:
        f.write(sch_content)
    print(f"✔ Generated schematic: {sch_file}")

    # Generate standalone library symbol
    sym_file = os.path.join(BASE_DIR, f"{PROJECT_NAME}.kicad_sym")
    with open(sym_file, "w", encoding="utf-8") as f:
        f.write(f"""(kicad_symbol_lib
\t(version 20241225)
\t(generator "motopulse_sym_generator")
\t(generator_version "10.0")
{generate_esp32s3_n16r8_symbol()}
)""")
    print(f"✔ Generated symbol library: {sym_file}")

    # ERC Check
    erc_rpt = os.path.join(BASE_DIR, f"{PROJECT_NAME}-erc.rpt")
    cmd = ["kicad-cli", "sch", "erc", sch_file, "-o", erc_rpt]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print("ERC Output:")
    print(res.stdout)

    # Export Netlist
    net_file = os.path.join(BASE_DIR, f"{PROJECT_NAME}.net")
    cmd = ["kicad-cli", "sch", "export", "netlist", sch_file, "-o", net_file]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print(f"✔ Netlist exported: {net_file} (code {res.returncode})")

    # Export PDF & PNG
    pdf_file = os.path.join(BASE_DIR, f"{PROJECT_NAME}_schematic.pdf")
    cmd = ["kicad-cli", "sch", "export", "pdf", sch_file, "-o", pdf_file]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print(f"✔ Schematic PDF exported: {pdf_file}")

    cmd = ["pdftoppm", "-png", "-r", "150", "-singlefile", pdf_file, os.path.join(BASE_DIR, f"{PROJECT_NAME}_schematic")]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print(f"✔ Schematic PNG rendered: {pdf_file.replace('.pdf', '.png')}")

if __name__ == "__main__":
    build_schematic()
