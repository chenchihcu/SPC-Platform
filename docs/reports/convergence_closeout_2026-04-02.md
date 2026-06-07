# Convergence Closeout Report (2026-04-02)

> Historical Snapshot Note (2026-04-02): the `01-10 Task Closeout` table below records an earlier convergence cycle. When it conflicts with current executable reality, use the `Current Validation Snapshot` and `11 Chart Sample-Integrity Closeout` sections in this file as the operational source of truth.

## Objective

Close architecture/runtime/documentation gaps for the SMT SPI/SPC platform with verifiable contracts, tests, and CI-aligned validation.

## 01-10 Task Closeout

| ID | Task | Status | Evidence |
|---|---|---|---|
| 01 | CI baseline (`ruff -> mypy -> pytest`) and root dependency entrypoint alignment | Closed | `.github/workflows/pytest.yml`, `requirements.txt`, `docs/decision-log.md` (CI baseline entries) |
| 02 | Analysis orchestration extraction from UI | Closed | `app/services/analysis_orchestrator.py`, `app/ui/main_window.py`, `tests/test_analysis_orchestrator.py` |
| 03 | Async analysis context contract hardening | Closed | `app/services/analysis_context.py`, orchestrator/main-window context integration, orchestration tests |
| 04 | Report risk domain extraction and unified risk semantics | Closed | `app/services/report_risk.py`, `app/services/report_service.py`, `tests/test_report_risk.py` |
| 05 | Report diagnostics/context modularization | Closed | `app/services/report_diagnostics.py`, `app/services/report_context.py`, `tests/test_report_context.py` |
| 06 | Report chart-lookup/action/formatter/executive-summary split | Closed | `app/services/report_chart_lookup.py`, `report_actions.py`, `report_formatters.py`, `report_exec_summary.py`, related tests |
| 07 | Chart draw contract normalization (`draw_chart -> bool`) | Closed | `app/charts/base_chart.py`, chart modules, `tests/test_chart_draw_contract.py` |
| 08 | Full-app static typing convergence (`python -m mypy app`) | Closed | full app mypy green, CI gate updated to `python -m mypy app` |
| 09 | Import pipeline contract regression coverage | Closed | `tests/test_import_service.py` (empty-path fallback, batch_qty unique/row-count behavior) |
| 10 | Warning/noise convergence and governance doc closure | Closed | `app/analytics/normality_engine.py`, `tests/test_normality_engine.py`, `docs/open-questions.md`, `code_review.md` |

## 11 Chart Sample-Integrity Closeout

### Scope

Audit every chart under `app/charts` plus chart-specific tabs that surface display/test sample counts.

### Findings Closed

1. Silent display truncation in Boxplot:
   - Root cause: `BoxplotChart` hard-clamped output to the first 50 groups in both single-feature and multi-feature paths.
   - Fix: remove group truncation; keep all groups and rely on sparse tick labels only.
   - Evidence: `app/charts/boxplot_chart.py`, `tests/test_chart_sample_integrity.py::test_boxplot_chart_single_feature_keeps_all_groups`, `tests/test_chart_sample_integrity.py::test_boxplot_chart_multi_feature_keeps_all_groups`.

2. Silent display truncation in Pareto:
   - Root cause: `ParetoChart` hard-clamped output to the first 50 categories, which also distorted cumulative percentage interpretation.
   - Fix: remove category truncation; compute and render cumulative percentage over the full category set.
   - Evidence: `app/charts/pareto_chart.py`, `tests/test_chart_sample_integrity.py::test_pareto_chart_keeps_all_categories`.

3. Sampling visibility gap in Parallel Coordinates:
   - Root cause: engine metadata existed, but the chart did not annotate displayed-vs-total sample count on the rendered figure.
   - Fix: annotate `displayed_n / n` and `normalization_basis` directly on the chart.
   - Evidence: `app/charts/parallel_coord_chart.py`, `tests/test_chart_sample_integrity.py::test_parallel_coord_chart_discloses_display_sampling`.

4. Sampling visibility gap in Normality:
   - Root cause: `tested_n / total_n` was available in engine statistics but not guaranteed to appear on the exported chart image.
   - Fix: annotate tested-vs-total sample count on both single-feature and multi-feature normality plots.
   - Evidence: `app/ui/tabs/normality_tab.py`, `tests/test_chart_sample_integrity.py::test_normality_tab_discloses_full_tested_sample_count`.

### Cross-Chart Audit Result

- Closed severe silent sample-distortion defects: `2`
- Closed chart-level sampling transparency gaps: `2`
- Verified already-transparent chart paths without further code changes:
  - `HeatmapChart` (`顯示聚合`)
  - `RepeatedOffenderChart` (`顯示截取`)
  - `RunChart` / `RunChart3F` (`顯示抽樣`)

### Render Evidence

Generated output artifacts:

- `Outputs/chart_sample_integrity/boxplot_all_groups.png`
- `Outputs/chart_sample_integrity/pareto_all_categories.png`
- `Outputs/chart_sample_integrity/parallel_sampling_annotation.png`
- `Outputs/chart_sample_integrity/normality_sampling_note.png`

## Current Validation Snapshot

Executed on 2026-04-02:

1. `python -m ruff check .`
2. `python -m mypy app`
3. `python -m pytest -q`

Result:

- `ruff`: pass
- `mypy app`: pass
- `pytest`: pass (`398 passed`)

## Post-Closeout Addendum (Documentation Convergence)

Additional convergence work completed on 2026-04-02:

1. Active layout/spec alignment:
   - `docs/specs/ui_target_layout.md` updated to current runtime architecture semantics (dashboard chart mode, **PPTX** export contract, non-goals and dependency specs). **（2026-04-06 補註：報告匯出已收斂為 engineering-only PPTX；UI 不提供 HTML 匯出；見 `docs/decision-log.md`。）**

2. Historical snapshot governance:
   - Added `docs/reports/README.md` to distinguish active contracts vs historical report evidence.
   - Added historical snapshot notes to selected legacy reports to prevent outdated contract wording from being interpreted as current behavior.

3. Link health:
   - Local markdown link integrity check executed across repository markdown files (excluding `node_modules`) with result `BROKEN_LINKS=0`.

## Baseline Completeness (Governance/Bootstrap)

Repository baseline artifacts now present:

- `AGENTS.md` (repository-level domain guardrails)
- `code_review.md` (findings-first review rubric)
- `docs/open-questions.md` (residual-risk ledger)
- `.env.example` (optional runtime/testing env template)
- `tests/fixtures/README.md`
- `tests/golden/README.md`

## Residual Risks

1. High-cardinality charts can become visually dense:
   - This is now a readability concern, not a sample-distortion concern.
   - Current policy prefers full data with sparse labels over hidden truncation.

2. Worker-thread timing path:
   - Current import regression tests verify synchronous `run()` contract behavior.
   - Real threaded signal-order races remain integration-sensitive and should be monitored by UI integration checks.

## Closure Decision

Chart sample-integrity closure is complete for this convergence cycle: all currently known silent sample-distortion defects are fixed, full-chart audit coverage has been added, rendered evidence is stored, and the repository validation snapshot now matches executable reality.
