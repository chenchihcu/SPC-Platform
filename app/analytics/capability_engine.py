import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from app.analytics.statistical_utils import StatisticalUtils, invalid_chart_payload

# ── SPC formula constants (AIAG SPC 2nd ed. / ISO 7870-2) ────────────────────
_D2_N2 = 1.128   # Bias-correction factor for moving range (subgroup n=2)
_CP_SIGMA_SPAN = 6  # Cp denominator: total process spread = ±3σ = 6σ
_ONE_SIDED_SIGMA = 3  # Cpu/Cpl numerator multiplier (one-sided 3σ)

# A real SPC process never approaches |Cpk| this large. When |Cpk| blows past
# it, the mean sits >150σ outside the spec — physically impossible for a genuine
# (even catastrophic) process. It signals the measurement values and the spec
# limits are on different scales/units (e.g. mm data vs a percent spec), so the
# indices are not directly-computed fact and must be flagged, not trusted.
_SCALE_MISMATCH_ABS_CPK = 50.0


class CapabilityEngine:
    """
    Computes Process Capability indices evaluating variation against Specification Limits.
    """
    
    @staticmethod
    def _short_term_sigma(
        valid_data: pd.Series, subgroup_ids: Optional[pd.Series]
    ) -> float:
        """Short-term sigma = MR̄ / d2 (AIAG within-subgroup variation).

        When ``subgroup_ids`` (board/panel) is supplied, moving ranges are taken
        WITHIN each subgroup and pooled — a moving range that straddles a board
        boundary would inject between-board variation into the within-board
        estimate. Falls back to the whole-series moving range when no usable
        subgroup structure is present (preserves legacy single-series behavior).
        """
        # Single source shared with SPCEngine.compute_imr (SPC_RULES §4).
        mr_bar, _basis, _excluded = StatisticalUtils.within_subgroup_mr_bar(
            valid_data, subgroup_ids
        )
        return float(mr_bar / _D2_N2)

    @staticmethod
    def compute_capability(
        data: pd.Series,
        usl: Optional[float],
        lsl: Optional[float],
        subgroup_ids: Optional[pd.Series] = None,
    ) -> Dict[str, Any]:
        """
        Computes Cp, Cpk (Short Term) and Pp, Ppk (Long Term).
        Complies with minimum sample requirements from docs/governance/SPC_RULES.md.

        subgroup_ids: optional board/panel id series (aligned by index). When
            given, short-term sigma uses within-subgroup moving ranges so board
            boundaries do not contaminate the within-board estimate.
        """
        is_valid, msg = StatisticalUtils.is_valid_for_spc(data)
        if not is_valid:
             return invalid_chart_payload("Capability", msg)

        if usl is None or lsl is None:
             return invalid_chart_payload("Capability", "Missing USL or LSL specifications. Capability cannot be computed.")

        if usl == lsl:
            return invalid_chart_payload("Capability", "USL 與 LSL 相同，製程能力無法定義。")

        valid_data = data.replace([np.inf, -np.inf], np.nan).dropna()
        mean_val = valid_data.mean()

        # Sigma ST from within-subgroup MR / d2 (AIAG: short-term variation)
        sigma_st = CapabilityEngine._short_term_sigma(valid_data, subgroup_ids)

        # Sigma LT (total sample std dev — long-term, overall variation)
        sigma_lt = np.std(valid_data, ddof=1)

        # Degenerate input: zero variation makes Cp/Cpk undefined (division by
        # zero); returning 0.0 here would misreport a perfect process as
        # "High risk", so fail closed per the engine contract (SPC_RULES.md).
        if sigma_st <= 0 or sigma_lt <= 0:
            return invalid_chart_payload("Capability", "製程變異為零（所有量測值相同），Cp/Cpk 無法定義。")

        cp = (usl - lsl) / (_CP_SIGMA_SPAN * sigma_st)
        cpk = min(
            (usl - mean_val) / (_ONE_SIDED_SIGMA * sigma_st),
            (mean_val - lsl) / (_ONE_SIDED_SIGMA * sigma_st),
        )

        pp = (usl - lsl) / (_CP_SIGMA_SPAN * sigma_lt)
        ppk = min(
            (usl - mean_val) / (_ONE_SIDED_SIGMA * sigma_lt),
            (mean_val - lsl) / (_ONE_SIDED_SIGMA * sigma_lt),
        )

        # Interpretation defined by docs/governance/SPC_RULES.md (Cpk < 1.0 unacceptable)
        defect_risk_level = "High risk" if cpk < 1.0 else "Acceptable" if cpk >= 1.33 else "Medium risk"

        # Unit/scale-mismatch sentinel: an impossibly large |Cpk| means the data
        # and the spec are on different scales (mm data vs % spec, etc.). The
        # numbers are still returned (is_valid stays True so charts render), but
        # flagged so trust labels and diagnosis narrative do not present them as
        # directly-computed capability fact.
        scale_mismatch = abs(cpk) > _SCALE_MISMATCH_ABS_CPK
        scale_reason = (
            f"能力指標尺度異常（|Cpk|={abs(cpk):.0f} 遠超真實製程範圍）：量測值與規格"
            f"疑似單位/尺度不符（如 mm 資料對百分比規格）。數值僅供參考，"
            f"請先確認量測單位與規格單位一致（Height 可設鋼板厚度絕對模式）。"
            if scale_mismatch else ""
        )

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
                "scale_mismatch": bool(scale_mismatch),
                "scale_mismatch_reason": scale_reason,
                "error": ""
            }
        }
