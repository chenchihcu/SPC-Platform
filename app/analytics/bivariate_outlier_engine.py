"""
Bivariate outlier detection based on Mahalanobis distance.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List


class BivariateOutlierEngine:
    """Identifies bivariate outliers using squared Mahalanobis distance."""

    @staticmethod
    def compute_bivariate_outlier(
        filtered_df: pd.DataFrame,
        col_x: str,
        col_y: str,
        alpha: float = 0.9973,
    ) -> Dict[str, Any]:
        """
        Returns scatter data and a mask/list of outlier indices.
        Outlier = d2 > chi-square threshold(df=2, alpha).
        """
        if filtered_df is None or filtered_df.empty:
            return {
                "chart_type": "BivariateOutlier",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": "無資料 (No data)."},
            }
        if col_x not in filtered_df.columns or col_y not in filtered_df.columns:
            return {
                "chart_type": "BivariateOutlier",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": f"缺少欄位 {col_x} 或 {col_y}."},
            }
        valid = filtered_df[[col_x, col_y]].dropna()
        if len(valid) < 3:
            return {
                "chart_type": "BivariateOutlier",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": "有效點數不足 (N<3)."},
            }
        points = valid[[col_x, col_y]].to_numpy(dtype=float)
        mean_vec = np.mean(points, axis=0)
        cov = np.cov(points, rowvar=False)
        if np.linalg.matrix_rank(cov) < 2:
            cov = cov + np.eye(2) * 1e-9
        try:
            cov_inv = np.linalg.inv(cov)
        except np.linalg.LinAlgError:
            cov_inv = np.linalg.pinv(cov)
        centered = points - mean_vec
        d2 = np.einsum("ij,jk,ik->i", centered, cov_inv, centered)
        try:
            from scipy.stats import chi2  # type: ignore[import-untyped]
            threshold = float(chi2.ppf(alpha, df=2))
        except ImportError:
            # chi2.ppf(0.9973, 2) ≈ 11.83
            threshold = 11.83
        outlier_mask = d2 > threshold
        x_vals = points[:, 0].tolist()
        y_vals = points[:, 1].tolist()
        outlier_indices: List[int] = [i for i, b in enumerate(outlier_mask.tolist()) if b]
        return {
            "chart_type": "BivariateOutlier",
            "data": {
                "x": x_vals,
                "y": y_vals,
                "is_outlier": outlier_mask.tolist(),
                "outlier_indices": outlier_indices,
                "n_outliers": int(outlier_mask.sum()),
                "distance2": d2.tolist(),
            },
            "statistics": {
                "n": len(x_vals),
                "n_outliers": int(outlier_mask.sum()),
                "threshold_d2": float(threshold),
                "alpha": float(alpha),
                "mean_x": float(mean_vec[0]),
                "mean_y": float(mean_vec[1]),
            },
            "metadata": {
                "is_valid": True,
                "error": "",
                "col_x": col_x,
                "col_y": col_y,
                "method": "mahalanobis_chi2",
            },
            "analysis_context": {"col_x": col_x, "col_y": col_y},
        }
