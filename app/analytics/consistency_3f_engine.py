"""
Multi-feature consistency: Volume/Area vs Height relationship for SMT (e.g. V/A should approximate H).
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional


class Consistency3FEngine:
    """Checks consistency between three features: col[0]/col[1] ratio vs col[2]."""

    DEFAULT_COLS = ["Volume", "Area", "Height"]

    @staticmethod
    def compute_consistency_3f(
        filtered_df: pd.DataFrame,
        cols: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Computes standardized consistency residual between ratio and height.
        cols defaults to ["Volume", "Area", "Height"] when not provided.
        diff_va_h = z(Volume/Area) - z(Height)
        """
        cols = cols if cols and len(cols) == 3 else Consistency3FEngine.DEFAULT_COLS
        if filtered_df is None or filtered_df.empty:
            return {
                "chart_type": "Consistency3F",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": "無資料 (No data)."},
            }
        missing = [c for c in cols if c not in filtered_df.columns]
        if missing:
            return {
                "chart_type": "Consistency3F",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": f"缺少欄位: {missing}."},
            }
        col_x, col_y, col_z = cols[0], cols[1], cols[2]
        valid = filtered_df[cols].dropna()
        valid = valid[(valid[col_y] > 0) & (valid[col_x] > 0)]
        if len(valid) < 2:
            return {
                "chart_type": "Consistency3F",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": f"有效筆數不足或 {col_y}/{col_x} 需為正 (N<2)."},
            }
        vol = valid[col_x]
        area = valid[col_y]
        height = valid[col_z]
        ratio_va = (vol / area).replace([np.inf, -np.inf], np.nan)
        keep = ratio_va.notna()
        ratio_va = ratio_va[keep]
        height = height[keep]
        if len(ratio_va) < 2:
            return {
                "chart_type": "Consistency3F",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": f"{col_x}/{col_y} 計算後有效筆數不足."},
            }
        ratio_std = float(ratio_va.std()) if len(ratio_va) > 1 else 0.0
        height_std = float(height.std()) if len(height) > 1 else 0.0
        ratio_den = ratio_std if ratio_std > 0 else 1e-9
        height_den = height_std if height_std > 0 else 1e-9
        ratio_z = (ratio_va - ratio_va.mean()) / ratio_den
        height_z = (height - height.mean()) / height_den
        diff = ratio_z - height_z
        return {
            "chart_type": "Consistency3F",
            "data": {
                "indices": ratio_va.index.tolist(),
                "ratio_va": ratio_va.tolist(),
                "height": height.tolist(),
                "ratio_va_z": ratio_z.tolist(),
                "height_z": height_z.tolist(),
                "diff_va_h": diff.tolist(),
            },
            "statistics": {
                "n": len(ratio_va),
                "mean_diff": float(diff.mean()),
                "std_diff": float(diff.std()) if len(diff) > 1 else 0.0,
                "ratio_std": ratio_std,
                "height_std": height_std,
            },
            "metadata": {
                "is_valid": True,
                "error": "",
                "columns": cols,
            },
            "analysis_context": {"columns": cols},
        }
