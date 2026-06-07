# Full Documentation Sync Audit (2026-05-16)

## Summary

- Done state: active documentation was compared against current code/config contracts and updated where drift was verified.
- Change boundary: documentation only; no runtime code, SPC formulas, schemas, payload shapes, chart IDs, UI labels, or release-gate logic changed.
- Source-of-truth priority: live code/config, CI workflow, validation outputs, then authoritative specs/decision log.

## Source Evidence

- Launch and UI shell: `main.py`, `app/ui/main_window.py`, `app/ui/workflow_labels.py`.
- Chart contract: `app/analytics/chart_registry.py`.
- Report contract: `app/services/report_service.py`, `app/services/report_*.py`, `app/services/diagnostic_evidence_matrix.py`, `app/services/pptx_report_builder.py`.
- Data/workorder contract: `docs/specs/data_contract.md`, `app/data/*`, `app/services/*`.
- Validation baseline: `pyproject.toml`, `.github/workflows/pytest.yml`, `scripts/check_launch.py`, `scripts/check_governance_alignment.py`, `scripts/run_release_gate.py`.
- Release evidence: `Outputs/release/release_report.json`, `Outputs/release_validation_report.json`.

## Inventory Classification

### sync

- `README.md`: expanded report service split to include the current helper modules and PPTX builder.
- `docs/README.md`: refreshed snapshot date and added this audit to the documentation map.
- `docs/reference/platform_overview.md`: added missing validation gates and current report helper modules.
- `docs/specs/data_contract.md`: clarified Layer 6 workorder metadata around dual workorder fields and compatibility-only `work_order_no`.
- `docs/open-questions.md`: changed stale `Watchlist #7` blocker text to monitoring based on latest PASS release evidence.
- `docs/governance/AGENTS.md`: replaced stale PDF report-generation wording with current PPTX/report rendering wording.
- `docs/decision-log.md`: fixed relative links that resolved outside the repo and added the 2026-05-16 documentation-sync decision.
- `tests/fixtures/golden/README.md`: fixed the relative link to `tests/release_validation/conftest.py`.
- `docs/reports/document_inventory_master.md` and `.csv`: refreshed inventory and classifications.

### delete / move candidate

- None executed.
- `docs/governance/GLOBAL_PLAN_FRAMEWORK_V2_1.md` is superseded but retained because `scripts/check_governance_alignment.py` explicitly requires and validates it.

### keep

- `docs/governance/SPC_RULES.md`: statistical authority; no formula/threshold drift was part of this pass.
- `docs/specs/project_architecture.md`: checked against current workflow tab map, report split, and validation baseline; no edit required.
- `docs/specs/release_validation_coverage.md`, `docs/specs/release_validation_data_flow_and_tolerance.md`, `docs/specs/release_validation_gap_matrix.md`: still point to `docs/open-questions.md` as the central status source for Watchlist #7.
- `docs/reports/*.md`: retained as dated snapshots; `docs/reports/README.md` explains that historical reports can contain superseded terminology.

### exclude

- `archive/**`: historical/recoverable archive, not freshened.
- `Outputs/**`: generated validation/release/final-audit artifacts; used as evidence only.
- `.venv/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `node_modules/`: dependency/cache output.
- `tmp/**`, screenshots, generated UI images, and runtime scratch artifacts: outside active documentation sync.

## Drift Fixed

- Stale active-risk status: `docs/open-questions.md` still described `Watchlist #7` as release-blocking even though latest available release evidence shows PASS.
- Stale report terminology: active governance text still referenced PDF report generation while the current service contract is PPTX-only engineering report export.
- Broken relative links: `docs/decision-log.md` linked to `.github`, `scripts`, and `Outputs` as if it were in repo root; `tests/fixtures/golden/README.md` linked one directory too shallow.
- Partial report-service maps: root/reference docs did not list all current report helper modules used by `ReportService`.

## Verification

- Active Markdown link scan: `BROKEN_LINKS=0`.
- Stale-term scan: remaining old report-mode terms are historical/context notes, not live contract claims.
- `.venv\\Scripts\\python.exe -m ruff check .`: PASS (`All checks passed!`).
- `.venv\\Scripts\\python.exe -m mypy app`: PASS (`Success: no issues found in 190 source files`; existing notes about unchecked untyped bodies and unused `pyqtgraph.*` override).
- `.venv\\Scripts\\python.exe -m pytest -q`: PASS (`772 passed in 155.93s`).
- `.venv\\Scripts\\python.exe scripts\\check_launch.py`: PASS (`Result: [PASS] Application started and rendered successfully.`).
- `.venv\\Scripts\\python.exe scripts\\check_governance_alignment.py`: PASS.
- `.venv\\Scripts\\python.exe scripts\\run_release_gate.py`: PASS (`150 passed in 30.07s`; wrote `Outputs/release_validation_report.json`, `release_allowed=True`).
