import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from app.analytics.statistical_utils import StatisticalUtils

# ── SPC formula constants (AIAG SPC 2nd ed. / ISO 7870-2) ────────────────────
_D2_N2 = 1.128   # Bias-correction factor for moving range (subgroup n=2)
_CP_SIGMA_SPAN = 6  # Cp denominator: total process spread = ±3σ = 6σ
_ONE_SIDED_SIGMA = 3  # Cpu/Cpl numerator multiplier (one-sided 3σ)


class CapabilityEngine:
    """
    Computes Process Capability indices evaluating variation against Specification Limits.
    """
    
    @staticmethod
    def compute_capability(data: pd.Series, usl: Optional[float], lsl: Optional[float]) -> Dict[str, Any]:
        """
        Computes Cp, Cpk (Short Term) and Pp, Ppk (Long Term).
        Complies with minimum sample requirements from docs/governance/SPC_RULES.md.
        """
        is_valid, msg = StatisticalUtils.is_valid_for_spc(data)
        if not is_valid:
             return {
                "chart_type": "Capability",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": msg}
            }
            
        if usl is None or lsl is None:
             return {
                "chart_type": "Capability",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": "Missing USL or LSL specifications. Capability cannot be computed."}
            }

        if usl == lsl:
            return {
                "chart_type": "Capability",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": "USL 與 LSL 相同，製程能力無法定義。"}
            }

        valid_data = data.replace([np.inf, -np.inf], np.nan).dropna()
        mean_val = valid_data.mean()
        
        # Sigma ST from MR / d2 (AIAG: short-term, within-subgroup variation)
        mr_series = StatisticalUtils.calculate_moving_range(valid_data)
        sigma_st = mr_series.mean() / _D2_N2

        # Sigma LT (total sample std dev — long-term, overall variation)
        sigma_lt = np.std(valid_data, ddof=1)

        # Safely compute capability to avoid division by zero
        cp, cpk, pp, ppk = 0.0, 0.0, 0.0, 0.0

        if sigma_st > 0:
            cp  = (usl - lsl) / (_CP_SIGMA_SPAN * sigma_st)
            cpk = min(
                (usl - mean_val) / (_ONE_SIDED_SIGMA * sigma_st),
                (mean_val - lsl) / (_ONE_SIDED_SIGMA * sigma_st),
            )

        if sigma_lt > 0:
            pp  = (usl - lsl) / (_CP_SIGMA_SPAN * sigma_lt)
            ppk = min(
                (usl - mean_val) / (_ONE_SIDED_SIGMA * sigma_lt),
                (mean_val - lsl) / (_ONE_SIDED_SIGMA * sigma_lt),
            )

        # Interpretation defined by docs/governance/SPC_RULES.md (Cpk < 1.0 unacceptable)
        defect_risk_level = "High risk" if cpk < 1.0 else "Acceptable" if cpk >= 1.33 else "Medium risk"
            
        return {
            "chart_type": "Capability",
            "data": {},  # Geometry handled by distribution engine
            "statistics": {
                "mean": float(mean_val),
                "sigma_st": float(sigma_st),
                "sigma_lt": float(sigma_lt),
                "cp": float(cp),
                "cpk": float(cpk),
                "pp": float(pp),
                "ppk": float(ppk)
            },
            "metadata": {
                "is_valid": True,
                "usl": usl,
                "lsl": lsl,
                "risk_level": defect_risk_level,
                "error": ""
            }
        }
