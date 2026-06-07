"""Correlation matrix engine for multi-feature association analysis."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from app.analytics.pearson_utils import pearson_r_safe


class CorrelationMatrixEngine:
    """Compute Pearson correlation matrix and ranked pairs."""

    @staticmethod
    def compute_matrix(
        df: pd.DataFrame,
        feature_cols: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if df is None or df.empty:
            return {
                "chart_type": "CorrelationMatrix",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": "無資料。"},
            }

        cols = feature_cols or ["Volume", "Area", "Height"]
        cols = [c for c in cols if c in df.columns]
        if len(cols) < 2:
            return {
                "chart_type": "CorrelationMatrix",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": "可用特徵不足（至少需 2 欄）。"},
            }

        work = df[cols].replace([np.inf, -np.inf], np.nan).dropna()
        if len(work) < 3:
            return {
                "chart_type": "CorrelationMatrix",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": "有效樣本不足（至少需 3 筆）。"},
            }

        n_c = len(cols)
        corr_arr = np.eye(n_c, dtype=float)
        for i in range(n_c):
            for j in range(i + 1, n_c):
                r = pearson_r_safe(work[cols[i]], work[cols[j]])
                corr_arr[i, j] = r
                corr_arr[j, i] = r
        if not np.all(np.isfinite(corr_arr)):
            return {
                "chart_type": "CorrelationMatrix",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": "輸入資料變異不足，統計量為 NaN。"},
            }
        corr_df = pd.DataFrame(corr_arr, index=cols, columns=cols)
        pair_rows: list[dict[str, Any]] = []
        for i, col_i in enumerate(cols):
            for j, col_j in enumerate(cols):
                if j <= i:
                    continue
                corr_raw: Any = corr_df.loc[col_i, col_j]
                corr_val = float(corr_raw)
                pair_rows.append(
                    {
                        "pair": f"{col_i} vs {col_j}",
                        "left": col_i,
                        "right": col_j,
                        "corr": corr_val,
                        "abs_corr": abs(corr_val),
                    }
                )
        pair_rows.sort(key=lambda r: r["abs_corr"], reverse=True)

        return {
            "chart_type": "CorrelationMatrix",
            "data": {
                "labels": cols,
                "matrix": corr_df.values.tolist(),
                "pairs_ranked": pair_rows,
            },
            "statistics": {
                "n": int(len(work)),
                "pair_count": len(pair_rows),
                "strong_pair_count": int(sum(1 for r in pair_rows if r["abs_corr"] >= 0.7)),
            },
            "metadata": {"is_valid": True, "error": ""},
        }
