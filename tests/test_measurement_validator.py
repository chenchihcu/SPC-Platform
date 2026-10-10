import pytest
import pandas as pd

from app.data.mapping.mapping_result import MappingResult
from app.data.mapping.schema_mapper import SchemaMapper
from app.data.validation.measurement_validator import validate_measurement_minimum


def test_measurement_validator_ok():
    mapped = MappingResult(mapped_columns={"RefDes": "RefDes", "BoardNo": "BoardNo", "Volume": "Volume"}, missing_required=[], original_columns=["RefDes","BoardNo","Volume"])
    ok, _ = validate_measurement_minimum(mapped)
    assert ok


@pytest.mark.parametrize(
    "columns",
    [
        ["RefDes", "BoardNo", "Volume"],
        ["RefDes", "Time", "Area"],
        ["BoardNo", "Volume"],
        ["RefDes", "BoardNo"],
        ["RefDes", "Height"],
    ],
)
def test_measurement_validator_delegates_schema_mapper_contract(columns):
    mapped = MappingResult(
        mapped_columns={column: column for column in columns},
        missing_required=[],
        original_columns=columns,
    )
    legacy_valid, _ = validate_measurement_minimum(mapped)
    mapper_valid, _ = SchemaMapper.validate_measurement_schema(pd.DataFrame(columns=columns))
    assert legacy_valid is mapper_valid
