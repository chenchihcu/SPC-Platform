"""Validate chart statistical semantics against a real DB-backed session.

This gate is intentionally stricter than payload contract/renderability checks:
it rebuilds the active session dataframe from measurement + coordinate files,
computes chart payloads through the normal application path, then independently
recomputes selected statistics from the joined dataframe.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterator, Sized
from contextlib import contextmanager
import json
import math
import sqlite3
import sys
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats  # type: ignore[import-untyped]
from scipy.spatial import KDTree  # type: ignore[import-untyped]

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
PAIR_EXPANSION_CHARTS = (
    "scatter_spec",
    "correlation_matrix",
    "correlation_heatmap",
    "quadrant",
    "bivariate_outlier",
    "density",
)
EXPECTED_DENSITY_MODES = {
    "1f_density": "univariate",
    "2f_density": "bivariate",
    "3f_density": "multi_feature_univariate",
}
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


@contextmanager
def _connect_readonly(db_path: Path) -> Iterator[sqlite3.Connection]:
    if not db_path.exists():
        raise FileNotFoundError(f"DB not found: {db_path}")
    conn = sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA query_only = ON")
        yield conn
    finally:
        conn.close()


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
        return type(actual) is bool and type(expected) is bool and actual is expected
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


def _max_abs_error(actual: Any, expected: Any) -> float | str:
    try:
        actual_values = np.asarray(actual, dtype=float).reshape(-1)
        expected_values = np.asarray(expected, dtype=float).reshape(-1)
    except (TypeError, ValueError):
        return "non_numeric"
    if actual_values.shape != expected_values.shape:
        return f"shape_mismatch:{actual_values.shape}!={expected_values.shape}"
    if actual_values.size == 0:
        return 0.0
    errors = np.abs(actual_values - expected_values)
    if not np.all(np.isfinite(errors)):
        return "non_finite"
    return float(np.max(errors))


def _sequence_mismatch_count(actual: Any, expected: Any) -> int | str:
    try:
        actual_values = list(actual)
        expected_values = list(expected)
    except TypeError:
        return "not_sequence"
    if len(actual_values) != len(expected_values):
        return f"length_mismatch:{len(actual_values)}!={len(expected_values)}"
    return sum(left != right for left, right in zip(actual_values, expected_values))


def _lisa_expected(joined_df: pd.DataFrame, feature: str, *, k: int = 3) -> dict[str, Any]:
    required = ["X", "Y", feature]
    if not set(required).issubset(joined_df.columns):
        return {"is_valid": False}
    work = _finite_frame(joined_df, required)
    n = int(len(work))
    if n < k + 1:
        return {"is_valid": False, "n": n}

    coords = work[["X", "Y"]].to_numpy(dtype=float, copy=False)
    values = work[feature].to_numpy(dtype=float, copy=False)
    k_eff = min(k, n - 1)
    neighbour_idx: np.ndarray
    weight = 1.0 / k_eff

    if n > 2000:
        flat = coords[:, 0] + coords[:, 1] * 1j
        _, first_occurrences, inverse_idx = np.unique(
            flat,
            return_index=True,
            return_inverse=True,
        )
        unique_count = int(first_occurrences.shape[0])
        if unique_count < n // 2 and unique_count > 1:
            unique_k = min(k, unique_count - 1)
            unique_coords = coords[first_occurrences]
            _, indices = KDTree(unique_coords).query(unique_coords, k=unique_k + 1)
            neighbour_idx = first_occurrences[indices[:, 1:][inverse_idx]]
            weight = 1.0 / unique_k
        else:
            _, indices = KDTree(coords).query(coords, k=k_eff + 1)
            neighbour_idx = indices[:, 1:]
    else:
        _, indices = KDTree(coords).query(coords, k=k_eff + 1)
        neighbour_idx = indices[:, 1:]

    centered = values - np.mean(values)
    variance = float(np.sum(centered ** 2) / (n - 1))
    if variance == 0:
        return {"is_valid": False, "n": n}
    local_i = centered * np.sum(centered[neighbour_idx], axis=1) * weight / variance
    standardized = centered / math.sqrt(variance)
    lag = np.mean(standardized[neighbour_idx], axis=1)
    z_scores = (
        (local_i - np.mean(local_i)) / np.std(local_i, ddof=1)
        if n > 2
        else np.zeros(n, dtype=float)
    )
    permutations = 49 if n > 20000 else 99 if n > 2000 else 999
    return {
        "is_valid": True,
        "n": n,
        "k": k,
        "permutations": permutations,
        "local_i": local_i,
        "z_scores": z_scores,
        "quadrant_std_value": standardized,
        "quadrant_lag": lag,
    }


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

        lisa_payload = bundle.get("lisa") or {}
        lisa_meta = lisa_payload.get("metadata") or {}
        lisa_data = lisa_payload.get("data") or {}
        lisa_stats = lisa_payload.get("statistics") or {}
        lisa_expected = _lisa_expected(joined_df, feature)
        lisa_expected_valid = bool(lisa_expected.get("is_valid"))
        _add_check(
            checks,
            f"{feature}.lisa.is_valid",
            lisa_meta.get("is_valid"),
            lisa_expected_valid,
        )
        if lisa_expected_valid:
            for key in ("n", "k", "permutations"):
                _add_check(
                    checks,
                    f"{feature}.lisa.{key}",
                    lisa_stats.get(key),
                    lisa_expected.get(key),
                )
            for key in ("local_i", "z_scores", "quadrant_std_value", "quadrant_lag"):
                _add_check(
                    checks,
                    f"{feature}.lisa.{key}.max_abs_error",
                    _max_abs_error(lisa_data.get(key), lisa_expected.get(key)),
                    0.0,
                )

            expected_n = int(lisa_expected["n"])
            try:
                p_values = np.asarray(lisa_data.get("p_values", []), dtype=float)
            except (TypeError, ValueError):
                p_values = np.asarray([], dtype=float)
            p_value_contract_ok = bool(
                p_values.shape == (expected_n,)
                and np.all(np.isfinite(p_values))
                and np.all((p_values > 0) & (p_values <= 1))
            )
            _add_check(
                checks,
                f"{feature}.lisa.p_values.contract",
                p_value_contract_ok,
                True,
            )
            if p_value_contract_ok:
                standardized = np.asarray(lisa_expected["quadrant_std_value"], dtype=float)
                lag = np.asarray(lisa_expected["quadrant_lag"], dtype=float)
                conditions = [
                    p_values >= 0.05,
                    (standardized > 0) & (lag > 0),
                    (standardized < 0) & (lag < 0),
                    (standardized > 0) & (lag < 0),
                    (standardized < 0) & (lag > 0),
                ]
                expected_classes = np.select(
                    conditions,
                    ["NS", "HH", "LL", "HL", "LH"],
                    default="NS",
                ).tolist()
                actual_classes = lisa_data.get("classifications", [])
                _add_check(
                    checks,
                    f"{feature}.lisa.classifications.mismatch_count",
                    _sequence_mismatch_count(actual_classes, expected_classes),
                    0,
                )
                significant_count = int(np.sum(p_values < 0.05))
                _add_check(
                    checks,
                    f"{feature}.lisa.n_significant",
                    lisa_stats.get("n_significant"),
                    significant_count,
                )
                _add_check(
                    checks,
                    f"{feature}.lisa.pct_significant",
                    lisa_stats.get("pct_significant"),
                    round(significant_count / expected_n * 100, 1),
                )
                actual_class_counts = lisa_stats.get("class_counts") or {}
                for class_name in ("HH", "LL", "HL", "LH", "NS"):
                    _add_check(
                        checks,
                        f"{feature}.lisa.class_counts.{class_name}",
                        actual_class_counts.get(class_name),
                        expected_classes.count(class_name),
                    )

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


def _validate_radar_semantics(
    joined_df: pd.DataFrame,
    three_feature_payload: dict[str, Any],
    features: list[str],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    radar = three_feature_payload.get("radar") or {}
    radar_meta = radar.get("metadata") or {}
    radar_data = radar.get("data") or {}
    if "RefDes" not in joined_df.columns:
        _add_check(checks, "3f.radar.is_valid", radar_meta.get("is_valid"), False)
        return checks

    feature_values = joined_df[features].apply(pd.to_numeric, errors="coerce")
    radar_work = pd.concat([joined_df[["RefDes"]], feature_values], axis=1)
    radar_work = radar_work.replace([np.inf, -np.inf], np.nan).dropna()
    if radar_work.empty:
        _add_check(checks, "3f.radar.is_valid", radar_meta.get("is_valid"), False)
        return checks

    means = radar_work.groupby("RefDes")[features].mean()
    expected_categories = sorted(features)
    expected_names = [str(name) for name in means.index]
    actual_categories = list(radar_data.get("categories") or [])
    actual_series = radar_data.get("series") or []
    actual_names = [str(item.get("name")) for item in actual_series if isinstance(item, dict)]

    _add_check(checks, "3f.radar.is_valid", radar_meta.get("is_valid"), True)
    _add_check(checks, "3f.radar.n_series", radar_meta.get("n_series"), len(expected_names))
    _add_check(
        checks,
        "3f.radar.n_categories",
        radar_meta.get("n_categories"),
        len(expected_categories),
    )
    _add_check(
        checks,
        "3f.radar.categories.mismatch_count",
        _sequence_mismatch_count(actual_categories, expected_categories),
        0,
    )
    _add_check(
        checks,
        "3f.radar.series_names.mismatch_count",
        _sequence_mismatch_count(actual_names, expected_names),
        0,
    )

    max_error: float | str = "shape_mismatch"
    if actual_categories == expected_categories and actual_names == expected_names:
        actual_values: list[float] = []
        expected_values: list[float] = []
        for series_item, group_name in zip(actual_series, means.index):
            if not isinstance(series_item, dict):
                break
            actual_values.extend(series_item.get("values") or [])
            expected_values.extend(float(means.loc[group_name, feature]) for feature in expected_categories)
        else:
            max_error = _max_abs_error(actual_values, expected_values)
    _add_check(checks, "3f.radar.values.max_abs_error", max_error, 0.0)
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

    hotelling = three_feature_payload.get("hotelling_t2") or {}
    hotelling_meta = hotelling.get("metadata") or {}
    hotelling_data = hotelling.get("data") or {}
    hotelling_stats = hotelling.get("statistics") or {}
    n, p = work.shape
    covariance: np.ndarray | None = None
    hotelling_expected_valid = False
    if p == 3 and n > p and n > 10:
        covariance = np.cov(work.to_numpy(dtype=float, copy=False), rowvar=False)
        hotelling_expected_valid = bool(np.linalg.cond(covariance) <= 1e12)
    _add_check(checks, "3f.hotelling_t2.is_valid", hotelling_meta.get("is_valid"), hotelling_expected_valid)
    if hotelling_expected_valid and covariance is not None:
        values = work.to_numpy(dtype=float, copy=False)
        center = np.mean(values, axis=0)
        inverse_covariance = np.linalg.inv(covariance)
        delta = values - center
        t2_values = np.sum(delta @ inverse_covariance * delta, axis=1)
        ucl = p * (n - 1) * (n + 1) / (n * (n - p)) * stats.f.ppf(0.95, p, n - p)
        ooc_count = int(np.sum(t2_values > ucl))
        expected_flags = [bool(value > ucl) for value in t2_values]
        _add_check(checks, "3f.hotelling_t2.n_samples", hotelling_meta.get("n_samples"), n)
        _add_check(checks, "3f.hotelling_t2.p_features", hotelling_meta.get("p_features"), p)
        _add_check(
            checks,
            "3f.hotelling_t2.indices.mismatch_count",
            _sequence_mismatch_count(hotelling_data.get("indices", []), range(n)),
            0,
        )
        _add_check(
            checks,
            "3f.hotelling_t2.t2_values.max_abs_error",
            _max_abs_error(hotelling_data.get("t2_values"), t2_values),
            0.0,
        )
        _add_check(
            checks,
            "3f.hotelling_t2.ooc_flags.mismatch_count",
            _sequence_mismatch_count(hotelling_data.get("ooc_flags", []), expected_flags),
            0,
        )
        _add_check(
            checks,
            "3f.hotelling_t2.mu0_vector.max_abs_error",
            _max_abs_error(hotelling_meta.get("mu0_vector"), center),
            0.0,
        )
        _add_check(
            checks,
            "3f.hotelling_t2.cov_matrix.max_abs_error",
            _max_abs_error(hotelling_meta.get("cov_matrix"), covariance.flatten()),
            0.0,
        )
        for key, expected in {
            "ucl_value": float(ucl),
            "mean_t2": float(np.mean(t2_values)),
            "max_t2": float(np.max(t2_values)),
            "ooc_count": ooc_count,
            "ooc_pct": float(ooc_count / n * 100),
        }.items():
            _add_check(checks, f"3f.hotelling_t2.{key}", hotelling_stats.get(key), expected)
    checks.extend(_validate_radar_semantics(joined_df, three_feature_payload, features))
    return checks


def _resolved_density_mode(resolved: dict[str, Any]) -> str:
    data = resolved.get("data") or {}
    if resolved.get("_multi_feature"):
        return "multi_feature_univariate"
    if data.get("mode"):
        return str(data.get("mode"))
    if "x" in data and "y" in data:
        return "bivariate"
    return "unknown"


def _bivariate_density_matches_pair(resolved: dict[str, Any], features: list[str]) -> bool:
    """Independently validate pair identity and point alignment for density."""
    if len(features) != 2 or not _is_valid_payload(resolved):
        return False
    data = resolved.get("data") or {}
    if not isinstance(data, dict) or _resolved_density_mode(resolved) != "bivariate":
        return False
    col_x = data.get("col_x")
    col_y = data.get("col_y")
    if not isinstance(col_x, str) or not col_x or not isinstance(col_y, str) or not col_y:
        return False
    if sorted([col_x, col_y]) != sorted(features):
        return False
    x_values = data.get("x")
    y_values = data.get("y")
    if (
        not isinstance(x_values, Sized)
        or not isinstance(y_values, Sized)
        or isinstance(x_values, (str, bytes, dict))
        or isinstance(y_values, (str, bytes, dict))
    ):
        return False
    return len(x_values) == len(y_values) and len(x_values) >= 2


def _density_mode(payload: dict[str, Any], features: list[str]) -> str:
    return _resolved_density_mode(_resolve(payload, "density", features))


def _validate_density_semantics(
    payloads: dict[int, dict[str, Any]],
    features: list[str],
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    modes = {
        "1f_density": _density_mode(payloads[1], features[:1]),
        "2f_density": _density_mode(payloads[2], features[:2]),
        "3f_density": _density_mode(payloads[3], features[:3]),
    }
    checks: list[dict[str, Any]] = []
    for name, expected in EXPECTED_DENSITY_MODES.items():
        _add_check(checks, f"density_mode.{name}", modes.get(name), expected)

    resolved_2f = _resolve(payloads[2], "density", features[:2])
    _add_check(
        checks,
        "density_mode.2f_pair_semantics",
        _bivariate_density_matches_pair(resolved_2f, features[:2]),
        True,
    )

    resolved_3f = _resolve(payloads[3], "density", features[:3])
    actual_features = list(resolved_3f.get("_features") or [])
    expected_features = list(features[:3])
    _add_check(
        checks,
        "density_mode.3f.features.mismatch_count",
        _sequence_mismatch_count(actual_features, expected_features),
        0,
    )
    feature_data = resolved_3f.get("_feature_data") or {}
    for feature in expected_features:
        child = feature_data.get(feature) if isinstance(feature_data, dict) else None
        _add_check(
            checks,
            f"density_mode.3f.{feature}.present",
            isinstance(child, dict),
            True,
        )
        _add_check(
            checks,
            f"density_mode.3f.{feature}.is_valid",
            bool(isinstance(child, dict) and (child.get("metadata") or {}).get("is_valid")),
            True,
        )
        _add_check(
            checks,
            f"density_mode.3f.{feature}.mode",
            _resolved_density_mode(child) if isinstance(child, dict) else "missing",
            "univariate",
        )
    return modes, checks


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
            if chart_id == "density":
                row["density_mode"] = _resolved_density_mode(resolved)
                row["semantic_valid"] = _bivariate_density_matches_pair(resolved, list(pair))
            rows.append(row)
            if row["available"] and (
                not row["resolver_valid"]
                or (chart_id == "density" and not row.get("semantic_valid"))
            ):
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
    density_modes, density_checks = _validate_density_semantics(payloads, features)
    checks.extend(density_checks)
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
        "density_modes": density_modes,
        "pair_expansion": _json_safe(pair_rows),
    }


def _resolve_output_dir(raw_output: str) -> Path:
    output = Path(raw_output)
    if not output.is_absolute():
        output = REPO_ROOT / output
    resolved = output.resolve()
    outputs_root = (REPO_ROOT / "Outputs").resolve()
    if resolved != outputs_root and not resolved.is_relative_to(outputs_root):
        raise ValueError(f"--output must stay within {outputs_root}: {raw_output}")
    return resolved


def _write_summary(out_dir: Path, summary: dict[str, Any]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "summary.json"
    resolved_summary_path = summary_path.resolve()
    outputs_root = (REPO_ROOT / "Outputs").resolve()
    if not resolved_summary_path.is_relative_to(outputs_root):
        raise ValueError(f"summary.json must stay within {outputs_root}: {summary_path}")
    resolved_summary_path.write_text(
        json.dumps(_json_safe(summary), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return resolved_summary_path


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
    out_dir: Path | None = None
    try:
        out_dir = _resolve_output_dir(args.output)
        summary = run_validation(args)
        summary_path = _write_summary(out_dir, summary)
    except Exception as exc:
        error_summary = {
            "status": "ERROR",
            "failures": 1,
            "requested_output": str(args.output),
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
            },
        }
        try:
            fallback_dir = _resolve_output_dir("Outputs/db_chart_semantics_error")
        except Exception as fallback_exc:
            error_result = {
                "status": "ERROR",
                "failures": 1,
                "summary": None,
                "error": error_summary["error"],
                "summary_error": {
                    "type": type(fallback_exc).__name__,
                    "message": str(fallback_exc),
                },
            }
            print(json.dumps(error_result, ensure_ascii=False, indent=None if args.quiet else 2))
            return 2
        error_dir = out_dir if out_dir is not None else fallback_dir
        try:
            summary_path = _write_summary(error_dir, error_summary)
        except Exception as summary_exc:
            if error_dir == fallback_dir:
                fallback_summary_path: Path | None = None
            else:
                try:
                    fallback_summary_path = _write_summary(fallback_dir, error_summary)
                except Exception:
                    fallback_summary_path = None
            error_result = {
                "status": "ERROR",
                "failures": 1,
                "summary": str(fallback_summary_path) if fallback_summary_path else None,
                "error": error_summary["error"],
                "summary_error": {
                    "type": type(summary_exc).__name__,
                    "message": str(summary_exc),
                },
            }
            print(json.dumps(error_result, ensure_ascii=False, indent=None if args.quiet else 2))
            return 2
        if args.quiet:
            print(f"[db-chart-semantics] ERROR failures=1 summary={summary_path}")
        else:
            print(json.dumps({"status": "ERROR", "failures": 1, "summary": str(summary_path)}, ensure_ascii=False, indent=2))
        return 2

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
