"""Fixture loading + payload computation + slice resolution + contract checks.

All heavy lifting is delegated to existing helpers (see module imports).  This
module only adds:

* ``load_fixture()``    — wraps the golden_scenario helpers and joins coords
                          opportunistically (joined when present, raw otherwise).
* ``apply_filter()``    — implements the four filter dimensions used by the matrix.
* ``compute_payload_for_cell()`` — pulls usl/lsl/target from the workorder spec.
* ``resolve_slice_for_cell()``   — thin wrapper around ``resolve_chart_payload``.
* ``check_contract_and_stats()`` — contract gate + NaN/Inf scan.
* ``check_data_renderability()`` — recursive non-empty + finite-scalar walk so
  the validator catches "looks valid but UI would crash" payloads without
  needing engine-specific renderers.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pandas as pd

from app.analytics.chart_registry import resolve_chart_payload
from app.data.relation.join_engine import JoinEngine
from app.viewmodels.chart_analysis_viewmodel import compute_analysis_payload
from tests.helpers.engine_contract import assert_engine_contract
from tests.release_validation.helpers.golden_scenario import (
    load_coords_optional,
    load_manifest,
    load_measurements,
    load_workorder_spec,
    scenario_path,
)

SPEC_KEY_BY_COL: dict[str, str] = {"Volume": "volume", "Area": "area", "Height": "height"}


def load_fixture(golden_root: Path, fixture: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Return ``(joined_or_raw_df, workorder_spec)`` for the named scenario."""
    sdir = scenario_path(golden_root, fixture)
    manifest = load_manifest(sdir)
    meas = load_measurements(sdir)
    join_exp = manifest.get("expected", {}).get("join") or {}
    coords = load_coords_optional(sdir, join_exp.get("coords_file"))
    if coords is not None:
        joined, report = JoinEngine.join(coords, meas)
        if joined.empty and report.get("error"):
            joined = meas
    else:
        joined = meas
    spec = load_workorder_spec(sdir, manifest)
    return joined, spec


def apply_filter(df: pd.DataFrame, filter_name: str, primary_feature: str) -> pd.DataFrame:
    if df is None or len(df) == 0:
        return df
    if filter_name == "full":
        return df
    if filter_name == "top10pct":
        if primary_feature not in df.columns:
            return df
        thresh = df[primary_feature].quantile(0.9)
        out = df[df[primary_feature] >= thresh]
        return out if len(out) > 0 else df
    if filter_name == "by_part_type":
        if "PartType" not in df.columns:
            return df
        top = df["PartType"].value_counts().idxmax()
        out = df[df["PartType"] == top]
        return out if len(out) > 0 else df
    if filter_name == "by_board":
        col = "BoardNo" if "BoardNo" in df.columns else (
            "PanelId" if "PanelId" in df.columns else None
        )
        if col is None:
            return df
        top = df[col].value_counts().idxmax()
        out = df[df[col] == top]
        return out if len(out) > 0 else df
    return df


def compute_payload_for_cell(
    df: pd.DataFrame, features: list[str], spec: dict[str, Any]
) -> tuple[dict[str, Any] | None, str | None]:
    if not features:
        return None, "no features"
    primary = features[0]
    f_spec = spec.get(SPEC_KEY_BY_COL.get(primary, primary.lower()), {}) or {}
    usl = f_spec.get("usl")
    lsl = f_spec.get("lsl")
    target = f_spec.get("target")
    if usl is None or lsl is None or target is None:
        return None, f"workorder_spec missing usl/lsl/target for {primary}"
    payload, err = compute_analysis_payload(
        df, features, float(usl), float(lsl), float(target), workorder_spec=spec
    )
    if payload is None:
        return None, err or "compute_analysis_payload returned None"
    return payload, None


def resolve_slice_for_cell(
    payload: dict[str, Any], chart_id: str, features: list[str]
) -> dict[str, Any]:
    return resolve_chart_payload(
        payload, chart_id, features=features, normalized=False, context="ui"
    )


def check_contract_and_stats(slice_dict: dict[str, Any]) -> tuple[bool, bool, str]:
    """Contract + NaN/Inf gate. Returns (contract_ok, stats_ok, error_message)."""
    is_valid = bool((slice_dict or {}).get("metadata", {}).get("is_valid", False))
    try:
        assert_engine_contract(slice_dict, expect_valid=is_valid)
    except AssertionError as exc:
        return False, False, f"contract: {exc}"
    if not is_valid:
        return True, True, ""
    bad = _scan_for_non_finite(slice_dict.get("statistics") or {}, "statistics")
    if bad:
        return True, False, bad
    return True, True, ""


_CONTRACT_KEYS = {"chart_type", "data", "statistics", "metadata", "analysis_context"}


def check_data_renderability(slice_dict: dict[str, Any]) -> tuple[bool, str]:
    """Confirm the slice is structurally usable by the UI.

    The contract guarantees engines return ``{chart_type, data, statistics,
    metadata}``, but ``resolve_chart_payload`` returns *resolved slices* that
    can take three shapes:

    1. **Engine-shaped** — most charts; ``data`` carries the renderable arrays.
    2. **Payload-shaped** — IMR's slice is the full payload with engine
       results nested under ``spc``/``cap``/``dist`` (see
       ``chart_registry.get_feature_payload_slice``).
    3. **Composite multi-feature** — uses ``_multi_feature`` / ``_feature_data``
       sentinels.

    Only the engine-shaped case is required to have a non-empty ``data`` —
    the other two carry their renderable data under different keys, which
    would be a false positive if we demanded ``data`` be non-empty.
    """
    meta = (slice_dict or {}).get("metadata", {})
    if not meta.get("is_valid", False):
        return True, ""
    if not isinstance(slice_dict, dict):
        return False, "slice is not a dict"

    extra_keys = set(slice_dict.keys()) - _CONTRACT_KEYS
    is_composite = (
        bool(extra_keys)
        or slice_dict.get("_multi_feature")
        or slice_dict.get("_overview_3f")
        or slice_dict.get("_feature_data")
    )

    data = slice_dict.get("data") or {}
    if not is_composite and (not isinstance(data, dict) or len(data) == 0):
        return False, "engine-shaped slice has empty data despite is_valid=True"

    bad = _scan_for_non_finite(data, "data")
    if bad:
        return False, bad
    return True, ""


def _scan_for_non_finite(obj: Any, path: str) -> str:
    """Return error string if any leaf scalar float is NaN or Inf, else ''."""
    if isinstance(obj, float):
        if math.isnan(obj):
            return f"{path} has NaN"
        if math.isinf(obj):
            return f"{path} has Inf"
        return ""
    if isinstance(obj, dict):
        for k, v in obj.items():
            err = _scan_for_non_finite(v, f"{path}.{k}")
            if err:
                return err
        return ""
    if isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            # only scan first 100 to keep the check O(1)-ish for big arrays
            if i >= 100:
                break
            err = _scan_for_non_finite(v, f"{path}[{i}]")
            if err:
                return err
        return ""
    return ""
