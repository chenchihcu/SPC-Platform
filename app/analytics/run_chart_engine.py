"""
Run Chart engine: individual values in run order with center line.
Phase 4 P1: trend view without control limits.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any


class RunChartEngine:
    """Run chart: plot values in run order with mean (center) line."""

    @staticmethod
    def compute_run_chart(
        data: pd.Series,
        target_col: str = "Measurement",
    ) -> Dict[str, Any]:
        """
        Compute run-order data for plotting.
        Returns metadata.is_valid, data (indices, values), statistics (center_line).
        """
        valid_data = data.dropna()
        if valid_data.empty:
            return {
                "chart_type": "RunChart",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "target_col": target_col, "error": "無資料。"},
            }
        n = len(valid_data)
        center = float(valid_data.mean())
        normalize_mean = center
        normalize_std = float(valid_data.std(ddof=1)) if n > 1 else 0.0
        if not np.isfinite(normalize_std) or normalize_std == 0.0:
            normalize_std = 1.0
        displayed_n = n
        sampled = False
        values = valid_data.tolist()
        indices = valid_data.index.tolist()
        return {
            "chart_type": "RunChart",
            "data": {
                "values": values,
                "indices": indices,
            },
            "statistics": {
                "center_line": center,
                "n": n,
                "displayed_n": displayed_n,
                "downsample_step": 1,
                "sampled_for_display": sampled,
                "normalize_mean": normalize_mean,
                "normalize_std": normalize_std,
                "normalize_basis_n": n,
                "normalization_basis": "full_valid_data",
            },
            "metadata": {
                "is_valid": True,
                "target_col": target_col,
                "error": "",
                "sampled_for_display": sampled,
            },
        }
