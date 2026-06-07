\# SPI\_PARAMETER\_MODEL.md

\## SPI Parameter Modeling Rules



This document defines how SPI measurement parameters

should be modeled and interpreted inside the analysis engine.



The purpose is to standardize the relationship between

measurement data and engineering analysis.



\---



\# 1. Core SPI Parameters



SPI systems measure several parameters.



Primary parameters:



Volume (%)

Height (µm)

Area (%)



Secondary parameters:



XOffset (mm)

YOffset (mm)



Derived parameters:



Volume deviation

Height deviation

Area coverage ratio



\---



\# 2. Nominal Reference Model



Each pad measurement should be compared with

a nominal reference.



Reference sources:



CAD stencil design

Stencil thickness

SPI machine reference



Nominal model example:



Volume\_nominal = 100%

Height\_nominal = stencil\_thickness

Area\_nominal = pad\_area



\---



\# 3. Parameter Normalization



SPI data should be normalized for comparison.



Example normalization:



Volume\_ratio = measured\_volume / nominal\_volume



Height\_ratio = measured\_height / stencil\_thickness



Area\_ratio = measured\_area / pad\_area



\---



\# 4. Parameter Stability



Process stability can be measured using:



Mean

Standard deviation

Coefficient of variation



Example:



CV = σ / μ



High CV indicates unstable printing.



\---



\# 5. Component-Level Metrics



SPI analysis should support aggregation.



Component metrics:



Mean volume

Volume deviation

Volume uniformity

Pad variation



\---



\# 6. Board-Level Metrics



Board-level statistics include:



Mean volume per board

Volume variation per board

Defect count per board



This helps identify printing drift.



\---



\# 7. Spatial Parameters



When coordinate data exists:



X

Y



SPI data can be projected to PCB layout.



Derived metrics:



Local volume variation

Cluster detection

Edge vs center variation



\---



\# 8. Time-Series Parameters



SPI data can be analyzed over time.



Example:



Volume trend per board index



Possible causes:



Printer drift

Stencil wear

Paste aging



\---



\# 9. Parameter Relationships



Certain SPI parameters are correlated.



Volume ≈ Area × Height



If area is low but height is high:



Stencil release issue.



If height normal but volume low:



Incomplete paste coverage.



\---



\# 10. Outlier Detection



Outliers should be identified using:



3-sigma rule

IQR method



Outliers should not automatically

be treated as defects.



Engineering context must be considered.



\---



\# 11. Parameter Modeling Goal



The purpose of parameter modeling is to support:



SPC analysis

defect classification

root cause analysis

process optimization

