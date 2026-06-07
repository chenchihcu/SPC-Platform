"""Utility helpers for out-of-control (OOC) sequence analysis."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional


def count_contiguous_ooc_clusters(indices: Iterable[int]) -> int:
    """Count contiguous OOC index clusters.

    Examples:
    - [] -> 0
    - [2, 3, 4, 10] -> 2
    - [5, 7, 9] -> 3
    """

    sorted_unique: List[int] = sorted({int(i) for i in indices})
    if not sorted_unique:
        return 0

    clusters = 1
    prev = sorted_unique[0]
    for idx in sorted_unique[1:]:
        if idx != prev + 1:
            clusters += 1
        prev = idx
    return clusters


def first_group_share(entries: List[Dict[str, Any]], total_oos: int) -> Optional[float]:
    """Return first group's OOS share over total OOS, or None when unavailable."""
    if total_oos <= 0 or not entries:
        return None
    first = entries[0]
    if not isinstance(first, dict):
        return None
    try:
        n = int(first.get("oos_count", 0))
    except (TypeError, ValueError):
        return None
    return float(n) / float(total_oos)
