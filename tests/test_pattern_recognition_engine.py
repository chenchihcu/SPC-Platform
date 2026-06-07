import pandas as pd

from app.analytics.pattern_recognition_engine import PatternRecognitionEngine


def test_pattern_recognition_requires_minimum_sample_size() -> None:
    result = PatternRecognitionEngine.compute_nelson(
        pd.Series([1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6]),
        "Volume",
    )
    assert result["metadata"]["is_valid"] is False
    assert "至少需 8 筆" in result["metadata"]["error"]


def test_pattern_recognition_detects_core_nelson_rules() -> None:
    # First 10 points on the same side of mean -> R2.
    # Tail contains strict monotonic run -> R3.
    series = pd.Series([1.0] * 10 + [-1.0] * 4 + [0.0, 1.0, 2.0, 3.0, 4.0, 5.0])

    result = PatternRecognitionEngine.compute_nelson(series, "Volume")

    assert result["metadata"]["is_valid"] is True
    rule_hits = result["data"]["rule_hits"]
    rules = {item["rule"] for item in rule_hits}
    assert "R2" in rules
    assert "R3" in rules
    assert result["statistics"]["rule_count"] >= 2
    assert result["statistics"]["hit_point_count"] > 0
