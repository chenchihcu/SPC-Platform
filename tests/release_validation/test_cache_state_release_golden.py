"""H + I: analysis cache key stability and SessionStore isolation (golden-shaped session)."""

from __future__ import annotations

from pathlib import Path

from app.data.session_store import SessionStore, _analysis_cache_key
from app.services.analysis_orchestrator import (
    STATUS_CACHED,
    STATUS_READY,
    AnalysisOrchestrator,
)
from app.utils.constants import FILTER_ALL, RANGE_ALL_BOARDS
from tests.release_validation.helpers.golden_scenario import load_joined_normal_baseline


def test_analysis_cache_key_distinguishes_features_and_spec_token(golden_root: Path) -> None:
    _sdir, manifest, joined_df, spec = load_joined_normal_baseline(golden_root)
    store = SessionStore()
    store.clear()
    try:
        store.workorder_spec = spec
        tok = store.spec_cache_token(store.workorder_spec)
        k_vol = _analysis_cache_key(
            ["Volume"],
            RANGE_ALL_BOARDS,
            FILTER_ALL,
            FILTER_ALL,
            spec_version=tok,
        )
        k_area = _analysis_cache_key(
            ["Area"],
            RANGE_ALL_BOARDS,
            FILTER_ALL,
            FILTER_ALL,
            spec_version=tok,
        )
        assert k_vol != k_area
        store.workorder_spec = dict(spec)
        store.workorder_spec["volume"] = {**spec["volume"], "usl": "130"}
        tok2 = store.spec_cache_token(store.workorder_spec)
        k_vol2 = _analysis_cache_key(
            ["Volume"],
            RANGE_ALL_BOARDS,
            FILTER_ALL,
            FILTER_ALL,
            spec_version=tok2,
        )
        assert k_vol != k_vol2
    finally:
        store.clear()


def test_session_clear_wipes_analysis_cache(golden_root: Path) -> None:
    _sdir, _manifest, joined_df, spec = load_joined_normal_baseline(golden_root)
    store = SessionStore()
    store.clear()
    try:
        store.joined_df = joined_df
        store.workorder_spec = spec
        store.meas_meta = {"is_valid": True, "missing_required": []}
        store._analysis_cache["dummy"] = {"selected_features": ["Volume"]}
        store.clear()
        assert store._analysis_cache == {}
    finally:
        store.clear()


def test_prepare_refresh_hits_cache_with_golden_joined_df(golden_root: Path) -> None:
    """Same filters + spec token: second prepare returns STATUS_CACHED after manual cache insert."""
    _sdir, _manifest, joined_df, spec = load_joined_normal_baseline(golden_root)
    store = SessionStore()
    store.clear()
    orchestrator = AnalysisOrchestrator()
    try:
        store.joined_df = joined_df
        store.workorder_spec = spec
        store.meas_meta = {"is_valid": True, "missing_required": []}

        first = orchestrator.prepare_refresh(
            store=store,
            selected_features=["Volume"],
            range_mode=RANGE_ALL_BOARDS,
            board_specify="",
            refdes=FILTER_ALL,
            part_type=FILTER_ALL,
            optional_filters={},
            manual_workorder_spec={},
        )
        assert first.status == STATUS_READY
        fake = {"selected_features": ["Volume"], "summary": {"process": {"verdict": "cached_marker"}}}
        store._analysis_cache[first.cache_key] = fake

        second = orchestrator.prepare_refresh(
            store=store,
            selected_features=["Volume"],
            range_mode=RANGE_ALL_BOARDS,
            board_specify="",
            refdes=FILTER_ALL,
            part_type=FILTER_ALL,
            optional_filters={},
            manual_workorder_spec={},
        )
        assert second.status == STATUS_CACHED
        assert second.cached_payload is fake
    finally:
        store.clear()
