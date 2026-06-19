---
name: run-spc
description: 啟動與驗證 SPC Platform 的 Windows/PySide6 應用程式。Use this skill 當要啟動 app、檢查啟動流程、驗證 Qt offscreen 啟動、選擇 Python runtime,或確認 check_launch.py 通過時。觸發詞包含「啟動」「launch app」「check_launch」「Qt offscreen」「startup」「驗證啟動」。
version: 1.0.0
---

# Run SPC

Use this skill to launch or verify the app without rediscovering the Windows runtime recipe.

## Runtime

- Work from the repository root.
- Prefer `.venv\Scripts\python.exe` when it exists.
- Set:
  - `QT_QPA_PLATFORM=offscreen` for automated launch checks.
  - `MPLBACKEND=Agg` for headless chart rendering.
  - `MPLCONFIGDIR=.matplotlib` when Matplotlib cache location matters.

## Startup Verification

Run:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
$env:MPLBACKEND = "Agg"
.venv\Scripts\python.exe scripts\check_launch.py
```

If `.venv\Scripts\python.exe` is unavailable, use `python scripts\check_launch.py` or pass an explicit Python path through `scripts\verify.ps1 -PythonExe <path>`.

The task is not launch-verified until `scripts/check_launch.py` reports `[PASS]`.

## Full Repository Verification

Use the repo gate only when the task scope warrants it:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts\verify.ps1
```

This gate runs ruff, mypy, pytest, qt_audit, check_launch, and harness_check. Do not run it automatically from hooks.
