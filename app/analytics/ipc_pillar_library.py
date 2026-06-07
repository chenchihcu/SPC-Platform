"""
IPC/J-STD four-pillar reference library loader and query helpers.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

VALID_PILLARS = ("dfm", "printing_spi", "bga_fa", "jstd_material")
VALID_RISK_LEVELS = ("H", "M", "L")
VALID_REVIEW_STATUS = ("reviewed", "draft")

REQUIRED_FIELDS = (
    "id",
    "pillar",
    "topic",
    "failure_mode",
    "ipc_jstd_refs",
    "key_parameters",
    "detection_signals",
    "fa_evidence",
    "control_actions",
    "risk_level",
    "keywords",
    "revision",
    "updated_at",
    "review_status",
)


def _data_path() -> Path:
    root = Path(__file__).resolve().parent.parent.parent
    return root / "data" / "ipc_jstd_pillar_seed.json"


def _is_non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_non_empty_str_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(_is_non_empty_str(v) for v in value)


def validate_entry(entry: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    for field in REQUIRED_FIELDS:
        if field not in entry:
            errors.append(f"missing:{field}")

    if errors:
        return errors

    if not _is_non_empty_str(entry.get("id")):
        errors.append("invalid:id")
    if entry.get("pillar") not in VALID_PILLARS:
        errors.append("invalid:pillar")
    if not _is_non_empty_str(entry.get("topic")):
        errors.append("invalid:topic")
    if not _is_non_empty_str(entry.get("failure_mode")):
        errors.append("invalid:failure_mode")
    if not _is_non_empty_str_list(entry.get("ipc_jstd_refs")):
        errors.append("invalid:ipc_jstd_refs")
    if not _is_non_empty_str_list(entry.get("key_parameters")):
        errors.append("invalid:key_parameters")
    if not _is_non_empty_str_list(entry.get("detection_signals")):
        errors.append("invalid:detection_signals")
    if not _is_non_empty_str_list(entry.get("fa_evidence")):
        errors.append("invalid:fa_evidence")
    if not _is_non_empty_str_list(entry.get("control_actions")):
        errors.append("invalid:control_actions")
    if entry.get("risk_level") not in VALID_RISK_LEVELS:
        errors.append("invalid:risk_level")
    if not _is_non_empty_str_list(entry.get("keywords")):
        errors.append("invalid:keywords")
    if not _is_non_empty_str(entry.get("revision")):
        errors.append("invalid:revision")
    if not _is_non_empty_str(entry.get("updated_at")):
        errors.append("invalid:updated_at")
    if entry.get("review_status") not in VALID_REVIEW_STATUS:
        errors.append("invalid:review_status")

    return errors


def load_all_entries() -> List[Dict[str, Any]]:
    path = _data_path()
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as file:
            payload = json.load(file)
    except (json.JSONDecodeError, OSError):
        return []

    raw_entries = payload.get("entries", [])
    if not isinstance(raw_entries, list):
        return []
    return [entry for entry in raw_entries if isinstance(entry, dict)]


def list_validation_errors(entries: Sequence[Mapping[str, Any]] | None = None) -> Dict[str, List[str]]:
    source = entries if entries is not None else load_all_entries()
    result: Dict[str, List[str]] = {}
    for idx, entry in enumerate(source):
        entry_id = str(entry.get("id") or f"row_{idx}")
        errors = validate_entry(entry)
        if errors:
            result[entry_id] = errors
    return result


def list_entries(
    *,
    pillar: str | None = None,
    keyword: str = "",
    risk_level: str | None = None,
    review_status: str | None = None,
) -> List[Dict[str, Any]]:
    entries = load_all_entries()
    key = keyword.strip().lower()
    filtered: List[Dict[str, Any]] = []
    for entry in entries:
        if pillar and entry.get("pillar") != pillar:
            continue
        if risk_level and entry.get("risk_level") != risk_level:
            continue
        if review_status and entry.get("review_status") != review_status:
            continue
        if key:
            haystack = " ".join(
                [
                    str(entry.get("topic", "")),
                    str(entry.get("failure_mode", "")),
                    " ".join(entry.get("keywords", [])),
                    " ".join(entry.get("ipc_jstd_refs", [])),
                ]
            ).lower()
            if key not in haystack:
                continue
        filtered.append(dict(entry))
    return filtered


def count_by_pillar(entries: Sequence[Mapping[str, Any]] | None = None) -> Dict[str, int]:
    source = entries if entries is not None else load_all_entries()
    counts = {pillar: 0 for pillar in VALID_PILLARS}
    for entry in source:
        pillar = str(entry.get("pillar", ""))
        if pillar in counts:
            counts[pillar] += 1
    return counts
