"""Xbar-R chart engine for subgrouped process control."""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd


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
    # Use median subgroup size for constants lookup; clamp to available table.
    n_med = int(np.median(subgroup_sizes))
    n_effective = max(2, min(10, n_med))
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
    n_effective = max(2, min(10, size))
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
            return {
                "chart_type": "Xbar-R",
                "data": {},
                "statistics": {},
                "metadata": {
                    "is_valid": False,
                    "target_col": target_col,
                    "error": "無資料或缺少欄位。",
                },
            }

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
            return {
                "chart_type": "Xbar-R",
                "data": {},
                "statistics": {},
                "metadata": {
                    "is_valid": False,
                    "target_col": target_col,
                    "error": "有效子群不足（每群至少 2 筆）。",
                },
            }

        a2, d3, d4 = _XBAR_R_CONSTANTS[n_effective]

        xbar_values: list[float] = []
        r_values: list[float] = []
        counts: list[int] = []
        for g in groups:
            xbar_values.append(float(np.mean(g)))
            r_values.append(float(np.max(g) - np.min(g)))
            counts.append(int(len(g)))

        xbarbar = float(np.mean(xbar_values))
        rbar = float(np.mean(r_values))
        ucl_xbar = xbarbar + a2 * rbar
        lcl_xbar = xbarbar - a2 * rbar
        ucl_r = d4 * rbar
        lcl_r = d3 * rbar

        ooc_xbar = [i for i, v in enumerate(xbar_values) if v > ucl_xbar or v < lcl_xbar]
        ooc_r = [i for i, v in enumerate(r_values) if v > ucl_r or v < lcl_r]
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
                "ucl_xbar": float(ucl_xbar),
                "lcl_xbar": float(lcl_xbar),
                "ucl_r": float(ucl_r),
                "lcl_r": float(lcl_r),
                "a2": float(a2),
                "d3": float(d3),
                "d4": float(d4),
                "source": source,
            },
            "metadata": {
                "is_valid": True,
                "target_col": target_col,
                "error": "",
            },
        }
