from app.charts.base_chart import resolve_target_col


def test_resolve_target_col_prefers_metadata():
    payload = {
        "metadata": {"target_col": "Volume"},
        "analysis_context": {"target_col": "Area"},
    }
    assert resolve_target_col(payload) == "Volume"


def test_resolve_target_col_falls_back_to_analysis_context():
    payload = {
        "metadata": {},
        "analysis_context": {"target_col": "Height"},
    }
    assert resolve_target_col(payload) == "Height"


def test_resolve_target_col_empty_when_missing():
    assert resolve_target_col({}) == ""
