from dataclasses import dataclass
from typing import Optional

@dataclass
class MappingResult:
    mapped_columns: dict
    missing_required: list[str]
    original_columns: list[str]

@dataclass
class RelationReport:
    matched_count: int
    unmatched_count: int
    match_rate: float
    invalid_refdes: list[str]
    duplicate_refdes: list[str]

@dataclass
class WorkorderRecord:
    workorder_no: str
    solder_paste_lot: Optional[str] = None
    pcb_datecode: Optional[str] = None
    line_name: Optional[str] = None
