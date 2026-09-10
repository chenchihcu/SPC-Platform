---
name: spc-change-router
description: "把 SPC Platform 任務路由到正確來源文件、reviewer 與驗證 gate。Use when 開始 SPC Platform 變更前需分類任務並決定先讀哪份文件、reviewer 與驗證 gate。Do NOT use for 直接實作分析引擎契約（改用 analytics-engine-contract）、圖表語意驗證（改用 spc-db-chart-semantics-validator）或通用 SAST（改用 audit-codebase-security）。"
metadata:
  version: "1.0.1"
---

# SPC Change Router

Classify the task before changing code. Keep routing concise and use existing repo guardrails.

## Route Table

> 機器可讀路由（正本位於 `.agents/skills/spc-change-router`）:[`route-table.json`](route-table.json)(`changed-path-advisor.ps1` hook 執行期讀取;pathRegex/docs/reviewer/gates 以 JSON 為準)。下表為人類可讀鏡像——**改路由先改 JSON,再同批更新本表**。

| Task surface | Read first | Prefer reviewer | Minimum verification |
|---|---|---|---|
| UI/theme/chart visuals | `.claude/rules/ui_theme.md`, `docs/specs/ui_state_semantics.md` | `qt-ui-token-auditor` | `.venv/Scripts/python.exe scripts/qt_audit.py app/`; `check_launch.py` only when AGENTS.md H3 launch surfaces are invalidated |
| Analytics/statistics/chart registry | `docs/governance/SPC_RULES.md`, `.claude/skills/analytics-engine-contract/SKILL.md`, `.claude/skills/spc-db-chart-semantics-validator/SKILL.md` | `spc-stat-contract-reviewer` | V1 affected-engine test + `--checks` semantic subset; V2 selected matrix; V3 full pytest only under the declared V3 conditions |
| Reports/PPTX/Excel exports | `README.md`, `docs/specs/project_architecture.md` | `report-export-parity-reviewer` | V1 focused export test; V2 export consumer pack; V3 full pytest under the declared V3 conditions; launch only for H3 launch surfaces |
| Docs/harness/Claude automation | `AGENTS.md`, `CLAUDE.md`, `docs/harness/README.md` | none by default | `pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/harness_check.ps1` |
| Release validation/performance | `docs/open-questions.md`, `README.md` validation section | `release-gate-triager` | `.venv/Scripts/python.exe scripts/run_release_gate.py` only when release scope requires it |

## Rules

- Do not change SPC formulas, thresholds, or interpretation rules without an explicit spec-first request.
- Do not accept chart contract/renderability PASS as statistical correctness when real DB/session data is available; use the DB-backed semantic gate for chart statistics, resolver, density, pair, or triple-feature changes.
- Do not treat `Residual risk` in a final response as the active risk ledger; active risks belong in `docs/open-questions.md`.
- Do not add MCP servers for this repo unless the user explicitly asks; first choice is read-only, project-local, no credentials.
- Do not run full verification from hooks. Use explicit gates selected by route.

## Delivery

Report with `Changes`, `Impact`, `Verification`, `Residual risk`, and `Next action`. Add Debug/RCA fields only for debugging, regressions, or repeated failures.
# V0–V3 selection

Route by invalidated surfaces, consumers, and oracle. V0 is read-back/static/parse. V1 single engine uses its focused test plus selected semantic checks; V2 shared helper/subsystem uses target matrix selectors; V3 only for >=4 production files, >=2 subsystems, public/statistical contract, release, weak/unknown oracle, or V1/V2 failure. Full pytest is V3-only; the complete V3 gate also includes `ruff .` and `mypy app` per AGENTS.md H3.

Run `check_launch.py` when bootstrap, entrypoint, shared initialization, runtime dependencies, shared theme, window lifecycle, or release are invalidated. After another patch, rerun only the invalidated gates. Hook output is advisory and never executes these commands.
