# SPC Platform Harness

This folder is the repo-local system of record for closed-loop Codex work. It keeps the root `AGENTS.md` map short while preserving the repository's stricter SPC/SPI governance.

## Sources

- Repo instructions: `AGENTS.md`
- Detailed governance: `docs/governance/AGENTS.md`
- UI/theme harness rules: `.claude/rules/ui_theme.md`
- Statistical authority: `docs/governance/SPC_RULES.md`
- Active risk single source: `docs/open-questions.md`
- Historical decisions: `docs/decision-log.md`
- Verification gate: `scripts/verify.ps1`
- Harness structure check: `scripts/harness_check.ps1`
- Canonical change routing: `.agents/skills/spc-change-router/route-table.json` and its `SKILL.md` table
- Hook projection and consumer: `.claude/skills/spc-change-router/route-table.json`, `.claude/hooks/changed-path-advisor.ps1`
- Release-focused gate: `scripts/run_release_gate.py`
- DB-backed chart semantic gate: `scripts/validate_db_chart_semantics.py`
- Command policy: `.codex/rules/project.rules`

## Operating Model

1. Use `AGENTS.md` as the map.
2. Read the narrow source-of-truth doc for the task.
3. Preserve SPC/SPI statistics, payload contracts, report parity, and UI state semantics unless the user explicitly approves a contract change.
4. Run the relevant verification gate. For chart statistics, resolver, density, pair, or triple-feature semantic changes, run `scripts/validate_db_chart_semantics.py` against real DB/session data when available.
5. Deliver with `Changes`, `Impact`, `Verification`, `Residual risk`, and `Next action`; after debugging or Investigation Path work, record reusable Debug/RCA learning in `closed-loop-log.md`.

## Change Routing Verification

Edit canonical routing JSON and both skill tables together, then copy the JSON to the Claude projection. The harness validates its structure, regexes, document targets, conditional full/launch gates, and exact JSON parity. `tests/test_change_router.py` exercises the real hook in PowerShell 7 and Windows PowerShell 5 when installed, including route categories, path separators, near matches, invalid JSON, and the complete harness. Its negative fixtures never change the live table.

The optional CLI rule has been retired from the mandatory project checks. Hook output remains advisory; a direct script test does not prove that a Claude client loaded or invoked the hook.

## Chart Statistics Semantic Gate

Use this gate when contract/renderability checks are insufficient:

```powershell
.venv\Scripts\python.exe scripts\validate_db_chart_semantics.py --db data\spc_master.db --latest-session --output Outputs\db_chart_semantics_current --quiet
```

Use `--session-id <id>` for exact replay. Passing means chart availability/resolver consistency, pair expansion, density mode, and selected statistics recomputed from joined measurement+coordinate data match the active spec.

## Non-goals

- This harness does not change SPC formulas, thresholds, payload shapes, reports, UI behavior, schema, or migration behavior.
- This harness does not replace `docs/open-questions.md` as the active risk ledger.
- This harness does not replace existing Gate A-F governance.
# V1–V3 validation entry

Record invalidated surfaces and direct consumers before selecting gates. V1 is focused, V2 is a subsystem/targeted matrix, and V3 is full only for shared/cross-subsystem/public-contract/release or weak/failed impact evidence.
