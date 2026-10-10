# Chart PNG baselines

Used by [`tests/test_chart_baseline_png.py`](../test_chart_baseline_png.py) with `matplotlib.testing.compare.compare_images`.

The pytest must use `matplotlib.pyplot.rc_context(...)` for DejaVu + dpi so **global** `rcParams` are not left on `DejaVu Sans` (that would flood later tests with CJK glyph warnings).

## Regenerate

The raster depends on the **matplotlib version**, not the OS: one release renders pixel-identically on `windows-latest` and `ubuntu-latest`, while a version change moves it well past the tolerance. The test therefore compares strictly (`RASTER_TOL`) only when the installed matplotlib equals `BASELINE_MPL_VERSION` in the test; otherwise it skips the raster step locally and **fails on CI** (`CI` env set) so drift is never silent.

Canonical baseline = the CI render. When CI fails with the version message (or the chart theme changes on purpose):

1. Download the `chart-baseline-images` artifact from the failed `ci-quality` run (uploaded on test failure).
2. Copy `pytest-of-*/pytest-0/test_density_chart_matches_bas0/actual.png` over `tests/baseline_images/density_chart_default.png`; inspect it first — only theme/version changes are acceptable, never data geometry.
3. Set `BASELINE_MPL_VERSION` to the matplotlib version from that run's install log.

Then run `python -m pytest tests/test_chart_baseline_png.py -q`.
