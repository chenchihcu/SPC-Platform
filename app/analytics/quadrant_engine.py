"""
Quadrant classification: four quadrants from two features using spec center or median as split.
"""
import pandas as pd
from typing import Dict, Any, Optional


def _parse_spec_center(spec: Optional[Dict[str, Any]]) -> Optional[float]:
    """Return target or (usl+lsl)/2 as center for quadrant split."""
    if not spec or not isinstance(spec, dict):
        return None
    try:
        if spec.get("target") not in (None, ""):
            return float(spec["target"])
        usl = float(spec.get("usl", "")) if spec.get("usl") else None
        lsl = float(spec.get("lsl", "")) if spec.get("lsl") else None
        if usl is not None and lsl is not None:
            return (usl + lsl) / 2.0
        return None
    except (TypeError, ValueError):
        return None


class QuadrantEngine:
    """Classifies points into four quadrants (high/low x, high/low y) for SMT dual-feature analysis."""

    @staticmethod
    def compute_quadrant(
        filtered_df: pd.DataFrame,
        col_x: str,
        col_y: str,
        spec_x: Optional[Dict[str, Any]] = None,
        spec_y: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Returns quadrant counts and per-point quadrant labels (Q1..Q4).
        Split uses spec center or median of each column.
        """
        if filtered_df is None or filtered_df.empty:
            return {
                "chart_type": "Quadrant",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": "無資料 (No data)."},
            }
        if col_x not in filtered_df.columns or col_y not in filtered_df.columns:
            return {
                "chart_type": "Quadrant",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": f"缺少欄位 {col_x} 或 {col_y}."},
            }
        valid = filtered_df[[col_x, col_y]].dropna()
        if len(valid) < 2:
            return {
                "chart_type": "Quadrant",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": "有效點數不足 (N<2)."},
            }
        center_x = _parse_spec_center(spec_x)
        center_y = _parse_spec_center(spec_y)
        if center_x is None:
            center_x = float(valid[col_x].median())
        if center_y is None:
            center_y = float(valid[col_y].median())
        x_vals = valid[col_x].tolist()
        y_vals = valid[col_y].tolist()
        q_list = []
        for x, y in zip(x_vals, y_vals):
            if x >= center_x and y >= center_y:
                q = 1
            elif x < center_x and y >= center_y:
                q = 2
            elif x < center_x and y < center_y:
                q = 3
            else:
                q = 4
            q_list.append(q)
        from collections import Counter
        counts = Counter(q_list)
        return {
            "chart_type": "Quadrant",
            "data": {
                "x": x_vals,
                "y": y_vals,
                "quadrant": q_list,
                "center_x": center_x,
                "center_y": center_y,
                "count_q1": counts.get(1, 0),
                "count_q2": counts.get(2, 0),
                "count_q3": counts.get(3, 0),
                "count_q4": counts.get(4, 0),
            },
            "statistics": {
                "center_x": center_x,
                "center_y": center_y,
                "n": len(x_vals),
            },
            "metadata": {
                "is_valid": True,
                "error": "",
                "col_x": col_x,
                "col_y": col_y,
            },
            "analysis_context": {"col_x": col_x, "col_y": col_y},
        }
