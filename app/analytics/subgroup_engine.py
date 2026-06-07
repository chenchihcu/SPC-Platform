"""
Subgroup comparison engine: per-group (PartType/RefDes) stats and violation rate.
Phase 4 P1: compare subgroups by mean and optionally out-of-spec rate.
"""
import pandas as pd
from typing import Dict, Any, Optional


class SubgroupEngine:
    """Subgroup comparison: mean and violation rate by PartType or RefDes."""

    @staticmethod
    def compute_subgroup(
        df: pd.DataFrame,
        target_col: str,
        group_col: str = "PartType",
        usl: Optional[float] = None,
        lsl: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Compute per-subgroup mean, count, and optional violation rate.
        If group_col not in df, tries RefDes.
        """
        if df is None or df.empty or target_col not in df.columns:
            return {
                "chart_type": "Subgroup",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "target_col": target_col, "error": "無資料或缺少欄位。"},
            }
        group_col = group_col if group_col in df.columns else "RefDes"
        if group_col not in df.columns:
            return {
                "chart_type": "Subgroup",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "target_col": target_col, "error": "缺少分組欄位 (PartType/RefDes)。"},
            }
        valid = df[[group_col, target_col]].dropna()
        if valid.empty:
            return {
                "chart_type": "Subgroup",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "target_col": target_col, "error": "無有效分組資料。"},
            }
        grp = valid.groupby(group_col)[target_col]
        labels = []
        means = []
        counts = []
        violation_rates = []
        for name, series in grp:
            labels.append(str(name))
            means.append(float(series.mean()))
            sample_n = int(len(series))
            counts.append(sample_n)
            if usl is not None or lsl is not None:
                violation_mask = pd.Series(False, index=series.index)
                if usl is not None:
                    violation_mask = violation_mask | (series > usl)
                if lsl is not None:
                    violation_mask = violation_mask | (series < lsl)
                violation_rates.append(100.0 * violation_mask.sum() / sample_n if sample_n else 0.0)
            else:
                violation_rates.append(0.0)
        return {
            "chart_type": "Subgroup",
            "data": {
                "labels": labels,
                "means": means,
                "counts": counts,
                "violation_rates": violation_rates,
            },
            "statistics": {"group_col": group_col, "n_groups": len(labels)},
            "metadata": {
                "is_valid": True,
                "target_col": target_col,
                "error": "",
            },
        }
