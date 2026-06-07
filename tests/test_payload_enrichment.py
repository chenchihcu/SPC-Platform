"""Tests for statistical_signals + enrich_analysis_payload wiring."""
from __future__ import annotations

import pandas as pd

from app.analytics.statistical_signals import (
    STATISTICAL_SIGNALS_SCHEMA_VERSION,
    build_statistical_signals,
)
from app.viewmodels.chart_analysis_viewmodel import compute_analysis_payload


def _minimal_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "RefDes": ["R1"] * 30,
            "BoardNo": [1] * 30,
            "Volume": [float(i % 10 + 90) for i in range(30)],
            "Area": [float(10 + (i % 5)) for i in range(30)],
            "Height": [float(0.1 + (i % 3) * 0.01) for i in range(30)],
            "X": [float(i % 6) for i in range(30)],
            "Y": [float(i // 6) for i in range(30)],
        }
    )


def test_enrich_adds_schema_versioned_signals() -> None:
    df = _minimal_df()
    wo = {
        "volume": {"usl": "120", "lsl": "80", "target": "100"},
        "area": {"usl": "20", "lsl": "5", "target": "10"},
        "height": {"usl": "0.2", "lsl": "0.05", "target": "0.12"},
    }
    payload, err = compute_analysis_payload(
        df,
        ["Volume"],
        120.0,
        80.0,
        100.0,
        workorder_spec=wo,
        workorder_master={},
    )
    assert err is None
    assert payload is not None
    sig = payload.get("statistical_signals")
    assert isinstance(sig, dict)
    assert sig.get("schema_version") == STATISTICAL_SIGNALS_SCHEMA_VERSION
    assert "capabilities" in sig
    assert payload.get("summary", {}).get("process", {}).get("diagnosis_engine")
    assert payload.get("summary", {}).get("process", {}).get("process_risk")
    assert payload.get("knowledge_inference")


def test_build_statistical_signals_without_summary() -> None:
    """Empty payload should not crash."""
    sig = build_statistical_signals({})
    assert sig.get("schema_version") == STATISTICAL_SIGNALS_SCHEMA_VERSION
