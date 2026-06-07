"""L: dashboard_layers KPIs align with process / per_measure (same summary pipeline)."""

from __future__ import annotations

from pathlib import Path
from statistics import mean

from app.analytics.summary_engine import compute_summary
from tests.release_validation.helpers.golden_scenario import load_joined_normal_baseline
from tests.release_validation.helpers.tolerance import (
    assert_with_tolerance,
    load_tolerance_policy,
)


def test_dashboard_layer2_yield_matches_process_overall_yield(golden_root: Path) -> None:
    _sdir, _manifest, joined_df, spec = load_joined_normal_baseline(golden_root)
    summary = compute_summary(joined_df, spec)
    process = summary["process"]
    l2 = process["dashboard_layers"]["layer_2_kpi"]
    assert l2["yield_pct"] == process["overall_yield_pct"]


def test_dashboard_layer2_yield_on_0_100_scale(golden_root: Path) -> None:
    """Contract: overall_yield_pct and layer_2_kpi.yield_pct are percentages 0-100, not 0-1 ratios."""
    _sdir, _manifest, joined_df, spec = load_joined_normal_baseline(golden_root)
    summary = compute_summary(joined_df, spec)
    process = summary["process"]
    l2 = process["dashboard_layers"]["layer_2_kpi"]
    for key in ("yield_pct",):
        y = l2.get(key)
        assert y is not None
        assert 0.0 <= float(y) <= 100.0
    oy = process.get("overall_yield_pct")
    assert oy is not None
    assert 0.0 <= float(oy) <= 100.0


def test_dashboard_layer2_avg_cpk_matches_per_measure_cpk_average(golden_root: Path) -> None:
    _sdir, manifest, joined_df, spec = load_joined_normal_baseline(golden_root)
    policy = load_tolerance_policy(golden_root / "golden_tolerance.json")
    ovr = manifest.get("tolerance_overrides") or {}
    summary = compute_summary(joined_df, spec)
    l2 = summary["process"]["dashboard_layers"]["layer_2_kpi"]
    cpks: list[float] = []
    for _col, pm in summary["per_measure"].items():
        c = ((pm.get("cap") or {}).get("statistics") or {}).get("cpk")
        if c is not None:
            cpks.append(float(c))
    assert cpks, "expected at least one cpk in per_measure"
    expected_avg = mean(cpks)
    assert_with_tolerance(expected_avg, float(l2["avg_cpk"]), "cp", policy=policy, tolerance_overrides=ovr)


def test_dashboard_layers_include_extended_contract_keys(golden_root: Path) -> None:
    _sdir, _manifest, joined_df, spec = load_joined_normal_baseline(golden_root)
    summary = compute_summary(
        joined_df, spec, primary_feature="Volume", workorder_master={"product_name": "GoldenTest"},
    )
    layers = summary["process"]["dashboard_layers"]
    for key in (
        "layer_4_defect_structure",
        "layer_5_spec_analysis",
        "layer_6_product_context",
        "layer_7_engineering_info",
    ):
        assert key in layers
    assert isinstance(layers["layer_4_defect_structure"], dict)
    assert layers["layer_6_product_context"].get("product_name") == "GoldenTest"
