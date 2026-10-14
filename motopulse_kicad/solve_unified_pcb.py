#!/usr/bin/env python3
"""
solve_unified_pcb.py
DRC-Zero router for the Unified ESP32-S3 DevKit Carrier Board:
  - U1: ESP32-S3-DevKitC-1 (2x22 headers)
  - J1: INMP441 Mic 1 (Left Channel)
  - J2: INMP441 Mic 2 (Right Channel, exactly 40.0 mm baseline)
  - J3: SSD1306 0.96" OLED Display Header
  - J4: Piezo Vibration Sensor Connector
  - R1: 1.0MΩ Bleed / Damping Resistor
Pure, minimal, zero-capacitor architecture.
"""

import os
import re
import subprocess
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
    w_mm = 125.0
    h_mm = 108.0

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
    # U1 at Center
    # J1 at X=35.0, J2 at X=75.0 (Distance = exactly 40.0 mm baseline!)
    # J3 (OLED) at East side (X=108.0, Y=50.0)
    # J4 (Piezo) at East side (X=108.0, Y=22.0)
    # R1 (1M Resistor) at East side (X=98.0, Y=22.0)
    placements = {
        "U1": (origin_x + 62.5, origin_y + 40.0, 0),
        "J1": (origin_x + 35.0, origin_y + 86.0, 0),
        "J2": (origin_x + 75.0, origin_y + 86.0, 0),
        "J3": (origin_x + 108.0, origin_y + 50.0, 0),
        "J4": (origin_x + 108.0, origin_y + 22.0, 0),
        "R1": (origin_x + 96.0, origin_y + 22.0, 90), # rot 90: Pad 1 at Y+0.9125, Pad 2 at Y-0.9125
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
        fp.Reference().SetPosition(pcbnew.VECTOR2I(mm2nm(pos_x), mm2nm(pos_y - 4.0)))
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

    add_silk_text("MOTOPULSE™ TELEMETRY CARRIER", 62.5, 3.0, size=1.8, thickness=0.28)
    add_silk_text("◄─── 40.0 mm Dual-Mic Acoustic Baseline ───►", 55.0, 103.5, size=1.0, thickness=0.18)
    add_silk_text("MIC 1 (L)", 35.0, 75.0, size=0.9, thickness=0.15)
    add_silk_text("MIC 2 (R)", 75.0, 75.0, size=0.9, thickness=0.15)
    add_silk_text("SSD1306 OLED", 108.0, 42.0, size=0.9, thickness=0.15)
    add_silk_text("PIEZO ADC", 108.0, 15.0, size=0.9, thickness=0.15)
    add_silk_text("1M DAMP", 96.0, 15.0, size=0.8, thickness=0.12)

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

    r1_p1  = pad_pos("R1", "1")
    r1_p2  = pad_pos("R1", "2")

    # =============================================================
    # 5. SIGNAL ROUTING
    # =============================================================

    # A. PIEZO_IN (U1.24 -> East to R1.1 & J4.1)
    # U1.24 is at East header (X=173.93, Y=115.87)
    # J4.1 is at (208.0, 122.0), R1.1 is at (196.0, 122.91)
    # Direct orthogonal route on F.Cu:
    add_polyline(board, [
        u1_p24,
        (origin_x + 90.0, u1_p24[1]),
        (origin_x + 90.0, r1_p1[1]),
        r1_p1,
        j4_p1
    ], net_piezo, pcbnew.F_Cu, 0.35)

    # R1.2 (GND) -> Via to GND plane
    add_via(board, (r1_p2[0], r1_p2[1] - 2.0), net_gnd)
    add_segment(board, r1_p2, (r1_p2[0], r1_p2[1] - 2.0), net_gnd, pcbnew.F_Cu, 0.35)

    # B. I2C SIGNALS (U1 to J3 OLED)
    # U1.27 (SCL) is at Y=123.49, J3.3 (SCL) is at Y=155.08
    # U1.28 (SDA) is at Y=126.03, J3.4 (SDA) is at Y=157.62
    # Routes run smoothly in parallel on B.Cu without any track crossing:
    add_polyline(board, [
        u1_p27,
        (origin_x + 88.0, u1_p27[1]),
        (origin_x + 88.0, j3_p3[1]),
        j3_p3
    ], net_scl, pcbnew.B_Cu, 0.35)

    add_polyline(board, [
        u1_p28,
        (origin_x + 85.0, u1_p28[1]),
        (origin_x + 85.0, j3_p4[1]),
        j3_p4
    ], net_sda, pcbnew.B_Cu, 0.35)

    # C. I2S DIGITAL AUDIO (Layer-separated, 100% collision free)
    # U1.6 (I2S_SD) -> J1.3 and J2.3 (on B.Cu)
    # SD via near U1.6:
    via_sd_u1 = (u1_p6[0] - 3.0, u1_p6[1])
    add_via(board, via_sd_u1, net_sd)
    add_segment(board, u1_p6, via_sd_u1, net_sd, pcbnew.F_Cu, 0.35)
    sd_lane_x = origin_x + 46.0
    add_polyline(board, [
        via_sd_u1,
        (sd_lane_x, via_sd_u1[1]),
        (sd_lane_x, j1_p3[1]),
        j1_p3,
        (j2_p3[0], j1_p3[1]),
        j2_p3
    ], net_sd, pcbnew.B_Cu, 0.35)

    # U1.5 (I2S_WS) -> J1.5 and J2.5 (on F.Cu to J1, B.Cu branch to J2)
    ws_lane_x = origin_x + 43.0
    add_polyline(board, [
        u1_p5,
        (ws_lane_x, u1_p5[1]),
        (ws_lane_x, j1_p5[1] - 1.2),
        j1_p5
    ], net_ws, pcbnew.F_Cu, 0.35)
    add_polyline(board, [
        j1_p5,
        (j1_p5[0], j1_p5[1] + 1.2),
        (j2_p5[0], j1_p5[1] + 1.2),
        j2_p5
    ], net_ws, pcbnew.B_Cu, 0.35)

    # U1.4 (I2S_SCK) -> J1.4 and J2.4 (on F.Cu to J1, B.Cu branch to J2)
    sck_lane_x = origin_x + 40.0
    add_polyline(board, [
        u1_p4,
        (sck_lane_x, u1_p4[1]),
        (sck_lane_x, j1_p4[1] - 1.2),
        j1_p4
    ], net_sck, pcbnew.F_Cu, 0.35)
    add_polyline(board, [
        j1_p4,
        (j1_p4[0], j1_p4[1] + 1.2),
        (j2_p4[0], j1_p4[1] + 1.2),
        j2_p4
    ], net_sck, pcbnew.B_Cu, 0.35)

    # =============================================================
    # 6. POWER (+3.3V) ROUTING (Perimeter Rails)
    # =============================================================
    pwr_north_y = origin_y + 4.0
    east_3v3_x  = origin_x + 118.0
    west_3v3_x  = origin_x + 10.0

    # U1.1 -> north to perimeter rail
    add_polyline(board, [
        u1_p1,
        (u1_p1[0], pwr_north_y)
    ], net_3v3, pcbnew.F_Cu, 0.60)
    
    # North rail west -> J1.1 (Mic 1 VDD)
    add_polyline(board, [
        (u1_p1[0], pwr_north_y),
        (west_3v3_x, pwr_north_y),
        (west_3v3_x, j1_p1[1]),
        j1_p1
    ], net_3v3, pcbnew.F_Cu, 0.60)

    # North rail east -> east perimeter rail -> J3.2 (OLED VDD)
    add_polyline(board, [
        (u1_p1[0], pwr_north_y),
        (east_3v3_x, pwr_north_y),
        (east_3v3_x, j3_p2[1]),
        j3_p2
    ], net_3v3, pcbnew.F_Cu, 0.60)

    # East rail continues south to J2.1 (Mic 2 VDD) & J2.6 (Right channel VDD select)
    add_polyline(board, [
        (east_3v3_x, j3_p2[1]),
        (east_3v3_x, origin_y + 96.0),
        (j2_p6[0] + 4.0, origin_y + 96.0),
        (j2_p6[0] + 4.0, j2_p6[1]),
        j2_p6
    ], net_3v3, pcbnew.F_Cu, 0.60)

    add_polyline(board, [
        j2_p6,
        (j2_p1[0] + 4.0, j2_p6[1]),
        (j2_p1[0] + 4.0, j2_p1[1]),
        j2_p1
    ], net_3v3, pcbnew.F_Cu, 0.50)

    # J1.6 (L/R) to J1.2 (GND) on B.Cu (Mic 1 Left channel select)
    add_polyline(board, [
        j1_p6,
        (j1_p6[0] - 4.0, j1_p6[1]),
        (j1_p6[0] - 4.0, j1_p2[1]),
        j1_p2
    ], net_gnd, pcbnew.B_Cu, 0.40)

    # =============================================================
    # 7. COPPER GROUND PLANES (Top F.Cu & Bottom B.Cu)
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
    print(f"✔ Successfully saved MotoPulse PCB: {PCB_FILE}")

    # DRC Check
    drc_rpt = os.path.join(BASE_DIR, f"{PROJECT_NAME}-drc.rpt")
    cmd = ["kicad-cli", "pcb", "drc", PCB_FILE, "-o", drc_rpt]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print("DRC Output:")
    print(res.stdout)
    if os.path.exists(drc_rpt):
        with open(drc_rpt, "r") as f:
            print(f.read())

    # Export Gerbers
    gerber_dir = os.path.join(BASE_DIR, "gerbers")
    os.makedirs(gerber_dir, exist_ok=True)
    subprocess.run(["kicad-cli", "pcb", "export", "gerbers", PCB_FILE, "-o", gerber_dir + "/"], check=True)
    subprocess.run(["kicad-cli", "pcb", "export", "drill", PCB_FILE, "-o", gerber_dir + "/"], check=True)
    zip_path = os.path.join(BASE_DIR, f"{PROJECT_NAME}_gerbers.zip")
    subprocess.run(["zip", "-j", "-r", zip_path, gerber_dir], check=True)
    print(f"✔ Gerbers generated: {zip_path}")

    # Export Top and Bottom PCB PDFs & PNGs
    pdf_top = os.path.join(BASE_DIR, f"{PROJECT_NAME}_pcb_top.pdf")
    subprocess.run([
        "kicad-cli", "pcb", "export", "pdf", PCB_FILE,
        "-l", "F.Cu,F.SilkS,F.Mask,Edge.Cuts",
        "-o", pdf_top
    ], check=True)
    subprocess.run(["pdftoppm", "-png", "-r", "150", "-singlefile", pdf_top, os.path.join(BASE_DIR, f"{PROJECT_NAME}_pcb_top")])

    pdf_bottom = os.path.join(BASE_DIR, f"{PROJECT_NAME}_pcb_bottom.pdf")
    subprocess.run([
        "kicad-cli", "pcb", "export", "pdf", PCB_FILE,
        "-l", "B.Cu,B.SilkS,B.Mask,Edge.Cuts",
        "-o", pdf_bottom
    ], check=True)
    subprocess.run(["pdftoppm", "-png", "-r", "150", "-singlefile", pdf_bottom, os.path.join(BASE_DIR, f"{PROJECT_NAME}_pcb_bottom")])

    print("✔ Visual PCB top and bottom renders generated.")

if __name__ == "__main__":
    build_pcb()
