"""Shared wall-clock timing helper for performance-style tests (chart baseline + release P gate)."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def measure_wall_seconds(fn: Callable[[], T]) -> tuple[T, float]:
    """Run ``fn`` once; return ``(result, elapsed_seconds)`` using perf_counter."""
    t0 = time.perf_counter()
    out = fn()
    return out, time.perf_counter() - t0
