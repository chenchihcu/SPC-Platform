import pytest
import pandas as pd

from app.data.mapping.mapping_result import MappingResult
from app.data.mapping.schema_mapper import SchemaMapper
from app.data.validation.coordinate_validator import validate_coordinate_minimum


def test_coordinate_validator_ok():
    mapped = MappingResult(mapped_columns={"RefDes": "RefDes", "X": "X", "Y": "Y"}, missing_required=[], original_columns=["RefDes","X","Y"])
    ok, _ = validate_coordinate_minimum(mapped)
    assert ok


@pytest.mark.parametrize(
    "columns",
    [
        ["RefDes", "X", "Y"],
        ["RefDes", "X"],
        ["X", "Y"],
        [],
    ],
)
def test_coordinate_validator_delegates_schema_mapper_contract(columns):
    mapped = MappingResult(
        mapped_columns={column: column for column in columns},
        missing_required=[],
        original_columns=columns,
    )
    legacy_valid, _ = validate_coordinate_minimum(mapped)
    mapper_valid, _ = SchemaMapper.validate_coordinate_schema(pd.DataFrame(columns=columns))
    assert legacy_valid is mapper_valid
