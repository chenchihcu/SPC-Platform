---
name: qa-auto-engineer
version: 1.0.0
description: QA 自動工程師 — 自動從頭到尾操作 SPC/SPI Platform UI,擷取每頁截圖、發現視覺缺失、功能異常與效能問題,輸出結構化缺失報告。Use this skill 當使用者要做端對端 UI 測試、找介面 bug、產出 QA 缺失報告。觸發詞包含「QA 測試」「找問題」「掃描問題」「缺失報告」「端對端測試」「E2E」「defect report」。
---

# QA 自動工程師 — 端對端 UI 測試技能

自動從頭到尾操作 SPC/SPI Platform，發現視覺缺失、功能異常、效能問題，並輸出一份結構化的缺失報告。

## 觸發時機

用戶說任何以下詞語時啟動本技能：
- "QA 測試"、"自動測試"、"UI 測試"、"端對端測試"、"E2E"
- "找問題"、"找缺失"、"掃描問題"、"全面測試"
- "缺失報告"、"QA 報告"、"defect report"
- "像 QA 工程師一樣測試"

---

## 執行流程總覽

```
Phase 0: 準備環境
Phase 1: 啟動程式 + 初始畫面
Phase 2: 頁面巡迴（每頁截圖 + 分析）
Phase 3: 功能流程測試（上傳 → 分析 → 報告）
Phase 4: 彙整所有發現
Phase 5: 輸出缺失報告
```

---

## Phase 0 — 準備環境

1. 確認工作目錄為 `c:\Users\user\Documents\SPC Platform`。
2. 尋找可用的測試樣本資料（使用 Glob/Bash）：
   - 量測檔：`sample_data/measurement/test_meas.csv`
   - 座標檔：`sample_data/coordinate/test_coords.csv`
3. 在 `Outputs/` 目錄下建立本次 QA 工作目錄：
   ```
   Outputs/qa_report_YYYYMMDD_HHMM/
   ```
4. 初始化 **缺失清單**（空的 Python list，記錄過程中所有發現）。

---

## Phase 1 — 啟動程式

> **截圖機制（Opus 4.8 / 現行 harness）**：本 harness **沒有**桌面截圖 MCP（Playwright 只能驅動瀏覽器，無法截 PySide6 桌面視窗）。舊版引用的 `mcp__Claude_in_Chrome__computer` 已失效。改用**程式內 Qt 截圖**——直接在 Python 內建立 `MainWindow`、以其自身方法導頁、用 `QWidget.grab().save(path, "PNG")` 存圖。可參考既有腳本 `presentations/smt-spi-platform-overview/capture_ui_screenshots.py`。

```python
# 程式內截圖骨架（在 repo 根目錄執行）
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

app = QApplication(sys.argv)
from app.ui.main_window import MainWindow
w = MainWindow()
w.resize(1360, 820)
w.show()
app.processEvents()
QTest.qWait(400)                      # 等視窗初始化（事件迴圈，非 sleep）
w.grab().save("Outputs/qa_report_YYYYMMDD_HHMM/00_startup.png", "PNG")
```

- 用 `app.processEvents()` + `QTest.qWait(...)` 取代固定 `sleep`：等的是事件迴圈穩定，不是牆鐘時間。
- 導頁用 app 自身方法（如 `w._go_to_page(stack_idx)`），不要模擬滑鼠點擊座標。
- 儲存截圖為 `00_startup.png`，再用 **Read** 工具讀回該 PNG 做視覺分析。
- **分析啟動畫面**：
  - [ ] 視窗是否出現？（若無則記錄 CRIT-001：程式無法啟動）
  - [ ] 標題列文字是否完整、未截斷？
  - [ ] 左側導覽列是否可見？
  - [ ] 初始頁面（資料設定）是否正確顯示？

---

## Phase 2 — 頁面巡迴

對每一頁執行以下固定流程（程式內導頁，非滑鼠模擬）：
1. `w._go_to_page(stack_idx)` 切換至該頁
2. `app.processEvents()` + `QTest.qWait(~350ms)`（等渲染穩定，非固定 sleep）
3. `w.grab().save(path, "PNG")` 截圖
4. 用 **Read** 讀回 PNG，依該頁「檢查清單」逐項分析
5. 將發現加入缺失清單

### 2-1 資料設定頁（資料）

**截圖**：`01_data_setup.png`

**檢查清單**：
- [ ] 「量測資料」與「座標資料」兩個上傳區塊是否可見？
- [ ] 上傳按鈕文字是否完整（未截斷）？
- [ ] 有無任何按鈕、標籤文字以 `…` 結尾（文字被截斷）？
- [ ] 資料表格區域是否顯示佔位符或提示說明？
- [ ] 頁面整體佈局是否正常（無元件溢出或重疊）？

### 2-2 工單頁（工單）

**截圖**：`02_workorder.png`

**檢查清單**：
- [ ] 工單編號、產品名稱、料號、供應商輸入欄是否全部可見？
- [ ] Volume / Area / Height 的 USL / LSL / Target 欄位是否對齊？
- [ ] 「儲存」按鈕是否可見且文字完整？
- [ ] 欄位標籤有無文字截斷（`…`）？
- [ ] 欄位寬度是否足以容納典型輸入（如工單編號）？

### 2-3 診斷分析頁（製程診斷儀表板 / `DiagnosticPage`）

**截圖**：`03_diagnostic_dashboard.png`（舊流程名稱 `03_statistics.png` 可並存對照）

**檢查清單**：
- [ ] 左側導覽是否為「診斷分析」，頁首是否為製程診斷儀表板語意？
- [ ] 警報／KPI 等儀表板區塊是否可見（無資料時應有空狀態或提示，而非空白無標題）？
- [ ] 主要指標（如 Cpk、良率、OOC 等）欄位標籤是否完整、未截斷？
- [ ] 若無分析資料，是否有清楚的空狀態提示訊息？
- [ ] 頁面有無應顯示內容卻空白之區塊？

### 2-4 圖表分析頁（圖表）

**截圖**：`04_chart_main.png`

**檢查清單**（主頁面）：
- [ ] 圖表功能按鈕（高度 / 面積 / 體積）是否可見且文字完整？
- [ ] 分頁標籤（tab bar）是否全部可見？有無被截斷的標籤文字？
- [ ] 圖表區是否顯示空狀態提示（而非空白畫面）？

**對每個分頁再截圖並分析**（需逐一點擊）：
- `04a_tab_distribution.png` — 分佈與製程能力
- `04b_tab_control_chart.png` — 管制圖
- `04c_tab_normality.png` — 常態性
- `04d_tab_pareto.png` — 柏拉圖
- `04e_tab_boxplot.png` — 盒鬚圖
- `04f_tab_comparison.png` — 比較分析
- `04g_tab_spatial.png` — 空間分析

**每個分頁的通用檢查**：
- [ ] 分頁標題是否清楚可見？
- [ ] 圖表繪圖區是否正常大小（非極小或零高度）？
- [ ] 有無「NaN」、「None」、「null」文字直接暴露在 UI 中？
- [ ] 圖例文字是否完整？
- [ ] Y/X 軸標籤是否清楚？
- [ ] 參數選擇下拉（Volume / Area / Height ComboBox）是否存在且有選項？

### 2-5 報告輸出頁（報告）

**截圖**：`05_report.png`

**檢查清單**：
- [ ] 匯出選項是否可見？
- [ ] 按鈕文字是否完整？
- [ ] 有無錯誤訊息或警告橫幅？
- [ ] 頁面是否有足夠的說明文字引導用戶？

### 2-6 資料管理頁（參考）

**截圖**：`06_data_management.png`

**檢查清單**：
- [ ] 資料表格是否可見？
- [ ] 有無按鈕或操作元素，文字是否清楚？
- [ ] 頁面佈局是否完整、無異常空白？

---

## Phase 3 — 功能流程測試

執行一個完整的端對端操作流程，以發現**功能性**和**動態**問題。

### 3-1 上傳量測資料

1. 切換至「資料」頁。
2. 點擊量測資料上傳按鈕，選擇 `sample_data/measurement/test_meas.csv`。
3. 等待 **3 秒**。
4. 截圖 `10_after_meas_upload.png`。
5. **檢查**：
   - [ ] 狀態列是否顯示「資料載入成功」或類似訊息？
   - [ ] 量測資料表格是否出現預覽？
   - [ ] 有無錯誤對話框或狀態列錯誤？
   - [ ] 載入時間是否合理（< 5 秒）？

### 3-2 上傳座標資料

1. 點擊座標資料上傳按鈕，選擇 `sample_data/coordinate/test_coords.csv`。
2. 等待 **3 秒**。
3. 截圖 `11_after_coord_upload.png`。
4. **檢查**：
   - [ ] 座標資料預覽是否出現？
   - [ ] 控制面板的資料連線狀態是否更新？
   - [ ] 有無錯誤？

### 3-3 填寫工單資料

1. 切換至「工單」頁。
2. 在工單欄位填入測試值（使用鍵盤輸入）：
   - 工單編號：`TEST-QA-001`
   - 料號：`TEST-PART`
   - Volume USL/LSL/Target：`120 / 80 / 100`
   - Area USL/LSL/Target：`1.5 / 0.5 / 1.0`
   - Height USL/LSL/Target：`0.25 / 0.15 / 0.20`
3. 截圖 `12_workorder_filled.png`。
4. 點擊「儲存」。
5. 等待 **3 秒**。
6. 截圖 `13_after_workorder_save.png`。
7. **檢查**：
   - [ ] 儲存按鈕樣式是否變化（成功/失敗）？
   - [ ] 狀態列是否顯示確認訊息？

### 3-4 觸發分析

1. 切換至「圖表」頁（或點擊「重新整理分析」按鈕）。
2. 等待 **5 秒**（分析耗時）。
3. 截圖 `14_after_analysis.png`。
4. **檢查**：
   - [ ] 狀態列是否顯示「分析完成」？
   - [ ] 圖表是否從空狀態變為有資料的圖表？
   - [ ] 有無分析錯誤訊息？

### 3-5 分頁圖表驗證（有資料後）

依序點擊每個分頁，截圖並記錄：
- `15a_tab_dist_data.png` — 有資料的分佈圖
- `15b_tab_ctrl_data.png` — 有資料的管制圖
- `15c_tab_norm_data.png` — 有資料的常態性
- `15d_tab_pareto_data.png` — 有資料的柏拉圖
- `15e_tab_box_data.png` — 有資料的盒鬚圖
- `15f_tab_comp_data.png` — 有資料的比較圖
- `15g_tab_spatial_data.png` — 有資料的空間圖

**每個分頁額外檢查（有資料時）**：
- [ ] 圖表是否正常渲染（非空、非全黑、非全白）？
- [ ] 控制界限線（UCL/LCL）是否可見（管制圖）？
- [ ] 數值標籤是否重疊或超出邊界？
- [ ] 參數 ComboBox 切換後圖表是否更新？
- [ ] 右側根因分析面板是否顯示（若有）？

### 3-6 製程診斷儀表板驗證（診斷分析）

1. 切換至左側「**診斷分析**」（`DiagnosticPage`）。
2. 截圖 `16_diagnostic_with_data.png`（舊檔名 `16_statistics_with_data.png` 可並存對照）。
3. **檢查**：
   - [ ] 儀表板（`summary.process.dashboard_layers`）：警報／KPI／規格等區塊是否顯示數值或合理提示（非 NaN 裸露）？
   - [ ] Cp / Cpk 等指標是否顯示（依當前儀表板設計；可能為卡片而非單一表格）？
   - [ ] 文字是否未截斷、可讀？

---

## Phase 4 — 缺失分類與嚴重度評估

對每個發現的問題，指定：

| 欄位 | 說明 |
|---|---|
| **ID** | QA-XXX（流水號） |
| **頁面** | 發生的頁面或分頁名稱 |
| **類型** | 見下方類型清單 |
| **嚴重度** | CRITICAL / HIGH / MEDIUM / LOW |
| **描述** | 清楚描述問題現象 |
| **截圖** | 對應截圖檔名 |
| **建議修復** | 簡短的修復方向 |

### 問題類型清單

| 代碼 | 類型 | 說明 |
|---|---|---|
| `TRUNCATION` | 文字截斷 | 標籤、按鈕、標題文字以 `…` 結尾 |
| `LAYOUT` | 佈局異常 | 元件重疊、溢出、零高度、未對齊 |
| `LOAD_SLOW` | 載入過慢 | 操作後超過 5 秒仍無回應/無 UI 變化 |
| `LOAD_FAIL` | 載入失敗 | 資料無法載入，出現錯誤訊息 |
| `EMPTY_STATE` | 空狀態缺失 | 應有內容但顯示空白，無引導提示 |
| `DATA_CORRUPT` | 資料顯示異常 | NaN/None/null/錯誤值直接暴露 |
| `CHART_FAIL` | 圖表渲染失敗 | 圖表空白、全黑、不正常縮放 |
| `UI_FREEZE` | 畫面卡頓 | 點擊後 UI 無反應超過 3 秒 |
| `ERROR_MSG` | 錯誤訊息 | 意外出現錯誤對話框或狀態列錯誤 |
| `CONTRAST` | 視覺清晰度 | 文字與背景對比不足、字體過小 |
| `MISSING_UI` | 元件缺失 | 預期應有的按鈕/欄位/面板不存在 |
| `FUNCTIONAL` | 功能異常 | 按鈕點擊無效、流程中斷 |

### 嚴重度定義

- **CRITICAL**：程式崩潰、無法啟動、核心功能完全失效
- **HIGH**：主要功能受阻、資料錯誤、使用者無法完成流程
- **MEDIUM**：功能可用但體驗差，或有顯示異常
- **LOW**：視覺微調、文字優化、非關鍵改善

---

## Phase 5 — 輸出缺失報告

在 `Outputs/qa_report_YYYYMMDD_HHMM/` 目錄下建立 `QA_DEFECT_REPORT.md`。

### 報告格式

```markdown
# QA 缺失報告
**程式**：SPC/SPI Platform v2
**測試日期**：YYYY-MM-DD HH:MM
**測試執行者**：Claude QA 自動工程師
**測試範圍**：端對端 UI 測試（全流程）

---

## 執行摘要

| 項目 | 數量 |
|---|---|
| 截圖總數 | N |
| 測試頁面數 | 6 頁 + N 個分頁 |
| 發現問題總數 | N |
| CRITICAL | N |
| HIGH | N |
| MEDIUM | N |
| LOW | N |

**整體評估**：[Pass / Fail / Conditional Pass] — [一句話總結]

---

## 缺失清單

| ID | 頁面 | 類型 | 嚴重度 | 描述 |
|---|---|---|---|---|
| QA-001 | ... | ... | ... | ... |

---

## 詳細說明

### QA-001 — [問題標題]
- **頁面**：...
- **類型**：...
- **嚴重度**：...
- **現象**：詳細描述觀察到的問題
- **截圖**：`XX_screenshot.png`
- **重現步驟**：
  1. ...
  2. ...
- **建議修復**：...

---

## 未發現問題的頁面 ✅

以下頁面/功能測試通過，無明顯問題：
- ...

---

## 測試限制

- 本次為自動化視覺 + 功能測試，不涵蓋效能壓力測試
- 使用樣本資料，非生產資料
- 部分問題需人工確認（如印表/PDF 輸出）
```

---

## 執行注意事項

### 截圖工具使用

用**程式內 Qt 截圖**（`w.grab().save(path, "PNG")`，見 Phase 1），存檔後以 **Read** 工具讀回 PNG 做視覺分析。本 harness 無桌面截圖 MCP，勿引用已失效的 `mcp__Claude_in_Chrome__computer`。每次讀回截圖後：
1. 仔細觀察畫面的每一個細節
2. 檢查所有可見文字是否完整（無 `…`）
3. 檢查元件邊界是否正常
4. 記錄任何異常到缺失清單

### 文字截斷檢測重點

在截圖分析時，特別注意以下元素的文字是否被截斷：
- 左側導覽選單的步驟名稱
- 分頁標籤（Tab header）文字
- 按鈕文字
- 欄位標籤（Label）
- 表格欄位標題
- 下拉選單選項
- 狀態列訊息
- 對話框訊息

### 等待時間準則

> 這些是 `QTest.qWait()` 的**上限預算**搭配 `app.processEvents()`，不是固定 `time.sleep`。優先輪詢可觀察條件（狀態列文字、圖表已繪、worker `finished`），達標即往下；只有到上限仍無變化才視為逾時。

| 操作 | 建議等待時間 |
|---|---|
| 頁面切換 | 1 秒 |
| 檔案上傳 | 3–5 秒 |
| 分析觸發 | 5–10 秒 |
| 報告匯出 | 5–15 秒 |

若超過最長等待時間仍無回應 → 記錄為 `UI_FREEZE` 問題。

### 若程式無法啟動

記錄 CRITICAL 問題後，繼續執行靜態分析：
1. 讀取並分析所有頁面的 Python 源碼
2. 搜尋已知問題模式：
   - `setFixedWidth` / `setMaximumWidth` 可能造成截斷
   - `setElideMode` / `Qt.ElideRight` 截斷設定
   - `setText` 傳入 `str(None)` 或 `str(nan)`
   - 硬寫死的像素值可能在不同 DPI 下異常
3. 將靜態分析發現加入報告的「靜態代碼分析」區段

---

## 快速啟動指令

**首選：程式內驅動腳本**（可截圖、可分析）。將整個巡迴寫成一支腳本：建立 `MainWindow` → 逐頁 `_go_to_page` → `grab().save()`，輸出到 `Outputs/qa_report_*/`，再用 Read 讀回各 PNG 分析。範本見 `presentations/smt-spi-platform-overview/capture_ui_screenshots.py` 與 Phase 1 骨架。

```bash
# 以 repo 既有腳本快速產生基準截圖（headed 環境）
cd "c:\Users\user\Documents\SPC Platform"
python presentations/smt-spi-platform-overview/capture_ui_screenshots.py
```

> **不要**用 `subprocess.Popen` / `start python main.py` 外部啟動再期待截圖——本 harness 無桌面截圖 MCP，外部視窗無法被擷取分析。外部啟動僅適用於純粹確認「能否開起來」，且應改用 `python scripts/check_launch.py`（見 `run-spc` 技能）。
