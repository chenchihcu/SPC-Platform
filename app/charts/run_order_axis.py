"""Run-order X axis helpers for sequence charts.

Engines emit ``data["indices"]`` as the original DataFrame index labels of the
series *in analysis order* (sorted by ``detect_order_col``). Those labels are
row identities, not positions: plotting them as X makes the line jump backwards
(zig-zag) and leaves gaps whenever the source file was not already in
time/board order. Sequence charts therefore plot the 1-based position in the
payload order and use the labels only to place OOC / MR / rule-hit markers.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Sequence, Tuple


def run_order_x(n: int) -> List[int]:
    """Return the 1-based sample positions ``1..n``."""
    return list(range(1, max(int(n), 0) + 1))


def series_axis(indices: Any, n_values: int) -> Tuple[List[int], Dict[Any, int]]:
    """Return ``(x_positions, label_to_position)`` for a series of ``n_values``.

    When ``indices`` is missing or its length disagrees with the values, labels
    cannot be trusted for marker lookup and the mapping is empty.
    """
    x = run_order_x(n_values)
    labels = list(indices) if isinstance(indices, (list, tuple)) else []
    if len(labels) != n_values:
        return x, {}
    return x, {label: pos for pos, label in enumerate(labels, start=1)}


def marker_points(
    labels: Iterable[Any],
    mapping: Dict[Any, int],
    values: Sequence[Any],
) -> Tuple[List[int], List[Any]]:
    """Return ``(x_positions, y_values)`` for marker labels found in ``mapping``."""
    xs: List[int] = []
    ys: List[Any] = []
    for label in labels:
        pos = mapping.get(label)
        if pos is None or pos > len(values):
            continue
        xs.append(pos)
        ys.append(values[pos - 1])
    return xs, ys


def mr_positions(mr_indices: Any, mapping: Dict[Any, int], n_mr: int) -> List[int]:
    """Positions for moving-range points (MR_t sits at sample t, i.e. ``2..N``)."""
    labels = list(mr_indices) if isinstance(mr_indices, (list, tuple)) else []
    xs = [mapping[label] for label in labels if label in mapping]
    if len(xs) == n_mr:
        return xs
    return list(range(2, n_mr + 2))
