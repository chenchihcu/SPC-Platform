"""Eval 4: confirm the threading watchdog catches a hung engine.

Monkey-patches ``compute_analysis_payload`` to sleep 60 s, then runs the matrix
with timeout=2 s (effective per-cell budget = 2 × 5 = 10 s for payload build).
Expected: SUMMARY.md contains '## STALL cells' and total wall-clock < 60 s.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]  # ...workspace/iteration-1/eval-4 → project root
SCRIPTS_DIR = PROJECT_ROOT / ".claude" / "skills" / "spc-validation-matrix" / "scripts"
for p in (str(PROJECT_ROOT), str(SCRIPTS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

# Force tight timeout BEFORE importing run_matrix (which reads env at import time)
os.environ["SPC_VALIDATION_ENGINE_TIMEOUT_S"] = "2"
os.environ["SPC_VALIDATION_MATRIX_TIMEOUT_S"] = "120"

# Monkey-patch the payload computer to hang
from app.viewmodels import chart_analysis_viewmodel as cavm  # noqa: E402

_orig = cavm.compute_analysis_payload

def _slow(*args, **kwargs):
    print("[mock] compute_analysis_payload hanging for 60s ...", flush=True)
    time.sleep(60)
    return _orig(*args, **kwargs)

cavm.compute_analysis_payload = _slow

# engine_invoker imports compute_analysis_payload at module-load — patch its ref too
import engine_invoker  # noqa: E402
engine_invoker.compute_analysis_payload = _slow

# Now run the matrix on a tiny scope
from run_matrix import main  # noqa: E402

OUT = Path(__file__).parent / "eval-4_watchdog_stall"

t0 = time.perf_counter()
rc = main(
    [
        "--fixture", "normal_baseline",
        "--engines", "imr",
        "--features", "Volume",
        "--filters", "full",
        "--arities", "1",
        "--skip-export",
        "--output", str(OUT),
    ]
)
elapsed = time.perf_counter() - t0
print(f"[eval-4] return code = {rc}, total wall-clock = {elapsed:.1f}s", flush=True)

# Verify expectation
summary = (OUT / "SUMMARY.md").read_text(encoding="utf-8")
has_stall_section = "## STALL cells" in summary
print(f"[eval-4] SUMMARY contains '## STALL cells': {has_stall_section}")
print(f"[eval-4] wall-clock <= 60s: {elapsed <= 60}")
print("[eval-4] PASS" if (has_stall_section and elapsed <= 60) else "[eval-4] FAIL")
