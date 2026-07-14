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

## Entry: SQLite vs legacy JSON registries data parity mismatch & test isolation

Date: 2026-07-13
Task: Fix SQLite active records and legacy JSON registries data parity mismatch, and resolve test isolation failures.
Changes: Added double-write sync logic to coordinate_registry register/remove and product_spec_registry save/remove functions. Exposed isolated JSON path helpers (`coordinate_json_path`, `spec_json_path`, `assignment_json_path`) in master_data_db and apply them across registries to prepend the DB name stem under testing environment (`SPC_MASTER_DB_PATH`).
Impact: Prevented data registries drift in future sessions, resolved 4 existing mismatch findings, and fixed pytest e2e test failures caused by test database initialization pollution.
Verification: `master_data_parity_audit.py` returns mismatch count 0; `pytest -v tests/test_product_spec_library_master_db_e2e.py` passed; full `verify.ps1` passed successfully (862 passed).
Residual risk: none.
Next action: None.
Debug/RCA (when applicable):
Observed: `master_data_parity_audit.py` failed with mismatch count > 0; and `test_product_spec_library_master_db_e2e.py` failed in subprocess e2e tests due to extra version count.
Root cause: During migration to SQLite backend in 2026-04, legacy JSON registries were left unsynced. When double-write sync was first added, it wrote directly to the production JSON path (`data/product_spec_registry.json`) even during E2E subprocess runs. The polluted production JSON was subsequently read during temp DB schema migrations for other test cases, inflating the version count.
Fix: Added JSON double-write serialization sync, and introduced DB-stem-prefixed JSON isolation to ensure temp test sessions do not touch or load production JSON data.
Harness update needed: yes (this entry)
Destination: docs/harness/closed-loop-log.md

## Entry: DB chart semantic gate false-green paths

Date: 2026-07-13
Task: Harden the DB-backed chart semantic validator and its routed matrix/governance gates.
Changes: Added blocking density-mode, exact-pair identity, and aligned-point assertions plus independent Hotelling checks; fixed pair-density resolution, Hotelling invalid contracts, and safe ERROR fallback for invalid output paths; made matrix quick cover arities 1/2/3 with non-zero blocking exits; and added executable command-policy/mirror/gateway checks to the harness.
Impact: A recorded-but-wrong density mode, bivariate payload for the wrong feature pair, incomplete Hotelling/Radar/LISA deterministic payload, matrix FAIL, malformed Codex rule, or the known stale Cursor absolute path can no longer be reported as a green local gate when the corresponding checker is available. Actual Cursor UI rule loading remains a manual verification boundary.
Verification: Focused pytest 45 PASS / 1 SKIP; real DB session 5 replay 185/185 semantic checks PASS; matrix quick 129/129 PASS; `codex execpolicy check` allow; harness, ruff, mypy (195 files), pytest (887 PASS / 1 SKIP), and `check_launch.py` PASS.
Residual risk: Exact Monte Carlo LISA p-values remain non-deterministic; the gate instead checks their range/length and independently validates deterministic LISA fields plus classifications derived from the emitted p-values. The symlink escape test is explicitly skipped where Windows does not grant symlink creation privilege; ordinary path traversal and output containment are verified. Actual Cursor UI rule loading remains not verified. Active risks, if any, remain in `docs/open-questions.md`.
Next action: Keep new chart statistical families on the same independent-recomputation pattern rather than relying on payload contract/renderability alone.
Debug/RCA (when applicable):
Observed: DB replay returned PASS while 3F density was only logged as `univariate`; a wrong-pair bivariate payload could still pass; an invalid output path raised a traceback before the ERROR contract; a full-arity matrix wrote one Hotelling FAIL but exited 0; Codex policy examples failed the official parser; Cursor's always-on gateway linked to a missing old repository.
Root cause: Density metadata was outside the failure sum, the resolver preferred a valid top-level 1F slice before pair expansion and checked only bivariate shape rather than exact feature identity, output resolution ran outside the guarded error path, Hotelling invalid branches overrode empty failure payloads, matrix main unconditionally returned 0, and harness checks counted text without executing the policy parser or checking mirrored assets.
Fix: Convert density modes and pair identity into named semantic checks, require exact pair labels and aligned X/Y points, prefer the matching precomputed pair density, route output/setup failures through a safe machine-readable ERROR fallback, enforce the analytics invalid contract and SPC sample guard, derive matrix exit status from rows, and extend the harness with executable/parser and mirror/path assertions.
Harness update needed: yes
Destination: `tests/`, `scripts/validate_db_chart_semantics.py`, `scripts/harness_check.ps1`, `.codex/rules/project.rules`, `.cursor/rules/agents_gateway.mdc`, and mirrored SPC skills.

## Entry: Report expansion, renderer parity, and grouped-view payload integrity

Date: 2026-07-14
Task: Expand engineering PPTX evidence across all selected features and feature pairs, complete Hotelling T²/Radar/LISA renderers, and add Pad/Image grouped views.
Changes: Introduced explicit per-chart feature contexts; expanded single-feature, pair, and Pad/Image evidence deterministically; completed the report renderer registry; kept grouping variants precomputed behind stable selector keys; and separated Radar payload completeness from its display-series cap.
Impact: A report no longer silently emits only the first feature or first pair, every registered report chart has a renderer, Pad/Image switching does not rerun analytics, and dense Radar output remains readable without discarding statistical series from the payload.
Verification: Focused tests 99 passed; full pytest 921 passed / 1 skipped; ruff, mypy, `check_launch.py`, Qt audit, harness check, DB semantic replay, 129/129 matrix validation, PPTX render/overflow audit, and 100%/125%/150% DPI inspection passed.
Residual risk: Report page count grows combinatorially with selected features and grouping variants; current three-feature scope passed runtime and output-size gates.
Next action: Any new report chart must add registry-context tests, renderer-parity coverage, and a real-artifact render check in the same change.
Debug/RCA (when applicable):
Observed: Reports used only the first compatible feature context; Hotelling T²/Radar/LISA were registered but lacked report renderers; valid LISA payloads lacked aligned coordinates for rendering; and limiting Radar at the payload layer broke semantic completeness.
Root cause: Feature compatibility, report expansion, payload semantics, and display capacity were represented as one implicit selection path instead of separate contracts.
Fix: Make feature contexts explicit and authoritative, require renderer parity for the chart registry, include renderer-required aligned fields in valid payloads, precompute group variants, and cap only the Radar drawing layer while preserving the full payload.
Harness update needed: yes (this entry and regression tests)
Destination: `docs/harness/closed-loop-log.md`, chart/report registry tests, DB semantic validation, matrix validation, and PPTX artifact QA.
