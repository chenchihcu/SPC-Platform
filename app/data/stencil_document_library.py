"""Immutable stencil-aperture document versions and per-pad nominal values.

The aperture source and Pad CSV are copied into managed storage before a version
is committed.  The SQLite ``gerber_*`` column names are retained as a legacy
storage contract, but may contain any verified aperture format.  A product may
have one active document per side; activation is explicit and active versions
cannot be deleted.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from app.data.master_data_db import (
    db_conn,
    db_path,
    file_sha256,
    now_iso,
    upsert_product,
)

SUPPORTED_APERTURE_SUFFIXES = frozenset(
    {
        ".gtp",
        ".gbp",
        ".gbr",
        ".ger",
        ".pho",
        ".zip",
        ".xml",
        ".ipc2581",
        ".dxf",
        ".tgz",
        ".tar",
        ".tar.gz",
    }
)
VALID_SIDES = frozenset({"TOP", "BOTTOM"})


def normalize_side(side: str) -> str:
    value = (side or "").strip().upper()
    if value not in VALID_SIDES:
        raise ValueError("side must be TOP or BOTTOM")
    return value


def _safe_segment(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", (value or "").strip()).strip("._")
    return cleaned or fallback


def _aperture_suffix(path: Path) -> str:
    name = path.name.casefold()
    if name.endswith(".tar.gz"):
        return ".tar.gz"
    return path.suffix.casefold()


def stencil_documents_root() -> Path:
    """Return managed root, colocated with an overridden test database."""
    return db_path().parent / "stencil_documents"


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _decode_row(row: Any) -> dict[str, Any]:
    result = dict(row)
    for key in ("coordinate_transform_json", "validation_summary_json", "preview_geometry_json"):
        if key in result:
            try:
                result[key.removesuffix("_json")] = json.loads(result[key] or "{}")
            except (TypeError, json.JSONDecodeError):
                result[key.removesuffix("_json")] = {}
    return result


def activation_blockers(validation_summary: dict[str, Any]) -> list[str]:
    """Return explicit reasons a parsed version cannot become active."""
    total = int(validation_summary.get("total_pads") or 0)
    matched = int(validation_summary.get("matched_pads") or 0)
    duplicate_rows = int(validation_summary.get("duplicate_pad_rows") or 0)
    ambiguous = int(validation_summary.get("ambiguous_openings") or 0)
    unclassified_extra = int(validation_summary.get("unclassified_extra_openings") or 0)
    missing_thickness = int(validation_summary.get("missing_thickness_pads") or 0)
    blockers: list[str] = []
    if total <= 0:
        blockers.append("Pad CSV 沒有可用資料")
    if matched != total:
        blockers.append(f"Pad 覆蓋不足：{matched}/{total}")
    if duplicate_rows:
        blockers.append(f"Pad CSV 有 {duplicate_rows} 筆重複 RefDes/Pad")
    if ambiguous:
        blockers.append(f"有 {ambiguous} 個開窗同時歸屬多個 Pad")
    if unclassified_extra:
        blockers.append(f"有 {unclassified_extra} 個額外開窗尚未標記 NON_COMPONENT")
    if missing_thickness:
        blockers.append(f"有 {missing_thickness} 個 Pad 缺少鋼板厚度")
    if validation_summary.get("requires_user_overlay_confirmation") and not validation_summary.get(
        "overlay_confirmed"
    ):
        blockers.append("尚未確認開窗/Pad 疊圖")
    return blockers


def nominal_activation_blockers(
    nominal_rows: Iterable[dict[str, Any]], validation_summary: dict[str, Any]
) -> list[str]:
    rows = [dict(row) for row in nominal_rows]
    blockers: list[str] = []
    total = int(validation_summary.get("total_pads") or 0)
    if len(rows) != total:
        blockers.append(f"Pad 名義值筆數不符：{len(rows)}/{total}")
    keys = [
        (
            str(row.get("refdes") or "").strip(),
            str(row.get("pad") or "").strip(),
            str(row.get("side") or "").strip().upper(),
        )
        for row in rows
    ]
    if len(set(keys)) != len(keys):
        blockers.append("Pad 名義值 RefDes/Pad 不唯一")
    if any(not refdes or not pad or side not in VALID_SIDES for refdes, pad, side in keys):
        blockers.append("Pad 名義值含空白 RefDes/Pad 或無效 Side")
    invalid = 0
    for row in rows:
        try:
            valid = (
                str(row.get("match_status") or "") == "MATCHED"
                and int(row.get("opening_count") or 0) >= 1
                and float(row.get("nominal_area_mm2") or 0) > 0
                and float(row.get("resolved_thickness_mm") or 0) > 0
                and float(row.get("nominal_volume_mm3") or 0) > 0
            )
        except (TypeError, ValueError):
            valid = False
        if not valid:
            invalid += 1
    if invalid:
        blockers.append(f"有 {invalid} 筆 Pad 名義值未達啟用條件")
    return blockers


def create_stencil_document_version(
    *,
    product_name: str,
    stencil_no: str,
    revision: str,
    side: str,
    gerber_source: str,
    pad_csv_source: str,
    coordinate_transform: dict[str, Any],
    validation_summary: dict[str, Any],
    parser_version: str,
    nominals: Iterable[dict[str, Any]],
    activate: bool = False,
) -> int:
    """Copy sources atomically and insert an immutable version plus nominals."""
    product = (product_name or "").strip()
    revision_value = (revision or "").strip()
    side_value = normalize_side(side)
    aperture = Path(gerber_source)
    pad_csv = Path(pad_csv_source)
    if not product:
        raise ValueError("product_name is required")
    if not revision_value:
        raise ValueError("revision is required")
    aperture_suffix = _aperture_suffix(aperture)
    if aperture_suffix not in SUPPORTED_APERTURE_SUFFIXES:
        raise ValueError("unsupported aperture source extension")
    if not aperture.is_file() or not pad_csv.is_file():
        raise FileNotFoundError("Aperture source and Pad CSV must both exist")
    if pad_csv.suffix.lower() != ".csv":
        raise ValueError("pad_csv_source must be a CSV file")
    nominal_rows = [dict(row) for row in nominals]
    blockers = activation_blockers(validation_summary) + nominal_activation_blockers(
        nominal_rows, validation_summary
    )
    if activate and blockers:
        raise ValueError("version is not activatable: " + "; ".join(blockers))
    root = stencil_documents_root()
    side_dir = root / _safe_segment(product, "product") / side_value.lower()
    side_dir.mkdir(parents=True, exist_ok=True)
    storage_key = (
        f"{_safe_segment(revision_value, 'revision')}_"
        f"{datetime.now().strftime('%Y%m%dT%H%M%S%f')}"
    )
    final_dir = side_dir / storage_key
    stage_dir = Path(tempfile.mkdtemp(prefix=".staging-", dir=side_dir))
    final_created = False
    try:
        staged_gerber = stage_dir / f"aperture{aperture_suffix}"
        staged_csv = stage_dir / "pads.csv"
        staged_snapshot = stage_dir / "parse_snapshot.json"
        shutil.copy2(aperture, staged_gerber)
        shutil.copy2(pad_csv, staged_csv)
        snapshot = {
            "product_name": product,
            "stencil_no": (stencil_no or "").strip(),
            "revision": revision_value,
            "side": side_value,
            "coordinate_transform": coordinate_transform,
            "validation_summary": validation_summary,
            "parser_version": parser_version,
            "nominals": nominal_rows,
        }
        staged_snapshot.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(stage_dir, final_dir)
        final_created = True
        managed_gerber = final_dir / staged_gerber.name
        managed_csv = final_dir / staged_csv.name

        with db_conn() as conn:
            product_id = upsert_product(conn, product)
            duplicate = conn.execute(
                """
                SELECT id FROM stencil_document_versions
                WHERE product_id = ? AND side = ? AND revision = ?
                """,
                (product_id, side_value, revision_value),
            ).fetchone()
            if duplicate:
                raise ValueError(
                    f"revision {revision_value!r} already exists for {product}/{side_value}"
                )
            if activate:
                conn.execute(
                    """
                    UPDATE stencil_document_versions SET is_active = 0
                    WHERE product_id = ? AND side = ?
                    """,
                    (product_id, side_value),
                )
            cur = conn.execute(
                """
                INSERT INTO stencil_document_versions(
                    product_id, stencil_no, revision, side,
                    gerber_path, pad_csv_path, gerber_sha256, pad_csv_sha256,
                    coordinate_transform_json, validation_summary_json,
                    parser_version, created_at, is_active
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product_id,
                    (stencil_no or "").strip(),
                    revision_value,
                    side_value,
                    str(managed_gerber.resolve()),
                    str(managed_csv.resolve()),
                    file_sha256(str(managed_gerber)),
                    file_sha256(str(managed_csv)),
                    _json(coordinate_transform),
                    _json(validation_summary),
                    parser_version,
                    now_iso(),
                    1 if activate else 0,
                ),
            )
            version_id = int(cur.lastrowid or 0)
            if version_id <= 0:
                raise RuntimeError("failed to create stencil document version")
            for row in nominal_rows:
                row_side = normalize_side(str(row.get("side") or side_value))
                if row_side != side_value:
                    raise ValueError("nominal side does not match version side")
                conn.execute(
                    """
                    INSERT INTO stencil_pad_nominals(
                        version_id, refdes, pad, side, opening_count,
                        nominal_area_mm2, resolved_thickness_mm,
                        nominal_volume_mm3, match_status, unmatched_reason,
                        preview_geometry_json
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        version_id,
                        str(row.get("refdes") or "").strip(),
                        str(row.get("pad") or "").strip(),
                        side_value,
                        int(row.get("opening_count") or 0),
                        row.get("nominal_area_mm2"),
                        row.get("resolved_thickness_mm"),
                        row.get("nominal_volume_mm3"),
                        str(row.get("match_status") or "UNMATCHED"),
                        str(row.get("unmatched_reason") or ""),
                        _json(row.get("preview_geometry") or {}),
                    ),
                )
            conn.execute(
                """
                INSERT INTO audit_events(entity_type, entity_id, action, payload_json, created_at)
                VALUES('stencil_document_version', ?, 'create', ?, ?)
                """,
                (
                    str(version_id),
                    _json({"product": product, "side": side_value, "revision": revision_value}),
                    now_iso(),
                ),
            )
        return version_id
    except (OSError, sqlite3.Error, TypeError, ValueError, RuntimeError):
        if final_created and final_dir.exists():
            shutil.rmtree(final_dir, ignore_errors=True)
        elif stage_dir.exists():
            shutil.rmtree(stage_dir, ignore_errors=True)
        raise


def list_stencil_document_versions(
    product_name: str = "", side: str = ""
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if (product_name or "").strip():
        clauses.append("p.product_name_ci = ?")
        params.append(product_name.strip().lower())
    if (side or "").strip():
        clauses.append("v.side = ?")
        params.append(normalize_side(side))
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with db_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT v.*, p.product_name, p.product_part_no,
                   (SELECT COUNT(*) FROM stencil_pad_nominals n
                    WHERE n.version_id = v.id) AS nominal_count
            FROM stencil_document_versions v
            JOIN products p ON p.id = v.product_id
            {where}
            ORDER BY v.created_at DESC, v.id DESC
            """,
            tuple(params),
        ).fetchall()
    return [_decode_row(row) for row in rows]


def get_stencil_document_version(version_id: int) -> dict[str, Any] | None:
    with db_conn() as conn:
        row = conn.execute(
            """
            SELECT v.*, p.product_name, p.product_part_no
            FROM stencil_document_versions v
            JOIN products p ON p.id = v.product_id
            WHERE v.id = ?
            """,
            (int(version_id),),
        ).fetchone()
    return _decode_row(row) if row else None


def get_active_stencil_document(product_name: str, side: str) -> dict[str, Any] | None:
    side_value = normalize_side(side)
    with db_conn() as conn:
        row = conn.execute(
            """
            SELECT v.*, p.product_name, p.product_part_no
            FROM stencil_document_versions v
            JOIN products p ON p.id = v.product_id
            WHERE p.product_name_ci = ? AND v.side = ? AND v.is_active = 1
            """,
            ((product_name or "").strip().lower(), side_value),
        ).fetchone()
    return _decode_row(row) if row else None


def list_stencil_pad_nominals(version_id: int) -> list[dict[str, Any]]:
    with db_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM stencil_pad_nominals
            WHERE version_id = ?
            ORDER BY refdes COLLATE NOCASE, pad COLLATE NOCASE
            """,
            (int(version_id),),
        ).fetchall()
    return [_decode_row(row) for row in rows]


def set_active_stencil_document_version(version_id: int) -> bool:
    with db_conn() as conn:
        row = conn.execute(
            """
            SELECT product_id, side, validation_summary_json
            FROM stencil_document_versions WHERE id = ?
            """,
            (int(version_id),),
        ).fetchone()
        if not row:
            return False
        validation = json.loads(row["validation_summary_json"] or "{}")
        nominal_rows = [
            dict(item)
            for item in conn.execute(
                "SELECT * FROM stencil_pad_nominals WHERE version_id = ?",
                (int(version_id),),
            ).fetchall()
        ]
        blockers = activation_blockers(validation) + nominal_activation_blockers(
            nominal_rows, validation
        )
        if blockers:
            raise ValueError("version is not activatable: " + "; ".join(blockers))
        conn.execute(
            """
            UPDATE stencil_document_versions SET is_active = 0
            WHERE product_id = ? AND side = ?
            """,
            (row["product_id"], row["side"]),
        )
        cur = conn.execute(
            "UPDATE stencil_document_versions SET is_active = 1 WHERE id = ?",
            (int(version_id),),
        )
        if cur.rowcount == 1:
            conn.execute(
                """
                INSERT INTO audit_events(entity_type, entity_id, action, payload_json, created_at)
                VALUES('stencil_document_version', ?, 'activate', ?, ?)
                """,
                (str(version_id), _json({"side": row["side"]}), now_iso()),
            )
        return cur.rowcount == 1


def deactivate_stencil_document_version(version_id: int) -> bool:
    """Explicit rollback: return subsequent analyses to the raw data domain."""
    with db_conn() as conn:
        cur = conn.execute(
            "UPDATE stencil_document_versions SET is_active = 0 WHERE id = ? AND is_active = 1",
            (int(version_id),),
        )
        if cur.rowcount == 1:
            conn.execute(
                """
                INSERT INTO audit_events(entity_type, entity_id, action, payload_json, created_at)
                VALUES('stencil_document_version', ?, 'deactivate', '{}', ?)
                """,
                (str(version_id), now_iso()),
            )
        return cur.rowcount == 1


def delete_inactive_stencil_document_version(version_id: int) -> bool:
    """Delete only an inactive version. UI must apply the repository double barrier."""
    return bool(delete_inactive_stencil_document_versions([version_id]))


def delete_inactive_stencil_document_versions(version_ids: Iterable[int]) -> list[int]:
    """Atomically delete selected inactive versions and their managed source folders.

    The caller remains responsible for the UI double-confirmation barrier.  This
    service validates every selected version before mutating anything, so a mixed
    selection containing an active or missing version cannot result in a partial
    deletion.
    """
    ids = sorted({int(version_id) for version_id in version_ids})
    if not ids:
        return []
    placeholders = ", ".join("?" for _ in ids)
    managed_paths: list[Path] = []
    with db_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT v.id, v.is_active, v.gerber_path, v.pad_csv_path,
                   p.product_name, v.side, v.revision
            FROM stencil_document_versions v
            JOIN products p ON p.id = v.product_id
            WHERE v.id IN ({placeholders})
            """,
            tuple(ids),
        ).fetchall()
        found_ids = {int(row["id"]) for row in rows}
        missing_ids = [version_id for version_id in ids if version_id not in found_ids]
        if missing_ids:
            raise ValueError(f"stencil document versions not found: {missing_ids}")
        active_ids = [int(row["id"]) for row in rows if int(row["is_active"] or 0)]
        if active_ids:
            raise ValueError(f"active stencil document versions cannot be deleted: {active_ids}")
        for row in rows:
            managed_paths.extend(
                [
                    Path(str(row["gerber_path"] or "")),
                    Path(str(row["pad_csv_path"] or "")),
                ]
            )
            conn.execute(
                """
                INSERT INTO audit_events(entity_type, entity_id, action, payload_json, created_at)
                VALUES('stencil_document_version', ?, 'delete', ?, ?)
                """,
                (
                    str(row["id"]),
                    _json(
                        {
                            "product_name": row["product_name"],
                            "side": row["side"],
                            "revision": row["revision"],
                        }
                    ),
                    now_iso(),
                ),
            )
        conn.execute(
            f"DELETE FROM stencil_document_versions WHERE id IN ({placeholders}) AND is_active = 0",
            tuple(ids),
        )
    parents = {path.parent for path in managed_paths if path.name}
    root = stencil_documents_root().resolve()
    for parent in parents:
        try:
            resolved = parent.resolve()
            if resolved != root and root in resolved.parents:
                shutil.rmtree(resolved, ignore_errors=True)
        except OSError:
            continue
    return ids
