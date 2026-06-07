# 製程統計分析輸出 - Figma / UI 對齊規格

**狀態**：與 PySide6、Excel、PPTX 輸出同步的呈現層契約。  
**維護觸發**：變更 `DiagnosticPage` 欄位、`dashboard_layers_display` 顯示規則、Excel/PPTX 診斷摘要、或製程統計分析相關 token/QSS 時，需同步更新本文件。

## 1. 單一真實來源

| 面向 | 路徑 |
|------|------|
| 共用欄位順序、嚴重性、資料來源標籤 | `app/analytics/dashboard_layers_display.py::build_process_stat_report_sections` |
| 頁面結構與 `_fields` 更新 | `app/ui/pages/diagnostic_page.py` |
| 報告式欄位元件 | `app/ui/widgets/process_dashboard_cards.py` |
| 字級、間距、語意色 | `app/ui/theme/tokens.py`, `app/ui/theme/dark_stylesheet.py` |
| Excel 摘要頁 | `app/services/diagnostic_excel_exporter.py` |
| PPTX 摘要與診斷文字 | `app/services/pptx_report_builder.py` + `dashboard_layers_display` helper |

本契約只調整呈現層。`dashboard_layers` payload、`diagnostic_evidence_matrix` schema、chart ID、Cp/Cpk/OOC/OOS/Yield/DPMO 等統計公式不變。

## 2. 頁面結構

頁首標題為 **製程統計分析**。主內容以單一 `QFrame#processStatReport` 呈現，避免 1-7 多卡片堆疊造成報告輸出感不足；底部矩陣分頁維持 `secondaryTabs processMatrixTabs` 與原本表格行為。

閱讀順序固定：

1. `狀態 -> 製程狀態摘要`
2. `規格/能力 -> 製程能力統計`
3. `穩定性/資料範圍 -> 量測與缺陷透視`
4. `診斷與對策 -> 工程結論`
5. `背景 -> 工單與鋼網資訊`

每個欄位必須顯示資料來源 layer，例如 `layer_5_spec_analysis`、`layer_2_kpi`，讓 UI、Excel、PPTX 都能追溯同一個 payload 來源。

## 3. 欄位契約

| 順序 | 欄位群 | 代表欄位 | 來源 |
|------|--------|----------|------|
| 狀態 | 分析結論、問題類別、OOC、OOS、均值偏移、群集、驅動特徵 | `status_zh`, `issue_type`, `ooc_rate`, `oos_rate`, `shift`, `cluster`, `driver` | layer 1 / 3 / 5 / 8 |
| 規格/能力 | Cpk、Cp、能力判讀、USL、LSL、目標、均值、標準差、規格緊度 | `cpk`, `cp`, `judgment`, `usl`, `lsl`, `target`, `mean`, `std`, `tightness` | layer 5 / 7 |
| 穩定性/資料範圍 | Yield、DPMO、Sigma、樣本數、全距、異常型態、群聚係數、趨勢、Top RefDes、離群觀察 | `yield`, `dpmo`, `sigma`, `sample`, `range`, `pattern`, `cluster_ratio`, `drift_insight`, `top_ref`, `outlier` | layer 1 / 2 / 3 / 4 |
| 診斷與對策 | 優先級、問題型態、可能根因、建議工程對策 | `priority`, `type`, `cause`, `action` | layer 8 |
| 背景 | 產品、工單、批量、鋼網、厚度 | `product`, `supplier_wo`, `outsource_wo`, `batch_qty`, `stencil`, `thickness` | layer 6 |

## 4. 嚴重性規則

共用狀態 token：`good`, `warning`, `bad`, `neutral`。

| 狀態 | 用途 | 色彩 |
|------|------|------|
| `good` | 正常、規格內、能力足夠 | `ACCENT_SUCCESS` |
| `warning` | 監控區間、接近門檻、需觀察 | `ACCENT_WARNING` |
| `bad` | 超規、Cpk 不足、OOC/OOS 嚴重、需處置項 | `ACCENT_ERROR` |
| `neutral` | 一般背景資料、來源、描述性欄位 | `TEXT_SECONDARY` / 中性色 |

紅色只能用於超出規格範圍、Cpk 不足、嚴重 OOC/OOS 或需工程處置欄位。一般資料不可用紅色強調。

## 5. 字體與密度

| Token | 現行值 | 用途 |
|-------|--------|------|
| `FONT_SIZE_PROCESS_DASH_KPI` | 10 pt | 報告式欄位字級（與其他欄位一致） |
| `FONT_SIZE_PROCESS_DASH_KPI_MEDIUM` | 10 pt | 報告式欄位字級（與其他欄位一致） |
| `FONT_SIZE_PROCESS_DASH_STAT` | 10 pt | 一般統計欄位 |
| `FONT_SIZE_DASH_LABEL` | 10 pt | 欄位標籤 |

報告面板內的欄位標籤、數值與資料來源維持一致字級，不以大/小字形成視覺層級；嚴重性只用顏色與必要粗體區分。數值欄位維持 tabular/mono 風格；中文標籤使用既有 CJK 字體堆疊。欄位要可換行與壓縮，不能撐大頁面最小寬度，避免底部矩陣在窄版失去自己的水平捲動。

## 6. 輸出一致性

- UI：`DiagnosticPage` 使用 `processStatReport` 單一報告面板。
- Excel：`診斷摘要` sheet 使用同一套 section/row/state/source/meaning 表格；矩陣 sheets 保留原有白話判讀欄位。
- PPTX：製程狀態、能力、穩定性、診斷與背景文字由 `dashboard_layers_display` helper 產生；色彩使用 token-derived palette。

## 7. 修訂紀錄

| 日期 | 說明 |
|------|------|
| 2026-05-24 | 將「製程診斷」輸出重整為「製程統計分析」報告式版面：少容器、固定欄位順序、共用嚴重性與 UI/Excel/PPTX 對齊。 |
| 2026-04-06 | 初版書面交付；實作併入 `diagnostic_page.py`。 |
