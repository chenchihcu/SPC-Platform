from app.analytics.chart_registry import resolve_chart_payload


def _single_feature_payload() -> dict:
    return {
        "selected_features": ["Volume"],
        "run_chart": {"metadata": {"is_valid": True}, "data": {"values": [1.0], "indices": [1]}, "statistics": {}},
        "dist": {"metadata": {"is_valid": True}, "data": {"bins": [1, 2], "counts": [2, 1]}},
        "cap": {"metadata": {"is_valid": True, "usl": 120.0, "lsl": 80.0}},
        "parameters": {
            "Volume": {
                "run_chart": {"metadata": {"is_valid": True}, "data": {"values": [1.0], "indices": [1]}, "statistics": {}},
                "spc": {"metadata": {"is_valid": True}, "data": {"values": [1.0], "indices": [1]}, "statistics": {}},
                "dist": {"metadata": {"is_valid": True}, "data": {"bins": [1, 2], "counts": [2, 1]}},
                "cap": {"metadata": {"is_valid": True, "usl": 120.0, "lsl": 80.0, "target": 100.0}},
            },
            "Area": {
                "run_chart": {"metadata": {"is_valid": True}, "data": {"values": [2.0], "indices": [1]}, "statistics": {}},
                "spc": {"metadata": {"is_valid": True}, "data": {"values": [2.0], "indices": [1]}, "statistics": {}},
                "dist": {"metadata": {"is_valid": True}, "data": {"bins": [1, 2], "counts": [1, 2]}},
                "cap": {"metadata": {"is_valid": True, "usl": 130.0, "lsl": 70.0, "target": 100.0}},
            },
            "Height": {
                "run_chart": {"metadata": {"is_valid": True}, "data": {"values": [3.0], "indices": [1]}, "statistics": {}},
                "spc": {"metadata": {"is_valid": True}, "data": {"values": [3.0], "indices": [1]}, "statistics": {}},
                "dist": {"metadata": {"is_valid": True}, "data": {"bins": [1, 2], "counts": [3, 1]}},
                "cap": {"metadata": {"is_valid": True, "usl": 1.2, "lsl": 0.8, "target": 1.0}},
            },
        },
        "dual_parameters": {
            "Volume+Area": {
                "scatter_spec": {"metadata": {"is_valid": True}, "data": {"x": [1.0], "y": [2.0]}, "statistics": {}}
            }
        },
        "triple_parameters": {
            "anomaly_3f": {"metadata": {"is_valid": True}, "data": {"scores": [0.1]}, "statistics": {}}
        },
    }


def test_parity_n1_override_dual_chart() -> None:
    payload = _single_feature_payload()
    ui_slice = resolve_chart_payload(payload, "scatter_spec", features=["Volume", "Area"], context="ui")
    report_slice = resolve_chart_payload(payload, "scatter_spec", features=["Volume", "Area"], context="report")
    assert ui_slice == report_slice
    assert ui_slice["metadata"]["is_valid"] is True


def test_parity_n1_override_triple_chart() -> None:
    payload = _single_feature_payload()
    ui_slice = resolve_chart_payload(payload, "anomaly_3f", features=["Volume", "Area", "Height"], context="ui")
    report_slice = resolve_chart_payload(payload, "anomaly_3f", features=["Volume", "Area", "Height"], context="report")
    assert ui_slice == report_slice
    assert ui_slice["metadata"]["is_valid"] is True


def test_parity_multi_feature_histogram_spec() -> None:
    payload = _single_feature_payload()
    ui_slice = resolve_chart_payload(payload, "histogram_spec", features=["Volume", "Area"], normalized=True, context="ui")
    report_slice = resolve_chart_payload(payload, "histogram_spec", features=["Volume", "Area"], normalized=True, context="report")
    assert ui_slice == report_slice
    assert ui_slice["_multi_feature"] is True
