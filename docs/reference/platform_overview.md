# SPI 製程統計分析（Overview）

本文件是參考用的高層總覽。**文件同步快照：2026-05-25**；架構行為仍以 repo root `README.md` 與 `docs/specs/project_architecture.md` 的 current snapshot 為準。

## 系統定位

PySide6 桌面工程分析平台，核心功能：
- SPI 量測資料分析
- SPC/能力指標與多圖表分析
- 座標關聯與空間分析
- 工程報告輸出（PPTX-only，`engineering`）

## 程式入口與主流程

- 入口：`main.py -> app.ui.main_window.run_app()`
- UI shell：`app/ui/main_window.py`（堆疊頁為 **資料／量測／圖表／報告／參考／診斷／量測庫**；左側 `CollapsibleSidebar` 顯示 6 個流程按鈕，`NAV_TO_STACK=[0,6,2,5,3,4]`；右側 `QTabWidget#workflowTabs` 保留 6 個內部頁面但 tab bar 隱藏；`量測` 頁不顯示於流程導覽）
- 製程統計分析輸出（`summary.process.dashboard_layers` + `diagnostic_evidence_matrix`）：`app/ui/pages/diagnostic_page.py`
- 分析前置與快取決策：`app/services/analysis_orchestrator.py`
- 分析 payload 組裝：`app/viewmodels/chart_analysis_viewmodel.py`
- 圖表契約來源：`app/analytics/chart_registry.py`
- 報告協調層：`app/services/report_service.py`

## 快速啟動

```bash
python -m pip install -r requirements.txt
python main.py
```

`requirements.txt` 會轉接到 `docs/reference/requirements.txt`。

## 品質驗證基線

- lint：`python -m ruff check .`
- type：`python -m mypy app`（full `app/` scope，與 CI 一致）
- tests：`python -m pytest -q`
- UI token/QSS 稽核：`python scripts/qt_audit.py app/`
- 啟動檢查：`python scripts/check_launch.py`
- 發行精簡檢查：`python scripts/release_check.py`（可選 `--with-release-ext`；ruff + mypy + `tests/release_validation`〔+ 三 traceability 測試〕，產出 `Outputs/release/release_report.json`）；golden／測試對照：`docs/specs/release_validation_coverage.md`；**收斂／ext 邊界**：`docs/open-questions.md` Watchlist #7

CI workflow：`.github/workflows/pytest.yml`

最終關帳稽核（完整 profile，產出於 `Outputs/final_audit/<timestamp>/`）：

```bash
python scripts/run_final_audit_suite.py --repo-root . --profile full
```

規格：`docs/specs/final_audit_suite.md`；計劃：`docs/plans/final_audit_execution_plan.md`。

## 重要文件導覽

- 文件索引與一覽表：`docs/README.md`
- 架構規格：`docs/specs/project_architecture.md`
- 資料契約：`docs/specs/data_contract.md`
- 規格對齊治理：`docs/specs/spec_maintenance_and_alignment.md`
- AI 幻覺重工預防矩陣（rules/skills）：`docs/governance/ai_hallucination_rework_prevention_matrix.md`
- 問題解決流程：`docs/specs/issue_resolution_workflow.md`
- 統計規則：`docs/governance/SPC_RULES.md`
- 決策紀錄：`docs/decision-log.md`

## 報告模組現況

`ReportService` 已拆分子領域模組：
- `report_context.py`
- `report_risk.py`
- `report_diagnostics.py`
- `report_chart_lookup.py`
- `report_chart_reason.py`
- `report_actions.py`
- `report_formatters.py`
- `report_exec_summary.py`
- `report_intent_presets.py`
- `report_process_narrative.py`
- `diagnostic_evidence_matrix.py`
- `pptx_report_builder.py`
