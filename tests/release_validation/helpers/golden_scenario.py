"""Load golden scenario directories (CSV, JSON manifest, workorder spec)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from app.data.relation.join_engine import JoinEngine


def scenario_path(golden_root: Path, scenario_id: str) -> Path:
    p = golden_root / scenario_id
    if not p.is_dir():
        raise FileNotFoundError(f"missing golden scenario directory: {p}")
    return p


def load_manifest(scenario_dir: Path) -> dict[str, Any]:
    mp = scenario_dir / "expected" / "manifest.json"
    return json.loads(mp.read_text(encoding="utf-8"))


def load_workorder_spec(scenario_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    name = str(manifest.get("workorder_spec_file") or "workorder_spec.json")
    sp = scenario_dir / name
    return json.loads(sp.read_text(encoding="utf-8"))


def load_measurements(scenario_dir: Path) -> pd.DataFrame:
    return pd.read_csv(scenario_dir / "measurements.csv")


def load_coords_optional(scenario_dir: Path, filename: str | None) -> pd.DataFrame | None:
    if not filename:
        return None
    cp = scenario_dir / filename
    if not cp.is_file():
        return None
    return pd.read_csv(cp)


def volume_ul_target_from_spec(spec: dict[str, Any]) -> tuple[float, float, float]:
    v = spec.get("volume") or {}
    return float(v["usl"]), float(v["lsl"]), float(v["target"])


def load_joined_normal_baseline(golden_root: Path) -> tuple[Path, dict[str, Any], pd.DataFrame, dict[str, Any]]:
    """normal_baseline: measurements + coords join (same path as Phase 2 tests)."""
    sdir = scenario_path(golden_root, "normal_baseline")
    manifest = load_manifest(sdir)
    meas = load_measurements(sdir)
    join_exp = manifest.get("expected", {}).get("join") or {}
    coords = load_coords_optional(sdir, join_exp.get("coords_file"))
    if coords is None:
        raise FileNotFoundError("normal_baseline requires coords_file in manifest.expected.join")
    joined_df, _report = JoinEngine.join(coords, meas)
    spec = load_workorder_spec(sdir, manifest)
    return sdir, manifest, joined_df, spec
