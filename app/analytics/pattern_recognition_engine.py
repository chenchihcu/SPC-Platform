"""Nelson-rules based pattern recognition for SPC sequences."""

from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd


def _as_valid_series(data: pd.Series) -> pd.Series:
    return data.replace([np.inf, -np.inf], np.nan).dropna()


def _collect_point_indices_for_bool_runs(
    mask: np.ndarray,
    indices: list[Any],
    *,
    min_len: int,
    end_extra: int = 0,
) -> list[Any]:
    """Return point indices covered by contiguous True runs in a boolean mask."""
    if mask.size == 0:
        return []
    true_positions = np.flatnonzero(mask)
    if true_positions.size == 0:
        return []

    breaks = np.flatnonzero(np.diff(true_positions) != 1) + 1
    groups = np.split(true_positions, breaks)
    out: list[Any] = []
    max_index = len(indices)
    for group in groups:
        if group.size < min_len:
            continue
        start = int(group[0])
        stop = min(int(group[-1]) + 1 + end_extra, max_index)
        out.extend(indices[start:stop])
    return out


def _collect_point_indices_for_same_side_runs(mask: np.ndarray, indices: list[Any], min_len: int) -> list[Any]:
    """Return point indices covered by same-side runs, for both True and False sides."""
    if mask.size == 0:
        return []
    change_points = np.flatnonzero(np.diff(mask.astype(np.int8)) != 0) + 1
    starts = np.concatenate(([0], change_points))
    stops = np.concatenate((change_points, [mask.size]))
    out: list[Any] = []
    for start, stop in zip(starts, stops):
        if int(stop) - int(start) >= min_len:
            out.extend(indices[int(start):int(stop)])
    return out


class PatternRecognitionEngine:
    """Detect core Nelson rule hits on a single sequence."""

    @staticmethod
    def compute_nelson(
        data: pd.Series,
        target_col: str,
    ) -> Dict[str, Any]:
        valid = _as_valid_series(data)
        if len(valid) < 8:
            return {
                "chart_type": "PatternRecognition",
                "data": {},
                "statistics": {},
                "metadata": {
                    "is_valid": False,
                    "target_col": target_col,
                    "error": "資料不足（至少需 8 筆）。",
                },
            }

        values = valid.to_numpy(dtype=float)
        indices = list(valid.index)
        mean = float(np.mean(values))
        sigma = float(np.std(values, ddof=1))
        if sigma <= 0:
            return {
                "chart_type": "PatternRecognition",
                "data": {},
                "statistics": {},
                "metadata": {
                    "is_valid": False,
                    "target_col": target_col,
                    "error": "標準差為 0，無法做規則判讀。",
                },
            }

        hits: list[dict[str, Any]] = []

        # Rule 1: one point more than 3 sigma from mean.
        rule1_idx = [indices[i] for i in np.flatnonzero(np.abs(values - mean) > 3 * sigma)]
        if rule1_idx:
            hits.append({"rule": "R1", "description": "1 point beyond 3σ", "indices": rule1_idx})

        # Rule 2: nine (or more) points in a row on same side of mean.
        rule2_idx = _collect_point_indices_for_same_side_runs(values >= mean, indices, 9)
        if rule2_idx:
            hits.append({"rule": "R2", "description": "9 points same side of mean", "indices": sorted(set(rule2_idx))})

        # Rule 3: six points in a row increasing or decreasing.
        diffs = np.diff(values)
        rule3_idx = (
            _collect_point_indices_for_bool_runs(diffs > 0, indices, min_len=5, end_extra=1)
            + _collect_point_indices_for_bool_runs(diffs < 0, indices, min_len=5, end_extra=1)
        )
        if rule3_idx:
            hits.append({"rule": "R3", "description": "6 points monotonic trend", "indices": sorted(set(rule3_idx))})

        # Rule 4: fourteen points alternating up and down.
        alternating_pairs = (diffs[:-1] * diffs[1:]) < 0
        rule4_idx = _collect_point_indices_for_bool_runs(
            alternating_pairs,
            indices,
            min_len=12,
            end_extra=2,
        )
        if rule4_idx:
            hits.append({"rule": "R4", "description": "14 points alternating", "indices": sorted(set(rule4_idx))})

        all_hit_indices = sorted({idx for h in hits for idx in h["indices"]})
        return {
            "chart_type": "PatternRecognition",
            "data": {
                "indices": indices,
                "values": values.tolist(),
                "hit_indices": all_hit_indices,
                "rule_hits": hits,
            },
            "statistics": {
                "mean": mean,
                "sigma": sigma,
                "rule_count": len(hits),
                "hit_point_count": len(all_hit_indices),
            },
            "metadata": {
                "is_valid": True,
                "target_col": target_col,
                "error": "",
            },
        }
