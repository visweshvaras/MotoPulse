#!/usr/bin/env python3
"""
MotoPulse™ Complete Project Documentation Generator (.docx)
Builds an exhaustive, highly-structured, and professionally styled Microsoft Word document
encompassing all hardware, electronics, PCB design, TinyML deep learning models,
firmware architecture, web cockpit software, and mathematical formulations.
"""

import os
import sys
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

def set_cell_shading(cell, color_hex):
    """Set background color of a table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    for child in tcPr:
        if child.tag.endswith('shd'):
            tcPr.remove(child)
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    tcPr.append(shading)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Set inner cell margins (in dxa: 20 dxa = 1 pt)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'''
        <w:tcMar {nsdecls("w")}>
            <w:top w:w="{top}" w:type="dxa"/>
            <w:bottom w:w="{bottom}" w:type="dxa"/>
            <w:left w:w="{left}" w:type="dxa"/>
            <w:right w:w="{right}" w:type="dxa"/>
        </w:tcMar>
    ''')
    tcPr.append(tcMar)

def set_table_borders(table, color="D3D3D3"):
    """Apply clean light borders to a table."""
    tblPr = table._tbl.tblPr
    borders = parse_xml(f'''
        <w:tblBorders {nsdecls("w")}>
            <w:top w:val="single" w:sz="4" w:space="0" w:color="{color}"/>
            <w:bottom w:val="single" w:sz="6" w:space="0" w:color="{color}"/>
            <w:left w:val="none"/>
            <w:right w:val="none"/>
            <w:insideH w:val="single" w:sz="4" w:space="0" w:color="{color}"/>
            <w:insideV w:val="none"/>
        </w:tblBorders>
    ''')
    tblPr.append(borders)

def add_heading_styled(doc, text, level):
    """Add a heading with professional color and spacing."""
    p = doc.add_heading(text, level=level)
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_before = Pt(14 if level == 1 else (10 if level == 2 else 6))
    p.paragraph_format.space_after = Pt(4)
    for run in p.runs:
        if level == 1:
            run.font.color.rgb = RGBColor(0x00, 0x33, 0x66) # Deep Navy
            run.font.name = 'Arial'
            run.font.size = Pt(18)
            run.font.bold = True
        elif level == 2:
            run.font.color.rgb = RGBColor(0x2A, 0x5D, 0x8F) # Steel Blue
            run.font.name = 'Arial'
            run.font.size = Pt(14)
            run.font.bold = True
        elif level == 3:
            run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
            run.font.name = 'Arial'
            run.font.size = Pt(12)
            run.font.bold = True
    return p

def add_callout(doc, title, text, alert_type="note"):
    """Create a styled callout box with a colored left border."""
    border_color = "003366" if alert_type == "note" else ("2E7D32" if alert_type == "success" else "C0392B")
    bg_color = "F0F4F8" if alert_type == "note" else ("F1F8E9" if alert_type == "success" else "FDF2E9")
    
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    
    cell = tbl.cell(0, 0)
    cell.width = Inches(6.5)
    set_cell_shading(cell, bg_color)
    set_cell_margins(cell, top=140, bottom=140, left=200, right=200)
    
    # Left border only
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(f'''
        <w:tcBorders {nsdecls("w")}>
            <w:left w:val="single" w:sz="36" w:space="0" w:color="{border_color}"/>
            <w:top w:val="none"/>
            <w:right w:val="none"/>
            <w:bottom w:val="none"/>
        </w:tcBorders>
    ''')
    tcPr.append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    r_title = p.add_run(f"📌 {title}: ")
    r_title.bold = True
    r_title.font.name = 'Arial'
    r_title.font.size = Pt(10)
    r_title.font.color.rgb = RGBColor(0x00, 0x33, 0x66) if alert_type == "note" else (RGBColor(0x2E, 0x7D, 0x32) if alert_type == "success" else RGBColor(0xC0, 0x39, 0x2B))
    
    r_text = p.add_run(text)
    r_text.font.name = 'Arial'
    r_text.font.size = Pt(9.5)
    
    # Add spacing after table
    p_spacer = doc.add_paragraph()
    p_spacer.paragraph_format.space_before = Pt(0)
    p_spacer.paragraph_format.space_after = Pt(4)

def add_code_block(doc, code_str, language="python"):
    """Render a clean monospaced code block with shaded background."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    
    cell = tbl.cell(0, 0)
    cell.width = Inches(6.5)
    set_cell_shading(cell, "F8F9FA")
    set_cell_margins(cell, top=100, bottom=100, left=150, right=150)
    
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(f'''
        <w:tcBorders {nsdecls("w")}>
            <w:left w:val="single" w:sz="12" w:space="0" w:color="CBD5E1"/>
            <w:top w:val="single" w:sz="6" w:space="0" w:color="E2E8F0"/>
            <w:right w:val="single" w:sz="6" w:space="0" w:color="E2E8F0"/>
            <w:bottom w:val="single" w:sz="6" w:space="0" w:color="E2E8F0"/>
        </w:tcBorders>
    ''')
    tcPr.append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = Pt(11)
    
    r = p.add_run(code_str.strip())
    r.font.name = 'Courier New'
    r.font.size = Pt(8.5)
    r.font.color.rgb = RGBColor(0x22, 0x22, 0x22)
    
    p_spacer = doc.add_paragraph()
    p_spacer.paragraph_format.space_before = Pt(0)
    p_spacer.paragraph_format.space_after = Pt(4)

def style_table(table, col_widths, col_alignments=None):
    """Apply styling, header colors, alternating row shading, and borders to a table."""
    set_table_borders(table)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    
    # Header Row
    for idx, cell in enumerate(table.rows[0].cells):
        set_cell_shading(cell, "003366") # Navy Blue
        set_cell_margins(cell, top=120, bottom=120, left=140, right=140)
        cell.width = Inches(col_widths[idx])
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if (col_alignments and col_alignments[idx] == 'C') else WD_ALIGN_PARAGRAPH.LEFT
        for run in p.runs:
            run.font.bold = True
            run.font.name = 'Arial'
            run.font.size = Pt(9.5)
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            
    # Body Rows
    for row_idx, row in enumerate(table.rows[1:], start=1):
        bg = "F8FAFC" if row_idx % 2 == 1 else "FFFFFF"
        for col_idx, cell in enumerate(row.cells):
            set_cell_shading(cell, bg)
            set_cell_margins(cell, top=80, bottom=80, left=120, right=120)
            cell.width = Inches(col_widths[col_idx])
            p = cell.paragraphs[0]
            if col_alignments:
                align = col_alignments[col_idx]
                if align == 'C': p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                elif align == 'R': p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                else: p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for run in p.runs:
                run.font.name = 'Arial'
                run.font.size = Pt(9)
                run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

def add_image_safe(doc, img_path, width_inches=5.8, caption=None):
    """Embed an image with a centered caption if file exists."""
    if os.path.exists(img_path):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run()
        run.add_picture(img_path, width=Inches(width_inches))
        
        if caption:
            p_cap = doc.add_paragraph()
            p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_cap.paragraph_format.space_before = Pt(0)
            p_cap.paragraph_format.space_after = Pt(8)
            r_cap = p_cap.add_run(f"Figure: {caption}")
            r_cap.font.name = 'Arial'
            r_cap.font.size = Pt(8.5)
            r_cap.font.italic = True
            r_cap.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
    else:
        print(f"[WARN] Image not found: {img_path}")

def generate_documentation():
    print("[1/5] Initializing Word Document...")
    doc = Document()
    
    # Set Standard 1-inch margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)
        
        # Header & Footer
        header = section.header
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hr = hp.add_run("MotoPulse™ Edge AI Automotive Predictive Maintenance System")
        hr.font.name = 'Arial'
        hr.font.size = Pt(8)
        hr.font.color.rgb = RGBColor(0x88, 0x88, 0x88)
        
        footer = section.footer
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.LEFT
        fr = fp.add_run("Confidential & Proprietary • Team MotoPulse (Hacktivate 2026)")
        fr.font.name = 'Arial'
        fr.font.size = Pt(8)
        fr.font.color.rgb = RGBColor(0x88, 0x88, 0x88)

    # ==========================================
    # COVER / TITLE BLOCK
    # ==========================================
    print("[2/5] Building Title & Executive Summary...")
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(24)
    p_title.paragraph_format.space_after = Pt(4)
    r_title = p_title.add_run("MOTOPULSE™")
    r_title.bold = True
    r_title.font.name = 'Arial'
    r_title.font.size = Pt(28)
    r_title.font.color.rgb = RGBColor(0x00, 0x33, 0x66)
    
    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(12)
    r_sub = p_sub.add_run("Automotive Acoustic Predictive Maintenance & Edge AI Prognostics Horizon")
    r_sub.font.name = 'Arial'
    r_sub.font.size = Pt(14)
    r_sub.font.color.rgb = RGBColor(0x46, 0x82, 0xB4)
    r_sub.italic = True
    
    p_meta = doc.add_paragraph()
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_meta.paragraph_format.space_before = Pt(0)
    p_meta.paragraph_format.space_after = Pt(24)
    r_meta = p_meta.add_run("Complete End-to-End System Specifications: Hardware, KiCad PCB, TinyML Models, Firmware, and Web Cockpit\n"
                           "Lead Developers: Visweshwara S & Ishan Kumar (@ishannvn) | IEEE RUAS - Hacktivate 2026 | October 2026")
    r_meta.font.name = 'Arial'
    r_meta.font.size = Pt(9.5)
    r_meta.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    
    # Title Rule
    p_rule = doc.add_paragraph()
    p_rule.paragraph_format.space_after = Pt(18)
    r_rule = p_rule.add_run("―" * 58)
    r_rule.font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)
    p_rule.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # ==========================================
    # SECTION 1: EXECUTIVE SUMMARY
    # ==========================================
    add_heading_styled(doc, "1. Executive Summary & Problem Statement", level=1)
    
    doc.add_paragraph(
        "Modern automotive vehicles and industrial reciprocating machinery experience continuous mechanical wear and dynamic thermal stress. "
        "Standard On-Board Diagnostics (OBD-II) systems rely on Diagnostic Trouble Codes (DTCs), which are fundamentally reactive—triggering "
        "only after catastrophic sensor thresholds (such as oxygen sensor deviations, severe misfire counters, or throttle body lockups) "
        "have already been breached. Internal mechanical friction anomalies—such as alternator bearing micro-spalling, connecting rod wrist-pin knock, "
        "hydraulic lifter ticking, or exhaust manifold blowby—exhibit prominent high-frequency acoustic and structural vibration signatures "
        "hundreds of operating hours before DTC illumination."
    )
    doc.add_paragraph(
        "MotoPulse™ is an edge-first, non-invasive, cyber-physical diagnostic system powered by the ESP32-S3 microcontroller, dual INMP441 "
        "I2S MEMS digital microphones, a high-sensitivity piezoelectric mechanical vibration sensor, an on-device I2C display, and a full-stack "
        "real-time web telemetry cockpit. By combining a 50cm acoustic spatial inverse-square-law perimeter gate, an on-device 13.58 KB INT8-quantized "
        "TinyML Deep Convolutional Neural Network (99.40% accuracy), and an autonomous continual self-learning engine, MotoPulse detects and grades "
        "mechanical degradation stages before road failure occurs."
    )
    
    add_callout(
        doc,
        "Zero-Storage Ephemeral Privacy Policy",
        "MotoPulse operates strictly on real-time rolling memory buffers. Acoustic and vibration signals are processed in-memory via 1.0-second sliding windows for TinyML feature extraction. Zero audio or vibration recordings are persisted to disk, fully complying with industrial acoustic surveillance and privacy regulations.",
        alert_type="note"
    )

    # ==========================================
    # SECTION 2: SYSTEM ARCHITECTURE
    # ==========================================
    add_heading_styled(doc, "2. End-to-End System Architecture", level=1)
    
    doc.add_paragraph(
        "The MotoPulse system architecture bridges high-speed hardware signal acquisition, on-device real-time digital filtering, edge inference, "
        "and asynchronous web telemetry streaming:"
    )
    
    arch_table = doc.add_table(rows=6, cols=3)
    arch_data = [
        ("Subsystem", "Component / Technology", "Functional Responsibility"),
        ("Acoustic Sensor Array", "Dual INMP441 MEMS (40mm Baseline)", "Captures 16 kHz 16-bit stereo PCM audio; spatial TDOA & sound pressure level gradient gating."),
        ("Structural Vibration", "27mm Ceramic Piezo (GPIO 1 ADC1)", "Monitors direct engine block / chassis mechanical shocks, knock events, and detonation pulses."),
        ("Edge Compute Module", "ESP32-S3-DevKitC-1-N16R8 (240 MHz)", "Dual-core Xtensa LX7 running MicroPython DMA audio acquisition, I2C display driver, and USB-CDC telemetry."),
        ("Visual Feedback", "16x2 I2C LCD (0x27) / 0.96\" OLED", "On-device display rendering vehicle operating regime, peak acoustic amplitude, and real-time health state."),
        ("Telemetry Cockpit", "Python Server + WebSocket (Port 8765)", "Broadcasts 36-40 FPS live hardware packets to HTML5 Canvas visualizers with dynamic RUL prognostics.")
    ]
    for r_idx, row in enumerate(arch_table.rows):
        for c_idx, val in enumerate(arch_data[r_idx]):
            row.cells[c_idx].paragraphs[0].text = val
    style_table(arch_table, [1.5, 2.2, 2.8], ['L', 'L', 'L'])

    # ==========================================
    # SECTION 3: HARDWARE SPECIFICATIONS
    # ==========================================
    print("[3/5] Building Hardware, Schematics & PCB Sections...")
    add_heading_styled(doc, "3. Hardware Architecture & Electronics Specifications", level=1)
    
    doc.add_paragraph(
        "The hardware platform is built entirely around industrial-grade, cost-effective off-the-shelf components mounted to a custom carrier PCB:"
    )
    
    add_heading_styled(doc, "3.1 Compute Module: ESP32-S3-DevKitC-1-N16R8", level=2)
    doc.add_paragraph(
        "The system utilizes the ESP32-S3-WROOM-1 module featuring:\n"
        "• Dual-Core Xtensa® 32-bit LX7 CPU running at 240 MHz with dedicated vector instructions (ESP-NN SIMD).\n"
        "• Memory Configuration: 512 KB internal SRAM, 16 MB external Quad-SPI Flash, and 8 MB Octal PSRAM.\n"
        "• High-Speed Peripherals: Dedicated I2S controller with DMA, independent I2C bus, 12-bit SAR ADC with hardware calibration, and native USB-CDC/JTAG."
    )

    add_heading_styled(doc, "3.2 Dual INMP441 Digital Microphone Array (40.0 mm Baseline)", level=2)
    doc.add_paragraph(
        "To overcome the severe electromagnetic interference and analog breadboard noise inherent to engine bay environments, "
        "MotoPulse rejects conventional analog electret capsules in favor of the INMP441 omnidirectional digital MEMS microphone. "
        "The INMP441 integrates an acoustic transducer, preamplifier, and 24-bit delta-sigma I2S A/D converter on a single die, providing an SNR of 61 dBA "
        "and an Acoustic Overload Point (AOP) of 120 dB SPL."
    )
    doc.add_paragraph(
        "The two microphones are mounted on a rigid PCB with an exact center-to-center baseline spacing of 40.0 mm. "
        "Mic 1 has its L/R pin grounded to stream on the I2S Left channel; Mic 2 has its L/R pin tied to +3.3V to stream on the Right channel. "
        "Both sensors share the continuous serial clock (SCK = GPIO 4), frame sync (WS = GPIO 5), and serial data line (SD = GPIO 6)."
    )

    add_heading_styled(doc, "3.3 Piezoelectric Vibration & Mechanical Shock Sensor", level=2)
    doc.add_paragraph(
        "A 27mm brass-backed piezoelectric ceramic disc is affixed directly to the motor casing or test jig. "
        "Piezoelectric transducers act as high-impedance AC voltage generators capable of developing large transient voltage spikes (>15V) "
        "upon sharp mechanical shock. To safely interface with the ESP32-S3 ADC without requiring an active op-amp split-rail power supply, "
        "the sensor is connected directly between GPIO 1 (ADC1 Channel 0) and GND with:\n"
        "1. An internal ESP32 pull-down resistor (~45 kΩ) activated in software to reference the baseline near 200–280 ADC counts.\n"
        "2. A 1.0 MΩ damping / bleed resistor (R1) across the terminals on the carrier board to discharge capacitive charge and suppress overshoot."
    )

    add_heading_styled(doc, "3.4 Master Pinout & Interconnection Matrix", level=2)
    
    pin_table = doc.add_table(rows=11, cols=4)
    pin_data = [
        ("ESP32-S3 Pin", "Peripheral", "Signal Name", "Description & Electrical Specification"),
        ("GPIO 4", "Dual INMP441", "I2S_SCK", "Continuous Bit Clock (BCLK) @ 1.024 MHz (16 kHz x 32 bits x 2 ch)"),
        ("GPIO 5", "Dual INMP441", "I2S_WS", "Word Select / Frame Sync (LRCLK) @ 16.0 kHz"),
        ("GPIO 6", "Dual INMP441", "I2S_SD", "Serial Data Line (Time-Multiplexed Left/Right 32-bit Slots)"),
        ("GPIO 1 (ADC1_0)", "Piezo Disc", "PIEZO_IN", "Analog Vibration Input (Atten: 11dB, 0-3.1V dynamic range)"),
        ("GPIO 8", "16x2 LCD / OLED", "I2C_SCL", "I2C Bus Clock @ 400 kHz Fast Mode (Hardware Pull-up)"),
        ("GPIO 9", "16x2 LCD / OLED", "I2C_SDA", "I2C Bus Serial Data @ 400 kHz Fast Mode"),
        ("+3.3V", "All Modules", "VCC_3V3", "Regulated 3.3V DC Power Rail from ESP32 On-Board LDO"),
        ("GND", "All Modules", "GND", "Continuous Top & Bottom Low-Impedance Ground Planes"),
        ("INMP441 (L/R - 1)", "Mic 1 (Left)", "L/R = GND", "Left Channel Active Slot Selection"),
        ("INMP441 (L/R - 2)", "Mic 2 (Right)", "L/R = 3V3", "Right Channel Active Slot Selection")
    ]
    for r_idx, row in enumerate(pin_table.rows):
        for c_idx, val in enumerate(pin_data[r_idx]):
            row.cells[c_idx].paragraphs[0].text = val
    style_table(pin_table, [1.3, 1.3, 1.2, 2.7], ['L', 'L', 'L', 'L'])

    # ==========================================
    # SECTION 4: KICAD PCB CARRIER BOARD
    # ==========================================
    add_heading_styled(doc, "4. KiCad 10 Custom Motherboard Carrier PCB", level=1)
    
    doc.add_paragraph(
        "To transition the MotoPulse system from experimental breadboard prototyping into an integrated automotive-grade test instrument, "
        "a custom 2-layer motherboard carrier board (Rev v2.2) was engineered in KiCad 10. "
        "The board unifies the compute module, microphone array, display header, and vibration circuit into a monolithic enclosure-ready form factor."
    )
    
    add_callout(
        doc,
        "Zero ERC & DRC Violations",
        "The carrier board design successfully passed complete KiCad Electrical Rules Check (0 Errors, 0 Warnings) and Design Rules Check (0 Violations, 0 Unconnected Nets) with a standard 0.20mm trace/space rule and continuous thermal reliefs.",
        alert_type="success"
    )

    # Embed 3D PCB Renders
    pcb_iso_path = "/home/vishwa/.gemini/antigravity-cli/brain/c7dd8daf-02ac-4cd3-b117-86f222a01f3a/motopulse_pcb_3d_isometric.png"
    pcb_top_path = "/home/vishwa/.gemini/antigravity-cli/brain/c7dd8daf-02ac-4cd3-b117-86f222a01f3a/motopulse_pcb_3d_top.png"
    breadboard_path = "/home/vishwa/Documents/hacktivate/mic_breadboard_circuit.png"
    
    add_image_safe(doc, pcb_iso_path, width_inches=5.8, caption="MotoPulse™ All-in-One Carrier Board — Isometric 3D KiCad 10 Render")
    add_image_safe(doc, pcb_top_path, width_inches=5.8, caption="MotoPulse™ Carrier Board Top Layer Layout (Dual Microphones at 40mm Baseline)")
    add_image_safe(doc, breadboard_path, width_inches=5.5, caption="Prototyping Circuit & Breadboard Wiring Guide for Verification")

    add_heading_styled(doc, "4.1 Bill of Materials (BOM) & Sourcing", level=2)
    bom_table = doc.add_table(rows=6, cols=5)
    bom_data = [
        ("Designator", "Component Description", "Package / Footprint", "Quantity", "Key Specifications"),
        ("U1", "ESP32-S3-DevKitC-1-N16R8", "DIP-44 (2x22 Pin, 0.9\" Spacing)", "1", "240 MHz Dual-Core, 16MB Flash, 8MB PSRAM"),
        ("J1", "INMP441 MEMS Microphone Module", "1x6 Pin Header, 2.54mm pitch", "1", "Digital I2S, Left Channel (L/R -> GND)"),
        ("J2", "INMP441 MEMS Microphone Module", "1x6 Pin Header, 2.54mm pitch", "1", "Digital I2S, Right Channel (L/R -> 3V3)"),
        ("J3", "16x2 I2C LCD / 0.96\" OLED Display", "1x4 Socket Header, 2.54mm pitch", "1", "VCC, GND, SCL (GPIO 8), SDA (GPIO 9)"),
        ("J4 / R1", "Piezo Disc Sensor & Bleed Resistor", "1x2 Pin Header / Axial Resistor", "1 / 1", "27mm Ceramic Element with 1.0 MΩ Damping")
    ]
    for r_idx, row in enumerate(bom_table.rows):
        for c_idx, val in enumerate(bom_data[r_idx]):
            row.cells[c_idx].paragraphs[0].text = val
    style_table(bom_table, [1.0, 1.8, 1.5, 0.6, 1.6], ['C', 'L', 'L', 'C', 'L'])

    # ==========================================
    # SECTION 5: 50CM PERIMETER GATE ALGORITHM
    # ==========================================
    add_heading_styled(doc, "5. 50cm Near-Field Acoustic Perimeter Gate", level=1)
    
    doc.add_paragraph(
        "A major challenge in vehicular acoustic diagnostics is the contamination of diagnostic signals by ambient environmental noise "
        "(traffic noise, pedestrian voices, nearby machinery, rain). MotoPulse implements an Acoustic Inverse-Square-Law Perimeter Gate "
        "leveraging the physical principle that sound pressure level decreases logarithmically with distance:"
    )
    doc.add_paragraph(
        "P(r) = P_0 / r    ===>    I(r) \\propto 1 / r^2"
    )
    doc.add_paragraph(
        "By continuously tracking the dynamic ambient noise floor (A_ambient) and computing the sound pressure gradient across the 40mm baseline, "
        "the system calculates an estimated distance in centimeters:"
    )
    
    add_code_block(doc, """
def compute_acoustic_gate(p2p_l, p2p_r, ambient_noise=220):
    max_amp = max(p2p_l, p2p_r)
    # Relative sound pressure gradient across 40mm baseline
    grad_pct = int((abs(p2p_l - p2p_r) * 100) / max(1, max_amp))
    
    # Acoustic Inverse Square Law distance mapping
    if max_amp > ambient_noise * 1.5:
        # Distance inverse model calibrated for engine bay acoustics
        dist_cm = max(5.0, min(120.0, 48.0 * ((ambient_noise * 3.5) / max(1, max_amp))**0.5))
    else:
        dist_cm = 120.0 # Far field / idle
        
    is_near = (dist_cm <= 50.0) and (max_amp >= 1200 or grad_pct >= 8)
    gate_state = "NEAR_ACCEPTED" if is_near else ("FAR_REJECTED" if max_amp > ambient_noise * 2 else "ARMED")
    return {"is_near": is_near, "distance_cm": round(dist_cm, 1), "gate_state": gate_state}
""", language="python")

    # ==========================================
    # SECTION 6: TINYML DEEP LEARNING MODEL SUITE
    # ==========================================
    print("[4/5] Building TinyML Deep Learning Model Documentation...")
    add_heading_styled(doc, "6. TinyML Edge Deep Learning Model Suite", level=1)
    
    doc.add_paragraph(
        "The core diagnostic intelligence of MotoPulse is provided by a custom Depthwise Separable 2D Convolutional Neural Network (CNN) "
        "trained on automotive acoustic datasets and fully quantized into signed 8-bit integers (INT8) for zero-copy execution on the ESP32-S3."
    )
    
    add_heading_styled(doc, "6.1 Feature Engineering: 32-Band Log-Mel Spectrogram", level=2)
    doc.add_paragraph(
        "Continuous 16,000 Hz 16-bit audio is buffered into 1.0-second non-overlapping windows (16,000 samples). "
        "Short-Time Fourier Transform (STFT) is computed using a Hann window of 480 samples (30 ms) with a hop size of 320 samples (20 ms). "
        "The resulting power spectrogram is projected onto 32 triangular Mel filterbanks spanning 40 Hz to 8,000 Hz, followed by dynamic range log compression: "
        "S_mel(m, t) = log(MelFilterBank * |STFT(x)|^2 + 1e-6). "
        "This yields a compact input tensor of shape (49 time steps, 32 frequency bins, 1 channel)."
    )

    add_heading_styled(doc, "6.2 Neural Network Architecture & Benchmarks", level=2)
    
    ml_table = doc.add_table(rows=8, cols=3)
    ml_data = [
        ("Metric / Attribute", "Core-8 Fast Diagnostics Model", "Full-30 Anomaly Model"),
        ("Model Filename", "motopulse_core8_classifier.tflite", "motopulse_full30_classifier.tflite"),
        ("Target Classes", "8 Core Engine Faults + Idle", "30 Detailed Automotive Defects"),
        ("Test Accuracy", "99.40%", "99.37%"),
        ("Macro F1-Score", "0.9949", "0.9824"),
        ("Quantization Format", "Full INT8 (signed int8_t inputs & outputs)", "Full INT8 (signed int8_t inputs & outputs)"),
        ("Flash Binary Size", "13.58 KB (13,904 bytes)", "15.27 KB (15,632 bytes)"),
        ("Inference Latency @ 240MHz", "14.7 ms per window", "17.0 ms per window")
    ]
    for r_idx, row in enumerate(ml_table.rows):
        for c_idx, val in enumerate(ml_data[r_idx]):
            row.cells[c_idx].paragraphs[0].text = val
    style_table(ml_table, [2.2, 2.1, 2.2], ['L', 'C', 'C'])

    add_heading_styled(doc, "6.3 Standardized Fault Diagnostic Classes", level=2)
    doc.add_paragraph(
        "1. normal_idle: Optimal engine operation across all 32 Mel bands (Stage 0: Nominal, RUL > 18,500 km).\n"
        "2. engine_knocking: High-energy mechanical shock on connecting rod / wrist pins (Stage 3: Critical, RUL < 1,200 km).\n"
        "3. bearing_wear: High-frequency friction screech in tensioner, water pump, or alternator bearings (Stage 2: Moderate wear).\n"
        "4. valve_ticking: Rhythmic tapping caused by excessive valve clearance or sticky hydraulic lifters.\n"
        "5. belt_slippage: Serpentine drive belt friction slip under alternator / AC compressor load.\n"
        "6. exhaust_leak: Pulsed blowby gas hiss from cracked manifold or damaged downpipe gasket.\n"
        "7. misfire: Periodic combustion cycle dropout resulting in irregular low-frequency torque oscillations.\n"
        "8. turbo_flutter: Compressor surge and wastegate pressure leakage under deceleration."
    )

    # ==========================================
    # SECTION 7: CONTINUAL SELF-LEARNING ENGINE
    # ==========================================
    add_heading_styled(doc, "7. Autonomous Continual On-Device Self-Learning", level=1)
    
    doc.add_paragraph(
        "Acoustic baselines naturally drift between engine models, cylinder counts, oil grades, and engine temperatures. "
        "MotoPulse features an on-device streaming continual learning engine that adapts without requiring cloud retraining. "
        "The learner categorizes vehicle telemetry into 3 operational driving regimes:\n"
        "• Regime 0: IDLE (750 ± 150 RPM) — Pure low-frequency acoustic profile.\n"
        "• Regime 1: CITY DRIVE (1800 ± 400 RPM) — Balanced mid-band acoustic and structural vibration.\n"
        "• Regime 2: HIGHWAY CRUISE (2800 ± 500 RPM) — High-frequency wind, road, and mechanical harmonics."
    )
    doc.add_paragraph(
        "For each regime, the engine executes Welford's algorithm to update running mean (μ) and variance (σ²) vectors across all 32 spectral bins. "
        "Novel anomalies trigger a Z-score deviation warning when the Mahalanobis distance exceeds statistical thresholds (Z > 3.0), "
        "flagging emergent mechanical problems before they appear in standard classification models."
    )

    # ==========================================
    # SECTION 8: FIRMWARE ARCHITECTURE
    # ==========================================
    print("[5/5] Building Firmware, Web Dashboard & Validation Sections...")
    add_heading_styled(doc, "8. Embedded Firmware Architecture", level=1)
    
    doc.add_paragraph(
        "The firmware is developed in MicroPython v1.29.0 with DMA hardware acceleration. "
        "The main loop maintains real-time synchronization between digital audio streaming, LCD display updates, "
        "and USB-CDC telemetry serialization at ~36 frames per second:"
    )
    
    add_code_block(doc, """
# MicroPython Fast Hardware Acquisition & Telemetry Streaming
import machine, struct, time

# Dual I2S Stereo Interface at 16 kHz, 32-bit slot width
i2s = machine.I2S(0, sck=machine.Pin(4), ws=machine.Pin(5), sd=machine.Pin(6),
                  mode=machine.I2S.RX, bits=32, format=machine.I2S.STEREO,
                  rate=16000, ibuf=4096)

# Piezo Vibration Sensor on GPIO 1 with Internal Pull-Down
piezo = machine.ADC(machine.Pin(1, machine.Pin.IN, machine.Pin.PULL_DOWN))
piezo.atten(machine.ADC.ATTN_11DB)

buf = bytearray(512)
while True:
    i2s.readinto(buf)
    words = struct.unpack('<128i', buf)
    left = [words[i] >> 16 for i in range(0, 128, 2)]
    right = [words[i] >> 16 for i in range(1, 128, 2)]
    
    p2p_l = max(left) - min(left)
    p2p_r = max(right) - min(right)
    
    # 64-sample burst read for transient shockwave capture
    pz_raw = [piezo.read() for _ in range(64)]
    pz_amp = max(pz_raw) - min(pz_raw)
    
    # Serialize compact telemetry frame over USB-CDC
    print(f"TEL:{p2p_l}:{p2p_r}:{pz_amp}:{left[:16]}")
""", language="python")

    # ==========================================
    # SECTION 9: WEB COCKPIT & PROGNOSTICS
    # ==========================================
    add_heading_styled(doc, "9. MotoPulse Web Cockpit & Prognostics Horizon", level=1)
    
    doc.add_paragraph(
        "The web interface operates as an aerospace-grade telemetry cockpit displaying 7 synchronized live diagnostic panels:"
    )
    doc.add_paragraph(
        "1. Dual-Microphone Oscilloscope: Real-time dual waveform canvas rendering Left (cyan) and Right (green) channel audio with peak holds.\n"
        "2. 360° Acoustic Perimeter Radar: Displays sound bearing angles and spatial blips calculated from the stereo interaural level difference.\n"
        "3. Piezoelectric Seismograph: Scrolling 250-point waveform tracing mechanical engine block vibrations, auto-detecting detonation knocks.\n"
        "4. Live Acoustic Ear Monitor: In-browser Web Audio API synthesizing live 16 kHz audio for headphones alongside a 32-band Log-Mel spectrum equalizer.\n"
        "5. Continual Self-Learning Panel: Live monitoring of learned driving regimes, anomaly confidence scores, and cluster centroids.\n"
        "6. Diagnostic Session Controller: Fixed 5s, 10s, and 15s evaluation locks that freeze and stabilize diagnoses to eliminate UI jitter.\n"
        "7. AI Predictive Prognostics Horizon: Computes Remaining Useful Life (RUL) in kilometers and operational hours, health score (0-100%), "
        "and four degradation stages (Stage 0: Nominal, Stage 1: Incipient, Stage 2: Moderate, Stage 3: Critical Defect)."
    )

    # ==========================================
    # SECTION 10: TEST BENCH & VALIDATION
    # ==========================================
    add_heading_styled(doc, "10. Test Bench & Serial Contention Protection", level=1)
    
    doc.add_paragraph(
        "To ensure robust testability during judge evaluations, MotoPulse provides an interactive command-line control panel (`mic_test/run_test.sh`). "
        "A dedicated serial contention protection algorithm (`check_and_free_port`) was implemented to eliminate USB CDC port contention:"
    )
    doc.add_paragraph(
        "• Problem: In Linux, two processes reading from `/dev/ttyACM0` simultaneously cause EOF errors (SerialException: multiple access on port).\n"
        "• Solution: The test bench automatically identifies any active background telemetry server holding the serial port, safely terminates it, "
        "grants exclusive access to the test visualizer, and soft-reboots the ESP32 upon exit (Ctrl+C) to seamlessly restore on-device firmware."
    )

    # ==========================================
    # SECTION 11: CONCLUSION & FUTURE ROADMAP
    # ==========================================
    add_heading_styled(doc, "11. Conclusion & Future Roadmap", level=1)
    
    doc.add_paragraph(
        "MotoPulse successfully demonstrates the complete viability of edge AI acoustic predictive maintenance for commercial and passenger vehicles. "
        "By hosting deep learning models and signal processing directly on the ESP32-S3 microcontroller, the system provides real-time failure prediction "
        "at a tiny fraction of the cost of industrial vibration analyzers, while maintaining absolute data privacy."
    )
    doc.add_paragraph(
        "Future Roadmap Milestones:\n"
        "1. Direct CAN-Bus Integration: Incorporating an SN65HVD230 transceiver to fuse acoustic prognostics with live engine RPM and throttle position.\n"
        "2. Multi-Sensor Spatial Mesh: Expanding from a dual-microphone carrier board to a distributed 4-node microphone array across the chassis.\n"
        "3. Fleet Telematics Sync: Transmitting lightweight INT8 diagnostic vectors over NB-IoT / 4G for commercial fleet maintenance tracking."
    )

    # Save Document
    output_path = "/home/vishwa/Documents/hacktivate/MotoPulse_Complete_Project_Documentation.docx"
    doc.save(output_path)
    print(f"✔ Document generated successfully at: {output_path}")
    print(f"  File size: {os.path.getsize(output_path):,} bytes")
    return output_path

if __name__ == "__main__":
    generate_documentation()
