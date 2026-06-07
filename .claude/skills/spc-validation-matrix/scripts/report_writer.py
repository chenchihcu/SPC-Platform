"""Write the matrix CSV, SUMMARY.md, and per-failure JSON dumps."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

CSV_COLUMNS: list[str] = [
    "fixture",
    "arity",
    "features",
    "chart_id",
    "filter",
    "status",
    "duration_ms",
    "peak_mb",
    "contract_ok",
    "stats_ok",
    "chart_render_ok",
    "export_ok",
    "error",
]


def write_matrix_csv(rows: list[dict[str, Any]], output_dir: Path) -> Path:
    out = output_dir / "matrix.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: _csv_value(row.get(col, "")) for col in CSV_COLUMNS})
    return out


def _csv_value(v: Any) -> Any:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (list, tuple)):
        return "+".join(str(x) for x in v)
    return v


def write_summary_md(
    rows: list[dict[str, Any]], output_dir: Path, wall_clock_s: float
) -> Path:
    counts: Counter[str] = Counter(r["status"] for r in rows)
    fail_rows = [
        r for r in rows if r["status"] in ("FAIL", "ERROR", "STALL", "OVERLOAD")
    ]
    by_chart: Counter[str] = Counter(r["chart_id"] for r in fail_rows)
    by_fixture: Counter[str] = Counter(r["fixture"] for r in fail_rows)
    stalls = [r for r in rows if r["status"] == "STALL"]
    overloads = [r for r in rows if r["status"] == "OVERLOAD"]
    export_fails = [r for r in rows if r.get("export_ok") is False]

    total = len(rows)
    pass_n = counts.get("PASS", 0)
    pct = (100.0 * pass_n / total) if total else 0.0

    lines: list[str] = []
    lines.append("# SPC Validation Matrix — Summary")
    lines.append("")
    lines.append(f"- Total cells: **{total}**")
    lines.append(f"- Wall-clock: **{wall_clock_s:.1f} s**")
    lines.append(f"- Pass rate: **{pct:.1f}%** ({pass_n}/{total})")
    lines.append("")

    lines.append("## Status counts")
    lines.append("")
    lines.append("| Status | Count |")
    lines.append("|---|---:|")
    for status in ("PASS", "FAIL", "STALL", "OVERLOAD", "ERROR", "SKIP"):
        lines.append(f"| {status} | {counts.get(status, 0)} |")
    lines.append("")

    if by_chart:
        lines.append("## Top 10 failing chart_ids")
        lines.append("")
        lines.append("| chart_id | fail count |")
        lines.append("|---|---:|")
        for chart_id, n in by_chart.most_common(10):
            lines.append(f"| `{chart_id}` | {n} |")
        lines.append("")

    if by_fixture:
        lines.append("## Failures by fixture")
        lines.append("")
        lines.append("| fixture | fail count |")
        lines.append("|---|---:|")
        for fixture, n in by_fixture.most_common():
            lines.append(f"| `{fixture}` | {n} |")
        lines.append("")

    if stalls:
        lines.append("## STALL cells")
        lines.append("")
        for row in stalls:
            lines.append(
                f"- `{row['chart_id']}` × {row['features']} × {row['filter']} "
                f"({row['fixture']}) — {row['error']}"
            )
        lines.append("")

    if overloads:
        lines.append("## OVERLOAD cells")
        lines.append("")
        for row in overloads:
            lines.append(
                f"- `{row['chart_id']}` × {row['features']} × {row['filter']} "
                f"({row['fixture']}) — peak {row['peak_mb']:.1f}MB"
            )
        lines.append("")

    if export_fails:
        lines.append("## Export failures")
        lines.append("")
        seen_keys: set[str] = set()
        for row in export_fails:
            key = f"{row['fixture']}::{row['arity']}f::{row['filter']}"
            if key in seen_keys:
                continue
            seen_keys.add(key)
            lines.append(f"- `{key}` — {row.get('error', '')}")
        lines.append("")

    out = output_dir / "SUMMARY.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def write_failure_artifact(
    cell: dict[str, Any],
    slice_dict: Any,
    traceback_str: str,
    output_dir: Path,
) -> None:
    folder = output_dir / "failures"
    folder.mkdir(parents=True, exist_ok=True)
    feat = "+".join(cell.get("features_list", []))
    name = (
        f"{cell['chart_id']}__{cell['arity']}f__{feat or 'noFeat'}"
        f"__{cell['filter']}__{cell['fixture']}.json"
    )
    blob = {
        "cell": cell,
        "slice": _to_jsonable(slice_dict),
        "traceback": traceback_str,
    }
    (folder / name).write_text(
        json.dumps(blob, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def _to_jsonable(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(x) for x in obj]
    return repr(obj)
