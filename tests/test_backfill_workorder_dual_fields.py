"""CSV-driven workorder dual-field backfill script contract."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def test_backfill_workorder_dual_fields_updates_measurement_session_subprocess() -> None:
    repo = Path(__file__).resolve().parents[1]
    fd, db_str = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db_path = Path(db_str)
    try:
        _run_child(repo, db_path)
    finally:
        db_path.unlink(missing_ok=True)


def _run_child(repo: Path, db_path: Path) -> None:
    code = f"""
import csv
import os
import sys
import tempfile
from pathlib import Path

os.environ["SPC_MASTER_DB_PATH"] = {str(db_path)!r}
sys.path.insert(0, {str(repo)!r})

from app.data.measurement_library import get_measurement_session, save_measurement_session
from scripts.backfill_workorder_dual_fields import run_backfill

sid = save_measurement_session("C:/tmp/backfill_target.csv", product_name="BackfillProduct")
assert sid > 0

fd, csv_str = tempfile.mkstemp(suffix=".csv")
os.close(fd)
csv_path = Path(csv_str)
with csv_path.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "session_id",
            "supplier_work_order_no",
            "outsource_work_order_no",
        ],
    )
    writer.writeheader()
    writer.writerow(
        {{
            "session_id": sid,
            "supplier_work_order_no": "SUP-BF-1",
            "outsource_work_order_no": "OUT-BF-2",
        }}
    )

report = run_backfill(csv_path=csv_path, dry_run=False)
assert report["updated_rows"] == 1
assert report["missing_target_rows"] == 0

row = get_measurement_session(sid)
assert row is not None
assert row["supplier_work_order_no"] == "SUP-BF-1"
assert row["outsource_work_order_no"] == "OUT-BF-2"
assert row["work_order_no"] == ""

csv_path.unlink(missing_ok=True)
"""
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(repo),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
    )
    assert proc.returncode == 0, f"stderr={proc.stderr!r}\nstdout={proc.stdout!r}"
