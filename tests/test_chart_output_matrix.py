import pandas as pd

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
        "anomaly_3f", "consistency_3f", "parallel_coord", "pass_fail_matrix"
    }

    payload2, err2 = compute_analysis_payload(df, ["Volume", "Area"], 130, 70, 100, workorder_spec=spec)
    assert err2 is None
    assert payload2 is not None
    for key in ("scatter_spec", "quadrant", "bivariate_outlier", "density"):
        assert payload2.get(key) is not None, f"dual-feature payload missing {key}"
    assert set((payload2.get("parameters") or {}).keys()) == {"Volume", "Area"}

    payload3, err3 = compute_analysis_payload(df, ["Volume", "Area", "Height"], 130, 70, 100, workorder_spec=spec)
    assert err3 is None
    assert payload3 is not None
    for key in ("anomaly_3f", "consistency_3f", "parallel_coord", "pass_fail_matrix"):
        assert payload3.get(key) is not None, f"triple-feature payload missing {key}"
    assert set((payload3.get("parameters") or {}).keys()) == {"Volume", "Area", "Height"}
