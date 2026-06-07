"""Release validation: deterministic RNG and shared paths."""

from __future__ import annotations

import json
import os
import random
from pathlib import Path

import pytest


def _default_golden_root() -> Path:
    """Repository-root golden_dataset/; override with GOLDEN_DATASET_ROOT."""
    env = os.environ.get("GOLDEN_DATASET_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    repo_root = Path(__file__).resolve().parents[2]
    return (repo_root / "golden_dataset").resolve()

try:
    import numpy as np

    _HAS_NUMPY = True
except ImportError:  # pragma: no cover
    _HAS_NUMPY = False


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--golden-profile",
        action="store",
        default="default",
        help="Release validation profile label (recorded for reporting only).",
    )


@pytest.fixture(scope="session")
def golden_profile(request: pytest.FixtureRequest) -> str:
    return str(request.config.getoption("--golden-profile"))


@pytest.fixture(scope="session")
def dataset_version(golden_root: Path) -> str:
    mp = golden_root / "normal_baseline" / "expected" / "manifest.json"
    doc = json.loads(mp.read_text(encoding="utf-8"))
    return str(doc.get("dataset_version") or "")


@pytest.fixture(scope="session")
def golden_root() -> Path:
    return _default_golden_root()


@pytest.fixture(scope="session")
def golden_tolerance_path(golden_root: Path) -> Path:
    return golden_root / "golden_tolerance.json"


@pytest.fixture(scope="session", autouse=True)
def _release_validation_deterministic_seed() -> None:
    """Fixed seed for any sampling / stochastic paths in release_validation (plan: 42)."""
    random.seed(42)
    if _HAS_NUMPY:
        np.random.seed(42)
