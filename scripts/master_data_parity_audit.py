#!/usr/bin/env python3
"""
Master-data parity audit (legacy JSON registry vs SQLite active records).

Output:
- Outputs/master_data/parity_report.json
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.repo_bootstrap import ensure_repo_root_on_sys_path
except ImportError:  # pragma: no cover - script entry fallback
    from repo_bootstrap import ensure_repo_root_on_sys_path

ensure_repo_root_on_sys_path(Path(__file__).resolve().parents[1])

from app.data.coordinate_registry import list_registered
from app.data.master_data_db import db_conn
from app.data.product_spec_registry import (
    DEFAULT_AREA_LSL,
    DEFAULT_AREA_TARGET,
    DEFAULT_AREA_USL,
    DEFAULT_HEIGHT_LSL,
    DEFAULT_HEIGHT_TARGET,
    DEFAULT_HEIGHT_USL,
    DEFAULT_VOLUME_LSL,
    DEFAULT_VOLUME_TARGET,
    DEFAULT_VOLUME_USL,
    get as get_spec,
    list_products as list_spec_products,
)


_COMPARE_FLOAT_FIELDS = (
    "thickness_main",
    "thickness_precision",
    "default_volume_target",
    "default_volume_lsl",
    "default_volume_usl",
    "default_area_target",
    "default_area_lsl",
    "default_area_usl",
    "default_height_target",
    "default_height_lsl",
    "default_height_usl",
)
_COMPARE_RAW_FIELDS = ("stencil_type", "precision_is_main")


def _ci_key(value: Any) -> str:
    return str(value or "").strip().lower()


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _latest_by_product(items: list[dict[str, Any]], ts_key: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in items:
        product_name = str(item.get("product_name") or "").strip()
        if not product_name:
            continue
        key = _ci_key(product_name)
        current = out.get(key)
        ts = str(item.get(ts_key) or "")
        if current is None or ts >= str(current.get(ts_key) or ""):
            out[key] = item
    return out


def _legacy_coordinate_map(repo_root: Path) -> dict[str, dict[str, Any]]:
    payload = _read_json(repo_root / "data" / "coordinate_registry.json")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        return {}
    normalized: list[dict[str, Any]] = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "product_name": str(item.get("product_name") or "").strip(),
                "product_part_no": str(item.get("product_part_no") or "").strip(),
                "file_path": str(item.get("file_path") or "").strip(),
                "created_at": str(item.get("created_at") or ""),
            }
        )
    return _latest_by_product(normalized, ts_key="created_at")


def _db_coordinate_map() -> dict[str, dict[str, Any]]:
    rows = list_registered()
    normalized: list[dict[str, Any]] = []
    for row in rows:
        normalized.append(
            {
                "product_name": str(row.get("product_name") or "").strip(),
                "product_part_no": str(row.get("product_part_no") or "").strip(),
                "file_path": str(row.get("file_path") or "").strip(),
                "created_at": str(row.get("created_at") or ""),
            }
        )
    return _latest_by_product(normalized, ts_key="created_at")


def _normalize_legacy_spec(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "product_name": str(item.get("product_name") or "").strip(),
        "stencil_type": str(item.get("stencil_type") or "normal").strip().lower(),
        "thickness_main": _safe_float(item.get("thickness_main")),
        "thickness_precision": _safe_float(item.get("thickness_precision")),
        "precision_is_main": bool(item.get("precision_is_main", False)),
        "default_volume_target": _safe_float(item.get("default_volume_target")) or DEFAULT_VOLUME_TARGET,
        "default_volume_lsl": _safe_float(item.get("default_volume_lsl")) or DEFAULT_VOLUME_LSL,
        "default_volume_usl": _safe_float(item.get("default_volume_usl")) or DEFAULT_VOLUME_USL,
        "default_area_target": _safe_float(item.get("default_area_target")) or DEFAULT_AREA_TARGET,
        "default_area_lsl": _safe_float(item.get("default_area_lsl")) or DEFAULT_AREA_LSL,
        "default_area_usl": _safe_float(item.get("default_area_usl")) or DEFAULT_AREA_USL,
        "default_height_target": _safe_float(item.get("default_height_target")) or DEFAULT_HEIGHT_TARGET,
        "default_height_lsl": _safe_float(item.get("default_height_lsl")) or DEFAULT_HEIGHT_LSL,
        "default_height_usl": _safe_float(item.get("default_height_usl")) or DEFAULT_HEIGHT_USL,
        "updated_at": str(item.get("updated_at") or ""),
    }


def _legacy_spec_map(repo_root: Path) -> dict[str, dict[str, Any]]:
    payload = _read_json(repo_root / "data" / "product_spec_registry.json")
    specs = payload.get("specs")
    if not isinstance(specs, dict):
        return {}
    items: list[dict[str, Any]] = []
    for raw in specs.values():
        if isinstance(raw, dict):
            items.append(_normalize_legacy_spec(raw))
    return _latest_by_product(items, ts_key="updated_at")


def _db_spec_map() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for product in list_spec_products():
        key = _ci_key(product)
        spec = get_spec(product)
        if isinstance(spec, dict):
            out[key] = spec
    return out


def _legacy_assignment_map(repo_root: Path) -> dict[str, dict[str, Any]]:
    payload = _read_json(repo_root / "data" / "stencil_assignments.json")
    assignment_payload = payload.get("assignments")
    coord_map_payload = payload.get("coord_path_by_product")
    assignments = assignment_payload if isinstance(assignment_payload, dict) else {}
    coord_map = coord_map_payload if isinstance(coord_map_payload, dict) else {}
    out: dict[str, dict[str, Any]] = {}
    products = set(assignments.keys()) | set(coord_map.keys())
    for product_name in products:
        key = _ci_key(product_name)
        if not key:
            continue
        raw_refdes = assignments.get(product_name)
        refdes_list: list[str] = []
        if isinstance(raw_refdes, list):
            refdes_list = sorted(
                {str(v).strip() for v in raw_refdes if str(v).strip()}
            )
        out[key] = {
            "product_name": str(product_name).strip(),
            "precision_refdes": refdes_list,
            "coord_file_path": str(coord_map.get(product_name) or "").strip(),
        }
    return out


def _db_assignment_map() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    with db_conn() as conn:
        ref_rows = conn.execute(
            """
            SELECT p.product_name AS product_name, sa.refdes AS refdes
            FROM stencil_assignments sa
            JOIN products p ON p.id = sa.product_id
            ORDER BY p.product_name_ci ASC, sa.refdes ASC
            """
        ).fetchall()
        for row in ref_rows:
            product_name = str(row["product_name"] or "").strip()
            key = _ci_key(product_name)
            if not key:
                continue
            entry = out.setdefault(
                key,
                {"product_name": product_name, "precision_refdes": [], "coord_file_path": ""},
            )
            refdes = str(row["refdes"] or "").strip()
            if refdes:
                entry["precision_refdes"].append(refdes)

        path_rows = conn.execute(
            """
            SELECT p.product_name AS product_name, sm.coord_file_path AS coord_file_path
            FROM stencil_assignment_meta sm
            JOIN products p ON p.id = sm.product_id
            ORDER BY p.product_name_ci ASC
            """
        ).fetchall()
        for row in path_rows:
            product_name = str(row["product_name"] or "").strip()
            key = _ci_key(product_name)
            if not key:
                continue
            entry = out.setdefault(
                key,
                {"product_name": product_name, "precision_refdes": [], "coord_file_path": ""},
            )
            entry["coord_file_path"] = str(row["coord_file_path"] or "").strip()

    for entry in out.values():
        refdes_unique = sorted({str(x).strip() for x in entry["precision_refdes"] if str(x).strip()})
        entry["precision_refdes"] = refdes_unique
    return out


def _set_diff(a: set[str], b: set[str]) -> list[str]:
    return sorted(a - b)


def _compare_coordinate(legacy_map: dict[str, dict[str, Any]], db_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    legacy_keys = set(legacy_map.keys())
    db_keys = set(db_map.keys())
    path_mismatches: list[dict[str, Any]] = []
    part_no_mismatches: list[dict[str, Any]] = []
    for key in sorted(legacy_keys & db_keys):
        legacy = legacy_map[key]
        current = db_map[key]
        legacy_path = str(legacy.get("file_path") or "").strip()
        db_path = str(current.get("file_path") or "").strip()
        if legacy_path != db_path:
            path_mismatches.append(
                {
                    "product_key": key,
                    "legacy_path": legacy_path,
                    "db_path": db_path,
                }
            )
        legacy_part_no = str(legacy.get("product_part_no") or "").strip()
        db_part_no = str(current.get("product_part_no") or "").strip()
        if legacy_part_no != db_part_no:
            part_no_mismatches.append(
                {
                    "product_key": key,
                    "legacy_part_no": legacy_part_no,
                    "db_part_no": db_part_no,
                }
            )

    return {
        "legacy_product_count": len(legacy_keys),
        "db_product_count": len(db_keys),
        "missing_in_db": _set_diff(legacy_keys, db_keys),
        "missing_in_legacy": _set_diff(db_keys, legacy_keys),
        "active_path_mismatches": path_mismatches,
        "product_part_no_mismatches": part_no_mismatches,
        "completeness": {
            "legacy_missing_file_path": sum(1 for x in legacy_map.values() if not str(x.get("file_path") or "").strip()),
            "db_missing_file_path": sum(1 for x in db_map.values() if not str(x.get("file_path") or "").strip()),
        },
    }


def _compare_specs(legacy_map: dict[str, dict[str, Any]], db_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    legacy_keys = set(legacy_map.keys())
    db_keys = set(db_map.keys())
    field_mismatches: list[dict[str, Any]] = []
    for key in sorted(legacy_keys & db_keys):
        legacy = legacy_map[key]
        current = db_map[key]
        for field in _COMPARE_RAW_FIELDS:
            legacy_value = legacy.get(field)
            db_value = current.get(field)
            if legacy_value != db_value:
                field_mismatches.append(
                    {
                        "product_key": key,
                        "field": field,
                        "legacy": legacy_value,
                        "db": db_value,
                    }
                )
        for field in _COMPARE_FLOAT_FIELDS:
            legacy_value = _safe_float(legacy.get(field))
            db_value = _safe_float(current.get(field))
            if legacy_value is None and db_value is None:
                continue
            if legacy_value is None or db_value is None or abs(legacy_value - db_value) > 1e-9:
                field_mismatches.append(
                    {
                        "product_key": key,
                        "field": field,
                        "legacy": legacy_value,
                        "db": db_value,
                    }
                )

    return {
        "legacy_product_count": len(legacy_keys),
        "db_product_count": len(db_keys),
        "missing_in_db": _set_diff(legacy_keys, db_keys),
        "missing_in_legacy": _set_diff(db_keys, legacy_keys),
        "field_mismatches": field_mismatches,
        "completeness": {
            "db_missing_stencil_type": sum(1 for x in db_map.values() if not str(x.get("stencil_type") or "").strip()),
            "db_missing_thickness_main": sum(1 for x in db_map.values() if _safe_float(x.get("thickness_main")) is None),
        },
    }


def _compare_assignments(
    legacy_map: dict[str, dict[str, Any]], db_map: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    legacy_keys = set(legacy_map.keys())
    db_keys = set(db_map.keys())
    refdes_mismatches: list[dict[str, Any]] = []
    coord_path_mismatches: list[dict[str, Any]] = []
    for key in sorted(legacy_keys & db_keys):
        legacy = legacy_map[key]
        current = db_map[key]
        legacy_refdes = sorted({str(x).strip() for x in legacy.get("precision_refdes", []) if str(x).strip()})
        db_refdes = sorted({str(x).strip() for x in current.get("precision_refdes", []) if str(x).strip()})
        if legacy_refdes != db_refdes:
            refdes_mismatches.append(
                {
                    "product_key": key,
                    "legacy_precision_refdes": legacy_refdes,
                    "db_precision_refdes": db_refdes,
                }
            )
        legacy_path = str(legacy.get("coord_file_path") or "").strip()
        db_path = str(current.get("coord_file_path") or "").strip()
        if legacy_path != db_path:
            coord_path_mismatches.append(
                {
                    "product_key": key,
                    "legacy_coord_path": legacy_path,
                    "db_coord_path": db_path,
                }
            )

    return {
        "legacy_product_count": len(legacy_keys),
        "db_product_count": len(db_keys),
        "missing_in_db": _set_diff(legacy_keys, db_keys),
        "missing_in_legacy": _set_diff(db_keys, legacy_keys),
        "precision_refdes_mismatches": refdes_mismatches,
        "coord_path_mismatches": coord_path_mismatches,
        "completeness": {
            "db_empty_coord_paths": sum(1 for x in db_map.values() if not str(x.get("coord_file_path") or "").strip()),
        },
    }


def _total_mismatch_count(section: dict[str, Any], detail_keys: list[str]) -> int:
    total = len(section.get("missing_in_db", [])) + len(section.get("missing_in_legacy", []))
    for key in detail_keys:
        total += len(section.get(key, []))
    return total


def build_parity_report(repo_root: Path) -> dict[str, Any]:
    legacy_coordinate = _legacy_coordinate_map(repo_root)
    db_coordinate = _db_coordinate_map()
    legacy_spec = _legacy_spec_map(repo_root)
    db_spec = _db_spec_map()
    legacy_assignment = _legacy_assignment_map(repo_root)
    db_assignment = _db_assignment_map()

    coordinate_report = _compare_coordinate(legacy_coordinate, db_coordinate)
    spec_report = _compare_specs(legacy_spec, db_spec)
    assignment_report = _compare_assignments(legacy_assignment, db_assignment)

    coordinate_mismatch_count = _total_mismatch_count(
        coordinate_report, detail_keys=["active_path_mismatches", "product_part_no_mismatches"]
    )
    spec_mismatch_count = _total_mismatch_count(spec_report, detail_keys=["field_mismatches"])
    assignment_mismatch_count = _total_mismatch_count(
        assignment_report, detail_keys=["precision_refdes_mismatches", "coord_path_mismatches"]
    )
    total_mismatch_count = coordinate_mismatch_count + spec_mismatch_count + assignment_mismatch_count

    sample_mismatches = (
        coordinate_report.get("active_path_mismatches", [])[:3]
        + spec_report.get("field_mismatches", [])[:3]
        + assignment_report.get("precision_refdes_mismatches", [])[:3]
    )
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository_root": str(repo_root.resolve()),
        "db_path": str((repo_root / "data" / "spc_master.db").resolve()),
        "summary": {
            "total_mismatch_count": total_mismatch_count,
            "coordinate_mismatch_count": coordinate_mismatch_count,
            "spec_mismatch_count": spec_mismatch_count,
            "assignment_mismatch_count": assignment_mismatch_count,
        },
        "coordinate": coordinate_report,
        "spec": spec_report,
        "assignment": assignment_report,
        "sample_mismatches": sample_mismatches,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit parity between legacy JSON registries and SQLite active data")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument(
        "--output",
        default="Outputs/master_data/parity_report.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    if not repo_root.exists() or not repo_root.is_dir():
        raise SystemExit(f"Invalid repo root: {repo_root}")

    report = build_parity_report(repo_root)
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = (repo_root / output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
