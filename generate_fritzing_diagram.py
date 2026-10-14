#!/usr/bin/env python3
"""
Generate a pristine Fritzing-style wiring diagram exactly matching 'Pasted image.png'.
Layout:
- Pure white background (#FFFFFF)
- Realistic ESP32-S3 on the left with pins
- Microphone Preamplifier circuit on the right with Header pins (3V3, OUT, GND) on its left edge
- 100% clean, non-crossing orthogonal wires (Red, Yellow, Black)
- Bold floating text labels: '3.3V (Power)', 'GPIO 1 (ADC1_CH0)', 'GND'
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

BASE_DIR = "/home/vishwa/Documents/hacktivate"
OUTPUT_IMAGE = os.path.join(BASE_DIR, "esp32s3_mic_fritzing_wiring.png")

def create_fritzing_diagram():
    # Canvas dimensions: 1400 x 920
    w, h = 1400, 920
    fig = plt.figure(figsize=(14.0, 9.2), dpi=150)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis('off')
    
    # Pure white background like reference image
    bg = patches.Rectangle((0, 0), w, h, facecolor='#ffffff')
    ax.add_patch(bg)

    # =========================================================================
    # 1. DRAW ESP32-S3 DEVKIT (LEFT SIDE)
    # =========================================================================
    esp_x, esp_y, esp_w, esp_h = 80, 80, 270, 760
    
    # Main PCB Body (matte dark slate/black with rounded corners)
    esp_pcb = patches.FancyBboxPatch((esp_x, esp_y), esp_w, esp_h, boxstyle="round,pad=10,rounding_size=20",
                                     facecolor='#18181b', edgecolor='#27272a', linewidth=2)
    ax.add_patch(esp_pcb)
    
    # 4 Corner mounting holes
    for hx, hy in [(esp_x + 18, esp_y + 18), (esp_x + esp_w - 18, esp_y + 18),
                   (esp_x + 18, esp_y + esp_h - 18), (esp_x + esp_w - 18, esp_y + esp_h - 18)]:
        hole = patches.Circle((hx, hy), 8.5, facecolor='#ffffff', edgecolor='#71717a', linewidth=1.5)
        ax.add_patch(hole)

    # Top Antenna Area
    ant_box = patches.FancyBboxPatch((esp_x + 25, esp_y + esp_h - 90), esp_w - 50, 72,
                                     boxstyle="round,pad=2,rounding_size=4",
                                     facecolor='#09090b', edgecolor='#3f3f46', linewidth=1)
    ax.add_patch(ant_box)
    
    # Meandering copper antenna trace
    ant_pts = [
        (esp_x + 40, esp_y + esp_h - 78), (esp_x + 40, esp_y + esp_h - 32),
        (esp_x + 65, esp_y + esp_h - 32), (esp_x + 65, esp_y + esp_h - 72),
        (esp_x + 90, esp_y + esp_h - 72), (esp_x + 90, esp_y + esp_h - 32),
        (esp_x + 115, esp_y + esp_h - 32), (esp_x + 115, esp_y + esp_h - 72),
        (esp_x + 140, esp_y + esp_h - 72), (esp_x + 140, esp_y + esp_h - 32),
        (esp_x + 165, esp_y + esp_h - 32), (esp_x + 165, esp_y + esp_h - 72),
        (esp_x + 190, esp_y + esp_h - 72), (esp_x + 190, esp_y + esp_h - 32),
        (esp_x + 215, esp_y + esp_h - 32), (esp_x + 215, esp_y + esp_h - 78),
    ]
    for i in range(len(ant_pts) - 1):
        ax.plot([ant_pts[i][0], ant_pts[i+1][0]], [ant_pts[i][1], ant_pts[i+1][1]],
                color='#e4e4e7', linewidth=2.5, solid_capstyle='round')

    # ESP32-S3 Metal RF Shield
    shield_w, shield_h = 165, 230
    shield_x = esp_x + (esp_w - shield_w) / 2
    shield_y = esp_y + esp_h - 355
    shield = patches.FancyBboxPatch((shield_x, shield_y), shield_w, shield_h,
                                   boxstyle="round,pad=4,rounding_size=6",
                                   facecolor='#3f3f46', edgecolor='#a1a1aa', linewidth=1.5)
    ax.add_patch(shield)
    
    # Shield Markings
    ax.text(shield_x + shield_w/2, shield_y + 180, "ESP32-S3", color='#fafafa', fontsize=15, fontweight='bold', ha='center', va='center')
    ax.text(shield_x + shield_w/2, shield_y + 155, "WROOM-1", color='#e4e4e7', fontsize=12, fontweight='bold', ha='center', va='center')
    
    # Wi-Fi badge
    wifi_box = patches.FancyBboxPatch((shield_x + shield_w/2 - 38, shield_y + 98), 76, 26,
                                      boxstyle="round,pad=2,rounding_size=4",
                                      facecolor='#27272a', edgecolor='#71717a', linewidth=1)
    ax.add_patch(wifi_box)
    ax.text(shield_x + shield_w/2, shield_y + 111, "Wi-Fi + BT", color='#e4e4e7', fontsize=9, fontweight='bold', ha='center', va='center')
    ax.text(shield_x + shield_w/2, shield_y + 55, "Xtensa Dual-Core 240MHz\n12-Bit SAR ADC", color='#a1a1aa', fontsize=8.5, ha='center', va='center')

    # USB-C Port at bottom
    usb_w, usb_h = 72, 36
    usb = patches.FancyBboxPatch((esp_x + (esp_w - usb_w)/2, esp_y - 12), usb_w, usb_h,
                                boxstyle="round,pad=3,rounding_size=5",
                                facecolor='#e4e4e7', edgecolor='#71717a', linewidth=1.5)
    ax.add_patch(usb)
    ax.text(esp_x + esp_w/2, esp_y + 6, "USB-C", color='#18181b', fontsize=8.5, fontweight='bold', ha='center', va='center')

    # Pushbuttons (RST & BOOT)
    for bx, bname in [(esp_x + 42, "RST"), (esp_x + esp_w - 42, "BOOT")]:
        btn_body = patches.Rectangle((bx - 12, esp_y + 36), 24, 24, facecolor='#27272a', edgecolor='#a1a1aa', linewidth=1)
        ax.add_patch(btn_body)
        btn_act = patches.Circle((bx, esp_y + 48), 6, facecolor='#e4e4e7', edgecolor='#71717a', linewidth=1)
        ax.add_patch(btn_act)
        ax.text(bx, esp_y + 70, bname, color='#a1a1aa', fontsize=7.5, fontweight='bold', ha='center', va='center')

    # Pin Headers (22 pins per side)
    num_pins = 22
    pin_pitch = 27
    start_pin_y = esp_y + 100
    
    left_pin_x = esp_x + 12
    right_pin_x = esp_x + esp_w - 12
    
    left_labels = ["3V3", "EN", "IO4", "IO5", "IO6", "IO7", "IO15", "IO16", "IO17", "IO18", "IO8", "IO3", "IO46", "IO9", "IO10", "IO11", "IO12", "IO13", "IO14", "5V", "GND", "GND"]
    right_labels = ["GND", "IO43", "IO44", "IO1", "IO2", "IO42", "IO41", "IO40", "IO39", "IO38", "IO37", "IO36", "IO35", "IO0", "IO45", "IO48", "IO47", "IO21", "IO20", "IO19", "GND", "3V3"]

    esp_pin_coords = {}

    for i in range(num_pins):
        py = start_pin_y + i * pin_pitch
        
        # Left Pin pad
        l_pad = patches.Rectangle((left_pin_x - 5, py - 5), 10, 10, facecolor='#ca8a04', edgecolor='#713f12', linewidth=0.8)
        ax.add_patch(l_pad)
        l_hole = patches.Circle((left_pin_x, py), 2.5, facecolor='#18181b')
        ax.add_patch(l_hole)
        ax.text(left_pin_x + 12, py, left_labels[i], color='#ffffff', fontsize=7.5, fontweight='bold', va='center')
        
        # Right Pin pad
        r_pad = patches.Rectangle((right_pin_x - 5, py - 5), 10, 10, facecolor='#ca8a04', edgecolor='#713f12', linewidth=0.8)
        ax.add_patch(r_pad)
        r_hole = patches.Circle((right_pin_x, py), 2.5, facecolor='#18181b')
        ax.add_patch(r_hole)
        ax.text(right_pin_x - 12, py, right_labels[i], color='#ffffff', fontsize=7.5, fontweight='bold', ha='right', va='center')
        
        # Key pins needed
        if right_labels[i] == "IO1":
            esp_pin_coords["IO1"] = (right_pin_x, py)
        if right_labels[i] == "GND" and i == 0:
            esp_pin_coords["GND"] = (right_pin_x, py)
        if right_labels[i] == "3V3" and i == 21:
            esp_pin_coords["3V3_TOP"] = (right_pin_x, py)

    # =========================================================================
    # 2. DRAW MICROPHONE PREAMPLIFIER CIRCUIT MODULE (RIGHT SIDE)
    # =========================================================================
    # Positioned at mic_x = 810 to leave plenty of room for wires & labels
    mic_x, mic_y, mic_w, mic_h = 810, 120, 530, 700
    
    # Preamp PCB Body
    mic_pcb = patches.FancyBboxPatch((mic_x, mic_y), mic_w, mic_h, boxstyle="round,pad=10,rounding_size=16",
                                     facecolor='#143d2b', edgecolor='#064e3b', linewidth=2.5)
    ax.add_patch(mic_pcb)
    
    # 4 Corner mounting holes
    for hx, hy in [(mic_x + 18, mic_y + 18), (mic_x + mic_w - 18, mic_y + 18),
                   (mic_x + 18, mic_y + mic_h - 18), (mic_x + mic_w - 18, mic_y + mic_h - 18)]:
        hole = patches.Circle((hx, hy), 8.5, facecolor='#ffffff', edgecolor='#a1a1aa', linewidth=1.5)
        ax.add_patch(hole)

    # Header Silkscreen
    ax.text(mic_x + mic_w/2, mic_y + mic_h - 35, "ESP32-S3 MIC PREAMPLIFIER",
            color='#ffffff', fontsize=14, fontweight='bold', ha='center', va='center')
    ax.text(mic_x + mic_w/2, mic_y + mic_h - 60, "LM358 LOW-NOISE OP-AMP  |  GAIN: 40.1 dB (x101)",
            color='#86efac', fontsize=10, fontweight='bold', ha='center', va='center')

    # --- HEADER J1 ON THE LEFT EDGE OF PREAMP BOARD ---
    j1_px = mic_x + 40
    j1_3v3_y = mic_y + 550   # Top: 3V3
    j1_io1_y = mic_y + 360   # Mid: OUT (IO1)
    j1_gnd_y = mic_y + 170   # Bot: GND
    
    # Header black plastic socket
    j1_hdr = patches.Rectangle((j1_px - 14, j1_gnd_y - 25), 28, 430, facecolor='#000000', edgecolor='#52525b', linewidth=1.5)
    ax.add_patch(j1_hdr)
    ax.text(j1_px, j1_3v3_y + 35, "HEADER J1", color='#38bdf8', fontsize=8.5, fontweight='bold', ha='center')

    # 3 Gold Pin Pads
    header_pins = [
        (j1_3v3_y, "3V3 (VCC)", "+3.3V Power"),
        (j1_io1_y, "OUT (IO1)", "Audio Output"),
        (j1_gnd_y, "GND", "Ground")
    ]
    for (py, plabel, psub) in header_pins:
        ax.add_patch(patches.Rectangle((j1_px - 8, py - 8), 16, 16, facecolor='#ca8a04', edgecolor='#fef08a', linewidth=1))
        ax.add_patch(patches.Circle((j1_px, py), 4, facecolor='#000000'))
        ax.text(j1_px + 20, py + 2, plabel, color='#ffffff', fontsize=9.5, fontweight='bold', va='center')

    # --- COMPONENTS ON THE PREAMP BOARD ---
    # A. Electret Microphone Capsule
    mc_x, mc_y = mic_x + 180, mic_y + 440
    mic_outer = patches.Circle((mc_x, mc_y), 36, facecolor='#94a3b8', edgecolor='#cbd5e1', linewidth=2.5)
    ax.add_patch(mic_outer)
    mic_inner = patches.Circle((mc_x, mc_y), 24, facecolor='#334155', edgecolor='#1e293b', linewidth=1.5)
    ax.add_patch(mic_inner)
    ax.text(mc_x, mc_y, "MIC", color='#ffffff', fontsize=11, fontweight='bold', ha='center', va='center')
    ax.text(mc_x, mc_y - 52, "Electret Capsule\n(MK1 / J2)", color='#f8fafc', fontsize=9, fontweight='bold', ha='center')

    # B. LM358 DIP-8 IC
    ic_x, ic_y = mic_x + 350, mic_y + 300
    ic_w, ic_h = 75, 125
    ic_body = patches.Rectangle((ic_x, ic_y), ic_w, ic_h, facecolor='#18181b', edgecolor='#3f3f46', linewidth=2)
    ax.add_patch(ic_body)
    notch = patches.Arc((ic_x + ic_w/2, ic_y + ic_h), 22, 18, theta1=180, theta2=360, color='#71717a', linewidth=2)
    ax.add_patch(notch)
    ax.text(ic_x + ic_w/2, ic_y + ic_h/2, "LM358", color='#e4e4e7', fontsize=12, fontweight='bold', ha='center', va='center', rotation=90)
    
    # 8 IC Pins
    for idx, (py, pnum) in enumerate([(ic_y + ic_h - 18, "1"), (ic_y + ic_h - 48, "2"), (ic_y + ic_h - 78, "3"), (ic_y + ic_h - 108, "4")]):
        ax.add_patch(patches.Rectangle((ic_x - 14, py - 4), 14, 8, facecolor='#e4e4e7', edgecolor='#71717a'))
        ax.text(ic_x + 8, py, pnum, color='#a1a1aa', fontsize=7.5, va='center')
        rpnum = str(5 + idx)
        ax.add_patch(patches.Rectangle((ic_x + ic_w, py - 4), 14, 8, facecolor='#e4e4e7', edgecolor='#71717a'))
        ax.text(ic_x + ic_w - 8, py, rpnum, color='#a1a1aa', fontsize=7.5, ha='right', va='center')

    # Resistors
    def draw_resistor(rx, ry, val_text, color_bands, horizontal=True):
        rw, rh = (58, 20) if horizontal else (20, 58)
        if horizontal:
            ax.plot([rx - 12, rx + rw + 12], [ry + rh/2, ry + rh/2], color='#cbd5e1', linewidth=2)
        else:
            ax.plot([rx + rw/2, rx + rw/2], [ry - 12, ry + rh + 12], color='#cbd5e1', linewidth=2)
        body = patches.FancyBboxPatch((rx, ry), rw, rh, boxstyle="round,pad=2,rounding_size=5",
                                      facecolor='#fef3c7', edgecolor='#b45309', linewidth=1)
        ax.add_patch(body)
        for b_idx, b_col in enumerate(color_bands):
            if horizontal:
                ax.plot([rx + 13 + b_idx * 9, rx + 13 + b_idx * 9], [ry + 2, ry + rh - 2], color=b_col, linewidth=3)
            else:
                ax.plot([rx + 2, rx + rw - 2], [ry + 13 + b_idx * 9, ry + 13 + b_idx * 9], color=b_col, linewidth=3)
        ax.text(rx + rw/2, ry - 13 if horizontal else ry + rh/2, val_text,
                color='#fef08a', fontsize=8.5, fontweight='bold', ha='center', va='center')

    draw_resistor(mic_x + 150, mic_y + 550, "R1: 10k", ['#854d0e', '#000000', '#ea580c', '#eab308'], horizontal=True)
    draw_resistor(mic_x + 250, mic_y + 550, "R2: 100k", ['#854d0e', '#000000', '#facc15', '#eab308'], horizontal=True)
    draw_resistor(mic_x + 250, mic_y + 160, "R3: 100k", ['#854d0e', '#000000', '#facc15', '#eab308'], horizontal=True)
    draw_resistor(mic_x + 350, mic_y + 490, "R4: 100k", ['#854d0e', '#000000', '#facc15', '#eab308'], horizontal=True)
    draw_resistor(mic_x + 350, mic_y + 190, "R5: 1k", ['#854d0e', '#000000', '#dc2626', '#eab308'], horizontal=True)
    draw_resistor(mic_x + 450, mic_y + 350, "R6: 1k", ['#854d0e', '#000000', '#dc2626', '#eab308'], horizontal=True)

    # Capacitors
    c1_box = patches.Rectangle((mic_x + 165, mic_y + 340), 34, 22, facecolor='#dc2626', edgecolor='#991b1b', linewidth=1.5)
    ax.add_patch(c1_box)
    ax.text(mic_x + 182, mic_y + 351, "C1: 1µF", color='#ffffff', fontsize=7.5, fontweight='bold', ha='center', va='center')
    
    c3 = patches.Circle((mic_x + 435, mic_y + 200), 16, facecolor='#2563eb', edgecolor='#93c5fd', linewidth=1.5)
    ax.add_patch(c3)
    ax.text(mic_x + 435, mic_y + 200, "C3\n10µF", color='#ffffff', fontsize=6.5, fontweight='bold', ha='center', va='center')
    
    c4 = patches.Circle((mic_x + 465, mic_y + 280), 14, facecolor='#ea580c', edgecolor='#fed7aa', linewidth=1.5)
    ax.add_patch(c4)
    ax.text(mic_x + 465, mic_y + 280, "C4\n10nF", color='#ffffff', fontsize=6.5, fontweight='bold', ha='center', va='center')

    c5 = patches.Circle((mic_x + 465, mic_y + 500), 14, facecolor='#ea580c', edgecolor='#fed7aa', linewidth=1.5)
    ax.add_patch(c5)
    ax.text(mic_x + 465, mic_y + 500, "C5\n100n", color='#ffffff', fontsize=6.5, fontweight='bold', ha='center', va='center')

    # =========================================================================
    # 3. DRAW FRITZING-STYLE SOLID WIRES (ZERO CROSSINGS, ZERO OVERLAPS)
    # =========================================================================
    def draw_fritzing_wire(pts, core_color='#ef4444', outline_color='#000000', wire_width=7.5):
        for i in range(len(pts) - 1):
            ax.plot([pts[i][0], pts[i+1][0]], [pts[i][1], pts[i+1][1]],
                    color=outline_color, linewidth=wire_width + 3.5, solid_capstyle='round', zorder=10)
        for i in range(len(pts) - 1):
            ax.plot([pts[i][0], pts[i+1][0]], [pts[i][1], pts[i+1][1]],
                    color=core_color, linewidth=wire_width, solid_capstyle='round', zorder=11)
            
        ax.add_patch(patches.Circle(pts[0], 7, facecolor=core_color, edgecolor=outline_color, linewidth=2, zorder=15))
        ax.add_patch(patches.Circle(pts[0], 2.8, facecolor='#000000', zorder=16))
        ax.add_patch(patches.Circle(pts[-1], 7, facecolor=core_color, edgecolor=outline_color, linewidth=2, zorder=15))
        ax.add_patch(patches.Circle(pts[-1], 2.8, facecolor='#000000', zorder=16))

    # --- TOP WIRE: RED (+3.3V) ---
    p_3v3 = esp_pin_coords["3V3_TOP"]
    wire_red = [
        (p_3v3[0], p_3v3[1]),
        (p_3v3[0] + 110, p_3v3[1]),
        (p_3v3[0] + 110, j1_3v3_y),
        (j1_px, j1_3v3_y)
    ]
    draw_fritzing_wire(wire_red, core_color='#dc2626', outline_color='#450a0a', wire_width=7.5)

    # --- MIDDLE WIRE: YELLOW (GPIO 1 / ADC1_CH0) ---
    p_io1 = esp_pin_coords["IO1"]
    wire_yellow = [
        (p_io1[0], p_io1[1]),
        (p_io1[0] + 180, p_io1[1]),
        (p_io1[0] + 180, j1_io1_y),
        (j1_px, j1_io1_y)
    ]
    draw_fritzing_wire(wire_yellow, core_color='#facc15', outline_color='#854d0e', wire_width=7.5)

    # --- BOTTOM WIRE: BLACK (GND) ---
    p_gnd = esp_pin_coords["GND"]
    wire_black = [
        (p_gnd[0], p_gnd[1]),
        (p_gnd[0] + 250, p_gnd[1]),
        (p_gnd[0] + 250, j1_gnd_y),
        (j1_px, j1_gnd_y)
    ]
    draw_fritzing_wire(wire_black, core_color='#18181b', outline_color='#09090b', wire_width=7.5)

    # =========================================================================
    # 4. BOLD WIRE CALLOUT LABELS (PLACED BEAUTIFULLY OVER THE WIRE RUNS)
    # =========================================================================
    # Red Wire Label
    ax.text(p_3v3[0] + 130, j1_3v3_y + 15, "3.3V (Power)",
            color='#dc2626', fontsize=18, fontweight='bold', va='bottom', ha='left')

    # Yellow Wire Label
    ax.text(p_io1[0] + 200, j1_io1_y + 15, "GPIO 1 (ADC1_CH0)",
            color='#ca8a04', fontsize=18, fontweight='bold', va='bottom', ha='left')
    
    # Black Wire Label
    ax.text(p_gnd[0] + 270, j1_gnd_y + 15, "GND (Ground)",
            color='#000000', fontsize=18, fontweight='bold', va='bottom', ha='left')

    # =========================================================================
    # 5. HEADER & FOOTER
    # =========================================================================
    ax.text(w / 2, h - 35, "ESP32-S3 Electret Microphone Preamplifier Wiring Diagram",
            color='#0f172a', fontsize=22, fontweight='bold', ha='center', va='center')
    ax.text(w / 2, h - 60, "Single-Supply LM358 Circuit Hookup for 12-Bit Analog-to-Digital Audio Sampling",
            color='#64748b', fontsize=12, ha='center', va='center')

    # Quick Verification Banner
    info_box = patches.FancyBboxPatch((mic_x, 30), mic_w, 75, boxstyle="round,pad=6,rounding_size=8",
                                      facecolor='#f8fafc', edgecolor='#cbd5e1', linewidth=1.5)
    ax.add_patch(info_box)
    ax.text(mic_x + 18, 86, "VERIFICATION & OPERATING VOLTAGES:", color='#0f172a', fontsize=10.5, fontweight='bold')
    ax.text(mic_x + 18, 66, "• DC Bias Operating Point: Exactly 1.65V DC (VCC / 2) on GPIO 1 — safe for 0–3.3V ADC", color='#334155', fontsize=9.5)
    ax.text(mic_x + 18, 48, "• AC Audio Dynamic Swing: 0.8V to 2.5V  |  Gain: +40.1 dB (x101)  |  LPF fc: 15.9 kHz", color='#334155', fontsize=9.5)

    plt.savefig(OUTPUT_IMAGE, bbox_inches='tight', pad_inches=0.1, facecolor='#ffffff')
    plt.close()
    print(f"Fritzing diagram saved to: {OUTPUT_IMAGE}")

if __name__ == "__main__":
    create_fritzing_diagram()
