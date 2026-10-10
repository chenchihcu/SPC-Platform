import pandas as pd

from app.data.mapping.schema_mapper import SchemaMapper


def validate_coordinate_minimum(mapped_result) -> tuple[bool, str]:
    """Compatibility wrapper over the authoritative SchemaMapper contract."""
    mapped = getattr(mapped_result, "mapped_columns", {})
    valid, missing = SchemaMapper.validate_coordinate_schema(
        pd.DataFrame(columns=list(mapped))
    )
    if valid:
        return True, "OK"
    if missing:
        return False, f"缺少欄位: {', '.join(missing)}"
    return False, "缺少欄位"
