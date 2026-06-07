"""Performance regression gate (P): measure end-to-end-ish segments vs performance_baselines.json."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from statistics import median
from typing import Any

from app.analytics.spc_engine import SPCEngine
from app.analytics.pattern_recognition_engine import PatternRecognitionEngine
from app.analytics.summary_engine import compute_summary
from app.data.session_store import SessionStore, _analysis_cache_key
from app.utils.dataframe_utils import detect_order_col
from app.viewmodels.chart_analysis_viewmodel import compute_analysis_payload
from tests.helpers.perf_timing import measure_wall_seconds
from tests.release_validation.helpers.golden_scenario import (
    load_joined_normal_baseline,
    volume_ul_target_from_spec,
)

TIME_METRIC_KEYS: tuple[str, ...] = (
    "analysis_total_sec",
    "spc_sec",
    "nelson_sec",
    "chart_payload_sec",
    "report_export_sec",
)

# `spc_sec` is intentionally excluded from gating. It is derived from a very fast
# micro-segment (sub-10ms) and is disproportionately sensitive to host jitter
# even after repeated averaging. Keep it as an informational metric, but do not
# fail the release gate on it.
GATING_TIME_METRIC_KEYS: tuple[str, ...] = (
    "analysis_total_sec",
    "chart_payload_sec",
    "report_export_sec",
)


def performance_baselines_path(golden_root: Path) -> Path:
    return golden_root / "performance_baselines.json"


def load_performance_baselines(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("performance_baselines.json root must be an object")
    return raw


def _build_synthetic_large_df(golden_root: Path, target_rows: int) -> tuple[Any, dict[str, Any]]:
    _sdir, _manifest, joined_df, spec = load_joined_normal_baseline(golden_root)
    n0 = len(joined_df)
    if n0 <= 0:
        raise ValueError("normal_baseline joined_df is empty")
    if target_rows % n0 != 0:
        raise ValueError(f"target_rows ({target_rows}) must be a multiple of normal_baseline rows ({n0})")
    k = target_rows // n0
    import pandas as pd

    large = pd.concat([joined_df] * k, ignore_index=True)
    return large, spec


@contextmanager
def _patch_chart_render_to_none():
    import app.services.chart_render as chart_render

    original = chart_render.render_chart_to_png_bytes
    chart_render.render_chart_to_png_bytes = lambda *args, **kwargs: None
    try:
        yield
    finally:
        chart_render.render_chart_to_png_bytes = original


def measure_performance_segments(*, golden_root: Path, target_rows: int = 100_000) -> dict[str, Any]:
    """
    Wall-clock segments plus optional process RSS (psutil) for synthetic large join.

    - analysis_total_sec: compute_summary
    - spc_sec: SPCEngine.compute_imr on Volume (ordered like viewmodel)
    - nelson_sec: PatternRecognitionEngine.compute_nelson on Volume
    - chart_payload_sec: compute_analysis_payload (single feature Volume)
    - report_export_sec: ReportService.generate_pptx_report reusing the cached payload with chart render stubbed
    - memory_peak_bytes: optional RSS via psutil when installed; else omitted (gate skips memory)
    """
    large_df, spec = _build_synthetic_large_df(golden_root, target_rows)
    usl, lsl, target = volume_ul_target_from_spec(spec)

    t_block0 = time.perf_counter()

    summary, analysis_total_sec = measure_wall_seconds(lambda: compute_summary(large_df, spec))

    order_col = detect_order_col(large_df)
    _df = large_df.sort_values(order_col) if order_col else large_df
    data_series = _df["Volume"]
    # Single-call IMR timing is sub-10ms and can be noisy under host jitter.
    # Use repeated runs and average to stabilize the regression signal without
    # changing gate thresholds.
    spc_repeats = 5
    spc_runs: list[float] = []
    for _ in range(spc_repeats):
        _, one_run_sec = measure_wall_seconds(lambda: SPCEngine.compute_imr(data_series, "Volume"))
        spc_runs.append(float(one_run_sec))
    spc_sec = float(sum(spc_runs) / float(spc_repeats))
    _, nelson_sec = measure_wall_seconds(
        lambda: PatternRecognitionEngine.compute_nelson(data_series, "Volume")
    )

    def _build_payload() -> dict[str, Any]:
        p, e = compute_analysis_payload(large_df, ["Volume"], usl, lsl, target, workorder_spec=spec)
        if e is not None or p is None:
            raise RuntimeError(f"compute_analysis_payload failed: {e}")
        return p

    payload_for_report, chart_payload_sec = measure_wall_seconds(_build_payload)

    store = SessionStore()
    store.clear()
    report_export_sec = 0.0
    try:
        store.joined_df = large_df.copy()
        store.meas_meta = {"is_valid": True, "missing_required": []}
        store.coord_meta = {"is_valid": True, "missing_required": []}
        store.relation_meta = {"match_rate": 100.0, "unmatch_count": 0}
        store.workorder_spec = spec
        store.selected_features = ["Volume"]
        store.workorder_master = {
            "work_order_no": "PERF-GATE",
            "product_name": "PerfRegression",
            "batch_qty": str(len(large_df)),
        }
        cache_key = _analysis_cache_key(
            ["Volume"],
            "全部 (All)",
            "全部 (All)",
            "全部 (All)",
            spec_version=store.spec_cache_token(spec),
        )
        store.last_analysis_payload = payload_for_report
        store._analysis_cache[cache_key] = payload_for_report

        with _patch_chart_render_to_none():
            import tempfile

            from app.services.report_service import ReportService

            with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
                out = Path(tmp.name)
            try:
                _ok_rerr, report_export_sec = measure_wall_seconds(lambda: ReportService().generate_pptx_report(str(out)))
                ok, rerr = _ok_rerr
                if not ok:
                    raise RuntimeError(f"PPTX export failed: {rerr}")
            finally:
                if out.is_file():
                    out.unlink(missing_ok=True)
    finally:
        store.clear()

    block_sec = time.perf_counter() - t_block0

    mem_peak: int | None = None
    try:
        import psutil  # type: ignore[import-untyped]

        mem_peak = int(psutil.Process(os.getpid()).memory_info().rss)
    except Exception:
        mem_peak = None

    out: dict[str, Any] = {
        "scenario_id": "synthetic_large_100k",
        "target_rows": target_rows,
        "analysis_total_sec": round(analysis_total_sec, 4),
        "spc_sec": round(spc_sec, 4),
        "nelson_sec": round(nelson_sec, 4),
        "chart_payload_sec": round(chart_payload_sec, 4),
        "report_export_sec": round(report_export_sec, 4),
        "measurement_wall_sec": round(block_sec, 4),
        "report_payload_cache_seeded": True,
        "volume_n": int((summary.get("per_measure", {}).get("Volume") or {}).get("n") or 0),
    }
    if mem_peak is not None:
        out["memory_peak_bytes"] = mem_peak
    return out


def should_retry_near_boundary_failures(
    failures: Sequence[Mapping[str, Any]],
    *,
    time_factor: float = 1.2,
    retry_upper_factor: float = 1.3,
) -> bool:
    """Retry only for time-metric failures in the near-boundary window."""
    if not failures:
        return False

    for fail in failures:
        metric = str(fail.get("metric") or "")
        if metric not in GATING_TIME_METRIC_KEYS:
            return False
        ratio = fail.get("ratio")
        try:
            ratio_f = float(ratio)
        except (TypeError, ValueError):
            return False
        if ratio_f <= time_factor or ratio_f > retry_upper_factor:
            return False
    return True


def aggregate_attempts_median(attempts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate repeated performance attempts by median for stable gate decisions."""
    if not attempts:
        raise ValueError("attempts must not be empty")

    first = attempts[0]
    scenario_id = str(first.get("scenario_id") or "synthetic_large_100k")

    def _median_float(key: str) -> float:
        vals = [float(a[key]) for a in attempts if a.get(key) is not None]
        if not vals:
            raise ValueError(f"missing metric across attempts: {key}")
        return round(float(median(vals)), 4)

    out: dict[str, Any] = {"scenario_id": scenario_id}

    target_rows_raw = first.get("target_rows")
    if target_rows_raw is not None:
        out["target_rows"] = int(target_rows_raw)

    for idx, attempt in enumerate(attempts, start=1):
        scenario = str(attempt.get("scenario_id") or "synthetic_large_100k")
        if scenario != scenario_id:
            raise ValueError(f"inconsistent scenario_id at attempt {idx}: {scenario!r} != {scenario_id!r}")
        if target_rows_raw is not None and attempt.get("target_rows") is not None:
            if int(attempt.get("target_rows")) != int(target_rows_raw):
                raise ValueError(
                    f"inconsistent target_rows at attempt {idx}: {attempt.get('target_rows')} != {target_rows_raw}"
                )

    for key in TIME_METRIC_KEYS:
        out[key] = _median_float(key)

    if any(a.get("measurement_wall_sec") is not None for a in attempts):
        out["measurement_wall_sec"] = _median_float("measurement_wall_sec")

    volume_vals = [int(a["volume_n"]) for a in attempts if a.get("volume_n") is not None]
    if volume_vals:
        out["volume_n"] = int(round(float(median(volume_vals))))

    memory_vals = [int(a["memory_peak_bytes"]) for a in attempts if a.get("memory_peak_bytes") is not None]
    if memory_vals:
        out["memory_peak_bytes"] = int(median(memory_vals))

    return out


def evaluate_performance_with_retry(
    *,
    baseline: Mapping[str, Any],
    measure_once: Callable[[], Mapping[str, Any]],
    time_factor: float = 1.2,
    mem_factor: float = 1.3,
    retry_upper_factor: float = 1.3,
    total_attempts: int = 3,
) -> dict[str, Any]:
    """
    Evaluate gate with fail-then-retry policy.

    Strategy:
    - Run one attempt first.
    - If FAIL and failures are all near-boundary time metrics, run extra attempts.
    - Use median of attempts as final current for gate comparison.
    """
    if total_attempts < 1:
        raise ValueError(f"total_attempts must be >= 1 (got {total_attempts})")

    attempts: list[dict[str, Any]] = [dict(measure_once())]
    current = attempts[0]
    status, failures = compare_to_baseline(
        current,
        baseline,
        time_factor=time_factor,
        mem_factor=mem_factor,
    )

    retry_applied = False
    final_current_source = "single_attempt"

    if (
        status == "FAIL"
        and total_attempts > 1
        and should_retry_near_boundary_failures(
            failures,
            time_factor=time_factor,
            retry_upper_factor=retry_upper_factor,
        )
    ):
        retry_applied = True
        for _ in range(total_attempts - 1):
            attempts.append(dict(measure_once()))
        current = aggregate_attempts_median(attempts)
        final_current_source = f"median_of_{len(attempts)}_attempts"
        status, failures = compare_to_baseline(
            current,
            baseline,
            time_factor=time_factor,
            mem_factor=mem_factor,
        )

    return {
        "status": status,
        "failures": failures,
        "current": current,
        "attempt_count": len(attempts),
        "retry_applied": retry_applied,
        "retry_policy": {
            "mode": "fail_then_retry",
            "time_factor": time_factor,
            "mem_factor": mem_factor,
            "near_boundary_ratio_gt": time_factor,
            "near_boundary_ratio_le": retry_upper_factor,
            "total_attempts": total_attempts,
        },
        "attempts": attempts,
        "final_current_source": final_current_source,
    }


def compare_to_baseline(
    current: Mapping[str, Any],
    baseline: Mapping[str, Any],
    *,
    time_factor: float = 1.2,
    mem_factor: float = 1.3,
) -> tuple[str, list[dict[str, Any]]]:
    """
    Return (status, failures) where status is PASS or FAIL.
    failures list entries: metric, baseline, current, ratio, limit
    """
    scenario = str(baseline.get("scenario_id") or "synthetic_large_100k")
    if str(current.get("scenario_id")) != scenario:
        return (
            "FAIL",
            [{"metric": "scenario_id", "baseline": scenario, "current": current.get("scenario_id"), "ratio": None, "limit": None}],
        )

    fails: list[dict[str, Any]] = []
    for key in GATING_TIME_METRIC_KEYS:
        b = baseline.get(key)
        c = current.get(key)
        if b is None or c is None:
            continue
        bf = float(b)
        cf = float(c)
        if bf <= 0:
            continue
        if cf > bf * time_factor:
            fails.append(
                {
                    "metric": key,
                    "baseline": bf,
                    "current": cf,
                    "ratio": round(cf / bf, 4),
                    "limit": time_factor,
                }
            )

    mb = baseline.get("memory_peak_bytes")
    mc = current.get("memory_peak_bytes")
    if mb is not None and mc is not None:
        bmi = int(mb)
        cmi = int(mc)
        if bmi > 0 and cmi > bmi * mem_factor:
            fails.append(
                {
                    "metric": "memory_peak_bytes",
                    "baseline": bmi,
                    "current": cmi,
                    "ratio": round(cmi / bmi, 4),
                    "limit": mem_factor,
                }
            )

    return ("FAIL", fails) if fails else ("PASS", [])


def gate_should_skip(baseline_doc: Mapping[str, Any]) -> bool:
    if os.environ.get("RELEASE_PERF_GATE", "").strip().lower() in {"0", "false", "no", "skip"}:
        return True
    gate = baseline_doc.get("performance_gate")
    return isinstance(gate, dict) and gate.get("skip") is True
