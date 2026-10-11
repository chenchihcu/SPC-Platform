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


def shared_label_positions(label_lists: Iterable[Any]) -> Dict[Any, int]:
    """Merge per-feature row labels into one ordered ``label -> 1-based position`` map.

    Multi-feature charts share one X axis, but each feature engine drops its own
    NaN/inf rows. Numbering every feature ``1..len`` would shift later samples of
    a feature that lost a row relative to the others, so all features are placed
    on the union of their labels. Each feature keeps its own order; a label first
    seen later is inserted right after its predecessor.
    """
    merged: List[Any] = []
    for labels in label_lists:
        if not isinstance(labels, (list, tuple)):
            continue
        seen = set(merged)
        prev = None
        for label in labels:
            if label not in seen:
                at = merged.index(prev) + 1 if prev is not None else 0
                merged.insert(at, label)
                seen.add(label)
            prev = label
    return {label: pos for pos, label in enumerate(merged, start=1)}


def aligned_axis(
    indices: Any, n_values: int, shared: Dict[Any, int]
) -> Tuple[List[int], Dict[Any, int]]:
    """Like :func:`series_axis`, but X comes from the shared multi-feature map.

    Falls back to plain ``1..n`` positions when labels are unusable.
    """
    labels = list(indices) if isinstance(indices, (list, tuple)) else []
    if len(labels) != n_values or any(label not in shared for label in labels):
        return series_axis(indices, n_values)
    return [shared[label] for label in labels], shared


def feature_label_lists(features: Iterable[str], feature_data: Dict[str, Any]) -> List[Any]:
    """Collect each valid feature's payload row labels for :func:`shared_label_positions`."""
    out: List[Any] = []
    for feat in features:
        fd = feature_data.get(feat, {})
        if fd.get("metadata", {}).get("is_valid", False):
            out.append(fd.get("data", {}).get("indices"))
    return out


def marker_points(
    labels: Iterable[Any],
    mapping: Dict[Any, int],
    values: Sequence[Any],
    x_positions: Sequence[int],
) -> Tuple[List[int], List[Any]]:
    """Return ``(x_positions, y_values)`` for marker labels found in ``mapping``.

    ``x_positions`` is the series' own X list from :func:`series_axis` /
    :func:`aligned_axis`. With a shared multi-feature map, a label's position is
    not its index into this feature's ``values`` (a dropped row shifts later
    samples), so Y is taken from the sample whose X equals that position.
    """
    own_index = {pos: i for i, pos in enumerate(x_positions) if i < len(values)}
    xs: List[int] = []
    ys: List[Any] = []
    for label in labels:
        pos = mapping.get(label)
        if pos is None or pos not in own_index:
            continue
        i = own_index[pos]
        xs.append(pos)
        ys.append(values[i])
    return xs, ys


def mr_positions(mr_indices: Any, mapping: Dict[Any, int], n_mr: int) -> List[int]:
    """Positions for moving-range points (MR_t sits at sample t, i.e. ``2..N``)."""
    labels = list(mr_indices) if isinstance(mr_indices, (list, tuple)) else []
    xs = [mapping[label] for label in labels if label in mapping]
    if len(xs) == n_mr:
        return xs
    return list(range(2, n_mr + 2))
