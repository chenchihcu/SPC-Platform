"""Step 4: golden_tolerance.json encodes planned metric families (D.1)."""

from __future__ import annotations

from pathlib import Path

from tests.release_validation.helpers.tolerance import load_tolerance_policy


def test_golden_tolerance_includes_planned_metric_keys(golden_tolerance_path: Path) -> None:
    policy = load_tolerance_policy(golden_tolerance_path)
    metrics = policy.get("metrics") or {}
    for name in (
        "mean",
        "std",
        "cp",
        "cpk",
        "pp",
        "ppk",
        "yield_pct",
        "dpmo",
        "sigma_level",
        "percentile",
        "normality_pvalue",
        "cpk_ci",
        "histogram_bin_count",
        "default_float",
    ):
        assert name in metrics, name
    exact = policy.get("exact_integer_metrics") or []
    for name in ("oos_count", "matched_count", "unmatched_count", "measurement_row_count"):
        assert name in exact, name
