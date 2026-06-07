import pandas as pd

from app.viewmodels.chart_analysis_viewmodel import compute_analysis_payload


def _build_df(rows: int = 18) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Volume": [100 + (i % 4) for i in range(rows)],
            "Area": [200 + (i % 5) for i in range(rows)],
            "Height": [50 + (i % 3) for i in range(rows)],
            "PartType": ["R0402" if i % 2 == 0 else "C0603" for i in range(rows)],
            "RefDes": [f"R{i % 6 + 1}" for i in range(rows)],
            "BoardNo": [f"B{i // 6 + 1}" for i in range(rows)],
            "X": [float(i % 6) for i in range(rows)],
            "Y": [float(i // 6) for i in range(rows)],
        }
    )


def test_dual_parameter_failure_returns_visible_invalid_payload(monkeypatch):
    df = _build_df()

    def _boom(*args, **kwargs):
        raise RuntimeError("forced scatter failure")

    monkeypatch.setattr(
        "app.viewmodels.chart_analysis_viewmodel.ScatterEngine.compute_scatter_spec",
        _boom,
    )

    payload, err = compute_analysis_payload(df, ["Volume"], 130, 70, 100, workorder_spec={})
    assert err is None
    assert payload is not None

    pair = payload["dual_parameters"]["Volume+Area"]["scatter_spec"]
    assert pair["metadata"]["is_valid"] is False
    assert "計算失敗" in pair["metadata"]["error"]


def test_triple_parameter_failure_returns_visible_invalid_payload(monkeypatch):
    df = _build_df()

    def _boom(*args, **kwargs):
        raise RuntimeError("forced anomaly failure")

    monkeypatch.setattr(
        "app.viewmodels.chart_analysis_viewmodel.Anomaly3FEngine.compute_anomaly_3f",
        _boom,
    )

    payload, err = compute_analysis_payload(df, ["Volume"], 130, 70, 100, workorder_spec={})
    assert err is None
    assert payload is not None

    anomaly = payload["triple_parameters"]["anomaly_3f"]
    assert anomaly["metadata"]["is_valid"] is False
    assert "計算失敗" in anomaly["metadata"]["error"]
