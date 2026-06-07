from app.data.mapping.mapping_result import MappingResult
from app.data.validation.measurement_validator import validate_measurement_minimum


def test_measurement_validator_ok():
    mapped = MappingResult(mapped_columns={"RefDes": "RefDes", "BoardNo": "BoardNo", "Volume": "Volume"}, missing_required=[], original_columns=["RefDes","BoardNo","Volume"])
    ok, _ = validate_measurement_minimum(mapped)
    assert ok
