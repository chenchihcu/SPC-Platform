\# SPC\_RULES.md

\## SMT SPI / SPC Statistical Rules Specification



This document defines the official statistical rules used by the

SMT SPI / SPC Statistical Analysis Platform.



These rules are mandatory for all implementations.



AI agents must not change or invent statistical formulas.



Repository governance (when to update this document before code, and how it relates to `docs/specs/data_contract.md` and chart specs): see **`docs/specs/spec_maintenance_and_alignment.md`** §6.



\---



\# 1. SPC Purpose



Statistical Process Control (SPC) is used to monitor

process stability and detect abnormal variations.



In the SPI process, SPC is applied to:



• solder paste volume  

• solder paste height  

• solder paste area  

• offset measurements



\---



\# 2. Supported Measurement Types



The system supports the following SPI measurements.



Volume  

Area  

Height  

XOffset  

YOffset



Primary SPC indicators focus on:



Volume  

Height



\# 2.1 Normality diagnostics (engine contract)



The Normality view may run formal tests (e.g. Shapiro-Wilk for n ≤ 5000, D'Agostino K² for larger n) when the sample is large enough.



**Zero-variance series** (all non-null values equal): Shapiro-Wilk is **not** executed. The engine sets `normality_test_skipped` to true, `shapiro_skip_reason` to `zero_variance`, and uses a deterministic p-value of 1.0 so the UI remains stable. Treat this as “test not informative for spread,” not as statistical evidence of Gaussian shape. Downstream summaries should rely on `normality_test_skipped` / `shapiro_skip_reason` when interpreting `is_normal`.



\---



\# 3. Control Chart Types



The platform supports three control chart types.



I-MR Chart  

Xbar-R Chart  

Xbar-S Chart



The selection depends on the data structure.



\# 3.1 Terminology Mapping (Statistical Name vs UI Label)



This document keeps **statistical canonical names** (I-MR / Xbar-R / Xbar-S) as the rule source.



Current product UI may show operational labels such as:



• `imr` / 「個別值與移動極差圖」  

• `run_chart` / 「趨勢圖」  

• `subgroup` / 「子群比較」



Important:



• `subgroup` is a subgroup comparison visualization and is **not** a direct replacement of classical Xbar-R/Xbar-S control-limit charts.  

• Statistical formulas and interpretation thresholds in this document remain authoritative regardless of UI wording.  

• If a future UI exposes explicit Xbar-R/Xbar-S chart labels, naming must map to this rules taxonomy without changing formulas/constants unless this file is updated first.



\---



\# 4. I-MR Chart



Used when measurements are individual values.



Example:



SPI inspection per pad.



Definitions:



X\_i = measurement value



Moving Range:



MR\_i = |X\_i - X\_(i-1)|



Average Moving Range:



MR\_bar = mean(MR)



Process Mean:



CL = mean(X)



Standard Deviation Estimate:



sigma = MR\_bar / d2



For MR chart:



d2 = 1.128



Control Limits:



UCL = CL + 3 \* sigma  

LCL = CL - 3 \* sigma



\---



\# 5. Xbar-R Chart



Used when measurements are subgrouped.



Example:



Multiple boards per lot.



Subgroup size:



n = number of samples per subgroup



Subgroup mean:



Xbar\_i = mean(subgroup)



Range:



R\_i = max(subgroup) - min(subgroup)



Average range:



R\_bar = mean(R)



Control limits:



Xbar chart:



UCL = Xbar\_bar + A2 \* R\_bar  

LCL = Xbar\_bar - A2 \* R\_bar



Constants depend on subgroup size.



\---



\# 6. Capability Analysis



Capability metrics measure the relationship

between process variation and specification limits.



Required parameters:



USL = Upper Specification Limit  

LSL = Lower Specification Limit



\---



\# 7. Cp



Cp measures potential capability.



Formula:



Cp = (USL - LSL) / (6 \* sigma)



Interpretation:



Cp < 1.0   → process incapable  

Cp = 1.33  → typical manufacturing target  

Cp ≥ 1.67  → high capability



\---



\# 8. Cpk



Cpk measures centered capability.



Formula:



Cpk = min(



(USL - mean) / (3 \* sigma),



(mean - LSL) / (3 \* sigma)



)



Interpretation:



Cpk < 1.0 → unacceptable  

Cpk ≥ 1.33 → acceptable  

Cpk ≥ 1.67 → high capability



\---



\# 9. Pp / Ppk



Pp and Ppk use overall standard deviation.



Pp = (USL - LSL) / (6 \* sigma\_total)



Ppk = min(



(USL - mean)/(3\*sigma\_total),



(mean - LSL)/(3\*sigma\_total)



)



\# 9.1 Cpk 95% Confidence Interval (dashboard/report contract)



For dashboard/report field `Cpk 95% CI`, the system uses the **Bissell approximation**
(common in NIST/AIAG practice) for a two-sided confidence interval:



SE(Cpk) = sqrt( 1/(9N) + Cpk^2/(2(N-1)) )



CI\_95% = \[ max(0, Cpk - z\_{0.975}\*SE), Cpk + z\_{0.975}\*SE \]



Where:

- N = valid sample size after removing NaN and ±inf
- z\_{0.975} = 1.959963984540054 (two-sided 95%)



When Cpk is undefined or N < 2, output must be `N/A`.



\---



\# 10. Western Electric Rules



The system may detect abnormal patterns.



Rule 1  

One point beyond UCL or LCL



Rule 2  

Two of three consecutive points beyond 2 sigma



Rule 3  

Four of five points beyond 1 sigma



Rule 4  

Eight consecutive points on one side of mean



These rules help detect process drift.



\---



\# 11. SPI Process Interpretation



SPI measurements relate to solder paste deposition quality.



Key metrics:



Volume  

Area  

Height



\---



\# 12. Typical SPI Target Ranges



Example engineering targets:



Volume



80% – 120% of nominal



Area



70% – 130% of nominal



Height



±25% variation



These values depend on stencil thickness

and pad design.



\---



\# 13. Outlier Detection



Outliers may be detected using:



3 sigma rule



or



IQR method



However SPC rules remain the primary detection mechanism.



\---



\# 14. Data Requirements



SPC calculations require minimum data.



Minimum:



20 samples



Recommended:



50+ samples



Capability analysis recommended:



100+ samples



\---



\# 15. Invalid SPC Conditions



SPC must not be computed when:



• sample size < 10  

• sigma = 0  

• missing measurement values  



In these cases, the system should display

a warning.



\---



\# 16. Spatial Analysis Rules



When coordinate data exists, measurements

can be projected to PCB coordinates.



Required fields:



X  

Y  

MeasurementValue



Output:



Heatmap  

Cluster detection



\---



\# 17. Performance Requirements



SPC calculations must handle datasets:



10k rows  

50k rows  

100k+ rows



Vectorized operations must be used.



\---



\# 18. Agent Compliance



AI agents must follow these rules.



Agents must NOT:



• invent SPC formulas  

• change statistical constants  

• alter capability interpretation  



Statistical accuracy is mandatory.

