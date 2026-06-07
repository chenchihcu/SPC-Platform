"""Unit tests for heuristic process_diagnosis_engine (dashboard Layer 8)."""

from __future__ import annotations

import pytest

from app.analytics.process_diagnosis_engine import run_process_diagnosis


def test_priority_from_oos_rate() -> None:
    r = run_process_diagnosis({"oos_rate": 0.03, "total_oos_count": 10})
    assert r["priority"] == "high"
    r = run_process_diagnosis({"oos_rate": 0.01, "total_oos_count": 10})
    assert r["priority"] == "medium"
    r = run_process_diagnosis({"oos_rate": 0.003, "total_oos_count": 10})
    assert r["priority"] == "low"


def test_center_shift_only() -> None:
    r = run_process_diagnosis(
        {
            "mean_shift_pct": 35.0,
            "std_spec_ratio": 0.1,
            "cp": 1.5,
            "cpk": 1.2,
            "oos_rate": 0.01,
            "cluster_ratio": 0.01,
            "total_oos_count": 5,
        }
    )
    assert r["issue_type"] == "process_center_shift"
    assert r["issue_type_display_zh"] == "偏移"
    assert r["process_diagnosis_flags"]["center_shift"] is True


def test_mixed_when_multiple_signals() -> None:
    r = run_process_diagnosis(
        {
            "mean_shift_pct": 40.0,
            "std_spec_ratio": 0.35,
            "cp": 1.2,
            "cpk": 0.9,
            "oos_rate": 0.05,
            "cluster_ratio": 0.08,
            "total_oos_count": 20,
        }
    )
    assert r["issue_type"] == "mixed"
    assert r["issue_type_display_zh"] == "混合"


def test_spec_too_tight() -> None:
    r = run_process_diagnosis(
        {
            "mean_shift_pct": 5.0,
            "std_spec_ratio": 0.1,
            "cp": 2.0,
            "cpk": 1.5,
            "oos_rate": 0.03,
            "cluster_ratio": 0.01,
            "total_oos_count": 30,
        }
    )
    assert r["issue_type"] == "spec_too_tight"
    assert r["process_diagnosis_flags"]["spec_too_tight"] is True


def test_step_stencil_when_rate_spikes() -> None:
    r = run_process_diagnosis(
        {
            "mean_shift_pct": 2.0,
            "std_spec_ratio": 0.1,
            "cp": 1.5,
            "cpk": 1.4,
            "oos_rate": 0.02,
            "step_stencil_oos_rate": 0.05,
            "cluster_ratio": 0.01,
            "total_oos_count": 100,
        }
    )
    assert r["issue_type"] == "step_stencil"
    assert r["process_diagnosis_flags"]["step_stencil_issue"] is True


def test_unknown_when_no_signals() -> None:
    r = run_process_diagnosis(
        {
            "mean_shift_pct": 5.0,
            "std_spec_ratio": 0.1,
            "cp": 1.5,
            "cpk": 1.4,
            "oos_rate": 0.001,
            "cluster_ratio": 0.01,
            "total_oos_count": 0,
        }
    )
    assert r["issue_type"] == "unknown"


def test_process_offset_cp_high_cpk_low() -> None:
    r = run_process_diagnosis(
        {
            "mean_shift_pct": 10.0,
            "std_spec_ratio": 0.12,
            "cp": 1.7,
            "cpk": 1.2,
            "oos_rate": 0.02,
            "cluster_ratio": 0.01,
            "total_oos_count": 10,
        }
    )
    assert r["issue_type"] == "process_offset"


@pytest.mark.parametrize(
    "total,ref_counts,expect_sub",
    [
        (10, [10], "同元件"),
        (0, [], "—"),
    ],
)
def test_defect_pattern_concentration(total: int, ref_counts: list[int], expect_sub: str) -> None:
    top: list[dict[str, object]] = []
    for n in ref_counts:
        top.append({"id": "R1", "oos_count": n})
    r = run_process_diagnosis({"total_oos_count": total, "top_oos_refdes": top, "cluster_ratio": 0.01})
    assert expect_sub in r["defect_pattern_zh"] or r["defect_pattern_zh"] == expect_sub
