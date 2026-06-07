\# SPI\_DEFECT\_CLASSIFICATION.md

\## SMT SPI Defect Classification Rules



This document defines defect classification rules for

Solder Paste Inspection (SPI) data.



The purpose is to enable automatic identification of

printing defects in SMT processes.



Note: All threshold values below are factory-defined defaults.

IPC-A-610 Class 1/2/3 integration was evaluated and deferred by design decision.



These rules are used together with:



SPC\_RULES.md

SPI\_PROCESS\_RULES.md



\---



\# 1. SPI Defect Categories



SPI inspection can detect the following defect types.



INSUFFICIENT  

EXCESS  

MISSING  

OFFSET  

BRIDGE\_RISK  

SHAPE\_ABNORMALITY



Each defect is defined using measurement thresholds.



\---



\# 2. Required Measurement Inputs



SPI classification uses the following data.



Volume (%)



Area (%)



Height (µm)



XOffset (mm)



YOffset (mm)



Pad size and component type may also be used.



\---



\# 3. Insufficient Paste



Definition:



Solder paste volume below acceptable limit.



Typical threshold:



Volume < 80%



Engineering meaning:



Not enough solder paste deposited.



Potential causes:



Stencil clogging  

Poor paste release  

Low paste viscosity  

Printing pressure issues



Risk:



Open solder joint.



\---



\# 4. Excess Paste



Definition:



Solder paste volume above acceptable limit.



Typical threshold:



Volume > 120%



Engineering meaning:



Too much solder paste.



Potential causes:



Overprinting  

Stencil aperture oversized  

Paste slump



Risk:



Solder bridging.



\---



\# 5. Missing Paste



Definition:



Paste volume near zero.



Typical threshold:



Volume < 10%



Engineering meaning:



Paste not deposited on pad.



Potential causes:



Stencil blocked  

Printer alignment failure  

Stencil damage



Risk:



Complete solder joint failure.



\---



\# 6. Offset Defect



Definition:



Paste printed away from pad center.



Typical threshold:



Offset > 25% of pad width



Example:



Pad width = 0.5 mm



Offset limit:



0.125 mm



Potential causes:



Printer misalignment  

Stencil shift  

PCB positioning error



Risk:



Tombstoning  

Weak solder joints.



\---



\# 7. Bridge Risk



Definition:



Paste volume or area too large near adjacent pads.



Typical indicators:



Volume > 130%



Area > 130%



or



Offset toward neighboring pad.



Engineering meaning:



High probability of solder bridge during reflow.



Common locations:



Fine pitch ICs  

QFP  

QFN  

BGA breakout areas.



\---



\# 8. Shape Abnormality



Definition:



Paste geometry abnormal even when volume is acceptable.



Indicators:



Area low but height high



or



Area high but height low



Possible causes:



Stencil release issue  

Paste sticking to stencil  

Paste slumping



\---



\# 9. Combined Defect Conditions



Some defects require multiple indicators.



Example:



Low volume + low area



→ Insufficient paste



High volume + large area



→ Bridge risk



Offset + high volume



→ High bridge probability



\---



\# 10. Component-Level Aggregation



Defects can be analyzed at component level.



Example metrics:



Number of defective pads per component



Defect ratio per component



Mean paste volume per component



This helps identify component-specific issues.



\---



\# 11. Board-Level Defect Mapping



Defects may be visualized using PCB coordinates.



Visualization methods:



Heatmap



Defect density map



Cluster analysis



These help identify printer or stencil problems.



\---



\# 12. Defect Severity Levels



Defects may be categorized by severity.



Level 1



Minor variation.



Level 2



Process warning.



Level 3



High risk defect.



Example:



Volume 75%



Level 2 warning.



Volume 60%



Level 3 defect.



\---



\# 13. Statistical Defect Monitoring



Defect counts may be monitored using SPC.



Examples:



Defect rate per board



Defect rate per component



Defect type distribution.



This supports process improvement.



\---



\# 14. Defect Reporting



The system should support automated reports.



Examples:



Top defect components



Top defect locations



Defect trend over time



\---



\# 15. Engineering Usage



Defect classification supports:



Process monitoring  

Root cause analysis  

Stencil maintenance decisions  

Printer calibration checks



The goal is to improve SMT printing stability.

