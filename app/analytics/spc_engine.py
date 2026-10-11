import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

from app.analytics.statistical_utils import StatisticalUtils, invalid_chart_payload

class SPCEngine:
    """
    Statistical Process Control (SPC) engine.
    Calculates Control Limits (CL, UCL, LCL) based on SPI Rules.
    """
    I_MR_D2 = 1.128  # Defined in docs/governance/SPC_RULES.md for MR chart

    @staticmethod
    def compute_imr(
        data: pd.Series,
        target_col: str = "Measurement",
        subgroup_ids: Optional[pd.Series] = None,
    ) -> Dict[str, Any]:
        """
        Computes I-MR (Individual-Moving Range) chart statistics.
        Identifies western electric Rule 1 (Out of control limits).

        subgroup_ids: optional board/panel id series (aligned by index). When
            given, sigma = pooled within-subgroup MR̄ / d2 — the same sigma_within
            Cp/Cpk use (SPC_RULES §4). Boundary MRs stay in ``mr_values`` for
            plotting but are excluded from MR̄.
        """
        is_valid, msg = StatisticalUtils.is_valid_for_spc(data)
        if not is_valid:
            return invalid_chart_payload("I-MR", msg, target_col)

        valid_data = data.replace([np.inf, -np.inf], np.nan).dropna()
        n = len(valid_data)
        values = valid_data.to_numpy(dtype=float, copy=False)

        cl = float(values.mean())
        mr_values = np.abs(np.diff(values))
        if subgroup_ids is None:
            mr_bar = float(mr_values.mean())
            sigma_basis, mr_boundary_excluded = "whole_series", 0
        else:
            mr_bar, sigma_basis, mr_boundary_excluded = (
                StatisticalUtils.within_subgroup_mr_bar(valid_data, subgroup_ids)
            )
        # Degenerate input: constant within every subgroup (only between-board
        # steps) gives MR̄_within = 0 → zero-width limits; fail closed like
        # CapabilityEngine does for sigma_st <= 0 (SPC_RULES §4).
        if not mr_bar > 0:
            return invalid_chart_payload(
                "I-MR", "板內移動全距為零（各板內量測值皆相同），I-MR 管制界限無法定義。", target_col
            )

        # Sigma estimation based on (within-subgroup) MR
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
                "mr_boundary_excluded": int(mr_boundary_excluded),
                "n": n
            },
            "metadata": {
                "is_valid": True,
                "target_col": target_col,
                "sigma_basis": sigma_basis,
                "error": ""
            }
        }
