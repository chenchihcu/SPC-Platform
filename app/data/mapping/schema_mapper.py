import pandas as pd
from typing import Dict, List, Tuple

class SchemaMapper:
    """
    Handles alias mapping and required column validation for CSV data.
    Ensures that variation in CSV header names from different machines
    is mapped to standard internal data contracts.
    """
    COORDINATE_ALIASES = {
        "RefDes": ["RefDes", "Ref", "Component", "Component ID", "Comp ID", "Designator", "Part", "Cmp"],
        "X": ["X", "Center-X", "PosX", "X-Loc"],
        "Y": ["Y", "Center-Y", "PosY", "Y-Loc"],
        "Layer": ["Layer", "Side", "Top/Bottom"],
        "Rotation": ["Rotation", "Rot", "Angle"],
        "PartType": ["PartType", "Type", "Package", "Footprint"],
        "Width": ["Width", "W"],
        "Height": ["Height", "H", "Length", "L"]
    }

    MEASUREMENT_ALIASES = {
        "RefDes": ["RefDes", "Ref", "Component", "Component ID", "Comp ID", "Designator", "Part", "Cmp"],
        "BoardNo": ["BoardNo", "BoardID", "Panel", "PanelID", "Barcode", "PCBID", "Board ID", "PCB ID"],
        "Time": ["Time", "Timestamp", "InspectTime", "Date"],
        "Volume": ["Volume", "Vol", "Volume(%)", "Vol(%)"],
        "Area": ["Area", "A", "Area(%)"],
        "Height": ["Height", "H", "Height(um)", "Height(%)", "Z"],
        "XOffset": ["XOffset", "OffsetX", "X-Offset"],
        "YOffset": ["YOffset", "OffsetY", "Y-Offset"],
        "Result": ["Result", "Judge", "Status", "Pass/Fail"]
    }

    @staticmethod
    def map_columns(df: pd.DataFrame, alias_dict: Dict[str, List[str]]) -> Tuple[pd.DataFrame, Dict[str, str], List[str]]:
        """
        Maps dataframe columns based on alias dictionary.
        Returns:
            - Mapped DataFrame
            - Mapping dictionary {standard_name: original_name}
            - List of unmapped original columns
        """
        mapped_df = df.copy()
        # Clean column names in original df (strip whitespace)
        mapped_df.columns = mapped_df.columns.astype(str).str.strip()

        mapping_result = {}
        used_columns = set()

        for std_col, aliases in alias_dict.items():
            for alias in aliases:
                # Case-insensitive match check
                matched_col = next((c for c in mapped_df.columns if c.lower() == alias.lower() and c not in used_columns), None)
                if matched_col:
                    mapped_df.rename(columns={matched_col: std_col}, inplace=True)
                    mapping_result[std_col] = matched_col
                    used_columns.add(std_col)
                    break

        unmapped_cols = [c for c in df.columns if str(c).strip() not in mapping_result.values()]

        return mapped_df, mapping_result, unmapped_cols

    @staticmethod
    def validate_coordinate_schema(df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Validates if coordinate dataframe has minimum required columns.
        Required: RefDes, X, Y
        """
        required = ["RefDes", "X", "Y"]
        missing = [col for col in required if col not in df.columns]
        return len(missing) == 0, missing

    @staticmethod
    def validate_measurement_schema(df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Validates if measurement dataframe has minimum required columns.
        Required: RefDes, at least one measurement (Volume/Area/Height), BoardNo or Time
        """
        missing = []
        if "RefDes" not in df.columns:
            missing.append("RefDes")

        measurements = ["Volume", "Area", "Height"]
        if not any(m in df.columns for m in measurements):
            missing.append("Measurement (Volume, Area, or Height)")

        if "BoardNo" not in df.columns and "Time" not in df.columns:
            missing.append("Identifier (BoardNo or Time)")

        return len(missing) == 0, missing
