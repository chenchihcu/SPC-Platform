# SPI 製程統計分析

## 系統架構說明 (Current Architecture Snapshot)

本文件描述 **2026-05-24 現行主線** 的可驗證架構（以程式碼與 `docs/decision-log.md` 為準）。

若架構、資料契約、輸出契約有變更，必須同步更新：
- `docs/specs/spec_maintenance_and_alignment.md`
- `docs/specs/data_contract.md`
- `docs/specs/ui_design_spec.md`
- `docs/decision-log.md`

# 1. 系統概述

本系統為 SPI 製程統計分析桌面工程分析平台，核心目標：
- SPI 量測資料分析與視覺化
- SPC 與能力指標計算（依 `docs/governance/SPC_RULES.md`）
- 座標關聯與空間分析
- 工程報告輸出（PPTX-only，`engineering`）

# 2. 技術組成

| 元件 | 技術 |
|-----|-----|
| UI Framework | PySide6 |
| Data Processing | Pandas |
| Statistical Calculation | NumPy / SciPy |
| Chart Rendering | Matplotlib（含 chart class 分層） |
| Optional Chart Utility | PyQtGraph（相依保留） |
| Storage / Inputs | CSV + SQLite master-data (`data/spc_master.db`) + in-memory SessionStore cache |
| Testing / Quality | pytest / ruff / mypy（設定於根目錄 `pyproject.toml` 之 `[tool.*]`） |

# 3. 分層架構（現行）

```text
main.py
  -> app.ui.main_window.run_app()
      -> MainWindow (UI shell + worker lifecycle)
          -> AnalysisOrchestrator (analysis preflight/cache decision)
          -> ChartAnalysisViewModel (payload computation)
          -> app.analytics.chart_registry (contract & routing)
          -> app.analytics.* (domain engines)
          -> app.charts.* (chart rendering classes)
          -> ReportService (export orchestration)
```

## 3.1 目錄與責任

```text
app/
  analytics/    # domain/stat engines + chart registry contract (single source)
  bootstrap/    # app config, DPI scaling, runtime env/font initialization
  assets/fonts/ # bundled runtime CJK font assets (OFL)
  charts/       # BaseChart + concrete Matplotlib chart draw logic
  data/         # loader/mapping/relation/validator/session store + SQLite master-data registry
  services/     # orchestration/import/report; multi_signal_diagnosis; knowledge engines
  ui/           # main window, pages, tabs, widgets, theme, state models
  utils/        # constants, dataframe helpers, IO, and logging utilities
  viewmodels/   # UI-binding and payload assembly
docs/
  governance/   # governance + SPC rule authority (formula source)
  specs/        # UI/data/architecture/workflow contracts
  reports/      # audits and verification reports (snapshots)
  plans/        # implementation and execution plans
```

# 4. UI 架構

主介面為混合導航兩欄式：
- 左欄：`CollapsibleSidebar`（可見 `NavigationPanel` 流程導覽、全域篩選、特徵快捷、下一步、重新分析）
- 右欄：`QTabWidget#workflowTabs` 內部頁面容器（保留 6 個 workflow page mapping，但 tab bar 隱藏）

主視窗尺寸由 `app/ui/theme/layout_policy.py` 的共用 helper 控制：新開視窗依目前螢幕可用工作區置中，現行初次開啟使用 `0.93` 可用區比例；`fit_top_level_to_available(...)` 同時套用於解讀、匯出確認與資料庫編輯對話框；從 `QSettings` 還原的幾何若離屏或超出工作區，會重設為安全尺寸後再建立 splitter 配比。

`DataSetupPage`（資料頁）目前為一頁式三步驟整合流程；主內容改為量化表格布局：工單列跨欄，座標區在左欄跨兩列，鋼板規格與量測區在右欄上下排列。`DataSetupLayoutBudget` 保留最新 `content_width/content_height`、左右欄寬、工單列高度、主內容高度與右側上下區高度；UI diagnostics snapshot 會輸出該 budget 供實機視窗/DPI 驗證。表格布局只將基準最小值套回 Qt layout，避免診斷預算把頁面撐出 `1280x752` / `1200x700` 等可用區。
其中工單主檔輸入採雙欄位契約：`supplier_work_order_no`（供應商製令工單）與 `outsource_work_order_no`（醫電製令工單）；舊 `work_order_no` 僅保留相容鍵且寫入固定空字串，`batch_no` 仍作相容回填，不再作為主要輸入來源。

## 4.1 堆疊頁與左側流程導覽（權威：`app/ui/main_window.py`）

**堆疊順序 `STACK_ORDER`**（索引 0..6）：
| 索引 | 頁名 | 類別／說明 |
|------|------|------------|
| 0 | 資料 | `DataSetupPage`（整合座標、工單、量測匯入） |
| 1 | 量測 | `ComponentSelectPage`（元件／量測特徵選定；**不顯示於可見流程導覽**，多由圖表頁切換進入） |
| 2 | 圖表 | `ChartAnalysisPage`（管制圖與統計分析） |
| 3 | 報告 | `ReportExportPage`（工程 PPTX） |
| 4 | 參考 | `DataManagementPage`（說明與參考資料） |
| 5 | 診斷 | `DiagnosticPage`（製程統計分析報告輸出，整合 Alarm/KPI、規格能力、組合矩陣與證據矩陣） |
| 6 | 量測庫 | `MeasurementLibraryPage`（SQLite 主資料庫查詢與載入） |

**可見流程導覽 `VISIBLE_WORKFLOW_TABS`**（Nav 0..5）：
- `資料設定` (Tab 0 -> Stack 0)
- `資料庫` (Tab 1 -> Stack 6)
- `統計圖表` (Tab 2 -> Stack 2)
- `診斷` (Tab 3 -> Stack 5)
- `報告匯出` (Tab 4 -> Stack 3)
- `說明` (Tab 5 -> Stack 4)

`NAV_TO_STACK = [0, 6, 2, 5, 3, 4]` 為左側流程導覽映射。`TAB_TO_STACK = [0, 6, 2, 5, 3, 4]` 保留給內部 `QTabWidget#workflowTabs` 頁面容器與既有快捷鍵相容；tab bar 不顯示。相較於舊版，`WorkorderPage` 已整合至 `DataSetupPage`，且 `量測` 頁仍保留為內部頁面。

側欄可尋性契約：左欄只放跨頁流程與全域分析控制，不承載表單內選檔/儲存/管理按鈕，也不承載資料表列操作。若側欄密度不足，優先收合分析條件，而不是加入更多側欄 action；流程導覽與 `下一步` / `重新分析` 必須保持可辨識。

製程統計分析輸出之 Figma／欄位對齊：`docs/specs/process_dashboard_figma_alignment.md`（實作：`app/ui/pages/diagnostic_page.py`）。

# 5. 分析執行流程（Orchestrated Pipeline）

## 5.1 資料前處理

`app/services/import_service.py::DataLoaderWorker` 負責：
- 讀取量測 / 座標資料
- 執行 join（`JoinEngine`）
- 寫入 `SessionStore` metadata（資料有效性、relation 狀態）

## 5.2 分析前置與快取

`app/services/analysis_orchestrator.py::AnalysisOrchestrator.prepare_refresh()` 統一處理：
- 特徵選定檢查
- 規格解析與門檻檢核（`spec_resolver`）
- 過濾條件組裝（batch/refdes/part type/product/time/line）
- 分析快取 key 計算與命中判定

狀態輸出（contract）：
- `missing_feature`
- `idle_no_data`
- `error`
- `cached`
- `ready`

## 5.3 計算與回寫

- `MainWindow` 啟動背景 `AnalysisWorker`。
- 多圖分析 payload 之**純計算單一來源**為 `app/viewmodels/chart_analysis_viewmodel.py::compute_analysis_payload(...)`（`ChartAnalysisViewModel.analyze` 委派至此）；完成後由 `app/analytics/analysis_payload_finalize.py` 補上 `statistical_signals`、`diagnosis_engine`、`process_risk`、`knowledge_inference` 與 `diagnostic_evidence_matrix`，再由 orchestrator／`SessionStore` 寫回上下文與快取。
- 分析 payload 對外 shape 維持相容：`parameters`、`dual_parameters`、`triple_parameters` 與既有 top-level keys 不移除不改名。單特徵主 payload 與全參數 payload 共用已計算的 selected-feature bundle，避免同一 feature 重複跑能力/摘要/圖表資料組裝。

# 6. 圖表契約架構

`app/analytics/chart_registry.py` 為圖表契約單一來源，定義了圖表 ID、類別、特徵數相容性及四區塊（Definition/Formula/Source/Interpretation）描述。

**UI 選單分組 (`CHART_UI_GROUPS_ORDER`)：**
- **製程監控**：I-MR, Xbar-R, Run Chart, OOC, Shift/Drift, Patterns (含 3F)
- **製程能力**：Cp/Cpk, Normality, Boxplot, Pass/Fail Matrix (含 3F)
- **異常根源**：Pareto, Spatial Heatmap, Repeated Offender, Anomaly/Consistency 3F
- **變數關係**：Scatter, Correlation matrix, Correlation heatmap, Density, Quadrant, Bivariate Outlier, Parallel Coord
- **比較分析**：Subgroup, ANOVA (PartType)

**工程診斷路徑 (`ROOT_CAUSE_FLOW_ORDER`)：**
1. 製程監控 -> 2. 製程能力 -> 3. 異常根源 -> 4. 變數關係 -> 5. 比較分析

**製程診斷組合矩陣 (`diagnostic_evidence_matrix`)：**
- 由 `app/services/diagnostic_evidence_matrix.py` 在既有 payload 之上展開候選證據，不重新定義 SPC/能力公式。
- 展開邏輯為 `1F charts × features + 2F charts × feature pairs + 3F charts × triple set`，每個候選記錄 `analyzed / available-not-selected / unavailable / not-applicable / missing-data`。
- 證據矩陣欄位固定為能力/規格風險、中心偏移、變異放大、穩定性/漂移、局部/群聚、分布異常、多特徵連動、資料信心；高信心診斷需多圖表族群或多維度互相支持。
- 同一模組提供 `build_readable_diagnostic_tabs(matrix)`，將矩陣轉為 UI、Excel、PPTX 共用的白話列（判讀結果、原因、證據來源、下一步），保留既有內部狀態與 payload shape。

**圖表實作分工：**
- **分析 payload 組裝**：`app/viewmodels/chart_analysis_viewmodel.py` (呼叫各引擎)。
- **摘要／儀表板資料源**：`app/analytics/summary_engine.py` (產出 `dashboard_layers` Layer 1–8)。
- **統計引擎**：`app/analytics/*_engine.py`（如 `spc_engine`, `xbar_r_engine`, `ewma_engine`, `cusum_engine` 等）。
- **異常分析引擎**：`app/analytics/analysis_cards_engine.py` (OOC/Shift/Drift/Outlier)。
- **知識庫與專家診斷**：`app/analytics/process_diagnosis_engine.py` 串接 `spi_process_kb_loader`。
- **繪圖實作**：`app/charts/*_chart.py` (基於 Matplotlib)；`app/charts/base_chart.py` 統一收斂 chart presentation semantics（量測線、中心線、管制限、規格限、OOC/OOS marker、latest point、sample disclosure、legend style），確保 UI 與 PPTX chart evidence 走同一視覺語意。

# 7. 報告架構（Engineering / PPTX-only）

`ReportExportPage` 提供：
- 產生預覽
- 匯出 PPTX（**工程報告**單一結構）；實際寫檔由背景 worker 執行，匯出期間停用匯出按鈕並透過既有 progress/status 顯示狀態，避免 UI thread reentry。
- 圖表清單微調（checkbox；首次載入套用工程建議預設勾選）
- 若所選圖表可渲染，PPTX 於第 8 節後自動插入 `5A. Chart Evidence Gallery`（2x2 圖表證據頁，可多頁）。
- PPTX 會輸出資料來源/未納入證據/章節可信狀態，並以圖表證據覆蓋表列出每張圖的使用特徵、狀態與原因。
- 若本批分析資料沒有有效 `X/Y` 欄位，`spatial_heatmap` 在匯出清單與 PPTX 覆蓋表標示為「未納入：缺座標資料」，空間章節只輸出未納入狀態，不輸出座標匹配率、空間點數或熱圖作為有效證據。
- 預覽補充匯出範圍摘要（已選/可用/不相容 + 建議未選示例）以提升缺圖可解釋性。
- 另存 PPTX 於選路徑後，新增「唯讀匯出清單確認」步驟（圖表名稱、張數、預估畫廊頁數與分布分析敘事頁固定包含提示）；確認後才觸發實際寫檔。

`app/services/report_service.py` 為協調層，子領域已拆分：
- `report_context.py`：報告上下文組裝、資料範圍、未納入證據、圖表覆蓋與指標口徑
- `report_risk.py`：風險語義與等級計算
- `report_diagnostics.py`：診斷條目組裝
- `report_chart_lookup.py`：圖表名稱/ID 正規化與解析
- `report_chart_reason.py`：無圖原因判定
- `report_actions.py`：建議措施映射
- `report_formatters.py`：格式化工具
- `report_exec_summary.py`：Executive summary builder
- `report_intent_presets.py`：報告意圖預設值
- `report_process_narrative.py`：製程敘事邏輯
- `diagnostic_evidence_matrix.py`：製程診斷組合候選、證據矩陣、多圖表關聯判讀與 readable presenter
- `pptx_report_builder.py`：PPTX 物理寫檔與橋接

報告服務契約（現行）：
- `generate_pptx_report(output_path, template_type, chart_ids_to_export)`
- `template_type` 僅支援 `engineering`（舊呼叫端傳入其他值時仍解析為 `engineering`）
- 核心為 12 章節骨架；若匯出勾選之圖表可渲染，會額外輸出圖表證據頁（gallery）。
- 非匯出勾選內之圖表不刪除診斷條目；改為保留 `chart_missing_reason` 並標註未納入匯出清單。
- `report_context` 集中提供 `data_scope` / `excluded_evidence` / `evidence_coverage` / `metric_definitions`；PPTX builder 不重新推導圖表相容性或空間納入狀態。
- 診斷文字以 `evidence_type` 標示 `統計計算`、`圖表證據`、`規則推論` 或 `未納入`；規則推論不得表述為已證實根因。
- `ReportService.generate_pptx_report(...)` 會優先使用與目前 filters/spec/selected_features 相符的 `SessionStore.last_analysis_payload` 或 `_analysis_cache`；缺失或 stale 時才重算分析 payload。
- 單次 PPTX 匯出內，diagnostic chart 與 evidence gallery 共用 chart image cache；cache key 由 chart id、features、normalized 與 context 組成，避免同一張圖重複 render。

# 8. 資料契約與治理關係

- 資料欄位、最小必要欄位、映射與關聯：`docs/specs/data_contract.md`
- 規格維護與跨文件對齊：`docs/specs/spec_maintenance_and_alignment.md`
- 統計規則與門檻單一來源：`docs/governance/SPC_RULES.md`
- 問題解決流程：`docs/specs/issue_resolution_workflow.md`
- 全域計畫框架（永久單人）：`docs/governance/GLOBAL_PLAN_FRAMEWORK_V2_2.md`
- 計畫模板：`docs/templates/PLAN.md`
- AI 幻覺重工預防矩陣（rules/skills）：`docs/governance/ai_hallucination_rework_prevention_matrix.md`

## 8.1 主資料持久化（Master Data）

`app/data/master_data_db.py` 提供主資料庫與遷移流程：
- DB 檔案：`data/spc_master.db`
- 啟動時一次性匯入舊版 JSON registry（若存在）：
  - `data/coordinate_registry.json`
  - `data/product_spec_registry.json`
  - `data/stencil_assignments.json`
- 主要資料表：
  - `products`
  - `coordinate_versions`（每產品單一 active）
  - `paste_printing_spec_versions`（錫膏印刷規格，產品層版本表；每產品單一 active）
  - `stencil_thickness_versions`（鋼板厚度規格，產品層版本表；每產品單一 active）
  - `spec_versions`（legacy 相容/回滾保險，split migration 後新流程不再寫入）
  - `supplier_records`（供應商管理；`supplier_code` 由系統自動維護）
  - `stencil_assignment_meta`
  - `stencil_assignments`
  - `audit_events`

規格解析契約（`app/services/spec_resolver.py`）：`Volume/Area` 取錫膏規格庫；`Height target` 取鋼板厚度規格庫基準（主厚度 100% 邏輯）；`Height LSL/USL` 取錫膏規格庫固定百分比值。`absolute` 模式僅在 resolver 以 `height_denominator_mm` 轉換為比對值域。

供應商管理契約（`app/data/supplier_library.py`）：新增資料時依 `SUP-####` 流水號自動給號；同名供應商沿用同一編號；編輯資料僅允許更新名稱/鋼板資訊，不允許人工修改 `supplier_code`。

# 9. 驗證基線

CI 與本地 baseline 一致：
1. `ruff` lint
2. `mypy`（full `app/` scope）
3. `pytest`（全庫 `tests/`）
4. `python scripts/qt_audit.py app/`（UI token/QSS 規則稽核）
5. `python scripts/check_launch.py`（離屏啟動渲染檢查）
6. `scripts/harness_check.ps1`（本地 harness 結構檢查）
7. `python scripts/release_check.py --skip-ruff --skip-mypy --with-release-ext`（演練發行腳本與 `Outputs/release/release_report.json`；不重複 lint／型別閘）

工作流程檔：`.github/workflows/pytest.yml`

品質工具設定（2026-04-04）：Python 的 ruff、mypy、pytest 預設值集中於**根目錄 `pyproject.toml`**（不使用獨立 `ruff.toml`）；跨編輯器換行見 `.editorconfig`、Git 換行見 `.gitattributes`。詳見 `docs/decision-log.md` 條目「2026-04-04 Tooling & Rules Baseline」。

最終關帳稽核入口（skill + MCP 編排）：
- `python scripts/run_final_audit_suite.py --repo-root . --profile full`
- 規格：`docs/specs/final_audit_suite.md`
- 計劃：`docs/plans/final_audit_execution_plan.md`

發行前精簡驗證（ruff、`mypy app`、`tests/release_validation` 含效能回歸 P gate；可選 **`--with-release-ext`** 再跑三個 traceability 測試）與 JSON 報告：`python scripts/release_check.py` → `Outputs/release/release_report.json`（schema v3：含 `performance_*`、`release_ext_enabled`、`release_ext_paths`、`git_commit`、`dataset_version`、`golden_scenarios`、`release_validation_plan_modules` 等；baseline 更新 `scripts/record_performance_baseline.py`；P gate near-boundary policy 為首次 fail 後補跑 2 次，若僅 time metrics 比值落在 `(1.2, 1.3]` 則以 3 次中位數判定）。**系統金標目錄**為 repo 根 **`golden_dataset/`**（pytest `GOLDEN_DATASET_ROOT` 可覆寫）。僅跑 release_validation 並寫 **`Outputs/validation_report.json`**：`python scripts/run_validation.py`（`validation/` 套件彙整 JUnit，schema v2 九區塊 + `final_result.release_allowed`）。可選 **`python scripts/run_release_gate.py`** → **`Outputs/release_validation_report.json`**（結束碼對齊 `release_allowed`）。情境與測試對照：`docs/specs/release_validation_coverage.md`；計畫對照：`docs/specs/release_validation_data_flow_and_tolerance.md`、`docs/specs/release_validation_gap_matrix.md`；**收斂／ext 邊界**：`docs/open-questions.md` Watchlist #7。

效能量測補充：performance harness 會輸出 `nelson_sec` 與 `report_payload_cache_seeded` 觀測欄位，協助定位 Nelson rule、payload reuse/report recompute 與 report export 的分段成本；blocking metrics 仍維持 `analysis_total_sec`、`chart_payload_sec`、`report_export_sec`。

# 10. UI / DPI 與效能目標

UI 要求：
- 100% / 125% / 150% 縮放可用
- 避免關鍵欄位裁切與重疊

效能目標（維持）：

| 操作 | 目標 |
|-----|-----|
| CSV loading | < 3s |
| Chart rendering | < 2s |
| Filtering | < 1s |

# 11. 修訂紀錄

| 日期 | 內容 |
|-----|-----|
| 2026-05-26 | Qt desktop layout/theme remediation：主視窗初次開啟改為 `0.93` 可用區 fitting；新增 `fit_top_level_to_available(...)` 並套用至解讀、匯出確認與資料庫編輯對話框；Data Setup 改為一頁式量化表格布局與 `DataSetupLayoutBudget` 診斷輸出；側欄高度不足時以可見 affordance 收合分析條件並保留 `下一步` / `重新分析`。 |
| 2026-05-24 | 分析與 PPTX 匯出效能收斂：Nelson rule 3/4 與 summary 缺陷統計改為向量化；payload 組裝避免 selected feature 重算；ReportService 優先重用相符分析快取並加入單次匯出 chart image cache；PPTX 匯出改為背景 worker；圖表卡片改為 first-use lazy creation；performance harness 增加 Nelson 與 report cache reuse 觀測欄位。SPC 公式、chart ID、payload top-level shape、PPTX 內容契約不變。 |
| 2026-05-23 | UI shell 改為左側可見流程導覽：`NavigationPanel` 承載 6 個 workflow buttons，右側 `QTabWidget#workflowTabs` 保留為內部容器但隱藏 tab bar；側欄可尋性契約限制為流程、全域篩選、特徵快捷與下一步/重新分析，並在高度不足時優先收合分析條件。 |
| 2026-05-05 | UI shell 改為混合導航：左側保留全域篩選/狀態/快捷操作，右側 `QTabWidget#workflowTabs` 承載 6 個可見 workflow tabs；`量測` 保留為內部頁，`NAV_TO_STACK` 僅作相容層。 |
| 2026-04-21 | 字型供應改為 repo 內建（`app/assets/fonts/NotoSansTC-VF.ttf` + `app/bootstrap/font_runtime.py`）；Matplotlib CJK 優先序修正（禁止 `DejaVu Sans` 先於 CJK），並收斂高風險 glyph 文案（`μ₀/MR̄/平均値/✓✗`）。 |
| 2026-04-20 | 最終文件收斂：新增 AI 幻覺重工預防矩陣入口；UI 導覽與頁面堆疊敘述再對齊 `main_window.py` 現況（無獨立 WorkorderPage、左側導覽 6 項）。 |
| 2026-04-06 | §4 與多份規格收斂：堆疊含 **量測庫**、**量測**不進導覽；獨立「統計」頁移除，儀表板於 **`DiagnosticPage`**；`docs/specs/process_dashboard_figma_alignment.md`／`docs/specs/ui_design_spec.md`／`docs/specs/data_contract.md`／`docs/specs/ui_state_semantics.md`／驗收快照用語統一（見 `docs/decision-log.md`）。 |
| 2026-04-08 | CI harness gate 收斂：`pytest.yml` 新增 `scripts/qt_audit.py app/` 與 `scripts/check_launch.py`，基線順序更新為 `ruff -> mypy -> pytest -> qt_audit -> check_launch -> release_check --with-release-ext`。 |
| 2026-04-05 | 金標遷至 **`golden_dataset/`**；新增 **`scripts/run_validation.py`**／**`validation/`** → **`Outputs/validation_report.json`**；`summary.process.dashboard_layers` 擴充 Layer 4–7（見 `docs/specs/data_contract.md` §14.4–14.7）。 |
| 2026-04-05 | **`validation_report.json` schema v2**（九固定區塊 + `release_allowed`）；新增 **`scripts/run_release_gate.py`** → **`Outputs/release_validation_report.json`**。 |
| 2026-04-05 | `release_report.json` schema **v3**：`git_commit`、`dataset_version`、`golden_scenarios`、`release_validation_plan_modules`；新增 release validation Step1/2 規格與 L/G/H/I 等測試（見 `docs/specs/release_validation_coverage.md`）。 |
| 2026-04-05 | `release_check`／`release_report.json` schema v2：`performance_baselines.json`、`test_performance_regression.py`（P gate）、`Outputs/release/performance_gate_result.json`（由 `RELEASE_PERF_RESULT_PATH` 驅動）；`run_final_audit_suite` 之 `pytest_release_validation_pack` 逾時調為 2400s。 |
| 2026-04-05 | 新增 `scripts/release_check.py`：發行前執行 ruff／mypy／`tests/release_validation` 並輸出 `Outputs/release/release_report.json`（見 `docs/specs/final_audit_suite.md`）。 |
| 2026-04-05 | 發行驗證：`tests/release_validation/test_resolve_chart_payload_two_feature_golden.py`（2F UI／report parity）與 `docs/specs/release_validation_coverage.md`（覆蓋矩陣）。 |
| 2026-04-05 | §6 圖表統計實作分工：補齊 `compute_analysis_payload`、`summary_engine`、`analysis_cards_engine`、`normality_engine`、共用 utils 與 Advanced 引擎敘述；§5.3 標明 payload 純函數單一來源路徑。 |
| 2026-04-05 | 文件快照對齊：根目錄 `README.md`、`docs/README.md`、`docs/reference/platform_overview.md` 與本架構規格之日期與敘述一致；修訂表更正 PPTX-only 時間線敘述。 |
| 2026-04-03 | 主資料持久化由 JSON registry 轉為 SQLite（`data/spc_master.db`），並加入啟動時一次性遷移與版本化資料表（coordinate/spec/stencil assignment）。 |
| 2026-04-03 | 新增最終稽核套件入口：`run_final_audit_suite.py`，整合 baseline/stat/chart-feature/ui/performance/exception-policy 並輸出 `Outputs/final_audit/*` 工件。 |
| 2026-04-03 | 多特徵互動收斂 Phase A：ChartAnalysis 新增 1F/2F/3F 頁籤分流、autoswitch reason、render status；ReportExport 新增 Preserve/Reset 模式與覆蓋摘要。 |
| 2026-04-03 | SPC 工程導向一次性重構：Dashboard 三層契約、主流程/Advanced 圖表分層、診斷六段格式、工程 PPTX 匯出契約（歷史版本曾描述雙模板；現行見 2026-04-06 decision-log）。 |
| 2026-04-01 | 對齊現行程式架構：新增 AnalysisOrchestrator 流程、ReportService 模組拆分、工程 PPTX 報告流程與 CI baseline（UI／服務路徑之 HTML 匯出已於 2026-04-03 移除，見 `docs/decision-log.md`「Report Export Contract Convergence」）。 |
| 2026-04-02 | 文件收斂關帳：活躍規格與 CI 現況再次對齊，並將歷史報告治理改為「快照標示 + 現行規格導向」。 |
