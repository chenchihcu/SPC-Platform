# SPI 製程統計分析

SPI 製程統計分析桌面平台（PySide6）。

## 主要功能 (Key Features)

- **① 準備 (Preparation)**：
    - **整合資料設定 (Data Setup)**：一頁式垂直佈局，整合座標、鋼板規格、多工單 (`supplier_work_order_no` / `outsource_work_order_no`) 與量測 CSV 匯入。
    - **歷史量測庫 (Measurement Library)**：基於 SQLite (`data/spcspi_master.db`) 的量測數據存儲與快速檢索分析。
- **② 分析 (Analysis)**：
    - **管制圖表 (Chart Analysis)**：支援 1F/2F/3F 多特徵同步分析（Volume/Area/Height），自動相容性切換，圖卡具備 `Ready/Incompatible/NoData/Error` 狀態標籤。
    - **診斷儀表板 (Diagnostic Dashboard)**：整合 `DiagnosticPage` 視野，採 `dashboard_layers` 契約提供 Alarm/KPI/規格偏移偵測與第 8 卡根因建議。
- **③ 輸出 (Output)**：
    - **專業報告匯出 (Report Export)**：一鍵產生 `engineering` 模板 PPTX 工程報告，支援圖表預覽、匯出範圍摘要與自動生成證據頁 (2x2 Chart Gallery)。

## 視覺與標準 (Standards)

- **字型標準**：全系統統一採用 **Noto Sans TC (思源黑體)**，確保 CJK 渲染與專業報表一致性。
- **設計風格**：深色模式工業美學，支援 100% / 125% / 150% DPI 自適應縮放。
- **架構核心**：以 `AnalysisOrchestrator` 統一處理規格解析、過濾與快取；報告邏輯模組化（`report_*`）。

---

## 快速啟動 (Quick Start)
- **SPI 製程對應知識庫**：人維護權威稿為 **`SPI_製程對應知識庫_v1.0.xlsx`**（見 `app/services/spi_process_kb_loader.py` 常數 `CANONICAL_SPI_KB_WORKBOOK_BASENAME`）；版本化 JSON 置於 `data/spi_process_kb/v1/`（四區塊：多訊號規則 R001–R030、三維對應、檢查門檻、圖表速查）；`multi_signal_diagnosis` 執行期載入並併入診斷 payload；以 `scripts/import_spi_process_kb_xlsx.py` 自該 xlsx 匯入更新。
- CI baseline 為 `lint -> type check -> tests -> qt_audit -> check_launch`。

## Current Architecture (2026-04-20)

### Runtime Flow

```text
main.py
  -> app.ui.main_window.run_app()
  -> MainWindow
      -> AnalysisOrchestrator (prepare/cache/context)
      -> ChartAnalysisViewModel (engine payload assembly)
      -> chart_registry (chart contract + compatibility + payload routing)
      -> ChartAnalysisPage UI state model (`active_features`, `selected_chart_ids`, `autoswitch_reason`, `render_status`)
      -> DiagnosticPage（製程診斷儀表板：`summary.process.dashboard_layers`）
      -> ReportService (PPTX-only engineering report orchestration, `template_type=engineering`)
```

### Service Split (Report Domain)

`app/services/report_service.py` 目前作為協調層，核心子領域已拆分：
- `report_context.py`
- `report_risk.py`
- `report_diagnostics.py`
- `report_chart_lookup.py`
- `report_chart_reason.py`
- `report_actions.py`
- `report_formatters.py`
- `report_exec_summary.py`

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

### Main window stack（與左側導覽）

堆疊順序見 `app/ui/main_window.py` 之 `STACK_ORDER`：**資料**、**量測**（元件／特徵選定；**不顯示於左側導覽**）、**圖表**、**報告**、**參考**、**診斷**、**量測庫**。左側導覽為 6 項（`資料匯入`、`資料庫`、`統計圖表`、`診斷`、`報告匯出`、`說明`），透過 `NAV_TO_STACK = [0, 6, 2, 5, 3, 4]` 對應到堆疊索引。

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
```

圖表 PNG baseline 回歸（`matplotlib.testing.compare`）：`tests/test_chart_baseline_png.py`；更新方式見 **`tests/baseline_images/README.md`**（建議與 CI 相同 **Python 3.12** 環境產生 baseline）。

發行前精簡檢查（同上 ruff／mypy，外加 `tests/release_validation`，含效能回歸 P gate），並寫入 **`Outputs/release/release_report.json`**（schema v3：含 `release_ext_enabled`／`release_ext_paths`、v2 之 `performance_*` 與可選 `final_audit_summary_path`，以及 `git_commit`、`dataset_version`、`golden_scenarios`、`release_validation_plan_modules` 等）。效能 baseline 更新：`python scripts/record_performance_baseline.py`。可選 **`--with-release-ext`** 再跑三個全庫 traceability 測試；其餘可選後續見 **`docs/open-questions.md` Watchlist #7**。**GitHub Actions** 目前 gate 順序為 `ruff -> mypy app -> pytest -q -> scripts/qt_audit.py app/ -> scripts/check_launch.py -> release_check --with-release-ext`，以強制 UI token/QSS 稽核與啟動可用性檢查。

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
- 主資料庫：`data/spcspi_master.db`
- 產出路徑：`Outputs/`

## Documentation Map

- 文件總覽：`docs/README.md`（含 **圖表與統計計算** 檔案／文件總覽表）
- 高層總覽（精簡）：`docs/reference/platform_overview.md`
- 系統架構：`docs/specs/project_architecture.md`
- 最終稽核規格：`docs/specs/final_audit_suite.md`
- 發行驗證覆蓋矩陣（golden／測試／閘門）：`docs/specs/release_validation_coverage.md`
- UI 規格：`docs/specs/ui_design_spec.md`
- 問題解決流程：`docs/specs/issue_resolution_workflow.md`
- 最終稽核計劃：`docs/plans/final_audit_execution_plan.md`
- 統計規則：`docs/governance/SPC_RULES.md`
- AI 幻覺重工預防矩陣（rules/skills 優化權威入口）：`docs/governance/ai_hallucination_rework_prevention_matrix.md`
- Repo 規範：`AGENTS.md`
- 治理規範：`docs/governance/AGENTS.md`
- Code Review 準則：`code_review.md`
- 決策紀錄：`docs/decision-log.md`
- 開放問題（active risk single source）：`docs/open-questions.md`
