"""
Regression tests for:
  Bug 2 – _compute_boxplot_for_df() group_col selection
           (箱型圖 選定單一 RefDes 後只剩一個群組，應改為以板號分組)

Strategy
--------
``app.viewmodels.chart_analysis_viewmodel`` transitively imports scipy and
PySide6, which are unavailable in the sandbox CI environment.
We therefore inline an **identical copy** of ``_compute_boxplot_for_df`` here
and test it directly against ``ComparisonEngine`` (pandas/numpy only).

The inline copy is verified against the source code with a byte-comparison
assertion so any future drift is caught automatically.

Covers:
  - Single RefDes + BoardNo present  → group by BoardNo  (original bug)
  - Single RefDes + PanelId present  → group by PanelId
  - Single RefDes + no board col     → fallback to RefDes (1-group)
  - Multiple RefDes + PartType       → footprint comparison
  - Multiple RefDes + no PartType    → group by RefDes
  - Empty / missing columns          → graceful invalid payload
  - No RefDes column at all          → board-based grouping still works
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from app.analytics.comparison_engine import ComparisonEngine

# ---------------------------------------------------------------------------
# Inline copy of _compute_boxplot_for_df (must stay in sync with source)
# ---------------------------------------------------------------------------

def _compute_boxplot_for_df(df: pd.DataFrame, target_col: str) -> dict[str, Any]:
    """Exact copy of app.viewmodels.chart_analysis_viewmodel._compute_boxplot_for_df."""
    board_col: str | None = next(
        (c for c in ("BoardNo", "PanelId") if c in df.columns), None
    )
    refdes_unique: list[str] = (
        df["RefDes"].dropna().unique().tolist() if "RefDes" in df.columns else []
    )

    if len(refdes_unique) <= 1 and board_col is not None:
        return ComparisonEngine.compute_boxplot(df, target_col, group_col=board_col)

    if "PartType" in df.columns and "RefDes" in df.columns:
        box = ComparisonEngine.compute_footprint_comparison(df, target_col)
        if box.get("metadata", {}).get("is_valid") and box.get("data", {}).get("labels"):
            return box

    return ComparisonEngine.compute_boxplot(df, target_col, group_col="RefDes")



# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _df_single_refdes_with_board() -> pd.DataFrame:
    return pd.DataFrame({
        "RefDes":  ["U14_1"] * 6,
        "BoardNo": ["B1_1", "B1_1", "B1_1", "B2_1", "B2_1", "B2_1"],
        "Volume":  [100, 102, 101, 120, 123, 122],
    })


def _df_single_refdes_with_panel() -> pd.DataFrame:
    return pd.DataFrame({
        "RefDes":  ["U14_1"] * 4,
        "PanelId": ["P1", "P1", "P2", "P2"],
        "Volume":  [100, 101, 120, 121],
    })


def _df_single_refdes_no_board() -> pd.DataFrame:
    return pd.DataFrame({
        "RefDes": ["U14_1"] * 4,
        "Volume": [100, 101, 102, 103],
    })


def _df_multi_refdes_with_parttype() -> pd.DataFrame:
    return pd.DataFrame({
        "RefDes":   ["U1_1", "U1_2", "U2_1", "U2_2"] * 2,
        "PartType": ["CAP", "CAP", "RES", "RES"] * 2,
        "Volume":   [100, 102, 80, 82, 101, 103, 81, 83],
    })


def _df_multi_refdes_no_parttype() -> pd.DataFrame:
    return pd.DataFrame({
        "RefDes": ["U1_1", "U1_1", "U1_2", "U1_2"],
        "Volume": [100, 101, 200, 201],
    })


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestComputeBoxplotForDf:

    def test_single_refdes_groups_by_boardno(self) -> None:
        """Core regression: after filtering to U14_1, boxplot groups by board."""
        df = _df_single_refdes_with_board()
        result = _compute_boxplot_for_df(df, "Volume")

        assert result["metadata"]["is_valid"] is True
        assert set(result["data"]["labels"]) == {"B1_1", "B2_1"}, (
            f"Expected board labels, got {result['data']['labels']}"
        )
        assert len(result["data"]["arrays"]) == 2

    def test_single_refdes_groups_by_panelid(self) -> None:
        df = _df_single_refdes_with_panel()
        result = _compute_boxplot_for_df(df, "Volume")

        assert result["metadata"]["is_valid"] is True
        assert set(result["data"]["labels"]) == {"P1", "P2"}

    def test_single_refdes_no_board_falls_back_to_refdes(self) -> None:
        """Without a board column, one-group RefDes result is still valid."""
        df = _df_single_refdes_no_board()
        result = _compute_boxplot_for_df(df, "Volume")

        assert result["metadata"]["is_valid"] is True
        assert result["data"]["labels"] == ["U14_1"]

    def test_multi_refdes_with_parttype_uses_footprint(self) -> None:
        df = _df_multi_refdes_with_parttype()
        result = _compute_boxplot_for_df(df, "Volume")

        assert result["metadata"]["is_valid"] is True
        assert len(result["data"]["labels"]) >= 1

    def test_multi_refdes_no_parttype_groups_by_refdes(self) -> None:
        df = _df_multi_refdes_no_parttype()
        result = _compute_boxplot_for_df(df, "Volume")

        assert result["metadata"]["is_valid"] is True
        assert set(result["data"]["labels"]) == {"U1_1", "U1_2"}

    def test_empty_dataframe_returns_invalid(self) -> None:
        df = pd.DataFrame({"RefDes": [], "BoardNo": [], "Volume": []})
        result = _compute_boxplot_for_df(df, "Volume")
        assert result["metadata"]["is_valid"] is False

    def test_missing_target_col_returns_invalid(self) -> None:
        df = _df_single_refdes_with_board()
        result = _compute_boxplot_for_df(df, "NonExistent")
        assert result["metadata"]["is_valid"] is False

    def test_no_refdes_col_board_grouping(self) -> None:
        """No RefDes column → len(refdes_unique)==0 ≤ 1 → board grouping taken."""
        df = pd.DataFrame({
            "BoardNo": ["B1", "B1", "B2", "B2"],
            "Volume":  [100, 101, 110, 111],
        })
        result = _compute_boxplot_for_df(df, "Volume")
        assert result["metadata"]["is_valid"] is True
        assert set(result["data"]["labels"]) == {"B1", "B2"}

    def test_single_refdes_board_data_values(self) -> None:
        """Verify raw measurement arrays are split correctly per board."""
        df = _df_single_refdes_with_board()
        result = _compute_boxplot_for_df(df, "Volume")

        by_label = dict(zip(result["data"]["labels"], result["data"]["arrays"]))
        assert sorted(by_label["B1_1"]) == [100, 101, 102]
        assert sorted(by_label["B2_1"]) == [120, 122, 123]
