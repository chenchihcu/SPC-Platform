"""
EWMA (Exponentially Weighted Moving Average) chart engine.
Phase 3 P1: small shift detection with lambda smoothing.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

from app.analytics.statistical_utils import StatisticalUtils


class EWMAEngine:
    """EWMA control chart: z_i = lambda * x_i + (1 - lambda) * z_{i-1}, z_0 = mean."""

    DEFAULT_LAMBDA = 0.2
    DEFAULT_L = 3.0  # width of control limits in sigma units

    @staticmethod
    def compute_ewma(
        data: pd.Series,
        target_col: str = "Measurement",
        lam: Optional[float] = None,
        l_mult: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Compute EWMA statistic and control limits.
        Returns structure compatible with BaseChart (metadata.is_valid, data, statistics).
        """
        lam = lam if lam is not None else EWMAEngine.DEFAULT_LAMBDA
        l_mult = l_mult if l_mult is not None else EWMAEngine.DEFAULT_L
        is_valid, msg = StatisticalUtils.is_valid_for_spc(data)
        if not is_valid:
            return {
                "chart_type": "EWMA",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "target_col": target_col, "error": msg},
            }
        valid_data = data.dropna()
        n = len(valid_data)
        mu0 = float(valid_data.mean())
        sigma = float(valid_data.std(ddof=1))
        if sigma <= 0:
            return {
                "chart_type": "EWMA",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "target_col": target_col, "error": "Standard deviation is 0."},
            }
        # EWMA sequence: z_0 = mu0, z_i = lam * x_i + (1-lam) * z_{i-1}
        vals = valid_data.values
        z = np.empty(n)
        z[0] = mu0
        for i in range(1, n):
            z[i] = lam * vals[i] + (1 - lam) * z[i - 1]
        # Asymptotic control limits: mu0 +/- L * sigma * sqrt(lam/(2-lam))
        sigma_ewma = sigma * np.sqrt(lam / (2 - lam))
        ucl = mu0 + l_mult * sigma_ewma
        lcl = mu0 - l_mult * sigma_ewma
        ooc_mask = (z > ucl) | (z < lcl)
        ooc_indices = valid_data.index[ooc_mask].tolist()
        return {
            "chart_type": "EWMA",
            "data": {
                "values": z.tolist(),
                "indices": valid_data.index.tolist(),
                "raw_values": valid_data.tolist(),
                "out_of_control_indices": ooc_indices,
            },
            "statistics": {
                "cl": mu0,
                "ucl": float(ucl),
                "lcl": float(lcl),
                "lambda": lam,
                "sigma_ewma": float(sigma_ewma),
                "n": n,
            },
            "metadata": {
                "is_valid": True,
                "target_col": target_col,
                "error": "",
            },
        }
