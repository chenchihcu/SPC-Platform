#!/usr/bin/env python3
"""
Aggregate final-audit runtime evidence from Outputs/final_audit/*/summary.json.

Outputs:
- Outputs/final_audit/runtime_report.json (default)
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _collect_summary_paths(input_root: Path) -> list[Path]:
    return sorted(p for p in input_root.glob("*/summary.json") if p.is_file())


def _duration_total(gates: Any) -> float:
    if not isinstance(gates, list):
        return 0.0
    total = 0.0
    for gate in gates:
        if isinstance(gate, dict):
            total += _safe_float(gate.get("duration_sec"), default=0.0)
    return round(total, 3)


def _normalize_entry(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    timestamp = str(payload.get("timestamp") or path.parent.name)
    profile = str(payload.get("profile") or "").strip().lower()
    overall = str(payload.get("overall") or "").strip().lower()
    gates = payload.get("gates")
    return {
        "timestamp": timestamp,
        "profile": profile,
        "overall": overall,
        "total_duration_sec": _duration_total(gates),
        "summary_path": str(path.resolve()),
    }


def _profile_report(entries: list[dict[str, Any]], recent_limit: int) -> dict[str, Any]:
    ordered = sorted(entries, key=lambda x: str(x.get("timestamp") or ""), reverse=True)
    recent = ordered[:recent_limit]
    durations = [float(x.get("total_duration_sec") or 0.0) for x in ordered]
    med: float | None = None
    if durations:
        med = round(float(median(durations)), 3)
    return {
        "run_count": len(ordered),
        "latest": recent[0] if recent else None,
        "recent": recent,
        "median_total_duration_sec": med,
    }


def build_runtime_report(input_root: Path, recent_limit: int) -> dict[str, Any]:
    paths = _collect_summary_paths(input_root)
    all_entries: list[dict[str, Any]] = []
    skipped_paths: list[str] = []
    for path in paths:
        payload = _load_json(path)
        if payload is None:
            skipped_paths.append(str(path.resolve()))
            continue
        entry = _normalize_entry(path, payload)
        if not entry["profile"]:
            skipped_paths.append(str(path.resolve()))
            continue
        all_entries.append(entry)

    quick_entries = [x for x in all_entries if x["profile"] == "quick"]
    full_entries = [x for x in all_entries if x["profile"] == "full"]
    quick_report = _profile_report(quick_entries, recent_limit=recent_limit)
    full_report = _profile_report(full_entries, recent_limit=recent_limit)

    quick_median = quick_report.get("median_total_duration_sec")
    full_median = full_report.get("median_total_duration_sec")
    ratio: float | None = None
    if isinstance(quick_median, (int, float)) and quick_median > 0 and isinstance(full_median, (int, float)):
        ratio = round(float(full_median) / float(quick_median), 3)

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_root": str(input_root.resolve()),
        "summary_file_count": len(paths),
        "valid_entry_count": len(all_entries),
        "recent_limit": recent_limit,
        "profiles": {
            "quick": quick_report,
            "full": full_report,
        },
        "comparison": {
            "quick_median_sec": quick_median,
            "full_median_sec": full_median,
            "full_over_quick_median_ratio": ratio,
        },
        "skipped_paths": skipped_paths,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build final-audit runtime report")
    parser.add_argument("--input-root", default="Outputs/final_audit", help="Directory containing run folders")
    parser.add_argument(
        "--output",
        default="Outputs/final_audit/runtime_report.json",
        help="Output runtime report path",
    )
    parser.add_argument("--recent-limit", type=int, default=5, help="How many recent runs to keep per profile")
    args = parser.parse_args()

    input_root = Path(args.input_root).resolve()
    if not input_root.exists() or not input_root.is_dir():
        raise SystemExit(f"Input root not found: {input_root}")

    report = build_runtime_report(input_root=input_root, recent_limit=max(1, int(args.recent_limit)))

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = (Path.cwd() / output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
