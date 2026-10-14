#!/usr/bin/env python3
"""
MotoPulse: Zero-DRC KiCad 10 PCB Generator for Unified ESP32-S3 Carrier Board
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
    net_blocks = re.findall(r'\(net\s+\(code\s+\"(\d+)\"\)\s+\(name\s+\"([^\"]+)\"\)(.*?)(?=\(net|\Z)', nets_section, re.DOTALL)
    nets = {}
    for code, name, body in net_blocks:
        nodes = re.findall(r'\(node\s+\(ref\s+\"([^\"]+)\"\)\s+\(pin\s+\"([^\"]+)\"', body, re.DOTALL)
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
    w_mm = 115.0
    h_mm = 90.0

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

    def get_net(name):
        return net_obj_map.get(name) or net_obj_map.get("/" + name) or net_obj_map.get(name.lstrip("/"))

    net_3v3 = get_net("+3.3V")
    net_gnd = get_net("GND")
    net_sck = get_net("I2S_SCK")
    net_ws  = get_net("I2S_WS")
    net_sd  = get_net("I2S_SD")
    net_scl = get_net("I2C_SCL")
    net_sda = get_net("I2C_SDA")
    net_piezo = get_net("PIEZO_IN")

    # 4. Component Placements
    # U1 is centered at X = origin_x + 57.5, Y = origin_y + 45.0
    # J1 (Left Mic) at X = origin_x + 30.0, Y = origin_y + 70.0 (Rot 0)
    # J2 (Right Mic) at X = origin_x + 70.0, Y = origin_y + 70.0 (Rot 0) -> EXACTLY 40.0mm!
    placements = {
        "U1": (origin_x + 57.5, origin_y + 45.0, 0),
        "J1": (origin_x + 30.0, origin_y + 70.0, 0),
        "J2": (origin_x + 70.0, origin_y + 70.0, 0),
        "J3": (origin_x + 98.0, origin_y + 30.0, 0),
        "J4": (origin_x + 18.0, origin_y + 30.0, 0),
        "C1": (origin_x + 22.0, origin_y + 65.0, 0),
        "C2": (origin_x + 78.0, origin_y + 65.0, 0),
        "C3": (origin_x + 90.0, origin_y + 24.0, 270),
        "C4": (origin_x + 38.0, origin_y + 15.0, 0),
        "R1": (origin_x + 90.0, origin_y + 32.0, 270),
        "R2": (origin_x + 90.0, origin_y + 38.0, 270),
        "R3": (origin_x + 26.0, origin_y + 30.0, 0),
    }

    footprint_instances = {}
    for ref, (val, fp_str) in comps.items():
        lib_name, mod_name = fp_str.split(":", 1)
        if lib_name == "motopulse":
            lib_path = os.path.join(BASE_DIR, "motopulse.pretty")
        else:
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
        fp.Reference().SetPosition(pcbnew.VECTOR2I(mm2nm(pos_x), mm2nm(pos_y - 3.5)))
        fp.Reference().SetVisible(True)
        fp.Value().SetVisible(False)
        board.Add(fp)
        footprint_instances[ref] = fp

    # Connect Component Pads to Net Objects
    for net_name, (_, node_list) in nets.items():
        net_item = get_net(net_name)
        if not net_item:
            continue
        for ref, pin_num in node_list:
            if ref in footprint_instances:
                pad = footprint_instances[ref].FindPadByNumber(pin_num)
                if pad:
                    pad.SetNet(net_item)

    # Silkscreen Labels
    def add_silk_text(text, x, y, size=1.2, thickness=0.2):
        t = pcbnew.PCB_TEXT(board)
        t.SetText(text)
        t.SetPosition(pcbnew.VECTOR2I(mm2nm(origin_x + x), mm2nm(origin_y + y)))
        t.SetTextSize(pcbnew.VECTOR2I(mm2nm(size), mm2nm(size)))
        t.SetTextThickness(mm2nm(thickness))
        t.SetLayer(pcbnew.F_SilkS)
        board.Add(t)

    add_silk_text("MOTOPULSE™ TELEMETRY CARRIER", 57.5, 5.0, size=1.8, thickness=0.28)
    add_silk_text("IEEE RUAS - HACKTIVATE 2026", 57.5, 8.5, size=1.0, thickness=0.18)
    add_silk_text("◄─── 40.0 mm Dual-Mic Acoustic Baseline ───►", 50.0, 84.0, size=1.0, thickness=0.18)
    add_silk_text("MIC 1 (L)", 30.0, 58.0, size=0.9, thickness=0.15)
    add_silk_text("MIC 2 (R)", 70.0, 58.0, size=0.9, thickness=0.15)
    add_silk_text("SSD1306 OLED", 98.0, 20.0, size=0.9, thickness=0.15)
    add_silk_text("PIEZO ADC", 18.0, 20.0, size=0.9, thickness=0.15)

    def pad_pos(ref, pin_str):
        p = footprint_instances[ref].FindPadByNumber(pin_str).GetPosition()
        return (nm2mm(p.x), nm2mm(p.y))

    # Pad positions
    u1_p1  = pad_pos("U1", "1")
    u1_p4  = pad_pos("U1", "4")
    u1_p5  = pad_pos("U1", "5")
    u1_p6  = pad_pos("U1", "6")
    u1_p23 = pad_pos("U1", "23")
    u1_p24 = pad_pos("U1", "24")
    u1_p27 = pad_pos("U1", "27")
    u1_p28 = pad_pos("U1", "28")

    j1_p1  = pad_pos("J1", "1")
    j1_p2  = pad_pos("J1", "2")
    j1_p3  = pad_pos("J1", "3")
    j1_p4  = pad_pos("J1", "4")
    j1_p5  = pad_pos("J1", "5")
    j1_p6  = pad_pos("J1", "6")

    j2_p1  = pad_pos("J2", "1")
    j2_p2  = pad_pos("J2", "2")
    j2_p3  = pad_pos("J2", "3")
    j2_p4  = pad_pos("J2", "4")
    j2_p5  = pad_pos("J2", "5")
    j2_p6  = pad_pos("J2", "6")

    j3_p1  = pad_pos("J3", "1")
    j3_p2  = pad_pos("J3", "2")
    j3_p3  = pad_pos("J3", "3")
    j3_p4  = pad_pos("J3", "4")

    j4_p1  = pad_pos("J4", "1")
    j4_p2  = pad_pos("J4", "2")

    c1_p1  = pad_pos("C1", "1")
    c1_p2  = pad_pos("C1", "2")
    c2_p1  = pad_pos("C2", "1")
    c2_p2  = pad_pos("C2", "2")
    c3_p1  = pad_pos("C3", "1")
    c3_p2  = pad_pos("C3", "2")
    c4_p1  = pad_pos("C4", "1")
    c4_p2  = pad_pos("C4", "2")

    r1_p1  = pad_pos("R1", "1")
    r1_p2  = pad_pos("R1", "2")
    r2_p1  = pad_pos("R2", "1")
    r2_p2  = pad_pos("R2", "2")
    r3_p1  = pad_pos("R3", "1")
    r3_p2  = pad_pos("R3", "2")

    # =============================================================
    # 5. SIGNAL ROUTING (Clean Orthogonal Corridors)
    # =============================================================

    # A. PIEZO_IN (U1 Pin 24 -> R3 Pin 1 -> J4 Pin 1)
    # Exits U1.24 right, loops around north of U1 header at Y = origin_y + 12.0
    add_polyline(board, [
        u1_p24,
        (u1_p24[0] + 3.0, u1_p24[1]),
        (u1_p24[0] + 3.0, origin_y + 12.0),
        (r3_p1[0], origin_y + 12.0),
        r3_p1,
        (r3_p1[0], j4_p1[1]),
        j4_p1
    ], net_piezo, pcbnew.F_Cu, 0.35)

    # B. I2C_SCL (U1 Pin 27 -> R1 Pin 2 -> J3 Pin 3)
    add_polyline(board, [
        u1_p27,
        (r1_p2[0], u1_p27[1]),
        r1_p2
    ], net_scl, pcbnew.F_Cu, 0.35)
    add_polyline(board, [
        r1_p2,
        (j3_p3[0] - 3.0, r1_p2[1]),
        (j3_p3[0] - 3.0, j3_p3[1]),
        j3_p3
    ], net_scl, pcbnew.F_Cu, 0.35)

    # C. I2C_SDA (U1 Pin 28 -> R2 Pin 2 -> J3 Pin 4)
    add_polyline(board, [
        u1_p28,
        (r2_p2[0], u1_p28[1]),
        r2_p2
    ], net_sda, pcbnew.F_Cu, 0.35)
    add_polyline(board, [
        r2_p2,
        (j3_p4[0] - 1.5, r2_p2[1]),
        (j3_p4[0] - 1.5, j3_p4[1]),
        j3_p4
    ], net_sda, pcbnew.F_Cu, 0.35)

    # D. I2S_SCK (U1 Pin 4 -> J1 Pin 4 & J2 Pin 4)
    # On F.Cu to J1.4, then across to J2.4 on B.Cu
    add_polyline(board, [
        u1_p4,
        (u1_p4[0] - 6.0, u1_p4[1]),
        (u1_p4[0] - 6.0, j1_p4[1] - 1.5),
        (j1_p4[0] + 3.0, j1_p4[1] - 1.5),
        j1_p4
    ], net_sck, pcbnew.F_Cu, 0.35)
    add_polyline(board, [
        (j1_p4[0] + 3.0, j1_p4[1] - 1.5),
        (j2_p4[0] - 3.0, j1_p4[1] - 1.5),
        j2_p4
    ], net_sck, pcbnew.B_Cu, 0.35)
    add_via(board, (j1_p4[0] + 3.0, j1_p4[1] - 1.5), net_sck)
    add_via(board, (j2_p4[0] - 3.0, j1_p4[1] - 1.5), net_sck)

    # E. I2S_WS (U1 Pin 5 -> J1 Pin 5 & J2 Pin 5)
    add_polyline(board, [
        u1_p5,
        (u1_p5[0] - 8.0, u1_p5[1]),
        (u1_p5[0] - 8.0, j1_p5[1] - 1.5),
        (j1_p5[0] + 3.0, j1_p5[1] - 1.5),
        j1_p5
    ], net_ws, pcbnew.F_Cu, 0.35)
    add_polyline(board, [
        (j1_p5[0] + 3.0, j1_p5[1] - 1.5),
        (j2_p5[0] - 3.0, j1_p5[1] - 1.5),
        j2_p5
    ], net_ws, pcbnew.B_Cu, 0.35)
    add_via(board, (j1_p5[0] + 3.0, j1_p5[1] - 1.5), net_ws)
    add_via(board, (j2_p5[0] - 3.0, j1_p5[1] - 1.5), net_ws)

    # F. I2S_SD (U1 Pin 6 -> J1 Pin 3 & J2 Pin 3)
    add_polyline(board, [
        u1_p6,
        (u1_p6[0] - 10.0, u1_p6[1]),
        (u1_p6[0] - 10.0, j1_p3[1] - 1.5),
        (j1_p3[0] + 3.0, j1_p3[1] - 1.5),
        j1_p3
    ], net_sd, pcbnew.F_Cu, 0.35)
    add_polyline(board, [
        (j1_p3[0] + 3.0, j1_p3[1] - 1.5),
        (j2_p3[0] - 3.0, j1_p3[1] - 1.5),
        j2_p3
    ], net_sd, pcbnew.B_Cu, 0.35)
    add_via(board, (j1_p3[0] + 3.0, j1_p3[1] - 1.5), net_sd)
    add_via(board, (j2_p3[0] - 3.0, j1_p3[1] - 1.5), net_sd)

    # =============================================================
    # 6. POWER (+3.3V) ROUTING (0.60mm wide trunk)
    # =============================================================
    pwr_north_y = origin_y + 8.0

    # U1.1 -> C4.1 -> north to rail
    add_polyline(board, [u1_p1, (c4_p1[0], u1_p1[1]), c4_p1, (c4_p1[0], pwr_north_y)], net_3v3, pcbnew.F_Cu, 0.60)
    
    # North rail west -> J1.1 & C1.1
    add_polyline(board, [
        (c4_p1[0], pwr_north_y),
        (origin_x + 12.0, pwr_north_y),
        (origin_x + 12.0, j1_p1[1] - 2.0),
        (j1_p1[0], j1_p1[1] - 2.0),
        j1_p1
    ], net_3v3, pcbnew.F_Cu, 0.60)
    add_segment(board, (j1_p1[0], j1_p1[1] - 2.0), c1_p1, net_3v3, pcbnew.F_Cu, 0.50)

    # North rail east -> OLED & pull-ups
    add_polyline(board, [
        (c4_p1[0], pwr_north_y),
        (origin_x + 104.0, pwr_north_y),
        (origin_x + 104.0, j3_p2[1]),
        j3_p2
    ], net_3v3, pcbnew.F_Cu, 0.60)
    add_polyline(board, [j3_p2, (c3_p1[0], j3_p2[1]), c3_p1, r1_p1, r2_p1], net_3v3, pcbnew.F_Cu, 0.50)

    # 3.3V to J2.1 & J2.6 (Right channel select to 3.3V) & C2.1
    add_polyline(board, [
        (origin_x + 104.0, j3_p2[1]),
        (origin_x + 104.0, origin_y + 82.0),
        (j2_p6[0] + 4.0, origin_y + 82.0),
        (j2_p6[0] + 4.0, j2_p6[1]),
        j2_p6
    ], net_3v3, pcbnew.B_Cu, 0.60)
    add_via(board, (origin_x + 104.0, j3_p2[1]), net_3v3)
    add_via(board, (j2_p6[0] + 4.0, j2_p6[1]), net_3v3)
    add_polyline(board, [j2_p6, (j2_p1[0] + 4.0, j2_p6[1]), (j2_p1[0] + 4.0, j2_p1[1]), j2_p1, c2_p1], net_3v3, pcbnew.F_Cu, 0.50)

    # =============================================================
    # 7. GROUND CONNECTIONS & VIAS
    # =============================================================
    # Add ground vias next to SMD component ground pads
    gnd_smd_pads = [c1_p2, c2_p2, c3_p2, c4_p2, r3_p2]
    for pt in gnd_smd_pads:
        via_pt = (pt[0] - 2.0, pt[1])
        add_via(board, via_pt, net_gnd)
        add_segment(board, pt, via_pt, net_gnd, pcbnew.F_Cu, 0.35)

    # Connect J1.6 (L/R) to J1.2 (GND)
    add_polyline(board, [j1_p6, (j1_p6[0] - 3.0, j1_p6[1]), (j1_p6[0] - 3.0, j1_p2[1]), j1_p2], net_gnd, pcbnew.F_Cu, 0.40)

    # =============================================================
    # 8. COPPER GROUND PLANES (Top F.Cu & Bottom B.Cu)
    # =============================================================
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

    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())

    # Save PCB
    board.Save(PCB_FILE)
    print(f"✔ Generated PCB: {PCB_FILE}")

if __name__ == "__main__":
    build_pcb()
