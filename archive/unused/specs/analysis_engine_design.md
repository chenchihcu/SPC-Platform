# SMT SPI / SPC 統計分析平台
## SPC Analysis Engine Design

# 1. 模組目標

SPC Analysis Engine 負責：
- SPI 量測資料統計處理
- 製程能力計算
- SPC 控制圖計算
- 空間分析
- 統計檢定
- 圖表資料輸出

此模組 **不處理 UI**，只負責資料分析與結果輸出。

公式與門檻之 **單一來源** 為 `docs/governance/SPC_RULES.md`；變更流程與 payload／圖表契約對齊見 **`docs/specs/spec_maintenance_and_alignment.md`** §5、§6。

# 2. 模組架構

```text
analytics
│
├── spc_engine.py
├── capability_engine.py
├── distribution_engine.py
├── spatial_engine.py
├── pareto_engine.py
├── comparison_engine.py
└── statistical_utils.py
```

# 3. 資料輸入

SPC Engine 接收 **經過 schema mapping 的 DataFrame**

### 必須欄位
```text
RefDes
BoardNo
MeasurementValue
```

### SPI 常見量測
```text
Volume
Area
Height
XOffset
YOffset
```

# 4. SPC Engine

檔案：
```text
spc_engine.py
```

## 4.1 控制圖類型
系統支援：
- I-MR Chart
- Xbar-R Chart
- Xbar-S Chart

## 4.2 I-MR Chart
適用於：
- SPI 單點量測
- 非分組資料

計算：
Mean
```text
CL = mean(X)
```

MR
```text
MR_i = |X_i - X_(i-1)|
```

Control Limits
```text
UCL = mean + 3 * sigma
LCL = mean - 3 * sigma
```

## 4.3 Out-of-Control Detection
偵測條件：
- 點超出 UCL
- 點低於 LCL

可擴充：
- Western Electric Rules

# 5. Capability Engine

檔案：
```text
capability_engine.py
```

## 5.1 計算指標
支援：
- Cp
- Cpk
- Pp
- Ppk

## 5.2 Cp
```text
Cp = (USL - LSL) / (6σ)
```

## 5.3 Cpk
```text
Cpk = min(
 (USL - μ) / (3σ),
 (μ - LSL) / (3σ)
)
```

## 5.4 Pp / Ppk
使用整體標準差。

# 6. Distribution Engine

檔案：
```text
distribution_engine.py
```

## 6.1 Histogram
輸出：
- bin edges
- frequency

## 6.2 Normal Distribution
計算：
```text
PDF(x) = normal distribution
```

## 6.3 Normality Test
支援：
- Shapiro-Wilk
- Anderson-Darling

# 7. Spatial Engine

檔案：
```text
spatial_engine.py
```

## 7.1 PCB Heatmap
輸入：
```text
X
Y
MeasurementValue
```

輸出：
- Heatmap grid
- Spatial density

## 7.2 Cluster Detection
可選：
- DBSCAN
- KMeans

用途：
- 異常聚集判斷

# 8. Pareto Engine

檔案：
```text
pareto_engine.py
```

## 8.1 計算
依類別統計：
```text
Category
Count
Percentage
Cumulative Percentage
```

# 9. Comparison Engine

檔案：
```text
comparison_engine.py
```

## 9.1 元件比較
分組：
```text
RefDes
PartType
Batch
```

輸出：
- group mean
- group variance
- boxplot data

# 10. Statistical Utils

檔案：
```text
statistical_utils.py
```

提供：
- mean
- std
- variance
- moving range
- outlier detection

# 11. 資料處理流程

```text
Raw CSV
   │
   ▼
Schema Mapping
   │
   ▼
Data Cleaning
   │
   ▼
SPC Engine
   │
   ├─ Control Chart
   ├─ Capability
   ├─ Distribution
   ├─ Pareto
   └─ Spatial Analysis
```

# 12. 錯誤處理

| 問題 | 處理 |
|----|----|
| 缺 RefDes | 無法關聯 |
| 缺量測值 | 無法統計 |
| σ = 0 | 能力分析無效 |
| 資料太少 | 停止 SPC |

# 13. 效能考量

系統必須支援：
```text
10k
50k
100k+
```

資料量。

優化方法：
- Pandas vectorization
- NumPy calculation
- caching

# 14. Engine 輸出格式

每個 engine 必須輸出 **統一資料結構**

```json
{
  "chart_type": "",
  "data": {},
  "statistics": {},
  "metadata": {}
}
```

# 15. 未來擴展

預留支援：
- AOI defect data
- Machine learning anomaly detection
- Multi-line SPC comparison
- Predictive process control
