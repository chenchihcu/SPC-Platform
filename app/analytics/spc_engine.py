import numpy as np
import pandas as pd
from typing import Dict, Any

class SPCEngine:
    """
    Statistical Process Control (SPC) engine.
    Calculates Control Limits (CL, UCL, LCL) based on SPI Rules.
    """
    I_MR_D2 = 1.128  # Defined in docs/governance/SPC_RULES.md for MR chart

    @staticmethod
    def compute_imr(data: pd.Series, target_col: str = "Measurement") -> Dict[str, Any]:
        """
        Computes I-MR (Individual-Moving Range) chart statistics.
        Identifies western electric Rule 1 (Out of control limits).
        """
        if data is None or data.empty:
            return {
                "chart_type": "I-MR",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "target_col": target_col, "error": "No data available."}
            }

        # Sanitize once and reuse the same clean slice for validation + metrics.
        valid_data = data.replace([np.inf, -np.inf], np.nan).dropna()
        n = len(valid_data)
        if n < 10:
            return {
                "chart_type": "I-MR",
                "data": {},
                "statistics": {},
                "metadata": {
                    "is_valid": False,
                    "target_col": target_col,
                    "error": f"Sample size too small (N={n}). Minimum required for SPC is 10.",
                },
            }

        values = valid_data.to_numpy(dtype=float, copy=False)
        if float(values.std(ddof=1)) == 0.0:
            return {
                "chart_type": "I-MR",
                "data": {},
                "statistics": {},
                "metadata": {
                    "is_valid": False,
                    "target_col": target_col,
                    "error": "Standard deviation is 0 (all values identical). Process variation cannot be measured.",
                },
            }

        cl = float(values.mean())
        mr_values = np.abs(np.diff(values))
        mr_bar = float(mr_values.mean())

        # Sigma estimation based on MR
        sigma_est = mr_bar / SPCEngine.I_MR_D2
        ucl = cl + 3 * sigma_est
        lcl = cl - 3 * sigma_est

        # Out-of-control point detection (Rule 1: Point > UCL or < LCL)
        ooc_mask = (values > ucl) | (values < lcl)
        valid_index = valid_data.index
        ooc_indices = valid_index[ooc_mask].tolist()

        return {
            "chart_type": "I-MR",
            "data": {
                "values": values.tolist(),
                "indices": valid_index.tolist(),
                "mr_values": mr_values.tolist(),
                "mr_indices": valid_index[1:].tolist(),
                "out_of_control_indices": ooc_indices
            },
            "statistics": {
                "cl": cl,
                "ucl": float(ucl),
                "lcl": float(lcl),
                "sigma": float(sigma_est),
                "mr_bar": float(mr_bar),
                "n": n
            },
            "metadata": {
                "is_valid": True,
                "target_col": target_col,
                "error": ""
            }
        }
