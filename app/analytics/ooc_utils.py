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


def ooc_run_positions(ooc_labels: Iterable[Any], sequence_labels: Iterable[Any]) -> List[int]:
    """Map OOC index labels to their 0-based positions in the analysed sequence.

    Engines report OOC points by DataFrame index label. Labels are adjacent in
    run order only when the source file was already sorted, so contiguity must
    be judged on positions within ``sequence_labels`` (the payload ``indices``,
    in analysis order). Labels missing from the sequence are dropped.
    """
    position = {label: pos for pos, label in enumerate(sequence_labels)}
    return [position[label] for label in ooc_labels if label in position]


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
