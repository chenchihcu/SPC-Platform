"""
Parallel coordinates engine: 3 columns as axes, each row a line.
Phase 4 P1: triple-feature only.
"""
import pandas as pd
from typing import Dict, Any, List


class ParallelCoordEngine:
    """Parallel coordinates: normalized values for Volume, Area, Height per row."""

    @staticmethod
    def compute_parallel_coord(
        df: pd.DataFrame,
        cols: List[str],
        max_points: int = 500,
    ) -> Dict[str, Any]:
        """
        Return column names and normalized (0-1) values per row for drawing lines.
        Uses full valid rows for display to avoid sample-count distortion.
        `max_points` is kept only for backward-compatible call signatures.
        """
        if df is None or df.empty:
            return {
                "chart_type": "ParallelCoord",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": "無資料。"},
            }
        missing = [c for c in cols if c not in df.columns]
        if missing:
            return {
                "chart_type": "ParallelCoord",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": f"缺少欄位: {missing}."},
            }
        valid = df[cols].dropna()
        if len(valid) < 2:
            return {
                "chart_type": "ParallelCoord",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": "有效筆數不足。"},
            }
        n = len(valid)
        # Normalize and display with full valid data (no display sampling).
        min_ = valid.min()
        max_ = valid.max()
        range_ = max_ - min_
        range_ = range_.replace(0, 1)
        norm = (valid - min_) / range_
        values = norm.values.tolist()
        return {
            "chart_type": "ParallelCoord",
            "data": {"columns": cols, "values": values},
            "statistics": {
                "n": n,
                "displayed_n": n,
                "n_points": n,      # legacy alias (migration window)
                "n_displayed": n,  # legacy alias (migration window)
                "sampled_for_display": False,
                "sampling_method": "full_data",
                "sampling_seed": None,
                "downsample_step": 1,
                "normalization_basis": "full_valid_data",
            },
            "metadata": {"is_valid": True, "error": "", "sampled_for_display": False},
        }
