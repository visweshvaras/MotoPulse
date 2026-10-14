#!/usr/bin/env python3
"""
Generate a precise, photorealistic-style Breadboard Wiring Diagram for the
ESP32-S3 LM358 Electret Microphone Preamplifier.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

def create_breadboard_diagram():
    fig, ax = plt.subplots(figsize=(18, 11), dpi=200)
    ax.set_facecolor("#ECEFF1")
    
    # Title & Header
    ax.text(15.5, 33.5, "ESP32-S3 Electret Microphone Preamplifier (LM358) — Solderless Breadboard Wiring Guide", 
            fontsize=16, fontweight="bold", ha="center", va="center", color="#263238")
    ax.text(15.5, 32.2, "Complete step-by-step layout with exact tie-points, component values, and ESP32-S3 connections", 
            fontsize=11, fontstyle="italic", ha="center", va="center", color="#546E7A")

    # Breadboard body dimensions
    bb_x0, bb_y0 = 1.0, 5.0
    bb_w, bb_h = 29.0, 26.0
    
    # Breadboard base (off-white plastic)
    bb_rect = patches.FancyBboxPatch(
        (bb_x0, bb_y0), bb_w, bb_h,
        boxstyle="round,pad=0.3,rounding_size=0.8",
        facecolor="#FDFBF7", edgecolor="#CFD8DC", linewidth=2.5, zorder=1
    )
    ax.add_patch(bb_rect)
    
    # Center divider trench
    trench = patches.Rectangle((bb_x0 + 1.0, 17.5), bb_w - 2.0, 1.0, facecolor="#E0E0E0", edgecolor="#BDBDBD", linewidth=1, zorder=2)
    ax.add_patch(trench)
    
    # Power rails lines (Top: + Red, - Blue; Bottom: + Red, - Blue)
    # Top rails: y = 29.5 (Red +), y = 28.2 (Blue -)
    ax.plot([bb_x0 + 2.0, bb_x0 + bb_w - 2.0], [29.8, 29.8], color="#E53935", lw=2, zorder=2)
    ax.plot([bb_x0 + 2.0, bb_x0 + bb_w - 2.0], [27.9, 27.9], color="#1E88E5", lw=2, zorder=2)
    ax.text(bb_x0 + 1.2, 29.8, "+", color="#E53935", fontsize=14, fontweight="bold", va="center", ha="center")
    ax.text(bb_x0 + 1.2, 27.9, "-", color="#1E88E5", fontsize=18, fontweight="bold", va="center", ha="center")
    ax.text(bb_x0 + bb_w - 1.2, 29.8, "+3.3V", color="#E53935", fontsize=10, fontweight="bold", va="center", ha="center")
    ax.text(bb_x0 + bb_w - 1.2, 27.9, "GND", color="#1E88E5", fontsize=10, fontweight="bold", va="center", ha="center")

    # Bottom rails: y = 7.8 (Red +), y = 6.5 (Blue -)
    ax.plot([bb_x0 + 2.0, bb_x0 + bb_w - 2.0], [8.1, 8.1], color="#E53935", lw=2, zorder=2)
    ax.plot([bb_x0 + 2.0, bb_x0 + bb_w - 2.0], [6.2, 6.2], color="#1E88E5", lw=2, zorder=2)
    ax.text(bb_x0 + 1.2, 8.1, "+", color="#E53935", fontsize=14, fontweight="bold", va="center", ha="center")
    ax.text(bb_x0 + 1.2, 6.2, "-", color="#1E88E5", fontsize=18, fontweight="bold", va="center", ha="center")
    ax.text(bb_x0 + bb_w - 1.2, 8.1, "+3.3V", color="#E53935", fontsize=10, fontweight="bold", va="center", ha="center")
    ax.text(bb_x0 + bb_w - 1.2, 6.2, "GND", color="#1E88E5", fontsize=10, fontweight="bold", va="center", ha="center")

    # Draw breadboard holes
    # Rows 1 to 30: x = 2.5 + (row-1)*0.85
    rows_x = {r: 2.5 + (r - 1) * 0.86 for r in range(1, 31)}
    
    # Top columns: A=23.5, B=22.3, C=21.1, D=19.9, E=18.7
    top_cols_y = {"A": 23.5, "B": 22.3, "C": 21.1, "D": 19.9, "E": 18.7}
    # Bottom columns: F=17.3, G=16.1, H=14.9, I=13.7, J=12.5
    bot_cols_y = {"F": 17.3, "G": 16.1, "H": 14.9, "I": 13.7, "J": 12.5}
    
    # Draw all holes
    for r in range(1, 31):
        rx = rows_x[r]
        # power holes
        for py in [29.8, 27.9, 8.1, 6.2]:
            ax.add_patch(patches.Circle((rx, py), 0.12, facecolor="#424242", edgecolor="#BDBDBD", lw=0.5, zorder=3))
        # top cols
        for cy in top_cols_y.values():
            ax.add_patch(patches.Rectangle((rx - 0.11, cy - 0.11), 0.22, 0.22, facecolor="#37474F", edgecolor="#90A4AE", lw=0.4, zorder=3))
        # bot cols
        for cy in bot_cols_y.values():
            ax.add_patch(patches.Rectangle((rx - 0.11, cy - 0.11), 0.22, 0.22, facecolor="#37474F", edgecolor="#90A4AE", lw=0.4, zorder=3))
        
        # Row number labels
        if r in [1, 5, 10, 15, 20, 25, 30]:
            ax.text(rx, 25.0, str(r), fontsize=8, ha="center", va="center", color="#78909C", fontweight="bold")
            ax.text(rx, 10.9, str(r), fontsize=8, ha="center", va="center", color="#78909C", fontweight="bold")

    # Column letter labels
    for cname, cy in top_cols_y.items():
        ax.text(1.8, cy, cname, fontsize=8, ha="center", va="center", color="#78909C", fontweight="bold")
    for cname, cy in bot_cols_y.items():
        ax.text(1.8, cy, cname, fontsize=8, ha="center", va="center", color="#78909C", fontweight="bold")

    # =========================================================================
    # HELPER FUNCTIONS FOR DRAWING COMPONENTS
    # =========================================================================
    def draw_wire(p1, p2, color="#1976D2", lw=3.0, zorder=5, rad=0.2):
        style = f"arc3,rad={rad}"
        arrow = patches.ConnectionStyle(style)
        ax.annotate("", xy=p2, xytext=p1,
                    arrowprops=dict(arrowstyle="-", color=color, lw=lw, connectionstyle=style,
                                    capstyle="round", joinstyle="round"),
                    zorder=zorder)
        # Solder pin dots
        ax.add_patch(patches.Circle(p1, 0.18, facecolor=color, edgecolor="#212121", lw=0.5, zorder=zorder+1))
        ax.add_patch(patches.Circle(p2, 0.18, facecolor=color, edgecolor="#212121", lw=0.5, zorder=zorder+1))

    def draw_resistor(p1, p2, label, color_bands, zorder=6):
        # Wire leads
        mid_x = (p1[0] + p2[0]) / 2.0
        mid_y = (p1[1] + p2[1]) / 2.0
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#B0BEC5", lw=2.2, zorder=zorder-1)
        
        # Resistor body
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = np.hypot(dx, dy)
        angle = np.degrees(np.arctan2(dy, dx))
        
        body_len = min(1.8, length * 0.7)
        body = patches.BoxStyle("Round,pad=0.1,rounding_size=0.15")
        rect = patches.FancyBboxPatch((mid_x - body_len/2.0, mid_y - 0.28), body_len, 0.56,
                                     boxstyle="round,pad=0.05,rounding_size=0.15",
                                     facecolor="#EED9B3", edgecolor="#8D6E63", lw=1.2, zorder=zorder)
        # Apply rotation
        import matplotlib.transforms as transforms
        t = transforms.Affine2D().rotate_deg_around(mid_x, mid_y, angle) + ax.transData
        rect.set_transform(t)
        ax.add_patch(rect)
        
        # Text label
        ax.text(mid_x, mid_y + (0.65 if dy >= 0 else -0.65), label,
                fontsize=8.5, fontweight="bold", ha="center", va="center",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="#FFF9C4", edgecolor="#FBC02D", lw=0.8),
                zorder=zorder+2)

    # =========================================================================
    # 1. PLACE LM358 IC (Rows 15 to 18, straddling trench)
    # =========================================================================
    ic_x1 = rows_x[15] - 0.35
    ic_x2 = rows_x[18] + 0.35
    ic_w = ic_x2 - ic_x1
    ic_body = patches.FancyBboxPatch(
        (ic_x1, 16.6), ic_w, 2.8,
        boxstyle="round,pad=0.08,rounding_size=0.2",
        facecolor="#212121", edgecolor="#424242", lw=1.5, zorder=8
    )
    ax.add_patch(ic_body)
    
    # Notch on left edge (Pin 1 side)
    notch = patches.Arc((ic_x1, 18.0), 0.5, 0.7, angle=0, theta1=270, theta2=90, color="#E0E0E0", lw=1.5, zorder=9)
    ax.add_patch(notch)
    
    # IC Label text
    ax.text((ic_x1 + ic_x2)/2.0, 18.0, "LM358\n(Dual Op-Amp)", color="#FFFFFF", fontsize=8.5, fontweight="bold",
            ha="center", va="center", zorder=9)
    
    # Pin numbers and pins
    pin_coords = {
        1: (rows_x[15], top_cols_y["E"]),
        2: (rows_x[16], top_cols_y["E"]),
        3: (rows_x[17], top_cols_y["E"]),
        4: (rows_x[18], top_cols_y["E"]),
        5: (rows_x[18], bot_cols_y["F"]),
        6: (rows_x[17], bot_cols_y["F"]),
        7: (rows_x[16], bot_cols_y["F"]),
        8: (rows_x[15], bot_cols_y["F"]),
    }
    
    pin_labels = {
        1: "1: OUT A",
        2: "2: IN- A",
        3: "3: IN+ A",
        4: "4: GND",
        5: "5: IN+ B (GND)",
        6: "6: IN- B (Follower)",
        7: "7: OUT B",
        8: "8: V+ (+3.3V)",
    }
    for pnum, (px, py) in pin_coords.items():
        # Silver lead from IC to hole
        ic_edge_y = 19.4 if py > 18.0 else 16.6
        ax.plot([px, px], [ic_edge_y, py], color="#CFD8DC", lw=3.0, zorder=7)

    # =========================================================================
    # 2. POWER SUPPLY WIRING
    # =========================================================================
    # Op-Amp V+ (Pin 8 at row 15 F) -> Red Rail (+)
    draw_wire((rows_x[15], bot_cols_y["G"]), (rows_x[15], 8.1), color="#D32F2F", lw=3.2, rad=0.1)
    
    # Op-Amp GND (Pin 4 at row 18 E) -> Blue Rail (-)
    draw_wire((rows_x[18], top_cols_y["D"]), (rows_x[18], 27.9), color="#212121", lw=3.2, rad=-0.1)

    # Power decoupling C5 (100nF / 104) between Pin 8 (row 15) and GND rail
    c5_x = rows_x[14]
    ax.plot([c5_x, c5_x], [bot_cols_y["H"], 6.2], color="#B0BEC5", lw=2.2, zorder=6)
    # jumper row 14 to row 15
    draw_wire((rows_x[15], bot_cols_y["H"]), (c5_x, bot_cols_y["H"]), color="#D32F2F", lw=2.2, rad=0)
    # C5 disc capacitor body
    c5_body = patches.Circle((c5_x, 9.5), 0.45, facecolor="#F57C00", edgecolor="#E65100", lw=1.2, zorder=7)
    ax.add_patch(c5_body)
    ax.text(c5_x - 0.6, 9.5, "C5: 100nF\n(Bypass)", fontsize=7.5, fontweight="bold", ha="right", va="center", color="#E65100")

    # Terminate Unused Op-Amp B (Pin 5 to GND, Pin 6 to Pin 7)
    draw_wire((rows_x[18], bot_cols_y["G"]), (rows_x[18], 6.2), color="#212121", lw=2.8, rad=0.1) # Pin 5 to GND
    draw_wire((rows_x[17], bot_cols_y["G"]), (rows_x[16], bot_cols_y["G"]), color="#7B1FA2", lw=2.8, rad=-0.3) # Pin 6 to Pin 7

    # =========================================================================
    # 3. MICROPHONE & BIAS INPUT CIRCUIT
    # =========================================================================
    # Electret Microphone Capsule at Row 6
    mic_x, mic_y = rows_x[4], top_cols_y["B"]
    mic_can = patches.Circle((mic_x, mic_y), 1.0, facecolor="#ECEFF1", edgecolor="#455A64", lw=2.0, zorder=10)
    ax.add_patch(mic_can)
    ax.text(mic_x, mic_y, "MIC1\nElectret", fontsize=7.5, fontweight="bold", ha="center", va="center", color="#263238", zorder=11)
    
    # Mic (-) terminal to GND rail
    draw_wire((mic_x, mic_y + 0.6), (rows_x[4], 27.9), color="#212121", lw=2.8, rad=-0.2)
    ax.text(rows_x[4] - 0.4, 26.5, "MIC (-)\nCase/GND", fontsize=7.5, color="#212121", fontweight="bold", ha="right")
    
    # Mic (+) terminal to Row 8
    draw_wire((mic_x, mic_y - 0.6), (rows_x[8], top_cols_y["A"]), color="#E64A19", lw=2.8, rad=0.2)
    ax.text(rows_x[8] - 0.4, top_cols_y["A"] + 0.5, "MIC (+)", fontsize=7.5, color="#E64A19", fontweight="bold", ha="right")

    # R1 (10 kΩ pull-up) from Row 8 to +3.3V rail
    draw_resistor((rows_x[8], top_cols_y["B"]), (rows_x[8], 29.8), "R1: 10kΩ\n(Mic Bias)", ["brown", "black", "orange"])

    # C1 (1 µF coupling) from Row 8 to Row 17 (Pin 3: IN+)
    c1_x1, c1_y1 = rows_x[8], top_cols_y["D"]
    c1_x2, c1_y2 = rows_x[17], top_cols_y["B"]
    # Wire leads
    ax.plot([c1_x1, rows_x[12]], [c1_y1, c1_y1], color="#B0BEC5", lw=2.2, zorder=6)
    ax.plot([rows_x[13], c1_x2], [c1_y2, c1_y2], color="#B0BEC5", lw=2.2, zorder=6)
    # Box film capacitor C1 body
    c1_box = patches.FancyBboxPatch((rows_x[12] - 0.2, c1_y1 - 0.45), 1.2, 0.9,
                                   boxstyle="round,pad=0.05,rounding_size=0.1",
                                   facecolor="#D32F2F", edgecolor="#B71C1C", lw=1.2, zorder=8)
    ax.add_patch(c1_box)
    ax.text(rows_x[12] + 0.4, c1_y1, "C1\n1µF", color="#FFFFFF", fontsize=7.5, fontweight="bold", ha="center", va="center", zorder=9)
    draw_wire((rows_x[13], c1_y1), (c1_x2, c1_y2), color="#E64A19", lw=2.5, rad=-0.2)

    # R2 (100 kΩ pull-up) from +3.3V rail to Row 17 (Pin 3)
    draw_resistor((rows_x[16], 29.8), (rows_x[17], top_cols_y["A"]), "R2: 100kΩ\n(Bias +)", ["brown", "black", "yellow"])

    # R3 (100 kΩ pull-down) from Row 17 (Pin 3) to GND rail
    draw_resistor((rows_x[17], top_cols_y["C"]), (rows_x[17], 27.9), "R3: 100kΩ\n(Bias -)", ["brown", "black", "yellow"])

    # Bulk power capacitor C2 (10 µF) across rails as recommended
    c2_x = rows_x[2]
    # C2 cylinder body
    c2_body = patches.Circle((c2_x, 28.85), 0.55, facecolor="#1976D2", edgecolor="#0D47A1", lw=1.2, zorder=7)
    ax.add_patch(c2_body)
    ax.plot([c2_x, c2_x], [29.8, 27.9], color="#B0BEC5", lw=2.2, zorder=6)
    ax.text(c2_x, 28.85, "C2\n10µF", color="#FFFFFF", fontsize=6.5, fontweight="bold", ha="center", va="center", zorder=8)
    ax.text(c2_x + 0.7, 28.85, "(Power Filter)", color="#0D47A1", fontsize=7, fontweight="bold", va="center")

    # =========================================================================
    # 4. FEEDBACK & GAIN NETWORK (Av = 101)
    # =========================================================================
    # R4 (100 kΩ feedback) between Pin 1 (Row 15) and Pin 2 (Row 16)
    draw_resistor((rows_x[15], top_cols_y["C"]), (rows_x[16], top_cols_y["C"]), "R4: 100kΩ (Feedback)", ["brown", "black", "yellow"])

    # R5 (1 kΩ) from Pin 2 (Row 16) to Row 22
    draw_resistor((rows_x[16], top_cols_y["B"]), (rows_x[22], top_cols_y["B"]), "R5: 1kΩ (Gain)", ["brown", "black", "red"])

    # C3 (10 µF electrolytic) from Row 22 to GND rail
    c3_x = rows_x[22]
    ax.plot([c3_x, c3_x], [top_cols_y["C"], 27.9], color="#B0BEC5", lw=2.2, zorder=6)
    c3_body = patches.Circle((c3_x, (top_cols_y["C"] + 27.9)/2.0), 0.55, facecolor="#1976D2", edgecolor="#0D47A1", lw=1.2, zorder=7)
    ax.add_patch(c3_body)
    ax.text(c3_x, (top_cols_y["C"] + 27.9)/2.0, "C3\n10µF", color="#FFFFFF", fontsize=6.5, fontweight="bold", ha="center", va="center", zorder=8)
    ax.text(c3_x + 0.7, (top_cols_y["C"] + 27.9)/2.0, "(-) to GND", color="#0D47A1", fontsize=7, fontweight="bold", va="center")

    # =========================================================================
    # 5. OUTPUT FILTER & ESP32-S3 CONNECTIONS
    # =========================================================================
    # R6 (1 kΩ) from Pin 1 (Row 15) to Row 26
    draw_resistor((rows_x[15], top_cols_y["A"]), (rows_x[26], top_cols_y["A"]), "R6: 1kΩ (Filter)", ["brown", "black", "red"])

    # C4 (10 nF disc / 103) from Row 26 to GND rail
    c4_x = rows_x[26]
    ax.plot([c4_x, c4_x], [top_cols_y["B"], 27.9], color="#B0BEC5", lw=2.2, zorder=6)
    c4_body = patches.Circle((c4_x, (top_cols_y["B"] + 27.9)/2.0), 0.45, facecolor="#F57C00", edgecolor="#E65100", lw=1.2, zorder=7)
    ax.add_patch(c4_body)
    ax.text(c4_x, (top_cols_y["B"] + 27.9)/2.0, "C4\n10nF", color="#FFFFFF", fontsize=6.5, fontweight="bold", ha="center", va="center", zorder=8)

    # ESP32-S3 Module illustration on the right
    esp_x0, esp_y0 = 23.5, 9.5
    esp_w, esp_h = 6.0, 11.0
    esp_box = patches.FancyBboxPatch((esp_x0, esp_y0), esp_w, esp_h,
                                     boxstyle="round,pad=0.2,rounding_size=0.4",
                                     facecolor="#263238", edgecolor="#37474F", lw=2.0, zorder=10)
    ax.add_patch(esp_box)
    
    # ESP32 RF Shield
    shield = patches.Rectangle((esp_x0 + 1.0, esp_y0 + 4.5), 4.0, 4.5, facecolor="#B0BEC5", edgecolor="#78909C", lw=1.5, zorder=11)
    ax.add_patch(shield)
    ax.text(esp_x0 + 3.0, esp_y0 + 6.75, "ESP32-S3\nWROOM", color="#263238", fontsize=9, fontweight="bold", ha="center", va="center", zorder=12)
    ax.text(esp_x0 + 3.0, esp_y0 + 2.5, "ESP32-S3 DevKit", color="#ECEFF1", fontsize=8.5, fontweight="bold", ha="center", va="center", zorder=12)
    
    # USB port
    usb = patches.Rectangle((esp_x0 + 1.8, esp_y0 - 0.3), 2.4, 1.2, facecolor="#CFD8DC", edgecolor="#78909C", lw=1.2, zorder=11)
    ax.add_patch(usb)
    ax.text(esp_x0 + 3.0, esp_y0 + 0.3, "USB-C", color="#37474F", fontsize=6.5, fontweight="bold", ha="center", va="center", zorder=12)

    # Wires from ESP32 to Breadboard:
    # 1. ESP32 3V3 pin to Red Rail (+)
    esp_3v3_pt = (esp_x0 + 0.5, esp_y0 + 9.5)
    ax.plot([esp_3v3_pt[0], esp_3v3_pt[0]], [esp_3v3_pt[1], 8.1], color="#D32F2F", lw=3.5, zorder=12)
    ax.text(esp_3v3_pt[0] + 0.8, esp_y0 + 9.5, "3V3 Pin", color="#D32F2F", fontsize=8, fontweight="bold", va="center")

    # 2. ESP32 GND pin to Blue Rail (-)
    esp_gnd_pt = (esp_x0 + 0.5, esp_y0 + 8.3)
    ax.plot([esp_gnd_pt[0], esp_gnd_pt[0] - 1.5, esp_gnd_pt[0] - 1.5], [esp_gnd_pt[1], esp_gnd_pt[1], 6.2], color="#212121", lw=3.5, zorder=12)
    ax.text(esp_gnd_pt[0] + 0.8, esp_y0 + 8.3, "GND Pin", color="#212121", fontsize=8, fontweight="bold", va="center")

    # 3. Audio Out: Row 26 (Col C) to ESP32 GPIO 1 pin
    esp_io1_pt = (esp_x0 + 0.5, esp_y0 + 4.0)
    draw_wire((rows_x[26], top_cols_y["C"]), esp_io1_pt, color="#00897B", lw=3.5, rad=-0.35)
    ax.text(esp_io1_pt[0] + 0.8, esp_y0 + 4.0, "GPIO 1 (ADC1_CH0)", color="#00897B", fontsize=8, fontweight="bold", va="center")

    # =========================================================================
    # CALLOUT BOXES & STEP-BY-STEP INSTRUCTIONS
    # =========================================================================
    summary_text = (
        "WIRING SUMMARY & CHECKLIST:\n"
        "• Row 8:  MIC(+) + R1 (10k to +3.3V) + C1 (1uF to Row 17)\n"
        "• Row 15: LM358 Pin 1 (OUT) + R4 (100k to Row 16) + R6 (1k to Row 26)\n"
        "• Row 16: LM358 Pin 2 (IN-) + R4 (100k from Row 15) + R5 (1k to Row 22)\n"
        "• Row 17: LM358 Pin 3 (IN+) + C1 (from Row 8) + R2 (100k to +3.3V) + R3 (100k to GND)\n"
        "• Row 18: LM358 Pin 4 (GND) to Blue rail | Pin 5 (IN+ B) to Blue rail\n"
        "• Row 22: R5 (1k from Row 16) + C3 (10uF positive leg) -> C3 negative leg to Blue rail (GND)\n"
        "• Row 26: R6 (1k from Row 15) + C4 (10nF to Blue rail) -> GREEN JUMPER TO ESP32 GPIO 1"
    )
    ax.text(1.5, 3.2, summary_text, fontsize=8.5, family="monospace", va="top",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#FFFFFF", edgecolor="#90A4AE", lw=1.2))

    test_text = (
        "QUICK VERIFICATION WITH MULTIMETER:\n"
        "1. Power on with ESP32 connected to USB.\n"
        "2. Measure DC voltage at Row 17 (Pin 3): should read exactly 1.65 V (VCC/2).\n"
        "3. Measure DC voltage at Row 26 (GPIO 1): should read 1.65 V.\n"
        "4. Speak into MIC: AC voltage will swing ±0.5V to ±1.0V around 1.65V."
    )
    ax.text(17.5, 3.2, test_text, fontsize=8.5, family="monospace", va="top",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#E8F5E9", edgecolor="#66BB6A", lw=1.2))

    ax.set_xlim(0, 31)
    ax.set_ylim(0, 35)
    ax.axis("off")
    plt.tight_layout()
    
    out_path = "/home/vishwa/Documents/design/breadboard_wiring_guide.png"
    plt.savefig(out_path, dpi=250, bbox_inches="tight")
    print(f"Breadboard diagram successfully generated at {out_path}")

if __name__ == "__main__":
    create_breadboard_diagram()
