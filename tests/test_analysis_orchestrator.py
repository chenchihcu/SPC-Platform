import pandas as pd

from app.data.session_store import SessionStore, _analysis_cache_key
from app.services.analysis_context import AnalysisFilterContext, AnalysisRunContext
from app.services.analysis_orchestrator import (
    STATUS_CACHED,
    STATUS_ERROR,
    STATUS_MISSING_FEATURE,
    STATUS_READY,
    AnalysisOrchestrator,
)
from app.utils.constants import FILTER_ALL, RANGE_ALL_BOARDS


def _fresh_store() -> SessionStore:
    store = SessionStore()
    store.clear()
    return store


def _manual_spec() -> dict:
    return {
        "volume": {"usl": "120", "lsl": "80", "target": "100"},
        "area": {"usl": "120", "lsl": "80", "target": "100"},
        "height": {"usl": "120", "lsl": "80", "target": "100"},
    }


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "BoardNo": ["B1", "B1", "B2", "B2"],
            "RefDes": ["R1", "R2", "R1", "R2"],
            "PartType": ["0402", "0402", "0603", "0603"],
            "Volume": [100.0, 101.0, 99.0, 102.0],
        }
    )


def test_prepare_refresh_returns_missing_feature_status() -> None:
    store = _fresh_store()
    store.meas_df = _sample_df()
    orchestrator = AnalysisOrchestrator()

    result = orchestrator.prepare_refresh(
        store=store,
        selected_features=[],
        range_mode=RANGE_ALL_BOARDS,
        board_specify="",
        refdes=FILTER_ALL,
        part_type=FILTER_ALL,
        optional_filters={},
        manual_workorder_spec=_manual_spec(),
    )

    assert result.status == STATUS_MISSING_FEATURE
    assert "至少選擇一個量測特徵" in result.message


def test_prepare_refresh_ready_with_manual_spec() -> None:
    store = _fresh_store()
    store.meas_df = _sample_df()
    orchestrator = AnalysisOrchestrator()

    result = orchestrator.prepare_refresh(
        store=store,
        selected_features=["Volume"],
        range_mode=RANGE_ALL_BOARDS,
        board_specify="",
        refdes=FILTER_ALL,
        part_type=FILTER_ALL,
        optional_filters={},
        manual_workorder_spec=_manual_spec(),
    )

    assert result.status == STATUS_READY
    assert result.filtered_df is not None
    assert len(result.filtered_df) == 4
    assert result.usl == 120.0
    assert result.lsl == 80.0
    assert result.target == 100.0
    assert result.filter_context is not None
    assert result.filter_context.batch == RANGE_ALL_BOARDS
    assert result.run_context is not None
    assert result.run_context.selected_features == ("Volume",)
    assert store.workorder_spec.get("volume", {}).get("usl") == "120"


def test_prepare_refresh_returns_cached_when_key_exists() -> None:
    store = _fresh_store()
    store.meas_df = _sample_df()
    orchestrator = AnalysisOrchestrator()

    first = orchestrator.prepare_refresh(
        store=store,
        selected_features=["Volume"],
        range_mode=RANGE_ALL_BOARDS,
        board_specify="",
        refdes=FILTER_ALL,
        part_type=FILTER_ALL,
        optional_filters={},
        manual_workorder_spec=_manual_spec(),
    )
    assert first.status == STATUS_READY
    cached_payload = {"selected_features": ["Volume"], "metadata": {"is_valid": True}}
    store._analysis_cache[first.cache_key] = cached_payload

    second = orchestrator.prepare_refresh(
        store=store,
        selected_features=["Volume"],
        range_mode=RANGE_ALL_BOARDS,
        board_specify="",
        refdes=FILTER_ALL,
        part_type=FILTER_ALL,
        optional_filters={},
        manual_workorder_spec=_manual_spec(),
    )
    assert second.status == STATUS_CACHED
    assert second.cached_payload is cached_payload


def test_cache_payload_uses_run_context_for_stable_key() -> None:
    store = _fresh_store()
    store.workorder_spec = _manual_spec()
    orchestrator = AnalysisOrchestrator()
    payload = {"selected_features": ["Volume"], "metadata": {"is_valid": True}}
    run_context = AnalysisRunContext(
        selected_features=("Volume",),
        filters=AnalysisFilterContext(
            batch="B2",
            refdes="R1",
            part_type="0402",
            product="P100",
            time_start="2026-03-01",
            time_end="2026-03-31",
            line="L3",
        ),
        spec_version="spec-v1",
    )

    key = orchestrator.cache_payload(store, payload, run_context=run_context)

    expected = _analysis_cache_key(
        ["Volume"],
        "B2",
        "R1",
        "0402",
        product="P100",
        time_start="2026-03-01",
        time_end="2026-03-31",
        line="L3",
        spec_version="spec-v1",
    )
    assert key == expected
    assert store._analysis_cache[key] is payload


def test_prepare_refresh_invalid_spec_returns_error() -> None:
    store = _fresh_store()
    store.meas_df = _sample_df()
    orchestrator = AnalysisOrchestrator()
    bad_spec = _manual_spec()
    bad_spec["volume"]["usl"] = "abc"

    result = orchestrator.prepare_refresh(
        store=store,
        selected_features=["Volume"],
        range_mode=RANGE_ALL_BOARDS,
        board_specify="",
        refdes=FILTER_ALL,
        part_type=FILTER_ALL,
        optional_filters={},
        manual_workorder_spec=bad_spec,
    )

    assert result.status == STATUS_ERROR
    assert "工單規格" in result.message
