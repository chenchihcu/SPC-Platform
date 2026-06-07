@AGENTS.md

# Claude Code Adapter - SPC Platform

Claude Code reads this file first and imports `AGENTS.md` as the shared repo policy source. Keep this file short and Claude-specific; do not duplicate SPC/SPI contracts here.

## Claude-Specific Notes

- Use `CLAUDE.md` as context, not as permission control. Enforced Claude behavior belongs in `.claude/settings.json`, permissions, or hooks.
- Treat `.claude/settings.local.json` as local-only preference state, not shared project policy.
- UI/theme details still live in `.claude/rules/ui_theme.md` and must remain narrower than `AGENTS.md`.
- For non-trivial changes, read `docs/harness/ai-rules-compatibility.md` before editing so tool-switching and one-writer rules stay aligned.
- Generated artifacts stay in `Outputs/`; statistical formulas and thresholds stay governed by `docs/governance/SPC_RULES.md`.

## Verification Pointers

```powershell
python -m ruff check .
python -m mypy app
python -m pytest -q
python scripts/qt_audit.py app/
python scripts/check_launch.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/harness_check.ps1
```
