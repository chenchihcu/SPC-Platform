#!/usr/bin/env python3
"""
One-shot CSV-driven backfill for measurement_sessions dual-workorder fields.

Accepted CSV columns:
- session_id or id (preferred)
- file_path (fallback identifier)
- supplier_work_order_no
- outsource_work_order_no
- work_order_no (optional legacy fallback source; always persisted as empty string)
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.repo_bootstrap import ensure_repo_root_on_sys_path
except ImportError:  # pragma: no cover - script entry fallback
    from repo_bootstrap import ensure_repo_root_on_sys_path

ensure_repo_root_on_sys_path(Path(__file__).resolve().parents[1])

from app.data.master_data_db import db_conn


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _parse_session_id(row: dict[str, str]) -> int | None:
    raw = _clean(row.get("session_id")) or _clean(row.get("id"))
    if not raw:
        return None
    if not raw.isdigit():
        return None
    return int(raw)


def _read_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        out: list[dict[str, str]] = []
        for row in reader:
            if isinstance(row, dict):
                out.append({str(k): str(v or "") for k, v in row.items()})
        return out


def _resolve_target(conn, session_id: int | None, file_path: str):
    if session_id is not None:
        return conn.execute(
            "SELECT id FROM measurement_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
    if file_path:
        return conn.execute(
            """
            SELECT id
            FROM measurement_sessions
            WHERE file_path = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (file_path,),
        ).fetchone()
    return None


def run_backfill(*, csv_path: Path, dry_run: bool) -> dict[str, Any]:
    rows = _read_rows(csv_path)
    report: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_csv": str(csv_path.resolve()),
        "dry_run": dry_run,
        "total_rows": len(rows),
        "updated_rows": 0,
        "skipped_rows": 0,
        "missing_target_rows": 0,
        "invalid_rows": 0,
        "samples": {
            "updated": [],
            "missing_target": [],
            "invalid": [],
            "skipped": [],
        },
    }

    with db_conn() as conn:
        for index, row in enumerate(rows, start=1):
            session_id = _parse_session_id(row)
            file_path = _clean(row.get("file_path"))
            supplier_work_order_no = _clean(row.get("supplier_work_order_no"))
            outsource_work_order_no = _clean(row.get("outsource_work_order_no"))
            legacy_work_order_no = _clean(row.get("work_order_no"))
            final_outsource = outsource_work_order_no or legacy_work_order_no or supplier_work_order_no

            if session_id is None and not file_path:
                report["invalid_rows"] += 1
                if len(report["samples"]["invalid"]) < 20:
                    report["samples"]["invalid"].append(
                        {"row": index, "reason": "missing session_id/id and file_path"}
                    )
                continue

            if not (supplier_work_order_no or final_outsource):
                report["skipped_rows"] += 1
                if len(report["samples"]["skipped"]) < 20:
                    report["samples"]["skipped"].append(
                        {"row": index, "reason": "no backfill values", "session_id": session_id}
                    )
                continue

            target = _resolve_target(conn, session_id=session_id, file_path=file_path)
            if target is None:
                report["missing_target_rows"] += 1
                if len(report["samples"]["missing_target"]) < 20:
                    report["samples"]["missing_target"].append(
                        {"row": index, "session_id": session_id, "file_path": file_path}
                    )
                continue

            target_id = int(target["id"])
            if not dry_run:
                conn.execute(
                    """
                    UPDATE measurement_sessions
                    SET work_order_no = '',
                        supplier_work_order_no = ?,
                        outsource_work_order_no = ?
                    WHERE id = ?
                    """,
                    (
                        supplier_work_order_no,
                        final_outsource,
                        target_id,
                    ),
                )
            report["updated_rows"] += 1
            if len(report["samples"]["updated"]) < 20:
                report["samples"]["updated"].append(
                    {
                        "row": index,
                        "session_id": target_id,
                        "work_order_no": "",
                        "supplier_work_order_no": supplier_work_order_no,
                        "outsource_work_order_no": final_outsource,
                    }
                )

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill measurement_sessions dual-workorder fields from CSV")
    parser.add_argument("--input-csv", required=True, help="CSV file path")
    parser.add_argument(
        "--output",
        default="Outputs/master_data/workorder_backfill_report.json",
        help="Output JSON report path",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate rows without writing DB updates")
    args = parser.parse_args()

    csv_path = Path(args.input_csv).resolve()
    if not csv_path.exists() or not csv_path.is_file():
        raise SystemExit(f"Input CSV not found: {csv_path}")

    report = run_backfill(csv_path=csv_path, dry_run=bool(args.dry_run))
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = (Path.cwd() / output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
