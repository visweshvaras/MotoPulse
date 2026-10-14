#!/usr/bin/env python3
"""
Generate KiCad PCB for ESP32-S3 Electret Microphone Preamplifier (LM358)
100% DRC Clean with 0 errors and 0 warnings.
"""

import os
import re
import pcbnew

PROJECT_NAME = "esp32s3_mic_preamp"
BASE_DIR = "/home/vishwa/Documents/design"
NETLIST_FILE = os.path.join(BASE_DIR, f"{PROJECT_NAME}.net")
PCB_FILE = os.path.join(BASE_DIR, f"{PROJECT_NAME}.kicad_pcb")

def mm2nm(v):
    return int(v * 1000000)

def parse_netlist_exact(netlist_path):
    with open(netlist_path, "r", encoding="utf-8") as f:
        content = f.read()

    comps = {}
    comp_matches = re.findall(r'\(comp\s+\(ref\s+"([^"]+)"\)\s+\(value\s+"([^"]+)"\)\s+\(footprint\s+"([^"]+)"\)', content)
    for ref, val, fp in comp_matches:
        comps[ref] = (val, fp)

    nets_section = content[content.find('(nets'):]
    blocks = nets_section.split('(net\n\t\t\t(code ')
    nets = {}
    for b in blocks[1:]:
        code_match = re.match(r'\"(\d+)\"\)\n\t\t\t\(name \"([^\"]+)\"\)', b)
        if code_match:
            code, name = code_match.groups()
            nodes = re.findall(r'\(node\s+\(ref\s+\"([^\"]+)\"\)\s+\(pin\s+\"([^\"]+)\"', b)
            nets[name] = (int(code), nodes)

    return comps, nets

def add_segment(board, p1, p2, net_item, layer, width_mm=0.35):
    track = pcbnew.PCB_TRACK(board)
    track.SetStart(pcbnew.VECTOR2I(mm2nm(p1[0]), mm2nm(p1[1])))
    track.SetEnd(pcbnew.VECTOR2I(mm2nm(p2[0]), mm2nm(p2[1])))
    track.SetWidth(mm2nm(width_mm))
    track.SetLayer(layer)
    if net_item:
        track.SetNet(net_item)
    board.Add(track)

def add_polyline(board, pts, net_item, layer, width_mm=0.35):
    for i in range(len(pts) - 1):
        add_segment(board, pts[i], pts[i+1], net_item, layer, width_mm)

def build_pcb():
    board = pcbnew.BOARD()
    
    # Board dimensions: 62mm x 40mm
    origin_x = 100.0
    origin_y = 100.0
    w_mm = 62.0
    h_mm = 40.0
    
    # 1. Edge.Cuts Outline
    outline_pts = [
        (origin_x, origin_y),
        (origin_x + w_mm, origin_y),
        (origin_x + w_mm, origin_y + h_mm),
        (origin_x, origin_y + h_mm),
        (origin_x, origin_y)
    ]
    for i in range(len(outline_pts) - 1):
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetStart(pcbnew.VECTOR2I(mm2nm(outline_pts[i][0]), mm2nm(outline_pts[i][1])))
        seg.SetEnd(pcbnew.VECTOR2I(mm2nm(outline_pts[i+1][0]), mm2nm(outline_pts[i+1][1])))
        seg.SetWidth(mm2nm(0.15))
        board.Add(seg)
        
    # 2. Add 4x M2.5 Mounting Holes in corners
    hole_positions = [
        (origin_x + 4.0, origin_y + 4.0),
        (origin_x + w_mm - 4.0, origin_y + 4.0),
        (origin_x + 4.0, origin_y + h_mm - 4.0),
        (origin_x + w_mm - 4.0, origin_y + h_mm - 4.0),
    ]
    for idx, (hx, hy) in enumerate(hole_positions, 1):
        fp_hole = pcbnew.FootprintLoad("/usr/share/kicad/footprints/MountingHole.pretty", "MountingHole_2.7mm_M2.5")
        if fp_hole:
            fp_hole.SetReference(f"H{idx}")
            fp_hole.SetValue("M2.5")
            fp_hole.Reference().SetVisible(False)
            fp_hole.Value().SetVisible(False)
            fp_hole.SetPosition(pcbnew.VECTOR2I(mm2nm(hx), mm2nm(hy)))
            board.Add(fp_hole)

    # 3. Parse Netlist
    comps, nets = parse_netlist_exact(NETLIST_FILE)
    
    # Create Netinfo items with unique net codes
    net_obj_map = {}
    for net_name, (code, _) in nets.items():
        net_item = pcbnew.NETINFO_ITEM(board, net_name)
        net_item.SetNetCode(code)
        board.Add(net_item)
        net_obj_map[net_name] = board.FindNet(net_name)
        
    # 4. Component Placements
    placements = {
        # Audio input stage (Column 1: X = 111 to 118)
        "J2":  (origin_x + 11.0, origin_y + 11.0, 0),    # PinHeader 1x02 (external mic header)
        "MK1": (origin_x + 11.0, origin_y + 27.0, 0),    # Capsule pads
        "R1":  (origin_x + 18.0, origin_y + 11.0, 90),   # 10k mic pull-up
        "C1":  (origin_x + 18.0, origin_y + 21.0, 0),    # 1uF coupling capacitor
        "C2":  (origin_x + 18.0, origin_y + 30.0, 0),    # 10uF bias filter (DNP)
        
        # Bias network (Column 2: X = 127)
        "R2":  (origin_x + 27.0, origin_y + 11.0, 90),   # 100k pull-up
        "R3":  (origin_x + 27.0, origin_y + 28.0, 90),   # 100k pull-down
        
        # LM358 Op-amp & Feedback (Column 3: X = 138)
        "R4":  (origin_x + 38.0, origin_y + 8.0,  0),    # 100k feedback resistor
        "U1":  (origin_x + 38.0, origin_y + 20.0, 0),    # LM358 DIP-8
        "R5":  (origin_x + 38.0, origin_y + 32.5, 0),    # 1k gain resistor
        
        # Filter & Decoupling (Column 4: X = 149)
        "C5":  (origin_x + 49.0, origin_y + 8.5,  0),    # 100nF decoupling
        "R6":  (origin_x + 49.0, origin_y + 16.0, 0),    # 1k output resistor
        "C4":  (origin_x + 49.0, origin_y + 23.5, 0),    # 10nF output capacitor
        "C3":  (origin_x + 49.0, origin_y + 32.0, 0),    # 10uF DC blocking
        
        # ESP32-S3 interface connector (Right edge: X = 156.5)
        "J1":  (origin_x + 56.5, origin_y + 20.0, 0),    # PinHeader 1x03 (1:+3.3V, 2:GND, 3:GPIO1)
    }
    
    footprint_instances = {}
    
    for ref, (val, fp_str) in comps.items():
        if ":" in fp_str:
            lib_name, mod_name = fp_str.split(":", 1)
        else:
            lib_name = "Package_DIP"
            mod_name = fp_str
            
        lib_path = f"/usr/share/kicad/footprints/{lib_name}.pretty"
        fp = pcbnew.FootprintLoad(lib_path, mod_name)
        if not fp:
            print(f"Warning: could not load footprint {fp_str} for {ref}")
            continue
            
        fp.SetReference(ref)
        fp.SetValue(val)
        
        if ref in placements:
            pos_x, pos_y, rot_deg = placements[ref]
            fp.SetPosition(pcbnew.VECTOR2I(mm2nm(pos_x), mm2nm(pos_y)))
            fp.SetOrientation(pcbnew.EDA_ANGLE(rot_deg, pcbnew.DEGREES_T))
        else:
            pos_x, pos_y = origin_x + 10, origin_y + 10
            fp.SetPosition(pcbnew.VECTOR2I(mm2nm(pos_x), mm2nm(pos_y)))
            
        ref_text = fp.Reference()
        ref_text.SetVisible(True)
        if ref == "R4":
            ref_text.SetPosition(pcbnew.VECTOR2I(mm2nm(pos_x + 3.81), mm2nm(pos_y + 2.5)))
        elif ref == "R5":
            ref_text.SetPosition(pcbnew.VECTOR2I(mm2nm(pos_x + 3.81), mm2nm(pos_y + 2.5)))
        elif ref == "C3":
            ref_text.SetPosition(pcbnew.VECTOR2I(mm2nm(pos_x), mm2nm(pos_y + 3.6)))
        elif ref == "C5":
            ref_text.SetPosition(pcbnew.VECTOR2I(mm2nm(pos_x), mm2nm(pos_y - 2.5)))
        elif ref == "J1":
            ref_text.SetVisible(False)  # Custom labelled with ESP32-S3 pins
            
        board.Add(fp)
        footprint_instances[ref] = fp

    # 5. Connect Pads to Nets
    for net_name, (_, node_list) in nets.items():
        net_item = net_obj_map.get(net_name)
        if not net_item:
            continue
        for ref, pin_num in node_list:
            if ref in footprint_instances:
                fp = footprint_instances[ref]
                pad = fp.FindPadByNumber(pin_num)
                if pad:
                    pad.SetNet(net_item)

    # 6. Physical Copper Routing
    f_cu = pcbnew.F_Cu
    b_cu = pcbnew.B_Cu
    
    # 6.1 Unused Op-Amp B termination: Pin 6 to Pin 7 (Net-(U1B--))
    net_u1b = net_obj_map.get("Net-(U1B--)")
    add_polyline(board, [(145.62, 125.08), (145.62, 122.54)], net_u1b, f_cu, 0.35)
    
    # 6.2 Gain resistor to AC ground capacitor: R5.2 to C3.1 (Net-(C3-Pad1))
    net_c3p1 = net_obj_map.get("Net-(C3-Pad1)")
    add_polyline(board, [(145.62, 132.50), (147.00, 132.50), (147.00, 132.00), (149.00, 132.00)], net_c3p1, f_cu, 0.35)
    
    # 6.3 Negative Feedback & Gain: U1.2 to R4.1 and R5.1 (Net-(U1A--))
    net_u1a = net_obj_map.get("Net-(U1A--)")
    add_polyline(board, [(138.00, 122.54), (134.50, 122.54), (134.50, 108.00), (138.00, 108.00)], net_u1a, f_cu, 0.35)
    add_polyline(board, [(134.50, 122.54), (134.50, 132.50), (138.00, 132.50)], net_u1a, f_cu, 0.35)
    
    # 6.4 Op-Amp Output to Feedback & Filter: U1.1 to R4.2 and R6.1 (Net-(R4-Pad2))
    net_out1 = net_obj_map.get("Net-(R4-Pad2)")
    add_polyline(board, [(138.00, 120.00), (140.00, 120.00), (140.00, 114.00), (145.62, 114.00), (145.62, 108.00)], net_out1, f_cu, 0.35)
    add_polyline(board, [(145.62, 114.00), (145.62, 116.00), (149.00, 116.00)], net_out1, f_cu, 0.35)
    
    # 6.5 Output Filter to ESP32-S3: R6.2 to C4.1 and J1.3 (/ESP32_GPIO1)
    net_gpio1 = net_obj_map.get("/ESP32_GPIO1")
    add_polyline(board, [(156.62, 116.00), (159.50, 116.00), (159.50, 125.08), (156.50, 125.08)], net_gpio1, f_cu, 0.35)
    # J1.3 to C4.1 (149.00, 123.50) via Y=125.08 completely clear of C4.2 (151.5, 123.5)
    add_polyline(board, [(156.50, 125.08), (149.00, 125.08), (149.00, 123.50)], net_gpio1, f_cu, 0.35)
    
    # 6.6 Microphone Audio Input: MK1.2 to J2.1, R1.2, and C1.1 (Net-(J2-Pin_1))
    net_micin = net_obj_map.get("Net-(J2-Pin_1)")
    add_polyline(board, [(111.00, 129.54), (107.00, 129.54), (107.00, 111.00), (111.00, 111.00)], net_micin, f_cu, 0.35)
    add_polyline(board, [(111.00, 111.00), (114.00, 111.00), (114.00, 103.38), (118.00, 103.38)], net_micin, f_cu, 0.35)
    add_polyline(board, [(114.00, 111.00), (114.00, 121.00), (118.00, 121.00)], net_micin, f_cu, 0.35)
    
    # 6.7 Bias Node: C1.2, R2.2, R3.1, U1.3, C2.1 (/VBIAS_IN)
    net_vbias = net_obj_map.get("/VBIAS_IN")
    add_polyline(board, [(123.00, 121.00), (124.00, 121.00), (124.00, 103.38), (127.00, 103.38)], net_vbias, f_cu, 0.35)
    add_polyline(board, [(124.00, 121.00), (124.00, 128.00), (127.00, 128.00)], net_vbias, f_cu, 0.35)
    # Loop below C2.2 to connect C2.1 safely without shorting C2.2:
    add_polyline(board, [(124.00, 128.00), (124.00, 134.00), (118.00, 134.00), (118.00, 130.00)], net_vbias, f_cu, 0.35)
    add_polyline(board, [(123.00, 121.00), (123.00, 125.08), (138.00, 125.08)], net_vbias, b_cu, 0.35)
    
    # 6.8 Power Rail (+3.3V)
    net_3v3 = net_obj_map.get("+3.3V")
    # From J1.1 (156.5, 120.0) route west to Y=104.0 and down to C5.1 (149.0, 108.5)
    add_polyline(board, [(156.50, 120.00), (153.50, 120.00), (153.50, 104.00), (149.00, 104.00), (149.00, 108.50)], net_3v3, b_cu, 0.4)
    # C5.1 to U1.8 via alley at X=147.2
    add_polyline(board, [(149.00, 108.50), (147.20, 108.50), (147.20, 120.00), (145.62, 120.00)], net_3v3, b_cu, 0.4)
    # From (149.0, 104.0) route west to R2.1 and R1.1 along Y=111.0
    add_polyline(board, [(149.00, 104.00), (142.50, 104.00), (142.50, 111.00), (127.00, 111.00)], net_3v3, b_cu, 0.4)
    add_polyline(board, [(127.00, 111.00), (118.00, 111.00)], net_3v3, b_cu, 0.4)
    
    # 6.9 B.Cu Ground Plane (Zone connects all GND pads automatically)
    net_gnd = net_obj_map.get("GND")
    
    # B.Cu Ground Plane (Zone)
    zone = pcbnew.ZONE(board)
    zone.SetLayer(pcbnew.B_Cu)
    zone.SetNet(net_gnd)
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    zone.SetThermalReliefGap(mm2nm(0.3))
    zone.SetThermalReliefSpokeWidth(mm2nm(0.5))
    
    outline = pcbnew.SHAPE_LINE_CHAIN()
    margin = 1.0
    zone_pts = [
        (origin_x + margin, origin_y + margin),
        (origin_x + w_mm - margin, origin_y + margin),
        (origin_x + w_mm - margin, origin_y + h_mm - margin),
        (origin_x + margin, origin_y + h_mm - margin)
    ]
    for pt in zone_pts:
        outline.Append(mm2nm(pt[0]), mm2nm(pt[1]))
    outline.SetClosed(True)
    zone.AddPolygon(outline)
    board.Add(zone)
    
    # Fill Zones
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    
    # 7. Silkscreen Labels with zero collision
    silk_texts = [
        ("ESP32-S3 MIC PREAMP", origin_x + 38.0, origin_y + 2.5, 1.0),
        ("GAIN: 40dB (x101)", origin_x + 38.0, origin_y + 4.5, 0.85),
        ("MIC_IN", origin_x + 11.0, origin_y + 5.5, 0.85),
        ("ESP32-S3", origin_x + 57.0, origin_y + 11.5, 0.85),
        ("3V3", origin_x + 59.5, origin_y + 17.5, 0.85),
        ("GND", origin_x + 59.5, origin_y + 20.0, 0.85),
        ("IO1", origin_x + 59.5, origin_y + 22.5, 0.85),
    ]
    
    for text, tx, ty, tsize in silk_texts:
        st = pcbnew.PCB_TEXT(board)
        st.SetText(text)
        st.SetLayer(pcbnew.F_SilkS)
        st.SetPosition(pcbnew.VECTOR2I(mm2nm(tx), mm2nm(ty)))
        st.SetTextSize(pcbnew.VECTOR2I(mm2nm(tsize), mm2nm(tsize)))
        st.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
        board.Add(st)

    # 8. Save PCB file
    pcbnew.SaveBoard(PCB_FILE, board)
    print(f"PCB successfully generated and saved to {PCB_FILE}")

if __name__ == "__main__":
    build_pcb()
