"""Build the (fixture × arity × features × chart_id × filter) cell list.

Pulls the chart catalog from ``app.analytics.chart_registry.CHART_CATALOG`` so
the validator stays in sync with whatever engines exist today — no hand-coded
inventory to drift.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any

from app.analytics.chart_registry import (
    CHART_CATALOG,
    REQUIRED_SINGLE,
)

DEFAULT_FEATURES: list[str] = ["Volume", "Area", "Height"]
DEFAULT_FILTERS: list[str] = ["full", "top10pct", "by_part_type"]
DEFAULT_ARITIES: list[int] = [1, 2, 3]

# Chart families whose required_feature_count is REQUIRED_SINGLE in the catalog
# but actually accept 1..N features (kept in sync with chart_registry's
# ``is_chart_available_for_selection`` logic).
MULTI_FEATURE_FAMILIES: frozenset[str] = frozenset(
    {
        "histogram_spec",
        "normality",
        "boxplot",
        "density",
        "anova_parttype",
        "ooc_analysis",
        "shift_detection",
        "drift_detection",
        "outlier_analysis",
        "pattern_recognition",
    }
)
DUAL_AT_LEAST_TWO: frozenset[str] = frozenset(
    {"scatter_spec", "correlation_matrix", "correlation_heatmap"}
)


@dataclass(frozen=True)
class Cell:
    fixture: str
    arity: int
    features: tuple[str, ...]
    chart_id: str
    filter_name: str

    def features_str(self) -> str:
        return "+".join(self.features)


def _arity_compatible(chart_id: str, entry: dict[str, Any], arity: int) -> bool:
    if chart_id in MULTI_FEATURE_FAMILIES:
        return arity >= 1
    if chart_id in DUAL_AT_LEAST_TWO:
        return arity >= 2
    req = int(entry.get("required_feature_count", REQUIRED_SINGLE))
    return req == arity


def list_engines() -> list[str]:
    """Return all chart_ids in CHART_CATALOG (preserving order)."""
    return [str(e["id"]) for e in CHART_CATALOG]


def build_matrix(
    fixtures: list[str],
    arities: list[int],
    features: list[str],
    filters: list[str],
    engines: list[str] | None = None,
) -> list[Cell]:
    catalog: dict[str, dict[str, Any]] = {str(e["id"]): e for e in CHART_CATALOG}
    selected = engines if engines is not None else list(catalog.keys())

    cells: list[Cell] = []
    for fixture in fixtures:
        for arity in arities:
            for feat_combo in combinations(features, arity):
                for chart_id in selected:
                    entry = catalog.get(chart_id)
                    if entry is None:
                        continue
                    if not _arity_compatible(chart_id, entry, arity):
                        continue
                    for filt in filters:
                        cells.append(
                            Cell(
                                fixture=fixture,
                                arity=arity,
                                features=tuple(feat_combo),
                                chart_id=chart_id,
                                filter_name=filt,
                            )
                        )
    return cells
