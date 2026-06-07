"""
Tests for chart_router.py — validates chart availability per feature count.
Includes regression test for BUG-1: density_1 must require n=2, not n=1.
"""
from chart_router import (
    ALL_CHARTS,
    CHART_MIN_N,
    ROUTER_TO_REGISTRY_ID,
    ChartContext,
    get_available_charts,
    get_condition_blocked_ids,
)


# ── helpers ───────────────────────────────────────────────────────────────────
def _ctx_all_loaded(n: int) -> ChartContext:
    """All data conditions satisfied; only n_selected varies."""
    return ChartContext(
        meas_loaded=True,
        mapping_done=True,
        coord_loaded=True,
        has_batch=True,
        has_component_type=True,
        n_selected=n,
    )


def _available_ids(n: int) -> set:
    result = get_available_charts(_ctx_all_loaded(n))
    return set(result.available)


def _blocked_ids(n: int) -> set:
    result = get_available_charts(_ctx_all_loaded(n))
    return set(result.blocked)


# ── single-feature (n=1) ──────────────────────────────────────────────────────
_SINGLE_CHARTS = {"imr", "run_chart", "ewma", "cusum", "histogram",
                  "normality", "repeatability", "boxplot", "heatmap", "pareto"}

_DUAL_CHARTS   = {"scatter", "quadrant", "bivariate", "subgroup"}
_TRIPLE_CHARTS = {"anomaly", "consistency", "parallel", "passfail"}


def test_single_feature_single_charts_available():
    available = _available_ids(1)
    for chart in _SINGLE_CHARTS:
        assert chart in available, f"{chart} should be available for n=1"


def test_single_feature_dual_charts_blocked():
    blocked = _blocked_ids(1)
    for chart in _DUAL_CHARTS:
        assert chart in blocked, f"{chart} should be blocked for n=1"


def test_single_feature_triple_charts_blocked():
    blocked = _blocked_ids(1)
    for chart in _TRIPLE_CHARTS:
        assert chart in blocked, f"{chart} should be blocked for n=1"


# ── REGRESSION BUG-1: density_1 must require n=2 ─────────────────────────────
def test_density_requires_n2_not_n1():
    """Regression: density_1 was incorrectly set to MIN_N=1 (BUG-1)."""
    assert CHART_MIN_N["density_1"] == 2, (
        "BUG-1 regression: density_1 MIN_N must be 2 — was incorrectly 1."
    )


def test_density_blocked_for_n1():
    blocked = _blocked_ids(1)
    assert "density_1" in blocked, (
        "density_1 must be blocked when n=1 (BUG-1 fix validation)."
    )


def test_density_available_for_n2():
    available = _available_ids(2)
    assert "density_1" in available, "density_1 should be available when n=2."


# ── dual-feature (n=2) ────────────────────────────────────────────────────────
def test_dual_feature_dual_charts_available():
    available = _available_ids(2)
    for chart in _DUAL_CHARTS:
        assert chart in available, f"{chart} should be available for n=2"


def test_dual_feature_single_charts_still_available():
    # Single-feature charts (MIN_N=1) remain in available at n=2 because 2 >= 1.
    # They are not blocked — the UI renders them with an incompatible placeholder.
    available = _available_ids(2)
    for chart in _SINGLE_CHARTS:
        assert chart in available, f"{chart} should still be available for n=2"


def test_dual_feature_triple_charts_blocked():
    blocked = _blocked_ids(2)
    for chart in _TRIPLE_CHARTS:
        assert chart in blocked, f"{chart} should be blocked for n=2"


# ── triple-feature (n=3) ──────────────────────────────────────────────────────
def test_triple_feature_triple_charts_available():
    available = _available_ids(3)
    for chart in _TRIPLE_CHARTS:
        assert chart in available, f"{chart} should be available for n=3"


def test_triple_feature_single_charts_available():
    # At n=3, all charts have MIN_N <= 3, so single-feature charts are available.
    available = _available_ids(3)
    for chart in _SINGLE_CHARTS:
        assert chart in available, f"{chart} should be available for n=3"


def test_triple_feature_dual_charts_available():
    # At n=3, dual-feature charts (MIN_N=2) satisfy 3 >= 2 → available.
    available = _available_ids(3)
    for chart in _DUAL_CHARTS:
        assert chart in available, f"{chart} should be available for n=3"


# ── no data loaded ────────────────────────────────────────────────────────────
def test_no_data_all_charts_blocked():
    ctx = ChartContext(
        meas_loaded=False, mapping_done=False, coord_loaded=False,
        has_batch=False, has_component_type=False, n_selected=1
    )
    result = get_available_charts(ctx)
    assert len(result.available) == 0


def test_meas_loaded_but_no_mapping_all_blocked():
    ctx = ChartContext(
        meas_loaded=True, mapping_done=False, coord_loaded=False,
        has_batch=True, has_component_type=True, n_selected=1
    )
    result = get_available_charts(ctx)
    assert len(result.available) == 0


# ── router-to-registry mapping completeness ───────────────────────────────────
def test_all_router_charts_have_registry_mapping():
    for router_key in ALL_CHARTS:
        assert router_key in ROUTER_TO_REGISTRY_ID, (
            f"Router chart '{router_key}' has no registry ID mapping."
        )


def test_registry_mapping_values_are_nonempty():
    for router_key, registry_id in ROUTER_TO_REGISTRY_ID.items():
        assert isinstance(registry_id, str) and len(registry_id) > 0


# ── get_condition_blocked_ids ─────────────────────────────────────────────────
def test_heatmap_blocked_without_coord():
    ctx = ChartContext(
        meas_loaded=True, mapping_done=True, coord_loaded=False,
        has_batch=True, has_component_type=True, n_selected=1
    )
    blocked = get_condition_blocked_ids(ctx)
    assert "heatmap" in blocked


def test_heatmap_blocked_when_coord_valid_but_not_joinable():
    """coord_loaded reflects can_do_spatial: coord file parsed but join failed → still blocked."""
    ctx = ChartContext(
        meas_loaded=True, mapping_done=True, coord_loaded=False,
        has_batch=True, has_component_type=True, n_selected=1,
    )
    blocked = get_condition_blocked_ids(ctx)
    assert "heatmap" in blocked


def test_temporal_charts_blocked_without_batch():
    ctx = ChartContext(
        meas_loaded=True, mapping_done=True, coord_loaded=True,
        has_batch=False, has_component_type=True, n_selected=1
    )
    blocked = get_condition_blocked_ids(ctx)
    for chart in ("imr", "run_chart", "ewma", "cusum"):
        assert chart in blocked, f"{chart} should be blocked without batch"
