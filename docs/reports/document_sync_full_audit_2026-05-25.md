# Full Documentation Sync Audit (2026-05-25)

## Summary

- Done state: active documentation was compared against current code/config contracts and updated where drift was verified.
- Change boundary: documentation only; no runtime code, SPC formulas, schemas, payload shapes, chart IDs, UI labels, or release-gate logic changed.
- Source-of-truth priority: live code/config and current authoritative specs, then prior sync evidence.

## Source Evidence

- Launch and UI shell: `main.py`, `app/ui/main_window.py`, `app/ui/workflow_labels.py`.
- Bundled font runtime: `app/assets/fonts/NotoSansTC-VF.ttf`, `app/assets/fonts/OFL-1.1.txt`, `app/bootstrap/font_runtime.py`.
- Report/process-statistics contract: `app/ui/pages/diagnostic_page.py`, `app/analytics/dashboard_layers_display.py`, `app/services/diagnostic_evidence_matrix.py`, `app/services/report_*.py`, `app/services/pptx_report_builder.py`.
- Validation baseline: `pyproject.toml`, `.github/workflows/pytest.yml`, `scripts/verify.ps1`, `scripts/harness_check.ps1`, `scripts/check_launch.py`, `scripts/check_governance_alignment.py`.
- Governance retention evidence: `scripts/check_governance_alignment.py` still requires `docs/governance/GLOBAL_PLAN_FRAMEWORK_V2_1.md` and validates its superseded notice.

## Inventory Classification

### sync

- `README.md`: current architecture heading aligned to the 2026-05-24 source snapshot.
- `docs/README.md`: snapshot date, process-statistics wording, and latest sync audit entry refreshed.
- `docs/reference/platform_overview.md`: UI shell wording aligned to the current left-sidebar workflow and hidden `QTabWidget#workflowTabs`.
- `docs/governance/AGENTS.md`: bundled font guidance aligned to `app/assets/fonts/NotoSansTC-VF.ttf` and `font_runtime.py`.
- `docs/specs/project_architecture.md`, `docs/specs/ui_design_spec.md`, `docs/specs/ui_target_layout.md`: workflow wording aligned to visible left navigation.
- `docs/specs/ui_state_semantics.md`, `docs/specs/data_contract.md`: `DiagnosticPage` wording aligned to current 製程統計分析輸出 terminology.
- `docs/reports/README.md`, `docs/reports/document_inventory_master.md`, `docs/reports/document_inventory_master.csv`: sync pointers and inventory refreshed.
- `docs/decision-log.md`: this sync recorded as a new decision.

### delete / move candidate

- None executed.
- `docs/governance/GLOBAL_PLAN_FRAMEWORK_V2_1.md` remains superseded but active because `scripts/check_governance_alignment.py` explicitly requires it.

### keep

- `docs/governance/SPC_RULES.md`: statistical formula/threshold authority; no statistical contract drift was part of this pass.
- `docs/open-questions.md`: active risk ledger remains current; no new active residual risk was found.
- `docs/specs/release_validation_*.md`: release command contracts still point to scripts and `docs/open-questions.md` Watchlist #7.
- `docs/reports/*.md`: historical snapshots retained with `docs/reports/README.md` caveat.

### exclude

- `archive/**`: historical/recoverable archive, not freshened.
- `Outputs/**`: generated validation/release/final-audit artifacts; used as evidence only.
- `.venv/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `node_modules/`: dependency/cache output.
- `tmp/**`, screenshots, generated images, and runtime scratch artifacts: outside active documentation sync.

## Drift Fixed

- Stale sync pointers: active docs still identified 2026-05-16 as the latest sync after 2026-05-24 architecture updates.
- Stale UI shell wording: overview and layout target docs still described right-side top workflow tabs, while the current UI uses left `CollapsibleSidebar` workflow buttons and a hidden-tab `QTabWidget#workflowTabs` content container.
- Stale font guidance: governance still stated that the repo did not ship fonts, but the current runtime ships and registers `NotoSansTC-VF.ttf`.
- Stale DiagnosticPage naming: several active docs still used older 診斷儀表板 wording where current specs use 製程統計分析輸出.

## Verification

- Active stale-term scan: PASS. No remaining matches in the patched active contract files for the stale live-contract term set used in this audit.
- New sync-reference scan: PASS. Active docs now point to the 2026-05-25 sync report.
- Path existence check: PASS for the new sync report, inventory, bundled font, font runtime, and verification scripts.
- `.venv\\Scripts\\python.exe scripts\\check_governance_alignment.py`: PASS (`[PASS] Governance alignment checks passed.`).
- `scripts\\verify.ps1 -PythonExe .\\.venv\\Scripts\\python.exe`: PASS.
  - `python -m ruff check .`: PASS (`All checks passed!`)
  - `python -m mypy app`: PASS (`Success: no issues found in 191 source files`)
  - `python -m pytest -q`: PASS (`799 passed in 146.57s`)
  - `python scripts/qt_audit.py app/`: PASS (`ALL CLEAR - ready for delivery`)
  - `python scripts/check_launch.py`: PASS (`Result: [PASS] Application started and rendered successfully.`)
  - `scripts\\harness_check.ps1`: PASS (`Harness check passed.`)
