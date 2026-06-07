# SPC Platform Harness

This folder is the repo-local system of record for closed-loop Codex work. It keeps the root `AGENTS.md` map short while preserving the repository's stricter SPC/SPI governance.

## Sources

- Repo instructions: `AGENTS.md`
- Detailed governance: `docs/governance/AGENTS.md`
- UI/theme harness rules: `AI_RULES.md`
- Statistical authority: `docs/governance/SPC_RULES.md`
- Active risk single source: `docs/open-questions.md`
- Historical decisions: `docs/decision-log.md`
- Verification gate: `scripts/verify.ps1`
- Harness structure check: `scripts/harness_check.ps1`
- Release-focused gate: `scripts/run_release_gate.py`
- Command policy: `.codex/rules/project.rules`

## Operating Model

1. Use `AGENTS.md` as the map.
2. Read the narrow source-of-truth doc for the task.
3. Preserve SPC/SPI statistics, payload contracts, report parity, and UI state semantics unless the user explicitly approves a contract change.
4. Run the relevant verification gate.
5. Deliver with `Changes`, `Impact`, `Verification`, `Residual risk`, and `Next action`; after debugging or Investigation Path work, record reusable Debug/RCA learning in `closed-loop-log.md`.

## Non-goals

- This harness does not change SPC formulas, thresholds, payload shapes, reports, UI behavior, schema, or migration behavior.
- This harness does not replace `docs/open-questions.md` as the active risk ledger.
- This harness does not replace existing Gate A-F governance.
