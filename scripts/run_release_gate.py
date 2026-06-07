#!/usr/bin/env python3
"""
Run release_validation pytest pack and write release_validation_report.json.

Same pytest/JUnit pipeline as run_validation.py; default output:
Outputs/release_validation_report.json. Exit code 0 only when
final_result.release_allowed is true (all nine section statuses PASS and pytest exit 0).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from scripts.repo_bootstrap import ensure_repo_root_on_sys_path
except ImportError:  # pragma: no cover - script entry fallback
    from repo_bootstrap import ensure_repo_root_on_sys_path


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Run tests/release_validation and emit release gate JSON (exit 0 iff release_allowed)"
    )
    ap.add_argument("--repo-root", default=".", help="Repository root")
    ap.add_argument(
        "--output",
        type=Path,
        default=Path("Outputs/release_validation_report.json"),
        help="Report path (default: Outputs/release_validation_report.json)",
    )
    ap.add_argument(
        "--golden-profile",
        default=os.environ.get("RELEASE_GOLDEN_PROFILE", "default"),
        help="Profile label stored in the report (default: default or RELEASE_GOLDEN_PROFILE)",
    )
    ap.add_argument(
        "pytest_args",
        nargs="*",
        help="Extra arguments forwarded to pytest after tests/release_validation",
    )
    args = ap.parse_args()

    repo = Path(args.repo_root).resolve()
    if not repo.is_dir():
        print(f"Not a directory: {repo}", file=sys.stderr)
        return 2

    ensure_repo_root_on_sys_path(repo)

    py = sys.executable
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as tmp:
        junit_path = Path(tmp.name)

    pytest_cmd = [
        py,
        "-m",
        "pytest",
        "-q",
        "tests/release_validation",
        f"--golden-profile={args.golden_profile}",
        f"--junitxml={junit_path}",
    ] + list(args.pytest_args)

    proc = subprocess.run(
        pytest_cmd,
        cwd=repo,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    rc = int(proc.returncode)

    from validation.report_builder import build_report, write_report

    out = args.output
    if not out.is_absolute():
        out = (repo / out).resolve()

    doc = build_report(
        repo_root=repo,
        junit_path=junit_path,
        pytest_exit_code=rc,
        golden_profile=str(args.golden_profile),
        extra_pytest_args=list(args.pytest_args),
    )
    write_report(out, doc)

    try:
        junit_path.unlink(missing_ok=True)
    except OSError:
        pass

    allowed = bool(doc.get("final_result", {}).get("release_allowed"))
    gate_rc = 0 if allowed else 1
    print(
        f"Wrote {out} (pytest exit {rc}, release_allowed={allowed}, gate exit {gate_rc})",
        flush=True,
    )
    return gate_rc


if __name__ == "__main__":
    raise SystemExit(main())
