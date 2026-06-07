import pandas as pd

from app.data.mapping.schema_mapper import SchemaMapper


def test_coordinate_schema_mapper():
    df = pd.DataFrame(columns=["RefDes", "X", "Y"])
    mapped_df, mapping, unmapped = SchemaMapper.map_columns(df, SchemaMapper.COORDINATE_ALIASES)
    valid, missing = SchemaMapper.validate_coordinate_schema(mapped_df)
    assert missing == []
    assert valid is True


def test_measurement_schema_mapper():
    df = pd.DataFrame(columns=["RefDes", "BoardNo", "Volume"])
    mapped_df, mapping, unmapped = SchemaMapper.map_columns(df, SchemaMapper.MEASUREMENT_ALIASES)
    assert "RefDes" in mapping
    valid, missing = SchemaMapper.validate_measurement_schema(mapped_df)
    assert valid is True
