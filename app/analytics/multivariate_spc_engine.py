import numpy as np
import pandas as pd
from scipy import stats  # type: ignore[import-untyped]
from app.analytics.statistical_utils import invalid_chart_payload


class MultivariateSPCEngine:
    """Hotelling T² multivariate SPC engine for exactly 3 features."""

    @staticmethod
    def compute_hotelling_t2(df: pd.DataFrame, feature_cols: list[str]) -> dict:
        """Compute Hotelling T² statistics for multivariate control charting."""
        if df is None or df.empty or not feature_cols or any(c not in df.columns for c in feature_cols):
            return invalid_chart_payload(
                "hotelling_t2",
                "無資料或缺少特徵欄位。",
                "Measurement",
                payload_key="hotelling_t2",
                data={"indices": [], "t2_values": [], "ooc_flags": []},
                statistics={"ucl_value": 0.0, "mean_t2": 0.0, "max_t2": 0.0, "ooc_count": 0, "ooc_pct": 0.0},
                n_samples=0,
                p_features=len(feature_cols or []),
                cov_matrix=[],
                mu0_vector=[],
            )
        X = df[feature_cols].to_numpy()
        mask = np.all(np.isfinite(X), axis=1)
        X = X[mask]
        n, p = X.shape

        if n <= p:
            return invalid_chart_payload(
                "hotelling_t2",
                "樣本數不足，需至少 4 筆資料 (p+1)",
                "Measurement",
                payload_key="hotelling_t2",
                data={"indices": [], "t2_values": [], "ooc_flags": []},
                statistics={"ucl_value": 0.0, "mean_t2": 0.0, "max_t2": 0.0, "ooc_count": 0, "ooc_pct": 0.0},
                n_samples=n,
                p_features=p,
                cov_matrix=[],
                mu0_vector=[],
            )

        mu0 = np.mean(X, axis=0)
        S = np.cov(X, rowvar=False)

        if np.linalg.cond(S) > 1e12:
            return invalid_chart_payload(
                "hotelling_t2",
                "共變異矩陣接近奇異，無法計算 T²",
                "Measurement",
                payload_key="hotelling_t2",
                data={"indices": [], "t2_values": [], "ooc_flags": []},
                statistics={"ucl_value": 0.0, "mean_t2": 0.0, "max_t2": 0.0, "ooc_count": 0, "ooc_pct": 0.0},
                n_samples=n,
                p_features=p,
                cov_matrix=[],
                mu0_vector=[],
            )

        S_inv = np.linalg.inv(S)
        diff = X - mu0
        t2_values = np.sum(diff @ S_inv * diff, axis=1)
        ucl = p * (n - 1) * (n + 1) / (n * (n - p)) * stats.f.ppf(0.95, p, n - p)
        ooc_flags = [float(t2) > float(ucl) for t2 in t2_values]

        return {
            "chart_type": "hotelling_t2",
            "payload_key": "hotelling_t2",
            "data": {
                "indices": list(range(n)),
                "t2_values": [float(v) for v in t2_values],
                "ooc_flags": [bool(f) for f in ooc_flags],
            },
            "statistics": {
                "ucl_value": float(ucl),
                "mean_t2": float(np.mean(t2_values)),
                "max_t2": float(np.max(t2_values)),
                "ooc_count": int(sum(ooc_flags)),
                "ooc_pct": float(sum(ooc_flags) / n * 100),
            },
            "metadata": {
                "is_valid": True,
                "n_samples": n,
                "p_features": p,
                "cov_matrix": [float(v) for v in S.flatten()],
                "mu0_vector": [float(v) for v in mu0],
                "error": None,
            },
        }
