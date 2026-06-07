---
name: run-SPC
description: Run and verify the SPC Platform Windows/PySide6 app. Use when launching the app, checking startup, validating Qt offscreen startup, choosing the Python runtime, or confirming check_launch.py passed.
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
