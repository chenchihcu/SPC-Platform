# Personal Desktop Audit Readiness Report - 2026-06-12

## Scope

Target: local PySide6 SPC Platform for one personal desktop user.

Out of scope: web app, cloud, SaaS migration, auth, tenant isolation, public API redesign, deployment platform, subscription/billing, or multi-user architecture.

Qualification meaning: all repo-defined gates plus manual/visual/output evidence pass for this personal desktop use case. This is not a legal certification guarantee.

## Change Summary

- Added a behavior-neutral docstring to `ClickableLabel.mousePressEvent` in `app/ui/widgets/control_panel.py`.
- Corrected local venv path drift from the older `spcspi platform v2` location to `C:\Users\user\Documents\SPC Platform\.venv`:
  - `.venv\pyvenv.cfg`
  - `.venv\Scripts\activate`
  - `.venv\Scripts\activate.bat`
  - `.venv\Scripts\activate.fish`
  - regenerated `.venv\Scripts` console launchers
  - corrected `.venv\Scripts\vba_extract.py` shebang
- Cleaned inactive old-path bytes from `data\spc_master.db` with SQLite `VACUUM`; active table query found no old-path records before vacuum.

No SPC formulas, thresholds, chart payload contracts, report schemas, database schema, UI object names, or workflow semantics were intentionally changed.

## Runtime

- Local audit runtime: `.venv\Scripts\python.exe`, Python `3.14.3`.
- Venv prefix verified: `C:\Users\user\Documents\SPC Platform\.venv`.
- Repo/CI expectation remains Python 3.12 unless separately updated by project policy.

## Automated Gate Results

| Gate | Result | Evidence |
|---|---|---|
| `ruff` | PASS | `.venv\Scripts\python.exe -m ruff check .` |
| `mypy` | PASS | `.venv\Scripts\python.exe -m mypy app` |
| `pytest -q` | PASS | `804 passed in 248.59s` |
| `qt_audit` | PASS | `scripts\qt_audit.py app\` reported all clear |
| `check_launch` | PASS | `[PASS] Application started and rendered successfully.` |
| `harness_check` | PASS | `scripts\harness_check.ps1` reported harness check passed |
| `release_check --with-release-ext` | PASS | `Outputs\release\release_report.json`, `overall_ok=true`, `performance_status=PASS` |
| `run_release_gate` | PASS | `Outputs\release_validation_report.json`, `overall_status=PASS`, `release_allowed=true`, `150 passed` |
| Cross-validation matrix | PASS | `Outputs\cross_validation_audit_20260612_implement\SUMMARY.md`, `372/372 PASS`, no fail/stall/overload/error/skip |
| Final audit suite | PASS | `Outputs\final_audit\20260612_050711\report.md`, `Overall: pass` |
| Exception scan | PASS | `Outputs\final_audit\20260612_050711\summary.json`, `total=0` |

Supplemental checks:

- `scan_repo_quality.py`: `OK|no-findings`.
- `run_smt_flow_gates.py`: pytest, ruff, and mypy gates passed.

## Performance Evidence

Source: `Outputs\release\release_report.json`.

- `overall_ok=true`
- `performance_status=PASS`
- Scenario: `synthetic_large_100k`
- Current timings:
  - `analysis_total_sec=0.7044`
  - `spc_sec=0.0073`
  - `nelson_sec=0.1097`
  - `chart_payload_sec=5.1418`
  - `report_export_sec=0.3463`
  - `measurement_wall_sec=7.0242`

## Manual Operation Evidence

Current-machine audit walkthrough: PASS.

Evidence path: `Outputs\visual_audit_20260612\visual_manifest.json`.

Covered workflow:

- Launch app shell.
- Load golden desktop fixture into the app session.
- Confirm setup readiness indicators for coordinate, spec, and measurement data.
- Produce analysis payload from `golden_dataset\normal_baseline`.
- Switch chart analysis display through 1F, 2F, and 3F modes.
- Inspect chart interpretation surfaces via visible chart cards/status.
- Inspect diagnostic page.
- Preview report export selection page.
- Export a real PPTX report and verify it opens with `python-pptx`.

PPTX evidence:

- `Outputs\manual_audit_20260612\audit_manual_export_20260612.pptx`
- Size: `262461` bytes
- Opens with `python-pptx`: true
- Slide count: `20`
- Contains expected evidence sections: process status, core diagnosis, process capability, SPC stability, evidence gallery, coverage table, distribution analysis, spatial analysis, variation source analysis, background info, statistics summary, appendix.

Manual boundary: this was an audit-controlled native Qt walkthrough on the current machine, not a separate physical third-party operator session.

## Visual Inspection Evidence

Current-machine native visual inspection: PASS.

Viewport conditions recorded in `Outputs\visual_audit_20260612\visual_manifest.json`:

- OS: Windows 11 (`Windows-11-10.0.26200-SP0`)
- Screen count: `1`
- Available logical viewport: `1280x752`
- Screen geometry: `1280x800`
- Physical system metrics: `2560x1600`
- Device pixel ratio: `2.0`
- Logical DPI: `96.0`
- Physical DPI: `108.049`
- Remote desktop inferred: `false`

Screenshots inspected:

- `Outputs\visual_audit_20260612\01_data_setup.png`
- `Outputs\visual_audit_20260612\02_measurement_library.png`
- `Outputs\visual_audit_20260612\03_chart_analysis_1f.png`
- `Outputs\visual_audit_20260612\03b_chart_analysis_2f.png`
- `Outputs\visual_audit_20260612\03c_chart_analysis_3f.png`
- `Outputs\visual_audit_20260612\04_diagnostic.png`
- `Outputs\visual_audit_20260612\05_report_export.png`
- `Outputs\visual_audit_20260612\06_pptx_export_confirm_dialog.png`

Observed pass criteria on current machine:

- No critical CJK clipping in inspected pages/dialog.
- No incoherent overlapping controls in inspected pages/dialog.
- Primary actions visible.
- Sidebar selected state and action colors distinguishable.
- Status badges readable.
- Chart status/group colors distinguishable.
- Chart limits, legends, and status text readable in 1F/2F/3F captures.
- Report export selection groups and confirmation dialog readable.

DPI matrix boundary:

- Current machine: verified with DPR `2.0`, logical DPI `96.0`.
- `100%`, `125%`, and `150%` OS scaling modes: not verified in this run because the OS scaling environment was not changed and no separate screenshots from those scaling modes were provided.

## Reliable Output Evidence

Reliable output pass: PASS for automated release/golden/matrix gates and current-machine PPTX export.

- Golden/release validation: PASS.
- Statistical validation: PASS.
- Chart validation: PASS.
- Dashboard validation: PASS.
- Report validation: PASS.
- Non-computable validation: PASS.
- Deterministic validation: PASS.
- Feature-switch validation: PASS.
- Cross-validation matrix: PASS, `372/372`.
- Manual PPTX export: PASS, opens with 20 slides and expected evidence sections.

## Active Risks

Source: `docs/open-questions.md`.

- Import worker thread-path verification: monitoring.
- Final audit runtime overhead: monitoring.
- Release validation performance gate convergence: monitoring.
- Windows runtime provider fragility (`_overlapped` / home-less shell): stabilizing.
- Bundled CJK font and chart visual parity across `100%/125%/150%`: stabilizing; current-machine visual pass refreshed, cross-DPI human evidence still not verified.

No active blocker is identified by the current gate evidence.

## Rerun Commands

```powershell
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m mypy app
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts\qt_audit.py app\
$env:QT_QPA_PLATFORM='offscreen'; $env:MPLBACKEND='Agg'; .venv\Scripts\python.exe scripts\check_launch.py
C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\harness_check.ps1
.venv\Scripts\python.exe scripts\release_check.py --skip-ruff --skip-mypy --with-release-ext
.venv\Scripts\python.exe scripts\run_release_gate.py
.venv\Scripts\python.exe .agents\skills\spc-validation-matrix\scripts\run_matrix.py --fixture normal_baseline --output Outputs\cross_validation_<timestamp>
.venv\Scripts\python.exe scripts\run_final_audit_suite.py --repo-root . --profile full
```

## Closeout Environment Checks

- Tracked source/docs old-path scan: PASS, no `spcspi platform v2` hits outside excluded caches/tool worktrees.
- `.venv\Scripts` old-path scan: PASS, no `spcspi platform v2` hits.
- Runtime prefix: `C:\Users\user\Documents\SPC Platform\.venv`.

## Final Status

Audit readiness: PASS with DPI modes not verified.

Pass coverage: repo-defined automated gates, reliable output gates, current-machine manual walkthrough, current-machine visual inspection, runtime path cleanup, and launch verification.

Not verified: separate OS scaling evidence for `100%`, `125%`, and `150%`.
