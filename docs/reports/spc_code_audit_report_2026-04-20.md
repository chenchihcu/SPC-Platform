# SPC Code Audit Report (Backend)

Date: 2026-04-20  
Scope: `app/`, `scripts/`, `tests/`, repo hygiene files (Batch A + Batch B + Batch C + Batch D applied)

## 1) Audit Basis

- Governance and contracts reviewed:
  - `AGENTS.md`
  - `docs/governance/AGENTS.md`
  - `docs/governance/SPC_RULES.md`
  - `README.md`
  - `docs/specs/project_architecture.md`
  - `docs/open-questions.md`
- Triage order followed:
  1. bytecode/runtime coupling
  2. broad exception / silent swallow
  3. encoding corruption
  4. chart-skip masking renderer failures
  5. root-level temp/decompiled artifacts
  6. packaging/README/runtime mismatch

## 2) Verification Gates Executed

- `python -m pytest -q` (baseline before edits) -> PASS (`663 passed in 38.00s`)
- `python C:/Users/user/.codex/skills/spc-code-audit/scripts/scan_repo_quality.py "c:/Users/user/Documents/SPC Platform"` -> PASS (`OK|no-findings`)
- `python -m pytest -q tests/test_import_spi_process_kb_xlsx.py tests/test_report_actions.py` -> PASS (`4 passed`)
- `python -m pytest -q tests/test_scripts_repo_bootstrap.py tests/test_import_spi_process_kb_xlsx.py tests/test_report_actions.py` -> PASS (`5 passed`)
- `python -m ruff check .` -> PASS
- `python -m mypy app` -> PASS (`Success: no issues found in 191 source files`)
- `python -m pytest -q` (after edits) -> PASS (`667 passed in 56.67s`)
- `python scripts/check_launch.py` -> PASS (`[PASS] Application started and rendered successfully.`)
- Post-Batch-D revalidation:
  - `python -m ruff check .` -> PASS
  - `python -m mypy app` -> PASS
  - `python -m pytest -q` -> PASS (`667 passed in 55.25s`)
  - `python scripts/check_launch.py` -> PASS

## 3) Findings (Severity-Ordered)

### High (Resolved in this phase)

1. **Broad exception with partial-import success semantics in KB import script**
  - File: `scripts/import_spi_process_kb_xlsx.py`
  - Previous evidence: `safe_read()` used `except Exception`; flow could end with `0` even when required sheets failed.
  - Applied fix: narrowed to explicit sheet-read exceptions and now returns non-zero when required sheets fail.
  - Regression coverage: `tests/test_import_spi_process_kb_xlsx.py`.

### Medium (Open)

1. **Runtime/source-tree coupling in script entrypoints (`sys.path.insert`)**
  - Files:
    - `scripts/check_launch.py`
    - `scripts/backfill_workorder_dual_fields.py`
    - `scripts/master_data_parity_audit.py`
    - `scripts/import_spi_process_kb_xlsx.py`
    - `scripts/run_release_gate.py`
    - `scripts/run_validation.py`
    - `scripts/record_performance_baseline.py`
  - Applied fix: all above scripts now use shared bootstrap helper `scripts/repo_bootstrap.py::ensure_repo_root_on_sys_path(...)` for deterministic repo-root import setup.
  - Regression coverage: `tests/test_scripts_repo_bootstrap.py`.
2. **Silent fallback in action collection path**
  - File: `app/services/report_actions.py`
  - Previous evidence: `except ImportError: pass` in `collect_pptx_actions()`.
  - Applied fix: replaced silent pass with warning log that indicates fallback mode.
  - Regression coverage: `tests/test_report_actions.py`.

### Low

1. **Historical encoding corruption in audit artifacts (not source corruption)**
  - Files:
    - `Outputs/final_audit/20260403_111410/summary.json`
    - `Outputs/final_audit/20260403_110723/summary.json`
    - `Outputs/final_audit/20260403_110648/summary.json`
  - Evidence: `UnicodeEncodeError: 'cp950'...` plus mojibake fragments in stored summaries.
  - Risk: Historical report readability/forensics impact; no active source-encoding corruption found in `app/` or `scripts/`.
2. **Root-level operational artifact**
  - File: `test_results.txt`
  - Evidence: captured run with `Python 3.14.3` and a historical failure snapshot.
  - Risk: Environment drift/noise in repo root; can confuse baseline interpretation.

## 4) No-Finding Areas

- No `.pyc`/bytecode-owned runtime coupling found in `app/` and `scripts/`.
- No decompiled-source artifacts found in audited source paths.
- No new broad `except Exception` in `app/` business modules from this audit pass.
- Chart renderer core path (`app/services/chart_render.py`) currently re-raises renderer failures after logging, which aligns with "no silent failure" intent.

## 5) Minimal Fix Batches (Status)

### Batch A (single problem: import error semantics) - Applied

- Target: `scripts/import_spi_process_kb_xlsx.py`
- Change intent:
  - Replace broad `except Exception` with specific parse/read exceptions.
  - Track required-sheet failures explicitly.
  - Return non-zero exit code when required sheets fail.
- Implemented tests:
  - `tests/test_import_spi_process_kb_xlsx.py`

### Batch B (single problem: visible fallback in action resolver) - Applied

- Target: `app/services/report_actions.py`
- Change intent:
  - Replace `except ImportError: pass` with explicit fallback marker/logging.
  - Keep output contract stable (no API break).
- Implemented tests:
  - `tests/test_report_actions.py` (fallback warning visibility)

### Batch C (single problem: runtime coupling hardening for scripts) - Applied

- Targets:
  - `scripts/check_launch.py`
  - `scripts/run_validation.py`
  - `scripts/run_release_gate.py`
  - other script entrypoints using `sys.path.insert`
- Change intent:
  - Centralize repo-root resolution and deterministic import bootstrap.
  - Preserve current CLI interfaces.
- Implemented tests:
  - `tests/test_scripts_repo_bootstrap.py`

### Batch D (single problem: artifact hygiene policy) - Applied

- Targets:
  - `.gitignore`
  - `tmp/.gitkeep`
  - `tmp/README.md`
- Applied policy:
  - Ignore noisy root artifacts (`debug-*.log`, `app/debug-*.log`, `test_results.txt`).
  - Introduce `tmp/` as quarantine root for transient artifacts.
  - Keep `tmp/.gitkeep` and `tmp/README.md` tracked as policy anchors.
- Notes:
  - Existing historical artifacts are intentionally not deleted in this phase (non-destructive rollout).

## 6) Residual Risks and Rollback Notes

- Residual risk: Historical root artifacts created before Batch D may still exist until owner-requested cleanup/migration.
- Rollback strategy (for any future batch): revert touched files in the specific batch only; do not cross-mix with SPC formula or UI-layout changes.

## 7) Conclusion

This audit pass confirms baseline quality gates are green and no active SPC formula-contract violations were detected.  
**Batch A + Batch B + Batch C + Batch D are completed** with regression coverage and full-gate revalidation.
