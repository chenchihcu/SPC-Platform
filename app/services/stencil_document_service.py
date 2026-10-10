"""Gerber-to-pad matching and derived SPI percentage calculations."""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree  # type: ignore[import-untyped]
from shapely import affinity  # type: ignore[import-untyped]
from shapely.geometry import Point, Polygon, box, mapping  # type: ignore[import-untyped]
from shapely.geometry.base import BaseGeometry  # type: ignore[import-untyped]
from shapely.ops import unary_union  # type: ignore[import-untyped]
from shapely.strtree import STRtree  # type: ignore[import-untyped]

from app.data.stencil_assignment_registry import PROFILE_PRECISION, get_profile_by_refdes
from app.data.paste_printing_spec_registry import get as get_paste_spec
from app.data.stencil_document_library import (
    get_active_stencil_document,
    list_stencil_pad_nominals,
    normalize_side,
)
from app.data.stencil_thickness_registry import STENCIL_STEPPED, get as get_stencil_spec
from app.services.stencil_aperture_loader import (
    APERTURE_PARSER_VERSION,
    load_gerber_openings,  # noqa: F401 - legacy public re-export
)

PARSER_VERSION = APERTURE_PARSER_VERSION
REQUIRED_PAD_COLUMNS = ("RefDes", "Pad", "X", "Y", "Width", "Height", "Rotation", "Side")
SUPPORTED_UNITS = frozenset({"mm", "inch"})


@dataclass(frozen=True)
class PadDefinition:
    refdes: str
    pad: str
    x_mm: float
    y_mm: float
    width_mm: float
    height_mm: float
    rotation_deg: float
    side: str

    @property
    def key(self) -> tuple[str, str, str]:
        """Return the immutable matching key."""
        return self.refdes, self.pad, self.side

    def geometry(self) -> BaseGeometry:
        """Build the rotated Pad outline in millimetres."""
        geom = box(
            self.x_mm - self.width_mm / 2.0,
            self.y_mm - self.height_mm / 2.0,
            self.x_mm + self.width_mm / 2.0,
            self.y_mm + self.height_mm / 2.0,
        )
        if not math.isclose(self.rotation_deg % 360.0, 0.0):
            geom = affinity.rotate(
                geom,
                self.rotation_deg,
                origin=(self.x_mm, self.y_mm),
                use_radians=False,
            )
        return geom


@dataclass(frozen=True)
class AlignmentCandidate:
    rotation_deg: int
    mirrored: bool
    translate_x_mm: float
    translate_y_mm: float
    coverage: float
    residual_mm: float
    matched_openings: int
    ambiguous_openings: int
    extra_openings: int

    def as_dict(self) -> dict[str, Any]:
        """Return the persisted rigid-transform and score summary."""
        return {
            "rotation_deg": self.rotation_deg,
            "mirrored": self.mirrored,
            "translate_x_mm": self.translate_x_mm,
            "translate_y_mm": self.translate_y_mm,
            "coverage": self.coverage,
            "residual_mm": self.residual_mm,
            "matched_openings": self.matched_openings,
            "ambiguous_openings": self.ambiguous_openings,
            "extra_openings": self.extra_openings,
            "scale": 1.0,
            "shear": 0.0,
        }


@dataclass(frozen=True)
class ImportAnalysis:
    transform: dict[str, Any]
    validation_summary: dict[str, Any]
    nominals: list[dict[str, Any]]
    transformed_openings: list[BaseGeometry]


@dataclass(frozen=True)
class DerivedPercentageResult:
    dataframe: pd.DataFrame
    metadata: dict[str, Any]


def infer_measurement_side(
    dataframe: pd.DataFrame, measurement_metadata: dict[str, Any] | None = None
) -> str | None:
    """Resolve side only from explicit data/metadata or an explicit TOP/BOTTOM token."""
    if "Side" in dataframe.columns:
        values = {
            str(value).strip().upper()
            for value in dataframe["Side"].dropna().unique().tolist()
            if str(value).strip()
        }
        if len(values) == 1 and next(iter(values)) in {"TOP", "BOTTOM"}:
            return next(iter(values))
    metadata = measurement_metadata or {}
    for key in ("side", "Side", "board_side"):
        value = str(metadata.get(key) or "").strip().upper()
        if value in {"TOP", "BOTTOM"}:
            return value
    tokens = " ".join(
        [
            str(metadata.get("vendor_profile") or ""),
            str(metadata.get("filepath") or ""),
        ]
    ).upper()
    has_top = "TOP" in tokens
    has_bottom = "BOTTOM" in tokens or "BOT" in tokens
    if has_top != has_bottom:
        return "TOP" if has_top else "BOTTOM"
    return None


def percentage_workorder_spec(product_name: str) -> dict[str, dict[str, str]] | None:
    """Return the product's active paste limits in the derived percent domain."""
    paste = get_paste_spec(product_name)
    if not paste:
        return None
    return {
        "volume": {
            "target": str(paste.get("default_volume_target", 100.0)),
            "lsl": str(paste.get("default_volume_lsl", 70.0)),
            "usl": str(paste.get("default_volume_usl", 150.0)),
        },
        "area": {
            "target": str(paste.get("default_area_target", 100.0)),
            "lsl": str(paste.get("default_area_lsl", 70.0)),
            "usl": str(paste.get("default_area_usl", 150.0)),
        },
        "height": {
            "target": "100.0",
            "lsl": str(paste.get("default_height_lsl", 70.0)),
            "usl": str(paste.get("default_height_usl", 140.0)),
        },
    }


def _canonical_pad_columns(fieldnames: Iterable[str]) -> dict[str, str]:
    names = {str(name).strip().lower(): str(name) for name in fieldnames if name is not None}
    missing = [name for name in REQUIRED_PAD_COLUMNS if name.lower() not in names]
    if missing:
        raise ValueError("Pad CSV 缺少欄位：" + ", ".join(missing))
    return {name: names[name.lower()] for name in REQUIRED_PAD_COLUMNS}


def load_pad_csv(path: str, *, unit: str, side: str) -> list[PadDefinition]:
    """Load the fixed Pad CSV contract while preserving Pad as text."""
    unit_value = (unit or "").strip().lower()
    if unit_value not in SUPPORTED_UNITS:
        raise ValueError("Pad CSV unit must be mm or inch")
    side_value = normalize_side(side)
    factor = 25.4 if unit_value == "inch" else 1.0
    rows: list[PadDefinition] = []
    seen: set[tuple[str, str, str]] = set()
    duplicates: list[str] = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = _canonical_pad_columns(reader.fieldnames or [])
        for line_no, raw in enumerate(reader, start=2):
            refdes = str(raw.get(columns["RefDes"], "")).strip()
            pad = str(raw.get(columns["Pad"], "")).strip()
            row_side = normalize_side(str(raw.get(columns["Side"], "")))
            if row_side != side_value:
                raise ValueError(
                    f"Pad CSV 第 {line_no} 列 Side={row_side}，與匯入 Side={side_value} 不符"
                )
            if not refdes or not pad:
                raise ValueError(f"Pad CSV 第 {line_no} 列 RefDes/Pad 不可空白")
            try:
                x = float(str(raw.get(columns["X"], "")).strip()) * factor
                y = float(str(raw.get(columns["Y"], "")).strip()) * factor
                width = float(str(raw.get(columns["Width"], "")).strip()) * factor
                height = float(str(raw.get(columns["Height"], "")).strip()) * factor
                rotation = float(str(raw.get(columns["Rotation"], "0")).strip() or 0.0)
            except ValueError as exc:
                raise ValueError(f"Pad CSV 第 {line_no} 列座標/尺寸/角度不是有效數字") from exc
            if not all(math.isfinite(value) for value in (x, y, width, height, rotation)):
                raise ValueError(f"Pad CSV 第 {line_no} 列含非有限數字")
            if width <= 0 or height <= 0:
                raise ValueError(f"Pad CSV 第 {line_no} 列 Width/Height 必須大於 0")
            item = PadDefinition(refdes, pad, x, y, width, height, rotation, side_value)
            if item.key in seen:
                duplicates.append(f"{refdes}/{pad}")
            seen.add(item.key)
            rows.append(item)
    if not rows:
        raise ValueError("Pad CSV 沒有資料列")
    if duplicates:
        raise ValueError("Pad CSV RefDes/Pad 重複：" + ", ".join(sorted(set(duplicates))))
    return rows


def _oriented_openings(
    openings: Sequence[BaseGeometry], rotation_deg: int, mirrored: bool
) -> list[BaseGeometry]:
    transformed = list(openings)
    if mirrored:
        transformed = [
            affinity.scale(g, xfact=-1.0, yfact=1.0, origin=(0.0, 0.0))
            for g in transformed
        ]
    if rotation_deg:
        transformed = [
            affinity.rotate(g, rotation_deg, origin=(0.0, 0.0)) for g in transformed
        ]
    return transformed


def _sample_indexes(length: int, maximum: int = 24) -> list[int]:
    if length <= maximum:
        return list(range(length))
    return sorted({int(value) for value in np.linspace(0, length - 1, maximum)})


def _rank_translation_candidates(
    oriented: Sequence[BaseGeometry], pads: Sequence[PadDefinition]
) -> list[tuple[float, float]]:
    """RANSAC-like bounded candidate search robust to extra/missing openings."""
    opening_centers = np.asarray([[g.centroid.x, g.centroid.y] for g in oriented], dtype=float)
    pad_centers = np.asarray([[pad.x_mm, pad.y_mm] for pad in pads], dtype=float)
    candidates: set[tuple[float, float]] = set()
    centroid_delta = pad_centers.mean(axis=0) - opening_centers.mean(axis=0)
    candidates.add((float(centroid_delta[0]), float(centroid_delta[1])))
    for opening_index in _sample_indexes(len(oriented)):
        for pad_index in _sample_indexes(len(pads)):
            delta = pad_centers[pad_index] - opening_centers[opening_index]
            candidates.add((round(float(delta[0]), 9), round(float(delta[1]), 9)))

    tree = cKDTree(pad_centers)
    pad_radii = np.asarray(
        [math.hypot(pad.width_mm, pad.height_mm) / 2.0 for pad in pads], dtype=float
    )
    ranked: list[tuple[tuple[float, float, float], tuple[float, float]]] = []
    for dx, dy in candidates:
        shifted = opening_centers + np.asarray([dx, dy])
        distances, nearest = tree.query(shifted, k=1)
        within = distances <= pad_radii[nearest]
        distinct = len(set(nearest[within].tolist()))
        residual = float(np.mean(distances[within])) if within.any() else float("inf")
        ranked.append(((-distinct / len(pads), residual, abs(dx) + abs(dy)), (dx, dy)))
    ranked.sort(key=lambda item: item[0])
    return [candidate for _, candidate in ranked[:8]]


def _opening_pad_matches(
    opening: BaseGeometry,
    pad_geometries: Sequence[BaseGeometry],
    *,
    overlap_threshold: float = 0.50,
    spatial_index: STRtree | None = None,
) -> list[int]:
    if opening.is_empty or opening.area <= 0:
        return []
    matched: list[int] = []
    indexes = (
        [int(index) for index in spatial_index.query(opening, predicate="intersects")]
        if spatial_index is not None
        else list(range(len(pad_geometries)))
    )
    for index in indexes:
        pad_geom = pad_geometries[index]
        overlap = opening.intersection(pad_geom).area / opening.area
        if overlap >= overlap_threshold:
            matched.append(index)
    return matched


def _score_alignment(
    transformed: Sequence[BaseGeometry], pads: Sequence[PadDefinition]
) -> tuple[float, float, int, int, int, list[list[int]]]:
    pad_geometries = [pad.geometry() for pad in pads]
    spatial_index = STRtree(pad_geometries)
    assignments: list[list[int]] = []
    matched_pad_indexes: set[int] = set()
    residuals: list[float] = []
    ambiguous = 0
    extras = 0
    matched_openings = 0
    for opening in transformed:
        matches = _opening_pad_matches(
            opening, pad_geometries, spatial_index=spatial_index
        )
        assignments.append(matches)
        if len(matches) == 1:
            pad_index = matches[0]
            matched_pad_indexes.add(pad_index)
            matched_openings += 1
            residuals.append(opening.centroid.distance(Point(pads[pad_index].x_mm, pads[pad_index].y_mm)))
        elif len(matches) > 1:
            ambiguous += 1
        else:
            extras += 1
    coverage = len(matched_pad_indexes) / len(pads) if pads else 0.0
    residual = float(np.mean(residuals)) if residuals else float("inf")
    return coverage, residual, matched_openings, ambiguous, extras, assignments


def select_alignment(
    openings: Sequence[BaseGeometry],
    pads: Sequence[PadDefinition],
    *,
    allow_mirror: bool = False,
) -> tuple[AlignmentCandidate, list[BaseGeometry]]:
    if not openings or not pads:
        raise ValueError("alignment requires Gerber openings and Pad rows")
    candidates: list[tuple[AlignmentCandidate, list[BaseGeometry]]] = []
    for mirrored in ((False, True) if allow_mirror else (False,)):
        for rotation in (0, 90, 180, 270):
            oriented = _oriented_openings(openings, rotation, mirrored)
            for dx, dy in _rank_translation_candidates(oriented, pads):
                transformed = [
                    affinity.translate(g, xoff=dx, yoff=dy) for g in oriented
                ]
                coverage, residual, matched, ambiguous, extras, _ = _score_alignment(
                    transformed, pads
                )
                candidate = AlignmentCandidate(
                    rotation,
                    mirrored,
                    dx,
                    dy,
                    coverage,
                    residual,
                    matched,
                    ambiguous,
                    extras,
                )
                candidates.append((candidate, transformed))
    candidates.sort(
        key=lambda pair: (
            -pair[0].coverage,
            pair[0].ambiguous_openings,
            pair[0].extra_openings,
            -pair[0].matched_openings,
            pair[0].residual_mm,
            pair[0].mirrored,
            pair[0].rotation_deg,
        )
    )
    return candidates[0]


def resolve_pad_thickness_mm(product_name: str, refdes: str) -> float | None:
    spec = get_stencil_spec(product_name)
    if not spec:
        return None
    main_raw = spec.get("thickness_main")
    if main_raw is None:
        return None
    try:
        main = float(main_raw)
    except (TypeError, ValueError):
        return None
    if main <= 0:
        return None
    if str(spec.get("stencil_type") or "").lower() != STENCIL_STEPPED:
        return main
    if get_profile_by_refdes(product_name, refdes) != PROFILE_PRECISION:
        return main
    precision_raw = spec.get("thickness_precision")
    if precision_raw is None:
        return None
    try:
        precision = float(precision_raw)
    except (TypeError, ValueError):
        return None
    return precision if precision > 0 else None


def analyze_stencil_import(
    *,
    product_name: str,
    side: str,
    pads: Sequence[PadDefinition],
    openings: Sequence[BaseGeometry],
    non_component_opening_indexes: Iterable[int] = (),
) -> ImportAnalysis:
    """Select rigid alignment, match windows, and calculate per-pad nominals."""
    side_value = normalize_side(side)
    if any(pad.side != side_value for pad in pads):
        raise ValueError("all Pad rows must use the selected side")
    candidate, transformed = select_alignment(
        openings, pads, allow_mirror=side_value == "BOTTOM"
    )
    pad_geometries = [pad.geometry() for pad in pads]
    spatial_index = STRtree(pad_geometries)
    assignments = [
        _opening_pad_matches(
            opening, pad_geometries, spatial_index=spatial_index
        )
        for opening in transformed
    ]
    non_component = {int(index) for index in non_component_opening_indexes}
    pad_openings: dict[int, list[BaseGeometry]] = {index: [] for index in range(len(pads))}
    ambiguous_indexes: list[int] = []
    extra_indexes: list[int] = []
    for opening_index, matches in enumerate(assignments):
        if len(matches) == 1:
            pad_openings[matches[0]].append(transformed[opening_index])
        elif len(matches) > 1:
            ambiguous_indexes.append(opening_index)
        elif opening_index not in non_component:
            extra_indexes.append(opening_index)

    nominals: list[dict[str, Any]] = []
    matched_pads = 0
    missing_thickness = 0
    unmatched_pads: list[str] = []
    for index, pad in enumerate(pads):
        assigned = pad_openings[index]
        thickness = resolve_pad_thickness_mm(product_name, pad.refdes)
        if assigned:
            unioned = unary_union(assigned)
            area = float(unioned.area)
            status = "MATCHED" if thickness is not None else "MISSING_THICKNESS"
            reason = "" if thickness is not None else "找不到可用鋼板厚度"
            nominal_volume = area * thickness if thickness is not None else None
            if thickness is not None and area > 0:
                matched_pads += 1
            else:
                missing_thickness += 1
        else:
            unioned = Polygon()
            area = None
            nominal_volume = None
            status = "UNMATCHED"
            reason = "沒有開窗達到 Pad 覆蓋門檻"
            unmatched_pads.append(f"{pad.refdes}/{pad.pad}")
        nominals.append(
            {
                "refdes": pad.refdes,
                "pad": pad.pad,
                "side": side_value,
                "opening_count": len(assigned),
                "nominal_area_mm2": area,
                "resolved_thickness_mm": thickness,
                "nominal_volume_mm3": nominal_volume,
                "match_status": status,
                "unmatched_reason": reason,
                "preview_geometry": mapping(unioned) if not unioned.is_empty else {},
            }
        )

    total = len(pads)
    summary = {
        "total_pads": total,
        "matched_pads": matched_pads,
        "coverage": matched_pads / total if total else 0.0,
        "duplicate_pad_rows": 0,
        "ambiguous_openings": len(ambiguous_indexes),
        "ambiguous_opening_indexes": ambiguous_indexes,
        "unclassified_extra_openings": len(extra_indexes),
        "extra_opening_indexes": extra_indexes,
        "non_component_openings": sorted(non_component),
        "missing_thickness_pads": missing_thickness,
        "unmatched_pads": unmatched_pads,
        "requires_user_overlay_confirmation": True,
    }
    return ImportAnalysis(candidate.as_dict(), summary, nominals, list(transformed))


def _normalize_join_key(series: pd.Series) -> pd.Series:
    return series.astype("string").fillna("").str.strip()


def _unit_multiplier(unit: str, feature: str) -> float | None:
    normalized = str(unit or "").strip().lower().replace("³", "3").replace("²", "2")
    normalized = normalized.replace("^", "").replace(" ", "")
    if feature == "Volume":
        return {"mm3": 1.0, "mm": 1.0, "in3": 25.4**3, "inch3": 25.4**3}.get(normalized)
    if feature == "Area":
        return {"mm2": 1.0, "mm": 1.0, "in2": 25.4**2, "inch2": 25.4**2}.get(normalized)
    if feature == "Height":
        return {"mm": 1.0, "millimeter": 1.0, "in": 25.4, "inch": 25.4}.get(normalized)
    return None


def derive_percentage_dataframe(
    dataframe: pd.DataFrame,
    *,
    product_name: str,
    side: str,
    measurement_units: dict[str, Any],
) -> DerivedPercentageResult:
    """Return an analysis copy in percent domain only when every filtered row matches.

    Raw input is never modified.  Any missing key, nominal, unit, or active
    version returns an unchanged copy with an explicit VERIFY contract.
    """
    source = dataframe.copy(deep=True)
    side_value = normalize_side(side)
    version = get_active_stencil_document(product_name, side_value)
    base_metadata: dict[str, Any] = {
        "value_domain": "raw",
        "stencil_version_id": None,
        "stencil_revision": "",
        "side": side_value,
        "matched": 0,
        "total": int(len(source)),
        "coverage": 0.0 if len(source) else 1.0,
        "verify": True,
        "verify_reasons": [],
        "unmatched_pads": [],
        "original_units": dict(measurement_units or {}),
    }
    if not version:
        base_metadata["verify_reasons"].append("沒有已啟用的鋼板開窗版本")
        return DerivedPercentageResult(source, base_metadata)

    refdes_col = "BaseRefDes" if "BaseRefDes" in source.columns else "RefDes"
    required = [refdes_col, "Pad", "Volume", "Area", "Height"]
    missing_cols = [column for column in required if column not in source.columns]
    if missing_cols:
        base_metadata["verify_reasons"].append("量測資料缺少欄位：" + ", ".join(missing_cols))
        return DerivedPercentageResult(source, base_metadata)

    unit_multipliers = {
        feature: _unit_multiplier(str((measurement_units or {}).get(feature) or ""), feature)
        for feature in ("Volume", "Area", "Height")
    }
    unsupported = [feature for feature, factor in unit_multipliers.items() if factor is None]
    if unsupported:
        base_metadata["verify_reasons"].append(
            "量測單位缺失或不支援：" + ", ".join(unsupported)
        )
        return DerivedPercentageResult(source, base_metadata)

    nominals = pd.DataFrame(list_stencil_pad_nominals(int(version["id"])))
    if nominals.empty:
        base_metadata["verify_reasons"].append("現用鋼板版本沒有 Pad 名義值")
        return DerivedPercentageResult(source, base_metadata)
    nominals = nominals[
        ["refdes", "pad", "match_status", "nominal_area_mm2", "resolved_thickness_mm", "nominal_volume_mm3"]
    ].copy()
    nominals["_refdes_key"] = _normalize_join_key(nominals["refdes"])
    nominals["_pad_key"] = _normalize_join_key(nominals["pad"])
    if nominals.duplicated(["_refdes_key", "_pad_key"]).any():
        base_metadata["verify_reasons"].append("現用鋼板版本的 RefDes/Pad 名義值不唯一")
        return DerivedPercentageResult(source, base_metadata)

    working = source.copy()
    working["_refdes_key"] = _normalize_join_key(working[refdes_col])
    working["_pad_key"] = _normalize_join_key(working["Pad"])
    working["_stencil_row_order"] = np.arange(len(working))
    merged = working.merge(
        nominals.drop(columns=["refdes", "pad"]),
        how="left",
        on=["_refdes_key", "_pad_key"],
        validate="many_to_one",
        sort=False,
    ).sort_values("_stencil_row_order", kind="stable")
    # merge() resets the index; restore the caller's labels so the derived
    # frame stays aligned with filtered_df (many_to_one left merge keeps rows).
    merged.index = source.index
    valid = (
        merged["match_status"].eq("MATCHED")
        & pd.to_numeric(merged["nominal_area_mm2"], errors="coerce").gt(0)
        & pd.to_numeric(merged["resolved_thickness_mm"], errors="coerce").gt(0)
        & pd.to_numeric(merged["nominal_volume_mm3"], errors="coerce").gt(0)
    )
    matched = int(valid.sum())
    total = int(len(merged))
    coverage = matched / total if total else 1.0
    unmatched_keys = sorted(
        {
            f"{refdes}/{pad}"
            for refdes, pad in merged.loc[~valid, ["_refdes_key", "_pad_key"]].itertuples(index=False, name=None)
        }
    )
    base_metadata.update(
        {
            "stencil_version_id": int(version["id"]),
            "stencil_revision": str(version.get("revision") or ""),
            "stencil_no": str(version.get("stencil_no") or ""),
            "matched": matched,
            "total": total,
            "coverage": coverage,
            "unmatched_pads": unmatched_keys,
        }
    )
    if coverage < 1.0:
        base_metadata["verify_reasons"].append(f"Pad 覆蓋不足：{matched}/{total}")
        return DerivedPercentageResult(source, base_metadata)

    derivation_broken = False
    for feature, nominal_col in (
        ("Volume", "nominal_volume_mm3"),
        ("Area", "nominal_area_mm2"),
        ("Height", "resolved_thickness_mm"),
    ):
        factor = unit_multipliers[feature]
        if factor is None:  # narrowed above; defensive for future feature additions
            raise RuntimeError(f"missing unit multiplier for {feature}")
        raw = pd.to_numeric(merged[feature], errors="coerce")
        # A missing/non-finite raw reading stays a missing value (engines drop
        # it); only a finite reading that derives to non-finite is a VERIFY.
        raw_finite = np.isfinite(raw.to_numpy(dtype=float))
        measured = raw.where(raw_finite) * float(factor)
        denominator = pd.to_numeric(merged[nominal_col], errors="coerce")
        derived_values = measured / denominator * 100.0
        if not np.isfinite(derived_values.to_numpy(dtype=float)[raw_finite]).all():
            derivation_broken = True
        merged[feature] = derived_values
    if derivation_broken:
        base_metadata["verify_reasons"].append("衍生百分比包含非有限值")
        return DerivedPercentageResult(source, base_metadata)

    drop_cols = [
        "_refdes_key",
        "_pad_key",
        "_stencil_row_order",
        "match_status",
        "nominal_area_mm2",
        "resolved_thickness_mm",
        "nominal_volume_mm3",
    ]
    derived = merged.drop(columns=[column for column in drop_cols if column in merged.columns])
    base_metadata.update(
        {
            "value_domain": "percent",
            "verify": False,
            "verify_reasons": [],
            "formula": {
                "Volume": "measured_volume_mm3 / nominal_volume_mm3 * 100",
                "Area": "measured_area_mm2 / nominal_area_mm2 * 100",
                "Height": "measured_height_mm / resolved_thickness_mm * 100",
            },
        }
    )
    return DerivedPercentageResult(derived, base_metadata)
