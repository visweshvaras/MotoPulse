# MotoPulse Hardware Package: KiCad 10 Schematic, PCB & Manufacturing Deliverables

**Project:** MotoPulse — Automotive Acoustic Predictive Maintenance Edge AI System  
**Event:** IEEE RUAS - Hacktivate 2026  
**Revision:** 2.0 (Digital I2S MEMS + OLED Real-Time Spectrum Hardware)  
**Verification:** **0 ERC Violations (100% Pass) | 0 DRC Violations (100% Pass) | 0 Unconnected Nets**

---

## 1. System Architecture Overview

MotoPulse captures automotive mechanical acoustic emissions using high-fidelity digital I2S MEMS microphones, processes spectral features via real-time edge FFTs on an ESP32-S3 microcontroller, and displays real-time frequency diagnostics on an onboard SSD1306 OLED display.

```
                    +-----------------------------+
                    |    ESP32-S3 DevKitC-1       |
                    |  (Dual-Core Xtensa LX7 MCU) |
                    +------+---------------+------+
                           |               |
          I2S Digital Bus  |               |  I2C Control Bus
     (SCK: GPIO4, WS: 5,   |               |  (SCL: GPIO9, SDA: 8)
      SD: GPIO6)           |               |  + 4.7k Pull-ups (R1, R2)
                           v               v
                +------------------+  +-------------------+
                | INMP441 Digital  |  | 0.96" SSD1306     |
                | MEMS Microphone  |  | 128x64 OLED Panel |
                | (Decoupled: C1)  |  | (Decoupled: C2)   |
                +------------------+  +-------------------+
```

---

## 2. Component Pinout & Interconnect Table

| Component | Ref | Pins / Description | Interface | ESP32-S3 Connection |
|:---|:---:|:---|:---:|:---|
| **ESP32-S3 DevKitC-1 Header 1** | `J1` | 22-pin Socket Header (2.54mm pitch) | Power & I2S | Pin 1 (+3.3V), Pin 6 (GPIO4/SCK), Pin 7 (GPIO5/WS), Pin 8 (GPIO6/SD), Pin 13 (GND) |
| **ESP32-S3 DevKitC-1 Header 2** | `J2` | 22-pin Socket Header (2.54mm pitch) | Power & I2C | Pin 1 (GND), Pin 14 (GPIO9/SCL), Pin 15 (GPIO8/SDA) |
| **INMP441 Breakout Header** | `J3` | 6-pin Header (VDD, GND, SD, SCK, WS, L/R) | Digital I2S | VDD (+3.3V), GND, SD (J1.8), SCK (J1.6), WS (J1.7), L/R (GND - Left Channel) |
| **SSD1306 OLED Header** | `J4` | 4-pin Header (VDD, GND, SCL, SDA) | I2C | VDD (+3.3V), GND, SCL (J2.14), SDA (J2.15) |
| **Mic Decoupling Capacitor** | `C1` | 100nF SMD 0805 | Bypass | Between INMP441 VDD and GND |
| **OLED Decoupling Capacitor** | `C2` | 100nF SMD 0805 | Bypass | Between OLED VDD and GND |
| **SCL Pull-up Resistor** | `R1` | 4.7kΩ SMD 0805 | I2C Bus | Between SCL and +3.3V |
| **SDA Pull-up Resistor** | `R2` | 4.7kΩ SMD 0805 | I2C Bus | Between SDA and +3.3V |
| **Mounting Holes** | `H1-H4`| 4x M2.5 (2.7mm drill) | Mechanical | Corner mounting holes inset 5.0mm |

---

## 3. PCB Layout & Routing Specifications

- **Board Dimensions:** 100.00 mm × 95.00 mm (FR4, 1.6mm thickness).
- **Layer Stack:** 2-Layer (Top Copper `F.Cu`, Bottom Copper `B.Cu`).
- **Ground Planes:** Continuous, solid copper ground planes on both Top and Bottom layers with thermal relief spoke connections on all ground pads and vias.
- **Trace Clearances & Routing Topology:**
  - `+3.3V` Power Rail: Routed on `F.Cu` along northern perimeter (0.50mm width).
  - `I2S` Audio Signals (`SCK`, `WS`): Routed on `B.Cu` in parallel non-overlapping tracks (0.35mm width).
  - `I2S` Data Signal (`SD`): Routed on `F.Cu` with dedicated isolation channel (0.35mm width).
  - `I2C` Signals (`SCL`, `SDA`): Straight horizontal parallel tracks on `B.Cu` (0.35mm width).
  - Minimum track clearance: **1.45 mm** (far exceeding standard 0.20 mm constraints).
  - Via count: **9 through-hole vias** (strictly minimized to reduce parasitic inductance).

---

## 4. Verification & DRC/ERC Reports

### Electrical Rules Check (ERC)
- Report: [`motopulse-erc.rpt`](./motopulse-erc.rpt)
- Status: **0 Errors, 0 Warnings, 0 Violations**

### Design Rule Check (DRC)
- Report: [`motopulse-drc.rpt`](./motopulse-drc.rpt)
- Status: **0 Errors, 0 Warnings, 0 Unconnected Pads, 0 Footprint Errors**

---

## 5. Submission Deliverables Index

| Deliverable | File Path | Format / Description |
|:---|:---|:---|
| **Schematic File** | [`motopulse.kicad_sch`](./motopulse.kicad_sch) | KiCad 10 Schematic |
| **Schematic PDF** | [`motopulse_schematic.pdf`](./motopulse_schematic.pdf) | High-Resolution Vector PDF |
| **Schematic Image** | [`motopulse_schematic.png`](./motopulse_schematic.png) | 300 DPI Raster Render |
| **PCB Layout File** | [`motopulse.kicad_pcb`](./motopulse.kicad_pcb) | KiCad 10 Complete PCB Layout |
| **PCB Top Layer PDF** | [`motopulse_pcb_top.pdf`](./motopulse_pcb_top.pdf) | Top Copper & Silkscreen Vector PDF |
| **PCB Bottom Layer PDF** | [`motopulse_pcb_bottom.pdf`](./motopulse_pcb_bottom.pdf) | Bottom Copper Vector PDF |
| **PCB Multipage PDF** | [`motopulse_pcb.pdf`](./motopulse_pcb.pdf) | Complete Multipage PCB Layout PDF |
| **PCB Top Render** | [`motopulse_pcb_top.png`](./motopulse_pcb_top.png) | 300 DPI Top Layer Render |
| **PCB Bottom Render** | [`motopulse_pcb_bottom.png`](./motopulse_pcb_bottom.png) | 300 DPI Bottom Layer Render |
| **PCB Statistics** | [`motopulse_pcb_stats.json`](./motopulse_pcb_stats.json) | Board dimensions, copper area, drill stats |
| **Netlist** | [`motopulse.net`](./motopulse.net) | Complete KiCad Netlist |
| **Bill of Materials** | [`motopulse_bom.csv`](./motopulse_bom.csv) | Full Component BOM (CSV) |
| **Gerber Archive** | [`motopulse_gerbers.zip`](./motopulse_gerbers.zip) | Standard RS-274X Gerbers + Drill Files |

---

## 6. Regeneration & Build Instructions

To re-generate all drawings from code:
```bash
# 1. Generate Schematic
python3 generate_motopulse_schematic.py

# 2. Run Schematic ERC
kicad-cli sch erc motopulse.kicad_sch

# 3. Generate 100% DRC-Clean PCB
python3 generate_motopulse_pcb.py

# 4. Run PCB DRC
kicad-cli pcb drc motopulse.kicad_pcb
```
