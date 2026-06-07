#!/usr/bin/env python3
"""
Release validation check: baseline gates + golden/release_validation pytest pack.

Runs (in order):
  python -m ruff check .
  python -m mypy app
  python -m pytest -q tests/release_validation
  Optional (--with-release-ext): pytest -q on traceability tests outside release_validation pack.

Writes JSON schema v3 to Outputs/release/release_report.json by default (see --output).
Exit code 0 only if every executed step succeeds.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 3
_DEFAULT_OUT = Path("Outputs/release/release_report.json")
_PERF_RESULT_ENV = "RELEASE_PERF_RESULT_PATH"
_OUTPUT_TAIL_LIMIT = 16_384

# Full-repo traceability tests; see docs/open-questions.md Watchlist #7.
_RELEASE_EXT_TEST_PATHS: tuple[str, ...] = (
    "tests/test_data_contract_code_alignment.py",
    "tests/test_spec_resolver_master_db_e2e.py",
    "tests/test_release_check_plan_modules.py",
)
_RELEASE_EXT_STEP_TIMEOUT_SEC = 900


def _repo_root(path: str) -> Path:
    root = Path(path).resolve()
    if not root.is_dir():
        raise SystemExit(f"Not a directory: {root}")
    return root


def _truncate_output(text: str, limit: int = _OUTPUT_TAIL_LIMIT) -> str:
    if len(text) <= limit:
        return text
    return f"... ({len(text) - limit} chars truncated)\n" + text[-limit:]


def _git_head(repo: Path) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        if proc.returncode == 0:
            return (proc.stdout or "").strip() or None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return None


def _golden_scenario_ids(repo: Path) -> list[str]:
    golden = repo / "golden_dataset"
    if not golden.is_dir():
        return []
    out: list[str] = []
    for p in sorted(golden.iterdir()):
        if p.is_dir() and (p / "expected" / "manifest.json").is_file():
            out.append(p.name)
    return out


def _normal_baseline_dataset_version(repo: Path) -> str | None:
    mp = repo / "golden_dataset" / "normal_baseline" / "expected" / "manifest.json"
    try:
        doc = json.loads(mp.read_text(encoding="utf-8"))
        v = doc.get("dataset_version")
        return str(v) if v is not None else None
    except (OSError, json.JSONDecodeError, TypeError):
        return None


def _release_plan_module_index() -> dict[str, Any]:
    """Step 10: traceability to plan modules A–P (see docs/specs/release_validation_gap_matrix.md)."""
    return {
        "A": "tests/release_validation/test_data_contract_golden.py",
        "B": [
            "tests/release_validation/test_partial_spec_golden.py",
            "tests/release_validation/test_spec_stencil_stepped_resolver.py",
        ],
        "C": "tests/release_validation/test_non_computable_golden.py",
        "D": [
            "docs/specs/release_validation_data_flow_and_tolerance.md",
            "tests/release_validation/test_spc_rules_release_authority.py",
            "tests/release_validation/test_spc_rules_numeric_contract.py",
        ],
        "E": "tests/release_validation/test_resolve_chart_payload_golden.py",
        "F": "tests/release_validation/test_three_feature_golden.py",
        "G": "tests/release_validation/test_chart_transparency_golden.py",
        "H": "tests/release_validation/test_cache_state_release_golden.py",
        "I": "tests/release_validation/test_cache_state_release_golden.py",
        "J": "tests/release_validation/test_report_pptx_golden_alignment.py",
        "K": "tests/release_validation/test_report_pptx_golden_alignment.py",
        "L": "tests/release_validation/test_dashboard_layers_alignment_golden.py",
        "M": "tests/release_validation/test_join_conservation_golden.py",
        "N": "tests/release_validation/test_analysis_payload_golden.py",
        "O": "tests/release_validation/test_analysis_payload_golden.py",
        "P": "tests/release_validation/test_performance_regression.py",
    }


def _run_step(
    cmd: list[str],
    cwd: Path,
    timeout_sec: int,
) -> tuple[int, float, str]:
    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_sec,
    )
    elapsed = time.perf_counter() - t0
    out = ((proc.stdout or "") + (proc.stderr or "")).strip()
    return proc.returncode, elapsed, out


def main() -> int:
    ap = argparse.ArgumentParser(description="Release validation check (ruff, mypy, release_validation pytest)")
    ap.add_argument("--repo-root", default=".", help="Repository root directory")
    ap.add_argument(
        "--output",
        type=Path,
        default=_DEFAULT_OUT,
        help=f"JSON report path (default: {_DEFAULT_OUT.as_posix()})",
    )
    ap.add_argument(
        "--final-audit-summary",
        type=Path,
        default=None,
        help="Optional path to final_audit summary.json for traceability (embedded as final_audit_summary_path)",
    )
    ap.add_argument("--skip-ruff", action="store_true", help="Do not run ruff")
    ap.add_argument("--skip-mypy", action="store_true", help="Do not run mypy")
    ap.add_argument("--skip-pytest", action="store_true", help="Do not run release_validation pytest")
    ap.add_argument(
        "--no-perf-result-artifact",
        action="store_true",
        help="Do not set RELEASE_PERF_RESULT_PATH for pytest (skip writing performance_gate_result.json)",
    )
    ap.add_argument(
        "--with-release-ext",
        action="store_true",
        help="After release_validation pytest, run traceability tests (data_contract alignment, "
        "spec_resolver DB e2e, plan_modules shape); see release_ext_paths in report JSON",
    )
    args = ap.parse_args()

    repo = _repo_root(args.repo_root)
    py = sys.executable

    perf_result_path = (repo / "Outputs" / "release" / "performance_gate_result.json").resolve()
    if not args.skip_pytest and not args.no_perf_result_artifact:
        os.environ[_PERF_RESULT_ENV] = str(perf_result_path)

    step_defs: list[tuple[str, list[str], int]] = []
    if not args.skip_ruff:
        step_defs.append(("ruff_check", [py, "-m", "ruff", "check", "."], 600))
    if not args.skip_mypy:
        step_defs.append(("mypy_app", [py, "-m", "mypy", "app"], 1200))
    release_ext_enabled = bool(args.with_release_ext and not args.skip_pytest)
    if not args.skip_pytest:
        step_defs.append(
            (
                "pytest_release_validation",
                [py, "-m", "pytest", "-q", "tests/release_validation"],
                2400,
            )
        )
        if release_ext_enabled:
            step_defs.append(
                (
                    "pytest_release_traceability_ext",
                    [py, "-m", "pytest", "-q", *_RELEASE_EXT_TEST_PATHS],
                    _RELEASE_EXT_STEP_TIMEOUT_SEC,
                )
            )

    if not step_defs:
        print("release_check: no steps selected.", file=sys.stderr)
        return 2

    steps_out: list[dict[str, Any]] = []
    overall_ok = True

    for key, cmd, timeout in step_defs:
        rc, dur, raw = _run_step(cmd, cwd=repo, timeout_sec=timeout)
        ok = rc == 0
        overall_ok = overall_ok and ok
        steps_out.append(
            {
                "key": key,
                "command": cmd,
                "ok": ok,
                "return_code": rc,
                "duration_sec": round(dur, 3),
                "output_tail": _truncate_output(raw),
            }
        )
        status = "ok" if ok else "FAIL"
        print(f"[{key}] {status} rc={rc} ({dur:.1f}s)", flush=True)

    golden = repo / "golden_dataset"
    perf_baseline_path = golden / "performance_baselines.json"
    performance_baseline: dict[str, Any] | None = None
    if perf_baseline_path.is_file():
        try:
            performance_baseline = json.loads(perf_baseline_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            performance_baseline = {"error": "failed_to_read", "path": str(perf_baseline_path)}

    performance_current: dict[str, Any] | None = None
    performance_status: str | None = None
    perf_result_file = perf_result_path if (not args.skip_pytest and not args.no_perf_result_artifact) else None
    if perf_result_file and perf_result_file.is_file():
        try:
            performance_current = json.loads(perf_result_file.read_text(encoding="utf-8"))
            performance_status = str(performance_current.get("performance_status") or "")
        except (OSError, json.JSONDecodeError):
            performance_current = {"error": "failed_to_read", "path": str(perf_result_file)}

    final_audit_summary_path: str | None = None
    if args.final_audit_summary is not None:
        p = args.final_audit_summary
        final_audit_summary_path = str(p.resolve() if not p.is_absolute() else p)

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository_root": str(repo),
        "overall_ok": overall_ok,
        "steps": steps_out,
        "final_audit_summary_path": final_audit_summary_path,
        "performance_baseline": performance_baseline,
        "performance_current": performance_current,
        "performance_status": performance_status,
        "git_commit": _git_head(repo),
        "dataset_version": _normal_baseline_dataset_version(repo),
        "golden_scenarios": _golden_scenario_ids(repo),
        "golden_profile": os.environ.get("RELEASE_GOLDEN_PROFILE", "default"),
        "release_validation_plan_modules": _release_plan_module_index(),
        "release_ext_enabled": release_ext_enabled,
        "release_ext_paths": list(_RELEASE_EXT_TEST_PATHS),
    }

    out_path = args.output
    if not out_path.is_absolute():
        out_path = (repo / out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}", flush=True)

    if _PERF_RESULT_ENV in os.environ:
        del os.environ[_PERF_RESULT_ENV]

    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
