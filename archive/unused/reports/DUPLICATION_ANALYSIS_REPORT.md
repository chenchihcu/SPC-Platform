# 圖表重複分析報告 (Chart Duplication Analysis)

**分析日期**: 2026-03-17
**分析者**: Claude Haiku 4.5
**狀態**: ⚠️ **發現重複實現**

---

## 📋 執行摘要

深度檢查發現**有2種圖表存在重複或冗餘實現**：

| # | 問題 | 嚴重程度 | 詳情 |
|---|------|--------|------|
| 1 | **histogram_spec + capability 共用同一個 Tab** | 🔴 HIGH | 兩個不同的 chart_id 映射到同一個 DistributionCapabilityTab，造成混淆 |
| 2 | **BoxplotTab 實現了但未被使用** | 🟡 MEDIUM | 我們為 BoxplotTab 添加了參數選擇器，但 chart_analysis_page.py 只使用 ComparisonTab |

---

## 🔍 深度分析

### 問題 1: Histogram & Capability 重複

**位置**: `app/ui/pages/chart_analysis_page.py`, lines 239-242

```python
if chart_id == "histogram_spec":
    return DistCapPageWrapper(DistributionCapabilityTab(self), self)
if chart_id == "capability":
    return DistCapPageWrapper(DistributionCapabilityTab(self), self)  # ⚠️ 同一個 Tab!
```

**映射關係** (來自 chart_registry.py):

| chart_id | payload_key | 名稱 |
|----------|------------|------|
| histogram_spec | ("dist", "cap") | 分布與能力（Histogram & Capability） |
| capability | ("dist", "cap") | 製程能力分析（Capability） |

**問題**:
- 兩個不同的 chart_id（`histogram_spec` 和 `capability`）都映射到 **同一個 payload_key** `("dist", "cap")`
- 兩個都返回 **同一個 DistributionCapabilityTab 實例**
- 用戶在圖表清單上會看到 2 個看起來不同的選項，但實際上打開的是同一個圖表
- 這造成**UI 冗餘和用戶困惑**

**建議修復**:
- **選項 A（推薦）**: 保留 `histogram_spec`，移除 `capability` 圖表（或反過來）
- **選項 B**: 創建兩個略微不同的實現，展示不同的聚焦（一個強調分布，一個強調能力指數）

---

### 問題 2: BoxplotTab 實現但未被使用

**位置**:
- `app/ui/tabs/boxplot_tab.py` - **存在並已實現參數選擇器**
- `app/ui/pages/chart_analysis_page.py`, line 243-244 - **只使用 ComparisonTab**

```python
if chart_id == "boxplot":
    return ComparisonTab(self)  # ⚠️ 沒有使用 BoxplotTab!
```

**為什麼我們實現了 BoxplotTab？**

看起來用戶需求是：
> "箱型圖有一個設計足印 (Part Type)... 我想評估是否每一種圖表都適用此設計..."

所以我們在所有 7 個圖表上添加了參數選擇器（包括 BoxplotTab），但實際上：
- **ComparisonTab** = Boxplot + 足印/參數選擇（完整功能）
- **BoxplotTab** = 只有參數選擇，沒有足印選擇（簡化版本）

由於 ComparisonTab 提供更完整的功能，chart_analysis_page.py 只實例化 ComparisonTab。

**結論**: BoxplotTab 成為**死代碼**（dead code）。

---

## 📊 圖表使用分佈分析

### 實際被使用的 7 個單特徵圖表

```
chart_id          → Page/Tab 實例化                         → 數據來源
─────────────────────────────────────────────────────────────────
1. imr            → ImrHistogramSplitPage (特殊頁面)       ✓ 使用
2. histogram_spec → DistributionCapabilityTab               ✓ 使用
3. capability     → DistributionCapabilityTab (同上!)      ⚠️ 重複
4. normality      → NormalityTab                            ✓ 使用
5. pareto         → ParetoTab                               ✓ 使用
6. boxplot        → ComparisonTab (不是 BoxplotTab!)       ✓ 使用
7. spatial_heatmap→ SpatialTab                              ✓ 使用
```

### 我們實現參數選擇器的 7 個圖表

```
我們實現的 Tab                 → 實際使用情況
─────────────────────────────────────────────
1. DistributionCapabilityTab  ✓ 被 histogram_spec + capability 使用
2. ControlChartTab            ✗ 未被 chart_analysis_page.py 使用！
3. NormalityTab               ✓ 被 normality 使用
4. ParetoTab                  ✓ 被 pareto 使用
5. BoxplotTab                 ✗ 未被使用（ComparisonTab 被使用）
6. ComparisonTab              ✓ 被 boxplot 使用
7. SpatialTab                 ✓ 被 spatial_heatmap 使用
```

**發現**:
- **ControlChartTab** - 我們實現了但沒有在 chart_analysis_page.py 中使用！
- **BoxplotTab** - 同樣的問題

---

## 🎯 核心發現

### 第一層問題：名字混淆
"控制圖表（Control Chart Tab）" 實際上是什麼？
✅ 答案: IMR 圖 (I-MR Chart) —— 但它由 **ImrHistogramSplitPage** 處理，不是我們實現的 ControlChartTab

### 第二層問題：未使用的實現

| Tab | 位置 | 參數選擇 | 使用情況 |
|-----|------|---------|--------|
| ControlChartTab | `app/ui/tabs/control_chart_tab.py` | ✓ 已實現 | ✗ **未被使用** |
| BoxplotTab | `app/ui/tabs/boxplot_tab.py` | ✓ 已實現 | ✗ **未被使用** |

**為什麼未被使用？**
- `chart_analysis_page.py` 的 `_make_page()` 方法沒有實例化這些 Tab
- 它們可能是為了未來擴展而實現，但現在是死代碼

---

## 💡 建議修復清單

### 優先級 1（立即修復）
- [ ] **移除 `capability` 圖表** —— 它與 `histogram_spec` 完全重複
  - 選項：在 chart_registry.py 中移除 capability 條目
  - 或在 chart_router.py 中移除 "capability" 映射

### 優先級 2（程式碼清理）
- [ ] **移除未使用的 ControlChartTab 和 BoxplotTab** —— 或明確地在 chart_analysis_page.py 中使用它們
  - 如果未來不需要，刪除這兩個文件
  - 如果將來需要，添加到 `_make_page()` 方法中

### 優先級 3（驗證）
- [ ] 驗證是否有其他地方實例化 ControlChartTab 或 BoxplotTab（現在沒有）
- [ ] 確認參數選擇器實現是否應該保留在 ComparisonTab 但不在 BoxplotTab

---

## 📈 統計

### 重複/冗餘實現

```
項目                              | 數量 | 狀態
──────────────────────────────────┼─────┼──────────
實現的 Tab 類                       | 7   | ✓
在 chart_analysis_page 中使用的    | 5   | ✓
未被使用但已實現的 Tab            | 2   | ⚠️
重複的 chart_id（同一個 Tab）      | 1   | 🔴
```

### 参数选择器實現進度

```
Tab 名稱                      | 參數選擇 | 使用情況
──────────────────────────────┼────────┼──────────
DistributionCapabilityTab     | ✓ 已實現 | ✓ 被使用
ControlChartTab               | ✓ 已實現 | ✗ 未使用
NormalityTab                  | ✓ 已實現 | ✓ 被使用
ParetoTab                     | ✓ 已實現 | ✓ 被使用
BoxplotTab                    | ✓ 已實現 | ✗ 未使用
ComparisonTab                 | ✓ 已實現 | ✓ 被使用
SpatialTab                    | ✓ 已實現 | ✓ 被使用
```

---

## ✅ 最終結論

### 實現的 7 個圖表中存在問題：

1. **`histogram_spec` + `capability` 重複**: 兩個 chart_id，一個 Tab —— **需要合併或移除之一**
2. **`ControlChartTab` 實現但未使用**: 死代碼 —— **需要移除或連接到 chart_analysis_page.py**
3. **`BoxplotTab` 實現但未使用**: ComparisonTab 包含所有功能 —— **建議移除，保留 ComparisonTab**

### 建議的清理方案：

✅ **保留 5 個實際被使用的 Tab**:
1. DistributionCapabilityTab (histogram_spec)
2. NormalityTab
3. ParetoTab
4. ComparisonTab (boxplot)
5. SpatialTab

❌ **移除或重構 2 個未使用的 Tab**:
- ControlChartTab → IMR 圖表由 ImrHistogramSplitPage 處理
- BoxplotTab → 功能被 ComparisonTab 完全包含

❌ **移除重複的 chart_id**:
- `capability` —— 與 `histogram_spec` 使用同一個 Tab

---

## 📝 行動項目

```
待辦項目                          | 優先級 | 預期時間
──────────────────────────────────┼────────┼──────────
1. 在 chart_registry 移除 capability | HIGH   | < 5 min
2. 在 chart_router 移除 capability   | HIGH   | < 5 min
3. 測試確認刪除不影響功能            | HIGH   | < 10 min
4. 刪除或存檔 BoxplotTab             | MEDIUM | < 5 min
5. 刪除或存檔 ControlChartTab        | MEDIUM | < 5 min
6. 驗證所有 7 個圖表的參數選擇器      | HIGH   | < 10 min
```

---

**簽核**: Claude Haiku 4.5 | 2026-03-17 | 深度分析完成
