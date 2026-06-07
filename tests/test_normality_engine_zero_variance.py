"""Contract: zero-variance series skip Shapiro with deterministic metadata (SPC_RULES §2.1)."""

from __future__ import annotations

import pandas as pd

from app.analytics.normality_engine import NormalityEngine


def test_normality_zero_variance_skips_shapiro_with_reason() -> None:
    s = pd.Series([42.0, 42.0, 42.0, 42.0])
    out = NormalityEngine.compute_normality(s)
    assert out["metadata"]["is_valid"] is True
    stats = out["statistics"]
    assert stats.get("normality_test_skipped") is True
    assert stats.get("shapiro_skip_reason") == "zero_variance"
    assert stats.get("test_name") == "Shapiro-Wilk (skipped: zero variance)"
    assert float(stats.get("p_value", 0.0)) == 1.0
