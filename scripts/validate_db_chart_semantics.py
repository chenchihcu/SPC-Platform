"""Validate chart statistical semantics against a real DB-backed session.

This gate is intentionally stricter than payload contract/renderability checks:
it rebuilds the active session dataframe from measurement + coordinate files,
computes chart payloads through the normal application path, then independently
recomputes selected statistics from the joined dataframe.
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.analytics import chart_registry  # noqa: E402
from app.data.loaders.coordinate_loader import CoordinateLoader  # noqa: E402
from app.data.loaders.measurement_loader import MeasurementLoader  # noqa: E402
from app.data.relation.join_engine import JoinEngine  # noqa: E402
from app.utils.dataframe_utils import detect_order_col  # noqa: E402
from app.viewmodels.chart_analysis_viewmodel import compute_analysis_payload  # noqa: E402


FEATURES = ["Volume", "Area", "Height"]
SPEC_KEY_BY_COL = {"Volume": "volume", "Area": "area", "Height": "height"}
PAIR_EXPANSION_CHARTS = ("scatter_spec", "correlation_matrix", "correlation_heatmap", "quadrant", "bivariate_outlier")
FLOAT_TOL = 1e-9


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


def _connect_readonly(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise FileNotFoundError(f"DB not found: {db_path}")
    conn = sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any]:
    return dict(row) if row is not None else {}


def _fetch_session(conn: sqlite3.Connection, session_id: int | None) -> dict[str, Any]:
    if session_id is not None:
        row = conn.execute("SELECT * FROM measurement_sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            raise ValueError(f"measurement session not found: {session_id}")
        return _row_to_dict(row)

    row = conn.execute(
        """
        SELECT ms.*
        FROM measurement_sessions ms
        JOIN coordinate_versions cv
          ON cv.product_id = ms.product_id AND cv.is_active = 1
        JOIN paste_printing_spec_versions pv
          ON pv.product_id = ms.product_id AND pv.is_active = 1
        JOIN stencil_thickness_versions sv
          ON sv.product_id = ms.product_id AND sv.is_active = 1
        WHERE ms.product_id IS NOT NULL
          AND TRIM(COALESCE(ms.file_path, '')) <> ''
        ORDER BY ms.upload_datetime DESC, ms.id DESC
        LIMIT 1
        """
    ).fetchone()
    if row is None:
        raise ValueError("no usable measurement session with active coordinate and spec")
    return _row_to_dict(row)


def _active_coordinate(conn: sqlite3.Connection, product_id: int) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT *
        FROM coordinate_versions
        WHERE product_id = ? AND is_active = 1
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (product_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"no active coordinate for product_id={product_id}")
    return _row_to_dict(row)


def _active_specs(conn: sqlite3.Connection, product_id: int) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, float]]]:
    paste = conn.execute(
        """
        SELECT *
        FROM paste_printing_spec_versions
        WHERE product_id = ? AND is_active = 1
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
        """,
        (product_id,),
    ).fetchone()
    stencil = conn.execute(
        """
        SELECT *
        FROM stencil_thickness_versions
        WHERE product_id = ? AND is_active = 1
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
        """,
        (product_id,),
    ).fetchone()
    if paste is None or stencil is None:
        raise ValueError(f"active paste/stencil spec not found for product_id={product_id}")

    paste_d = _row_to_dict(paste)
    stencil_d = _row_to_dict(stencil)
    unit_mode = str(stencil_d.get("unit_mode") or "percent").strip().lower()
    denominator = float(stencil_d.get("height_denominator_mm") or stencil_d.get("thickness_main") or 0.12)
    height_lsl = float(paste_d.get("default_height_lsl") or 70.0)
    height_usl = float(paste_d.get("default_height_usl") or 140.0)
    if unit_mode == "absolute":
        height_spec = {
            "target": denominator,
            "lsl": denominator * height_lsl / 100.0,
            "usl": denominator * height_usl / 100.0,
        }
    else:
        height_spec = {"target": 100.0, "lsl": height_lsl, "usl": height_usl}

    spec = {
        "volume": {
            "target": float(paste_d.get("default_volume_target") or 100.0),
            "lsl": float(paste_d.get("default_volume_lsl") or 70.0),
            "usl": float(paste_d.get("default_volume_usl") or 150.0),
        },
        "area": {
            "target": float(paste_d.get("default_area_target") or 100.0),
            "lsl": float(paste_d.get("default_area_lsl") or 70.0),
            "usl": float(paste_d.get("default_area_usl") or 150.0),
        },
        "height": height_spec,
    }
    return paste_d, stencil_d, spec


def _feature_spec(workorder_spec: dict[str, dict[str, Any]], feature: str) -> dict[str, float]:
    raw = workorder_spec.get(SPEC_KEY_BY_COL.get(feature, feature.lower()), {}) or {}
    return {
        "target": float(raw.get("target") or 0.0),
        "lsl": float(raw.get("lsl") or 0.0),
        "usl": float(raw.get("usl") or 0.0),
    }


def _finite_series(data: pd.Series) -> pd.Series:
    return pd.to_numeric(data, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()


def _finite_frame(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    work = df[cols].apply(pd.to_numeric, errors="coerce")
    return work.replace([np.inf, -np.inf], np.nan).dropna()


def _analysis_ordered_df(df: pd.DataFrame) -> pd.DataFrame:
    order_col = detect_order_col(df)
    return df.sort_values(order_col) if order_col else df


def _is_valid_payload(payload: Any) -> bool:
    return bool(isinstance(payload, dict) and (payload.get("metadata") or {}).get("is_valid"))


def _payload_error(payload: Any) -> str:
    if not isinstance(payload, dict):
        return "payload is not a dict"
    return str((payload.get("metadata") or {}).get("error") or "")


def _resolve(payload: dict[str, Any], chart_id: str, features: list[str]) -> dict[str, Any]:
    return chart_registry.resolve_chart_payload(payload, chart_id, features=features, context="db_semantic")


def _pair_key(payload: dict[str, Any], x_col: str, y_col: str) -> str | None:
    dual = payload.get("dual_parameters") or {}
    for key in (f"{x_col}+{y_col}", f"{y_col}+{x_col}"):
        if key in dual:
            return key
    return None


def _numeric_equal(actual: Any, expected: Any, *, tol: float = FLOAT_TOL) -> bool:
    if actual is None or expected is None:
        return actual is expected
    if isinstance(actual, bool) or isinstance(expected, bool):
        return bool(actual) is bool(expected)
    if isinstance(actual, str) or isinstance(expected, str):
        return str(actual) == str(expected)
    try:
        a = float(actual)
        e = float(expected)
    except (TypeError, ValueError):
        return actual == expected
    if not math.isfinite(a) or not math.isfinite(e):
        return a == e
    return abs(a - e) <= tol * max(1.0, abs(e))


def _add_check(checks: list[dict[str, Any]], name: str, actual: Any, expected: Any) -> None:
    checks.append(
        {
            "name": name,
            "status": "PASS" if _numeric_equal(actual, expected) else "FAIL",
            "actual": _json_safe(actual),
            "expected": _json_safe(expected),
        }
    )


def _build_payload(joined_df: pd.DataFrame, features: list[str], spec: dict[str, dict[str, float]]) -> dict[str, Any]:
    first_spec = _feature_spec(spec, features[0])
    payload, err = compute_analysis_payload(
        joined_df,
        features,
        first_spec["usl"],
        first_spec["lsl"],
        first_spec["target"],
        workorder_spec=spec,
    )
    if payload is None:
        raise RuntimeError(f"compute_analysis_payload failed for {features}: {err}")
    return payload


def _imr_expected(series: pd.Series) -> dict[str, float | int]:
    valid = _finite_series(series)
    values = valid.to_numpy(dtype=float, copy=False)
    cl = float(values.mean())
    mr_values = np.abs(np.diff(values))
    mr_bar = float(mr_values.mean())
    sigma = mr_bar / 1.128
    return {
        "n": int(len(valid)),
        "cl": cl,
        "mr_bar": mr_bar,
        "sigma": sigma,
        "ucl": cl + 3 * sigma,
        "lcl": cl - 3 * sigma,
    }


def _capability_expected(series: pd.Series, spec: dict[str, float]) -> dict[str, float]:
    valid = _finite_series(series)
    mean_val = float(valid.mean())
    mr_bar = float(valid.diff().abs().mean())
    sigma_st = mr_bar / 1.128
    sigma_lt = float(np.std(valid, ddof=1))
    usl = spec["usl"]
    lsl = spec["lsl"]
    return {
        "mean": mean_val,
        "sigma_st": sigma_st,
        "sigma_lt": sigma_lt,
        "cp": (usl - lsl) / (6 * sigma_st),
        "cpk": min((usl - mean_val) / (3 * sigma_st), (mean_val - lsl) / (3 * sigma_st)),
        "pp": (usl - lsl) / (6 * sigma_lt),
        "ppk": min((usl - mean_val) / (3 * sigma_lt), (mean_val - lsl) / (3 * sigma_lt)),
    }


def _cusum_expected(series: pd.Series, spec: dict[str, float]) -> dict[str, Any]:
    valid = _finite_series(series)
    mean_val = float(valid.mean())
    sigma = float(valid.std(ddof=1))
    mu0 = spec["target"]
    mu0_source = "spec_target"
    fallback = False
    if sigma > 0:
        deviation = abs(mu0 - mean_val) / sigma
        if deviation > 10:
            mu0 = mean_val
            mu0_source = "data_mean"
            fallback = True
    return {
        "n": int(len(valid)),
        "mu0": mu0,
        "mu0_source": mu0_source,
        "sigma": sigma,
        "h_sigma": 5.0 * sigma,
        "mu0_fallback_applied": fallback,
    }


def _corr_expected(work: pd.DataFrame, left: str, right: str) -> float:
    return float(work[left].corr(work[right]))


def _validate_single_feature_semantics(
    joined_df: pd.DataFrame,
    one_feature_payload: dict[str, Any],
    features: list[str],
    spec: dict[str, dict[str, float]],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    parameters = one_feature_payload.get("parameters") or {}
    ordered_df = _analysis_ordered_df(joined_df)
    for feature in features:
        bundle = parameters.get(feature) or {}
        series = ordered_df[feature]
        feat_spec = _feature_spec(spec, feature)

        imr_actual = (bundle.get("spc") or {}).get("statistics") or {}
        for key, expected in _imr_expected(series).items():
            _add_check(checks, f"{feature}.imr.{key}", imr_actual.get(key), expected)

        cap_actual = (bundle.get("cap") or {}).get("statistics") or {}
        for key, expected in _capability_expected(series, feat_spec).items():
            _add_check(checks, f"{feature}.capability.{key}", cap_actual.get(key), expected)

        run_actual = (bundle.get("run_chart") or {}).get("statistics") or {}
        valid = _finite_series(series)
        _add_check(checks, f"{feature}.run_chart.center_line", run_actual.get("center_line"), float(valid.mean()))
        _add_check(checks, f"{feature}.run_chart.n", run_actual.get("n"), int(len(valid)))

        ewma_actual = (bundle.get("ewma") or {}).get("statistics") or {}
        sigma_ewma = float(valid.std(ddof=1)) * math.sqrt(0.2 / (2 - 0.2))
        _add_check(checks, f"{feature}.ewma.cl", ewma_actual.get("cl"), float(valid.mean()))
        _add_check(checks, f"{feature}.ewma.sigma_ewma", ewma_actual.get("sigma_ewma"), sigma_ewma)
        _add_check(checks, f"{feature}.ewma.n", ewma_actual.get("n"), int(len(valid)))

        cusum_actual = (bundle.get("cusum") or {}).get("statistics") or {}
        for key, expected in _cusum_expected(series, feat_spec).items():
            _add_check(checks, f"{feature}.cusum.{key}", cusum_actual.get(key), expected)

        spatial_actual = (bundle.get("spatial") or {}).get("statistics") or {}
        spatial_valid = _finite_frame(joined_df, ["X", "Y", feature]) if {"X", "Y", feature}.issubset(joined_df.columns) else pd.DataFrame()
        if not spatial_valid.empty:
            _add_check(checks, f"{feature}.spatial.n", spatial_actual.get("n"), int(len(spatial_valid)))

    return checks


def _validate_pair_semantics(
    joined_df: pd.DataFrame,
    one_feature_payload: dict[str, Any],
    features: list[str],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    dual = one_feature_payload.get("dual_parameters") or {}
    for x_col, y_col in combinations(features, 2):
        key = _pair_key(one_feature_payload, x_col, y_col)
        if key is None:
            _add_check(checks, f"{x_col}+{y_col}.dual_parameters.present", False, True)
            continue
        pair_payload = dual.get(key) or {}
        work = _finite_frame(joined_df, [x_col, y_col])
        expected_n = int(len(work))
        expected_corr = _corr_expected(work, x_col, y_col)

        scatter_stats = (pair_payload.get("scatter_spec") or {}).get("statistics") or {}
        _add_check(checks, f"{x_col}+{y_col}.scatter.n", scatter_stats.get("n"), expected_n)
        _add_check(checks, f"{x_col}+{y_col}.scatter.corr", scatter_stats.get("corr"), expected_corr)

        corr_payload = pair_payload.get("correlation_matrix") or {}
        corr_stats = corr_payload.get("statistics") or {}
        corr_data = corr_payload.get("data") or {}
        matrix = corr_data.get("matrix") or [[None, None], [None, None]]
        _add_check(checks, f"{x_col}+{y_col}.correlation.n", corr_stats.get("n"), expected_n)
        _add_check(checks, f"{x_col}+{y_col}.correlation.r", matrix[0][1], expected_corr)

        quadrant_stats = (pair_payload.get("quadrant") or {}).get("statistics") or {}
        _add_check(checks, f"{x_col}+{y_col}.quadrant.n", quadrant_stats.get("n"), expected_n)

        density_stats = (pair_payload.get("density") or {}).get("statistics") or {}
        _add_check(checks, f"{x_col}+{y_col}.bivariate_density.n_points", density_stats.get("n_points"), expected_n)

        bivariate_stats = (pair_payload.get("bivariate_outlier") or {}).get("statistics") or {}
        _add_check(checks, f"{x_col}+{y_col}.bivariate_outlier.n", bivariate_stats.get("n"), expected_n)

    return checks


def _validate_three_feature_semantics(
    joined_df: pd.DataFrame,
    three_feature_payload: dict[str, Any],
    features: list[str],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    work = _finite_frame(joined_df, features)
    expected_n = int(len(work))
    _add_check(checks, "3f.anomaly_3f.n", (three_feature_payload.get("anomaly_3f") or {}).get("statistics", {}).get("n"), expected_n)
    _add_check(checks, "3f.parallel_coord.n", (three_feature_payload.get("parallel_coord") or {}).get("statistics", {}).get("n"), expected_n)
    _add_check(checks, "3f.pass_fail_matrix.n_total", (three_feature_payload.get("pass_fail_matrix") or {}).get("statistics", {}).get("n_total"), expected_n)
    _add_check(checks, "3f.correlation_matrix.n", (three_feature_payload.get("correlation_matrix") or {}).get("statistics", {}).get("n"), expected_n)

    consistency_work = work[(work[features[1]] > 0) & (work[features[0]] > 0)]
    ratio = (consistency_work[features[0]] / consistency_work[features[1]]).replace([np.inf, -np.inf], np.nan)
    expected_consistency_n = int(ratio.dropna().shape[0])
    _add_check(
        checks,
        "3f.consistency_3f.n",
        (three_feature_payload.get("consistency_3f") or {}).get("statistics", {}).get("n"),
        expected_consistency_n,
    )
    return checks


def _density_mode(payload: dict[str, Any], features: list[str]) -> str:
    resolved = _resolve(payload, "density", features)
    data = resolved.get("data") or {}
    if data.get("mode"):
        return str(data.get("mode"))
    if "x" in data and "y" in data:
        return "bivariate"
    if resolved.get("_multi_feature"):
        return "multi_feature_univariate"
    return "unknown"


def _build_resolver_rows(payloads: dict[int, dict[str, Any]], features: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    mismatches: list[dict[str, Any]] = []
    for arity, payload in payloads.items():
        active_features = features[:arity]
        for chart_id in chart_registry.CHART_ORDER:
            available = chart_registry.is_chart_available_for_selection(chart_id, active_features)
            resolved = _resolve(payload, chart_id, active_features)
            resolver_valid = _is_valid_payload(resolved)
            row = {
                "arity": arity,
                "chart_id": chart_id,
                "features": active_features,
                "available": available,
                "resolver_valid": resolver_valid,
                "error": _payload_error(resolved),
            }
            rows.append(row)
            if available and not resolver_valid:
                mismatches.append(row)
    return rows, mismatches


def _build_pair_expansion_rows(one_feature_payload: dict[str, Any], features: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for chart_id in PAIR_EXPANSION_CHARTS:
        for pair in combinations(features, 2):
            resolved = _resolve(one_feature_payload, chart_id, list(pair))
            row = {
                "chart_id": chart_id,
                "pair": list(pair),
                "available": chart_registry.is_chart_available_for_selection(chart_id, list(pair)),
                "resolver_valid": _is_valid_payload(resolved),
                "error": _payload_error(resolved),
            }
            rows.append(row)
            if row["available"] and not row["resolver_valid"]:
                failures.append(row)
    return rows, failures


def _load_joined_frame(session: dict[str, Any], coordinate: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any], dict[str, Any]]:
    measurement_path = Path(str(session.get("file_path") or ""))
    coordinate_path = Path(str(coordinate.get("file_path") or ""))
    if not measurement_path.exists():
        raise FileNotFoundError(f"measurement file not found: {measurement_path}")
    if not coordinate_path.exists():
        raise FileNotFoundError(f"coordinate file not found: {coordinate_path}")

    meas_df, meas_meta = MeasurementLoader().load(str(measurement_path), supplier=str(session.get("supplier") or ""))
    if not meas_meta.get("is_valid"):
        raise ValueError(f"measurement load failed: {meas_meta}")
    coord_df, coord_meta = CoordinateLoader().load(str(coordinate_path))
    if not coord_meta.get("is_valid"):
        raise ValueError(f"coordinate load failed: {coord_meta}")
    joined_df, join_report = JoinEngine.join(coord_df, meas_df)
    if joined_df.empty:
        raise ValueError(f"join produced no rows: {join_report}")
    return joined_df, meas_meta, coord_meta, join_report


def run_validation(args: argparse.Namespace) -> dict[str, Any]:
    db_path = Path(args.db)
    if not db_path.is_absolute():
        db_path = REPO_ROOT / db_path
    with _connect_readonly(db_path) as conn:
        session = _fetch_session(conn, args.session_id)
        product_id = session.get("product_id")
        if product_id is None:
            raise ValueError(f"session has no product_id: {session.get('id')}")
        coordinate = _active_coordinate(conn, int(product_id))
        paste_spec, stencil_spec, workorder_spec = _active_specs(conn, int(product_id))

    joined_df, meas_meta, coord_meta, join_report = _load_joined_frame(session, coordinate)
    features = [feature for feature in FEATURES if feature in joined_df.columns]
    if len(features) < 3:
        raise ValueError(f"expected at least 3 measurement features, found {features}")

    payloads = {
        1: _build_payload(joined_df, features[:1], workorder_spec),
        2: _build_payload(joined_df, features[:2], workorder_spec),
        3: _build_payload(joined_df, features[:3], workorder_spec),
    }
    resolver_rows, resolver_mismatches = _build_resolver_rows(payloads, features)
    pair_rows, pair_failures = _build_pair_expansion_rows(payloads[1], features)

    checks = []
    checks.extend(_validate_single_feature_semantics(joined_df, payloads[1], features, workorder_spec))
    checks.extend(_validate_pair_semantics(joined_df, payloads[1], features))
    checks.extend(_validate_three_feature_semantics(joined_df, payloads[3], features[:3]))
    semantic_failures = [check for check in checks if check["status"] != "PASS"]

    return {
        "db": str(Path(args.db)),
        "session": _json_safe(session),
        "measurement": {"loaded": True, "rows": int(len(joined_df)), "metadata": _json_safe(meas_meta)},
        "coordinate": {
            "file_path": coordinate.get("file_path"),
            "loaded": True,
            "metadata": _json_safe(coord_meta),
            "join_report": _json_safe(join_report),
        },
        "spec": {
            "paste_printing": _json_safe(paste_spec),
            "stencil_thickness": _json_safe(stencil_spec),
            "workorder_spec": _json_safe(workorder_spec),
        },
        "features": features,
        "available_resolver_mismatch_count": len(resolver_mismatches),
        "pair_expansion_failure_count": len(pair_failures),
        "statistical_semantic_failure_count": len(semantic_failures),
        "statistical_semantic_checks": checks,
        "mismatches": _json_safe([*resolver_mismatches, *pair_failures, *semantic_failures]),
        "resolver_rows": _json_safe(resolver_rows),
        "density_modes": {
            "1f_density": _density_mode(payloads[1], features[:1]),
            "2f_density": _density_mode(payloads[2], features[:2]),
            "3f_density": _density_mode(payloads[3], features[:3]),
        },
        "pair_expansion": _json_safe(pair_rows),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate DB-backed chart statistical semantics.")
    parser.add_argument("--db", default="data/spc_master.db", help="SQLite master DB path.")
    parser.add_argument("--session-id", type=int, default=None, help="Exact measurement_sessions.id to validate.")
    parser.add_argument(
        "--latest-session",
        action="store_true",
        help="Use the latest usable session with active coordinate/spec. This is the default when --session-id is omitted.",
    )
    parser.add_argument("--output", default="Outputs/db_chart_semantics_current", help="Output directory for summary.json.")
    parser.add_argument("--quiet", action="store_true", help="Only print the final PASS/FAIL line.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = run_validation(args)
    out_dir = Path(args.output)
    if not out_dir.is_absolute():
        out_dir = REPO_ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(_json_safe(summary), ensure_ascii=False, indent=2), encoding="utf-8")

    failures = (
        int(summary["available_resolver_mismatch_count"])
        + int(summary["pair_expansion_failure_count"])
        + int(summary["statistical_semantic_failure_count"])
    )
    status = "PASS" if failures == 0 else "FAIL"
    if args.quiet:
        print(f"[db-chart-semantics] {status} failures={failures} summary={summary_path}")
    else:
        print(json.dumps({"status": status, "failures": failures, "summary": str(summary_path)}, ensure_ascii=False, indent=2))
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
