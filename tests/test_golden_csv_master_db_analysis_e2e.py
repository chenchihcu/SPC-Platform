"""Watchlist #7 optional B: golden CSV join + isolated master DB + analysis payload (subprocess)."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def test_normal_baseline_csv_with_temp_master_db_produces_payload() -> None:
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
import json
import os
import sys
from pathlib import Path

import pandas as pd

os.environ["SPC_MASTER_DB_PATH"] = {str(db_path)!r}
sys.path.insert(0, {str(repo)!r})

from app.data.product_spec_registry import STENCIL_NORMAL, save as save_spec
from app.data.relation.join_engine import JoinEngine
from app.services.spec_resolver import resolve_workorder_spec
from app.viewmodels.chart_analysis_viewmodel import compute_analysis_payload

prod = "GoldenNormalDbCsvE2E"
assert save_spec({{
    "product_name": prod,
    "stencil_type": STENCIL_NORMAL,
    "thickness_main": 0.12,
    "default_volume_target": 100.0,
    "default_volume_lsl": 80.0,
    "default_volume_usl": 120.0,
    "default_area_target": 100.0,
    "default_area_lsl": 80.0,
    "default_area_usl": 120.0,
}})

golden = Path({str(repo)!r}) / "golden_dataset" / "normal_baseline"
spec_file = json.loads((golden / "workorder_spec.json").read_text(encoding="utf-8"))
meas = pd.read_csv(golden / "measurements.csv")
coord = pd.read_csv(golden / "coords.csv")
joined, _meta = JoinEngine.join(coord, meas)

wo, err = resolve_workorder_spec(prod)
assert err is None, err
assert float(wo["volume"]["target"]) == float(spec_file["volume"]["target"])
assert float(wo["volume"]["lsl"]) == float(spec_file["volume"]["lsl"])
assert float(wo["volume"]["usl"]) == float(spec_file["volume"]["usl"])

u = float(wo["volume"]["usl"])
l = float(wo["volume"]["lsl"])
t = float(wo["volume"]["target"])
payload, perr = compute_analysis_payload(joined, ["Volume"], u, l, t, workorder_spec=wo)
assert perr is None, perr
assert payload is not None
assert payload.get("summary") is not None
vol = (payload.get("summary") or {{}}).get("per_measure", {{}}).get("Volume", {{}})
assert vol, "expected Volume in summary"
"""
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(repo),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert proc.returncode == 0, f"stderr={proc.stderr!r}\nstdout={proc.stdout!r}"
