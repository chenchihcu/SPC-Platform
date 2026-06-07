# CJK Typography Remediation Report

## Scope
- Target: global QSS in `app/ui/theme/dark_stylesheet.py`
- Goal: remove risky intermediate CJK weights (`500`/`600`) and keep only `400`/`700`/`bold` for on-screen Chinese text
- Policy reference: `docs/governance/AGENTS.md` §4, `docs/specs/spec_maintenance_and_alignment.md` §4.1

## Change Summary
- Replaced all `font-weight: 500;` with `font-weight: 400;`
- Replaced all `font-weight: 600;` with `font-weight: 700;`
- Updated guardrail baseline in `tests/test_ui_font_caps.py`:
  - `_STYLESHEET_FONT_WEIGHT_500_BASELINE = 0`
  - `_STYLESHEET_FONT_WEIGHT_600_BASELINE = 0`

## Evidence
- Source scan (`dark_stylesheet.py`): no remaining `font-weight: 500/600`
- Automated verification: `python -m pytest -q` passed

## Visual Verification Matrix (Windows)
This section is required by §4.1 outcome validation. Fill and attach captures per release.

| Item | Required | Status |
|------|----------|--------|
| Page title CJK (example: `工單資料輸入`) | 100% + one of 125/150 | Pending manual check |
| Body/form CJK (example: form labels) | 100% + one of 125/150 | Pending manual check |
| Environment note (OS build, monitor setup, RDP yes/no) | Mandatory | Pending manual note |

## Follow-up
- If any selector needs softer emphasis after switching `600 -> 700`, prefer size/spacing/color hierarchy first.
- Do not reintroduce `500/600`; if a temporary exception is unavoidable, add TODO + owner/date + test + approval as defined in `docs/governance/AGENTS.md`.
