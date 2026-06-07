# SMT SPI 圖表增強路線圖 (SMT Chart Enhancement Roadmap)

**分析日期**: 2026-03-17
**分析範圍**: 基於現有分析引擎，識別可新增的 SMT 相關圖表
**目標**: 為 SPC 分析平台補充缺失的製程診斷工具

---

## 📊 現狀分析

### 已實現的圖表（20 個）
```
單特徵 (7)：IMR, RunChart, Subgroup, RepeatedOffender, Histogram, Normality, Spatial
時間序列 (2)：EWMA, CUSUM
雙特徵 (4)：Scatter+Spec, Quadrant, BivariatOutlier, Density
三特徵 (4)：Anomaly3F, Consistency3F, ParallelCoord, PassFailMatrix
聚焦分析 (3)：Pareto, Boxplot/Comparison, 空間熱圖
```

### 已實現但未做成圖表的分析引擎

| 引擎 | 功能 | SMT 價值 | 建議圖表名 |
|------|------|--------|----------|
| TransferEfficiency | IPC-7525 TE、Area Ratio、釋放品質評級 | 🟢 HIGH | Transfer Efficiency Chart |
| RootCause | 根據 SPC 模式推斷根本原因 | 🟢 HIGH | Root Cause Dashboard / Hints Panel |
| Comparison | 足印間的箱線圖比較 | 🟡 MEDIUM | 已通過 ComparisonTab 實現 |
| SummaryEngine | 批次級統計摘要 | 🟡 MEDIUM | Batch Summary Report |

---

## 🎯 推薦新增圖表（優先順序）

### 🔴 優先級 1：轉移效率分析 (Transfer Efficiency Chart)

**現況**：
- ✓ TransferEfficiencyEngine 已實現
- ✗ 無對應圖表顯示 TE 分佈與品質評級

**SMT 業界需求**：
- IPC-7525 標準強制要求 TE ≥ 75%（可接受）或 ≥ 90%（優異）
- 直接影響焊點品質、製程能力評估
- 與 Volume 密切相關（TE = Volume% / 100）

**圖表內容**：
```
┌─ TE 直方圖 + 能力指標區間 (GOOD/ACCEPTABLE/MARGINAL/POOR)
├─ TE vs 板序趨勢線（偵測漂移）
├─ 統計卡片
│  ├─ TE Mean (目標 > 90%)
│  ├─ TE Std (低 = 穩定)
│  ├─ Release Quality Rating
│  └─ 與規格的合規性
└─ 建議值
   ├─ 理論体積 (theoretical_volume = stencil_thickness × aperture_area)
   ├─ Area Ratio (應 ≥ 0.66)
   └─ Pitch-to-Thickness 推薦
```

**需要的數據**：
```python
# 在 Workorder 規格中添加
"stencil_thickness_um": 100,      # 鋼板厚度（微米）
"aperture_area_mm2": 1.5,         # 孔徑面積（平方毫米）
"component_pitch_mm": 0.65,       # 元件間距（用於推薦檢查）
```

**實現複雜度**: 🟡 **中等**（引擎已有，只需添加 UI 呈現）

---

### 🔴 優先級 2：根本原因推斷儀表板 (Root Cause Hints Dashboard)

**現況**：
- ✓ RootCauseEngine 已實現（規則庫）
- ✗ 無專用 UI 面板展示推斷結果

**SMT 業界應用場景**：
- 錫膏乾涸 (Paste Drying)：Volume 沿板序下降 → 更換錫膏或增加噴霧
- 鋼板張力問題 (Stencil Tension)：OOS 聚集於邊緣 → 檢查鋼板安裝
- RefDes 間差異 (Component Type Effect)：某些足印方差過大 → 檢查孔徑設計
- 位置漂移 (Alignment Drift)：Area/Height 趨勢上升 → 檢查對位系統
- 擠壓量不穩 (Squeegee Pressure Variation)：高頻振動模式 → 調整壓力或速度

**圖表內容**：
```
┌─ 警告區 (Rules-based Hints)
│  ├─ 🔴 Critical: TE < 60% 或 多點 OOS
│  ├─ 🟡 Warning: 趨勢明顯 或 局部異常聚集
│  └─ ℹ️ Info: 製程變化提示
│
├─ 每個提示
│  ├─ Hint Text (製程診斷)
│  ├─ Confidence (推斷信心度)
│  ├─ Supporting Evidence (證據圖表連結)
│  └─ Recommended Action (建議動作)
│
└─ 文件化追蹤
   ├─ 問題編號 (rule_id)
   ├─ 時間戳 (何時偵測)
   └─ 操作員筆記
```

**需要的改動**：
- 在 chart_analysis_viewmodel.py 中調用 RootCauseEngine.infer_root_cause_hints()
- 創建 RootCausePanel UI 顯示提示列表
- 允許操作員點擊提示跳轉到支持圖表

**實現複雜度**: 🟡 **中等**（引擎邏輯已有，UI 集成）

---

### 🟡 優先級 3：多特徵相關性矩陣 (Multi-Feature Correlation Matrix)

**現況**：
- ✓ 雙特徵有 Scatter+Spec 和 Quadrant
- ✗ 三特徵相關性矩陣尚缺（視覺化 Volume-Area-Height 的相關性）

**SMT 業界應用**：
- 診斷 Volume 和 Area 是否同向變化（應該是）
- 識別異常關係：如 Volume 高但 Height 低 → 擠壓不足
- PCB 挑選：某些板位 3 參數相關性差 → 板質問題

**圖表內容**：
```
┌─ 相關係數矩陣 (3×3 Pearson Correlation)
│  Volume  | 1.00  |  0.85  |  0.72
│  Area    | 0.85  |  1.00  |  0.68
│  Height  | 0.72  |  0.68  |  1.00
│
├─ 熱力圖（顏色表示相關強度）
│  藍=正相關，紅=負相關，白=無關
│
├─ 散點矩陣 (pairwise scatter plots)
│  左下角：6 個 2D 散點圖
│  對角線：直方圖
│  右上角：相關係數值
│
└─ 統計檢驗
   ├─ p-value（顯著性）
   └─ 95% CI for correlation
```

**需要的分析**：
```python
# 新增引擎
class CorrelationMatrixEngine:
    @staticmethod
    def compute_correlation_matrix(df, features=["Volume", "Area", "Height"]):
        # 計算 Pearson correlation matrix
        # 計算 p-values
        # 準備 pairwise scatter 數據
```

**實現複雜度**: 🟡 **中等**（統計計算直接，需要 matplotlib 矩陣圖）

---

### 🟡 優先級 4：製程能力趨勢 (Process Capability Trend)

**現況**：
- ✓ 單點時刻的 Cpk 已有
- ✗ 縱向時間序列 Cpk 追蹤尚缺

**SMT 業界應用**：
- 監控製程是否逐漸惡化（Cpk 下降）
- 識別離散事件（Cpk 突然跳變）
- 長期製程改善驗證

**圖表內容**：
```
┌─ Cpk vs 板序 / 時間
│  Y 軸：Cpk 值（目標 > 1.33）
│  X 軸：板序或時間
│  圖表：折線圖 + 警告區（Cpk < 1.0 紅區、1.0-1.33 黃區、>1.33 綠區）
│
├─ Cp vs 批次（對比製程能力與居中性）
│
└─ 滑動平均線 (moving average)
   ├─ 原始 Cpk（灰線）
   ├─ 7-板滑動平均（藍線）
   └─ 趨勢線（紅線）
```

**需要的改動**：
- 修改 chart_registry 允許時序 Cpk 數據（類似 EWMA/CUSUM）
- 在 viewmodel 中累積多個時間點的 Cpk 值

**實現複雜度**: 🟡 **中等**（邏輯簡單，需要數據累積邏輯）

---

### 🟢 優先級 5：批次級品質摘要卡 (Batch Quality Summary Card)

**現況**：
- ✓ SummaryEngine 已實現概念
- ✗ 無專用 UI 卡片展示

**SMT 業界應用**：
- 生產巡檢：快速掌握批次整體品質（Go/No-Go）
- 異常報告：自動標記超規格或低能力批次
- 追蹤卡片化展示

**卡片內容**：
```
┌─────────────────────────────────────────────┐
│  批次 #2204156                              │
│  時間：2026-03-17 14:30 ~ 15:45            │
│  檢測點數：120                              │
├─────────────────────────────────────────────┤
│ Volume:  Cpk=1.42 ✓  |  Mean=102.5%  σ=3.2 │
│ Area:    Cpk=1.18 ⚠  |  Mean=98.1%   σ=4.1 │
│ Height:  Cpk=0.95 ✗  |  Mean=94.2%   σ=5.0 │
├─────────────────────────────────────────────┤
│ OOS Rate:    1.7% ✓   (目標 < 3%)          │
│ TE Quality:  ACCEPTABLE (87%)              │
│ 異常位置:    PCB 左邊界 (3 點 OOS)          │
├─────────────────────────────────────────────┤
│ 建議:  高度偏低，檢查擠壓壓力或鋼板磨損      │
│ 狀態:  🟡 需注意，建議下批調整              │
└─────────────────────────────────────────────┘
```

**實現複雜度**: 🟢 **簡單**（純展示，邏輯已有）

---

## 🛠️ 進階增強方向（未來）

### 可選的未來圖表

| 圖表 | SMT 應用 | 複雜度 | 建議時間 |
|------|--------|--------|---------|
| **Yield vs 參數關係** | 識別哪個參數與 Yield 最相關 | 🔴 HIGH | 6 個月+ |
| **孔徑設計驗證 (AOI 對標)** | 與 AOI 數據對標，驗證 SPI 代表性 | 🔴 HIGH | 6 個月+ |
| **隨機焊點分佈分析** | 分析焊點位置偏差對品質的影響 | 🔴 HIGH | 未來 |
| **多批次對標 (Benchmark)** | 批次間能力對標，跨月份趨勢 | 🟡 MEDIUM | 3 個月 |
| **預測性維護指標** | 基於 TE 和趨勢預測設備維護時機 | 🔴 HIGH | 未來 |
| **焊接可靠性模型** | 基於 Volume/Area/Height 預測不良率 | 🔴 HIGH | 未來 |

---

## 📋 實現檢查清單

### 第一階段（立即，1-2 週）

- [ ] **TransferEfficiency 圖表**
  - [ ] 在 chart_registry 添加 "te_chart" 條目
  - [ ] 在 chart_router 添加映射
  - [ ] 創建 TransferEfficiencyTab UI
  - [ ] 添加參數選擇器（同 7 個圖表模式）
  - [ ] 測試端到端數據流

- [ ] **根本原因提示面板**
  - [ ] 創建 RootCausePanel widget
  - [ ] 集成到 chart_analysis_page
  - [ ] 添加提示點擊 → 跳轉到支持圖表
  - [ ] 測試規則觸發

- [ ] **修復圖表重複問題** （前面報告）
  - [ ] 移除 "capability" chart_id
  - [ ] 刪除未使用的 Tab (BoxplotTab, ControlChartTab)

### 第二階段（1 個月）

- [ ] **多特徵相關矩陣**
  - [ ] 實現 CorrelationMatrixEngine
  - [ ] 創建 CorrelationMatrixTab
  - [ ] 支持三特徵分析選擇

- [ ] **製程能力趨勢圖**
  - [ ] 擴展數據累積邏輯
  - [ ] 創建 CapabilityTrendTab

### 第三階段（1.5 個月）

- [ ] **批次品質摘要卡**
  - [ ] 設計卡片 UI
  - [ ] 集成自動評級邏輯
  - [ ] 添加導出功能

---

## 💡 實現優先邏輯

### 推薦順序理由

1. **TransferEfficiency（優先 1）**
   - ✓ 引擎已完全實現
   - ✓ IPC-7525 業界標準要求
   - ✓ 直接影響產品出貨決策
   - ✓ 實現複雜度最低

2. **RootCause Hints（優先 2）**
   - ✓ 引擎已實現，規則已定義
   - ✓ 增加分析平台的診斷價值
   - ✓ 操作員最關心的「為什麼」

3. **相關性矩陣（優先 3）**
   - ✓ 增加多特徵分析價值
   - ✓ 現有 Scatter/Quadrant 的自然延伸
   - ✓ 幫助發現 3 個參數間的異常關係

4. **能力趨勢（優先 4）**
   - ✓ 簡化了的 EWMA/CUSUM
   - ✓ 製程長期監控必需

5. **摘要卡（優先 5）**
   - ✓ 純展示，實現最簡
   - ✓ 提升 UX 便利性

---

## 📈 預期效益

| 新增圖表 | 功能補缺 | 業界應用 | 用戶價值 |
|---------|---------|--------|---------|
| TE Chart | IPC-7525 合規 | 產品出貨決策 | 🟢 必需 |
| Root Cause | 診斷工具 | 製程持續改善 | 🟢 高價值 |
| Correlation | 多參數分析 | 異常診斷 | 🟡 增值 |
| CapTrend | 長期監控 | 趨勢警報 | 🟡 增值 |
| Summary Card | 快速掌握 | 巡檢時間節省 | 🟡 便利性 |

---

## ✅ 完整專案里程碑

```
目前         第一階段(1-2週)        第二階段(1月)      第三階段(1.5月)
│             │                      │                 │
20 圖表       20→23 圖表             23→25 圖表        25→26 圖表
(無 TE)       (+TE, RootCause)      (+Correlation)    (+CapTrend)
              (+修復重複)            (+去除死代碼)     (+Summary Card)
```

---

**簽核**: Claude Haiku 4.5 | 2026-03-17 | 根據現有分析引擎和 SMT 業界最佳實踐
