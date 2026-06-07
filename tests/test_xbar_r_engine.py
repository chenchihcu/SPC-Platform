import pandas as pd

from app.analytics.xbar_r_engine import XbarREngine


def test_xbar_r_engine_computes_limits_with_board_groups() -> None:
    df = pd.DataFrame(
        {
            "BoardNo": ["B1", "B1", "B1", "B2", "B2", "B2", "B3", "B3", "B3"],
            "Volume": [100.0, 101.0, 99.8, 100.2, 100.1, 100.3, 99.7, 99.9, 100.0],
        }
    )

    result = XbarREngine.compute_xbar_r(df, "Volume")

    assert result["metadata"]["is_valid"] is True
    assert result["statistics"]["n_subgroups"] == 3
    assert result["statistics"]["n_effective"] >= 2
    assert "ucl_xbar" in result["statistics"]
    assert "ucl_r" in result["statistics"]


def test_xbar_r_engine_returns_invalid_when_column_missing() -> None:
    df = pd.DataFrame({"BoardNo": ["B1", "B2"]})
    result = XbarREngine.compute_xbar_r(df, "Volume")
    assert result["metadata"]["is_valid"] is False
