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

## Entry: Evidence-driven active-risk convergence

Date: 2026-07-14
Task: Converge the repository active risk ledger without hiding unresolved release cost.
Changes: Revalidated six active items, moved all six to dormant with explicit reactivation triggers, reduced duplicated 3F chart lifecycle code into `BaseChart`, made legacy validators delegate to `SchemaMapper`, and removed duplicate targeted-pack execution from the full audit profile.
Impact: `docs/open-questions.md` now has zero active items instead of six; Watchlist #7 keeps its stable number; D3/D6 and avoidable full-audit orchestration overhead no longer remain active risks.
Verification: lifecycle 18 tests PASS; 5-run 100k CoV 4.59%–6.80%; release gate 150 tests PASS; home-less launch PASS; CJK/readability 11 tests PASS; four pre/post 3F PNG hashes match; focused 33 tests PASS; matrix 129/129 PASS; full pytest 930 PASS / 1 SKIP; Qt audit and launch PASS.
Residual risk: none active; full audit remains an accepted release-only cost at 351.79 seconds, with a 20% mechanical reactivation threshold.
Next action: On the next release, reactivate #5 only if full total or `pytest_full` grows more than 20% above the 2026-07-14 baseline; do not reduce full coverage to keep the ledger empty.
Debug/RCA (when applicable):
Observed: The ledger claimed five active risks but listed six, several latest-evidence dates were stale, and one full-audit invocation exceeded an external 360-second observer timeout while its child pytest continued running.
Root cause: Monitoring items were not retired after durable guards landed, D3/D6 remained deferred despite safe compatibility-preserving convergence paths, and observer timeout was shorter than the now seven-minute full test duration.
Fix: Require current authoritative evidence plus a reactivation condition before moving an item dormant; use exact pre/post render hashes for presentation-only refactors; delegate compatibility wrappers to the single schema authority; measure full audit with a sufficient external window.
Harness update needed: yes (this entry and active ledger update)
Destination: `docs/open-questions.md`, `docs/harness/closed-loop-log.md`, regression tests, release/runtime reports, and matrix/launch gates.

## Entry: Change router repair and optional CLI rule retirement

Date: 2026-09-06
Task: 002#修復 SPC 路由與退役舊工具規則；使用者核准退役、路由對齊及完整 harness 驗證三項工作。
Changes: 退役 `.cursor/rules/vibe-tools.mdc` 並移除活躍依賴；保留 `.agents` 路由正本與 `.claude` 投影，同步兩份 SKILL 表；修正 UI 文件指標、V3 full pytest 與 H3 launch 條件；新增 JSON 結構、regex、文件目標與精確投影檢查。
Impact: 必要 gate 不再依賴選用 CLI 文件。路徑建議維持五類路由，備份檔不會被額外粗略標記誤路由，無效 JSON 會回傳停用警告；hook 只提供建議。
Verification: `tests/test_change_router.py` 的 9 項 unittest 通過，包含 21 種路徑案例、分隔符、重疊路由、純文字 fallback、負向 JSON 與兩版完整 harness。PowerShell 7.6.5 / Windows PowerShell 5.1.26100.9278 各 14 種資料/投影防護情境通過，包含 focused pytest 可留在 V1 的正向案例；新測試檔 ruff 通過。驗證範圍為 V0–V2 的 routing/harness 子系統。
Residual risk: Claude 客戶端實際載入/觸發 hook 為 `not verified`；直接呼叫腳本的證據不等同客戶端整合。產品 Full/Qt/Release 未選定，本次未失效產品或資料契約。
Next action: 後續路由修改應同步正本、投影與 SKILL 表，重跑路由測試及 harness；需要客戶端整合結論時另觀察實際 Claude hook 事件。
Debug/RCA (when applicable):
Observed: 空 JSON 物件在 StrictMode 下拋例外，`AGENTS.md.bak` 被誤路由，UI 路由引用不存在的 `AI_RULES.md` 且 launch 無條件。
Root cause: `.surfaces` 存取位於 catch 外；已取得精確路徑後仍以全文標記新增假路徑；路由資料與現存文件/H3 條件不同步。另 PS5 測試子程序繼承 PS7 模組路徑，環境鍵值大小寫使原清除失效。
Fix: 將讀取及路由錯誤收斂為停用警告；只在無精確路徑時使用 fallback；對齊 JSON 與文件；測試以不分大小寫方式清除繼承的 PSModulePath。
Harness update needed: yes
Destination: `.agents/skills/spc-change-router/`, `.claude/skills/spc-change-router/`, `.claude/hooks/changed-path-advisor.ps1`, `scripts/harness_check.ps1`, `tests/test_change_router.py`, `docs/harness/`。
