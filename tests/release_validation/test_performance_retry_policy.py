"""Retry policy tests for release_validation performance gate (P)."""

from __future__ import annotations

from typing import Any

from tests.release_validation.helpers.performance_gate import (
    aggregate_attempts_median,
    evaluate_performance_with_retry,
    should_retry_near_boundary_failures,
)


def _baseline(*, include_memory: bool = False) -> dict[str, Any]:
    base: dict[str, Any] = {
        "scenario_id": "synthetic_large_100k",
        "target_rows": 100_000,
        "analysis_total_sec": 10.0,
        "spc_sec": 10.0,
        "nelson_sec": 10.0,
        "chart_payload_sec": 10.0,
        "report_export_sec": 10.0,
    }
    if include_memory:
        base["memory_peak_bytes"] = 100
    return base


def _attempt(
    *,
    analysis: float = 10.0,
    spc: float = 10.0,
    nelson: float = 10.0,
    chart: float = 10.0,
    report: float = 10.0,
    memory: int | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "scenario_id": "synthetic_large_100k",
        "target_rows": 100_000,
        "analysis_total_sec": analysis,
        "spc_sec": spc,
        "nelson_sec": nelson,
        "chart_payload_sec": chart,
        "report_export_sec": report,
        "measurement_wall_sec": analysis + chart + report,
        "volume_n": 100_000,
    }
    if memory is not None:
        out["memory_peak_bytes"] = memory
    return out


def test_should_retry_near_boundary_time_failure() -> None:
    failures = [
        {
            "metric": "chart_payload_sec",
            "baseline": 10.0,
            "current": 12.5,
            "ratio": 1.25,
            "limit": 1.2,
        }
    ]
    assert should_retry_near_boundary_failures(failures, time_factor=1.2, retry_upper_factor=1.3) is True


def test_should_not_retry_when_ratio_above_upper_bound() -> None:
    failures = [
        {
            "metric": "chart_payload_sec",
            "baseline": 10.0,
            "current": 13.1,
            "ratio": 1.31,
            "limit": 1.2,
        }
    ]
    assert should_retry_near_boundary_failures(failures, time_factor=1.2, retry_upper_factor=1.3) is False


def test_should_not_retry_on_memory_or_non_time_metric_failure() -> None:
    memory_failures = [
        {
            "metric": "memory_peak_bytes",
            "baseline": 100,
            "current": 150,
            "ratio": 1.5,
            "limit": 1.3,
        }
    ]
    scenario_failures = [
        {
            "metric": "scenario_id",
            "baseline": "synthetic_large_100k",
            "current": "wrong_scenario",
            "ratio": None,
            "limit": None,
        }
    ]
    assert should_retry_near_boundary_failures(memory_failures) is False
    assert should_retry_near_boundary_failures(scenario_failures) is False


def test_aggregate_attempts_median_returns_expected_values() -> None:
    attempts = [
        _attempt(analysis=9.8, spc=0.0090, chart=12.5, report=16.2),
        _attempt(analysis=10.3, spc=0.0100, chart=11.8, report=15.9),
        _attempt(analysis=10.0, spc=0.0095, chart=11.7, report=16.4),
    ]
    agg = aggregate_attempts_median(attempts)
    assert agg["analysis_total_sec"] == 10.0
    assert agg["spc_sec"] == 0.0095
    assert agg["nelson_sec"] == 10.0
    assert agg["chart_payload_sec"] == 11.8
    assert agg["report_export_sec"] == 16.2
    assert agg["measurement_wall_sec"] == 38.1
    assert agg["volume_n"] == 100_000


def test_evaluate_with_retry_uses_three_attempts_on_near_boundary_fail() -> None:
    samples = [
        _attempt(chart=12.5),
        _attempt(chart=11.6),
        _attempt(chart=11.7),
    ]
    call_count = {"n": 0}

    def _measure_once() -> dict[str, Any]:
        idx = call_count["n"]
        call_count["n"] += 1
        return samples[idx]

    result = evaluate_performance_with_retry(
        baseline=_baseline(),
        measure_once=_measure_once,
    )

    assert call_count["n"] == 3
    assert result["retry_applied"] is True
    assert result["attempt_count"] == 3
    assert result["status"] == "PASS"
    assert result["final_current_source"] == "median_of_3_attempts"


def test_evaluate_with_retry_does_not_retry_clear_fail_over_upper_bound() -> None:
    samples = [
        _attempt(chart=13.1),
        _attempt(chart=11.6),  # should never be consumed
    ]
    call_count = {"n": 0}

    def _measure_once() -> dict[str, Any]:
        idx = call_count["n"]
        call_count["n"] += 1
        return samples[idx]

    result = evaluate_performance_with_retry(
        baseline=_baseline(),
        measure_once=_measure_once,
    )

    assert call_count["n"] == 1
    assert result["retry_applied"] is False
    assert result["attempt_count"] == 1
    assert result["status"] == "FAIL"


def test_evaluate_with_retry_does_not_retry_memory_fail() -> None:
    samples = [
        _attempt(memory=150),
        _attempt(memory=90),  # should never be consumed
    ]
    call_count = {"n": 0}

    def _measure_once() -> dict[str, Any]:
        idx = call_count["n"]
        call_count["n"] += 1
        return samples[idx]

    result = evaluate_performance_with_retry(
        baseline=_baseline(include_memory=True),
        measure_once=_measure_once,
    )

    assert call_count["n"] == 1
    assert result["retry_applied"] is False
    assert result["attempt_count"] == 1
    assert result["status"] == "FAIL"
