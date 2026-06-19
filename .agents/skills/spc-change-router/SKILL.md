---
name: spc-change-router
version: 1.0.0
description: 把 SPC Platform 任務路由到正確的來源文件、reviewer subagent 與驗證 gate。Use this skill 當任務涉及 UI/theme、analytics engine、chart registry、報告/匯出、docs/harness、release validation,或使用者詢問該跑哪些檢查時。觸發詞包含「該跑什麼檢查」「route」「change router」「驗證 gate」「reviewer」「UI/theme」「analytics engine」。
---

# SPC Change Router

Classify the task before changing code. Keep routing concise and use existing repo guardrails.

## Route Table

| Task surface | Read first | Prefer reviewer | Minimum verification |
|---|---|---|---|
| UI/theme/chart visuals | `AI_RULES.md`, `docs/specs/ui_state_semantics.md` | `qt-ui-token-auditor` | `python scripts/qt_audit.py app/`, `python scripts/check_launch.py` |
| Analytics/statistics/chart registry | `docs/governance/SPC_RULES.md`, `.claude/skills/analytics-engine-contract/SKILL.md` | `spc-stat-contract-reviewer` | focused pytest, then `python .claude/skills/spc-validation-matrix/scripts/run_matrix.py --quick` when routing changes |
| Reports/PPTX/Excel exports | `README.md`, `docs/specs/project_architecture.md` | `report-export-parity-reviewer` | focused pytest plus `python scripts/check_launch.py` |
| Docs/harness/Claude automation | `AGENTS.md`, `CLAUDE.md`, `docs/harness/README.md` | none by default | `pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/harness_check.ps1` |
| Release validation/performance | `docs/open-questions.md`, `README.md` validation section | `release-gate-triager` | `python scripts/run_release_gate.py` only when release scope requires it |

## Rules

- Do not change SPC formulas, thresholds, or interpretation rules without an explicit spec-first request.
- Do not treat `Residual risk` in a final response as the active risk ledger; active risks belong in `docs/open-questions.md`.
- Do not add MCP servers for this repo unless the user explicitly asks; first choice is read-only, project-local, no credentials.
- Do not run full verification from hooks. Use explicit gates selected by route.

## Delivery

Report with `Changes`, `Impact`, `Verification`, `Residual risk`, and `Next action`. Add Debug/RCA fields only for debugging, regressions, or repeated failures.
