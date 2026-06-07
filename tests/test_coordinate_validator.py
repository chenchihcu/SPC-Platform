from app.data.mapping.mapping_result import MappingResult
from app.data.validation.coordinate_validator import validate_coordinate_minimum


def test_coordinate_validator_ok():
    mapped = MappingResult(mapped_columns={"RefDes": "RefDes", "X": "X", "Y": "Y"}, missing_required=[], original_columns=["RefDes","X","Y"])
    ok, _ = validate_coordinate_minimum(mapped)
    assert ok
