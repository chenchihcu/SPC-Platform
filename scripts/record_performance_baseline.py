#!/usr/bin/env python3
"""
Record performance baseline metrics for golden_dataset/performance_baselines.json.

Run from repo root after code changes that intentionally shift performance expectations:
  python scripts/record_performance_baseline.py

Uses the same measurement helper as tests/release_validation/test_performance_regression.py.
"""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path
from statistics import median

try:
    from scripts.repo_bootstrap import ensure_repo_root_on_sys_path
except ImportError:  # pragma: no cover - script entry fallback
    from repo_bootstrap import ensure_repo_root_on_sys_path


def main() -> int:
    ap = argparse.ArgumentParser(description="Record synthetic_large_100k performance baseline JSON.")
    ap.add_argument("--repo-root", default=".", help="Repository root")
    ap.add_argument(
        "--output",
        type=Path,
        default=Path("golden_dataset/performance_baselines.json"),
        help="Output JSON path",
    )
    ap.add_argument("--rows", type=int, default=100_000, help="Synthetic row count (multiple of normal_baseline rows)")
    ap.add_argument(
        "--samples",
        type=int,
        default=3,
        help="Number of repeated measurements; baseline uses median across samples",
    )
    ap.add_argument(
        "--emit-sample-json",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    args = ap.parse_args()

    repo = Path(args.repo_root).resolve()
    if not repo.is_dir():
        print(f"Not a directory: {repo}", file=sys.stderr)
        return 2
    if args.samples < 1:
        print(f"--samples must be >= 1 (got {args.samples})", file=sys.stderr)
        return 2

    ensure_repo_root_on_sys_path(repo)

    def _measure_once() -> dict[str, object]:
        from tests.release_validation.helpers.performance_gate import (  # noqa: E402
            measure_performance_segments,
        )

        golden = repo / "golden_dataset"
        return dict(measure_performance_segments(golden_root=golden, target_rows=args.rows))

    if args.emit_sample_json:
        print(json.dumps(_measure_once(), ensure_ascii=False))
        return 0

    def _measure_once_subprocess() -> dict[str, object]:
        cmd = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--repo-root",
            str(repo),
            "--rows",
            str(args.rows),
            "--samples",
            "1",
            "--emit-sample-json",
        ]
        proc = subprocess.run(
            cmd,
            cwd=repo,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=2400,
            check=False,
        )
        if proc.returncode != 0:
            print(proc.stdout, file=sys.stderr)
            print(proc.stderr, file=sys.stderr)
            raise RuntimeError(f"sample subprocess failed: rc={proc.returncode}")
        lines = [line for line in proc.stdout.splitlines() if line.strip()]
        if not lines:
            raise RuntimeError("sample subprocess returned empty output")
        raw = json.loads(lines[-1])
        if not isinstance(raw, dict):
            raise RuntimeError("sample subprocess JSON must be an object")
        return dict(raw)

    samples: list[dict[str, object]] = []
    scenario_id: str | None = None
    for _ in range(args.samples):
        measured = _measure_once_subprocess()
        measured_scenario = str(measured.get("scenario_id") or "synthetic_large_100k")
        if scenario_id is None:
            scenario_id = measured_scenario
        elif measured_scenario != scenario_id:
            print(
                f"Inconsistent scenario_id across samples: expected {scenario_id}, got {measured_scenario}",
                file=sys.stderr,
            )
            return 2
        samples.append(dict(measured))

    assert scenario_id is not None  # guarded by args.samples >= 1

    def _median_float(key: str) -> float:
        vals = [float(sample[key]) for sample in samples if sample.get(key) is not None]
        if not vals:
            raise ValueError(f"missing metric in sampled results: {key}")
        return round(float(median(vals)), 4)

    target_rows = int(samples[0].get("target_rows") or args.rows)
    median_metrics: dict[str, object] = {
        "analysis_total_sec": _median_float("analysis_total_sec"),
        "spc_sec": _median_float("spc_sec"),
        "chart_payload_sec": _median_float("chart_payload_sec"),
        "report_export_sec": _median_float("report_export_sec"),
    }
    memory_vals = [int(sample["memory_peak_bytes"]) for sample in samples if sample.get("memory_peak_bytes") is not None]
    if memory_vals:
        median_metrics["memory_peak_bytes"] = int(median(memory_vals))

    doc = {
        "schema_version": "1",
        "description": "Reference timings for performance regression gate (P). Update via: python scripts/record_performance_baseline.py",
        "baseline_toolchain": {
            "python": platform.python_version(),
            "os": sys.platform,
            "recorded_note": f"Recorded by scripts/record_performance_baseline.py (median of {args.samples} samples)",
        },
        "performance_gate": {"skip": False},
        "scenarios": {
            scenario_id: {
                "scenario_id": scenario_id,
                "target_rows": target_rows,
                **median_metrics,
            }
        },
    }

    out = args.output
    if not out.is_absolute():
        out = (repo / out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
