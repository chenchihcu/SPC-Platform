# 文件對齊更新計畫（Document Alignment Patch Plan）

日期：2026-03-19

## 前提與範圍
本文件只提出「文件/計畫文字」層級的更新方向，用於讓 `.cursor/plans/*.md` 與目前程式碼現況保持一致。
- 不改程式碼。
- 不直接修該 plan 檔案；此處只提供可執行的 patch 指南，供你確認後再由 Agent 實作。

**通用治理準則**（何時歸檔、`needs-update`、權威來源）：見 **`docs/specs/spec_maintenance_and_alignment.md`** §2 與 §7。  
**新計畫擬定紀律**（避免假設架構、未盤點即寫「已落地」）：見 **`docs/plans/ai_change_and_planning_discipline.md`**、**`.cursor/plans/README.md`**。

## 歸檔策略（依你先前選定）
當計畫明顯已與目前實作落差很大，採取歸檔：在計畫檔頂部加入 `[ARCHIVED]` 註記，保留原內容並補上「目前狀態/對應現行程式/新建議方向」段落。

## 需要更新/歸檔的項目

### 1) `.cursor/plans/adaptive-toasting-ladybug.md` → 建議 `ARCHIVED`
原因（對照報告）：
- 計畫宣稱 SQLite DB（`spi_platform.db`、`init_db()`、`measurement_imports` 等）與「透明取代 JSON registry API」；但目前程式端 registry 仍為 JSON（`coordinate_registry.json`、`product_spec_registry.json`、`stencil_assignments.json`）。
- 計畫宣稱資料設定頁「全寬垂直三步驟 + 移除座標預覽表格」；但目前 UI 仍是兩欄 form template，且 `CoordinateManagerPage` 仍有 `座標預覽` 的 `QTableView`。
- 鋼板規格標題仍為「產品鋼板規格」，非「步驟二：產品鋼板規格」。

建議新增章節（patch 指南）：
1. 在檔案最上方加入 `[ARCHIVED]`。
2. 追加 `## 目前狀態（以程式碼為證據）`：
   - 持久化：引用 `app/data/coordinate_registry.py`、`app/data/product_spec_registry.py`、`app/data/stencil_assignment_registry.py`
   - UI：引用 `app/ui/pages/data_setup_page.py`、`app/ui/pages/coordinate_manager_page.py`、`app/ui/widgets/stencil_spec_editor.py`
3. 追加 `## 對應程式位置（閱讀與驗證）`：
   - 用條列列出三個對應程式路徑與一句話證據（例如座標預覽表格仍存在、兩欄骨架仍使用 setup_two_column_form_page）。
4. 追加 `## 下一步建議（新計畫方向）`：
   - 若仍要推 SQLite：建議新增一份「以目前架構為基底」的 DB 計畫（例如 `docs/sqlite-persistence-v2-plan.md` 或 `.cursor/plans/sqlite-persistence-v2_<hash>.plan.md`），並把落地點精準對準目前 JSON registry 與 DataSetupPage 的實作位置（例如先做 repository layer、再逐步替換 registry 模組）。

### 2) `.cursor/plans/data_setup_流程版面重排_4fc8f5e3.plan.md` → 建議 `needs-update`
原因（對照報告）：
- 計畫描述「scroll 內順序 coord → upload」，但目前 `DataSetupPage`：左欄 scroll 內是 coord + stencil_editor；upload_page 在右欄。

建議新增章節：
1. 追加 `## 目前狀態（程式端證據）`：
   - 引用 `app/ui/pages/data_setup_page.py`：標註 `_coord_page`/_stencil_editor 在 scroll、`_upload_page` 在右欄。
2. 追加 `## 與原計畫差異`：
   - 明確指出「閱讀流程雖可能在一次視窗同時可見，但不等同於 scroll 內 coord → upload」。
3. 追加 `## 更新方案（擇一）`（僅文字）：
   - 方案 A（最小 UI 變更）：保留兩欄 form template，但在視覺上新增 Step 指引或調整 card 分組，使使用者仍可按流程理解。
   - 方案 B（完全對齊原流程）：將 `DataUploadPage` 也放入同一個 scroll inner（使順序真為 coord → upload），並同步驗收「Tab order 不破壞既有連線/行為」。

### 3) `.cursor/plans/data-setup-single-page-2k-layout_b0a7ab96.plan.md` → 建議 `needs-update`
原因（對照報告）：
- 計畫目標「2K 下無整頁卷軸的一頁式/卡片化」；但目前實作仍為兩欄模板骨架 + 局部 QScrollArea。

建議新增章節：
1. 追加 `## 目前狀態（程式端證據）`：
   - 引用 `app/ui/pages/data_setup_page.py`：標註兩欄 form template 與局部 QScrollArea。
2. 追加 `## 仍待驗證事項`：
   - 若要主張「2K 下無整頁卷軸」，需增加具體驗收方式（例如在 2560×1440、縮放 100%/125%/150% 下，判定是否需要整頁捲動）。
3. 追加 `## 更新目標（避免承諾過度）`：
   - 將目標調整為「視覺上卡片化且降低整頁捲動」，而非一開始就宣稱完全不需要捲動。

## 已對齊項目（建議不動）
- `.cursor/plans/limit-preview-to-three-lines_c706c906.plan.md`：與程式目前 head(3)/lines[:3] 行為一致，標示 `ok`。
- `.cursor/plans/fix-typography-and-control-heights_814e6f04.plan.md`：dark_stylesheet 與 tokens 中已存在 stepTitle/sectionTitle/caption 等 min-height 相關規則，標示 `ok`。
- `.cursor/plans/spc-feature-mode-shortcuts_8f4b4281.plan.md`：圖表快捷按鈕與 main_window 映射一致，標示 `ok`。

## 本輪完成度說明
本輪已完成所有「明顯不一致」計畫檔的文字落地更新（SQLite/三步驟全寬/移除座標預覽/2K 無整頁捲動等高風險關鍵需求），並以 `docs/reports/document_alignment_report.md` 中的「全量關鍵字掃描結論」作為範圍錨點。

## 建議後續驗證（文件修訂完成後）
1. 對每個 `[ARCHIVED]` 或 `needs-update` 計畫，確保新章節中的證據引用路徑皆存在於目前程式碼。
2. 若計畫仍提出「下一步建議」新計畫，確保新計畫描述清楚「目前程式權威架構」而不是舊架構（避免再次出現 SQLite/JSON registry 或三步驟/兩欄骨架的落差）。

