# Windows Runtime Recovery Runbook (`_overlapped` / `WinError 10106`)

Last updated: 2026-04-20

## Goal

在不修改業務程式碼前提下，排除 Windows host 層的 provider 異常，避免 `asyncio.windows_events -> _overlapped` 載入失敗。

## Symptoms

- `OSError: [WinError 10106] 無法載入或初始化所要求的服務提供者`
- 堆疊常見於：
  - `import asyncio`
  - `import unittest.mock`（間接進入 asyncio）
  - `pytest` 初始化或特定測試執行階段

## Repo-Level Guardrails (already applied)

- `pyproject.toml`: pytest 預設 `-p no:debugging`（避免 `_pytest.debugging -> pdb -> asyncio` 路徑）
- `app/bootstrap/runtime_env.py`: `ensure_home_env()` 補齊 `HOME/USERPROFILE`
- 接入點：`main.py`、`scripts/check_launch.py`、`app/charts/base_chart.py`、`tests/conftest.py`

## Host Recovery Steps

1. 基本健康檢查
```powershell
.venv\Scripts\python.exe -c "import _overlapped; print('OK _overlapped')"
.venv\Scripts\python.exe -c "import asyncio; print('OK asyncio')"
```

2. Winsock reset（需系統管理員）
```powershell
netsh winsock show catalog > "%TEMP%\winsock_before.txt"
netsh winsock reset
```

3. 重新開機後重驗
```powershell
netsh winsock show catalog > "%TEMP%\winsock_after.txt"
.venv\Scripts\python.exe -c "import _overlapped; print('OK _overlapped')"
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts/check_launch.py
```

4. 若仍失敗，檢查 Python runtime 與虛擬環境
```powershell
where python
.venv\Scripts\python.exe -V
```

## Evidence to Record

- `_overlapped` import 結果
- `pytest -q` 與 `scripts/check_launch.py` 結果
- `%TEMP%\winsock_before.txt` / `%TEMP%\winsock_after.txt` 差異摘要

## Rollback

若 host 修復尚未完成，維持 repo 內 guardrails，不回退 `runtime_env` 與 pytest 預設設定。

