"""Performance regression gate (P): synthetic 100k rows vs performance_baselines.json."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tests.release_validation.helpers.performance_gate import (
    evaluate_performance_with_retry,
    gate_should_skip,
    load_performance_baselines,
    measure_performance_segments,
    performance_baselines_path,
)


def _result_path_from_env() -> Path | None:
    raw = os.environ.get("RELEASE_PERF_RESULT_PATH", "").strip()
    if not raw:
        return None
    return Path(raw)


def test_performance_regression_synthetic_large_100k(golden_root: Path) -> None:
    base_path = performance_baselines_path(golden_root)
    doc = load_performance_baselines(base_path)
    if gate_should_skip(doc):
        pytest.skip("performance gate skipped (RELEASE_PERF_GATE or baseline performance_gate.skip)")

    scenario_id = "synthetic_large_100k"
    scenarios = doc.get("scenarios") or {}
    baseline = scenarios.get(scenario_id)
    if not isinstance(baseline, dict):
        raise AssertionError(f"missing scenarios.{scenario_id} in performance_baselines.json")

    eval_result = evaluate_performance_with_retry(
        baseline=baseline,
        measure_once=lambda: measure_performance_segments(
            golden_root=golden_root,
            target_rows=int(baseline.get("target_rows") or 100_000),
        ),
    )
    status = str(eval_result["status"])
    failures = list(eval_result["failures"])
    current = dict(eval_result["current"])
    result_payload = {
        "performance_status": status,
        "scenario_id": scenario_id,
        "current": current,
        "baseline_ref": str(base_path.as_posix()),
        "failures": failures,
        "attempt_count": int(eval_result["attempt_count"]),
        "retry_applied": bool(eval_result["retry_applied"]),
        "retry_policy": dict(eval_result["retry_policy"]),
        "attempts": list(eval_result["attempts"]),
        "final_current_source": str(eval_result["final_current_source"]),
    }
    out = _result_path_from_env()
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if status != "PASS":
        detail = json.dumps(failures, indent=2, ensure_ascii=False)
        raise AssertionError(f"performance regression (P): {detail}")
