from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class AnalysisFilterContext:
    batch: str = ""
    refdes: str = ""
    part_type: str = ""
    product: Optional[str] = None
    time_start: Optional[str] = None
    time_end: Optional[str] = None
    line: Optional[str] = None


@dataclass(frozen=True)
class AnalysisRunContext:
    selected_features: Tuple[str, ...]
    filters: AnalysisFilterContext
    spec_version: str = ""
