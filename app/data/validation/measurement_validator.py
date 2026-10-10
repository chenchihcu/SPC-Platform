import pandas as pd

from app.data.mapping.schema_mapper import SchemaMapper


def validate_measurement_minimum(mapped_result) -> tuple[bool, str]:
    """Compatibility wrapper over the authoritative SchemaMapper contract."""
    mapped = getattr(mapped_result, "mapped_columns", {})
    valid, missing = SchemaMapper.validate_measurement_schema(
        pd.DataFrame(columns=list(mapped))
    )
    if valid:
        return True, "OK"
    legacy_messages = {
        "RefDes": "缺少 RefDes",
        "Measurement (Volume, Area, or Height)": "缺少量測欄位",
        "Identifier (BoardNo or Time)": "缺少樣本識別欄位",
    }
    return False, legacy_messages.get(missing[0], f"缺少欄位: {missing[0]}")
