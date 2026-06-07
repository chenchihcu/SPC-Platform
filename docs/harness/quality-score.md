# Harness Quality Score

This scorecard tracks whether the repository is legible and verifiable for future Codex runs.

| Area | Current | Evidence | Next action |
| --- | --- | --- | --- |
| Knowledge map | Pass | `AGENTS.md` points to governance, SPC rules, risk ledger, decisions, harness docs, exec plans, verify gate, and command rules. | Keep links current when docs move. |
| Verification gate | Pass | `scripts/verify.ps1` runs ruff, mypy, pytest, qt_audit, check_launch, and harness structure check. | Keep release gate separate unless doing release work. |
| Command policy | Pass | `.codex/rules/project.rules` allows only explicit harness and full verification scripts. | Add rules only for repeated safe commands. |
| Closed-loop learning | Watch | `docs/harness/closed-loop-log.md` exists; entries must be added after real debugging lessons. | Review during doc gardening. |
| Active risk control | Pass | `docs/open-questions.md` remains the active risk single source. | Do not create parallel risk ledgers. |
| Release governance | Pass | `scripts/run_release_gate.py` remains release-focused optional validation. | Run for release/release-risk work. |

## Grading Rules

- `Pass`: current and backed by an executable check or clear source.
- `Watch`: current enough to use, but needs recurring review.
- `Fail`: stale, missing, or contradicted by code/config.

Do not lower statistical, release, or global Hard Trigger gates to improve this score.
