"""
多特徵並列圖（3F）共用 Z-score 顯示正規化。

面板骨架在 ``BaseChart._prepare_multi_feature_axes`` / ``_finish_multi_feature_axes``；
本模組只負責顯示座標縮放：不改動任何統計量、管制界限或 payload 語意。
Z-score 只用於顯示座標轉換（display-only），原始數值仍保留在標籤中。
"""
from __future__ import annotations

from typing import Sequence

import numpy as np


# ── Z-score display normalization ──────────────────────────────────────

def zscore_scale(
    values: Sequence[float] | np.ndarray,
    *,
    mean: float | None = None,
    std: float | None = None,
) -> tuple[float, float]:
    """Return ``(mean, std)`` for display z-scoring.

    ``mean``/``std`` override the sample estimates (e.g. engine-provided
    ``normalize_mean``/``normalize_std``). The sample std uses ``ddof=1``;
    a degenerate std (<= 0, non-finite, or a single point) falls back to 1.0
    so the transform degrades to a pure shift instead of dividing by zero.
    """
    arr = np.asarray(values, dtype=float)
    if mean is None:
        mean_val = float(np.mean(arr)) if arr.size else 0.0
    else:
        mean_val = float(mean)
    if std is None:
        std_val = float(np.std(arr, ddof=1)) if arr.size > 1 else 0.0
    else:
        std_val = float(std)
    if not np.isfinite(std_val) or std_val <= 0:
        std_val = 1.0
    return mean_val, std_val


def zscore_value(value: float, mean: float, std: float) -> float:
    """Map one raw value (limit, centre line, zero) into the z-score display axis."""
    return (float(value) - mean) / std


def zscore_array(values: Sequence[float] | np.ndarray, mean: float, std: float) -> np.ndarray:
    """Map a series into the z-score display axis."""
    return (np.asarray(values, dtype=float) - mean) / std
