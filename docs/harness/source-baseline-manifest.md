# Source Baseline Manifest - SPC Platform

Last inspected: 2026-05-25

## Purpose

This manifest is the local source-control baseline register for AI-agent handoff. It does not stage, commit, delete, or approve files. It records the current Git boundary and the baseline risks that must be resolved before parallel AI writers or worktree automation are enabled.

Claim types used here: `local-observed`, `audit-inference`, `assumption`, `not verified`.

## Inspection Commands

| Claim | Type | Command or source |
| --- | --- | --- |
| Git root and tracked files | `local-observed` | `C:\Program Files\Git\cmd\git.exe rev-parse --show-toplevel`; `C:\Program Files\Git\cmd\git.exe ls-files` |
| Working tree status | `local-observed` | `C:\Program Files\Git\cmd\git.exe status --short --untracked-files=all` |
| Ignored file surface | `local-observed` | `C:\Program Files\Git\cmd\git.exe status --short --ignored` |
| Governance file presence | `local-observed` | `Test-Path` checks for `AGENTS.md`, `CLAUDE.md`, `.agents/rules`, `.cursor/rules`, `.codex/rules`, and `scripts/harness_check.ps1` |

## Git Boundary Summary

| Field | Type | Value |
| --- | --- | --- |
| Repository path | `local-observed` | `c:\Users\user\Documents\SPC Platform` |
| Git root | `local-observed` | `c:/Users/user/Documents/SPC Platform` |
| Tracked files | `local-observed` | `1` |
| Tracked sample | `local-observed` | `README.md` |
| Modified tracked files | `local-observed` | `1` (`README.md`) |
| Untracked files before this manifest was added | `local-observed` | `656` |
| Ignored-only entries observed | `local-observed` | `52` |
| `source_baseline_status` | `audit-inference` | `not-ready: only README.md is tracked and it is modified` |
| Current writer mode | `audit-inference` | `single writer per worktree` |

## Tracked / Untracked / Ignored Summary

| Group | Type | Observed examples | Baseline meaning |
| --- | --- | --- | --- |
| Tracked source | `local-observed` | `README.md` | Not enough for rollback, diff discipline, or worktree automation. |
| Modified tracked source | `local-observed` | `README.md` | Existing modification must be reviewed before any baseline commit. |
| Untracked governance | `local-observed` | `AGENTS.md`, `CLAUDE.md`, `.agents/rules/agents_gateway.md`, `.cursor/rules/agents_gateway.mdc`, `.cursor/rules/vibe-tools.mdc`, `.codex/rules/project.rules`, `docs/harness/ai-rules-compatibility.md` | Candidate for reviewed baseline tracking. |
| Untracked product source | `local-observed` | `app/`, `scripts/`, `tests/`, `validation/`, `main.py`, `chart_router.py` | Appears to be core project source, but requires reviewed staging. |
| Ignored runtime/generated | `local-observed` | `.env`, `.venv/`, `Outputs/`, `data/`, `tmp/`, `SPC_Platform.exe`, `*.xlsx`, `*.pptx`, caches, Claude worktrees | Must not be captured by blind staging. |
| Local-only tool state | `local-observed` | `.claude/settings.local.json`, `.claude/worktrees/`, `.cursor/skills/` | Keep local-only; do not use as shared policy. |

## File Classification

| List | Type | Items |
| --- | --- | --- |
| `recommended-track-list` | `audit-inference` | `README.md` after review, `AGENTS.md`, `CLAUDE.md`, `.gitignore`, `.editorconfig`, `.gitattributes`, `.env.example`, `pyproject.toml`, `requirements.txt`, `main.py`, `chart_router.py`, `app/**/*.py`, `scripts/**`, `tests/**`, `validation/**`, `docs/**`, `.github/workflows/**`, `.agents/rules/**`, `.agents/skills/**`, `.cursor/rules/**`, `.cursor/plans/**`, `.codex/rules/**`, `.claude/settings.json`, `.claude/hooks/**`, `.claude/rules/**`, `.claude/skills/**`, `.claude/agents/**` |
| `recommended-ignore-list` | `audit-inference` | `.env`, `.env.local`, `.venv/`, `venv/`, `__pycache__/`, `.matplotlib/`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, `Outputs/`, `data/`, `tmp/` generated content, `*.log`, `*.exe`, `*.xlsx`, `*.pptx`, `node_modules/`, `.claude/settings.local.json`, `.claude/worktrees/`, `.claude/**/exports/`, `.claude/**/failures/`, `.claude/**/matrix.csv`, `.cursor/skills/` |
| `needs-user-decision-list` | `audit-inference` | `--help`, `Dashboard.tsx`, `ProcessDashboard.tsx`, `ReportExportDashboard.tsx`, `package.json`, `package-lock.json`, `archive/`, `assets/`, `golden_dataset/`, `sample_data/`, `presentations/`, `references/`, any PDF/CSV/PNG that is a fixture rather than generated output, `.claude/skills/spc-validation-matrix-workspace/**` summary files |
| `do-not-track-list` | `audit-inference` | `.env`, generated outputs, runtime data, executable/package artifacts, cache directories, local-only Claude/Cursor state, generated matrix/export/failure outputs |

## Suspicious Items

| Item | Type | Finding | Action |
| --- | --- | --- | --- |
| `--help` | `local-observed` | Zero-byte root file with a command-like name. | Do not delete automatically; keep in `needs-user-decision-list`. |
| `README.md` | `local-observed` | Only tracked file and currently modified. | Review before staging any baseline. |
| Large untracked source surface | `local-observed` | 656 untracked files before this manifest was added. | Use explicit path lists only; never use `git add .`. |
| Mixed source and generated data | `audit-inference` | Source, fixtures, generated reports, and tool outputs coexist in one checkout. | Keep baseline commit blocked until candidate lists are reviewed. |

## Baseline Commit Readiness

| Gate | Type | Status |
| --- | --- | --- |
| Git root exists | `local-observed` | `pass` |
| Governance files are visible to Git | `local-observed` | `pass` |
| Generated/runtime files are ignored | `local-observed` | `pass with residual risk` |
| Reviewed source baseline exists | `local-observed` | `blocker` |
| Suspicious root file resolved | `local-observed` | `blocker` |
| Worktree automation readiness | `audit-inference` | `blocker until reviewed baseline commit exists` |

## Role Review Simulation

| Role | Result | Basis |
| --- | --- | --- |
| Repo Owner | `blocker` | Only `README.md` is tracked; source baseline is not representative. |
| AI Rules Auditor | `pass with concern` | Gateway files exist, but all governance files except `README.md` remain untracked. |
| Windows Local Developer | `concern` | Repo path contains spaces and a root `--help` file can confuse command handling. |
| Automation Operator | `concern` | Automation must remain local/report-only because worktree baseline is not credible yet. |
| Security / Data Reviewer | `concern` | `.env` is ignored, but fixture vs generated datasets need review before baseline. |
| Release Gate Reviewer | `blocker` | No reviewed source baseline commit exists; `README.md` is already modified. |

## Residual Risk

- `audit-inference`: Parallel AI writing remains unsafe because most code and governance files are untracked.
- `audit-inference`: Fixture data, generated data, and source assets need owner review before a baseline commit.
- `not verified`: Manual Cursor/Antigravity UI rule panels were not opened in this pass.

## Next Action

Keep `SPC Platform` in single-writer mode. Next approved phase should resolve `--help`, review the modified `README.md`, classify datasets/assets/prototypes, run `git add --dry-run -- <approved paths>`, then create a reviewed source baseline commit only after user approval.
