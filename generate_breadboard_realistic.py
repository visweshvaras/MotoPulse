#!/usr/bin/env python3
"""
Ultra-Clear, High-Precision Breadboard Assembly Diagram (V5 - Direct Assembly Focus)
Circuit: ESP32-S3 Microphone Preamplifier (LM358)
Features:
- Focused 20-column breadboard layout (giant, high-resolution holes and coordinates)
- High-visibility colored insertion rings on EVERY active tie point
- Clear step-by-step assembly badges [1] through [10]
- Realistic components with exact color bands and printed values
- Left-hand side 5-minute quick assembly card
- Zero overlapping text or crossing leads
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

BASE_DIR = "/home/vishwa/Documents/hacktivate"
OUTPUT_IMAGE = os.path.join(BASE_DIR, "mic_breadboard_circuit.png")

def generate_mic_breadboard():
    cw, ch = 2500, 1600
    fig = plt.figure(figsize=(25, 16), dpi=180)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, cw)
    ax.set_ylim(0, ch)
    ax.axis('off')

    # Pure white background
    ax.add_patch(patches.Rectangle((0, 0), cw, ch, facecolor='#ffffff'))

    # =========================================================================
    # HEADER BANNER
    # =========================================================================
    ax.text(cw / 2, ch - 45, "ESP32-S3 Microphone Preamp (LM358) — Breadboard Wiring Diagram",
            color='#0f172a', fontsize=28, fontweight='bold', ha='center', va='center')
    ax.text(cw / 2, ch - 82, "Direct Assembly Guide: Large Tie-Point Sockets, Step-by-Step Badges & Exact Hole Coordinates",
            color='#475569', fontsize=15, ha='center', va='center')

    # =========================================================================
    # BREADBOARD GEOMETRY (ZOOMED 20-COLUMN FOCUS)
    # =========================================================================
    # Left margin for assembly instruction card: 560px
    bb_x = 580
    bb_y = 260
    bb_w = 1860
    bb_h = 1050

    # Breadboard Shadow
    ax.add_patch(patches.FancyBboxPatch((bb_x + 14, bb_y - 14), bb_w, bb_h,
                                        boxstyle="round,pad=16,rounding_size=28",
                                        facecolor='#cbd5e1', edgecolor='none', alpha=0.45))
    # Breadboard Main Body (Off-white / cream plastic)
    ax.add_patch(patches.FancyBboxPatch((bb_x, bb_y), bb_w, bb_h,
                                        boxstyle="round,pad=16,rounding_size=28",
                                        facecolor='#f8fafc', edgecolor='#94a3b8', linewidth=3.0))
    
    # Inner border / bevel groove
    ax.add_patch(patches.FancyBboxPatch((bb_x + 20, bb_y + 20), bb_w - 40, bb_h - 40,
                                        boxstyle="round,pad=10,rounding_size=20",
                                        facecolor='none', edgecolor='#e2e8f0', linewidth=1.8))

    # Center Divider Trough
    trough_y = bb_y + bb_h / 2
    trough_h = 42
    ax.add_patch(patches.Rectangle((bb_x + 50, trough_y - trough_h/2), bb_w - 100, trough_h,
                                   facecolor='#e2e8f0', edgecolor='#cbd5e1', linewidth=1.5))

    # Grid parameters (20 columns, wide spacing for maximum clarity)
    num_cols = 20
    col_spacing = 84
    start_col_x = bb_x + 130

    # Power rail positions
    top_red_y  = bb_y + bb_h - 90
    top_blue_y = bb_y + bb_h - 150
    
    # Rows A-E (Upper Terminal Block)
    row_e_y = trough_y + 55
    row_d_y = trough_y + 115
    row_c_y = trough_y + 175
    row_b_y = trough_y + 235
    row_a_y = trough_y + 295

    # Rows F-J (Lower Terminal Block)
    row_f_y = trough_y - 55
    row_g_y = trough_y - 115
    row_h_y = trough_y - 175
    row_i_y = trough_y - 235
    row_j_y = trough_y - 295

    # Bottom Power Rails
    bot_red_y  = bb_y + 150
    bot_blue_y = bb_y + 90

    # Power rail colored indicator lines
    rail_x1 = start_col_x - 45
    rail_x2 = start_col_x + (num_cols - 1) * col_spacing + 45

    # Top Rails
    ax.plot([rail_x1, rail_x2], [top_red_y + 22, top_red_y + 22], color='#ef4444', linewidth=4.5)
    ax.plot([rail_x1, rail_x2], [top_blue_y - 22, top_blue_y - 22], color='#3b82f6', linewidth=4.5)
    ax.text(rail_x1 - 25, top_red_y + 22, "+ (3.3V)", color='#ef4444', fontsize=16, fontweight='bold', va='center', ha='right')
    ax.text(rail_x1 - 25, top_blue_y - 22, "− (GND)", color='#3b82f6', fontsize=16, fontweight='bold', va='center', ha='right')
    ax.text(rail_x2 + 25, top_red_y + 22, "+ (3.3V)", color='#ef4444', fontsize=16, fontweight='bold', va='center', ha='left')
    ax.text(rail_x2 + 25, top_blue_y - 22, "− (GND)", color='#3b82f6', fontsize=16, fontweight='bold', va='center', ha='left')

    # Bottom Rails
    ax.plot([rail_x1, rail_x2], [bot_red_y + 22, bot_red_y + 22], color='#ef4444', linewidth=4.5)
    ax.plot([rail_x1, rail_x2], [bot_blue_y - 22, bot_blue_y - 22], color='#3b82f6', linewidth=4.5)
    ax.text(rail_x1 - 25, bot_red_y + 22, "+ (3.3V)", color='#ef4444', fontsize=16, fontweight='bold', va='center', ha='right')
    ax.text(rail_x1 - 25, bot_blue_y - 22, "− (GND)", color='#3b82f6', fontsize=16, fontweight='bold', va='center', ha='right')
    ax.text(rail_x2 + 25, bot_red_y + 22, "+ (3.3V)", color='#ef4444', fontsize=16, fontweight='bold', va='center', ha='left')
    ax.text(rail_x2 + 25, bot_blue_y - 22, "− (GND)", color='#3b82f6', fontsize=16, fontweight='bold', va='center', ha='left')

    # Coordinate mapping
    hole_xy = {}
    rows_top = {'A': row_a_y, 'B': row_b_y, 'C': row_c_y, 'D': row_d_y, 'E': row_e_y}
    rows_bot = {'F': row_f_y, 'G': row_g_y, 'H': row_h_y, 'I': row_i_y, 'J': row_j_y}

    def draw_breadboard_socket(hx, hy):
        # Large dark socket hole
        ax.add_patch(patches.Rectangle((hx - 8.0, hy - 8.0), 16, 16,
                                       facecolor='#0f172a', edgecolor='#94a3b8', linewidth=1.0, zorder=2))
        # Silver internal spring contact
        ax.add_patch(patches.Rectangle((hx - 3.5, hy - 5.5), 7, 11,
                                       facecolor='#64748b', edgecolor='none', zorder=3))

    for col in range(1, num_cols + 1):
        cx = start_col_x + (col - 1) * col_spacing
        
        # Power rail holes
        hole_xy[f"TOP_RED_{col}"] = (cx, top_red_y)
        hole_xy[f"TOP_BLUE_{col}"] = (cx, top_blue_y)
        hole_xy[f"BOT_RED_{col}"] = (cx, bot_red_y)
        hole_xy[f"BOT_BLUE_{col}"] = (cx, bot_blue_y)
        
        draw_breadboard_socket(cx, top_red_y)
        draw_breadboard_socket(cx, top_blue_y)
        draw_breadboard_socket(cx, bot_red_y)
        draw_breadboard_socket(cx, bot_blue_y)
        
        # Terminal strip holes
        for r_name, ry in rows_top.items():
            hole_xy[f"{col}_{r_name}"] = (cx, ry)
            draw_breadboard_socket(cx, ry)
            
        for r_name, ry in rows_bot.items():
            hole_xy[f"{col}_{r_name}"] = (cx, ry)
            draw_breadboard_socket(cx, ry)
            
        # Large Column Numbers (Top & Bottom on outer margin)
        ax.text(cx, top_red_y + 40, str(col), color='#1e293b', fontsize=15, fontweight='bold', ha='center', va='center', zorder=60)
        ax.text(cx, bot_blue_y - 40, str(col), color='#1e293b', fontsize=15, fontweight='bold', ha='center', va='center', zorder=60)

    # Large Row Letters (Left & Right margins)
    for r_name, ry in rows_top.items():
        ax.text(start_col_x - 55, ry, r_name, color='#1e293b', fontsize=16, fontweight='bold', ha='center', va='center')
        ax.text(start_col_x + (num_cols - 1) * col_spacing + 55, ry, r_name, color='#1e293b', fontsize=16, fontweight='bold', ha='center', va='center')
    for r_name, ry in rows_bot.items():
        ax.text(start_col_x - 55, ry, r_name, color='#1e293b', fontsize=16, fontweight='bold', ha='center', va='center')
        ax.text(start_col_x + (num_cols - 1) * col_spacing + 55, ry, r_name, color='#1e293b', fontsize=16, fontweight='bold', ha='center', va='center')

    # =========================================================================
    # ACTIVE TIE-POINT HIGHLIGHT FUNCTION (COLOR RINGS FOR ZERO GUESSWORK)
    # =========================================================================
    def mark_active_hole(hkey, color='#38bdf8'):
        pt = hole_xy[hkey]
        ax.add_patch(patches.Circle(pt, 12, facecolor=color, edgecolor='#0f172a', linewidth=1.5, alpha=0.35, zorder=4))
        ax.add_patch(patches.Circle(pt, 5, facecolor=color, edgecolor='none', zorder=5))

    # =========================================================================
    # JUMPER WIRE DRAWING HELPER
    # =========================================================================
    def draw_wire(pt1, pt2, color='#1e293b', outline='#09090b', width=7.0, curve=0):
        x1, y1 = pt1
        x2, y2 = pt2
        
        if curve == 0:
            ax.plot([x1, x2], [y1, y2], color=outline, linewidth=width + 3.5, solid_capstyle='round', zorder=10)
            ax.plot([x1, x2], [y1, y2], color=color, linewidth=width, solid_capstyle='round', zorder=11)
            ax.plot([x1, x2], [y1, y2], color='#ffffff', linewidth=width * 0.28, alpha=0.4, solid_capstyle='round', zorder=12)
        else:
            t = np.linspace(0, 1, 40)
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2 + curve
            bx = (1 - t)**2 * x1 + 2 * (1 - t) * t * mid_x + t**2 * x2
            by = (1 - t)**2 * y1 + 2 * (1 - t) * t * mid_y + t**2 * y2
            ax.plot(bx, by, color=outline, linewidth=width + 3.5, solid_capstyle='round', zorder=10)
            ax.plot(bx, by, color=color, linewidth=width, solid_capstyle='round', zorder=11)
            ax.plot(bx, by, color='#ffffff', linewidth=width * 0.28, alpha=0.4, solid_capstyle='round', zorder=12)
            
        for pt in [pt1, pt2]:
            ax.add_patch(patches.Circle(pt, 8.0, facecolor='#1e293b', edgecolor='#0f172a', linewidth=1.8, zorder=13))
            ax.add_patch(patches.Circle(pt, 5.0, facecolor=color, edgecolor='none', zorder=14))
            ax.add_patch(patches.Circle(pt, 2.2, facecolor='#000000', zorder=15))

    def draw_orthogonal_wire(pts, color='#1e293b', outline='#09090b', width=7.5):
        for i in range(len(pts) - 1):
            x1, y1 = pts[i]
            x2, y2 = pts[i+1]
            ax.plot([x1, x2], [y1, y2], color=outline, linewidth=width + 3.5, solid_capstyle='round', zorder=10)
            ax.plot([x1, x2], [y1, y2], color=color, linewidth=width, solid_capstyle='round', zorder=11)
            ax.plot([x1, x2], [y1, y2], color='#ffffff', linewidth=width * 0.28, alpha=0.4, solid_capstyle='round', zorder=12)
        for pt in [pts[0], pts[-1]]:
            ax.add_patch(patches.Circle(pt, 8.0, facecolor='#1e293b', edgecolor='#0f172a', linewidth=1.8, zorder=13))
            ax.add_patch(patches.Circle(pt, 5.0, facecolor=color, edgecolor='none', zorder=14))
            ax.add_patch(patches.Circle(pt, 2.2, facecolor='#000000', zorder=15))

    # Helper for numbered step badges
    def draw_step_badge(x, y, step_num):
        ax.add_patch(patches.Circle((x, y), 16, facecolor='#0284c7', edgecolor='#ffffff', linewidth=2.5, zorder=55))
        ax.text(x, y, str(step_num), color='#ffffff', fontsize=12, fontweight='bold', ha='center', va='center', zorder=56)

    # =========================================================================
    # STEP 2: POWER BUS BRIDGES (COLUMN 1)
    # =========================================================================
    # Top Red to Bottom Red (+3.3V)
    draw_wire(hole_xy["TOP_RED_1"], hole_xy["BOT_RED_1"], color='#dc2626', outline='#450a0a', width=7.0)
    # Top Blue to Bottom Blue (GND)
    draw_wire(hole_xy["TOP_BLUE_1"], hole_xy["BOT_BLUE_1"], color='#2563eb', outline='#172554', width=7.0)
    mark_active_hole("TOP_RED_1", '#ef4444')
    mark_active_hole("BOT_RED_1", '#ef4444')
    mark_active_hole("TOP_BLUE_1", '#3b82f6')
    mark_active_hole("BOT_BLUE_1", '#3b82f6')

    # =========================================================================
    # STEP 1: LM358 DUAL OP-AMP IC (DIP-8) STRADDLING COLS 9 - 12
    # =========================================================================
    ic_start = 9
    ic_end = 12
    ic_x1 = hole_xy[f"{ic_start}_E"][0] - 36
    ic_x2 = hole_xy[f"{ic_end}_E"][0] + 36
    ic_w = ic_x2 - ic_x1
    ic_h = 82
    ic_y = trough_y - ic_h / 2

    # DIP-8 Plastic Package Body
    ax.add_patch(patches.FancyBboxPatch((ic_x1, ic_y), ic_w, ic_h,
                                        boxstyle="round,pad=2,rounding_size=6",
                                        facecolor='#18181b', edgecolor='#3f3f46', linewidth=2.8, zorder=20))
    # Bevel highlight inside package
    ax.add_patch(patches.Rectangle((ic_x1 + 4, ic_y + 4), ic_w - 8, ic_h - 8,
                                   facecolor='#27272a', edgecolor='none', zorder=21))

    # Orientation notch on the left
    ax.add_patch(patches.Arc((ic_x1, trough_y), 22, 28, theta1=270, theta2=90, color='#71717a', linewidth=2.8, zorder=22))
    # Pin 1 indicator dot
    ax.add_patch(patches.Circle((ic_x1 + 22, trough_y + 22), 4.5, facecolor='#52525b', edgecolor='#3f3f46', linewidth=1.2, zorder=22))

    # Laser-etched chip text
    ax.text(ic_x1 + ic_w/2, trough_y, "LM358N", color='#f4f4f5', fontsize=15, fontweight='bold', ha='center', va='center', zorder=23)

    # 8 IC Pins plugging into Rows E & F
    for col in range(ic_start, ic_end + 1):
        pt_e = hole_xy[f"{col}_E"]
        pt_f = hole_xy[f"{col}_F"]
        # Silver pin legs
        ax.plot([pt_e[0], pt_e[0]], [trough_y + 32, pt_e[1]], color='#cbd5e1', linewidth=5.5, solid_capstyle='butt', zorder=19)
        ax.plot([pt_f[0], pt_f[0]], [trough_y - 32, pt_f[1]], color='#cbd5e1', linewidth=5.5, solid_capstyle='butt', zorder=19)
        mark_active_hole(f"{col}_E", '#38bdf8')
        mark_active_hole(f"{col}_F", '#38bdf8')

    # Direct Pin Numbers Laser-Etched on the Chip Body
    top_pins = [(9, "1\nOUT"), (10, "2\nIN-"), (11, "3\nIN+"), (12, "4\nGND")]
    for col, ptxt in top_pins:
        px = hole_xy[f"{col}_E"][0]
        ax.text(px, trough_y + 24, ptxt, color='#e2e8f0', fontsize=8.0, fontweight='bold', ha='center', va='center', zorder=24)

    bot_pins = [(9, "8\nVCC"), (10, "7\nOUT2"), (11, "6\nIN2-"), (12, "5\nIN2+")]
    for col, ptxt in bot_pins:
        px = hole_xy[f"{col}_F"][0]
        ax.text(px, trough_y - 24, ptxt, color='#e2e8f0', fontsize=8.0, fontweight='bold', ha='center', va='center', zorder=24)

    draw_step_badge(ic_x1 - 25, trough_y, 1)

    # =========================================================================
    # STEP 2: LM358 POWER & GROUND CONNECTIONS
    # =========================================================================
    # Pin 4 (Col 12_E) -> Jumper from 12_D to Top Blue Rail (GND)
    draw_wire(hole_xy["12_D"], hole_xy["TOP_BLUE_12"], color='#18181b', outline='#09090b', width=6.5)
    mark_active_hole("12_D", '#18181b')
    mark_active_hole("TOP_BLUE_12", '#3b82f6')

    # Pin 8 (Col 9_F) -> Jumper from 9_G to Bottom Red Rail (+3.3V)
    draw_wire(hole_xy["9_G"], hole_xy["BOT_RED_9"], color='#dc2626', outline='#450a0a', width=6.5)
    mark_active_hole("9_G", '#dc2626')
    mark_active_hole("BOT_RED_9", '#ef4444')
    draw_step_badge(hole_xy["9_G"][0] - 30, hole_xy["9_G"][1] - 40, 2)

    # =========================================================================
    # STEP 3: UNUSED OP-AMP B TERMINATION (PINS 5, 6, 7)
    # =========================================================================
    # Pin 5 (Col 12_F) -> Jumper from 12_G to Bottom Blue Rail (GND)
    draw_wire(hole_xy["12_G"], hole_xy["BOT_BLUE_12"], color='#18181b', outline='#09090b', width=6.5)
    mark_active_hole("12_G", '#18181b')
    mark_active_hole("BOT_BLUE_12", '#3b82f6')

    # Pin 6 (Col 11_F) to Pin 7 (Col 10_F): Buffer Loop Jumper
    draw_wire(hole_xy["11_G"], hole_xy["10_G"], color='#10b981', outline='#064e3b', width=6.5, curve=-26)
    mark_active_hole("11_G", '#10b981')
    mark_active_hole("10_G", '#10b981')
    ax.text((hole_xy["11_G"][0] + hole_xy["10_G"][0])/2, hole_xy["11_G"][1] - 44, "Op-Amp B Loop\n(Pin 6 → Pin 7)",
            color='#064e3b', fontsize=8.5, fontweight='bold', ha='center', zorder=25)
    draw_step_badge(hole_xy["11_G"][0] + 48, hole_xy["11_G"][1] - 30, 3)

    # =========================================================================
    # STEP 4: ELECTRET MICROPHONE & R1 BIAS (COLUMNS 3 & 4)
    # =========================================================================
    mic_cx = (hole_xy["3_B"][0] + hole_xy["4_B"][0]) / 2
    mic_cy = (hole_xy["3_B"][1] + hole_xy["4_B"][1]) / 2

    # Metal Leads into Col 3_B (GND) and Col 4_B (+)
    ax.plot([hole_xy["3_B"][0], mic_cx - 18], [hole_xy["3_B"][1], mic_cy], color='#94a3b8', linewidth=4.5, zorder=22)
    ax.plot([hole_xy["4_B"][0], mic_cx + 18], [hole_xy["4_B"][1], mic_cy], color='#94a3b8', linewidth=4.5, zorder=22)
    mark_active_hole("3_B", '#18181b')
    mark_active_hole("4_B", '#dc2626')

    # Mic Ground Jumper from Col 3_A to Top Blue Rail (GND)
    draw_wire(hole_xy["3_A"], hole_xy["TOP_BLUE_3"], color='#18181b', outline='#09090b', width=6.5)
    mark_active_hole("3_A", '#18181b')
    mark_active_hole("TOP_BLUE_3", '#3b82f6')

    # Brushed Aluminum Mic Body
    ax.add_patch(patches.Circle((mic_cx, mic_cy), 44, facecolor='#cbd5e1', edgecolor='#64748b', linewidth=3.0, zorder=24))
    ax.add_patch(patches.Circle((mic_cx, mic_cy), 32, facecolor='#334155', edgecolor='#1e293b', linewidth=2.0, zorder=25))
    ax.add_patch(patches.Circle((mic_cx, mic_cy), 14, facecolor='#0f172a', edgecolor='#000000', linewidth=1.5, zorder=26))
    ax.text(mic_cx, mic_cy - 20, "MIC1", color='#ffffff', fontsize=9.5, fontweight='bold', ha='center', va='center', zorder=27)

    # Polarity labels clearly marked inside outer rim
    ax.text(mic_cx - 25, mic_cy, "−", color='#09090b', fontsize=18, fontweight='bold', ha='center', va='center', zorder=28)
    ax.text(mic_cx + 25, mic_cy, "+", color='#ef4444', fontsize=18, fontweight='bold', ha='center', va='center', zorder=28)

    # Capsule descriptive header badge
    ax.text(mic_cx, mic_cy + 58, "Electret Capsule\n(Case Pin = GND)", color='#0f172a', fontsize=10.5, fontweight='bold', ha='center',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#f8fafc', edgecolor='#94a3b8', linewidth=1.5), zorder=30)
    draw_step_badge(mic_cx - 45, mic_cy + 40, 4)

    # =========================================================================
    # REALISTIC RESISTOR DRAWING FUNCTION
    # =========================================================================
    def draw_realistic_resistor(hole_from, hole_to, name_text, val_text, color_bands, label_offset=(0, 26)):
        x1, y1 = hole_xy[hole_from]
        x2, y2 = hole_xy[hole_to]
        mark_active_hole(hole_from, '#f59e0b')
        mark_active_hole(hole_to, '#f59e0b')
        
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        dx, dy = x2 - x1, y2 - y1
        length = np.hypot(dx, dy)
        angle = np.degrees(np.arctan2(dy, dx))
        
        # Tinned copper leads
        ax.plot([x1, x2], [y1, y2], color='#cbd5e1', linewidth=3.6, solid_capstyle='round', zorder=28)

        # Dumbbell / Tapered Ceramic Resistor Body
        body_len = min(length * 0.65, 75)
        body_w = 22
        
        body = patches.Rectangle((-body_len/2, -body_w/2), body_len, body_w,
                                 facecolor='#fef08a', edgecolor='#ca8a04', linewidth=1.5, zorder=30)
        t = plt.matplotlib.transforms.Affine2D().rotate_deg(angle).translate(mx, my) + ax.transData
        body.set_transform(t)
        ax.add_patch(body)

        # Bulbous rims
        rim_w = 6
        rim_h = body_w + 4
        rim_l = patches.Rectangle((-body_len/2 - 1, -rim_h/2), rim_w, rim_h,
                                  facecolor='#fef08a', edgecolor='#ca8a04', linewidth=1.5, zorder=30)
        rim_r = patches.Rectangle((body_len/2 - rim_w + 1, -rim_h/2), rim_w, rim_h,
                                  facecolor='#fef08a', edgecolor='#ca8a04', linewidth=1.5, zorder=30)
        rim_l.set_transform(t)
        rim_r.set_transform(t)
        ax.add_patch(rim_l)
        ax.add_patch(rim_r)

        # 4 Standard Color Bands
        band_w = 5.0
        band_starts = np.linspace(-body_len/2 + 12, body_len/2 - 12, len(color_bands))
        for b_pos, b_col in zip(band_starts, color_bands):
            band = patches.Rectangle((b_pos - band_w/2, -rim_h/2 + 0.5), band_w, rim_h - 1,
                                     facecolor=b_col, edgecolor='none', zorder=31)
            t_band = plt.matplotlib.transforms.Affine2D().rotate_deg(angle).translate(mx, my) + ax.transData
            band.set_transform(t_band)
            ax.add_patch(band)

        # High-Contrast Component Label
        full_label = f"{name_text}: {val_text}" if "\n" in val_text else f"{name_text}: {val_text}"
        ax.text(mx + label_offset[0], my + label_offset[1], full_label,
                color='#78350f', fontsize=11.0, fontweight='bold', ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.25', facecolor='#ffffff', edgecolor='#d97706', linewidth=1.8, alpha=0.98), zorder=35)

    # R1: 10 kΩ (Mic Bias Pull-Up): Top Red Rail Col 4 -> Col 4_A
    draw_realistic_resistor("TOP_RED_4", "4_A", "R1", "10kΩ",
                            ['#78350f', '#000000', '#ea580c', '#eab308'], label_offset=(52, 0))

    # =========================================================================
    # STEP 5: DC BIAS DIVIDER (R2, R3 AT COLUMN 7) + JUMPER TO PIN 3
    # =========================================================================
    # R2: 100 kΩ (Bias Pull-Up): Top Red Rail Col 7 -> Col 7_A
    draw_realistic_resistor("TOP_RED_7", "7_A", "R2", "100kΩ",
                            ['#78350f', '#000000', '#facc15', '#eab308'], label_offset=(-58, 0))

    # R3: 100 kΩ (Bias Pull-Down): Col 7_B -> Top Blue Rail Col 7
    draw_realistic_resistor("7_B", "TOP_BLUE_7", "R3", "100kΩ",
                            ['#78350f', '#000000', '#facc15', '#eab308'], label_offset=(58, 0))

    # Purple Jumper: Col 7_D to Col 11_D (Bias 1.65V to Pin 3 IN1+)
    draw_wire(hole_xy["7_D"], hole_xy["11_D"], color='#9333ea', outline='#581c87', width=6.5, curve=28)
    mark_active_hole("7_D", '#9333ea')
    mark_active_hole("11_D", '#9333ea')
    ax.text((hole_xy["7_D"][0] + hole_xy["11_D"][0])/2, hole_xy["7_D"][1] + 28, "Bias (1.65V) to Pin 3",
            color='#581c87', fontsize=9.5, fontweight='bold', ha='center',
            bbox=dict(boxstyle='round,pad=0.25', facecolor='#faf5ff', edgecolor='#c084fc', linewidth=1.5), zorder=32)
    draw_step_badge(hole_xy["7_A"][0] - 52, hole_xy["7_A"][1] + 45, 5)

    # =========================================================================
    # STEP 6: AC COUPLING CAPACITOR C1 (1µF BOX FILM - NON-POLARIZED)
    # Col 4_C (Mic +) -> Col 7_C (Bias Node)
    # =========================================================================
    c1_x1, c1_y1 = hole_xy["4_C"]
    c1_x2, c1_y2 = hole_xy["7_C"]
    mark_active_hole("4_C", '#dc2626')
    mark_active_hole("7_C", '#9333ea')
    ax.plot([c1_x1, (c1_x1 + c1_x2)/2 - 32], [c1_y1, c1_y1], color='#cbd5e1', linewidth=3.6, zorder=28)
    ax.plot([(c1_x1 + c1_x2)/2 + 32, c1_x2], [c1_y2, c1_y2], color='#cbd5e1', linewidth=3.6, zorder=28)
    # Red WIMA Box Body
    c1_box_w, c1_box_h = 66, 36
    c1_box = patches.Rectangle(((c1_x1 + c1_x2)/2 - c1_box_w/2, c1_y1 - c1_box_h/2), c1_box_w, c1_box_h,
                               facecolor='#dc2626', edgecolor='#991b1b', linewidth=2.0, zorder=32)
    ax.add_patch(c1_box)
    ax.text((c1_x1 + c1_x2)/2, c1_y1 + 5, "C1: 1µF", color='#ffffff', fontsize=9.5, fontweight='bold', ha='center', va='center', zorder=33)
    ax.text((c1_x1 + c1_x2)/2, c1_y1 - 8, "NON-POL", color='#fef08a', fontsize=7.5, fontweight='bold', ha='center', va='center', zorder=33)
    ax.text((c1_x1 + c1_x2)/2, c1_y1 - 27, "NON-POLARIZED (Either Way)", color='#047857', fontsize=8.0, fontweight='bold', ha='center', va='top',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='#ecfdf5', edgecolor='#10b981', linewidth=1.2), zorder=33)
    draw_step_badge((c1_x1 + c1_x2)/2, c1_y1 + 32, 6)

    # =========================================================================
    # STEP 7: NEGATIVE FEEDBACK RESISTOR R4 (100kΩ)
    # Between Pin 1 (Col 9_C) and Pin 2 (Col 10_C)
    # =========================================================================
    draw_realistic_resistor("9_C", "10_C", "R4", "100kΩ\n(Feedback)",
                            ['#78350f', '#000000', '#facc15', '#eab308'], label_offset=(0, 30))
    draw_step_badge(hole_xy["10_C"][0] + 36, hole_xy["10_C"][1], 7)

    # =========================================================================
    # STEP 8: AC GAIN NETWORK: R5 (1kΩ) & C3 (10µF POLARIZED)
    # R5: Pin 2 (Col 10_B) -> Col 15_B
    # C3: Col 15_A -> Top Blue Rail (GND)
    # =========================================================================
    draw_realistic_resistor("10_B", "15_B", "R5", "1kΩ (Gain)",
                            ['#78350f', '#000000', '#dc2626', '#eab308'], label_offset=(0, 28))

    # C3 Electrolytic Radial Can (POLARIZED)
    c3_pos = hole_xy["15_A"]
    c3_neg = hole_xy["TOP_BLUE_15"]
    mark_active_hole("15_A", '#2563eb')
    mark_active_hole("TOP_BLUE_15", '#3b82f6')
    c3_mid_y = (c3_pos[1] + c3_neg[1]) / 2
    ax.plot([c3_pos[0], c3_pos[0]], [c3_pos[1], c3_mid_y - 18], color='#cbd5e1', linewidth=3.6, zorder=28)
    ax.plot([c3_neg[0], c3_neg[0]], [c3_mid_y + 18, c3_neg[1]], color='#cbd5e1', linewidth=3.6, zorder=28)
    
    # Blue Aluminum Can Body
    c3_can = patches.Circle((c3_pos[0] + 24, c3_mid_y), 24, facecolor='#1d4ed8', edgecolor='#93c5fd', linewidth=2.5, zorder=34)
    ax.add_patch(c3_can)
    # Negative White Stripe
    c3_stripe = patches.Rectangle((c3_pos[0] + 24 + 9, c3_mid_y - 24), 13, 48, facecolor='#f1f5f9', edgecolor='none', zorder=35)
    ax.add_patch(c3_stripe)
    for m_off in [-14, 0, 14]:
        ax.text(c3_pos[0] + 24 + 15.5, c3_mid_y + m_off, "−", color='#1e3a8a', fontsize=13, fontweight='bold', ha='center', va='center', zorder=37)
    
    ax.text(c3_pos[0] + 24 - 4, c3_mid_y + 5, "C3\n10µF", color='#ffffff', fontsize=9.5, fontweight='bold', ha='center', va='center', zorder=36)
    ax.text(c3_pos[0] + 24 - 4, c3_mid_y - 13, "POLAR", color='#93c5fd', fontsize=6.5, fontweight='bold', ha='center', va='center', zorder=36)

    # High-contrast Polarity Callouts at Sockets
    ax.text(c3_pos[0] + 55, c3_pos[1] - 8, "(+) POS (Long Leg)", color='#b91c1c', fontsize=8.5, fontweight='bold', ha='left', va='center',
            bbox=dict(boxstyle='round,pad=0.25', facecolor='#fef2f2', edgecolor='#ef4444', linewidth=1.4), zorder=45)
    ax.text(c3_neg[0] + 32, c3_neg[1], "(−) NEG (Stripe)", color='#1d4ed8', fontsize=8.5, fontweight='bold', ha='left', va='center',
            bbox=dict(boxstyle='round,pad=0.25', facecolor='#eff6ff', edgecolor='#3b82f6', linewidth=1.4), zorder=45)

    draw_step_badge(hole_xy["15_B"][0] + 35, hole_xy["15_B"][1] - 30, 8)

    # =========================================================================
    # STEP 9: OUTPUT LOW-PASS FILTER: R6 (1kΩ) & C4 (10nF NON-POLARIZED)
    # R6: Pin 1 (Col 9_A) -> Col 18_A
    # C4: Col 18_B -> Top Blue Rail Col 18
    # =========================================================================
    draw_realistic_resistor("9_A", "18_A", "R6", "1kΩ (Filter)",
                            ['#78350f', '#000000', '#dc2626', '#eab308'], label_offset=(0, 28))

    # C4 Ceramic Disc (NON-POLARIZED)
    c4_sig = hole_xy["18_B"]
    c4_gnd = hole_xy["TOP_BLUE_18"]
    mark_active_hole("18_B", '#ea580c')
    mark_active_hole("TOP_BLUE_18", '#3b82f6')
    c4_mid_y = (c4_sig[1] + c4_gnd[1]) / 2
    ax.plot([c4_sig[0], c4_sig[0]], [c4_sig[1], c4_mid_y - 18], color='#cbd5e1', linewidth=3.6, zorder=28)
    ax.plot([c4_gnd[0], c4_gnd[0]], [c4_mid_y + 18, c4_gnd[1]], color='#cbd5e1', linewidth=3.6, zorder=28)
    c4_disc = patches.Circle((c4_sig[0] + 24, c4_mid_y), 25, facecolor='#ea580c', edgecolor='#fed7aa', linewidth=2.0, zorder=34)
    ax.add_patch(c4_disc)
    ax.text(c4_sig[0] + 24, c4_mid_y, "10nF\n(103)", color='#ffffff', fontsize=9.0, fontweight='bold', ha='center', va='center', zorder=35)
    
    # Non-polarized callout
    ax.text(c4_sig[0] + 55, c4_mid_y + 20, "NON-POLARIZED\n(Either Leg)", color='#047857', fontsize=7.5, fontweight='bold', ha='left', va='center',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='#ecfdf5', edgecolor='#10b981', linewidth=1.2), zorder=40)
    draw_step_badge(hole_xy["18_B"][0] + 62, hole_xy["18_B"][1] - 30, 9)

    # =========================================================================
    # STEP 10: POWER DECOUPLING CAPACITORS (C5 NON-POL & C2 POLARIZED)
    # C5 (100nF): From Pin 8 (Col 9_H) to Bottom Blue Rail Col 8
    # C2 (10µF Bulk): Across Top Rails at Col 20
    # =========================================================================
    c5_vcc = hole_xy["9_H"]
    c5_gnd = hole_xy["BOT_BLUE_8"]
    mark_active_hole("9_H", '#dc2626')
    mark_active_hole("BOT_BLUE_8", '#3b82f6')
    c5_mx = (c5_vcc[0] + c5_gnd[0]) / 2
    c5_my = (c5_vcc[1] + c5_gnd[1]) / 2
    ax.plot([c5_vcc[0], c5_mx + 8], [c5_vcc[1], c5_my + 16], color='#cbd5e1', linewidth=3.6, zorder=28)
    ax.plot([c5_gnd[0], c5_mx - 8], [c5_gnd[1], c5_my - 16], color='#cbd5e1', linewidth=3.6, zorder=28)
    c5_disc = patches.Circle((c5_mx, c5_my), 25, facecolor='#ea580c', edgecolor='#fed7aa', linewidth=2.0, zorder=34)
    ax.add_patch(c5_disc)
    ax.text(c5_mx, c5_my, "100nF\n(104)", color='#ffffff', fontsize=8.5, fontweight='bold', ha='center', va='center', zorder=35)
    
    # Non-polarized callout for C5 (placed neatly in empty Col 7.5 Row I)
    ax.text(c5_mx - 48, c5_my + 16, "NON-POLARIZED\n(Either Leg)", color='#047857', fontsize=7.2, fontweight='bold', ha='center', va='center',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='#ecfdf5', edgecolor='#10b981', linewidth=1.2), zorder=40)

    # C2 Bulk Can (POLARIZED)
    c2_x = hole_xy["TOP_RED_20"][0]
    c2_y = (top_red_y + top_blue_y) / 2
    mark_active_hole("TOP_RED_20", '#ef4444')
    mark_active_hole("TOP_BLUE_20", '#3b82f6')
    c2_can = patches.Circle((c2_x, c2_y), 24, facecolor='#1d4ed8', edgecolor='#93c5fd', linewidth=2.5, zorder=34)
    ax.add_patch(c2_can)
    c2_stripe = patches.Rectangle((c2_x + 9, c2_y - 24), 13, 48, facecolor='#f1f5f9', edgecolor='none', zorder=35)
    ax.add_patch(c2_stripe)
    for m_off in [-14, 0, 14]:
        ax.text(c2_x + 15.5, c2_y + m_off, "−", color='#1e3a8a', fontsize=13, fontweight='bold', ha='center', va='center', zorder=37)
        
    ax.text(c2_x - 4, c2_y + 5, "C2\n10µF", color='#ffffff', fontsize=9.5, fontweight='bold', ha='center', va='center', zorder=36)
    ax.text(c2_x - 4, c2_y - 13, "POLAR", color='#93c5fd', fontsize=6.5, fontweight='bold', ha='center', va='center', zorder=36)

    # C2 Polarity Callouts at Sockets (placed to the left in empty Col 19.5)
    ax.text(c2_x - 38, top_red_y, "(+) POS (Long Leg)", color='#b91c1c', fontsize=8.2, fontweight='bold', ha='right', va='center',
            bbox=dict(boxstyle='round,pad=0.25', facecolor='#fef2f2', edgecolor='#ef4444', linewidth=1.4), zorder=45)
    ax.text(c2_x - 38, top_blue_y, "(−) NEG (Stripe)", color='#1d4ed8', fontsize=8.2, fontweight='bold', ha='right', va='center',
            bbox=dict(boxstyle='round,pad=0.25', facecolor='#eff6ff', edgecolor='#3b82f6', linewidth=1.4), zorder=45)

    draw_step_badge(c5_mx + 50, c5_my, 10)

    # =========================================================================
    # DEDICATED CAPACITOR POLARITY QUICK-REFERENCE BOX (COLS 13-17, ROWS G-J)
    # =========================================================================
    pol_box_x = hole_xy["13_G"][0] - 25
    pol_box_y = row_j_y - 28
    pol_box_w = 460
    pol_box_h = 240

    # Polarity Card Container with drop shadow
    ax.add_patch(patches.FancyBboxPatch((pol_box_x + 5, pol_box_y - 5), pol_box_w, pol_box_h,
                                        boxstyle="round,pad=6,rounding_size=12",
                                        facecolor='#cbd5e1', edgecolor='none', alpha=0.5, zorder=30))
    ax.add_patch(patches.FancyBboxPatch((pol_box_x, pol_box_y), pol_box_w, pol_box_h,
                                        boxstyle="round,pad=6,rounding_size=12",
                                        facecolor='#ffffff', edgecolor='#0284c7', linewidth=2.4, zorder=31))
    
    # Header bar
    ax.add_patch(patches.FancyBboxPatch((pol_box_x + 4, pol_box_y + pol_box_h - 38), pol_box_w - 8, 34,
                                        boxstyle="round,pad=4,rounding_size=8",
                                        facecolor='#0369a1', edgecolor='none', zorder=32))
    ax.text(pol_box_x + pol_box_w/2, pol_box_y + pol_box_h - 21, "⚡ CAPACITOR POLARITY GUIDE",
            color='#ffffff', fontsize=12.5, fontweight='bold', ha='center', va='center', zorder=33)

    # Section 1: Polarized Electrolytic Capacitors
    ax.text(pol_box_x + 14, pol_box_y + pol_box_h - 56, "1. ELECTROLYTIC CAPS (C2, C3 = 10µF) → POLARIZED!",
            color='#0f172a', fontsize=10.0, fontweight='bold', ha='left', va='center', zorder=33)
    ax.text(pol_box_x + 24, pol_box_y + pol_box_h - 78, "• (+) POSITIVE: Longer leg → Red Rail (+3.3V) / Col 15-A",
            color='#b91c1c', fontsize=9.2, fontweight='bold', ha='left', va='center', zorder=33)
    ax.text(pol_box_x + 24, pol_box_y + pol_box_h - 98, "• (−) NEGATIVE: Shorter leg / White Stripe '−' → Blue Rail (GND)",
            color='#1d4ed8', fontsize=9.2, fontweight='bold', ha='left', va='center', zorder=33)

    # Divider line
    ax.plot([pol_box_x + 10, pol_box_x + pol_box_w - 10], [pol_box_y + pol_box_h - 114, pol_box_y + pol_box_h - 114],
            color='#e2e8f0', linewidth=1.5, zorder=33)

    # Section 2: Non-Polarized Ceramic & Film Capacitors
    ax.text(pol_box_x + 14, pol_box_y + pol_box_h - 132, "2. FILM & CERAMIC CAPS (C1, C4, C5) → NON-POLARIZED!",
            color='#0f172a', fontsize=10.0, fontweight='bold', ha='left', va='center', zorder=33)
    ax.text(pol_box_x + 24, pol_box_y + pol_box_h - 154, "• C1 (1µF Box Film), C4 (10nF '103'), C5 (100nF '104')",
            color='#047857', fontsize=9.0, fontweight='bold', ha='left', va='center', zorder=33)
    ax.text(pol_box_x + 24, pol_box_y + pol_box_h - 174, "• NO positive or negative! Connect in either direction.",
            color='#047857', fontsize=9.0, fontweight='bold', ha='left', va='center', zorder=33)
    ax.text(pol_box_x + 24, pol_box_y + pol_box_h - 196, "• Both leads are completely interchangeable.",
            color='#64748b', fontsize=8.5, ha='left', va='center', zorder=33)

    # =========================================================================
    # STEP 11: OUTGOING WIRES TO ESP32-S3 (EXACT 90° ORTHOGONAL)
    # =========================================================================
    wire_bottom_y = 100

    # 1. RED WIRE: +3.3V POWER FROM ESP32
    # Plugs into Bottom Red Rail Col 5
    p_3v3 = hole_xy["BOT_RED_5"]
    mark_active_hole("BOT_RED_5", '#ef4444')
    pts_3v3 = [
        p_3v3,
        (p_3v3[0], wire_bottom_y)
    ]
    draw_orthogonal_wire(pts_3v3, color='#dc2626', outline='#450a0a', width=8.5)

    # 2. BLACK WIRE: GND FROM ESP32
    # Plugs into Bottom Blue Rail Col 11
    p_gnd = hole_xy["BOT_BLUE_11"]
    mark_active_hole("BOT_BLUE_11", '#3b82f6')
    pts_gnd = [
        p_gnd,
        (p_gnd[0], wire_bottom_y)
    ]
    draw_orthogonal_wire(pts_gnd, color='#18181b', outline='#09090b', width=8.5)

    # 3. YELLOW WIRE: AUDIO OUT TO ESP32 GPIO 1 (ADC1_CH0)
    # Plugs into Col 18_C (After R6 & C4 filter)
    p_sig = hole_xy["18_C"]
    mark_active_hole("18_C", '#facc15')
    sig_drop_x = hole_xy["BOT_BLUE_19"][0]
    pts_sig = [
        p_sig,
        (sig_drop_x, p_sig[1]),
        (sig_drop_x, wire_bottom_y)
    ]
    draw_orthogonal_wire(pts_sig, color='#facc15', outline='#854d0e', width=8.5)

    # Huge Prominent Terminal Badges at the bottom
    ax.text(p_3v3[0], wire_bottom_y - 38, "+3.3V (From ESP32 3V3 Pin)",
            color='#dc2626', fontsize=17, fontweight='bold', ha='center', va='center',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#ffffff', edgecolor='#dc2626', linewidth=2.8), zorder=50)

    ax.text(p_gnd[0], wire_bottom_y - 38, "GND (From ESP32 GND Pin)",
            color='#18181b', fontsize=17, fontweight='bold', ha='center', va='center',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#ffffff', edgecolor='#18181b', linewidth=2.8), zorder=50)

    ax.text(sig_drop_x, wire_bottom_y - 38, "TO ESP32 GPIO 1 (ADC1_CH0)",
            color='#ca8a04', fontsize=17, fontweight='bold', ha='center', va='center',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#ffffff', edgecolor='#ca8a04', linewidth=2.8), zorder=50)

    draw_step_badge(p_3v3[0] - 32, p_3v3[1] - 35, 11)

    # =========================================================================
    # LEFT-HAND SIDE: 5-MINUTE DIRECT ASSEMBLY GUIDE
    # =========================================================================
    card_x = 40
    card_y = 60
    card_w = 515
    card_h = 1260

    # Panel container with drop shadow
    ax.add_patch(patches.FancyBboxPatch((card_x + 8, card_y - 8), card_w, card_h,
                                        boxstyle="round,pad=12,rounding_size=18",
                                        facecolor='#cbd5e1', edgecolor='none', alpha=0.4))
    ax.add_patch(patches.FancyBboxPatch((card_x, card_y), card_w, card_h,
                                        boxstyle="round,pad=12,rounding_size=18",
                                        facecolor='#f8fafc', edgecolor='#94a3b8', linewidth=2.5))
    
    # Header badge
    ax.add_patch(patches.FancyBboxPatch((card_x + 12, card_y + card_h - 68), card_w - 24, 52,
                                        boxstyle="round,pad=6,rounding_size=10",
                                        facecolor='#0f172a', edgecolor='none'))
    ax.text(card_x + card_w/2, card_y + card_h - 42, "QUICK BUILD GUIDE (STEPS 1-11)",
            color='#ffffff', fontsize=17, fontweight='bold', ha='center', va='center')

    assembly_steps = [
        (1, "Place LM358 IC", "Straddle center trough: Pins 1-4 in Cols 9-12 (Row E),\nPins 8-5 in Cols 9-12 (Row F). Notch faces LEFT.", '#0284c7'),
        (2, "Wire Power Rails", "Col 1: Red wire connects Top+ to Bot+.\nCol 1: Blue wire connects Top- to Bot-.\nPin 8 (9-G) -> Bot Red (+3.3V). Pin 4 (12-D) -> Top Blue (GND).", '#dc2626'),
        (3, "Terminate Op-Amp B", "Pin 5 (12-G) -> Bot Blue (GND).\nGreen wire: Pin 6 (11-G) -> Pin 7 (10-G) buffer loop.", '#059669'),
        (4, "Insert Mic Capsule", "Case (-) pin in Col 3-B, Sig (+) pin in Col 4-B.\nJumper: 3-A -> Top Blue (GND).\nR1 (10kΩ): Top Red (Col 4) -> Col 4-A.", '#d97706'),
        (5, "Bias Divider (1.65V)", "R2 (100kΩ): Top Red (Col 7) -> Col 7-A.\nR3 (100kΩ): Col 7-B -> Top Blue (Col 7).\nPurple Jumper: Col 7-D -> Col 11-D (Pin 3 IN+).", '#9333ea'),
        (6, "AC Coupling Cap C1", "C1 (1µF Box Film): Col 4-C to Col 7-C.\n★ NON-POLARIZED: Connect in either direction (no +/-).", '#dc2626'),
        (7, "Feedback Resistor R4", "R4 (100kΩ): Connect between Pin 1 (9-C) and Pin 2 (10-C).", '#d97706'),
        (8, "Gain Stage (R5 & C3)", "R5 (1kΩ): Connect from Pin 2 (10-B) to Col 15-B.\nC3 (10µF Electrolytic): POLARIZED!\n★ (+) LONG LEG -> Col 15-A\n★ (−) STRIPE / SHORT LEG -> Top Blue Rail (GND).", '#2563eb'),
        (9, "RC Filter (R6 & C4)", "R6 (1kΩ): Connect from Pin 1 (9-A) to Col 18-A.\nC4 (10nF disc '103'): Col 18-B to Top Blue Rail.\n★ NON-POLARIZED: Connect in either direction.", '#ea580c'),
        (10, "Bypass Capacitors", "C5 (100nF disc '104'): Col 9-H (+3.3V) -> Bot Blue (Col 8).\n★ NON-POLARIZED: Connect either way.\nC2 (10µF Electrolytic): POLARIZED!\n★ (+) LONG LEG -> Top Red (+3.3V)\n★ (−) STRIPE / SHORT LEG -> Top Blue (GND).", '#2563eb'),
        (11, "Connect to ESP32-S3", "RED Wire: Bot Red Rail -> ESP32 3V3 Pin.\nBLACK Wire: Bot Blue Rail -> ESP32 GND Pin.\nYELLOW Wire: Col 18-C -> ESP32 GPIO 1.", '#ca8a04')
    ]

    cur_ty = card_y + card_h - 96
    for snum, stitle, sdesc, scolor in assembly_steps:
        # Step number badge
        ax.add_patch(patches.Circle((card_x + 26, cur_ty), 13, facecolor=scolor, edgecolor='#ffffff', linewidth=1.5, zorder=60))
        ax.text(card_x + 26, cur_ty, str(snum), color='#ffffff', fontsize=10.0, fontweight='bold', ha='center', va='center', zorder=61)
        # Title
        ax.text(card_x + 48, cur_ty, stitle, color=scolor, fontsize=11.0, fontweight='bold', va='center')
        cur_ty -= 18
        # Description
        for line in sdesc.split('\n'):
            line_color = '#b91c1c' if '(+)' in line else ('#1d4ed8' if '(−)' in line else ('#047857' if 'NON-POLARIZED' in line else '#334155'))
            line_weight = 'bold' if ('(+)' in line or '(−)' in line or 'NON-POLARIZED' in line) else 'normal'
            ax.text(card_x + 48, cur_ty, line, color=line_color, fontsize=8.6, fontweight=line_weight, va='center')
            cur_ty -= 16
        cur_ty -= 6
        # Subtle divider
        ax.plot([card_x + 14, card_x + card_w - 14], [cur_ty + 4, cur_ty + 4], color='#e2e8f0', linewidth=1.0)
    # Save finalized diagram
    plt.savefig(OUTPUT_IMAGE, bbox_inches='tight', pad_inches=0.15, facecolor='#ffffff')
    plt.close()
    print(f"V5 direct-assembly breadboard diagram saved to: {OUTPUT_IMAGE}")

if __name__ == "__main__":
    generate_mic_breadboard()
