# 文件對齊稽核報告（Document Alignment Audit）

日期：2026-03-19

## 目的
針對目前程式碼實作狀態，對照本專案中的設計/規格文件（`docs/`、根目錄 `.md`）與大量迭代計畫（`.cursor/plans/*.md`），找出「明顯不一致」的項目，並以程式碼證據標註狀態。

**相關治理索引**：必須更新規格時的通用觸發條件、計畫檔生命週期與驗收寫法，已彙整於 **`docs/specs/spec_maintenance_and_alignment.md`**。

## 證據優先原則
- 以程式碼為權威來源。
- 只要計畫明確宣稱某功能已落地（例如 SQLite/DB、三步驟全寬排版、移除座標預覽表格），就必須在程式端找到對應實作證據；否則標示為 `needs-archive` 或 `needs-update`。

## 本次納入的「高信心候選」清單
本次為確保聚焦，先以你提供的「檢查點關鍵字」鎖定候選計畫，並搭配已明確可定位的 UI/資料持久化程式碼做對照。

候選計畫（`.cursor/plans/*.md`）：
- `adaptive-toasting-ladybug.md`
- `data_setup_流程版面重排_4fc8f5e3.plan.md`
- `data-setup-single-page-2k-layout_b0a7ab96.plan.md`
- `limit-preview-to-three-lines_c706c906.plan.md`
- `fix-typography-and-control-heights_814e6f04.plan.md`
- `spc-feature-mode-shortcuts_8f4b4281.plan.md`

候選 UI/持久化程式碼（證據來源）：
- 持久化 registry（仍為 JSON）：`app/data/coordinate_registry.py`、`app/data/product_spec_registry.py`、`app/data/stencil_assignment_registry.py`
- 資料設定頁排版：`app/ui/pages/data_setup_page.py`
- 座標預覽表格：`app/ui/pages/coordinate_manager_page.py`
- 鋼板規格標題：`app/ui/widgets/stencil_spec_editor.py`
- 預覽三行策略：`app/ui/pages/data_setup_page.py`、`app/ui/pages/data_upload_page.py`、`app/ui/pages/coordinate_manager_page.py`、`app/ui/pages/report_export_page.py`
- 特徵快捷：`app/ui/pages/chart_analysis_page.py`、`app/ui/main_window.py`

## 狀態總表
| 類型 | 檔案 | 狀態 | 主要原因（概述） |
|---|---|---|---|
| Plan | `.cursor/plans/adaptive-toasting-ladybug.md` | `needs-archive` | 內容宣稱 SQLite DB + 三步驟全寬 + 移除座標預覽；目前程式仍是 JSON registry，且座標預覽表格與兩欄骨架仍存在。 |
| Plan | `.cursor/plans/data_setup_流程版面重排_4fc8f5e3.plan.md` | `needs-update` | 計畫期待 scroll 內順序 coord → upload；目前 `DataSetupPage` 是左欄 scroll（含 coord + 鋼板編輯）+ 右欄 upload。 |
| Plan | `.cursor/plans/data-setup-single-page-2k-layout_b0a7ab96.plan.md` | `needs-update` | 計畫目標「2K 下無整頁卷軸的一頁式/卡片化」；目前仍是兩欄 form template 骨架 + 局部 QScrollArea。 |
| Plan | `.cursor/plans/limit-preview-to-three-lines_c706c906.plan.md` | `ok` | 量測/座標/報告預覽皆使用 head(3) 或前 3 行。 |
| Plan | `.cursor/plans/fix-typography-and-control-heights_814e6f04.plan.md` | `ok` | QSS 與 tokens 中已有 stepTitle/sectionTitle/caption 與 min-height 規則，且程式碼使用既有 class/樣式模式。 |
| Plan | `.cursor/plans/spc-feature-mode-shortcuts_8f4b4281.plan.md` | `ok` | 圖表頁頂部特徵快捷與模式切換已存在，主視窗也有快捷映射與 refresh。 |

## 全量關鍵字掃描結論（本輪）
為了降低逐檔人工審查成本，本輪使用「需求關鍵字」做全量掃描（`.cursor/plans/` 與 `docs/`）：
- SQLite/DB 落地（`spi_platform.db`、`init_db()`、`measurement_imports`、`WAL`、`schema_version` 等）：僅 `adaptive-toasting-ladybug.md` 觸發不一致條件，且已按歸檔策略完成更新。
- 資料設定頁全寬垂直三步驟、移除座標預覽表格、鋼板規格步驟二標題：僅 `adaptive-toasting-ladybug.md` 觸發不一致條件，且已歸檔並補上「目前狀態」與「對應程式」段落。
- 2K 無整頁捲動：僅 `data-setup-single-page-2k-layout_b0a7ab96.plan.md` 觸發不一致條件，且已按 needs-update 策略補上「目前狀態/仍待驗證事項/更新目標」。

因此，本輪實作層級的 document alignment 主要集中在上述三份 plan，其餘文件沒有再命中這些高風險關鍵字；若你希望進一步做到「所有 plan 均以證據驗證 ok/needs-update」，需要第二輪逐檔驗證（尤其是純 UI 改版與側欄/密度/文案計畫）。

## 詳細說明與程式碼證據

### 1) `.cursor/plans/adaptive-toasting-ladybug.md`：`needs-archive`
計畫宣稱（摘要）：
- 建立 SQLite：`data/spi_platform.db`、`init_db()`、`measurement_imports` 等。
- 「資料設定」頁改為全寬垂直三步驟排版，並移除座標預覽表格。

程式端證據（目前狀態）：
- 持久化仍是 JSON registry，而非 SQLite DB：
  - `app/data/coordinate_registry.py` 直接讀寫 `data/coordinate_registry.json`
  - `app/data/product_spec_registry.py` 直接讀寫 `data/product_spec_registry.json`
  - `app/data/stencil_assignment_registry.py` 直接讀寫 `data/stencil_assignments.json`
- UI 仍為兩欄 form template 骨架，座標預覽表格仍存在：
  - `app/ui/pages/data_setup_page.py` 使用 `setup_two_column_form_page(...)`；QScrollArea 包住左欄內容，`DataUploadPage` 放右欄。
  - `app/ui/pages/coordinate_manager_page.py` 仍包含 `QLabel("座標預覽：")` 與 `QTableView`。
- 鋼板規格區塊標題仍為「產品鋼板規格」，未符合「步驟二：產品鋼板規格」的計畫宣稱：
  - `app/ui/widgets/stencil_spec_editor.py` 使用 `QLabel("產品鋼板規格")`

結論：
該計畫已與目前程式現況產生明顯落差，建議歸檔並改用「新的、能描述目前架構的 DB/排版落地計畫」。

### 2) `.cursor/plans/data_setup_流程版面重排_4fc8f5e3.plan.md`：`needs-update`
計畫宣稱（摘要）：
- 期望 `DataSetupPage` scroll 內順序為：Step 1（依產品載入座標）→ Step 2（座標檔管理）→ Step 3（上傳量測資料），且只調整 UI 結構與版面順序，不改 signal/slot。

程式端證據（目前狀態）：
- `app/ui/pages/data_setup_page.py`：
  - scroll 內順序是：`_coord_page`（座標頁）→ `_stencil_editor`（鋼板規格）
  - `_upload_page`（上傳量測）是右欄元件（不在同一個 scroll 內）

結論：
「閱讀/操作順序」在視覺上無法等同於計畫要求的 scroll 內 coord → upload；需更新計畫敘述或調整落地策略。

### 3) `.cursor/plans/data-setup-single-page-2k-layout_b0a7ab96.plan.md`：`needs-update`
計畫宣稱（摘要）：
- 2K 下「無整頁卷軸」的一頁式布局與卡片化，並保留既有邏輯不變。

程式端證據（目前狀態）：
- `app/ui/pages/data_setup_page.py` 仍使用 `setup_two_column_form_page(...)` 兩欄骨架，且包含局部 `QScrollArea`（並非完全不需要捲動的單一一頁式卡片化）。

結論：
若目標仍是「2K 下無整頁捲動」，則該計畫需更新落地做法與驗收方式（目前實作尚不足以宣稱達成）。

### 4) `.cursor/plans/limit-preview-to-three-lines_c706c906.plan.md`：`ok`
計畫宣稱（摘要）：
- 預覽區塊統一只顯示前三行/前三列，不破壞匯出與分析主流程。

程式端證據（目前狀態）：
- 量測預覽：
  - `app/ui/pages/data_setup_page.py`：`update_meas_display` 依 `meas_meta` 更新 `lbl_path`（無內嵌表格）
  - `app/ui/pages/data_upload_page.py`：選檔後僅更新路徑並發送 `meas_uploaded`，不讀檔預覽
- 座標預覽：
  - `app/ui/pages/coordinate_manager_page.py`：載入 CSV 後以 Schema 驗證更新 `lbl_path`（無預覽表格）
- 報告預覽：
  - `app/ui/pages/report_export_page.py`：`preview_lines = lines[:3]` 並寫入 `self.text_preview`

結論：
計畫與目前實作一致，標示為 `ok`。

### 5) `.cursor/plans/fix-typography-and-control-heights_814e6f04.plan.md`：`ok`
計畫宣稱（摘要）：
- 用 tokens/QSS 統一字型、控件高度與間距，修正高 DPI 下的裁切/基線錯位，並統一 DataSetup/CoordinateManager/Upload 等頁面的 Step/Caption 類別。

程式端證據（目前狀態）：
- `app/ui/theme/dark_stylesheet.py` 中已定義 `QLabel[class="stepTitle"]`、`QLabel[class="sectionTitle"]`、`QLabel[class="caption"]`、以及多處 `min-height: {LABEL_ROW_MIN_HEIGHT}/{INPUT_MIN_HEIGHT}/{SECTION_TITLE_MIN_HEIGHT}` 的 token 化規則。

結論：
本計畫主要屬「設計系統/樣式層落地」，目前已有明顯對應實作證據，因此標示 `ok`。

### 6) `.cursor/plans/spc-feature-mode-shortcuts_8f4b4281.plan.md`：`ok`
計畫宣稱（摘要）：
- 圖表頁頂部加入特徵模式切換與高度/面積/體積快捷按鈕，維持既有分析流程與圖表佈局不變。

程式端證據（目前狀態）：
- `app/ui/pages/chart_analysis_page.py`：存在 `btn_feature_height` 等快捷按鈕並連到 `_on_feature_shortcut_clicked`
- `app/ui/main_window.py`：已提供快捷映射 `_on_feature_shortcut_clicked`，並呼叫 `_schedule_refresh_analysis`

結論：
與目前實作一致，標示 `ok`。

## 未納入但可能需要二輪掃描的項目
- 目前僅先針對與你指定檢查點高度相關的計畫做「落地對照」。若你希望全面掃描所有 `.cursor/plans/*.md`（66+ 檔）逐一判定，下一步可以擴到關鍵字批量索引並補齊未知狀態。

## 預防類似問題再發生（規則化）

本報告所列 **needs-archive**／**needs-update** 案例，已萃取為通用紀律，見：

- **`docs/plans/ai_change_and_planning_discipline.md`** — 過期計畫與失敗模式對照表、計畫 Preflight、根因優先、關聯模組／爆炸半徑。
- **`docs/governance/AGENTS.md` §13** — 執行摘要（禁止假設性跨改、計畫範本 `.cursor/plans/README.md`）。
- **`.cursor/rules/ai-planning-and-root-cause.mdc`** — Cursor 編輯計畫檔時之簡要規則。

