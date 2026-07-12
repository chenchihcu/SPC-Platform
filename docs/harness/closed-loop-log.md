# Closed-loop Log

Use this file for reusable lessons from debugging, regressions, repeated failures, or Investigation Path work.

## Entry Template

```text
Date:
Task:
Changes:
Impact:
Verification:
Residual risk:
Next action:
Debug/RCA (when applicable):
Observed:
Root cause:
Fix:
Harness update needed:
Destination:
```

## Initial Entry

Date: 2026-05-16
Task: Install closed-loop harness.
Changes: Added harness docs, exec-plan directories, a harness structure check, a full PowerShell verification entrypoint, and project command rules.
Impact: The repo now exposes a common harness layer while preserving strict SPC/SPI governance and release-focused validation boundaries.
Verification: Run `scripts\harness_check.ps1` and `scripts\verify.ps1`.
Residual risk: active residual risks remain only in `docs/open-questions.md`; this log is not a parallel ledger.
Next action: Use weekly harness gardening to report drift and keep remediation explicitly requested.
Debug/RCA (when applicable):
Observed: The repo already had strict AGENTS governance, AI_RULES, SPC rules, active risk ledger, release gates, and verification scripts, but no shared `docs/harness` structure or single PowerShell verification entrypoint.
Root cause: Harness behavior was strong but distributed across several governance and script files.
Fix: Add harness docs, exec-plan directories, a harness structure check, a full verification script, and project command rules.
Harness update needed: yes
Destination: `AGENTS.md`, `docs/harness/`, `docs/exec-plans/`, `scripts/harness_check.ps1`, `scripts/verify.ps1`, `.codex/rules/project.rules`

## Entry: Fresh worktree missing seed/knowledge-base data

Date: 2026-07-11
Task: Fix `triple_parameters["radar"]` always-invalid stub in `chart_analysis_viewmodel.py`; `pytest -q` baseline gate also reported 7 unrelated failures in a fresh worktree.
Changes: Copied 6 missing files into this worktree's `data/` (no code change): `data/ipc_jstd_pillar_seed.json`, `data/spi_process_kb/v1/{manifest,multi_signal_rules,dimension_abnormality_matrix,inspection_checklist,chart_signal_lookup}.json`, `data/spi_process_kb/v1/import_report.txt`.
Impact: `tests/test_spi_process_kb.py`, `tests/test_ipc_pillar_library.py`, `tests/test_data_management_page_tabs.py::test_master_selection_updates_detail_panel` now pass in this worktree.
Verification: `pytest -q tests/test_spi_process_kb.py tests/test_ipc_pillar_library.py tests/test_data_management_page_tabs.py` → 19 passed.
Residual risk: none for this worktree; the same gap will recur in any future fresh worktree/checkout until copied again.
Next action: none required unless the repo later decides to bring this data under version control (explicitly declined for this task — kept as an untracked, per-checkout artifact).
Debug/RCA (when applicable):
Observed: `pytest -q` failed 7 tests on a freshly created worktree, all either returning empty results (`[]`, count `0`) or missing-file assertions, with no exceptions raised.
Root cause: `/data/` is fully git-ignored (`.gitignore:35`). `git worktree add` only materializes committed content, so a new worktree never receives locally-generated files under `data/` that exist only in whichever checkout originally generated them (main repo root, in this case). `app/analytics/ipc_pillar_library.py::load_all_entries()` and `app/services/spi_process_kb_loader.py::load_spi_process_kb()` both degrade silently (return `[]` / partial status) instead of raising when their source file/dir is absent, so the gap surfaces only as test assertion failures, not a clear "file not found" error.
Fix: Copy `data/ipc_jstd_pillar_seed.json` and `data/spi_process_kb/v1/*` from an existing populated checkout (e.g. main repo root) into the new worktree before running the full test suite. No generation script currently exists for `ipc_jstd_pillar_seed.json`; `data/spi_process_kb/v1/*` can alternatively be regenerated via `scripts/import_spi_process_kb_xlsx.py <workbook.xlsx> --out data/spi_process_kb/v1`, but the source `.xlsx` is also git-ignored, so copying the already-generated JSON is simpler.
Harness update needed: yes (this entry)
Destination: `docs/harness/closed-loop-log.md`

## Entry: SQLite vs legacy JSON registries data parity mismatch

Date: 2026-07-12
Task: Fix SQLite active records and legacy JSON registries data parity mismatch.
Changes: Added double-write sync logic to coordinate_registry register/remove and product_spec_registry save/remove functions. Created a one-time sync script to align SQLite with JSON registries.
Impact: Prevented data registries drift in future sessions and resolved 4 existing mismatch findings in master_data_parity_audit.
Verification: run master_data_parity_audit.py and verify total_mismatch_count is 0. verify.ps1 passed successfully.
Residual risk: none.
Next action: None.
Debug/RCA (when applicable):
Observed: master_data_parity_audit.py failed with mismatch count > 0.
Root cause: During migration to SQLite backend in 2026-04, write/save paths in coordinate_registry.py and product_spec_registry.py were updated to only write to SQLite, while leaving legacy JSON registries untouched, leading to synchronization drift.
Fix: Added JSON double-write serialization sync and cascaded delete logic back to coordinate_registry.py and product_spec_registry.py.
Harness update needed: yes (this entry)
Destination: docs/harness/closed-loop-log.md
