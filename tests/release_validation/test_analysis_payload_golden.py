"""compute_analysis_payload vs summary / dist KPI; feature switch; spec propagation."""

from __future__ import annotations

from pathlib import Path

from app.analytics.summary_engine import compute_summary
from app.viewmodels.chart_analysis_viewmodel import compute_analysis_payload
from tests.release_validation.helpers.golden_scenario import (
    load_joined_normal_baseline,
    volume_ul_target_from_spec,
)
from tests.release_validation.helpers.tolerance import (
    assert_with_tolerance,
    load_tolerance_policy,
)


def test_payload_summary_matches_compute_summary(golden_root: Path) -> None:
    _sdir, _manifest, joined_df, spec = load_joined_normal_baseline(golden_root)
    usl, lsl, target = volume_ul_target_from_spec(spec)

    payload, err = compute_analysis_payload(
        joined_df, ["Volume"], usl, lsl, target, workorder_spec=spec, workorder_master={},
    )
    assert err is None and payload is not None
    direct = compute_summary(
        joined_df, spec, primary_feature="Volume", workorder_master={},
    )
    # compute_analysis_payload appends enrich_analysis_payload fields on summary.process
    sum_cmp = dict(payload["summary"])
    proc_cmp = dict(sum_cmp.get("process") or {})
    proc_cmp.pop("diagnosis_engine", None)
    proc_cmp.pop("process_risk", None)
    sum_cmp["process"] = proc_cmp
    assert sum_cmp == direct


def test_chart_dist_matches_summary_per_measure_dist(golden_root: Path) -> None:
    _sdir, manifest, joined_df, spec = load_joined_normal_baseline(golden_root)
    policy = load_tolerance_policy(golden_root / "golden_tolerance.json")
    ovr = manifest.get("tolerance_overrides") or {}
    usl, lsl, target = volume_ul_target_from_spec(spec)

    payload, err = compute_analysis_payload(joined_df, ["Volume"], usl, lsl, target, workorder_spec=spec)
    assert err is None and payload is not None

    sum_dist = (payload["summary"]["per_measure"]["Volume"].get("dist") or {}).get("statistics") or {}
    pay_dist = (payload.get("dist") or {}).get("statistics") or {}
    assert_with_tolerance(sum_dist["mean"], pay_dist["mean"], "mean", policy=policy, tolerance_overrides=ovr)
    assert_with_tolerance(sum_dist["std"], pay_dist["std"], "std", policy=policy, tolerance_overrides=ovr)


def test_spc_ooc_count_matches_dashboard_per_feature_alarm(golden_root: Path) -> None:
    """Chart SPC OOC indices align with summary dashboard per_feature_alarm for Volume."""
    _sdir, _manifest, joined_df, spec = load_joined_normal_baseline(golden_root)
    usl, lsl, target = volume_ul_target_from_spec(spec)
    payload, err = compute_analysis_payload(joined_df, ["Volume"], usl, lsl, target, workorder_spec=spec)
    assert err is None and payload is not None
    spc = payload.get("spc") or {}
    spc_data = spc.get("data") or {}
    spc_stats = spc.get("statistics") or {}
    ooc_n = len(spc_data.get("out_of_control_indices") or [])
    spc_n = int(spc_stats.get("n") or 0)
    layers = (payload["summary"].get("process") or {}).get("dashboard_layers") or {}
    per = layers.get("per_feature_alarm") or {}
    row = per.get("Volume")
    assert row is not None
    assert int(row["ooc_count"]) == ooc_n
    assert int(row["sample_n"] or 0) == spc_n


def test_feature_switch_changes_dist_mean(golden_root: Path) -> None:
    _sdir, _manifest, joined_df, spec = load_joined_normal_baseline(golden_root)
    usl, lsl, target = volume_ul_target_from_spec(spec)

    p_vol, e1 = compute_analysis_payload(joined_df, ["Volume"], usl, lsl, target, workorder_spec=spec)
    p_area, e2 = compute_analysis_payload(joined_df, ["Area"], usl, lsl, target, workorder_spec=spec)
    assert e1 is None and e2 is None and p_vol and p_area
    m_vol = (p_vol.get("dist") or {}).get("statistics", {}).get("mean")
    m_area = (p_area.get("dist") or {}).get("statistics", {}).get("mean")
    assert m_vol is not None and m_area is not None
    assert abs(float(m_vol) - float(m_area)) > 1e-6


def test_payload_includes_keys_used_by_report_and_ui_paths(golden_root: Path) -> None:
    """Minimal contract: top-level keys present for downstream report/chart consumers."""
    _sdir, _manifest, joined_df, spec = load_joined_normal_baseline(golden_root)
    usl, lsl, target = volume_ul_target_from_spec(spec)
    payload, err = compute_analysis_payload(joined_df, ["Volume"], usl, lsl, target, workorder_spec=spec)
    assert err is None and payload is not None
    for key in (
        "summary",
        "selected_features",
        "spc",
        "cap",
        "dist",
        "parameters",
        "spatial",
        "pareto",
        "statistical_signals",
        "knowledge_inference",
    ):
        assert key in payload


def test_spec_propagation_changes_capability_cpk(golden_root: Path) -> None:
    _sdir, _manifest, joined_df, spec = load_joined_normal_baseline(golden_root)
    usl, lsl, target = volume_ul_target_from_spec(spec)

    p_tight, _ = compute_analysis_payload(joined_df, ["Volume"], usl, lsl, target, workorder_spec=spec)
    p_loose, _ = compute_analysis_payload(joined_df, ["Volume"], usl + 15.0, lsl - 15.0, target, workorder_spec=spec)
    assert p_tight and p_loose
    cpk_t = ((p_tight.get("cap") or {}).get("statistics") or {}).get("cpk")
    cpk_l = ((p_loose.get("cap") or {}).get("statistics") or {}).get("cpk")
    assert cpk_t is not None and cpk_l is not None
    assert abs(float(cpk_t) - float(cpk_l)) > 1e-6
