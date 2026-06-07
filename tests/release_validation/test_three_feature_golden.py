"""Triple-feature analysis path on joined normal_baseline golden data."""

from __future__ import annotations

from pathlib import Path

from tests.release_validation.helpers.three_feature_payload import (
    THREE_FEATURES,
    load_three_feature_payload_from_golden,
)


def test_three_feature_payload_has_core_engines(golden_root: Path) -> None:
    payload, _spec = load_three_feature_payload_from_golden(golden_root)
    assert payload["selected_features"] == THREE_FEATURES
    for key in ("anomaly_3f", "consistency_3f", "parallel_coord", "pass_fail_matrix"):
        assert payload.get(key) is not None, f"missing {key}"
    assert set((payload.get("parameters") or {}).keys()) == {"Volume", "Area", "Height"}


def test_three_feature_correlation_matrix_populated(golden_root: Path) -> None:
    payload, _spec = load_three_feature_payload_from_golden(golden_root)
    cm = payload.get("correlation_matrix")
    assert cm is not None
    meta = cm.get("metadata") or {}
    assert meta.get("is_valid") is True
