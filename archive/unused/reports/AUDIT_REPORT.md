# AUDIT_REPORT

- Timestamp: `20260419_213547`
- Profile: `full`
- Overall: `pass`
- Exception findings: `0`

## Gate Matrix

| Gate | Phase | Status | Return Code | Required |
|---|---|---|---:|---|
| ruff_all | baseline | pass | 0 | true |
| mypy_app | baseline | pass | 0 | true |
| pytest_full | baseline | pass | 0 | true |
| pytest_statistics_pack | statistical_correctness | pass | 0 | true |
| pytest_chart_feature_pack | chart_feature_cross | pass | 0 | true |
| pytest_release_validation_pack | release_validation | pass | 0 | true |
| pytest_ui_runtime_pack | ui_runtime | pass | 0 | true |
| pytest_performance_pack | performance_baseline | pass | 0 | true |
| qt_policy_audit | qt_policy | pass | 0 | false |

## Failed Gate

- None

## Root Cause

- Exception by kind: `{}`
- None

## Fix

- Keep statistical definitions aligned with `docs/governance/SPC_RULES.md`.
- Keep chart/data-flow contract aligned with `docs/reports/chart_contract_audit.md` and `docs/specs/data_contract.md`.
- Narrow exception handlers and preserve existing fallback/log behavior.

## Rerun Evidence

- Summary JSON: `c:/Users/user/Documents/SPC Platform/Outputs/final_audit/20260419_213547/summary.json`
- Run report: `c:/Users/user/Documents/SPC Platform/Outputs/final_audit/20260419_213547/report.md`
- Commands:
- `python -m ruff check .`
- `python -m mypy app`
- `python -m pytest -q`
- `python scripts/run_final_audit_suite.py --repo-root . --profile full`
