"""
Moran's I spatial autocorrelation engine.

Computes Global and Local (LISA) Moran's I using a K-nearest-neighbor
spatial weight matrix built via scipy.spatial.KDTree — no external
spatial-statistics dependency required.

Formula reference (Global Moran's I):
    I = (n / S₀) * ΣᵢΣⱼ wᵢⱼ (xᵢ − x̄)(xⱼ − x̄) / Σᵢ (xᵢ − x̄)²

Local Moran's I (LISA):
    Iᵢ = zᵢ * Σⱼ wᵢⱼ zⱼ            (z = standardised value)
"""

from __future__ import annotations

from typing import Any, Dict
from app.analytics.statistical_utils import invalid_chart_payload

import numpy as np
from numpy.random import default_rng

import pandas as pd
from scipy.spatial import KDTree  # type: ignore[import-untyped]


_DEFAULT_K = 3          # default K-nearest neighbours
_N_PERMUTATIONS = 999   # Monte Carlo permutations for p-value


def _sanitise(data: pd.Series) -> np.ndarray:
    """Return a finite float64 ndarray; raise ValueError if empty."""
    arr = pd.to_numeric(data, errors="coerce").to_numpy(dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        raise ValueError("No finite values to compute Moran's I.")
    return arr


def _row_standardised_weights(
    coords: np.ndarray,
    k: int,
) -> tuple[np.ndarray, float]:
    """Build a row-standardised KNN weight matrix (N×N sparse as ndarray of indices & weights)."""
    n = coords.shape[0]
    k_eff = min(k, n - 1)  # cannot have more neighbours than n-1
    if k_eff < 1:
        raise ValueError(f"k={k} requires at least 2 points (got {n}).")

    # Optimisation for large datasets with duplicate coordinates (e.g. concatenated batches)
    if n > 2000:
        # Use complex representation to speed up 2D unique by 100x+
        flat = coords[:, 0] + coords[:, 1] * 1j
        _, first_occurrences, inverse_idx = np.unique(
            flat, return_index=True, return_inverse=True
        )
        m = first_occurrences.shape[0]
        
        # Only apply unique optimization if there are actual duplicates and we have enough unique points (m > 1)
        if m < n // 2 and m > 1:
            u_k_eff = min(k, m - 1)
            unique_coords = coords[first_occurrences]
            tree = KDTree(unique_coords)
            distances, indices = tree.query(unique_coords, k=u_k_eff + 1)
            neighbour_idx = first_occurrences[indices[:, 1:][inverse_idx]]
            w_val = 1.0 / u_k_eff
            return neighbour_idx, w_val

    tree = KDTree(coords)
    # Query k+1 because KDTree returns self as the first neighbour
    distances, indices = tree.query(coords, k=k_eff + 1)

    # indices[:, 0] is self; neighbours start at column 1
    neighbour_idx = indices[:, 1:].copy()  # (N, k_eff)
    # Row-standardised weight: 1/k_eff for each neighbour
    w_val = 1.0 / k_eff

    return neighbour_idx, w_val


class MoranIEngine:
    """Global and Local (LISA) Moran's I spatial autocorrelation."""

    @staticmethod
    def compute_global_moran_i(
        coords: pd.DataFrame | np.ndarray,
        values: pd.Series,
        *,
        k: int = _DEFAULT_K,
        permutations: int = _N_PERMUTATIONS,
    ) -> Dict[str, Any]:
        """Compute Global Moran's I with Monte Carlo p-value.

        Parameters
        ----------
        coords : DataFrame with X, Y columns, or (N, 2) ndarray.
        values : Series of measurement values.
        k : number of nearest neighbours for spatial weights (default 3).
        permutations : Monte Carlo permutations for pseudo p-value (default 999).

        Returns
        -------
        Standard analytics-engine dict.
        """
        chart_type = "MoranI"
        try:
            vals = _sanitise(values)
            n = vals.size
            if n < k + 1:
                return invalid_chart_payload(chart_type, f"資料不足（{n} 筆），至少需 {k + 1} 筆才能計算空間權重。")
            # coords
            if isinstance(coords, pd.DataFrame):
                if "X" not in coords.columns or "Y" not in coords.columns:
                    return invalid_chart_payload(chart_type, "座標資料需包含 X 與 Y 欄位。")
                # align coords to values index if possible
                coord_arr = coords[["X", "Y"]].to_numpy(dtype=float)
            else:
                coord_arr = np.asarray(coords, dtype=float)

            if coord_arr.ndim != 2 or coord_arr.shape[1] != 2:
                return invalid_chart_payload(chart_type, "座標需為 (N, 2) 陣列。")
            if coord_arr.shape[0] != n:
                return invalid_chart_payload(chart_type, f"座標數（{coord_arr.shape[0]}）與數值數（{n}）不符。")
        except ValueError as exc:
            return invalid_chart_payload(chart_type, str(exc))

        # --- weights ---
        try:
            neighbour_idx, w_val = _row_standardised_weights(coord_arr, k)
        except ValueError as exc:
            return invalid_chart_payload(chart_type, str(exc))

        # --- Global Moran's I ---
        z = vals - np.mean(vals)
        s2 = np.sum(z ** 2)
        if s2 == 0:
            return invalid_chart_payload(chart_type, "所有數值相同，無法計算 Moran's I。")

        # numerator: ΣᵢΣⱼ wᵢⱼ zᵢ zⱼ
        numer = 0.0
        for i in range(n):
            numer += z[i] * np.sum(z[neighbour_idx[i]])
        numer *= w_val  # each weight is 1/k

        I_obs = (n / (n * 1.0)) * numer / s2  # S₀ = n * k * (1/k) = n for row-std

        # ---- Monte Carlo p-value ----
        I_rand = np.empty(permutations, dtype=float)
        rng = default_rng()
        for p in range(permutations):
            z_shuffled = rng.permutation(z)
            numer_p = 0.0
            for i in range(n):
                numer_p += z_shuffled[i] * np.sum(z_shuffled[neighbour_idx[i]])
            numer_p *= w_val
            I_rand[p] = numer_p / s2

        # pseudo p-value (two-sided)
        n_extreme = int(np.sum(np.abs(I_rand) >= np.abs(I_obs)))
        p_value = (n_extreme + 1) / (permutations + 1)

        # z-score approximation based on permutation distribution
        std_perm = float(np.std(I_rand, ddof=1))
        z_score = float((I_obs - np.mean(I_rand)) / std_perm) if std_perm > 0 else 0.0

        return {
            "chart_type": chart_type,
            "data": {},
            "statistics": {
                "global_moran_i": float(I_obs),
                "expected_i": -1.0 / (n - 1) if n > 1 else 0.0,
                "p_value": float(p_value),
                "z_score": z_score,
                "n": n,
                "k": k,
                "permutations": permutations,
                "is_significant": bool(p_value < 0.05),
            },
            "metadata": {
                "is_valid": True,
                "error": "",
                "method": f"KNN(k={k})_row_standardised",
            },
        }

    @staticmethod
    def compute_local_moran_i(
        coords: pd.DataFrame | np.ndarray,
        values: pd.Series,
        *,
        k: int = _DEFAULT_K,
        permutations: int = _N_PERMUTATIONS,
    ) -> Dict[str, Any]:
        """Compute Local Moran's I (LISA) with significance flags.

        Returns per-location Iᵢ, z-score, p-value, and quadrant
        classification (HH / LL / HL / LH / NS).

        Parameters
        ----------
        coords, values, k, permutations : same as compute_global_moran_i.

        Returns
        -------
        Standard analytics-engine dict with data containing per-point results.
        """
        chart_type = "MoranI_LISA"
        # --- guard ---
        try:
            vals = _sanitise(values)
            n = vals.size
            if n < k + 1:
                return {
                    "chart_type": chart_type,
                    "data": {},
                    "statistics": {},
                    "metadata": {
                        "is_valid": False,
                        "error": f"資料不足（{n} 筆），至少需 {k + 1} 筆。",
                    },
                }
            if isinstance(coords, pd.DataFrame):
                if "X" not in coords.columns or "Y" not in coords.columns:
                    return {
                        "chart_type": chart_type,
                        "data": {},
                        "statistics": {},
                        "metadata": {
                            "is_valid": False,
                            "error": "座標資料需包含 X 與 Y 欄位。",
                        },
                    }
                coord_arr = coords[["X", "Y"]].to_numpy(dtype=float)
            else:
                coord_arr = np.asarray(coords, dtype=float)

            if coord_arr.ndim != 2 or coord_arr.shape[1] != 2:
                return {
                    "chart_type": chart_type,
                    "data": {},
                    "statistics": {},
                    "metadata": {
                        "is_valid": False,
                        "error": "座標需為 (N, 2) 陣列。",
                    },
                }
            if coord_arr.shape[0] != n:
                return {
                    "chart_type": chart_type,
                    "data": {},
                    "statistics": {},
                    "metadata": {
                        "is_valid": False,
                        "error": f"座標數（{coord_arr.shape[0]}）與數值數（{n}）不符。",
                    },
                }
        except ValueError as exc:
            return {
                "chart_type": chart_type,
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": str(exc)},
            }

        # --- weights ---
        try:
            neighbour_idx, w_val = _row_standardised_weights(coord_arr, k)
        except ValueError as exc:
            return {
                "chart_type": chart_type,
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": str(exc)},
            }

        z = vals - np.mean(vals)
        s2 = np.sum(z ** 2) / (n - 1)  # variance
        if s2 == 0:
            return {
                "chart_type": chart_type,
                "data": {},
                "statistics": {},
                "metadata": {
                    "is_valid": False,
                    "error": "所有數值相同，無法計算 Local Moran's I。",
                },
            }

        # --- Local Iᵢ ---
        # Vectorized local I calculation:
        # z[neighbour_idx] has shape (n, k), summing over axis=1 gives the neighbor sum for each i.
        I_local = z * np.sum(z[neighbour_idx], axis=1) * w_val / s2

        # --- Monte Carlo pseudo p-values (per location) ---
        # Adjust permutations based on sample size to avoid scaling bottleneck
        if permutations == _N_PERMUTATIONS:
            if n > 20000:
                permutations = 49
            elif n > 2000:
                permutations = 99

        # Vectorized Monte Carlo permutation
        lag_sum = np.sum(z[neighbour_idx], axis=1)
        abs_lag_sum = np.abs(lag_sum)
        n_extreme = np.zeros(n, dtype=int)
        rng = default_rng()

        for _ in range(permutations):
            z_shuffled = rng.permutation(z)
            lag_shuffled = np.sum(z_shuffled[neighbour_idx], axis=1)
            n_extreme += (np.abs(lag_shuffled) >= abs_lag_sum)

        p_values = (n_extreme + 1) / (permutations + 1)

        # --- quadrant classification ---
        z_std = z / np.sqrt(s2)  # standardised value
        # Vectorized spatial lag calculation
        lag = np.mean(z_std[neighbour_idx], axis=1)

        # Vectorized quadrant classification
        conds = [
            p_values >= 0.05,
            (z_std > 0) & (lag > 0),
            (z_std < 0) & (lag < 0),
            (z_std > 0) & (lag < 0),
            (z_std < 0) & (lag > 0)
        ]
        choices = ["NS", "HH", "LL", "HL", "LH"]
        classifications = np.select(conds, choices, default="NS").tolist()

        n_sig = int(np.sum(p_values < 0.05))
        return {
            "chart_type": chart_type,
            "data": {
                "x": coord_arr[:, 0].tolist(),
                "y": coord_arr[:, 1].tolist(),
                "local_i": I_local.tolist(),
                "p_values": p_values.tolist(),
                "z_scores": ((I_local - np.mean(I_local)) / np.std(I_local, ddof=1)).tolist()
                if n > 2
                else [0.0] * n,
                "classifications": classifications,
                "quadrant_std_value": z_std.tolist(),
                "quadrant_lag": lag.tolist(),
            },
            "statistics": {
                "n": n,
                "k": k,
                "permutations": permutations,
                "n_significant": n_sig,
                "pct_significant": round(n_sig / n * 100, 1) if n > 0 else 0.0,
                "class_counts": {
                    "HH": classifications.count("HH"),
                    "LL": classifications.count("LL"),
                    "HL": classifications.count("HL"),
                    "LH": classifications.count("LH"),
                    "NS": classifications.count("NS"),
                },
            },
            "metadata": {
                "is_valid": True,
                "error": "",
                "method": f"KNN(k={k})_row_standardised",
            },
        }
