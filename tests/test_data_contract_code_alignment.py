"""A (ext): docs/specs/data_contract.md examples align with SchemaMapper + ORDER_COL_PRIORITY (single-source drift guard)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from app.data.mapping.schema_mapper import SchemaMapper
from app.utils.constants import FEATURE_COLUMNS, ORDER_COL_PRIORITY


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_data_contract_markdown_exists() -> None:
    p = _repo_root() / "docs" / "specs" / "data_contract.md"
    assert p.is_file(), p
    body = p.read_text(encoding="utf-8")
    assert "最低必要欄位" in body
    assert "RefDes" in body and "BoardNo" in body


@pytest.mark.parametrize(
    ("standard", "doc_example_alias"),
    [
        ("RefDes", "Ref"),
        ("RefDes", "Component"),
        ("BoardNo", "Panel"),
        ("Volume", "Vol"),
        ("Area", "A"),
        ("Height", "H"),
        ("X", "Center-X"),
        ("Y", "Center-Y"),
    ],
)
def test_schema_mapper_includes_data_contract_table_examples(standard: str, doc_example_alias: str) -> None:
    meas = SchemaMapper.MEASUREMENT_ALIASES.get(standard)
    coord = SchemaMapper.COORDINATE_ALIASES.get(standard)
    candidates = meas or coord
    assert candidates is not None, standard
    lowered = {str(a).strip().lower() for a in candidates}
    assert doc_example_alias.lower() in lowered, (standard, doc_example_alias, candidates)


def test_order_col_priority_lists_time_like_before_board_identifiers() -> None:
    """Keep time-first ordering for SPC trend charts (see constants.py comment)."""
    time_like = ("Time", "Timestamp", "timestamp", "DateTime")
    assert ORDER_COL_PRIORITY[: len(time_like)] == time_like
    assert "BoardNo" in ORDER_COL_PRIORITY
    assert "PanelId" in ORDER_COL_PRIORITY
    board_idx = ORDER_COL_PRIORITY.index("BoardNo")
    time_last_idx = len(time_like) - 1
    assert board_idx > time_last_idx


def test_feature_columns_match_measurement_family_names() -> None:
    assert FEATURE_COLUMNS == ["Volume", "Area", "Height"]
    assert set(FEATURE_COLUMNS) <= set(SchemaMapper.MEASUREMENT_ALIASES.keys())


def test_validate_coordinate_schema_matches_documented_minimum() -> None:
    ok, missing = SchemaMapper.validate_coordinate_schema(pd.DataFrame(columns=["RefDes", "X", "Y"]))
    assert ok and missing == []


def test_validate_measurement_schema_accepts_mapped_minimum_grid() -> None:
    df = pd.DataFrame(
        columns=["RefDes", "BoardNo", "Volume"],
        data=[["R1", "B1", 1.0]],
    )
    ok, missing = SchemaMapper.validate_measurement_schema(df)
    assert ok and missing == []
