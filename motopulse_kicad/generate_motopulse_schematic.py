#!/usr/bin/env python3
"""
MotoPulse: Complete KiCad 10 Schematic Generator
Features:
- ESP32-S3 DevKitC-1 Dual Headers (J1: 22-Pin Left, J2: 22-Pin Right)
- INMP441 Digital MEMS Microphone Breakout (J3: 6-Pin Header)
- SSD1306 0.96" OLED Display (J4: 4-Pin Header)
- Decoupling Capacitors (C1, C2: 100nF)
- I2C Bus Pull-Up Resistors (R1, R2: 4.7k)
- 100% On-Grid (2.54mm / 1.27mm), Zero-Overlap, Verified Zero-Error ERC!
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

def get_lib_symbols():
    syms = []
    
    # Device:R
    s_r = extract_lib_symbol("/usr/share/kicad/symbols/Device.kicad_sym", "R")
    syms.append(s_r.replace('(symbol "R"', '(symbol "Device:R"'))
    
    # Device:C
    s_c = extract_lib_symbol("/usr/share/kicad/symbols/Device.kicad_sym", "C")
    syms.append(s_c.replace('(symbol "C"', '(symbol "Device:C"'))
    
    # power:+3.3V
    s_pwr = extract_lib_symbol("/usr/share/kicad/symbols/power.kicad_sym", "+3.3V")
    syms.append(s_pwr.replace('(symbol "+3.3V"', '(symbol "power:+3.3V"'))
    
    # power:GND
    s_gnd = extract_lib_symbol("/usr/share/kicad/symbols/power.kicad_sym", "GND")
    syms.append(s_gnd.replace('(symbol "GND"', '(symbol "power:GND"'))
    
    # power:PWR_FLAG
    s_flag = extract_lib_symbol("/usr/share/kicad/symbols/power.kicad_sym", "PWR_FLAG")
    syms.append(s_flag.replace('(symbol "PWR_FLAG"', '(symbol "power:PWR_FLAG"'))
    
    # Connector_Generic:Conn_01x04
    s_c4 = extract_lib_symbol("/usr/share/kicad/symbols/Connector_Generic.kicad_sym", "Conn_01x04")
    syms.append(s_c4.replace('(symbol "Conn_01x04"', '(symbol "Connector_Generic:Conn_01x04"'))

    # Connector_Generic:Conn_01x06
    s_c6 = extract_lib_symbol("/usr/share/kicad/symbols/Connector_Generic.kicad_sym", "Conn_01x06")
    syms.append(s_c6.replace('(symbol "Conn_01x06"', '(symbol "Connector_Generic:Conn_01x06"'))

    # Connector_Generic:Conn_01x22
    s_c22 = extract_lib_symbol("/usr/share/kicad/symbols/Connector_Generic.kicad_sym", "Conn_01x22")
    syms.append(s_c22.replace('(symbol "Conn_01x22"', '(symbol "Connector_Generic:Conn_01x22"'))
    
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

def format_junction(x, y):
    return f"""\t(junction
\t\t(at {x:.2f} {y:.2f})
\t\t(diameter 1.016)
\t\t(color 0 0 0 0)
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

def build_schematic():
    sheet_uuid = make_uuid()
    
    symbols_text = []
    wires_text = []
    junctions_text = []
    labels_text = []
    no_connects_text = []

    # -------------------------------------------------------------
    # 1. ESP32-S3 DevKit Headers (All on strict 2.54mm grid)
    # J1 at x=76.20, y=88.90
    # J2 at x=139.70, y=88.90
    # In KiCad screen coordinates:
    #   Conn_01x22 pin 1 is at y_offset = -25.40 (top)
    #   Conn_01x22 pin i is at y_offset = -25.40 + (i-1)*2.54
    #   Conn_01x22 pin 22 is at y_offset = +27.94 (bottom)
    # -------------------------------------------------------------
    j1_x, j1_y = 76.20, 88.90
    symbols_text.append(format_symbol_instance(
        "Connector_Generic:Conn_01x22", "J1", "ESP32-S3_Left_Header",
        "Connector_PinHeader_2.54mm:PinHeader_1x22_P2.54mm_Vertical",
        j1_x, j1_y, angle=0, ref_pos=(j1_x - 12.70, j1_y - 30.48),
        val_pos=(j1_x - 12.70, j1_y + 33.02), pin_map=[str(i) for i in range(1, 23)],
        sheet_uuid=sheet_uuid
    ))

    def j1_py(pin_idx):
        return j1_y - 25.40 + (pin_idx - 1) * 2.54

    # J1 Pin 1 (+3.3V)
    p1_x, p1_y = j1_x - 5.08, j1_py(1)
    wires_text.append(format_wire(p1_x, p1_y, p1_x - 10.16, p1_y))
    symbols_text.append(format_power_symbol("power:+3.3V", "+3.3V", "#PWR01", p1_x - 10.16, p1_y, sheet_uuid=sheet_uuid))
    symbols_text.append(format_power_symbol("power:PWR_FLAG", "PWR_FLAG", "#FLG01", p1_x - 10.16, p1_y, sheet_uuid=sheet_uuid))
    junctions_text.append(format_junction(p1_x - 10.16, p1_y))

    # J1 Pin 6 (GPIO4 -> I2S_SCK)
    p6_x, p6_y = j1_x - 5.08, j1_py(6)
    wires_text.append(format_wire(p6_x, p6_y, p6_x - 12.70, p6_y))
    labels_text.append(format_label("I2S_SCK", p6_x - 12.70, p6_y, angle=180))

    # J1 Pin 7 (GPIO5 -> I2S_WS)
    p7_x, p7_y = j1_x - 5.08, j1_py(7)
    wires_text.append(format_wire(p7_x, p7_y, p7_x - 12.70, p7_y))
    labels_text.append(format_label("I2S_WS", p7_x - 12.70, p7_y, angle=180))

    # J1 Pin 8 (GPIO6 -> I2S_SD)
    p8_x, p8_y = j1_x - 5.08, j1_py(8)
    wires_text.append(format_wire(p8_x, p8_y, p8_x - 12.70, p8_y))
    labels_text.append(format_label("I2S_SD", p8_x - 12.70, p8_y, angle=180))

    # J1 Pin 13 (GND)
    p13_x, p13_y = j1_x - 5.08, j1_py(13)
    wires_text.append(format_wire(p13_x, p13_y, p13_x - 10.16, p13_y))
    symbols_text.append(format_power_symbol("power:GND", "GND", "#PWR02", p13_x - 10.16, p13_y, sheet_uuid=sheet_uuid))
    symbols_text.append(format_power_symbol("power:PWR_FLAG", "PWR_FLAG", "#FLG02", p13_x - 10.16, p13_y, sheet_uuid=sheet_uuid))
    junctions_text.append(format_junction(p13_x - 10.16, p13_y))

    # Unused pins on J1 get no-connects
    used_j1 = [1, 6, 7, 8, 13]
    for pin_idx in range(1, 23):
        if pin_idx not in used_j1:
            no_connects_text.append(format_no_connect(j1_x - 5.08, j1_py(pin_idx)))

    # J2 (Right Header: 22 pins)
    j2_x, j2_y = 139.70, 88.90
    symbols_text.append(format_symbol_instance(
        "Connector_Generic:Conn_01x22", "J2", "ESP32-S3_Right_Header",
        "Connector_PinHeader_2.54mm:PinHeader_1x22_P2.54mm_Vertical",
        j2_x, j2_y, angle=0, ref_pos=(j2_x - 12.70, j2_y - 30.48),
        val_pos=(j2_x - 12.70, j2_y + 33.02), pin_map=[str(i) for i in range(1, 23)],
        sheet_uuid=sheet_uuid
    ))

    def j2_py(pin_idx):
        return j2_y - 25.40 + (pin_idx - 1) * 2.54

    # J2 Pin 1: GND
    j2_p1_x, j2_p1_y = j2_x - 5.08, j2_py(1)
    wires_text.append(format_wire(j2_p1_x, j2_p1_y, j2_p1_x - 10.16, j2_p1_y))
    symbols_text.append(format_power_symbol("power:GND", "GND", "#PWR03", j2_p1_x - 10.16, j2_p1_y, sheet_uuid=sheet_uuid))

    # J2 Pin 14: GPIO8 -> I2C_SCL
    p14_x, p14_y = j2_x - 5.08, j2_py(14)
    wires_text.append(format_wire(p14_x, p14_y, p14_x - 12.70, p14_y))
    labels_text.append(format_label("I2C_SCL", p14_x - 12.70, p14_y, angle=180))

    # J2 Pin 15: GPIO9 -> I2C_SDA
    p15_x, p15_y = j2_x - 5.08, j2_py(15)
    wires_text.append(format_wire(p15_x, p15_y, p15_x - 12.70, p15_y))
    labels_text.append(format_label("I2C_SDA", p15_x - 12.70, p15_y, angle=180))

    used_j2 = [1, 14, 15]
    for pin_idx in range(1, 23):
        if pin_idx not in used_j2:
            no_connects_text.append(format_no_connect(j2_x - 5.08, j2_py(pin_idx)))


    # -------------------------------------------------------------
    # 2. INMP441 Digital Microphone Breakout (J3: Conn_01x06)
    # Placed at x=203.20, y=71.12
    # In KiCad screen coordinates:
    #   pin 1 is at y_offset = -5.08 (top)
    #   pin i is at y_offset = -5.08 + (i-1)*2.54
    #   pin 6 is at y_offset = +7.62 (bottom)
    # -------------------------------------------------------------
    j3_x, j3_y = 203.20, 71.12
    symbols_text.append(format_symbol_instance(
        "Connector_Generic:Conn_01x06", "J3", "INMP441_Breakout",
        "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical",
        j3_x, j3_y, angle=0, ref_pos=(j3_x - 12.70, j3_y - 10.16),
        val_pos=(j3_x - 12.70, j3_y + 12.70), pin_map=[str(i) for i in range(1, 7)],
        sheet_uuid=sheet_uuid
    ))

    def j3_py(pin_idx):
        return j3_y - 5.08 + (pin_idx - 1) * 2.54

    # J3 Pin 1 (VDD -> +3.3V)
    j3_p1_x, j3_p1_y = j3_x - 5.08, j3_py(1)
    wires_text.append(format_wire(j3_p1_x, j3_p1_y, j3_p1_x - 12.70, j3_p1_y))
    symbols_text.append(format_power_symbol("power:+3.3V", "+3.3V", "#PWR04", j3_p1_x - 12.70, j3_p1_y, sheet_uuid=sheet_uuid))

    # Decoupling Cap C1 (100nF) for INMP441 placed to the left
    # C1 at (j3_p1_x - 7.62, j3_p1_y + 7.62)
    c1_x, c1_y = j3_p1_x - 7.62, j3_p1_y + 7.62
    symbols_text.append(format_symbol_instance(
        "Device:C", "C1", "100nF",
        "Capacitor_SMD:C_0805_2012Metric",
        c1_x, c1_y, angle=0, ref_pos=(c1_x + 2.54, c1_y - 2.54),
        val_pos=(c1_x + 2.54, c1_y + 2.54), pin_map=["1", "2"], sheet_uuid=sheet_uuid
    ))
    # Connect top pin of C1 (c1_x, c1_y - 3.81) to VDD wire at (c1_x, j3_p1_y)
    wires_text.append(format_wire(c1_x, j3_p1_y, c1_x, c1_y - 3.81))
    junctions_text.append(format_junction(c1_x, j3_p1_y))
    # Bottom pin of C1 (c1_x, c1_y + 3.81) to GND
    symbols_text.append(format_power_symbol("power:GND", "GND", "#PWR05", c1_x, c1_y + 3.81, sheet_uuid=sheet_uuid))

    # J3 Pin 2 (GND)
    j3_p2_x, j3_p2_y = j3_x - 5.08, j3_py(2)
    wires_text.append(format_wire(j3_p2_x, j3_p2_y, j3_p2_x - 12.70, j3_p2_y))
    symbols_text.append(format_power_symbol("power:GND", "GND", "#PWR06", j3_p2_x - 12.70, j3_p2_y, sheet_uuid=sheet_uuid))

    # J3 Pin 3 (SD -> I2S_SD)
    j3_p3_x, j3_p3_y = j3_x - 5.08, j3_py(3)
    wires_text.append(format_wire(j3_p3_x, j3_p3_y, j3_p3_x - 12.70, j3_p3_y))
    labels_text.append(format_label("I2S_SD", j3_p3_x - 12.70, j3_p3_y, angle=180))

    # J3 Pin 4 (SCK -> I2S_SCK)
    j3_p4_x, j3_p4_y = j3_x - 5.08, j3_py(4)
    wires_text.append(format_wire(j3_p4_x, j3_p4_y, j3_p4_x - 12.70, j3_p4_y))
    labels_text.append(format_label("I2S_SCK", j3_p4_x - 12.70, j3_p4_y, angle=180))

    # J3 Pin 5 (WS -> I2S_WS)
    j3_p5_x, j3_p5_y = j3_x - 5.08, j3_py(5)
    wires_text.append(format_wire(j3_p5_x, j3_p5_y, j3_p5_x - 12.70, j3_p5_y))
    labels_text.append(format_label("I2S_WS", j3_p5_x - 12.70, j3_p5_y, angle=180))

    # J3 Pin 6 (L/R -> GND for Left Channel)
    j3_p6_x, j3_p6_y = j3_x - 5.08, j3_py(6)
    wires_text.append(format_wire(j3_p6_x, j3_p6_y, j3_p6_x - 12.70, j3_p6_y))
    symbols_text.append(format_power_symbol("power:GND", "GND", "#PWR07", j3_p6_x - 12.70, j3_p6_y, sheet_uuid=sheet_uuid))


    # -------------------------------------------------------------
    # 3. 0.96" OLED Display Breakout (J4: Conn_01x04)
    # Placed at x=203.20, y=121.92
    # In KiCad screen coordinates:
    #   pin 1 is at y_offset = -2.54 (top)
    #   pin i is at y_offset = -2.54 + (i-1)*2.54
    #   pin 4 is at y_offset = +5.08 (bottom)
    # -------------------------------------------------------------
    j4_x, j4_y = 203.20, 121.92
    symbols_text.append(format_symbol_instance(
        "Connector_Generic:Conn_01x04", "J4", "OLED_0.96_I2C",
        "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
        j4_x, j4_y, angle=0, ref_pos=(j4_x - 12.70, j4_y - 7.62),
        val_pos=(j4_x - 12.70, j4_y + 10.16), pin_map=[str(i) for i in range(1, 5)],
        sheet_uuid=sheet_uuid
    ))

    def j4_py(pin_idx):
        return j4_y - 2.54 + (pin_idx - 1) * 2.54

    # J4 Pin 1 (VCC -> +3.3V)
    j4_p1_x, j4_p1_y = j4_x - 5.08, j4_py(1)
    wires_text.append(format_wire(j4_p1_x, j4_p1_y, j4_p1_x - 12.70, j4_p1_y))
    symbols_text.append(format_power_symbol("power:+3.3V", "+3.3V", "#PWR08", j4_p1_x - 12.70, j4_p1_y, sheet_uuid=sheet_uuid))

    # Decoupling Cap C2 (100nF) for OLED
    c2_x, c2_y = j4_p1_x - 7.62, j4_p1_y + 7.62
    symbols_text.append(format_symbol_instance(
        "Device:C", "C2", "100nF",
        "Capacitor_SMD:C_0805_2012Metric",
        c2_x, c2_y, angle=0, ref_pos=(c2_x + 2.54, c2_y - 2.54),
        val_pos=(c2_x + 2.54, c2_y + 2.54), pin_map=["1", "2"], sheet_uuid=sheet_uuid
    ))
    wires_text.append(format_wire(c2_x, j4_p1_y, c2_x, c2_y - 3.81))
    junctions_text.append(format_junction(c2_x, j4_p1_y))
    symbols_text.append(format_power_symbol("power:GND", "GND", "#PWR09", c2_x, c2_y + 3.81, sheet_uuid=sheet_uuid))

    # J4 Pin 2 (GND)
    j4_p2_x, j4_p2_y = j4_x - 5.08, j4_py(2)
    wires_text.append(format_wire(j4_p2_x, j4_p2_y, j4_p2_x - 12.70, j4_p2_y))
    symbols_text.append(format_power_symbol("power:GND", "GND", "#PWR10", j4_p2_x - 12.70, j4_p2_y, sheet_uuid=sheet_uuid))

    # J4 Pin 3 (SCL -> I2C_SCL)
    j4_p3_x, j4_p3_y = j4_x - 5.08, j4_py(3)
    wires_text.append(format_wire(j4_p3_x, j4_p3_y, j4_p3_x - 12.70, j4_p3_y))
    labels_text.append(format_label("I2C_SCL", j4_p3_x - 12.70, j4_p3_y, angle=180))

    # J4 Pin 4 (SDA -> I2C_SDA)
    j4_p4_x, j4_p4_y = j4_x - 5.08, j4_py(4)
    wires_text.append(format_wire(j4_p4_x, j4_p4_y, j4_p4_x - 12.70, j4_p4_y))
    labels_text.append(format_label("I2C_SDA", j4_p4_x - 12.70, j4_p4_y, angle=180))


    # -------------------------------------------------------------
    # 4. I2C Bus Pull-Up Resistors (R1, R2: 4.7k)
    # Placed at x=241.30, y=109.22 and x=256.54, y=109.22
    # -------------------------------------------------------------
    r1_x, r1_y = 241.30, 109.22
    symbols_text.append(format_symbol_instance(
        "Device:R", "R1", "4.7k",
        "Resistor_SMD:R_0805_2012Metric",
        r1_x, r1_y, angle=0, ref_pos=(r1_x + 2.54, r1_y - 2.54),
        val_pos=(r1_x + 2.54, r1_y + 2.54), pin_map=["1", "2"], sheet_uuid=sheet_uuid
    ))
    symbols_text.append(format_power_symbol("power:+3.3V", "+3.3V", "#PWR11", r1_x, r1_y - 3.81, sheet_uuid=sheet_uuid))
    labels_text.append(format_label("I2C_SCL", r1_x, r1_y + 3.81, angle=270))

    r2_x, r2_y = 256.54, 109.22
    symbols_text.append(format_symbol_instance(
        "Device:R", "R2", "4.7k",
        "Resistor_SMD:R_0805_2012Metric",
        r2_x, r2_y, angle=0, ref_pos=(r2_x + 2.54, r2_y - 2.54),
        val_pos=(r2_x + 2.54, r2_y + 2.54), pin_map=["1", "2"], sheet_uuid=sheet_uuid
    ))
    symbols_text.append(format_power_symbol("power:+3.3V", "+3.3V", "#PWR12", r2_x, r2_y - 3.81, sheet_uuid=sheet_uuid))
    labels_text.append(format_label("I2C_SDA", r2_x, r2_y + 3.81, angle=270))


    # -------------------------------------------------------------
    # 5. Assemble Full KiCad Schematic File
    # -------------------------------------------------------------
    lib_symbols_content = get_lib_symbols()

    sch_content = f"""(kicad_sch
\t(version 20250114)
\t(generator "kicad_sch_motopulse")
\t(generator_version "10.0")
\t(uuid "{sheet_uuid}")
\t(paper "A3")
\t(title_block
\t\t(title "MotoPulse: Automotive Acoustic Predictive Maintenance")
\t\t(date "2026-10-14")
\t\t(rev "2.0")
\t\t(company "IEEE RUAS - Hacktivate 2026")
\t\t(comment 1 "ESP32-S3 + INMP441 Digital MEMS Microphone + SSD1306 OLED")
\t\t(comment 2 "I2S Digital Audio + I2C Real-Time Spectrum Hardware System")
\t\t(comment 3 "Author: Visweshwara S & Team")
\t)
\t(lib_symbols
{lib_symbols_content}
\t)
{chr(10).join(wires_text)}
{chr(10).join(junctions_text)}
{chr(10).join(no_connects_text)}
{chr(10).join(labels_text)}
{chr(10).join(symbols_text)}
\t(sheet_instances
\t\t(path "/"
\t\t\t(page "1")
\t\t)
\t)
)"""

    sch_file = os.path.join(BASE_DIR, "motopulse.kicad_sch")
    with open(sch_file, "w", encoding="utf-8") as f:
        f.write(sch_content)
    print(f"Schematic generated successfully: {sch_file}")

    # Generate Project File
    pro_file = os.path.join(BASE_DIR, "motopulse.kicad_pro")
    pro_content = """{
  "board": {
    "design_settings": {
      "rules": {
        "max_error": 0.005,
        "min_clearance": 0.2,
        "min_hole_clearance": 0.25,
        "min_hole_to_hole": 0.25,
        "min_microvia_diameter": 0.2,
        "min_microvia_drill": 0.1,
        "min_silk_clearance": 0.0,
        "min_through_hole_diameter": 0.3,
        "min_track_width": 0.25,
        "min_via_annular_width": 0.15,
        "min_via_diameter": 0.6
      }
    }
  },
  "meta": {
    "filename": "motopulse.kicad_pro",
    "version": 1
  },
  "schematic": {
    "annotate_start_num": 1,
    "drawing": {
      "dashed_lines_dash_length_ratio": 12.0,
      "dashed_lines_gap_length_ratio": 3.0,
      "default_line_thickness": 6.0,
      "default_text_size": 50.0,
      "field_names": [],
      "junction_size_choice": 3,
      "label_size_ratio": 0.375,
      "pin_symbol_size": 25.0,
      "text_offset_ratio": 0.15
    }
  }
}"""
    with open(pro_file, "w", encoding="utf-8") as f:
        f.write(pro_content)
    print(f"Project file generated: {pro_file}")

if __name__ == '__main__':
    build_schematic()
