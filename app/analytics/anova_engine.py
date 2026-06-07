"""One-way ANOVA engine (default factor: PartType)."""

from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd
from scipy import stats  # type: ignore[import-untyped]


class AnovaEngine:
    """Compute one-way ANOVA statistics for a measurement column."""

    @staticmethod
    def compute_one_way(
        df: pd.DataFrame,
        value_col: str,
        *,
        group_col: str = "PartType",
    ) -> Dict[str, Any]:
        if df is None or df.empty or value_col not in df.columns:
            return {
                "chart_type": "ANOVA",
                "data": {},
                "statistics": {},
                "metadata": {
                    "is_valid": False,
                    "value_col": value_col,
                    "group_col": group_col,
                    "error": "無資料或缺少量測欄位。",
                },
            }
        if group_col not in df.columns:
            return {
                "chart_type": "ANOVA",
                "data": {},
                "statistics": {},
                "metadata": {
                    "is_valid": False,
                    "value_col": value_col,
                    "group_col": group_col,
                    "error": f"缺少分組欄位：{group_col}",
                },
            }

        work = df[[group_col, value_col]].replace([np.inf, -np.inf], np.nan).dropna()
        if work.empty:
            return {
                "chart_type": "ANOVA",
                "data": {},
                "statistics": {},
                "metadata": {
                    "is_valid": False,
                    "value_col": value_col,
                    "group_col": group_col,
                    "error": "無有效資料。",
                },
            }

        grouped = work.groupby(group_col)[value_col]
        labels: list[str] = []
        group_values: list[np.ndarray] = []
        n_by_group: list[int] = []
        mean_by_group: list[float] = []
        for name, series in grouped:
            vals = series.to_numpy(dtype=float)
            if len(vals) < 2:
                continue
            labels.append(str(name))
            group_values.append(vals)
            n_by_group.append(int(len(vals)))
            mean_by_group.append(float(np.mean(vals)))

        if len(group_values) < 2:
            return {
                "chart_type": "ANOVA",
                "data": {},
                "statistics": {},
                "metadata": {
                    "is_valid": False,
                    "value_col": value_col,
                    "group_col": group_col,
                    "error": "有效分組不足（至少需 2 組且每組 >= 2 筆）。",
                },
            }

        f_stat, p_value = stats.f_oneway(*group_values)
        if not (np.isfinite(f_stat) and np.isfinite(p_value)):
            return {
                "chart_type": "ANOVA",
                "data": {},
                "statistics": {},
                "metadata": {
                    "is_valid": False,
                    "value_col": value_col,
                    "group_col": group_col,
                    "error": "輸入資料變異不足，統計量為 NaN。",
                },
            }
        return {
            "chart_type": "ANOVA",
            "data": {
                "group_labels": labels,
                "n_by_group": n_by_group,
                "mean_by_group": mean_by_group,
            },
            "statistics": {
                "f_stat": float(f_stat),
                "p_value": float(p_value),
                "group_count": len(group_values),
                "total_n": int(sum(n_by_group)),
                "is_significant": bool(p_value < 0.05),
                "alpha": 0.05,
            },
            "metadata": {
                "is_valid": True,
                "value_col": value_col,
                "group_col": group_col,
                "error": "",
            },
        }
