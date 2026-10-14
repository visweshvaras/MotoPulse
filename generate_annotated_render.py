#!/usr/bin/env python3
"""
Generate a high-resolution annotated 3D PCB top-view graphic
using standard Cartesian coordinates (Y=0 at bottom, Y=ch at top).
"""

import os
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.patches as patches

BASE_DIR = "/home/vishwa/Documents/design"
INPUT_RENDER = os.path.join(BASE_DIR, "pcb_render_top.png")
OUTPUT_IMAGE = os.path.join(BASE_DIR, "esp32s3_connections_annotated.png")

def generate():
    render_img = Image.open(INPUT_RENDER)
    
    # Target canvas size: 2600 x 1500
    cw, ch = 2600, 1500
    
    # Crop transparent borders around the PCB
    bbox = render_img.getbbox()
    if bbox:
        pad = 20
        box = (max(0, bbox[0]-pad), max(0, bbox[1]-pad), min(render_img.width, bbox[2]+pad), min(render_img.height, bbox[3]+pad))
        pcb_cropped = render_img.crop(box)
    else:
        pcb_cropped = render_img

    # Scale PCB to fit width ~1420
    target_w = 1420
    ratio = target_w / pcb_cropped.width
    target_h = int(pcb_cropped.height * ratio)
    pcb_scaled = pcb_cropped.resize((target_w, target_h), Image.Resampling.LANCZOS)
    
    # Create dark background image
    canvas = Image.new("RGBA", (cw, ch), (15, 23, 42, 255))
    
    # Paste PCB at (60, 260) in PIL coordinates (top-down)
    paste_x = 60
    paste_y_pil = 270 # from top
    canvas.paste(pcb_scaled, (paste_x, paste_y_pil), pcb_scaled)
    
    temp_canvas = os.path.join(BASE_DIR, "temp_canvas.png")
    canvas.save(temp_canvas)
    
    # Matplotlib with standard Cartesian coordinates: (0,0) bottom-left, (cw, ch) top-right
    fig = plt.figure(figsize=(26, 15), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, cw)
    ax.set_ylim(0, ch)
    ax.axis('off')
    
    # Invert Y when displaying PIL image so that (0,0) of image is at top (ch)
    loaded_canvas = Image.open(temp_canvas)
    ax.imshow(loaded_canvas, extent=[0, cw, 0, ch])
    
    # Function to convert relative PCB coordinates (0-1, 0-1 from top-left) to Cartesian (0-cw, 0-ch)
    def pcb_coord(rel_x, rel_y):
        cx = paste_x + rel_x * target_w
        # In Cartesian, Y from bottom = ch - (paste_y_pil + rel_y * target_h)
        cy = ch - (paste_y_pil + rel_y * target_h)
        return (cx, cy)

    # 1. Main Header Title
    ax.text(cw / 2, ch - 55, "ESP32-S3 & LM358 Microphone Preamplifier — KiCad 3D Top View & Wiring",
            color='#f8fafc', fontsize=24, fontweight='bold', ha='center', va='center')
    ax.text(cw / 2, ch - 95, "Complete Component Interconnections, Physical Copper Traces, and Direct Microcontroller Hookup",
            color='#94a3b8', fontsize=14, ha='center', va='center')
    
    # 2. Signal Path Ribbon
    flow_box = patches.FancyBboxPatch((180, ch - 165), 1580, 46, boxstyle="round,pad=6,rounding_size=10",
                                      facecolor='#1e293b', edgecolor='#38bdf8', linewidth=1.8)
    ax.add_patch(flow_box)
    ax.text(970, ch - 142, "SIGNAL PATH:  MIC Audio  ➔  C1 (AC Coupling)  ➔  LM358 Pin 3 (IN+)  ➔  LM358 Pin 1 (OUT)  ➔  R6/C4 Low-Pass Filter  ➔  ESP32 GPIO 1",
            color='#38bdf8', fontsize=12.5, fontweight='bold', ha='center', va='center')

    # Helper function for callouts
    def draw_callout(comp_rel, box_xy, title, desc, tag_color='#38bdf8', align='left'):
        cx, cy = pcb_coord(comp_rel[0], comp_rel[1])
        bx, by = box_xy[0], box_xy[1]
        
        # Component target dot
        ax.plot(cx, cy, 'o', color=tag_color, markersize=10, markeredgecolor='white', markeredgewidth=2)
        
        # Connecting line
        ax.plot([cx, bx], [cy, by], color=tag_color, linewidth=2.2, alpha=0.9)
        
        # Callout box
        ha = 'right' if align == 'left' else 'left'
        tx = bx - 12 if align == 'left' else bx + 12
        txt = f" {title} \n {desc} "
        ax.text(tx, by, txt, color='#f1f5f9', fontsize=11, ha=ha, va='center',
                bbox=dict(boxstyle='round,pad=0.6', facecolor='#1e293b', edgecolor=tag_color, alpha=0.96, linewidth=1.5))

    # --- CALLOUTS AROUND PCB ---
    # 1. MK1 / J2 (Electret Mic)
    draw_callout((0.155, 0.45), (140, ch - 680),
                 "MK1 / J2 : Electret Microphone Input",
                 "• Metal casing terminal = GND\n• Positive terminal = Audio signal out\n• Connects to R1 bias and C1 coupling capacitor",
                 tag_color='#38bdf8', align='left')

    # 2. R1 (Mic Bias)
    draw_callout((0.24, 0.21), (140, ch - 360),
                 "R1 : 10 kΩ (Microphone Bias Pull-up)",
                 "• Supplies ~0.3 mA operating current to electret capsule JFET\n• Connected from +3.3V power rail to microphone (+)",
                 tag_color='#fbbf24', align='left')

    # 3. C1 (AC Coupling)
    draw_callout((0.28, 0.44), (140, ch - 520),
                 "C1 : 1 µF (DC Blocking / AC Coupling)",
                 "• Blocks microphone DC supply voltage\n• Passes AC voice audio to LM358 Pin 3 (IN+)\n• High-pass cutoff frequency: < 3.2 Hz",
                 tag_color='#f43f5e', align='left')

    # 4. R2 & R3 (Mid-Rail Bias)
    draw_callout((0.36, 0.22), (480, ch - 1340),
                 "R2 (100 kΩ) & R3 (100 kΩ) : Bias Divider",
                 "• Sets DC operating point: VCC / 2 = 1.65 V\n• Biases LM358 Pin 3 (IN+) for maximum symmetrical audio headroom\n• Centers waveform perfectly in ESP32 0–3.3V ADC window",
                 tag_color='#c084fc', align='right')

    # 5. R4 (Feedback)
    draw_callout((0.57, 0.21), (1080, ch - 1340),
                 "R4 : 100 kΩ (Negative Feedback)",
                 "• Connects LM358 Pin 1 (OUT) back to Pin 2 (IN-)\n• Voltage gain: Av = 1 + (R4 / R5) = 101 (+40.1 dB)\n• Provides clean, closed-loop amplification",
                 tag_color='#4ade80', align='right')

    # 6. U1 (LM358 Dual Op-Amp)
    draw_callout((0.57, 0.49), (820, ch - 1420),
                 "U1 : LM358 Dual Operational Amplifier (DIP-8)",
                 "• Pin 1: OUT1 (Audio Out)  |  Pin 2: IN1- (Feedback)  |  Pin 3: IN1+ (Audio In)\n• Pin 4: GND  |  Pin 8: +3.3V VCC  |  Unit B terminated (Pin 5 to GND, 6-7 looped)",
                 tag_color='#38bdf8', align='center')

    # 7. R5 & C3 (Gain & AC Ground)
    draw_callout((0.58, 0.77), (1380, ch - 1420),
                 "R5 (1 kΩ) & C3 (10 µF) : AC Gain Network",
                 "• Sets DC gain to 1.0 to preserve precise 1.65 V DC bias\n• Delivers full x101 (+40dB) gain to AC audio above 15.9 Hz",
                 tag_color='#facc15', align='right')

    # 8. C5 (Power Decoupling)
    draw_callout((0.69, 0.22), (1330, ch - 240),
                 "C5 : 100 nF (High-Frequency Bypass)",
                 "• Mounted right next to LM358 Pin 8 (VCC)\n• Absorbs high-frequency switching transients",
                 tag_color='#fb923c', align='right')

    # 9. R6 & C4 (Anti-Aliasing Filter)
    draw_callout((0.71, 0.40), (1330, ch - 390),
                 "R6 (1 kΩ) & C4 (10 nF) : RC Low-Pass Filter",
                 "• Cutoff frequency: fc = 1 / (2π · 1k · 10n) = 15.9 kHz\n• Filters op-amp hiss and prevents ESP32 ADC aliasing\n• Current-limiting protection into ESP32 ADC",
                 tag_color='#2dd4bf', align='right')

    # --- ESP32-S3 DEVKIT (Right Column) ---
    esp_x, esp_y, esp_w, esp_h = 1840, ch - 1200, 700, 920
    
    # Outer DevKit Box
    dev_box = patches.FancyBboxPatch((esp_x, esp_y), esp_w, esp_h, boxstyle="round,pad=14,rounding_size=20",
                                     facecolor='#1e293b', edgecolor='#475569', linewidth=3)
    ax.add_patch(dev_box)
    
    # Header Title on DevKit
    ax.text(esp_x + esp_w/2, esp_y + esp_h - 45, "ESP32-S3 DevKit Wiring", color='#38bdf8', fontsize=18, fontweight='bold', ha='center')
    ax.text(esp_x + esp_w/2, esp_y + esp_h - 75, "Connect Preamp Header J1 to ESP32-S3 pins as shown:", color='#94a3b8', fontsize=12, ha='center')
    
    # SoC Module Shield
    soc = patches.FancyBboxPatch((esp_x + 90, esp_y + esp_h - 350), 520, 240, boxstyle="round,pad=8,rounding_size=10",
                                 facecolor='#334155', edgecolor='#94a3b8', linewidth=2)
    ax.add_patch(soc)
    ax.text(esp_x + esp_w/2, esp_y + esp_h - 225, "ESP32-S3\nWROOM-1", color='#f8fafc', fontsize=22, fontweight='bold', ha='center', va='center')
    ax.text(esp_x + esp_w/2, esp_y + esp_h - 305, "Dual-Core Xtensa LX7 @ 240 MHz | Built-in 12-Bit SAR ADC", color='#38bdf8', fontsize=11, ha='center', va='center')
    
    # Three Pin Connection Badges on ESP32
    pins_data = [
        ("ESP32-S3  3V3  (Pin)", "Supplies clean +3.3V DC to Preamp & Mic", "#ef4444", "#7f1d1d", esp_y + 440, "3V3"),
        ("ESP32-S3  GND  (Pin)", "Common ground return", "#94a3b8", "#1e293b", esp_y + 320, "GND"),
        ("ESP32-S3  GPIO 1  (ADC1_CH0)", "Analog Audio Input to 12-bit ADC", "#10b981", "#064e3b", esp_y + 200, "IO1")
    ]
    
    # Header J1 positions on PCB
    j1_base = pcb_coord(0.795, 0.445)
    j1_3v3_xy = (j1_base[0], j1_base[1] + 46)
    j1_gnd_xy = (j1_base[0], j1_base[1])
    j1_io1_xy = (j1_base[0], j1_base[1] - 46)
    
    # Draw Header J1 Badge
    j1_rect = patches.FancyBboxPatch((j1_base[0] - 45, j1_base[1] + 80), 140, 50, boxstyle="round,pad=4,rounding_size=6",
                                     facecolor='#0284c7', edgecolor='#38bdf8', linewidth=1.8)
    ax.add_patch(j1_rect)
    ax.text(j1_base[0] + 25, j1_base[1] + 105, "HEADER J1", color='white', fontsize=12, fontweight='bold', ha='center', va='center')
    
    j1_targets = [j1_3v3_xy, j1_gnd_xy, j1_io1_xy]
    
    for (name, desc, border_col, bg_col, py, tag), j1_pt in zip(pins_data, j1_targets):
        badge = patches.FancyBboxPatch((esp_x + 50, py - 35), 600, 72, boxstyle="round,pad=6,rounding_size=8",
                                       facecolor=bg_col, edgecolor=border_col, linewidth=2)
        ax.add_patch(badge)
        ax.text(esp_x + 80, py + 10, name, color='#ffffff', fontsize=14, fontweight='bold', va='center')
        ax.text(esp_x + 80, py - 16, desc, color='#cbd5e1', fontsize=11, va='center')
        
        # Wire arrow from Preamp J1 to ESP32 Badge
        ax.annotate("", xy=(esp_x + 50, py), xytext=j1_pt,
                    arrowprops=dict(arrowstyle="->", color=border_col, lw=3.5, shrinkA=8, shrinkB=6,
                                    connectionstyle="arc3,rad=-0.08"))

    # USB-C port at bottom of DevKit
    usb = patches.FancyBboxPatch((esp_x + esp_w/2 - 90, esp_y + 35), 180, 42, boxstyle="round,pad=4,rounding_size=6",
                                 facecolor='#020617', edgecolor='#cbd5e1', linewidth=2)
    ax.add_patch(usb)
    ax.text(esp_x + esp_w/2, esp_y + 56, "USB-C (Power / Flash)", color='#f8fafc', fontsize=12, fontweight='bold', ha='center', va='center')

    # Bottom Summary Checklist Banner
    check_box = patches.FancyBboxPatch((80, 50), 650, 95, boxstyle="round,pad=6,rounding_size=8",
                                       facecolor='#1e293b', edgecolor='#38bdf8', linewidth=1.5)
    ax.add_patch(check_box)
    ax.text(100, 115, "QUICK MULTIMETER SANITY VERIFICATION:", color='#38bdf8', fontsize=11, fontweight='bold')
    ax.text(100, 90, "• DC Voltage at Header J1 Pin 3 (IO1) : Exactly 1.65 V DC (VCC / 2)", color='#cbd5e1', fontsize=10.5)
    ax.text(100, 68, "• Audio AC Swing when speaking : 0.8 V to 2.5 V (within 0–3.3V ADC range)", color='#cbd5e1', fontsize=10.5)

    plt.savefig(OUTPUT_IMAGE, bbox_inches='tight', pad_inches=0.1, facecolor='#0f172a')
    plt.close()
    
    if os.path.exists(temp_canvas):
        os.remove(temp_canvas)
        
    print(f"Annotated 3D render generated successfully at {OUTPUT_IMAGE}")

if __name__ == "__main__":
    generate()
