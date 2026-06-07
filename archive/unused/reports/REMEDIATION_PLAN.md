# REMEDIATION_PLAN

- Objective: drive audit to `overall=pass` with `exception_scan.summary.total=0`.
- Current overall: `pass`

## Failed Gate

- None

## Root Cause

- Total exception findings: `0`
- Highest-impact modules (by finding count):
- None

## Minimal Fix

- Replace broad `except Exception` and bare `except:` with narrow exception classes per module risk.
- Keep existing fallback return shape and logging message format.
- Replace raw UI constants with token constants; add missing method docstrings for qt_policy checks.

## Rerun Evidence

- Last run summary: `c:/Users/user/Documents/SPC Platform/Outputs/final_audit/20260419_213547/summary.json`
- Last run markdown: `c:/Users/user/Documents/SPC Platform/Outputs/final_audit/20260419_213547/report.md`
