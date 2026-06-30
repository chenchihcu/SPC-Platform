import os
import re
from typing import Any, Dict, List, Tuple

import pandas as pd

from app.data.mapping.schema_mapper import SchemaMapper


ZHEN_SHUN_FENG_SUPPLIER = "振順豐"
ZHEN_SHUN_FENG_TOP_PROFILE = "zhen_shun_feng_top_mm"
_ZSF_REQUIRED_ID_COLUMNS = ("Component ID", "PAD ID")
_ZSF_METRICS = ("Volume", "Height", "Area")
_ZSF_METRIC_PATTERN = re.compile(r"^(Volume|Height|Area)\(mm\)(\d+)$")


def _normalize_supplier(value: str | None) -> str:
    return str(value or "").strip()


class MeasurementLoader:
    """
    Loads and validates measurement CSV files.
    """
    def __init__(self):
        self.last_metadata = {}

    def _fail(self, filepath: str, error: str, **extra: Any) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        self.last_metadata = {
            "filepath": filepath,
            "is_valid": False,
            "error": error,
            **extra,
        }
        return pd.DataFrame(), self.last_metadata

    @staticmethod
    def _analyze_zhen_shun_feng_signature(df: pd.DataFrame) -> Tuple[bool, List[str], List[str]]:
        columns = [str(c).strip() for c in df.columns]
        column_set = set(columns)
        missing = [c for c in _ZSF_REQUIRED_ID_COLUMNS if c not in column_set]
        boards_by_metric: Dict[str, set[str]] = {metric: set() for metric in _ZSF_METRICS}

        for col in columns:
            match = _ZSF_METRIC_PATTERN.fullmatch(col)
            if match:
                metric, board_no = match.groups()
                boards_by_metric[metric].add(board_no)

        all_boards = set().union(*boards_by_metric.values())
        if not all_boards:
            missing.append("Volume(mm)<n>/Height(mm)<n>/Area(mm)<n>")
        for board_no in sorted(all_boards, key=int):
            for metric in _ZSF_METRICS:
                expected = f"{metric}(mm){board_no}"
                if board_no not in boards_by_metric[metric]:
                    missing.append(expected)

        return not missing, missing, sorted(all_boards, key=int)

    @staticmethod
    def _should_use_zhen_shun_feng_profile(
        filepath: str,
        supplier: str,
        df: pd.DataFrame,
    ) -> Tuple[bool, bool, List[str], List[str], str]:
        signature_ok, missing, board_numbers = MeasurementLoader._analyze_zhen_shun_feng_signature(df)
        normalized_supplier = _normalize_supplier(supplier)
        supplier_matches = normalized_supplier == ZHEN_SHUN_FENG_SUPPLIER
        path_matches = ZHEN_SHUN_FENG_SUPPLIER in str(filepath)

        if supplier_matches:
            return True, signature_ok, missing, board_numbers, "supplier"
        if not normalized_supplier and path_matches and signature_ok:
            return True, True, [], board_numbers, "path"
        return False, signature_ok, missing, board_numbers, ""

    def _load_zhen_shun_feng_top_format(
        self,
        filepath: str,
        df: pd.DataFrame,
        *,
        activation_source: str,
        missing_signature: List[str],
        board_numbers: List[str],
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        if missing_signature:
            return self._fail(
                filepath,
                "振順豐 TOP CSV signature error: missing required columns "
                + ", ".join(missing_signature),
                vendor_profile=ZHEN_SHUN_FENG_TOP_PROFILE,
                missing_required=missing_signature,
            )

        raw_rows = len(df)
        raw_columns = len(df.columns)
        frames: List[pd.DataFrame] = []
        for board_no in board_numbers:
            cols = [
                "Component ID",
                "PAD ID",
                f"Volume(mm){board_no}",
                f"Height(mm){board_no}",
                f"Area(mm){board_no}",
            ]
            temp = df[cols].copy()
            temp = temp.rename(
                columns={
                    "Component ID": "RefDes",
                    "PAD ID": "Pad",
                    f"Volume(mm){board_no}": "Volume",
                    f"Height(mm){board_no}": "Height",
                    f"Area(mm){board_no}": "Area",
                }
            )
            temp["BoardNo"] = f"Board_{board_no}"
            frames.append(temp)

        mapped_df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        mapped_df = self._finalize_mapped_measurements(mapped_df)
        is_valid, missing_cols = SchemaMapper.validate_measurement_schema(mapped_df)
        measurement_units = {"Volume": "mm", "Height": "mm", "Area": "mm"}

        self.last_metadata = {
            "filepath": filepath,
            "total_rows": len(mapped_df),
            "raw_rows": raw_rows,
            "raw_columns": raw_columns,
            "board_count": len(board_numbers),
            "mapping": {
                "RefDes": "Component ID",
                "Pad": "PAD ID",
                "Volume": "Volume(mm)",
                "Height": "Height(mm)",
                "Area": "Area(mm)",
                "BoardNo": "BoardNo",
            },
            "unmapped_columns": [],
            "is_valid": is_valid,
            "missing_required": missing_cols,
            "vendor_profile": ZHEN_SHUN_FENG_TOP_PROFILE,
            "vendor_profile_activation": activation_source,
            "measurement_units": measurement_units,
        }
        return mapped_df, self.last_metadata

    def _melt_wide_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detects wide-format machine exports (e.g. Component ID, Height(%)1, Volume(%)1...)
        and melts them into standard long format tracking Boards as 'BoardNo'.
        """
        import re
        cols = df.columns.tolist()

        # Check if wide format: suffix like "1", "2" on typical metric names
        metrics = ["Volume", "Area", "Height", "Result"]
        is_wide = any(any(m in c and c[-1].isdigit() for m in metrics) for c in cols)

        if not is_wide:
            return df

        id_vars = [c for c in cols if not any(c.startswith(m) or m in c for m in metrics if c[-1].isdigit())]

        long_frames = []
        numbers = set()
        for c in cols:
            match = re.search(r'(\d+)$', c)
            if match and any(m in c for m in metrics):
                numbers.add(match.group(1))

        for num in sorted(numbers, key=int):
            num_str = str(num)

            board_cols = {}
            for c in cols:
                m = re.search(r'(\d+)$', c)
                if m and m.group(1) == num_str and c not in id_vars and any(met in c for met in metrics):
                    board_cols[c] = re.sub(r'\d+$', '', c)

            if not board_cols:
                continue

            # Filter rows to only those that actually have data for this iter to save memory
            subset_cols = id_vars + list(board_cols.keys())
            # Safely grab available columns only
            subset_cols = [c for c in subset_cols if c in df.columns]

            temp_df = df[subset_cols].copy()
            temp_df = temp_df.rename(columns=board_cols)
            temp_df["BoardNo"] = f"Board_{num_str}"

            long_frames.append(temp_df)

        if long_frames:
            return pd.concat(long_frames, ignore_index=True)

        return df

    @staticmethod
    def _finalize_mapped_measurements(mapped_df: pd.DataFrame) -> pd.DataFrame:
        # Data cleaning for RefDes
        if "RefDes" in mapped_df.columns:
            mapped_df["RefDes"] = mapped_df["RefDes"].astype(str).str.strip()

            # Auto-synthesize pseudo PartType from RefDes (e.g., C131_1 -> C)
            if "PartType" not in mapped_df.columns:
                mapped_df["PartType"] = mapped_df["RefDes"].str.extract(r"([a-zA-Z]+)")[0]
                mapped_df["PartType"] = mapped_df["PartType"].fillna("UNKNOWN")

        # Data cleaning for BoardNo
        if "BoardNo" in mapped_df.columns:
            mapped_df["BoardNo"] = mapped_df["BoardNo"].astype(str).str.strip()
        if "Pad" in mapped_df.columns:
            mapped_df["Pad"] = mapped_df["Pad"].astype(str).str.strip()

        # Type casting for numeric measurements
        measurements = ["Volume", "Area", "Height", "XOffset", "YOffset"]
        for col in measurements:
            if col in mapped_df.columns:
                mapped_df[col] = pd.to_numeric(mapped_df[col], errors="coerce")

        return mapped_df

    def load(self, filepath: str, supplier: str = "") -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Loads measurement CSV, maps fields, validates and returns (DataFrame, metadata).
        """
        if not os.path.exists(filepath):
             return pd.DataFrame(), {"is_valid": False, "error": f"File not found: {filepath}"}

        try:
            raw_df = pd.read_csv(filepath, encoding="utf-8")
            raw_df.columns = raw_df.columns.astype(str).str.strip()

            should_use_zsf, signature_ok, missing_signature, board_numbers, activation_source = (
                self._should_use_zhen_shun_feng_profile(filepath, supplier, raw_df)
            )
            if should_use_zsf:
                return self._load_zhen_shun_feng_top_format(
                    filepath,
                    raw_df,
                    activation_source=activation_source,
                    missing_signature=[] if signature_ok else missing_signature,
                    board_numbers=board_numbers,
                )

            # Auto-Melt wide outputs to Long format
            df = self._melt_wide_format(raw_df)

            mapped_df, mapping, unmapped = SchemaMapper.map_columns(df, SchemaMapper.MEASUREMENT_ALIASES)

            mapped_df = self._finalize_mapped_measurements(mapped_df)

            is_valid, missing_cols = SchemaMapper.validate_measurement_schema(mapped_df)

            self.last_metadata = {
                "filepath": filepath,
                "total_rows": len(df),
                "raw_rows": len(raw_df),
                "raw_columns": len(raw_df.columns),
                "board_count": int(mapped_df["BoardNo"].nunique()) if "BoardNo" in mapped_df.columns else 0,
                "mapping": mapping,
                "unmapped_columns": unmapped,
                "is_valid": is_valid,
                "missing_required": missing_cols,
                "vendor_profile": "",
                "measurement_units": {},
            }

            return mapped_df, self.last_metadata

        except (UnicodeDecodeError, OSError) as e:
            # IO / 文字編碼錯誤：標記為檔案層級錯誤
            return self._fail(filepath, f"Measurement file read failed: {e}")
        except ValueError as e:
            # 例如數值轉換或 schema 映射問題
            return self._fail(filepath, f"Measurement schema/parse error: {e}")
