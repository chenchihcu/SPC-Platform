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


---
### 多變量統計製程管制 (Multivariate SPC)

### Hotelling T² 管制圖

**公式：**
- T² 統計量：`T²ᵢ = (xᵢ - x̄)' * S⁻¹ * (xᵢ - x̄)`
  - xᵢ：第 i 個樣本的 p 維特徵向量 (Volume, Area, Height)
  - x̄：特徵均值向量
  - S⁻¹：樣本共變異矩陣 S 的逆矩陣
- 上管制界限 (UCL)：`UCL = p * (n - 1) * (n + 1) / (n * (n - p)) * F_{α}(p, n - p)`
  - p = 特徵數 (3)
  - n = 樣本數
  - F_{α}(p, n-p)：F 分佈在 α = 0.05 的第 95 百分位數
  - 註：`(n + 1) / n` 因子來自 Hotelling T² Phase I 管制圖的標準公式（樣本均值向量作為目標 μ₀ 時）
- 若 T²ᵢ > UCL，則第 i 點判定為失控 (OOC)

**假設：**
- 資料來自多變量常態分佈 (p-variate normal)
- 樣本獨立
- 共變異矩陣 S 為正定 (positive definite)

**μ₀ 估計：**
- 若無歷史均值，使用樣本均值向量 x̄ 作為目標
- 可選：使用規格中心 (USL + LSL) / 2 作為目標向量

**參數：**
- α = 0.05 (95% 信心水準)
- p = 3 (Volume, Area, Height)
- n = 樣本數 (最小要求: n > p，且 n > 10)

---
### 空間自相關分析 (Spatial Autocorrelation)

#### Moran's I 全局空間自相關

**公式：**
- Global Moran's I：`I = (n / S₀) * ΣᵢΣⱼ wᵢⱼ (xᵢ − x̄)(xⱼ − x̄) / Σᵢ (xᵢ − x̄)²`
  - n：樣本數
  - xᵢ：第 i 個樣本的值
  - x̄：樣本均值
  - wᵢⱼ：空間權重矩陣（本實作使用 K 近鄰 KNN，權重 = 1/k）
  - S₀：所有空間權重之和 `S₀ = ΣᵢΣⱼ wᵢⱼ`

**假設檢驗：**
- 零假設 H₀：空間隨機（無空間自相關）
- 備擇假設 H₁：存在空間自相關
- 使用 Monte Carlo 置換檢驗（預設 999 次置換）計算 pseudo p-value
- 若 p-value < 0.05，拒絕 H₀，認為存在顯著空間自相關

**解釋：**
- I > E[I]（期望值 ≈ -1/(n-1)）：正空間自相關（相似值聚集）
- I < E[I]：負空間自相關（相異值聚集）
- I ≈ E[I]：空間隨機

---

#### Local Moran's I (LISA) 局部空間自相關

**公式：**
- Local Iᵢ：`Iᵢ = zᵢ * Σⱼ wᵢⱼ zⱼ`
  - zᵢ = (xᵢ − x̄) / σ（標準化值）
  - Σⱼ wᵢⱼ zⱼ：空間滯後（鄰居的加權均值）

**分類（象限）：**
基於標準化值 zᵢ 和空間滯後（鄰居均值）的符號：
- **HH (High-High)**：高值被高值包圍（熱點）
- **LL (Low-Low)**：低值被低值包圍（冷點）
- **HL (High-Low)**：高值被低值包圍（高值離群）
- **LH (Low-High)**：低值被高值包圍（低值離群）
- **NS (Not Significant)**：p-value ≥ 0.05，不顯著

**顯著性檢驗：**
- 每個位置的 Iᵢ 使用 Monte Carlo 置換檢驗（999 次）
- 若 p-value < 0.05，分類有效；否則標記為 NS

**參數：**
- k：K 近鄰數（預設 k = 5）
- permutations：置換次數（預設 999）
- α = 0.05（顯著性水準）

