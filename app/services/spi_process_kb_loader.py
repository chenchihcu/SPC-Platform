"""
Load SPI process knowledge base JSON bundles from data/spi_process_kb/v1/.

Read-only; used by multi_signal_diagnosis and report builders.

**Authoritative human-maintained source** (not committed to the repo by default):
`SPI_製程對應知識庫_v1.0.xlsx` — import to JSON via ``scripts/import_spi_process_kb_xlsx.py``.
Shipped runtime data is the JSON bundle under ``data/spi_process_kb/v1/``; ``manifest.json``
may record ``source_xlsx_basename`` and ``source_xlsx_sha256`` after import.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_RELATIVE_DIR = Path("data") / "spi_process_kb" / "v1"

# Canonical workbook filename (v1 pipeline). Sheet names expected by the importer are
# documented in scripts/import_spi_process_kb_xlsx.py (--sheet-* defaults).
CANONICAL_SPI_KB_WORKBOOK_BASENAME = "SPI_製程對應知識庫_v1.0.xlsx"


@dataclass
class SPIProcessKnowledgeBase:
    """Normalized KB payload (empty lists if missing files)."""

    manifest: Dict[str, Any] = field(default_factory=dict)
    multi_signal_rules: List[Dict[str, Any]] = field(default_factory=list)
    dimension_abnormality_matrix: List[Dict[str, Any]] = field(default_factory=list)
    inspection_checklist: List[Dict[str, Any]] = field(default_factory=list)
    chart_signal_lookup: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class KBLoadReport:
    status: str  # "ok" | "partial" | "empty"
    messages: List[str] = field(default_factory=list)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def default_kb_dir() -> Path:
    return _repo_root() / DEFAULT_RELATIVE_DIR


def _read_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_multi_signal_rule(entry: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    required = (
        "rule_id",
        "signal_a",
        "signal_b",
        "spatial_temporal_condition",
        "trigger_description",
        "process_type_classification",
        "cause_hypotheses",
        "confidence_stars",
        "priority_inspection_items",
    )
    for k in required:
        if k not in entry:
            errs.append(f"missing:{k}")
    ch = entry.get("cause_hypotheses")
    if ch is not None and not isinstance(ch, list):
        errs.append("invalid:cause_hypotheses")
    cs = entry.get("confidence_stars")
    if cs is not None and not isinstance(cs, int):
        errs.append("invalid:confidence_stars")
    return errs


def validate_dimension_row(entry: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    for k in ("spi_dimension", "abnormality_type"):
        if k not in entry or not str(entry.get(k, "")).strip():
            errs.append(f"missing_or_empty:{k}")
    return errs


def validate_checklist_row(entry: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    for k in (
        "process_category",
        "inspection_item",
        "measurement_method",
        "normal_threshold",
        "priority_stars",
        "remarks",
    ):
        if k not in entry:
            errs.append(f"missing:{k}")
    ps = entry.get("priority_stars")
    if ps is not None and not isinstance(ps, int):
        errs.append("invalid:priority_stars")
    return errs


def validate_chart_lookup_row(entry: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    for k in (
        "chart_type",
        "observed_signal",
        "likely_cause_1",
        "likely_cause_2",
        "likely_cause_3",
        "rule_ids",
        "process_type",
        "urgency",
    ):
        if k not in entry:
            errs.append(f"missing:{k}")
    rid = entry.get("rule_ids")
    if rid is not None and not isinstance(rid, list):
        errs.append("invalid:rule_ids")
    return errs


def load_spi_process_kb(
    bundle_dir: Optional[Path] = None,
    *,
    strict: bool = False,
) -> tuple[SPIProcessKnowledgeBase, KBLoadReport]:
    """
    Load all KB JSON files under bundle_dir.

    If a file is missing or invalid, that section is empty and status is partial
    (unless all missing → empty). Does not raise on parse errors unless strict=True.
    """
    base = bundle_dir or default_kb_dir()
    report = KBLoadReport(status="ok", messages=[])
    kb = SPIProcessKnowledgeBase()

    manifest_path = base / "manifest.json"
    if manifest_path.is_file():
        try:
            raw = _read_json(manifest_path)
            if isinstance(raw, dict):
                kb.manifest = raw
        except (json.JSONDecodeError, OSError) as e:
            report.messages.append(f"manifest.json: {e}")
            if strict:
                raise
    else:
        report.messages.append(f"missing:{manifest_path}")

    files = {
        "multi_signal_rules": ("multi_signal_rules.json", "entries"),
        "dimension_abnormality_matrix": ("dimension_abnormality_matrix.json", "entries"),
        "inspection_checklist": ("inspection_checklist.json", "entries"),
        "chart_signal_lookup": ("chart_signal_lookup.json", "entries"),
    }

    for attr, (fname, key) in files.items():
        path = base / fname
        if not path.is_file():
            report.messages.append(f"missing:{path}")
            continue
        try:
            raw = _read_json(path)
            entries = raw.get(key) if isinstance(raw, dict) else None
            if not isinstance(entries, list):
                report.messages.append(f"invalid_structure:{path}")
                continue
            cleaned: List[Dict[str, Any]] = []
            for i, ent in enumerate(entries):
                if not isinstance(ent, dict):
                    report.messages.append(f"{path}: row_{i}_not_object")
                    continue
                if attr == "multi_signal_rules":
                    ve = validate_multi_signal_rule(ent)
                    if ve:
                        report.messages.append(f"{path}:R{ent.get('rule_id', i)}:{','.join(ve)}")
                        if strict:
                            raise ValueError(ve)
                        continue
                elif attr == "dimension_abnormality_matrix":
                    ve = validate_dimension_row(ent)
                    if ve:
                        report.messages.append(f"{path}:row{i}:{','.join(ve)}")
                        if strict:
                            raise ValueError(ve)
                        continue
                elif attr == "inspection_checklist":
                    ve = validate_checklist_row(ent)
                    if ve:
                        report.messages.append(f"{path}:row{i}:{','.join(ve)}")
                        if strict:
                            raise ValueError(ve)
                        continue
                elif attr == "chart_signal_lookup":
                    ve = validate_chart_lookup_row(ent)
                    if ve:
                        report.messages.append(f"{path}:row{i}:{','.join(ve)}")
                        if strict:
                            raise ValueError(ve)
                        continue
                cleaned.append(ent)
            setattr(kb, attr, cleaned)
        except (json.JSONDecodeError, OSError) as e:
            report.messages.append(f"{path}: {e}")
            if strict:
                raise

    has_any = any(
        [
            kb.multi_signal_rules,
            kb.dimension_abnormality_matrix,
            kb.inspection_checklist,
            kb.chart_signal_lookup,
        ]
    )
    if not has_any:
        report.status = "empty"
        report.messages.append("kb:no_valid_entries_loaded")
    elif report.messages:
        report.status = "partial"
    return kb, report
