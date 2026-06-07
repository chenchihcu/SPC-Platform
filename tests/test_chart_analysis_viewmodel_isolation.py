"""F2 regression: per-engine isolation in _build_feature_parameters.

Verifies that when a single engine raises an exception, the wrapper
`_safe_compute_chart` converts it into a contract-compliant invalid payload
and the rest of the per-feature bundle still completes — i.e. one engine
failure does NOT propagate up and kill the entire payload (Bug A blast
radius prevention).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.analytics.density_engine import DensityEngine
from app.viewmodels.chart_analysis_viewmodel import (
    _build_feature_parameters,
    _safe_compute_chart,
)


# ── _safe_compute_chart unit behaviour ──────────────────────────────────────
def test_safe_compute_chart_passes_through_valid_result():
    def fake(*_a, **_k):
        return {
            "chart_type": "Foo",
            "data": {"x": 1},
            "statistics": {"n": 1},
            "metadata": {"is_valid": True, "error": ""},
        }
    out = _safe_compute_chart("Foo", fake)
    assert out["metadata"]["is_valid"] is True
    assert out["data"] == {"x": 1}


def test_safe_compute_chart_converts_value_error_to_invalid_payload():
    def boom(*_a, **_k):
        raise ValueError("synthetic failure")
    out = _safe_compute_chart("Foo", boom)
    assert out["metadata"]["is_valid"] is False
    assert out["data"] == {}
    assert out["statistics"] == {}
    assert "synthetic failure" in out["metadata"]["error"]


def test_safe_compute_chart_converts_linalgerror_to_invalid_payload():
    """np.linalg.LinAlgError is a ValueError subclass and must be caught."""
    def boom(*_a, **_k):
        raise np.linalg.LinAlgError("singular covariance")
    out = _safe_compute_chart("Density", boom)
    assert out["metadata"]["is_valid"] is False
    assert out["data"] == {}


# ── _build_feature_parameters integration: density failure isolation ────────
def _make_df(n: int = 60) -> pd.DataFrame:
    """Minimal df with the columns used across single-feature engines."""
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "Volume":   rng.normal(100.0, 10.0, n),
        "PartType": (["A"] * (n // 2)) + (["B"] * (n - n // 2)),
        "RefDes":   ["U1"] * n,
        "BoardNo":  [(i // 10) + 1 for i in range(n)],
    })


def test_build_feature_parameters_isolates_density_failure(monkeypatch):
    """If DensityEngine raises, payload still completes and other engines run."""
    def boom(*_a, **_k):
        raise np.linalg.LinAlgError("singular covariance")

    monkeypatch.setattr(DensityEngine, "compute_univariate_density", boom)

    params = _build_feature_parameters(
        filtered_df=_make_df(),
        feature_cols=["Volume"],
        workorder_spec={},
    )

    assert "Volume" in params, "feature bundle missing — outer call propagated exception"
    bundle = params["Volume"]

    # Density slot must be contract-compliant invalid (not raised, not partial)
    density = bundle["density"]
    assert density["metadata"]["is_valid"] is False
    assert density["data"] == {}
    assert density["statistics"] == {}

    # At least one *other* engine must still have run — proves no cascade
    # (we don't assert is_valid=True because tiny synthetic df may fail
    # other engines' min-N guards; we only assert the slot exists as a dict)
    assert isinstance(bundle.get("normality"), dict)
    assert isinstance(bundle.get("anova_parttype"), dict)
    assert isinstance(bundle.get("ewma"), dict)
    assert isinstance(bundle.get("run_chart"), dict)


def test_build_feature_parameters_happy_path_all_slots_present():
    """Sanity: when no engine raises, every documented slot is populated."""
    params = _build_feature_parameters(
        filtered_df=_make_df(),
        feature_cols=["Volume"],
        workorder_spec={},
    )

    assert "Volume" in params
    bundle = params["Volume"]
    expected_keys = {
        "spc", "xbar_r", "cap", "dist", "box",
        "normality", "density", "ewma", "cusum", "run_chart",
        "anova_parttype", "pattern_recognition",
        "ooc_analysis", "shift_detection", "drift_detection", "outlier_analysis",
        "subgroup", "repeated_offender", "pareto", "spatial",
    }
    assert expected_keys.issubset(set(bundle.keys()))
