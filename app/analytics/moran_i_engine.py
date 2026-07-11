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
                        "error": f"資料不足（{n} 筆），至少需 {k + 1} 筆才能計算空間權重。",
                    },
                }
            # coords
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
                # align coords to values index if possible
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

        # --- Global Moran's I ---
        z = vals - np.mean(vals)
        s2 = np.sum(z ** 2)
        if s2 == 0:
            return {
                "chart_type": chart_type,
                "data": {},
                "statistics": {},
                "metadata": {
                    "is_valid": False,
                    "error": "所有數值相同，無法計算 Moran's I。",
                },
            }

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
        I_local = np.empty(n, dtype=float)
        for i in range(n):
            I_local[i] = z[i] * np.sum(z[neighbour_idx[i]]) * w_val / s2

        # --- Monte Carlo pseudo p-values (per location) ---
        p_values = np.ones(n, dtype=float)
        rng = default_rng()
        for i in range(n):
            n_extreme = 0
            neighbours = neighbour_idx[i]
            for _ in range(permutations):
                z_shuffled = rng.permutation(z)
                I_p = z[i] * np.sum(z_shuffled[neighbours]) * w_val / s2
                if np.abs(I_p) >= np.abs(I_local[i]):
                    n_extreme += 1
            p_values[i] = (n_extreme + 1) / (permutations + 1)

        # --- quadrant classification ---
        z_std = z / np.sqrt(s2)  # standardised value
        lag = np.empty(n, dtype=float)  # spatial lag (mean of neighbours)
        for i in range(n):
            lag[i] = float(np.mean(z_std[neighbour_idx[i]]))

        classifications: list[str] = []
        for i in range(n):
            if p_values[i] >= 0.05:
                classifications.append("NS")
            elif z_std[i] > 0 and lag[i] > 0:
                classifications.append("HH")
            elif z_std[i] < 0 and lag[i] < 0:
                classifications.append("LL")
            elif z_std[i] > 0 and lag[i] < 0:
                classifications.append("HL")
            else:
                classifications.append("LH")

        n_sig = int(np.sum(p_values < 0.05))
        return {
            "chart_type": chart_type,
            "data": {
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
