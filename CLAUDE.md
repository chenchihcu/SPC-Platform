@AGENTS.md

# Claude Code Adapter - SPC Platform

Claude Code reads this file first and imports `AGENTS.md` as the shared repo policy source. Keep this file short and Claude-specific; do not duplicate SPC/SPI contracts here.

## Claude-Specific Notes

- Use `CLAUDE.md` as context, not as permission control. Enforced Claude behavior belongs in `.claude/settings.json`, permissions, or hooks.
- Treat `.claude/settings.local.json` as local-only preference state, not shared project policy.
- UI/theme details still live in `.claude/rules/ui_theme.md` and must remain narrower than `AGENTS.md`.
- For non-trivial changes, read `docs/harness/ai-rules-compatibility.md` before editing so tool-switching and one-writer rules stay aligned.
- Generated artifacts stay in `Outputs/`; statistical formulas and thresholds stay governed by `docs/governance/SPC_RULES.md`.
- In the Bash tool, bare `python` fails silently (exit 49, no output); always invoke `.venv/Scripts/python.exe` explicitly.
- Before `git add -A` / commit, re-check `git log --oneline -3`: parallel AI sessions in this checkout have previously advanced HEAD mid-task and swept in-flight edits into their own commits (see decision-log 2026-07-12). Verify HEAD matches expectations and review any foreign commits first.

## Verification Pointers

```powershell
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m mypy app
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe scripts/qt_audit.py app/
.venv/Scripts/python.exe scripts/check_launch.py
.venv/Scripts/python.exe .claude/skills/spc-validation-matrix/scripts/run_matrix.py --quick   # when chart registry/routing changes (~7s, 129 cells)
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/harness_check.ps1
```
