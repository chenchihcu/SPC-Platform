"""
Pass/fail matrix engine: per-feature pass rate and optional cross-tab.
Phase 4 P1: triple-feature with USL/LSL per column.
"""
import pandas as pd
from typing import Dict, Any, List, Optional


def _get_spec_bounds(spec: Optional[Dict]) -> tuple:
    if not spec or not isinstance(spec, dict):
        return None, None
    try:
        usl = float(spec.get("usl", "")) if spec.get("usl") else None
        lsl = float(spec.get("lsl", "")) if spec.get("lsl") else None
        return usl, lsl
    except (TypeError, ValueError):
        return None, None


def _invalid_pass_fail(error: str) -> Dict[str, Any]:
    return {
        "chart_type": "PassFail",
        "data": {},
        "statistics": {},
        "metadata": {"is_valid": False, "error": error},
    }


class PassFailEngine:
    """Pass/fail rate per feature (Volume, Area, Height) when spec is given."""

    @staticmethod
    def compute_pass_fail(
        df: pd.DataFrame,
        cols: List[str],
        spec_by_col: Optional[Dict[str, Dict]] = None,
    ) -> Dict[str, Any]:
        """
        spec_by_col: e.g. {"Volume": {"usl": 120, "lsl": 80}, ...}.
        Returns pass_count, fail_count, pass_rate per column.
        """
        if df is None or df.empty:
            return _invalid_pass_fail("無資料。")
        missing = [c for c in cols if c not in df.columns]
        if missing:
            return _invalid_pass_fail(f"缺少欄位: {missing}.")
        spec_by_col = spec_by_col or {}
        valid = df[cols].dropna()
        if valid.empty:
            return _invalid_pass_fail("無有效資料。")
        n_total = len(valid)
        labels = []
        pass_counts = []
        fail_counts = []
        pass_rates = []
        per_feature_n = []
        for col in cols:
            spec = spec_by_col.get(col, {})
            usl, lsl = _get_spec_bounds(spec) if isinstance(spec, dict) else (None, None)
            labels.append(col)
            if usl is None and lsl is None:
                pass_counts.append(n_total)
                fail_counts.append(0)
                pass_rates.append(100.0)
                per_feature_n.append(n_total)
            else:
                s = valid[col]
                pass_mask = pd.Series(True, index=s.index)
                if usl is not None:
                    pass_mask = pass_mask & (s <= usl)
                if lsl is not None:
                    pass_mask = pass_mask & (s >= lsl)
                pc = int(pass_mask.sum())
                fc = n_total - pc
                pass_counts.append(pc)
                fail_counts.append(fc)
                pass_rates.append(100.0 * pc / n_total if n_total else 0.0)
                per_feature_n.append(n_total)
        return {
            "chart_type": "PassFail",
            "data": {
                "labels": labels,
                "pass_counts": pass_counts,
                "fail_counts": fail_counts,
                "pass_rates": pass_rates,
                "denominator_n": per_feature_n,
            },
            "statistics": {
                "n_total": n_total,
                "denominator_mode": "common_valid_rows_across_features",
                "denominator_note": "以三特徵共同有效樣本作為分母；各特徵 denominator_n 相同。",
            },
            "metadata": {"is_valid": True, "error": "", "sampled_for_display": False},
        }
