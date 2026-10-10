"""Xbar-R chart engine for subgrouped process control."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, Optional
from app.analytics.statistical_utils import invalid_chart_payload

import numpy as np
import pandas as pd
from scipy.stats import norm  # type: ignore[import-untyped]


# AIAG d2 / d3 for n = 2..10 (relative-range mean and std of n standard normals).
_D2_D3_TABLE: dict[int, tuple[float, float]] = {
    2: (1.128, 0.853),
    3: (1.693, 0.888),
    4: (2.059, 0.880),
    5: (2.326, 0.864),
    6: (2.534, 0.848),
    7: (2.704, 0.833),
    8: (2.847, 0.820),
    9: (2.970, 0.808),
    10: (3.078, 0.797),
}

_XBAR_R_CONSTANTS: dict[int, tuple[float, float, float]] = {
    # n: (A2, D3, D4)
    2: (1.880, 0.000, 3.267),
    3: (1.023, 0.000, 2.574),
    4: (0.729, 0.000, 2.282),
    5: (0.577, 0.000, 2.114),
    6: (0.483, 0.000, 2.004),
    7: (0.419, 0.076, 1.924),
    8: (0.373, 0.136, 1.864),
    9: (0.337, 0.184, 1.816),
    10: (0.308, 0.223, 1.777),
}

_DEFAULT_SUBGROUP_SIZE = 5


def _d2_d3(n: int) -> tuple[float, float]:
    """d2(n), d3(n) for any n >= 2 (SPC_RULES §5): AIAG table for n <= 10,
    exact numerical integration beyond (SPI board subgroups hold hundreds of pads)."""
    if n in _D2_D3_TABLE:
        return _D2_D3_TABLE[n]
    return _integrate_d2_d3(n)


@lru_cache(maxsize=256)
def _integrate_d2_d3(n: int) -> tuple[float, float]:
    """Exact range distribution of n standard normals:
    d2 = ∫ [1 − Φ^n − (1 − Φ)^n] dx; F_R(w) = n ∫ φ(x)[Φ(x+w) − Φ(x)]^(n−1) dx;
    d3 = sqrt(2∫ w(1 − F_R(w)) dw − d2²).
    """
    x = np.linspace(-9.0, 9.0, 1801)
    w = np.linspace(0.0, 18.0, 1201)
    phi = norm.pdf(x)
    cdf = norm.cdf(x)
    d2 = float(np.trapezoid(1.0 - cdf**n - (1.0 - cdf) ** n, x))
    spread = norm.cdf(x[None, :] + w[:, None]) - cdf[None, :]
    range_cdf = n * np.trapezoid(phi[None, :] * spread ** (n - 1), x, axis=1)
    second_moment = 2.0 * float(np.trapezoid(w * np.clip(1.0 - range_cdf, 0.0, 1.0), w))
    d3 = float(np.sqrt(max(second_moment - d2 * d2, 0.0)))
    return d2, d3


def _xbar_r_constants(n: int) -> tuple[float, float, float]:
    """(A2, D3, D4) for subgroup size n; table values for n <= 10, exact beyond."""
    if n in _XBAR_R_CONSTANTS:
        return _XBAR_R_CONSTANTS[n]
    d2, d3 = _d2_d3(n)
    return 3.0 / (d2 * np.sqrt(n)), max(0.0, 1.0 - 3.0 * d3 / d2), 1.0 + 3.0 * d3 / d2


def _valid_series(data: pd.Series) -> pd.Series:
    return data.replace([np.inf, -np.inf], np.nan).dropna()


def _build_subgroups_by_board(
    df: pd.DataFrame,
    value_col: str,
    board_col: str,
) -> tuple[list[str], list[np.ndarray], int]:
    labels: list[str] = []
    groups: list[np.ndarray] = []
    subgroup_sizes: list[int] = []
    for board_id, gdf in df.groupby(board_col):
        vals = _valid_series(gdf[value_col]).to_numpy(dtype=float)
        if len(vals) < 2:
            continue
        labels.append(str(board_id))
        groups.append(vals)
        subgroup_sizes.append(len(vals))
    if not groups:
        return [], [], 0
    # Median subgroup size drives the display limits. Never clamp to the n=10
    # table row: SPI boards hold hundreds of pads (SPC_RULES §5).
    n_effective = max(2, int(np.median(subgroup_sizes)))
    return labels, groups, n_effective


def _build_subgroups_by_chunk(
    data: pd.Series,
    subgroup_size: int,
) -> tuple[list[str], list[np.ndarray], int]:
    vals = _valid_series(data).to_numpy(dtype=float)
    if len(vals) < 2:
        return [], [], 0
    size = max(2, subgroup_size)
    groups: list[np.ndarray] = []
    labels: list[str] = []
    i = 0
    group_idx = 1
    while i < len(vals):
        chunk = vals[i : i + size]
        if len(chunk) >= 2:
            groups.append(chunk)
            labels.append(f"G{group_idx}")
            group_idx += 1
        i += size
    if not groups:
        return [], [], 0
    n_effective = size
    return labels, groups, n_effective


class XbarREngine:
    """Compute Xbar-R subgroup chart statistics and limits."""

    @staticmethod
    def compute_xbar_r(
        df: pd.DataFrame,
        target_col: str,
        *,
        board_col: Optional[str] = None,
        subgroup_size: int = _DEFAULT_SUBGROUP_SIZE,
    ) -> Dict[str, Any]:
        if df is None or df.empty or target_col not in df.columns:
            return invalid_chart_payload("Xbar-R", "無資料或缺少欄位。", target_col)

        effective_board_col = board_col
        if effective_board_col is None:
            for candidate in ("BoardNo", "PanelId"):
                if candidate in df.columns:
                    effective_board_col = candidate
                    break

        labels: list[str]
        groups: list[np.ndarray]
        n_effective: int
        source = "chunk"
        if effective_board_col and effective_board_col in df.columns:
            labels, groups, n_effective = _build_subgroups_by_board(df, target_col, effective_board_col)
            source = f"group_by:{effective_board_col}"
        else:
            labels, groups, n_effective = _build_subgroups_by_chunk(df[target_col], subgroup_size)

        if not groups or n_effective < 2:
            return invalid_chart_payload("Xbar-R", "有效子群不足（每群至少 2 筆）。", target_col)

        a2, d3, d4 = _xbar_r_constants(n_effective)

        xbar_values: list[float] = []
        r_values: list[float] = []
        counts: list[int] = []
        for g in groups:
            xbar_values.append(float(np.mean(g)))
            r_values.append(float(np.max(g) - np.min(g)))
            counts.append(int(len(g)))

        xbarbar = float(np.mean(xbar_values))
        rbar = float(np.mean(r_values))
        # sigma_hat = mean(R_i / d2(n_i)) so ranges from unequal subgroup sizes
        # are put on a common scale before pooling (SPC_RULES §5).
        sigma_hat = float(np.mean([r / _d2_d3(c)[0] for r, c in zip(r_values, counts)]))
        # Global display limits use the median-n constants; with equal n they
        # equal Xbar_bar ± A2·R_bar and D3/D4·R_bar (to table rounding).
        d2_eff, d3_eff = _d2_d3(n_effective)
        ucl_xbar = xbarbar + 3.0 * sigma_hat / np.sqrt(n_effective)
        lcl_xbar = xbarbar - 3.0 * sigma_hat / np.sqrt(n_effective)
        ucl_r = (d2_eff + 3.0 * d3_eff) * sigma_hat
        lcl_r = max(0.0, d2_eff - 3.0 * d3_eff) * sigma_hat

        # OOC detection uses per-subgroup limits so unequal subgroup sizes get
        # the statistically correct limits (SPC_RULES §5: constants depend on n).
        ooc_xbar: list[int] = []
        ooc_r: list[int] = []
        for i, (n_i, xbar_v, r_v) in enumerate(zip(counts, xbar_values, r_values)):
            half_width = 3.0 * sigma_hat / np.sqrt(n_i)
            if xbar_v > xbarbar + half_width or xbar_v < xbarbar - half_width:
                ooc_xbar.append(i)
            d2_i, d3_i = _d2_d3(n_i)
            if r_v > (d2_i + 3.0 * d3_i) * sigma_hat or r_v < max(0.0, d2_i - 3.0 * d3_i) * sigma_hat:
                ooc_r.append(i)
        ooc_indices = sorted(set(ooc_xbar + ooc_r))

        return {
            "chart_type": "Xbar-R",
            "data": {
                "labels": labels,
                "xbar_values": xbar_values,
                "r_values": r_values,
                "subgroup_counts": counts,
                "ooc_xbar_indices": ooc_xbar,
                "ooc_r_indices": ooc_r,
                "out_of_control_indices": ooc_indices,
            },
            "statistics": {
                "n_subgroups": len(labels),
                "n_effective": n_effective,
                "xbarbar": xbarbar,
                "rbar": rbar,
                "sigma_hat": sigma_hat,
                "ucl_xbar": float(ucl_xbar),
                "lcl_xbar": float(lcl_xbar),
                "ucl_r": float(ucl_r),
                "lcl_r": float(lcl_r),
                "a2": float(a2),
                "d3": float(d3),
                "d4": float(d4),
                "source": source,
                "subgroup_sizes": counts,
                "sizes_uniform": len(set(counts)) == 1,
            },
            "metadata": {
                "is_valid": True,
                "target_col": target_col,
                "error": "",
            },
        }
