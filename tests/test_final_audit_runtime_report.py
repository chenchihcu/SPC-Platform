"""Runtime report aggregation for final audit quick/full profiles."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    repo = Path(__file__).resolve().parents[1]
    path = repo / "scripts" / "final_audit_runtime_report.py"
    spec = importlib.util.spec_from_file_location("_final_audit_runtime_report_under_test", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_summary(
    root: Path,
    timestamp: str,
    profile: str,
    gate_durations: list[float],
) -> None:
    run_dir = root / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": timestamp,
        "profile": profile,
        "overall": "pass",
        "gates": [{"duration_sec": x} for x in gate_durations],
    }
    (run_dir / "summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def test_runtime_report_builds_quick_full_recent_and_median(tmp_path: Path) -> None:
    mod = _load_module()
    input_root = tmp_path / "Outputs" / "final_audit"
    _write_summary(input_root, "20260420_090000", "quick", [1.0, 2.0])  # 3.0
    _write_summary(input_root, "20260420_100000", "quick", [2.0, 3.0])  # 5.0
    _write_summary(input_root, "20260420_110000", "full", [5.0, 7.0])   # 12.0
    _write_summary(input_root, "20260420_120000", "full", [6.0, 8.0])   # 14.0

    report = mod.build_runtime_report(input_root=input_root, recent_limit=2)
    quick = report["profiles"]["quick"]
    full = report["profiles"]["full"]
    comparison = report["comparison"]

    assert quick["run_count"] == 2
    assert full["run_count"] == 2
    assert quick["latest"]["timestamp"] == "20260420_100000"
    assert full["latest"]["timestamp"] == "20260420_120000"
    assert quick["median_total_duration_sec"] == 4.0
    assert full["median_total_duration_sec"] == 13.0
    assert comparison["full_over_quick_median_ratio"] == 3.25
