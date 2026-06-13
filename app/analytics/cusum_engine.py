"""
CUSUM (Cumulative Sum) chart engine.
Phase 3 P1: small shift and variance change detection.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

from app.analytics.statistical_utils import StatisticalUtils


class CUSUMEngine:
    """CUSUM C+ and C- with reference k and decision interval h (in sigma units)."""

    DEFAULT_K = 0.5  # slack (typically 0.5 for 1-sigma shift)
    DEFAULT_H = 5.0  # decision interval (e.g. 5 sigma)

    @staticmethod
    def compute_cusum(
        data: pd.Series,
        target_col: str = "Measurement",
        k: Optional[float] = None,
        h: Optional[float] = None,
        board_ids: Optional[pd.Series] = None,
        target: Optional[float] = None,
        usl: Optional[float] = None,
        lsl: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Compute CUSUM C+ and C- statistics.
        C+_i = max(0, (x_i - (mu0 + k*sigma)) + C+_{i-1})
        C-_i = max(0, ((mu0 - k*sigma) - x_i) + C-_{i-1})

        target: explicit process target (e.g. stencil thickness for Height).
                Priority: target > (usl+lsl)/2 > data mean.
        board_ids: optional Series; resets C+/C- at board boundaries.
        Returns structure compatible with BaseChart.
        """
        k = k if k is not None else CUSUMEngine.DEFAULT_K
        h = h if h is not None else CUSUMEngine.DEFAULT_H
        is_valid, msg = StatisticalUtils.is_valid_for_spc(data)
        if not is_valid:
            return {
                "chart_type": "CUSUM",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "target_col": target_col, "error": msg},
            }
        if usl is None or lsl is None:
            return {
                "chart_type": "CUSUM",
                "data": {},
                "statistics": {},
                "metadata": {
                    "is_valid": False,
                    "target_col": target_col,
                    "error": "Missing USL or LSL.",
                },
            }
        if usl == lsl:
            return {
                "chart_type": "CUSUM",
                "data": {},
                "statistics": {},
                "metadata": {
                    "is_valid": False,
                    "target_col": target_col,
                    "error": "USL 與 LSL 相同。",
                },
            }
        valid_data = data.replace([np.inf, -np.inf], np.nan).dropna()
        n = len(valid_data)

        # μ₀ priority: explicit target → spec midpoint → data mean
        data_mean = float(valid_data.mean())
        data_sigma = float(valid_data.std(ddof=1))
        if target is not None:
            mu0 = float(target)
            mu0_source = "spec_target"
        elif usl is not None and lsl is not None:
            mu0 = (float(usl) + float(lsl)) / 2.0
            mu0_source = "spec_midpoint"
        else:
            mu0 = data_mean
            mu0_source = "data_mean"

        sigma = data_sigma

        # Safety check: if target is wildly different from data mean
        # (likely a unit mismatch, e.g. mm spec vs percentage data),
        # fall back to data mean to avoid meaningless CUSUM output.
        fallback_applied = False
        fallback_reason = ""
        fallback_deviation_sigma = None
        if sigma > 0 and mu0_source != "data_mean":
            deviation = abs(mu0 - data_mean) / sigma
            if deviation > 10:
                fallback_applied = True
                fallback_deviation_sigma = float(deviation)
                fallback_reason = (
                    "target_or_spec_midpoint_far_from_data_mean"
                )
                mu0 = data_mean
                mu0_source = "data_mean"
        if sigma <= 0:
            return {
                "chart_type": "CUSUM",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "target_col": target_col, "error": "Standard deviation is 0."},
            }
        vals = valid_data.values
        cp = np.zeros(n)
        cm = np.zeros(n)
        upper_ref = mu0 + k * sigma
        lower_ref = mu0 - k * sigma

        # Align board_ids to valid_data index for boundary detection
        board_vals = None
        if board_ids is not None:
            try:
                board_vals = board_ids.reindex(valid_data.index).values
            except (AttributeError, TypeError, ValueError):
                board_vals = None

        for i in range(n):
            # Reset at board boundary: when board ID changes, start fresh
            is_boundary = (
                i > 0
                and board_vals is not None
                and board_vals[i] != board_vals[i - 1]
            )
            prev_cp = 0.0 if (i == 0 or is_boundary) else cp[i - 1]
            prev_cm = 0.0 if (i == 0 or is_boundary) else cm[i - 1]
            cp[i] = max(0.0, (vals[i] - upper_ref) + prev_cp)
            cm[i] = max(0.0, (lower_ref - vals[i]) + prev_cm)

        h_sigma = h * sigma
        ooc_cp = valid_data.index[(cp > h_sigma)].tolist()
        ooc_cm = valid_data.index[(cm > h_sigma)].tolist()
        out_of_control_indices = list(set(ooc_cp + ooc_cm))

        # ── Board-level summary (for 全批 multi-board view) ──────────
        board_summary = {}
        if board_vals is not None:
            board_labels = []
            board_max_cp = []
            board_max_cm = []
            board_ooc_flags = []
            current_board = board_vals[0]
            seg_start = 0
            for i in range(1, n + 1):
                if i == n or board_vals[i] != current_board:
                    seg_cp = cp[seg_start:i]
                    seg_cm = cm[seg_start:i]
                    peak_cp = float(np.max(seg_cp))
                    peak_cm = float(np.max(seg_cm))
                    board_labels.append(str(current_board))
                    board_max_cp.append(peak_cp)
                    board_max_cm.append(peak_cm)
                    board_ooc_flags.append(peak_cp > h_sigma or peak_cm > h_sigma)
                    if i < n:
                        current_board = board_vals[i]
                        seg_start = i
            board_summary = {
                "board_labels": board_labels,
                "max_cp": board_max_cp,
                "max_cm": board_max_cm,
                "ooc_flags": board_ooc_flags,
            }

        return {
            "chart_type": "CUSUM",
            "data": {
                "values": cp.tolist(),      # C+
                "values_cm": cm.tolist(),   # C-
                "indices": valid_data.index.tolist(),
                "out_of_control_indices": out_of_control_indices,
                "board_summary": board_summary,
            },
            "statistics": {
                "mu0": mu0,
                "mu0_source": mu0_source,
                "sigma": sigma,
                "k": k,
                "h": h,
                "h_sigma": float(h_sigma),
                "n": n,
                "ooc_count": len(out_of_control_indices),
                "mu0_fallback_applied": fallback_applied,
                "mu0_fallback_reason": fallback_reason,
                "mu0_fallback_deviation_sigma": fallback_deviation_sigma,
            },
            "metadata": {
                "is_valid": True,
                "target_col": target_col,
                "error": "",
            },
        }
