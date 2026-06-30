import pandas as pd
from typing import Dict, Any, Tuple
from app.data.mapping.schema_mapper import SchemaMapper
import os

class CoordinateLoader:
    """
    Loads and validates coordinate CSV files.
    """
    def __init__(self):
        self.last_metadata = {}

    def _fail(self, filepath: str, error: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        self.last_metadata = {
            "filepath": filepath,
            "is_valid": False,
            "error": error,
        }
        return pd.DataFrame(), self.last_metadata

    def load(self, filepath: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Loads coordinate CSV, maps fields, validates and returns (DataFrame, metadata).
        """
        if not os.path.exists(filepath):
             return pd.DataFrame(), {"is_valid": False, "error": f"File not found: {filepath}"}

        try:
            df = pd.read_csv(filepath, encoding="utf-8")

            mapped_df, mapping, unmapped = SchemaMapper.map_columns(df, SchemaMapper.COORDINATE_ALIASES)

            # Data cleaning for RefDes (strip whitespaces) to avoid pseudo-mismatch in joining
            if "RefDes" in mapped_df.columns:
                mapped_df["RefDes"] = mapped_df["RefDes"].astype(str).str.strip()

            # Type casting for numeric coordinates
            for col in ["X", "Y", "Rotation", "Width", "Height"]:
                if col in mapped_df.columns:
                    mapped_df[col] = pd.to_numeric(mapped_df[col], errors='coerce')

            is_valid, missing_cols = SchemaMapper.validate_coordinate_schema(mapped_df)

            self.last_metadata = {
                "filepath": filepath,
                "total_rows": len(df),
                "mapping": mapping,
                "unmapped_columns": unmapped,
                "is_valid": is_valid,
                "missing_required": missing_cols
            }

            return mapped_df, self.last_metadata

        except (UnicodeDecodeError, OSError) as e:
            # IO / 文字編碼問題：明確標記為檔案層級錯誤
            return self._fail(filepath, f"Coordinate file read failed: {e}")
        except ValueError as e:
            # 例如數值轉換或 schema mapping 失敗
            return self._fail(filepath, f"Coordinate schema/parse error: {e}")
