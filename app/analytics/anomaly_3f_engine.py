"""
3-feature anomaly score: composite z-score over Volume, Area, Height for SMT consistency.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List


class Anomaly3FEngine:
    """Computes a simple composite anomaly score from three columns (e.g. mean of absolute z-scores)."""

    @staticmethod
    def compute_anomaly_3f(
        filtered_df: pd.DataFrame,
        cols: List[str],
    ) -> Dict[str, Any]:
        """
        cols should be ["Volume", "Area", "Height"] (or subset order).
        Score per row = mean of abs(z) for each column; high score = anomalous.
        """
        if filtered_df is None or filtered_df.empty:
            return {
                "chart_type": "Anomaly3F",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": "無資料 (No data)."},
            }
        missing = [c for c in cols if c not in filtered_df.columns]
        if missing:
            return {
                "chart_type": "Anomaly3F",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": f"缺少欄位: {missing}."},
            }
        valid = filtered_df[cols].dropna()
        if len(valid) < 2:
            return {
                "chart_type": "Anomaly3F",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": "有效筆數不足 (N<2)."},
            }
        z = (valid - valid.mean()) / (valid.std().replace(0, 1e-9))
        score = np.abs(z).mean(axis=1)
        indices = valid.index.tolist()
        scores = score.tolist()
        return {
            "chart_type": "Anomaly3F",
            "data": {
                "indices": indices,
                "scores": scores,
                "columns": cols,
            },
            "statistics": {
                "n": len(scores),
                "mean_score": float(np.mean(scores)),
                "max_score": float(np.max(scores)),
            },
            "metadata": {
                "is_valid": True,
                "error": "",
                "columns": cols,
            },
            "analysis_context": {"columns": cols},
        }
