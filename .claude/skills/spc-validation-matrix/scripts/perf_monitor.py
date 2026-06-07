"""Threading watchdog with tracemalloc-based peak memory tracking.

Cross-platform (no SIGALRM dependency) — uses ``threading.Thread(daemon=True)``
+ ``join(timeout=...)``. If the worker thread is still alive after timeout,
the cell is marked STALL; the orphan thread keeps running but is daemonized so
it dies when the main process exits.

For real "kill the runaway" semantics on Windows, future iterations may switch
to ``multiprocessing``; for v1 we accept this limitation since this validator
is a developer-time tool, not a production gate.
"""

from __future__ import annotations

import threading
import time
import traceback
import tracemalloc
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class CellOutcome:
    status: str          # PASS / FAIL / STALL / OVERLOAD / ERROR
    result: Any
    duration_s: float
    peak_mb: float
    error: str
    traceback: str


def run_with_watchdog(
    fn: Callable[..., Any],
    *args: Any,
    timeout_s: float,
    peak_mb_limit: float,
    **kwargs: Any,
) -> CellOutcome:
    """Run ``fn(*args, **kwargs)`` with a soft timeout and peak-memory cap.

    tracemalloc is process-wide; this helper assumes sequential cell execution.
    """
    state: dict[str, Any] = {
        "result": None,
        "error": "",
        "traceback": "",
        "peak_bytes": 0,
        "duration_s": 0.0,
    }

    def _target() -> None:
        tracemalloc.start()
        t0 = time.perf_counter()
        try:
            state["result"] = fn(*args, **kwargs)
        except BaseException as exc:
            state["error"] = f"{type(exc).__name__}: {exc}"
            state["traceback"] = traceback.format_exc()
        finally:
            state["duration_s"] = time.perf_counter() - t0
            try:
                _, peak = tracemalloc.get_traced_memory()
                state["peak_bytes"] = peak
            finally:
                tracemalloc.stop()

    th = threading.Thread(target=_target, daemon=True)
    th.start()
    th.join(timeout=timeout_s)

    peak_mb = state["peak_bytes"] / (1024.0 * 1024.0)

    if th.is_alive():
        return CellOutcome(
            status="STALL",
            result=None,
            duration_s=timeout_s,
            peak_mb=peak_mb,
            error=f"timeout after {timeout_s:.1f}s",
            traceback="",
        )

    if state["error"]:
        return CellOutcome(
            status="ERROR",
            result=None,
            duration_s=state["duration_s"],
            peak_mb=peak_mb,
            error=state["error"],
            traceback=state["traceback"],
        )

    if peak_mb > peak_mb_limit:
        return CellOutcome(
            status="OVERLOAD",
            result=state["result"],
            duration_s=state["duration_s"],
            peak_mb=peak_mb,
            error=f"peak memory {peak_mb:.1f}MB exceeds {peak_mb_limit:.1f}MB",
            traceback="",
        )

    return CellOutcome(
        status="PASS",
        result=state["result"],
        duration_s=state["duration_s"],
        peak_mb=peak_mb,
        error="",
        traceback="",
    )
