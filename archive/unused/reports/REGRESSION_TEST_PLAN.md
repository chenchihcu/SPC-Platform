# REGRESSION_TEST_PLAN

- Timestamp: `20260419_213547`
- Overall target: `pass`

## Required Regression Tests

- `tests/test_qt_audit_cli_stability.py`
- `tests/test_exception_policy_guard.py`
- `tests/test_final_audit_outputs.py`

## Validation Commands

- `python -m ruff check .`
- `python -m mypy app`
- `python -m pytest -q`
- `python scripts/run_final_audit_suite.py --repo-root . --profile full`

## Failed Gate

- None

## Root Cause

- Exception summary: `{}`

## Fix

- Apply minimal patches only to failing modules, then rerun full suite.

## Rerun Evidence

- Summary artifact: `c:/Users/user/Documents/SPC Platform/Outputs/final_audit/20260419_213547/summary.json`
- Markdown artifact: `c:/Users/user/Documents/SPC Platform/Outputs/final_audit/20260419_213547/report.md`
