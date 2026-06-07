"""Numeric tolerance helpers for golden / release_validation assertions."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_JSON_POLICY_CACHE: dict[str, dict[str, Any]] = {}


def load_tolerance_policy(path: Path) -> dict[str, Any]:
    """Load golden_tolerance.json (cached by resolved path)."""
    key = str(path.resolve())
    if key not in _JSON_POLICY_CACHE:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("tolerance policy root must be a JSON object")
        _JSON_POLICY_CACHE[key] = raw
    return _JSON_POLICY_CACHE[key]


def _merged_metric_configs(
    policy: Mapping[str, Any],
    overrides: Mapping[str, Any] | None,
) -> dict[str, Any]:
    base = dict(policy.get("metrics") or {})
    ovr = overrides or {}
    if not ovr:
        return base
    merged = dict(base)
    for name, patch in ovr.items():
        if isinstance(patch, dict) and isinstance(merged.get(name), dict):
            merged[name] = {**merged[name], **patch}
        else:
            merged[name] = patch
    return merged


def assert_with_tolerance(
    expected: Any,
    actual: Any,
    metric_name: str,
    *,
    policy: Mapping[str, Any],
    tolerance_overrides: Mapping[str, Any] | None = None,
) -> None:
    """
    Compare expected vs actual using policy exact_integer_metrics or float abs/rel tolerances.

    If both expected and actual are None, passes (non-computable pair).
    """
    if expected is None and actual is None:
        return
    if expected is None or actual is None:
        raise AssertionError(f"{metric_name}: expected {expected!r} but got {actual!r} (one side None)")

    exact_names = list(policy.get("exact_integer_metrics") or [])
    if metric_name in exact_names:
        if int(expected) != int(actual):  # type: ignore[arg-type]
            raise AssertionError(f"{metric_name}: expected exact int {expected!r}, got {actual!r}")
        return

    metrics = _merged_metric_configs(policy, tolerance_overrides)
    cfg = metrics.get(metric_name)
    if not isinstance(cfg, dict):
        cfg = metrics.get("default_float")
    if not isinstance(cfg, dict):
        cfg = {"abs": 1e-6}

    abs_tol = float(cfg.get("abs", 1e-6))
    rel_tol = float(cfg.get("rel", 0.0))

    exp_f = float(expected)  # type: ignore[arg-type]
    act_f = float(actual)  # type: ignore[arg-type]
    if not math.isclose(act_f, exp_f, rel_tol=rel_tol, abs_tol=abs_tol):
        raise AssertionError(
            f"{metric_name}: expected {exp_f!r} ~ {act_f!r} "
            f"(abs_tol={abs_tol}, rel_tol={rel_tol})"
        )
