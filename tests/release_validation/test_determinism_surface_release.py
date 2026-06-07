"""RNG: no hidden stochastic engines in app/; manifests document determinism notes."""

from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_app_sources_avoid_numpy_random_entrypoints() -> None:
    """If this fails, add explicit seeding / manifest.engine_seed_params and release-validation notes."""
    app_root = _repo_root() / "app"
    needles = ("np.random.", "numpy.random.")
    hits: list[tuple[str, str]] = []
    for path in sorted(app_root.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for n in needles:
            if n in text:
                hits.append((n, str(path.relative_to(_repo_root()))))
    assert not hits, f"app/ must not call numpy RNG entrypoints in release builds: {hits}"
