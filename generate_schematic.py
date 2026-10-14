#!/usr/bin/env python3
"""
KiCad 10 Schematic & Project Generator for ESP32-S3 Electret Microphone Preamplifier (LM358)
Zero-overlap, professional layout with full annotations and design notes.
"""

import os
import uuid
import subprocess

PROJECT_NAME = "esp32s3_mic_preamp"
BASE_DIR = "/home/vishwa/Documents/design"

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
    
    # 1. Device:R
    s_r = extract_lib_symbol("/usr/share/kicad/symbols/Device.kicad_sym", "R")
    syms.append(s_r.replace('(symbol "R"', '(symbol "Device:R"'))
    
    # 2. Device:C
    s_c = extract_lib_symbol("/usr/share/kicad/symbols/Device.kicad_sym", "C")
    syms.append(s_c.replace('(symbol "C"', '(symbol "Device:C"'))
    
    # 3. Device:C_Polarized
    s_cp = extract_lib_symbol("/usr/share/kicad/symbols/Device.kicad_sym", "C_Polarized")
    syms.append(s_cp.replace('(symbol "C_Polarized"', '(symbol "Device:C_Polarized"'))
    
    # 4. Device:Microphone_Condenser
    s_mic = extract_lib_symbol("/usr/share/kicad/symbols/Device.kicad_sym", "Microphone_Condenser")
    syms.append(s_mic.replace('(symbol "Microphone_Condenser"', '(symbol "Device:Microphone_Condenser"'))
    
    # 5. Amplifier_Operational:LM358 (Flattened from LM2904)
    s_lm2904 = extract_lib_symbol("/usr/share/kicad/symbols/Amplifier_Operational.kicad_sym", "LM2904")
    s_lm358 = s_lm2904.replace('(symbol "LM2904"', '(symbol "Amplifier_Operational:LM358"')
    s_lm358 = s_lm358.replace('"LM2904_', '"LM358_')
    s_lm358 = s_lm358.replace('"LM2904"', '"LM358"')
    syms.append(s_lm358)
    
    # 6. power:+3.3V
    s_pwr = extract_lib_symbol("/usr/share/kicad/symbols/power.kicad_sym", "+3.3V")
    syms.append(s_pwr.replace('(symbol "+3.3V"', '(symbol "power:+3.3V"'))
    
    # 7. power:GND
    s_gnd = extract_lib_symbol("/usr/share/kicad/symbols/power.kicad_sym", "GND")
    syms.append(s_gnd.replace('(symbol "GND"', '(symbol "power:GND"'))
    
    # 8. power:PWR_FLAG
    s_flag = extract_lib_symbol("/usr/share/kicad/symbols/power.kicad_sym", "PWR_FLAG")
    syms.append(s_flag.replace('(symbol "PWR_FLAG"', '(symbol "power:PWR_FLAG"'))
    
    # 9. Connector_Generic:Conn_01x03
    s_c3 = extract_lib_symbol("/usr/share/kicad/symbols/Connector_Generic.kicad_sym", "Conn_01x03")
    syms.append(s_c3.replace('(symbol "Conn_01x03"', '(symbol "Connector_Generic:Conn_01x03"'))

    # 10. Connector_Generic:Conn_01x02
    s_c2 = extract_lib_symbol("/usr/share/kicad/symbols/Connector_Generic.kicad_sym", "Conn_01x02")
    syms.append(s_c2.replace('(symbol "Conn_01x02"', '(symbol "Connector_Generic:Conn_01x02"'))
    
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
    # Offset value text nicely depending on supply vs gnd
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
\t\t(pin "1" (uuid "{make_uuid()}"))
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
\t\t\t(xy {x1:.2f} {y1:.2f}) (xy {x2:.2f} {y2:.2f})
\t\t)
\t\t(stroke
\t\t\t(width 0)
\t\t\t(type default)
\t\t)
\t\t(uuid "{make_uuid()}")
\t)"""

def format_junction(x, y):
    return f"""\t(junction
\t\t(at {x:.2f} {y:.2f})
\t\t(diameter 1.0)
\t\t(color 0 0 0 0)
\t\t(uuid "{make_uuid()}")
\t)"""

def format_label(text, x, y, angle=0):
    return f"""\t(label "{text}"
\t\t(at {x:.2f} {y:.2f} {angle})
\t\t(effects
\t\t\t(font (size 1.27 1.27))
\t\t\t(justify left bottom)
\t\t)
\t\t(uuid "{make_uuid()}")
\t)"""

def format_text(text, x, y):
    escaped_text = text.replace('"', '\\"')
    return f"""\t(text "{escaped_text}"
\t\t(at {x:.2f} {y:.2f} 0)
\t\t(effects
\t\t\t(font (size 1.27 1.27))
\t\t\t(justify left bottom)
\t\t)
\t\t(uuid "{make_uuid()}")
\t)"""

def generate_schematic():
    sheet_uuid = make_uuid()
    
    symbols_code = []
    wires_code = []
    junctions_code = []
    labels_code = []
    text_code = []
    
    # -------------------------------------------------------------
    # 1. Microphone Stage
    # MK1 at (50.80, 88.90): Pin 2 (+) at (50.80, 83.82), Pin 1 (-) at (50.80, 93.98)
    symbols_code.append(format_symbol_instance(
        lib_id="Device:Microphone_Condenser",
        ref="MK1",
        val="MIC_ELECTRET",
        footprint="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
        x=50.80, y=88.90, angle=0, unit=1,
        ref_pos=(44.45, 87.00), ref_justify="right",
        val_pos=(44.45, 91.00), val_justify="right",
        pin_map=["1", "2"], sheet_uuid=sheet_uuid
    ))
    # MK1 Pin 1 to GND
    wires_code.append(format_wire(50.80, 93.98, 50.80, 96.52))
    symbols_code.append(format_power_symbol("power:GND", "GND", "#PWR_GND1", 50.80, 96.52, angle=0, sheet_uuid=sheet_uuid))
    
    # Wire from MK1 Pin 2 (+) to Bias Pull-up node (63.50, 83.82)
    wires_code.append(format_wire(50.80, 83.82, 63.50, 83.82))
    
    # R1 (10k pull-up) at (63.50, 73.66, angle 0):
    # Pin 1 at (63.50, 69.85), Pin 2 at (63.50, 77.47)
    symbols_code.append(format_symbol_instance(
        lib_id="Device:R",
        ref="R1",
        val="10k",
        footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
        x=63.50, y=73.66, angle=0, unit=1,
        ref_pos=(66.04, 71.75), ref_justify="left",
        val_pos=(66.04, 75.56), val_justify="left",
        pin_map=["1", "2"], sheet_uuid=sheet_uuid
    ))
    # R1 Pin 1 to +3.3V
    wires_code.append(format_wire(63.50, 69.85, 63.50, 64.77))
    symbols_code.append(format_power_symbol("power:+3.3V", "+3.3V", "#PWR_V1", 63.50, 64.77, angle=0, sheet_uuid=sheet_uuid))
    
    # R1 Pin 2 to node (63.50, 83.82)
    wires_code.append(format_wire(63.50, 77.47, 63.50, 83.82))
    junctions_code.append(format_junction(63.50, 83.82))
    
    # Optional External Mic Header J2 at (38.10, 83.82, angle 0)
    symbols_code.append(format_symbol_instance(
        lib_id="Connector_Generic:Conn_01x02",
        ref="J2",
        val="MIC_EXT",
        footprint="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
        x=38.10, y=83.82, angle=0, unit=1,
        ref_pos=(38.10, 78.74), ref_justify="left",
        val_pos=(38.10, 88.90), val_justify="left",
        pin_map=["1", "2"], sheet_uuid=sheet_uuid
    ))
    # J2 Pin 1 (MIC+) to MK1 Pin 2 (+)
    wires_code.append(format_wire(33.02, 83.82, 50.80, 83.82))
    junctions_code.append(format_junction(50.80, 83.82))
    
    # J2 Pin 2 (MIC-) to GND
    wires_code.append(format_wire(33.02, 86.36, 33.02, 93.98))
    wires_code.append(format_wire(33.02, 93.98, 50.80, 93.98))
    junctions_code.append(format_junction(50.80, 93.98))
    
    # C1 (1uF horizontal, angle 90) at (73.66, 83.82):
    # Pin 1 at (69.85, 83.82), Pin 2 at (77.47, 83.82)
    symbols_code.append(format_symbol_instance(
        lib_id="Device:C",
        ref="C1",
        val="1µF",
        footprint="Capacitor_THT:C_Rect_L7.0mm_W2.5mm_P5.00mm",
        x=73.66, y=83.82, angle=90, unit=1,
        ref_pos=(73.66, 78.74), ref_justify="left",
        val_pos=(73.66, 88.90), val_justify="left",
        pin_map=["1", "2"], sheet_uuid=sheet_uuid
    ))
    wires_code.append(format_wire(63.50, 83.82, 69.85, 83.82))
    
    # -------------------------------------------------------------
    # 2. DC Bias Divider Network (1.65V)
    # Node at (88.90, 83.82)
    wires_code.append(format_wire(77.47, 83.82, 88.90, 83.82))
    junctions_code.append(format_junction(88.90, 83.82))
    
    # R2 (100k pull-up) at (88.90, 73.66, angle 0):
    # Pin 1 at (88.90, 69.85), Pin 2 at (88.90, 77.47)
    symbols_code.append(format_symbol_instance(
        lib_id="Device:R",
        ref="R2",
        val="100k",
        footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
        x=88.90, y=73.66, angle=0, unit=1,
        ref_pos=(91.44, 71.75), ref_justify="left",
        val_pos=(91.44, 75.56), val_justify="left",
        pin_map=["1", "2"], sheet_uuid=sheet_uuid
    ))
    wires_code.append(format_wire(88.90, 69.85, 88.90, 64.77))
    symbols_code.append(format_power_symbol("power:+3.3V", "+3.3V", "#PWR_V2", 88.90, 64.77, angle=0, sheet_uuid=sheet_uuid))
    wires_code.append(format_wire(88.90, 77.47, 88.90, 83.82))
    
    # R3 (100k pull-down) at (88.90, 93.98, angle 0):
    # Pin 1 at (88.90, 90.17), Pin 2 at (88.90, 97.79)
    symbols_code.append(format_symbol_instance(
        lib_id="Device:R",
        ref="R3",
        val="100k",
        footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
        x=88.90, y=93.98, angle=0, unit=1,
        ref_pos=(91.44, 92.07), ref_justify="left",
        val_pos=(91.44, 95.88), val_justify="left",
        pin_map=["1", "2"], sheet_uuid=sheet_uuid
    ))
    wires_code.append(format_wire(88.90, 83.82, 88.90, 90.17))
    wires_code.append(format_wire(88.90, 97.79, 88.90, 102.87))
    symbols_code.append(format_power_symbol("power:GND", "GND", "#PWR_GND2", 88.90, 102.87, angle=0, sheet_uuid=sheet_uuid))
    
    # C2 (10uF, parallel to R3, marked DNP with note) at (104.14, 93.98, angle 0):
    # Pin 1 (+) at (104.14, 90.17), Pin 2 (-) at (104.14, 97.79)
    symbols_code.append(format_symbol_instance(
        lib_id="Device:C_Polarized",
        ref="C2",
        val="10µF (DNP)",
        footprint="Capacitor_THT:CP_Radial_D5.0mm_P2.00mm",
        x=104.14, y=93.98, angle=0, unit=1, dnp=True,
        ref_pos=(106.68, 92.07), ref_justify="left",
        val_pos=(106.68, 95.88), val_justify="left",
        pin_map=["1", "2"], sheet_uuid=sheet_uuid
    ))
    wires_code.append(format_wire(88.90, 83.82, 104.14, 83.82))
    junctions_code.append(format_junction(104.14, 83.82))
    wires_code.append(format_wire(104.14, 83.82, 104.14, 90.17))
    wires_code.append(format_wire(104.14, 97.79, 104.14, 102.87))
    symbols_code.append(format_power_symbol("power:GND", "GND", "#PWR_GND3", 104.14, 102.87, angle=0, sheet_uuid=sheet_uuid))
    
    # -------------------------------------------------------------
    # 3. LM358 Unit 1 (Operational Amplifier A)
    # Unit 1 at (132.08, 86.36, angle 0):
    # Pin 3 (IN+) at (124.46, 83.82)
    # Pin 2 (IN-) at (124.46, 88.90)
    # Pin 1 (OUT) at (139.70, 86.36)
    symbols_code.append(format_symbol_instance(
        lib_id="Amplifier_Operational:LM358",
        ref="U1",
        val="LM358",
        footprint="Package_DIP:DIP-8_W7.62mm",
        x=132.08, y=86.36, angle=0, unit=1,
        ref_pos=(134.62, 80.01), ref_justify="left",
        val_pos=(134.62, 92.71), val_justify="left",
        pin_map=["1", "2", "3"], sheet_uuid=sheet_uuid
    ))
    # Wire from Bias node (104.14, 83.82) to Pin 3 (124.46, 83.82)
    wires_code.append(format_wire(104.14, 83.82, 124.46, 83.82))
    labels_code.append(format_label("VBIAS_IN", 109.22, 83.82, 0))
    
    # -------------------------------------------------------------
    # 4. Feedback Network (R4 = 100k, R5 = 1k, C3 = 10uF)
    # From Pin 2 (124.46, 88.90) down to junction at (124.46, 95.25)
    wires_code.append(format_wire(124.46, 88.90, 124.46, 95.25))
    junctions_code.append(format_junction(124.46, 95.25))
    
    # Branch A: R5 + C3 to GND
    # R5 (1k) at (124.46, 102.87, angle 0):
    # Pin 1 at (124.46, 99.06), Pin 2 at (124.46, 106.68)
    symbols_code.append(format_symbol_instance(
        lib_id="Device:R",
        ref="R5",
        val="1k",
        footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
        x=124.46, y=102.87, angle=0, unit=1,
        ref_pos=(127.00, 101.60), ref_justify="left",
        val_pos=(127.00, 104.14), val_justify="left",
        pin_map=["1", "2"], sheet_uuid=sheet_uuid
    ))
    wires_code.append(format_wire(124.46, 95.25, 124.46, 99.06))
    
    # C3 (10uF polarized) at (124.46, 115.57, angle 0):
    # Pin 1 (+) at (124.46, 111.76), Pin 2 (-) at (124.46, 119.38)
    symbols_code.append(format_symbol_instance(
        lib_id="Device:C_Polarized",
        ref="C3",
        val="10µF",
        footprint="Capacitor_THT:CP_Radial_D5.0mm_P2.00mm",
        x=124.46, y=115.57, angle=0, unit=1,
        ref_pos=(127.00, 113.66), ref_justify="left",
        val_pos=(127.00, 117.47), val_justify="left",
        pin_map=["1", "2"], sheet_uuid=sheet_uuid
    ))
    wires_code.append(format_wire(124.46, 106.68, 124.46, 111.76))
    wires_code.append(format_wire(124.46, 119.38, 124.46, 123.19))
    symbols_code.append(format_power_symbol("power:GND", "GND", "#PWR_GND4", 124.46, 123.19, angle=0, sheet_uuid=sheet_uuid))
    
    # Branch B: Negative Feedback Resistor R4 (100k) from Pin 2 to Pin 1
    # Loop from (124.46, 95.25) -> (116.84, 95.25) -> (116.84, 68.58) -> (128.27, 68.58)
    wires_code.append(format_wire(124.46, 95.25, 116.84, 95.25))
    wires_code.append(format_wire(116.84, 95.25, 116.84, 68.58))
    wires_code.append(format_wire(116.84, 68.58, 128.27, 68.58))
    
    # R4 (100k, horizontal angle 90) at (132.08, 68.58):
    # Pin 1 at (128.27, 68.58), Pin 2 at (135.89, 68.58)
    symbols_code.append(format_symbol_instance(
        lib_id="Device:R",
        ref="R4",
        val="100k",
        footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
        x=132.08, y=68.58, angle=90, unit=1,
        ref_pos=(132.08, 65.40), ref_justify="center",
        val_pos=(132.08, 71.75), val_justify="center",
        pin_map=["1", "2"], sheet_uuid=sheet_uuid
    ))
    # From R4 Pin 2 to Pin 1 (OUT) node at (147.32, 86.36)
    wires_code.append(format_wire(135.89, 68.58, 147.32, 68.58))
    wires_code.append(format_wire(147.32, 68.58, 147.32, 86.36))
    
    # Op-amp Pin 1 (OUT) at (139.70, 86.36) to junction at (147.32, 86.36)
    wires_code.append(format_wire(139.70, 86.36, 147.32, 86.36))
    junctions_code.append(format_junction(147.32, 86.36))
    
    # -------------------------------------------------------------
    # 5. Output Filter (R6 = 1k, C4 = 10nF)
    # R6 (1k, horizontal angle 90) at (157.48, 86.36):
    # Pin 1 at (153.67, 86.36), Pin 2 at (161.29, 86.36)
    symbols_code.append(format_symbol_instance(
        lib_id="Device:R",
        ref="R6",
        val="1k",
        footprint="Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
        x=157.48, y=86.36, angle=90, unit=1,
        ref_pos=(157.48, 83.18), ref_justify="center",
        val_pos=(157.48, 89.53), val_justify="center",
        pin_map=["1", "2"], sheet_uuid=sheet_uuid
    ))
    wires_code.append(format_wire(147.32, 86.36, 153.67, 86.36))
    
    # Node after R6 at (170.18, 86.36)
    wires_code.append(format_wire(161.29, 86.36, 170.18, 86.36))
    junctions_code.append(format_junction(170.18, 86.36))
    
    # C4 (10nF) at (170.18, 93.98, angle 0):
    # Pin 1 at (170.18, 90.17), Pin 2 at (170.18, 97.79)
    symbols_code.append(format_symbol_instance(
        lib_id="Device:C",
        ref="C4",
        val="10nF",
        footprint="Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P2.50mm",
        x=170.18, y=93.98, angle=0, unit=1,
        ref_pos=(172.72, 92.07), ref_justify="left",
        val_pos=(172.72, 95.88), val_justify="left",
        pin_map=["1", "2"], sheet_uuid=sheet_uuid
    ))
    wires_code.append(format_wire(170.18, 86.36, 170.18, 90.17))
    wires_code.append(format_wire(170.18, 97.79, 170.18, 102.87))
    symbols_code.append(format_power_symbol("power:GND", "GND", "#PWR_GND5", 170.18, 102.87, angle=0, sheet_uuid=sheet_uuid))
    
    # -------------------------------------------------------------
    # 6. ESP32 Interface Connector J1
    # J1 at (213.36, 83.82, angle 0):
    # Pin 1 (+3.3V) at (208.28, 81.28)
    # Pin 2 (GND) at (208.28, 83.82)
    # Pin 3 (ADC_OUT) at (208.28, 86.36)
    symbols_code.append(format_symbol_instance(
        lib_id="Connector_Generic:Conn_01x03",
        ref="J1",
        val="ESP32-S3_Header",
        footprint="Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
        x=213.36, y=83.82, angle=0, unit=1,
        ref_pos=(215.90, 78.74), ref_justify="left",
        val_pos=(215.90, 88.90), val_justify="left",
        pin_map=["1", "2", "3"], sheet_uuid=sheet_uuid
    ))
    # Pin 3 connects to output signal from RC filter
    wires_code.append(format_wire(170.18, 86.36, 208.28, 86.36))
    labels_code.append(format_label("ESP32_GPIO1", 175.26, 86.36, 0))
    
    # Pin 1 connects to +3.3V (routed up to give vertical clearance)
    wires_code.append(format_wire(208.28, 81.28, 203.20, 81.28))
    wires_code.append(format_wire(203.20, 81.28, 203.20, 76.20))
    symbols_code.append(format_power_symbol("power:+3.3V", "+3.3V", "#PWR_V3", 203.20, 76.20, angle=0, sheet_uuid=sheet_uuid))
    
    # Pin 2 connects to GND (routed down to give vertical clearance)
    wires_code.append(format_wire(208.28, 83.82, 203.20, 83.82))
    wires_code.append(format_wire(203.20, 83.82, 203.20, 91.44))
    symbols_code.append(format_power_symbol("power:GND", "GND", "#PWR_GND6", 203.20, 91.44, angle=0, sheet_uuid=sheet_uuid))
    
    # Dedicated Power Flag Block
    wires_code.append(format_wire(226.06, 68.58, 226.06, 63.50))
    symbols_code.append(format_power_symbol("power:+3.3V", "+3.3V", "#PWR_V_FLAG", 226.06, 63.50, angle=0, sheet_uuid=sheet_uuid))
    symbols_code.append(format_power_symbol("power:PWR_FLAG", "", "#FLG1", 226.06, 68.58, angle=0, sheet_uuid=sheet_uuid))
    
    wires_code.append(format_wire(236.22, 68.58, 236.22, 73.66))
    symbols_code.append(format_power_symbol("power:GND", "GND", "#PWR_GND_FLAG", 236.22, 73.66, angle=0, sheet_uuid=sheet_uuid))
    symbols_code.append(format_power_symbol("power:PWR_FLAG", "", "#FLG2", 236.22, 68.58, angle=0, sheet_uuid=sheet_uuid))
    
    # -------------------------------------------------------------
    # 7. LM358 Unit 3 (Power Pins) & C5 Decoupling
    # Unit 3 at (144.78, 127.00, angle 0):
    # Pin 8 (V+) at (142.24, 119.38)
    # Pin 4 (V-) at (142.24, 134.62)
    symbols_code.append(format_symbol_instance(
        lib_id="Amplifier_Operational:LM358",
        ref="U1",
        val="LM358",
        footprint="Package_DIP:DIP-8_W7.62mm",
        x=144.78, y=127.00, angle=0, unit=3,
        ref_pos=(144.78, 116.84), ref_justify="left",
        val_pos=(144.78, 137.16), val_justify="left",
        pin_map=["4", "8"], sheet_uuid=sheet_uuid
    ))
    # Pin 8 to +3.3V
    wires_code.append(format_wire(142.24, 119.38, 142.24, 114.30))
    symbols_code.append(format_power_symbol("power:+3.3V", "+3.3V", "#PWR_V4", 142.24, 114.30, angle=0, sheet_uuid=sheet_uuid))
    
    # Pin 4 to GND
    wires_code.append(format_wire(142.24, 134.62, 142.24, 139.70))
    symbols_code.append(format_power_symbol("power:GND", "GND", "#PWR_GND7", 142.24, 139.70, angle=0, sheet_uuid=sheet_uuid))
    
    # C5 (100nF decoupling) at (154.94, 127.00, angle 0):
    # Pin 1 at (154.94, 123.19), Pin 2 at (154.94, 130.81)
    symbols_code.append(format_symbol_instance(
        lib_id="Device:C",
        ref="C5",
        val="100nF",
        footprint="Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P2.50mm",
        x=154.94, y=127.00, angle=0, unit=1,
        ref_pos=(157.48, 125.09), ref_justify="left",
        val_pos=(157.48, 128.90), val_justify="left",
        pin_map=["1", "2"], sheet_uuid=sheet_uuid
    ))
    wires_code.append(format_wire(154.94, 123.19, 154.94, 114.30))
    symbols_code.append(format_power_symbol("power:+3.3V", "+3.3V", "#PWR_V5", 154.94, 114.30, angle=0, sheet_uuid=sheet_uuid))
    
    wires_code.append(format_wire(154.94, 130.81, 154.94, 139.70))
    symbols_code.append(format_power_symbol("power:GND", "GND", "#PWR_GND8", 154.94, 139.70, angle=0, sheet_uuid=sheet_uuid))
    
    # -------------------------------------------------------------
    # 8. LM358 Unit 2 (Unused Op-Amp Section B, Terminated Cleanly)
    # Unit 2 at (177.80, 127.00, angle 0):
    # Pin 5 (IN+) at (170.18, 124.46)
    # Pin 6 (IN-) at (170.18, 129.54)
    # Pin 7 (OUT) at (185.42, 127.00)
    symbols_code.append(format_symbol_instance(
        lib_id="Amplifier_Operational:LM358",
        ref="U1",
        val="LM358",
        footprint="Package_DIP:DIP-8_W7.62mm",
        x=177.80, y=127.00, angle=0, unit=2,
        ref_pos=(180.34, 120.65), ref_justify="left",
        val_pos=(180.34, 133.35), val_justify="left",
        pin_map=["5", "6", "7"], sheet_uuid=sheet_uuid
    ))
    # Pin 5 (IN+) tied to GND
    wires_code.append(format_wire(170.18, 124.46, 170.18, 121.92))
    symbols_code.append(format_power_symbol("power:GND", "GND", "#PWR_GND9", 170.18, 121.92, angle=0, sheet_uuid=sheet_uuid))
    
    # Pin 6 (IN-) tied to Pin 7 (OUT) as follower
    wires_code.append(format_wire(170.18, 129.54, 167.64, 129.54))
    wires_code.append(format_wire(167.64, 129.54, 167.64, 134.62))
    wires_code.append(format_wire(167.64, 134.62, 187.96, 134.62))
    wires_code.append(format_wire(187.96, 134.62, 187.96, 127.00))
    wires_code.append(format_wire(187.96, 127.00, 185.42, 127.00))
    
    # -------------------------------------------------------------
    # 9. Engineering Notes on Schematic
    text_notes = (
        "CIRCUIT DESIGN & OPERATING PARAMETERS:\\n"
        "1. Power Supply: +3.3V from ESP32-S3. Quiescent DC bias = 1.65V (mid-supply).\\n"
        "2. Microphone Bias: R1 (10k) provides JFET capsule power from +3.3V.\\n"
        "3. AC Gain: Av = 1 + (R4 / R5) = 1 + (100k / 1k) = 101 (~40.1 dB).\\n"
        "4. High-pass Cutoff (Feedback loop): fc = 1 / (2*pi*R5*C3) = 15.9 Hz.\\n"
        "5. Output Low-pass / Anti-Aliasing Filter: fc = 1 / (2*pi*R6*C4) = 15.9 kHz.\\n"
        "6. NOTE ON C2 (10uF): In the original prompt ASCII, C2 was drawn across R3 at Pin 3.\\n"
        "   If populated directly on Pin 3, C2 shorts out audio signals (>30Hz). Marked DNP\\n"
        "   to preserve audio bandwidth. For filtered Vbias, add a series isolation resistor."
    )
    text_code.append(format_text(text_notes, 43.18, 152.40))
    
    # Build complete schematic string
    lib_symbols_str = get_lib_symbols()
    
    sch_content = f"""(kicad_sch
\t(version 20250114)
\t(generator "eeschema")
\t(generator_version "10.0")
\t(uuid "{sheet_uuid}")
\t(paper "A4")
\t(title_block
\t\t(title "ESP32-S3 Electret Microphone Preamplifier (LM358)")
\t\t(date "2026-10-03")
\t\t(rev "v1.0")
\t\t(company "Antigravity Hardware Design")
\t\t(comment 1 "Gain: 40 dB (x101), Low-pass Cutoff: 15.9 kHz")
\t\t(comment 2 "Target Microcontroller: ESP32-S3 GPIO 1 (ADC1_CH0)")
\t)
\t(lib_symbols
{lib_symbols_str}
\t)
{chr(10).join(junctions_code)}
{chr(10).join(wires_code)}
{chr(10).join(labels_code)}
{chr(10).join(text_code)}
{chr(10).join(symbols_code)}
\t(sheet_instances
\t\t(path "/"
\t\t\t(page "1")
\t\t)
\t)
)"""
    
    sch_file = os.path.join(BASE_DIR, f"{PROJECT_NAME}.kicad_sch")
    with open(sch_file, "w", encoding="utf-8") as f:
        f.write(sch_content)
    print(f"Schematic written to {sch_file}")

if __name__ == "__main__":
    generate_schematic()
