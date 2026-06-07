"""
Repeated offender engine: rank RefDes by out-of-spec count (violation count).
Phase 4 P1: single batch or filtered data, per-RefDes violation count.
"""
import pandas as pd
from typing import Dict, Any, Optional


class RepeatedOffenderEngine:
    """Rank RefDes by number of violations (out of USL/LSL)."""

    @staticmethod
    def compute_repeated_offender(
        df: pd.DataFrame,
        target_col: str,
        usl: Optional[float] = None,
        lsl: Optional[float] = None,
        refdes_col: str = "RefDes",
        top_n: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        For each RefDes, count violations; return ranking by count (descending).
        When top_n is provided, returns only top_n entries with explicit metadata.
        """
        if df is None or df.empty or target_col not in df.columns:
            return {
                "chart_type": "RepeatedOffender",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "target_col": target_col, "error": "無資料或缺少欄位。"},
            }
        if refdes_col not in df.columns:
            return {
                "chart_type": "RepeatedOffender",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "target_col": target_col, "error": "缺少 RefDes 欄位。"},
            }
        if usl is None and lsl is None:
            return {
                "chart_type": "RepeatedOffender",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "target_col": target_col, "error": "請設定規格上下限 (USL/LSL) 以計算違規。"},
            }
        valid = df[[refdes_col, target_col]].dropna()
        if valid.empty:
            return {
                "chart_type": "RepeatedOffender",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "target_col": target_col, "error": "無有效資料。"},
            }
        violations = pd.Series(False, index=valid.index)
        if usl is not None:
            violations = violations | (valid[target_col] > usl)
        if lsl is not None:
            violations = violations | (valid[target_col] < lsl)
        valid = valid.assign(_violation=violations)
        counts = valid.groupby(refdes_col)["_violation"].sum().astype(int)
        counts = counts[counts > 0].sort_values(ascending=False)
        if counts.empty:
            labels = []
            values = []
        else:
            if top_n is not None and top_n > 0:
                shown = counts.head(top_n)
            else:
                shown = counts
            labels = shown.index.tolist()
            values = shown.values.tolist()
        sampled_for_display = len(labels) < len(counts)
        return {
            "chart_type": "RepeatedOffender",
            "data": {"labels": [str(x) for x in labels], "counts": values},
            "statistics": {
                "usl": usl,
                "lsl": lsl,
                "n_refdes_with_violations": len(counts),
                "displayed_n": len(labels),
                "sampled_for_display": sampled_for_display,
                "top_n": top_n,
            },
            "metadata": {
                "is_valid": True,
                "target_col": target_col,
                "error": "",
                "sampled_for_display": sampled_for_display,
            },
        }
