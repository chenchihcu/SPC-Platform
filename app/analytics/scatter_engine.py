"""
Scatter + Spec Zones: bivariate plot with optional USL/LSL rectangles for SMT failure analysis.
"""
import math

import pandas as pd

from app.analytics.pearson_utils import pearson_r_safe
from typing import Dict, Any, Optional, Tuple


def _parse_spec(spec: Optional[Dict[str, Any]]) -> Tuple[Optional[float], Optional[float]]:
    """Return (usl, lsl) from workorder_spec entry (values may be strings)."""
    if not spec or not isinstance(spec, dict):
        return None, None
    try:
        usl = float(spec.get("usl", "")) if spec.get("usl") else None
        lsl = float(spec.get("lsl", "")) if spec.get("lsl") else None
        return usl, lsl
    except (TypeError, ValueError):
        return None, None


class ScatterEngine:
    """Produces scatter data and spec zone bounds for two measurement columns."""

    @staticmethod
    def compute_scatter_spec(
        filtered_df: pd.DataFrame,
        col_x: str,
        col_y: str,
        spec_x: Optional[Dict[str, Any]] = None,
        spec_y: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Returns scatter points and optional spec rectangles (usl/lsl per axis).
        """
        if filtered_df is None or filtered_df.empty:
            return {
                "chart_type": "ScatterSpec",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": "無資料 (No data)."},
            }
        if col_x not in filtered_df.columns or col_y not in filtered_df.columns:
            return {
                "chart_type": "ScatterSpec",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": f"缺少欄位 {col_x} 或 {col_y}."},
            }
        valid = filtered_df[[col_x, col_y]].dropna()
        if len(valid) < 2:
            return {
                "chart_type": "ScatterSpec",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": "有效點數不足 (N<2)."},
            }
        x_vals = valid[col_x].tolist()
        y_vals = valid[col_y].tolist()
        usl_x, lsl_x = _parse_spec(spec_x)
        usl_y, lsl_y = _parse_spec(spec_y)
        corr_val = pearson_r_safe(valid[col_x], valid[col_y])
        if not math.isfinite(corr_val):
            return {
                "chart_type": "ScatterSpec",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": "輸入資料變異不足，統計量為 NaN。"},
            }
        return {
            "chart_type": "ScatterSpec",
            "data": {
                "x": x_vals,
                "y": y_vals,
                "usl_x": usl_x,
                "lsl_x": lsl_x,
                "usl_y": usl_y,
                "lsl_y": lsl_y,
            },
            "statistics": {
                "n": len(x_vals),
                "corr": corr_val,
            },
            "metadata": {
                "is_valid": True,
                "error": "",
                "col_x": col_x,
                "col_y": col_y,
            },
            "analysis_context": {"col_x": col_x, "col_y": col_y},
        }
