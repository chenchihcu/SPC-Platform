"""Standard analytics-engine return shape for pytest."""

from __future__ import annotations

from typing import Any


def assert_engine_contract(result: dict[str, Any], expect_valid: bool) -> None:
    assert "chart_type" in result, "Missing key: chart_type"
    assert "data" in result, "Missing key: data"
    assert "statistics" in result, "Missing key: statistics"
    assert "metadata" in result, "Missing key: metadata"

    assert isinstance(result["chart_type"], str), "chart_type must be str"
    assert isinstance(result["data"], dict), "data must be dict"
    assert isinstance(result["statistics"], dict), "statistics must be dict"
    assert isinstance(result["metadata"], dict), "metadata must be dict"

    meta = result["metadata"]
    assert "is_valid" in meta, "metadata missing key: is_valid"
    assert isinstance(meta["is_valid"], bool), "metadata.is_valid must be bool"

    if not expect_valid:
        assert meta["is_valid"] is False, "Expected is_valid=False"
        assert result["data"] == {}, "On failure data must be {}"
        assert result["statistics"] == {}, "On failure statistics must be {}"
        assert meta.get("error"), "On failure metadata.error must be non-empty"

    if expect_valid:
        assert meta["is_valid"] is True, "Expected is_valid=True"
