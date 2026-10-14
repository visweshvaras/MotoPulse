#!/usr/bin/env python3
"""
solve_routing.py
DRC-Zero generator for MotoPulse PCB.
"""

import os
import re
import pcbnew

PROJECT_NAME = "motopulse"
BASE_DIR = "/home/vishwa/Documents/hacktivate/motopulse_kicad"
NETLIST_FILE = os.path.join(BASE_DIR, f"{PROJECT_NAME}.net")
PCB_FILE = os.path.join(BASE_DIR, f"{PROJECT_NAME}.kicad_pcb")

def mm2nm(v):
    return int(round(v * 1000000))

def nm2mm(v):
    return v / 1000000.0

def parse_netlist(netlist_path):
    with open(netlist_path, "r", encoding="utf-8") as f:
        content = f.read()

    comps = {}
    comp_matches = re.findall(r'\(comp\s+\(ref\s+"([^"]+)"\)\s+\(value\s+"([^"]+)"\)\s+\(footprint\s+"([^"]+)"\)', content)
    for ref, val, fp in comp_matches:
        comps[ref] = (val, fp)

    nets_section = content[content.find('(nets'):]
    blocks = re.split(r'\(net\s+\(code\s+', nets_section)
    nets = {}
    for b in blocks[1:]:
        m_head = re.match(r'\"(\d+)\"\)\s+\(name\s+\"([^\"]+)\"\)', b)
        if m_head:
            code, name = m_head.groups()
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
        track.SetNetCode(net_item.GetNetCode())
    board.Add(track)

def add_polyline(board, pts, net_item, layer, width_mm=0.35):
    for i in range(len(pts) - 1):
        if pts[i] != pts[i+1]:
            add_segment(board, pts[i], pts[i+1], net_item, layer, width_mm)

def add_via(board, pos, net_item, diameter_mm=0.8, drill_mm=0.4):
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(pcbnew.VECTOR2I(mm2nm(pos[0]), mm2nm(pos[1])))
    via.SetWidth(mm2nm(diameter_mm))
    via.SetDrill(mm2nm(drill_mm))
    if net_item:
        via.SetNet(net_item)
        via.SetNetCode(net_item.GetNetCode())
    board.Add(via)

def build_pcb():
    board = pcbnew.BOARD()
    
    origin_x = 100.0
    origin_y = 100.0
    w_mm = 100.0
    h_mm = 95.0

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

    # 2. 4x M2.5 Mounting Holes in corners
    hole_positions = [
        (origin_x + 5.0, origin_y + 5.0),
        (origin_x + w_mm - 5.0, origin_y + 5.0),
        (origin_x + 5.0, origin_y + h_mm - 5.0),
        (origin_x + w_mm - 5.0, origin_y + h_mm - 5.0),
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
    comps, nets = parse_netlist(NETLIST_FILE)
    
    net_obj_map = {}
    for net_name, (code, _) in nets.items():
        net_item = pcbnew.NETINFO_ITEM(board, net_name)
        net_item.SetNetCode(code)
        board.Add(net_item)
        net_obj_map[net_name] = board.FindNet(net_name)

    # 4. Component Placements
    # Using rot=270 for C1, C2, R1, R2 so Pad 1 (+3.3V) is at the TOP, Pad 2 is at BOTTOM
    placements = {
        "J1": (origin_x + 18.0, origin_y + 24.0, 0),
        "J2": (origin_x + 43.4, origin_y + 24.0, 0),
        "J3": (origin_x + 82.0, origin_y + 18.0, 0),
        "J4": (origin_x + 82.0, origin_y + 52.0, 0),
        "C1": (origin_x + 66.0, origin_y + 14.0, 270),
        "C2": (origin_x + 70.0, origin_y + 46.0, 270),
        "R1": (origin_x + 64.0, origin_y + 50.0, 270),  # North of SCL
        "R2": (origin_x + 64.0, origin_y + 66.0, 90)    # South of SDA: Pad 2 at top (Y=65.088), Pad 1 at bottom (Y=66.912)
    }

    footprint_instances = {}
    for ref, (val, fp_str) in comps.items():
        lib_name, mod_name = fp_str.split(":", 1)
        lib_path = f"/usr/share/kicad/footprints/{lib_name}.pretty"
        fp = pcbnew.FootprintLoad(lib_path, mod_name)
        if not fp:
            print(f"Error: Could not load footprint {fp_str} for {ref}")
            continue
        fp.SetReference(ref)
        fp.SetValue(val)
        pos_x, pos_y, rot_deg = placements[ref]
        fp.SetPosition(pcbnew.VECTOR2I(mm2nm(pos_x), mm2nm(pos_y)))
        fp.SetOrientation(pcbnew.EDA_ANGLE(rot_deg, pcbnew.DEGREES_T))
        # Move text out of way
        fp.Reference().SetPosition(pcbnew.VECTOR2I(mm2nm(pos_x + 4.0), mm2nm(pos_y)))
        fp.Value().SetVisible(False)
        board.Add(fp)
        footprint_instances[ref] = fp

    # 5. Connect Component Pads to Net Objects
    for net_name, (_, node_list) in nets.items():
        net_item = net_obj_map.get(net_name)
        if not net_item:
            continue
        for ref, pin_num in node_list:
            if ref in footprint_instances:
                pad = footprint_instances[ref].FindPadByNumber(pin_num)
                if pad:
                    pad.SetNet(net_item)

    # 6. Silkscreen Labels
    title_text = pcbnew.PCB_TEXT(board)
    title_text.SetText("MotoPulse Edge AI System")
    title_text.SetPosition(pcbnew.VECTOR2I(mm2nm(origin_x + 50.0), mm2nm(origin_y + 6.0)))
    title_text.SetTextSize(pcbnew.VECTOR2I(mm2nm(1.8), mm2nm(1.8)))
    title_text.SetTextThickness(mm2nm(0.28))
    title_text.SetLayer(pcbnew.F_SilkS)
    board.Add(title_text)

    sub_text = pcbnew.PCB_TEXT(board)
    sub_text.SetText("Automotive Acoustic Predictive Maintenance")
    sub_text.SetPosition(pcbnew.VECTOR2I(mm2nm(origin_x + 50.0), mm2nm(origin_y + 9.5)))
    sub_text.SetTextSize(pcbnew.VECTOR2I(mm2nm(1.0), mm2nm(1.0)))
    sub_text.SetTextThickness(mm2nm(0.18))
    sub_text.SetLayer(pcbnew.F_SilkS)
    board.Add(sub_text)

    lbl_mic = pcbnew.PCB_TEXT(board)
    lbl_mic.SetText("INMP441 MEMS (I2S)")
    lbl_mic.SetPosition(pcbnew.VECTOR2I(mm2nm(origin_x + 82.0), mm2nm(origin_y + 14.0)))
    lbl_mic.SetTextSize(pcbnew.VECTOR2I(mm2nm(1.0), mm2nm(1.0)))
    lbl_mic.SetLayer(pcbnew.F_SilkS)
    board.Add(lbl_mic)

    lbl_oled = pcbnew.PCB_TEXT(board)
    lbl_oled.SetText("SSD1306 OLED (I2C)")
    lbl_oled.SetPosition(pcbnew.VECTOR2I(mm2nm(origin_x + 82.0), mm2nm(origin_y + 48.0)))
    lbl_oled.SetTextSize(pcbnew.VECTOR2I(mm2nm(1.0), mm2nm(1.0)))
    lbl_oled.SetLayer(pcbnew.F_SilkS)
    board.Add(lbl_oled)

    def pad_pos(ref, pin_str):
        p = footprint_instances[ref].FindPadByNumber(pin_str).GetPosition()
        return (nm2mm(p.x), nm2mm(p.y))

    # Net objects
    net_3v3 = net_obj_map.get("+3.3V")
    net_gnd = net_obj_map.get("GND")
    net_sck = net_obj_map.get("/I2S_SCK")
    net_ws  = net_obj_map.get("/I2S_WS")
    net_sd  = net_obj_map.get("/I2S_SD")
    net_scl = net_obj_map.get("/I2C_SCL")
    net_sda = net_obj_map.get("/I2C_SDA")

    # Pad positions
    p_j1_1  = pad_pos("J1", "1")
    p_j1_6  = pad_pos("J1", "6")
    p_j1_7  = pad_pos("J1", "7")
    p_j1_8  = pad_pos("J1", "8")
    p_j1_13 = pad_pos("J1", "13")

    p_j2_1  = pad_pos("J2", "1")
    p_j2_14 = pad_pos("J2", "14")
    p_j2_15 = pad_pos("J2", "15")

    p_j3_1  = pad_pos("J3", "1")
    p_j3_2  = pad_pos("J3", "2")
    p_j3_3  = pad_pos("J3", "3")
    p_j3_4  = pad_pos("J3", "4")
    p_j3_5  = pad_pos("J3", "5")
    p_j3_6  = pad_pos("J3", "6")

    p_j4_1  = pad_pos("J4", "1")
    p_j4_2  = pad_pos("J4", "2")
    p_j4_3  = pad_pos("J4", "3")
    p_j4_4  = pad_pos("J4", "4")

    p_c1_1  = pad_pos("C1", "1")
    p_c1_2  = pad_pos("C1", "2")
    p_c2_1  = pad_pos("C2", "1")
    p_c2_2  = pad_pos("C2", "2")

    p_r1_1  = pad_pos("R1", "1")
    p_r1_2  = pad_pos("R1", "2")
    p_r2_1  = pad_pos("R2", "1")
    p_r2_2  = pad_pos("R2", "2")

    # =========================================================================
    # ROUTING
    # =========================================================================

    # 1. +3.3V POWER TRUNK (on F.Cu Top Layer)
    rail_3v3_y = origin_y + 7.0
    east_3v3_x = origin_x + 93.0

    # J1.1 -> north to rail -> east to perimeter rail -> down to south of J4
    add_polyline(board, [p_j1_1, (p_j1_1[0], rail_3v3_y), (east_3v3_x, rail_3v3_y), (east_3v3_x, p_r2_1[1])], net_3v3, pcbnew.F_Cu, 0.5)

    # C1.1 (+3.3V): drop down from rail
    add_polyline(board, [(p_c1_1[0], rail_3v3_y), p_c1_1], net_3v3, pcbnew.F_Cu, 0.4)

    # J3.1 (+3.3V): drop down from rail
    add_polyline(board, [(p_j3_1[0], rail_3v3_y), p_j3_1], net_3v3, pcbnew.F_Cu, 0.5)

    # J4.1 (+3.3V): branch west from east rail
    add_polyline(board, [(east_3v3_x, p_j4_1[1]), p_j4_1], net_3v3, pcbnew.F_Cu, 0.5)

    # C2.1 (+3.3V): enter from north at Y=143.0 to avoid Pad 2 (GND at Y=146.95)
    add_polyline(board, [p_j4_1, (origin_x + 75.0, p_j4_1[1]), (origin_x + 75.0, origin_y + 43.0), (p_c2_1[0], origin_y + 43.0), p_c2_1], net_3v3, pcbnew.F_Cu, 0.4)

    # R1.1 (+3.3V): from C2.1 north rail west and down to R1.1
    add_polyline(board, [(p_c2_1[0], origin_y + 43.0), (p_r1_1[0], origin_y + 43.0), p_r1_1], net_3v3, pcbnew.F_Cu, 0.4)

    # R2.1 (+3.3V): from east rail west to R2.1
    add_polyline(board, [(east_3v3_x, p_r2_1[1]), p_r2_1], net_3v3, pcbnew.F_Cu, 0.4)


    # 2. I2S DIGITAL AUDIO (100% Non-Crossing Collision-Free Routing)
    # SCK on B.Cu:
    add_polyline(board, [
        p_j1_6,
        (origin_x + 27.0, p_j1_6[1]),
        (origin_x + 27.0, origin_y + 13.5),
        (origin_x + 77.0, origin_y + 13.5),
        (origin_x + 77.0, p_j3_4[1]),
        p_j3_4
    ], net_sck, pcbnew.B_Cu, 0.35)

    # WS on B.Cu:
    add_polyline(board, [
        p_j1_7,
        (origin_x + 30.0, p_j1_7[1]),
        (origin_x + 30.0, origin_y + 16.0),
        (origin_x + 74.0, origin_y + 16.0),
        (origin_x + 74.0, p_j3_5[1]),
        p_j3_5
    ], net_ws, pcbnew.B_Cu, 0.35)

    # SD on F.Cu (Top layer: completely isolated from SCK/WS, well clear of J2 and C1):
    add_polyline(board, [
        p_j1_8,
        (origin_x + 24.0, p_j1_8[1]),
        (origin_x + 24.0, origin_y + 20.0),
        (origin_x + 79.0, origin_y + 20.0),
        (origin_x + 79.0, p_j3_3[1]),
        p_j3_3
    ], net_sd, pcbnew.F_Cu, 0.35)


    # 3. I2C DISPLAY SIGNALS (on B.Cu Bottom Layer: straight horizontal parallel)
    add_polyline(board, [p_j2_14, p_j4_3], net_scl, pcbnew.B_Cu, 0.35)
    add_polyline(board, [p_j2_15, p_j4_4], net_sda, pcbnew.B_Cu, 0.35)

    # R1 (SCL pull-up): R1.2 (Y=150.912) drops south to SCL via
    via_scl_pos = (p_r1_2[0], p_j2_14[1] - 2.0)
    add_via(board, via_scl_pos, net_scl)
    add_segment(board, p_r1_2, via_scl_pos, net_scl, pcbnew.F_Cu, 0.35)
    add_segment(board, via_scl_pos, (via_scl_pos[0], p_j2_14[1]), net_scl, pcbnew.B_Cu, 0.35)

    # R2 (SDA pull-up): R2.2 (Y=65.088) goes north to SDA via
    via_sda_pos = (p_r2_2[0], p_j2_15[1] + 2.0)
    add_via(board, via_sda_pos, net_sda)
    add_segment(board, p_r2_2, via_sda_pos, net_sda, pcbnew.F_Cu, 0.35)
    add_segment(board, via_sda_pos, (via_sda_pos[0], p_j2_15[1]), net_sda, pcbnew.B_Cu, 0.35)


    # 4. GND VIAS & STUBS
    # Place GND vias with safe distance from SMD pads
    add_via(board, (p_c1_2[0] - 2.0, p_c1_2[1]), net_gnd)
    add_segment(board, p_c1_2, (p_c1_2[0] - 2.0, p_c1_2[1]), net_gnd, pcbnew.F_Cu, 0.35)

    add_via(board, (p_c2_2[0], p_c2_2[1] + 1.8), net_gnd)
    add_segment(board, p_c2_2, (p_c2_2[0], p_c2_2[1] + 1.8), net_gnd, pcbnew.F_Cu, 0.35)

    # Header GND vias
    pth_gnd = [
        ("J1", "13", p_j1_13, (+2.5, 0.0)),
        ("J2", "1",  p_j2_1,  (+2.5, 0.0)),
        ("J3", "2",  p_j3_2,  (+2.5, 0.0)),
        ("J3", "6",  p_j3_6,  (+2.5, 0.0)),
        ("J4", "2",  p_j4_2,  (+2.5, 0.0))
    ]
    for ref, pin, p, (dx, dy) in pth_gnd:
        via_pos = (p[0] + dx, p[1] + dy)
        add_via(board, via_pos, net_gnd)
        add_segment(board, p, via_pos, net_gnd, pcbnew.F_Cu, 0.35)


    # 5. GROUND COPPER ZONES (F.Cu and B.Cu)
    for layer in [pcbnew.F_Cu, pcbnew.B_Cu]:
        zone = pcbnew.ZONE(board)
        zone.SetLayer(layer)
        zone.SetNet(net_gnd)
        zone.SetNetCode(net_gnd.GetNetCode())
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        zone.SetThermalReliefGap(mm2nm(0.3))
        zone.SetThermalReliefSpokeWidth(mm2nm(0.4))

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

    # Save PCB
    board.Save(PCB_FILE)
    print(f"MotoPulse PCB saved successfully: {PCB_FILE}")

if __name__ == '__main__':
    build_pcb()
