from app.ui.pages.chart_analysis_page import _resolve_selection_override_ids


def test_triple_override_includes_all_3f_charts_for_single_payload_analysis():
    payload = {
        "selected_features": ["Volume"],
        "triple_parameters": {
            "anomaly_3f": {},
            "consistency_3f": {},
            "parallel_coord": {},
            "pass_fail_matrix": {},
        },
        "parameters": {"Volume": {}, "Area": {}, "Height": {}},
    }
    display_features = ["Volume", "Area", "Height"]

    dual_ids, triple_ids = _resolve_selection_override_ids(payload, display_features)

    assert dual_ids == set()
    assert {
        "anomaly_3f", "consistency_3f", "parallel_coord", "pass_fail_matrix",
        "imr_3f", "run_chart_3f", "ewma_3f", "cusum_3f", "boxplot_3f",
        "histogram_spec", "normality", "boxplot",
    }.issubset(triple_ids)


def test_dual_override_for_single_payload_analysis_with_precomputed_pair():
    payload = {
        "selected_features": ["Volume"],
        "dual_parameters": {
            "Area+Volume": {"scatter_spec": {}},
        },
        "parameters": {"Volume": {}, "Area": {}},
    }
    display_features = ["Volume", "Area"]

    dual_ids, triple_ids = _resolve_selection_override_ids(payload, display_features)

    assert {"scatter_spec", "quadrant", "bivariate_outlier", "density", "histogram_spec", "normality", "boxplot"}.issubset(dual_ids)
    assert triple_ids == set()


def test_no_override_when_payload_not_single_feature_analysis():
    payload = {
        "selected_features": ["Volume", "Area"],
        "dual_parameters": {"Volume+Area": {"scatter_spec": {}}},
        "triple_parameters": {"anomaly_3f": {}},
    }
    display_features = ["Volume", "Area", "Height"]

    dual_ids, triple_ids = _resolve_selection_override_ids(payload, display_features)

    assert dual_ids == set()
    assert triple_ids == set()
