"""
Density engine.
Supports both:
- 1D density (single feature) for distribution analysis.
- 2D hexbin density (dual feature) for association analysis.
"""
from typing import Any, Dict

import numpy as np
import pandas as pd
from scipy import stats  # type: ignore[import-untyped]


class DensityEngine:
    """2D density (hexbin) data from two columns."""

    @staticmethod
    def compute_univariate_density(
        series: pd.Series,
        col: str,
        points: int = 160,
    ) -> Dict[str, Any]:
        """Return KDE-ready 1D density payload for one feature."""
        if series is None:
            return {
                "chart_type": "Density",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": "缺少單特徵資料。"},
            }
        valid = series.replace([np.inf, -np.inf], np.nan).dropna()
        if len(valid) < 3:
            return {
                "chart_type": "Density",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": "有效資料不足（至少需 3 筆）。"},
            }
        values = valid.to_numpy(dtype=float)
        if not np.isfinite(values).all() or float(np.std(values)) < 1e-12:
            return {
                "chart_type": "Density",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": "資料變異不足，無法估計密度。"},
            }
        x_grid = np.linspace(float(np.min(values)), float(np.max(values)), points)
        try:
            kde = stats.gaussian_kde(values)
            y_density = kde.evaluate(x_grid)
        except np.linalg.LinAlgError:
            return {
                "chart_type": "Density",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": "KDE 共變異數矩陣奇異，無法估計密度。"},
            }
        return {
            "chart_type": "Density",
            "data": {
                "mode": "univariate",
                "values": values.tolist(),
                "x_grid": x_grid.tolist(),
                "density": y_density.tolist(),
                "col": col,
            },
            "statistics": {
                "n_points": int(len(values)),
                "points": int(points),
            },
            "metadata": {"is_valid": True, "error": ""},
        }

    @staticmethod
    def compute_density(
        df: pd.DataFrame,
        col_x: str,
        col_y: str,
        gridsize: int = 30,
    ) -> Dict[str, Any]:
        """
        Return x, y arrays for hexbin/density plot. Optionally limit points for large data.
        """
        if df is None or df.empty or col_x not in df.columns or col_y not in df.columns:
            return {
                "chart_type": "Density",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": "無資料或缺少雙特徵欄位。"},
            }
        valid = df[[col_x, col_y]].dropna()
        if len(valid) < 2:
            return {
                "chart_type": "Density",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": "有效點數不足。"},
            }
        x = valid[col_x].tolist()
        y = valid[col_y].tolist()
        return {
            "chart_type": "Density",
            "data": {"x": x, "y": y, "col_x": col_x, "col_y": col_y},
            "statistics": {"gridsize": gridsize, "n_points": len(x)},
            "metadata": {"is_valid": True, "error": ""},
        }
