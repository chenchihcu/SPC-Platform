# SPI Engineering Knowledge Base

## SMT Solder Paste Printing Engineering Knowledge Base

This document provides engineering background knowledge for SMT solder paste printing processes.
The purpose is to support intelligent SPI analysis and assist in engineering root cause diagnosis.

---

# 1. Solder Paste Printing Process

The SMT printing process deposits solder paste onto PCB pads using a stencil and squeegee system.

Key steps:
1. PCB alignment
2. stencil contact
3. solder paste rolling
4. squeegee printing
5. stencil separation
6. paste release

SPI inspection measures the result of this process.

---

# 2. Stencil Thickness

Stencil thickness directly affects solder paste volume.

Typical stencil thickness: 80 µm, 100 µm, 120 µm, 150 µm.

Volume is roughly proportional to stencil thickness.

### IPC-7525 Pitch-to-Thickness Recommendation

| Component Pitch | Recommended Thickness | Standard |
|---|---|---|
| >= 0.65 mm | 120 - 150 µm | IPC-7525 |
| 0.50 - 0.65 mm | 100 - 120 µm | IPC-7525 |
| 0.40 - 0.50 mm | 80 - 100 µm | IPC-7525 |
| <= 0.40 mm | 60 - 80 µm | IPC-7525 |

---

# 3. Aperture Design

Stencil aperture shape strongly affects paste release. (Ref: IPC-7525)

Common aperture designs:
- **Square** — Standard pad opening.
- **Rounded corner** — Improves paste release. (IPC-7525 recommended for fine pitch)
- **Home plate** — Used for QFN to reduce solder bridging. (IPC-7525)
- **Modified aperture** — Used for fine pitch components.

---

# 4. Aperture Area Ratio

Area ratio determines stencil release efficiency. (Ref: IPC-7525 Sec 4.2)

Formula: Area Ratio = Pad Area / Stencil Wall Area

**Guideline: Area Ratio >= 0.66** (IPC-7525 Sec 4.2)

If area ratio is too small, paste release becomes unstable, leading to low volume variation.

---

# 5. Transfer Efficiency

Transfer Efficiency (TE) measures stencil paste release quality. (Ref: IPC-7525)

Formula: TE = Measured Volume / Theoretical Volume

Where: Theoretical Volume = Stencil Thickness × Aperture Area

| TE Range | Quality Rating |
|---|---|
| >= 90% | GOOD |
| 75% - 90% | ACCEPTABLE |
| 60% - 75% | MARGINAL |
| < 60% | POOR |

---

# 6. Paste Rheology (J-STD-005)

Solder paste viscosity affects printing quality.

Key properties: Viscosity, Thixotropy, Slump resistance.

### J-STD-005 Paste Type Classification

| Type | Particle Size (µm) | Viscosity (Pa·s) | Application |
|---|---|---|---|
| Type 3 | 25 - 45 | 800 - 1200 | Standard SMT |
| Type 4 | 20 - 38 | 600 - 1000 | Fine pitch |
| Type 5 | 15 - 25 | 500 - 800 | Ultra fine pitch |
| Type 6 | 5 - 15 | 400 - 700 | Micro BGA |

Low viscosity may cause paste spreading. High viscosity may cause poor stencil release.

### J-STD-005 Slump Test

Solder paste must pass slump resistance testing per J-STD-005. Paste that slumps excessively increases bridge risk on fine-pitch components.

### Stencil Life / Open Time

Solder paste on stencil has limited working life (typically 8 hours per J-STD-005 guidelines). Properties degrade with extended exposure. Type 5/6 pastes are more sensitive to drying due to smaller particle size.

---

# 7. Squeegee Parameters

Printing parameters include:
- Squeegee speed: 20 - 50 mm/s
- Squeegee pressure: 0.4 - 0.8 kg/cm
- Squeegee angle

Incorrect parameters may cause insufficient paste, excess paste, or stencil smearing.

---

# 8. Printer Alignment

Printer alignment determines paste placement accuracy.

Misalignment causes offset printing. Typical acceptable offset: <= 25% pad width.
Excess offset increases bridge risk.

---

# 9. Stencil Cleaning

Stencil cleaning removes residual paste that blocks stencil apertures.

Typical cleaning frequency: Every 5 - 10 boards.

If cleaning interval is too long, paste volume variation increases.

---

# 10. Environmental Factors

Printing quality is influenced by environment.
- Temperature: Recommended 22 - 26°C
- Humidity: Recommended 40 - 60%

High humidity may cause paste slumping. Low temperature may increase viscosity.

---

# 11. PCB Design Influence

PCB pad design affects printing performance.

Important parameters: Pad size, Pad spacing, Solder mask design.
Fine pitch components require more precise printing control.

---

# 12. Common Printing Defects

Typical printing defects include:
- Insufficient paste
- Excess paste
- Offset printing
- Missing paste
- Bridge risk

These defects may originate from stencil design, printer setup, paste condition, or environment.

---

# 13. SPI False Calls

SPI systems may produce false defect signals. Examples: Reflection errors, Shadow effects, Measurement noise.

SPI results should be interpreted together with engineering context.

---

# 14. Root Cause Analysis

SPI data helps engineers identify process issues.

Example root causes:
- Stencil wear (IPC-7525)
- Printer alignment drift (IPC-7527)
- Paste viscosity change (J-STD-005)
- Cleaning interval too long

---

# 15. Engineering Analysis Strategy

When analyzing SPI data, consider:
- Statistical indicators (SPC)
- Process parameters
- Environmental factors
- Stencil design (IPC-7525)
- Paste properties (J-STD-005)

Combining these factors produces more reliable engineering conclusions.

---

# 16. Standard References

| Standard | Scope | Relevance to SPI Analysis |
|---|---|---|
| IPC-7525 | Stencil Design Guidelines | Area ratio, aperture design, TE, stencil thickness |
| IPC-7527 | SPI Machine Requirements | Measurement definitions, GR&R, acceptance criteria |
| J-STD-005 | Solder Paste Requirements | Paste type, viscosity, slump, stencil life |
| J-STD-004 | Flux Requirements | Flux classification (metadata) |
| J-STD-006 | Solder Alloy Requirements | Alloy composition (metadata) |

Note: Defect classification thresholds (e.g., Volume 80%-120%) in this system are factory-defined defaults, not directly from IPC-A-610. IPC-A-610 Class 1/2/3 integration was evaluated and deferred by design decision.
