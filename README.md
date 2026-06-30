# SPI 製程統計分析

SPI 製程統計分析桌面平台（PySide6）。

## 主要功能 (Key Features)

- **① 準備 (Preparation)**：
    - **整合資料設定 (Data Setup)**：一頁式量化表格布局，整合座標、產品規格、多工單 (`supplier_work_order_no` / `outsource_work_order_no`) 與量測 CSV 匯入；legacy `work_order_no` 僅保留相容鍵且寫入固定空字串。
    - **供應商格式相容**：量測 CSV 支援供應商限定 profile；目前 `振順豐` TOP 寬表會在供應商匹配（或未選供應商且路徑/欄位簽名完全符合）時轉為標準 `RefDes/Pad/Volume/Area/Height/BoardNo` 長表，不擴大全域欄位別名。
    - **歷史量測庫 (Measurement Library)**：基於 SQLite (`data/spc_master.db`) 的量測數據存儲與快速檢索分析；量測 session 會保存供應商名稱、雙工單與料號，從量測庫回載時會同步回 `SessionStore` 供供應商限定 CSV profile 使用；規格管理以合併表呈現「錫膏印刷規格 + 鋼板厚度規格」，可手動新增每產品 active 規格並由兩庫各自維護版本；供應商管理分頁之 `supplier_code` 由系統自動產生（`SUP-0001` 流水格式）且 UI 唯讀不可手改。
- **② 分析 (Analysis)**：
    - **統計圖表 (Chart Analysis)**：支援 1F/2F/3F 多特徵同步分析（Volume/Area/Height），自動相容性切換；所有 Matplotlib 圖表共用 `BaseChart` 視覺語意（量測線、中心線、管制限、規格限、OOC/OOS 標記、樣本揭露），圖卡具備 `Ready/Incompatible/NoData/Error` 狀態標籤；純文字摘要（失控、偏移、漂移、離群）改由同列左側選單 `統計資料` 以一頁式資料表瀏覽。
    - **製程統計分析 (Process Statistics Analysis)**：整合 `DiagnosticPage` 視野，採少容器報告式輸出呈現 `dashboard_layers` 的 Alarm/KPI/規格能力/穩定性/第 8 層根因建議；另以 `diagnostic_evidence_matrix` 展開 `特徵 × 圖表 × 篩選 × 顯示` 候選組合，輸出 7 個固定子分頁的白話判讀列、組合矩陣、證據矩陣與多圖表關聯判讀。
- **③ 輸出 (Output)**：
    - **專業報告匯出 (Report Export)**：一鍵產生 `engineering` 模板 PPTX 工程報告，支援圖表預覽、匯出範圍摘要、自動生成證據頁 (2x2 Chart Gallery) 與圖表證據覆蓋表；報告會揭露資料來源、未納入證據與診斷證據類型，無有效 X/Y 座標時空間分析不作為有效判讀證據。

## 視覺與標準 (Standards)

- **字型標準**：全系統統一採用 **Noto Sans TC (思源黑體)**，確保 CJK 渲染與專業報表一致性。
- **字型供應**：repo 內建 `app/assets/fonts/NotoSansTC-VF.ttf`（`OFL-1.1`），由 `app/bootstrap/font_runtime.py` 於 Qt/Matplotlib 啟動時註冊；系統字型僅作 fallback。
- **設計風格**：淺色 Slate + Electric Blue 工程分析介面，保留高密度表單/表格與 100% / 125% / 150% DPI 自適應縮放。
- **視窗適配**：主視窗初次開啟依目前螢幕可用工作區 `0.93` 比例置中；共用 fitting helper 同步套用於主要解讀、匯出確認與資料庫編輯對話框；已儲存幾何只在目前螢幕可見且未超出工作區時保留，否則自動重設為安全尺寸。
- **QSS 相容性**：`scripts/qt_audit.py app/` 會阻擋 Qt QSS 不支援的 CSS 屬性，避免樣式看似存在但在 PySide 實際被忽略。
- **架構核心**：以 `AnalysisOrchestrator` 統一處理規格解析、過濾與快取；報告邏輯模組化（`report_*`）。

---

## 快速啟動 (Quick Start)
- **SPI 製程對應知識庫**：人維護權威稿為 **`SPI_製程對應知識庫_v1.0.xlsx`**（見 `app/services/spi_process_kb_loader.py` 常數 `CANONICAL_SPI_KB_WORKBOOK_BASENAME`）；版本化 JSON 置於 `data/spi_process_kb/v1/`（四區塊：多訊號規則 R001–R030、三維對應、檢查門檻、圖表速查）；`multi_signal_diagnosis` 執行期載入並併入診斷 payload；以 `scripts/import_spi_process_kb_xlsx.py` 自該 xlsx 匯入更新。
- CI baseline 為 `lint -> type check -> tests -> qt_audit -> check_launch`。

## Current Architecture (2026-06-30)

### Runtime Flow

```text
main.py
  -> app.ui.main_window.run_app()
  -> MainWindow
      -> AnalysisOrchestrator (prepare/cache/context)
      -> ChartAnalysisViewModel (engine payload assembly)
      -> analysis_payload_finalize (statistical signals + diagnostic_evidence_matrix)
      -> chart_registry (chart contract + compatibility + payload routing)
      -> ChartAnalysisPage UI state model (`active_features`, `selected_chart_ids`, `autoswitch_reason`, `render_status`; visual chart cards lazy-create on first visible use)
      -> StatisticsDataPage（一頁式瀏覽 OOC/Shift/Drift/Outlier 文字統計摘要）
      -> DiagnosticPage（製程統計分析報告輸出：`summary.process.dashboard_layers` + `diagnostic_evidence_matrix`）
      -> ReportService (PPTX-only engineering report orchestration, `template_type=engineering`; reuses matching analysis cache and per-export chart image cache)
```

### Service Split (Report Domain)

`app/services/report_service.py` 目前作為協調層，核心子領域已拆分：
- `report_context.py`（含資料範圍、未納入證據、圖表覆蓋與指標口徑）
- `report_risk.py`
- `report_diagnostics.py`
- `report_chart_lookup.py`
- `report_chart_reason.py`
- `report_actions.py`
- `report_formatters.py`
- `report_exec_summary.py`
- `report_intent_presets.py`
- `report_process_narrative.py`
- `diagnostic_evidence_matrix.py`（含組合候選、證據矩陣、多圖表關聯與 UI/Excel/PPTX readable presenter）
- `pptx_report_builder.py`

### Directory Snapshot

```text
app/
  analytics/     # SPC, capability, anomaly, chart registry, statistics engines
  charts/        # chart renderers (BaseChart + individual chart classes)
  data/          # loaders, mapping, relation, validators, session store, SQLite master-data registry
  services/      # analysis orchestration, import, multi_signal_diagnosis, SPI process KB, report export
  ui/            # main window, pages, tabs, widgets, theme
  viewmodels/    # UI-binding viewmodels
docs/
  governance/    # governance and SPC rules
  specs/         # product/data/UI/contracts/workflows
  reports/       # audits and verification reports
  plans/         # planning artifacts
```

### Main window stack（與左側流程導覽）

堆疊順序見 `app/ui/main_window.py` 之 `STACK_ORDER`：**資料**、**量測**（元件／特徵選定；**不顯示於流程導覽**）、**圖表**、**報告**、**參考**、**診斷**、**量測庫**、**診斷二**、**統計資料**。左側 `CollapsibleSidebar` 顯示 8 個流程按鈕（`資料設定`、`資料庫`、`統計圖表`、`統計資料`、`診斷一`、`診斷二`、`報告匯出`、`說明`），其中 `統計圖表 / 統計資料` 與 `診斷一 / 診斷二` 各自並列，維持 6 個視覺列；透過 `NAV_TO_STACK = [0, 6, 2, 8, 5, 7, 3, 4]` 與 `TAB_TO_STACK = [0, 6, 2, 8, 5, 7, 3, 4]` 對應到內部堆疊；右側 `QTabWidget#workflowTabs` 保留為頁面容器但隱藏 tab bar。左側欄只承載流程切換、全域篩選、特徵快捷與 `下一步` / `重新分析`，表單與資料表列操作保留在內容區；當視窗高度不足時，側欄會先收合 `分析條件` 並顯示已收合提示，保留目前篩選值、流程導覽與底部主動作可辨識。Data Setup 主區採量化表格布局與 `DataSetupLayoutBudget` 診斷輸出，避免回到整頁垂直 scroll 作為主要布局。

## Quick Start

### Prerequisites
- Windows + Python 3.12 (與 CI 對齊)

### Install

```bash
python -m pip install -r requirements.txt
```

`requirements.txt` 目前透過 `-r docs/reference/requirements.txt` 轉接實際依賴清單。

### Run

```bash
python main.py
```

或使用：

```bat
run.bat
```

## Validation Baseline

與 CI 相同，最小驗證流程：

```bash
python -m ruff check .
python -m mypy app
python -m pytest -q
python scripts/qt_audit.py app/
python scripts/check_launch.py
scripts/harness_check.ps1
```

圖表 PNG baseline 回歸（`matplotlib.testing.compare`）：`tests/test_chart_baseline_png.py`；更新方式見 **`tests/baseline_images/README.md`**（建議與 CI 相同 **Python 3.12** 環境產生 baseline）。

發行前精簡檢查（同上 ruff／mypy，外加 `tests/release_validation`，含效能回歸 P gate），並寫入 **`Outputs/release/release_report.json`**（schema v3：含 `release_ext_enabled`／`release_ext_paths`、v2 之 `performance_*` 與可選 `final_audit_summary_path`，以及 `git_commit`、`dataset_version`、`golden_scenarios`、`release_validation_plan_modules` 等）。P gate 目前採「**首次 fail 才補 2 次**」策略：若僅 time metrics 在 near-boundary（ratio `(1.2, 1.3]`）超限，會以 3 次量測中位數作最終判定；`analysis_total_sec`／`chart_payload_sec`／`report_export_sec` 為阻擋指標，`spc_sec` 與 `nelson_sec` 只作觀測；`ratio > 1.3`、memory fail 或 scenario mismatch 仍直接 fail。效能 baseline 更新：`python scripts/record_performance_baseline.py`。可選 **`--with-release-ext`** 再跑三個全庫 traceability 測試；其餘可選後續見 **`docs/open-questions.md` Watchlist #7**。**GitHub Actions** 目前 gate 順序為 `ruff -> mypy app -> pytest -q -> scripts/qt_audit.py app/ -> scripts/check_launch.py -> release_check --with-release-ext`，以強制 UI token/QSS 稽核與啟動可用性檢查。

```bash
python scripts/release_check.py
python scripts/release_check.py --with-release-ext
```

發行／稽核用 **系統金標** 位於 repo 根目錄 **`golden_dataset/`**（pytest `golden_root` 與環境變數 **`GOLDEN_DATASET_ROOT`** 覆寫見 `tests/release_validation/conftest.py`）。

僅執行 `tests/release_validation` 並產出 **`Outputs/validation_report.json`**（schema v2：JUnit 彙整、九區塊摘要、`final_result.release_allowed`）：

```bash
python scripts/run_validation.py
```

發行 gate（同上 pytest 範圍，預設寫 **`Outputs/release_validation_report.json`**；結束碼 0 僅當 `release_allowed` 為 true）：

```bash
python scripts/run_release_gate.py
```

工具預設值集中於根目錄 **`pyproject.toml`**（`[tool.ruff]`、`[tool.mypy]`、`[tool.pytest.ini_options]`）。跨編輯器換行與縮排見 **`.editorconfig`**；Git 換行策略見 **`.gitattributes`**。

React 原型（`Outputs/industrial-data-setup-ui/`）：`npm run lint`、`npm run typecheck`、`npm test`。

最終稽核（完整性 / 正確性 / 效能）入口：

```bash
python scripts/run_final_audit_suite.py --repo-root . --profile full
```

## Data and Output Contract

- 資料契約：`docs/specs/data_contract.md`
- 圖表/流程契約維護：`docs/specs/spec_maintenance_and_alignment.md`
- 報告輸出：
  - 工程導向 PPTX（`engineering`）
- 主資料庫：`data/spc_master.db`
- 產出路徑：`Outputs/`

## Documentation Map

- 文件總覽：`docs/README.md`（含 **圖表與統計計算** 檔案／文件總覽表）
- 高層總覽（精簡）：`docs/reference/platform_overview.md`
- 系統架構：`docs/specs/project_architecture.md`
- 最終稽核規格：`docs/specs/final_audit_suite.md`
- 發行驗證覆蓋矩陣（golden／測試／閘門）：`docs/specs/release_validation_coverage.md`
- UI 規格：`docs/specs/ui_design_spec.md`
- 問題解決流程：`docs/specs/issue_resolution_workflow.md`
- 全域計畫框架（永久單人版）：`docs/governance/GLOBAL_PLAN_FRAMEWORK_V2_2.md`
- 計畫可複製模板：`docs/templates/PLAN.md`
- 最終稽核計劃：`docs/plans/final_audit_execution_plan.md`
- 統計規則：`docs/governance/SPC_RULES.md`
- AI 幻覺重工預防矩陣（rules/skills 優化權威入口）：`docs/governance/ai_hallucination_rework_prevention_matrix.md`
- Repo 規範：`AGENTS.md`
- 治理規範：`docs/governance/AGENTS.md`
- Code Review 準則：`code_review.md`
- 決策紀錄：`docs/decision-log.md`
- 開放問題（active risk single source）：`docs/open-questions.md`
