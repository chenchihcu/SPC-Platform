import pandas as pd
import pytest

from app.analytics.chart_registry import resolve_chart_payload
from app.viewmodels import chart_analysis_viewmodel as viewmodel
from app.viewmodels.chart_analysis_viewmodel import compute_analysis_payload


def _build_df(rows: int = 24) -> pd.DataFrame:
    data = {
        "Volume": [100 + (i % 5) for i in range(rows)],
        "Area": [200 + ((i * 2) % 7) for i in range(rows)],
        "Height": [50 + ((i * 3) % 6) for i in range(rows)],
        "PartType": ["R0402" if i % 2 == 0 else "C0603" for i in range(rows)],
        "RefDes": [f"R{i % 8 + 1}" for i in range(rows)],
        "BoardNo": [f"B{i // 6 + 1}" for i in range(rows)],
        "PanelId": [f"P{i // 6 + 1}" for i in range(rows)],
        "X": [float(i % 6) for i in range(rows)],
        "Y": [float(i // 6) for i in range(rows)],
    }
    return pd.DataFrame(data)


def _spec() -> dict:
    return {
        "volume": {"usl": 130, "lsl": 70, "target": 100},
        "area": {"usl": 260, "lsl": 150, "target": 200},
        "height": {"usl": 70, "lsl": 35, "target": 50},
    }


def test_output_matrix_single_dual_triple_feature_payloads_exist():
    df = _build_df()
    spec = _spec()

    payload1, err1 = compute_analysis_payload(df, ["Volume"], 130, 70, 100, workorder_spec=spec)
    assert err1 is None
    assert payload1 is not None
    for key in (
        "spc", "cap", "dist", "pareto", "spatial", "box", "normality",
        "ewma", "cusum", "run_chart", "subgroup", "repeated_offender",
    ):
        assert payload1.get(key) is not None, f"single-feature payload missing {key}"
    assert set(payload1.get("dual_parameters", {}).keys()) == {"Volume+Area", "Volume+Height", "Area+Height"}
    assert set(payload1.get("triple_parameters", {}).keys()) == {
        "anomaly_3f", "consistency_3f", "parallel_coord", "pass_fail_matrix", "hotelling_t2", "radar"
    }

    payload2, err2 = compute_analysis_payload(df, ["Volume", "Area"], 130, 70, 100, workorder_spec=spec)
    assert err2 is None
    assert payload2 is not None
    for key in ("scatter_spec", "quadrant", "bivariate_outlier", "density"):
        assert payload2.get(key) is not None, f"dual-feature payload missing {key}"
    assert set((payload2.get("parameters") or {}).keys()) == {"Volume", "Area"}
    assert set((payload2.get("dual_parameters") or {}).keys()) == {"Volume+Area"}
    reused_pair = payload2["dual_parameters"]["Volume+Area"]
    for chart_id in (
        "scatter_spec",
        "correlation_matrix",
        "correlation_heatmap",
        "quadrant",
        "bivariate_outlier",
        "density",
    ):
        assert reused_pair[chart_id] is payload2[chart_id]

    payload3, err3 = compute_analysis_payload(df, ["Volume", "Area", "Height"], 130, 70, 100, workorder_spec=spec)
    assert err3 is None
    assert payload3 is not None
    for key in ("anomaly_3f", "consistency_3f", "parallel_coord", "pass_fail_matrix", "hotelling_t2", "radar"):
        assert payload3.get(key) is not None, f"triple-feature payload missing {key}"
    assert set((payload3.get("parameters") or {}).keys()) == {"Volume", "Area", "Height"}
    assert set((payload3.get("dual_parameters") or {}).keys()) == {
        "Volume+Area", "Volume+Height", "Area+Height"
    }

    volume_height = resolve_chart_payload(
        payload3,
        "scatter_spec",
        features=["Volume", "Height"],
    )
    assert volume_height["metadata"]["is_valid"] is True
    assert volume_height["metadata"]["col_x"] == "Volume"
    assert volume_height["metadata"]["col_y"] == "Height"

    missing_pair_payload = dict(payload3)
    missing_pair_payload["dual_parameters"] = {}
    missing_pair = resolve_chart_payload(
        missing_pair_payload,
        "correlation_matrix",
        features=["Volume", "Height"],
    )
    assert missing_pair["metadata"]["is_valid"] is False
    assert missing_pair["metadata"]["incompatible"] is True
    assert not missing_pair.get("data", {}).get("labels")


@pytest.mark.parametrize(
    ("features", "expected_calls"),
    [(["Volume", "Area"], 1), (["Volume", "Area", "Height"], 3)],
)
def test_dual_parameter_builder_computes_each_pair_once(
    monkeypatch, features, expected_calls
):
    counters = {name: 0 for name in ("scatter", "correlation", "quadrant", "outlier", "density")}

    def counted(owner, method_name, counter_name):
        original = getattr(owner, method_name)

        def wrapper(*args, **kwargs):
            counters[counter_name] += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(owner, method_name, wrapper)

    counted(viewmodel.ScatterEngine, "compute_scatter_spec", "scatter")
    counted(viewmodel.CorrelationMatrixEngine, "compute_matrix", "correlation")
    counted(viewmodel.QuadrantEngine, "compute_quadrant", "quadrant")
    counted(viewmodel.BivariateOutlierEngine, "compute_bivariate_outlier", "outlier")
    counted(viewmodel.DensityEngine, "compute_density", "density")

    result = viewmodel._build_dual_feature_parameters(
        _build_df(), features, _spec()
    )

    assert len(result) == expected_calls
    assert set(counters.values()) == {expected_calls}
