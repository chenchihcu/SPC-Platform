# AGENTS.md

## Scope
Repository-level domain guardrails for `SPC Platform`.
Global/shared defaults remain in `%USERPROFILE%\\.codex\\AGENTS.md`.

## Repository Rule Boundary
- Keep this file focused on SPC/SPI domain constraints and repository architecture/contracts.
- Keep global generic workflow in `%USERPROFILE%\\.codex\\AGENTS.md`; only add stricter repo rules here.
- If a repository rule conflicts with global defaults, keep the stricter domain rule and document rationale.

## Knowledge Map
- Product/runtime overview: `README.md`.
- Detailed governance: `docs/governance/AGENTS.md` and UI theme rules (`.cursor/rules/ui_theme.mdc` / `.claude/rules/ui_theme.md`).
- Statistical authority: `docs/governance/SPC_RULES.md`.
- Active risk single source: `docs/open-questions.md`.
- Historical decisions: `docs/decision-log.md`.
- Specs and contracts: `docs/specs/`.
- Closed-loop harness: `docs/harness/README.md`, `docs/harness/closed-loop-log.md`, `docs/harness/quality-score.md`, and `docs/harness/doc-gardening.md`.
- AI rules compatibility and source-control boundary: `docs/harness/ai-rules-compatibility.md`, `docs/harness/source-baseline-manifest.md`, `.agents/rules/agents_gateway.md`, `.cursor/rules/agents_gateway.mdc`, `CLAUDE.md`, and `.codex/rules/project.rules`.
- Execution plans: `docs/exec-plans/active/` and `docs/exec-plans/completed/`.
- Verification gate: `scripts/verify.ps1`; harness structure check: `scripts/harness_check.ps1`.
- Command policy: `.codex/rules/project.rules`.

## Harness Operating Model (Repo)
Use this repository in a **harness-first** way: every task must be bounded, testable, and reversible.

### H1. Task Contract (before edits)
- Define `Done` in one sentence.
- Define target output contract (UI behavior, payload, report, or file format).
- Define non-goals (what this task will not change).

### H2. Change Boundary (during edits)
- Patch the smallest scope that fixes the issue.
- Do not cross subsystem boundaries unless required by correctness/stability.
- Preserve backward compatibility unless user explicitly requests contract change.

### H3. Verification Gates (after edits)
Run mandatory baseline gates:
- `python -m ruff check .`
- `python -m mypy app`
- `python -m pytest -q`
- `python scripts/check_launch.py`

If impact is broad (`>=4` production files, `>=2` subsystems, or contract change), expand verification and provide findings-first review output.

### H4. Evidence & Rollback
- Record what was run and what passed/failed.
- If any gate fails, task is not done.
- For risky changes, provide rollback approach (exact files/modules to revert).

## Domain Priorities
1. Statistical correctness (SPC/SPI semantics)
2. Contract stability (payload/UI/report compatibility)
3. Reproducible validation (`ruff`/`mypy`/`pytest`/`check_launch`)
4. Maintainable modular boundaries

## Statistical Contract Rules
- `docs/governance/SPC_RULES.md` is the formula/threshold source of truth.
- Do not change Cp/Cpk/Pp/Ppk, control-chart constants, or interpretation thresholds without spec-first updates.
- If a chart/stat result is not computable, return explicit metadata reason; do not silently infer.

## Analysis & Report Architecture Rules
- Keep `MainWindow` focused on orchestration; move analysis preflight/cache logic to services.
- Keep `ReportService` as coordinator; place domain logic in `app/services/report_*` modules.
- Preserve chart registry single-source behavior in `app/analytics/chart_registry.py`.

## UI & Layout Rules
- Use `app/ui/theme/tokens.py` and shared page templates (`app/ui/widgets/page_templates.py`).
- Avoid hard-coded visual constants in page modules.
- Keep UI state semantics aligned with `docs/specs/ui_state_semantics.md`.
- UI/theme detailed harness rules live in `.cursor/rules/ui_theme.mdc` (or `.claude/rules/ui_theme.md`).

## Data Safety Rules
- Before merge/join, deduplicate lookup-side keys when repetition is possible.
- Sanitize `np.inf`/`-np.inf` before statistical aggregation.
- Do not introduce broad silent exception handlers in analytics/import/report paths.

## Bugfix Scope (Agents)
- **Fix**: wrong results, crashes, resource leaks (including Qt `QThread`/widget lifecycle), or runtime-contract violations.
- **Defer/Avoid**: style-only edits, doc-only churn, type-hint/comment cosmetics, and micro-performance tweaks unless tied to correctness/stability.

## Validation Baseline (Mandatory)
- `python -m ruff check .`
- `python -m mypy app`
- `python -m pytest -q`
- `python scripts/check_launch.py`

Optional release-focused validation:
- `python scripts/run_validation.py` -> `Outputs/validation_report.json`
- `python scripts/run_release_gate.py` -> `Outputs/release_validation_report.json` (exit code 0 only if `release_allowed=true`)

If any step is unavailable, report `not configured` or `not available` explicitly.

## Documentation Sync Rules
When architecture/contracts/validation baseline changes, update in the same task:
- `README.md`
- `docs/specs/project_architecture.md`
- `docs/decision-log.md`
- `docs/open-questions.md` (when residual risks/assumptions change)

## Active Risk Ledger Rules (Repo)
- `docs/open-questions.md` is the single active risk ledger; do not track active residual risks in parallel docs.
- Each active risk item must include: `Scope`, `Risk`, `Current guardrail`, `Next action`, `Revalidation gate`, `Rollback`, `Status`.
- `Next action` must be owner-explicit (no ownerless follow-up text).
- Keep `Watchlist #7` numbering stable for release-validation boundary compatibility.

## Post-Task Verification (Universal Rule)
Every task must pass launch verification:
1. Run `python scripts/check_launch.py`.
2. Any exception/hang means task is incomplete.
3. Continue fixing until `[PASS]` is reported.
4. Completion message must explicitly state launch check passed.

## Closed-loop Harness
- Use the completion impact format for task delivery: `Changes`, `Impact`, `Verification`, `Residual risk`, and `Next action`.
- For debugging, regressions, repeated failures, or Investigation Path work, add Debug/RCA fields: `Observed`, `Root cause`, `Fix`, `Harness update needed`, and `Destination`.
- If a harness update is needed, update the narrowest durable location: repo docs, tests, `scripts/verify.ps1`, `scripts/harness_check.ps1`, `.codex/rules/project.rules`, `.cursor/rules/ui_theme.mdc` (or `.claude/rules/ui_theme.md`), `docs/governance/AGENTS.md`, or this file.
- Keep one-off bug details out of global Codex rules. Promote only reusable SPC/SPI project knowledge into `docs/harness/closed-loop-log.md` or the relevant source-of-truth doc.
- This format does not weaken global Hard Triggers, `blocked`, `not verified`, or `not pass` semantics.
- `Residual risk` is a task-delivery summary, not a parallel active risk ledger. Active residual risks remain in `docs/open-questions.md`.

## Task Exit Criteria (Harness Pass)
A task is complete only when all are true:
- Done state met.
- Output contract preserved (or explicitly updated with user approval).
- Mandatory validation gates executed and reported.
- Known residual risks/assumptions listed.

## Multi-Assistant Coexistence
- **Coexistence Policy:** Codex, Claude Code, Cursor, and Gemini/Antigravity operate in the same workspace. All assistants must treat this file as the authoritative repository policy. Cursor rules are defined in `.cursor/rules/` and point to this file.
- **Gemini (Antigravity) Flow & Workflow Sync:** When operating via Antigravity, strictly follow `~/.gemini/GEMINI.md` triage (L0/L1/M1/F1/F2), implementation plans, and the Gate A~F checklists. Deliverables (plans, tasks, walkthroughs) must use Traditional Chinese (繁體中文). If changes were directly made using Cursor or Claude Code without prior Gemini plan approval, the developer must perform `git diff` when switching back to Gemini, manually update `walkthrough.md` to document changes, and resolve any process gaps before completing the task.
- **Command Policy & Codex Sync Rule:** Any modifications or additions to verification and development commands must be synchronized with the Python-like rules in `.codex/rules/project.rules` to prevent Codex sandbox blocks.
- **AI Rules Compatibility:** Read `docs/harness/ai-rules-compatibility.md` before cross-tool handoff or governance edits. Official claims, local observations, audit inferences, assumptions, and `not verified` items must remain labeled.
- **Source-Control Boundary:** If `git status --short` is noisy, the source baseline is absent, or the repo was just initialized, use one writer per worktree. Do not run parallel writing AI tools in the same checkout. Prefer Antigravity New Worktree Mode for complex or parallel tasks; Local Mode is for small interactive work only.
