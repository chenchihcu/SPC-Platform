import pandas as pd

from app.analytics.anova_engine import AnovaEngine


def test_anova_one_way_detects_group_difference() -> None:
    df = pd.DataFrame(
        {
            "PartType": ["A"] * 8 + ["B"] * 8,
            "Height": [0.120, 0.121, 0.119, 0.122, 0.120, 0.118, 0.121, 0.119,
                       0.155, 0.156, 0.154, 0.157, 0.155, 0.153, 0.156, 0.154],
        }
    )

    result = AnovaEngine.compute_one_way(df, "Height", group_col="PartType")

    assert result["metadata"]["is_valid"] is True
    assert result["statistics"]["group_count"] == 2
    assert result["statistics"]["p_value"] < 0.05


def test_anova_requires_group_column() -> None:
    df = pd.DataFrame({"Height": [0.1, 0.2, 0.3]})
    result = AnovaEngine.compute_one_way(df, "Height", group_col="PartType")
    assert result["metadata"]["is_valid"] is False
    assert "PartType" in result["metadata"]["error"]


def test_anova_insufficient_groups_returns_empty_data() -> None:
    """Bug B1 regression: contract requires data={} and statistics={} on failure."""
    df = pd.DataFrame(
        {"PartType": ["A", "A", "A"], "Height": [0.12, 0.13, 0.11]}
    )
    result = AnovaEngine.compute_one_way(df, "Height", group_col="PartType")
    assert result["metadata"]["is_valid"] is False
    assert result["data"] == {}
    assert result["statistics"] == {}
