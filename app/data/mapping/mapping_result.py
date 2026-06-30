from dataclasses import dataclass

@dataclass
class MappingResult:
    mapped_columns: dict[str, str]
    missing_required: list[str]
    original_columns: list[str]
