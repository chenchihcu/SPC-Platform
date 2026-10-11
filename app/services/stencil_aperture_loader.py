"""Safe, explicit loaders for stencil aperture geometry sources.

The public result is always millimetre-based Shapely geometry.  Format-specific
metadata is retained so the import snapshot can disclose exactly what was
parsed.  Unsupported constructs fail the entire load; partial geometry is
never returned as if it were complete.
"""
from __future__ import annotations

import math
import re
import stat
import tarfile
import warnings
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Iterator, Sequence

import ezdxf  # type: ignore[import-untyped]
from ezdxf import units as dxf_units  # type: ignore[import-untyped]
from ezdxf.enums import InsertUnits  # type: ignore[import-untyped]
from ezdxf.path import from_hatch, make_path  # type: ignore[import-untyped]
from gerbonara import GerberFile  # type: ignore[import-untyped]
from gerbonara.graphic_primitives import MM  # type: ignore[import-untyped]
from lxml import etree  # type: ignore[import-untyped]
from shapely import affinity  # type: ignore[import-untyped]
from shapely.geometry import (  # type: ignore[import-untyped]
    LineString,
    Point,
    Polygon,
    box,
)
from shapely.geometry.base import BaseGeometry  # type: ignore[import-untyped]
from shapely.ops import polygonize_full, unary_union  # type: ignore[import-untyped]

APERTURE_PARSER_VERSION = (
    "stencil-aperture-3;gerbonara-1.6.3;ezdxf-1.4.4;lxml-6.0.2;shapely-2.1.2"
)
GERBER_SUFFIXES = frozenset({".gtp", ".gbp", ".gbr", ".ger", ".pho"})
IPC2581_SUFFIXES = frozenset({".xml", ".ipc2581"})
DXF_SUFFIXES = frozenset({".dxf"})
ODB_ARCHIVE_SUFFIXES = (".tgz", ".tar.gz", ".tar")
SUPPORTED_APERTURE_SUFFIXES = frozenset(
    {*GERBER_SUFFIXES, *IPC2581_SUFFIXES, *DXF_SUFFIXES, ".zip", ".tgz", ".gz", ".tar"}
)

_MAX_ARCHIVE_FILES = 100_000
_MAX_ARCHIVE_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
_MAX_ARCHIVE_MEMBER_BYTES = 512 * 1024 * 1024
_MAX_XML_BYTES = 1024 * 1024 * 1024
_ARC_MAX_ERROR_MM = 0.001
# IPC-2581 CadHeader@units enumeration (MILLIMETER/INCH/MICRON) -> mm factor.
# "MM" is kept as a tolerated short alias.
_IPC_UNIT_TO_MM = {"MILLIMETER": 1.0, "MM": 1.0, "INCH": 25.4, "MICRON": 0.001}
_PASTE_WORDS = ("paste", "stencil", "aperture", "solderpaste", "solder_paste")


@dataclass(frozen=True)
class ApertureLoadResult:
    """Fully parsed aperture source with explicit provenance."""

    openings: list[BaseGeometry]
    format_id: str
    format_label: str
    source_layer: str
    parser_version: str = APERTURE_PARSER_VERSION
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class _ArchiveEntry:
    original_name: str
    canonical_name: str
    size: int


@dataclass(frozen=True)
class _LegacyPhoNormalization:
    text: str
    short_g_codes: int
    short_d_codes: int
    implicit_operations: int
    missing_i_offsets: int
    missing_j_offsets: int
    empty_aperture_definitions: int

    def disclosure(self) -> str:
        """Return an operator-facing audit summary for the bounded rewrite."""
        return (
            "Legacy PHO 正規化："
            f"G-code={self.short_g_codes}、D-code={self.short_d_codes}、"
            f"隱含 D={self.implicit_operations}、"
            f"缺省 I/J={self.missing_i_offsets}/{self.missing_j_offsets}、"
            f"空 AD={self.empty_aperture_definitions}"
        )


class _ArchiveBundle:
    """Read a ZIP/TAR archive without extracting untrusted paths."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.kind = "zip" if zipfile.is_zipfile(path) else "tar"
        self._archive: zipfile.ZipFile | tarfile.TarFile
        if self.kind == "zip":
            self._archive = zipfile.ZipFile(path)
            raw_entries = self._zip_entries(self._archive)
        else:
            self._archive = tarfile.open(path, mode="r:*")
            raw_entries = self._tar_entries(self._archive)
        if len(raw_entries) > _MAX_ARCHIVE_FILES:
            self.close()
            raise ValueError(f"封裝檔案數超過安全上限 {_MAX_ARCHIVE_FILES}")
        total = sum(entry.size for entry in raw_entries)
        if total > _MAX_ARCHIVE_TOTAL_BYTES:
            self.close()
            raise ValueError("封裝解壓後總大小超過 2 GiB 安全上限")
        self.entries: dict[str, _ArchiveEntry] = {}
        for entry in raw_entries:
            key = entry.canonical_name.casefold()
            if key in self.entries:
                self.close()
                raise ValueError(f"封裝含大小寫重複路徑：{entry.canonical_name}")
            self.entries[key] = entry

    @staticmethod
    def _canonical_name(name: str) -> str:
        normalized = name.replace("\\", "/")
        pure = PurePosixPath(normalized)
        if pure.is_absolute() or ".." in pure.parts:
            raise ValueError(f"封裝含不安全路徑：{name}")
        return "/".join(part for part in pure.parts if part not in {"", "."})

    @classmethod
    def _zip_entries(cls, archive: zipfile.ZipFile) -> list[_ArchiveEntry]:
        entries: list[_ArchiveEntry] = []
        for info in archive.infolist():
            if info.is_dir():
                continue
            mode = info.external_attr >> 16
            if mode and stat.S_ISLNK(mode):
                raise ValueError(f"ZIP 不接受符號連結：{info.filename}")
            if info.file_size > _MAX_ARCHIVE_MEMBER_BYTES:
                raise ValueError(f"封裝成員過大：{info.filename}")
            canonical = cls._canonical_name(info.filename)
            entries.append(_ArchiveEntry(info.filename, canonical, info.file_size))
        return entries

    @classmethod
    def _tar_entries(cls, archive: tarfile.TarFile) -> list[_ArchiveEntry]:
        entries: list[_ArchiveEntry] = []
        for member in archive.getmembers():
            if member.isdir():
                continue
            if not member.isfile():
                raise ValueError(f"TAR 只接受一般檔案：{member.name}")
            if member.size > _MAX_ARCHIVE_MEMBER_BYTES:
                raise ValueError(f"封裝成員過大：{member.name}")
            canonical = cls._canonical_name(member.name)
            entries.append(_ArchiveEntry(member.name, canonical, member.size))
        return entries

    def close(self) -> None:
        """Close the underlying archive handle."""
        self._archive.close()

    def __enter__(self) -> _ArchiveBundle:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def has(self, canonical_name: str) -> bool:
        """Return whether a canonical member path exists."""
        return canonical_name.casefold() in self.entries

    def read_bytes(self, canonical_name: str) -> bytes:
        """Read one validated archive member as bytes."""
        entry = self.entries.get(canonical_name.casefold())
        if entry is None:
            raise FileNotFoundError(canonical_name)
        if self.kind == "zip":
            assert isinstance(self._archive, zipfile.ZipFile)
            return self._archive.read(entry.original_name)
        assert isinstance(self._archive, tarfile.TarFile)
        handle = self._archive.extractfile(entry.original_name)
        if handle is None:
            raise FileNotFoundError(entry.original_name)
        with handle:
            return handle.read(_MAX_ARCHIVE_MEMBER_BYTES + 1)

    def read_text(self, canonical_name: str) -> str:
        """Read one validated archive member as decoded text."""
        data = self.read_bytes(canonical_name)
        if len(data) > _MAX_ARCHIVE_MEMBER_BYTES:
            raise ValueError(f"封裝成員過大：{canonical_name}")
        try:
            return data.decode("utf-8-sig")
        except UnicodeDecodeError:
            return data.decode("latin-1")


def aperture_source_suffix(path: str | Path) -> str:
    """Return a supported compound suffix for managed storage."""
    name = Path(path).name.casefold()
    if name.endswith(".tar.gz"):
        return ".tar.gz"
    return Path(name).suffix


def detect_aperture_format(path: str | Path) -> str:
    """Detect the source container without trusting only a ``.zip`` suffix."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(str(source))
    suffix = aperture_source_suffix(source)
    if suffix in GERBER_SUFFIXES:
        return "gerber"
    if suffix in IPC2581_SUFFIXES:
        return "ipc2581"
    if suffix in DXF_SUFFIXES:
        return "dxf"
    if suffix in ODB_ARCHIVE_SUFFIXES:
        return "odbpp"
    if suffix != ".zip":
        raise ValueError(f"不支援的開窗文件副檔名：{suffix or '(none)'}")
    with _ArchiveBundle(source) as bundle:
        matrix_files = [
            entry.canonical_name
            for entry in bundle.entries.values()
            if entry.canonical_name.casefold().endswith("/matrix/matrix")
            or entry.canonical_name.casefold() == "matrix/matrix"
        ]
        if matrix_files:
            return "odbpp"
        gerbers = [
            entry
            for entry in bundle.entries.values()
            if Path(entry.canonical_name).suffix.casefold() in GERBER_SUFFIXES
        ]
        if gerbers:
            return "gerber_zip"
    raise ValueError("ZIP 內找不到 ODB++ matrix 或可辨識的 Paste Gerber")


def _normalize_side(side: str) -> str:
    value = (side or "").strip().upper()
    if value not in {"TOP", "BOTTOM"}:
        raise ValueError("side must be TOP or BOTTOM")
    return value


def _local_name(element: Any) -> str:
    return str(etree.QName(element).localname)


def _polygon_parts(geometry: BaseGeometry) -> Iterator[BaseGeometry]:
    if geometry.is_empty:
        return
    if geometry.geom_type == "Polygon":
        if geometry.area > 1e-12:
            yield geometry
        return
    if hasattr(geometry, "geoms"):
        for part in geometry.geoms:
            yield from _polygon_parts(part)


def _clean_openings(geometries: Iterable[BaseGeometry], *, label: str) -> list[BaseGeometry]:
    openings: list[BaseGeometry] = []
    for geometry in geometries:
        fixed = geometry if geometry.is_valid else geometry.buffer(0)
        openings.extend(_polygon_parts(fixed))
    if not openings:
        raise ValueError(f"{label} 中沒有可計算的 Paste 開窗")
    return openings


def _arc_points(
    start: tuple[float, float],
    end: tuple[float, float],
    center: tuple[float, float],
    clockwise: bool,
) -> list[tuple[float, float]]:
    radius = math.dist(start, center)
    if radius <= 1e-12 or not math.isclose(
        radius,
        math.dist(end, center),
        rel_tol=5e-3,
        abs_tol=0.0003,
    ):
        raise ValueError("圓弧起點/終點與圓心不構成有效圓弧")
    start_angle = math.atan2(start[1] - center[1], start[0] - center[0])
    end_angle = math.atan2(end[1] - center[1], end[0] - center[0])
    delta = end_angle - start_angle
    if clockwise:
        while delta >= 0:
            delta -= 2.0 * math.pi
    else:
        while delta <= 0:
            delta += 2.0 * math.pi
    if math.dist(start, end) <= 1e-9:
        delta = -2.0 * math.pi if clockwise else 2.0 * math.pi
    if radius <= _ARC_MAX_ERROR_MM:
        maximum_step = math.pi / 18.0
    else:
        ratio = max(-1.0, min(1.0, 1.0 - _ARC_MAX_ERROR_MM / radius))
        maximum_step = max(math.pi / 180.0, 2.0 * math.acos(ratio))
    segments = max(2, int(math.ceil(abs(delta) / maximum_step)))
    points = [
        (
            center[0] + radius * math.cos(start_angle + delta * index / segments),
            center[1] + radius * math.sin(start_angle + delta * index / segments),
        )
        for index in range(1, segments + 1)
    ]
    # IPC-2581/ODB++ exporters quantize coordinates independently.  Snap only
    # the final sampled point back to the declared endpoint after the bounded
    # radius check so adjacent segments remain exactly connected.
    points[-1] = end
    return points


def _primitive_geometry(primitive: Any) -> BaseGeometry:
    arc_poly = primitive.to_arc_poly().approximate_arcs(max_error=0.0001)
    if not arc_poly.outline:
        return Polygon()
    geometry = Polygon(arc_poly.outline)
    return geometry if geometry.is_valid else geometry.buffer(0)


def _gerber_file_openings(gerber: GerberFile) -> list[BaseGeometry]:
    openings: list[BaseGeometry] = []
    for obj in gerber.objects:
        geometry: BaseGeometry = Polygon()
        for primitive in obj.to_primitives(unit=MM):
            piece = _primitive_geometry(primitive)
            if piece.is_empty:
                continue
            if bool(getattr(primitive, "polarity_dark", True)):
                geometry = geometry.union(piece)
            else:
                geometry = geometry.difference(piece)
        openings.extend(_polygon_parts(geometry))
    return _clean_openings(openings, label="Gerber")


def _gerber_identifiers(name: str, text: str) -> set[str]:
    identifiers = {Path(name).stem.upper()}
    identifiers.update(
        match.group(1).strip().upper()
        for match in re.finditer(r"%LN([^*%]+)\*%", text, flags=re.IGNORECASE)
    )
    return {re.sub(r"[^A-Z0-9]+", "", value) for value in identifiers if value}


def _legacy_pho_role(name: str, text: str) -> str:
    """Classify a PHO layer without treating every photoplot as an aperture."""
    identifiers = _gerber_identifiers(name, text)
    reference = any(
        re.search(r"(?:TXT|TEXT|LEGEND|SILK|SILKSCREEN|OVERLAY)(?:TOP|BOT|BOTTOM)?$", value)
        for value in identifiers
    )
    aperture = any(
        re.search(r"(?:SMD|PASTE|CREAM|STENCIL|APERTURE)(?:TOP|BOT|BOTTOM)?$", value)
        for value in identifiers
    )
    if reference and aperture:
        return "conflict"
    if reference:
        return "reference"
    if aperture:
        return "aperture"
    return "unknown"


def _gerber_declared_side(name: str, text: str) -> str | None:
    upper = text.upper().replace(" ", "")
    top_attr = "TF.FILEFUNCTION,PASTE,TOP" in upper
    bottom_attr = any(
        token in upper
        for token in ("TF.FILEFUNCTION,PASTE,BOT", "TF.FILEFUNCTION,PASTE,BOTTOM")
    )
    if top_attr != bottom_attr:
        return "TOP" if top_attr else "BOTTOM"
    suffix = Path(name).suffix.casefold()
    if suffix == ".gtp":
        return "TOP"
    if suffix == ".gbp":
        return "BOTTOM"
    if suffix == ".pho":
        compact_identifiers = _gerber_identifiers(name, text)
        role_words = (
            r"(?:SMD|PASTE|CREAM|STENCIL|APERTURE|TXT|TEXT|LEGEND|"
            r"SILK|SILKSCREEN|OVERLAY)"
        )
        compact_top = any(
            re.search(role_words + r"TOP$", value) for value in compact_identifiers
        )
        compact_bottom = any(
            re.search(role_words + r"(?:BOT|BOTTOM)$", value)
            for value in compact_identifiers
        )
        if compact_top != compact_bottom:
            return "TOP" if compact_top else "BOTTOM"
    normalized = re.sub(r"[^a-z0-9]+", "_", Path(name).stem.casefold())
    top_name = "top" in normalized.split("_")
    bottom_name = bool({"bottom", "bot"} & set(normalized.split("_")))
    if top_name != bottom_name:
        return "TOP" if top_name else "BOTTOM"
    return None


def _normalize_legacy_pho(text: str) -> _LegacyPhoNormalization:
    """Normalize only legacy constructs observed in validated PHO samples."""
    normalized_lines: list[str] = []
    short_g_codes = 0
    short_d_codes = 0
    implicit_operations = 0
    missing_i_offsets = 0
    missing_j_offsets = 0
    empty_aperture_definitions = 0
    modal_operation: str | None = None
    interpolation_mode = "G01"

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if line == "%AD*%":
            empty_aperture_definitions += 1
            continue

        line, count = re.subn(
            r"^G([123])(?=[XYIJD])",
            r"G0\1",
            line,
        )
        short_g_codes += count
        if re.match(r"^(?:G0[123])?[XYIJ]", line) or re.fullmatch(r"D[123]\*", line):
            line, count = re.subn(
                r"D([123])(?=\*)",
                r"D0\1",
                line,
            )
            short_d_codes += count

        mode_match = re.match(r"^(G0[123])", line)
        if mode_match:
            interpolation_mode = mode_match.group(1)
        is_coordinate = bool(re.match(r"^(?:G0[123])?[XYIJ]", line))
        operation_match = re.search(r"(D0[123])(?=\*)", line)
        if operation_match:
            modal_operation = operation_match.group(1)
        elif is_coordinate:
            if modal_operation is None:
                raise ValueError(
                    f"PHO 第 {line_number} 行省略 D 操作，但前文沒有可沿用的 modal D"
                )
            if not line.endswith("*"):
                raise ValueError(f"PHO 第 {line_number} 行座標命令缺少終止符 *")
            line = f"{line[:-1]}{modal_operation}*"
            implicit_operations += 1

        if is_coordinate and interpolation_mode in {"G02", "G03"} and "D01" in line:
            has_i = bool(re.search(r"I[+-]?\d+", line))
            has_j = bool(re.search(r"J[+-]?\d+", line))
            if has_j and not has_i:
                line = line.replace("J", "I0J", 1)
                missing_i_offsets += 1
            elif has_i and not has_j:
                line = line.replace("D01", "J0D01", 1)
                missing_j_offsets += 1

        normalized_lines.append(line)

    return _LegacyPhoNormalization(
        text="\n".join(normalized_lines),
        short_g_codes=short_g_codes,
        short_d_codes=short_d_codes,
        implicit_operations=implicit_operations,
        missing_i_offsets=missing_i_offsets,
        missing_j_offsets=missing_j_offsets,
        empty_aperture_definitions=empty_aperture_definitions,
    )


def _parse_legacy_pho(text: str, filename: str) -> tuple[GerberFile, tuple[str, ...]]:
    normalization = _normalize_legacy_pho(text)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        gerber = GerberFile.from_string(normalization.text, filename=filename)
    unsupported = [
        str(item.message)
        for item in caught
        if not (
            issubclass(item.category, DeprecationWarning)
            and "Deprecated LN (load name) statement" in str(item.message)
        )
    ]
    if unsupported:
        details = "; ".join(unsupported[:3])
        raise ValueError(f"PHO 正規化後仍有未支援或不明語法：{details}")
    return gerber, (normalization.disclosure(),)


def _parse_gerber_source(name: str, text: str) -> tuple[GerberFile, tuple[str, ...]]:
    if Path(name).suffix.casefold() == ".pho":
        return _parse_legacy_pho(text, name)
    return GerberFile.from_string(text, filename=name), ()


def _load_single_gerber(source: Path, side: str) -> ApertureLoadResult:
    text = source.read_text(encoding="utf-8-sig", errors="replace")
    is_legacy_pho = source.suffix.casefold() == ".pho"
    if is_legacy_pho:
        role = _legacy_pho_role(source.name, text)
        if role == "reference":
            raise ValueError(
                f"PHO {source.name} 是 TXT/Legend 文字參考層，不是鋼板開窗層"
            )
        if role == "conflict":
            raise ValueError(f"PHO {source.name} 的 layer name 同時像開窗與文字層，拒絕猜測")
        if role == "unknown":
            raise ValueError(
                f"PHO {source.name} 無法由檔名或 LN metadata 確認為 SMD/Paste 開窗層"
            )
    declared = _gerber_declared_side(source.name, text)
    if is_legacy_pho and declared is None:
        raise ValueError(f"PHO {source.name} 無法確認 TOP/BOTTOM，拒絕猜測 Side")
    if declared and declared != side:
        raise ValueError(f"Gerber 宣告 Side={declared}，與匯入 Side={side} 不符")
    gerber, parse_warnings = _parse_gerber_source(source.name, text)
    result_warnings: tuple[str, ...] = parse_warnings
    if declared is None:
        result_warnings += ("Gerber 未帶可辨識 Side metadata；必須以疊圖人工確認",)
    return ApertureLoadResult(
        openings=_gerber_file_openings(gerber),
        format_id="gerber",
        format_label=(
            "Legacy Gerber/Photoplotter (.pho)"
            if is_legacy_pho
            else "Gerber RS-274X/X2"
        ),
        source_layer=source.name,
        warnings=result_warnings,
    )


def _load_gerber_zip(source: Path, side: str) -> ApertureLoadResult:
    with _ArchiveBundle(source) as bundle:
        candidates: list[tuple[_ArchiveEntry, str, str | None]] = []
        excluded_pho_layers: list[str] = []
        for entry in bundle.entries.values():
            if Path(entry.canonical_name).suffix.casefold() not in GERBER_SUFFIXES:
                continue
            text = bundle.read_text(entry.canonical_name)
            if Path(entry.canonical_name).suffix.casefold() == ".pho":
                role = _legacy_pho_role(entry.canonical_name, text)
                if role != "aperture":
                    excluded_pho_layers.append(entry.canonical_name)
                    continue
            candidates.append(
                (entry, text, _gerber_declared_side(entry.canonical_name, text))
            )
        matched = [item for item in candidates if item[2] == side]
        result_warnings: tuple[str, ...] = ()
        if len(matched) == 1:
            selected = matched[0]
        elif len(matched) > 1:
            names = ", ".join(item[0].canonical_name for item in matched[:8])
            raise ValueError(f"ZIP 內有多個 {side} Paste Gerber：{names}")
        elif len(candidates) == 1 and candidates[0][2] is None:
            selected = candidates[0]
            result_warnings = ("ZIP 內唯一 Gerber 未帶 Side metadata；必須以疊圖人工確認",)
        else:
            names = ", ".join(item[0].canonical_name for item in candidates[:8])
            excluded = ", ".join(excluded_pho_layers[:8])
            suffix = f"；已排除非開窗 PHO：{excluded}" if excluded else ""
            raise ValueError(
                f"ZIP 無法唯一選出 {side} Paste Gerber；候選：{names or '無'}{suffix}"
            )
        gerber, parse_warnings = _parse_gerber_source(
            selected[0].canonical_name, selected[1]
        )
        result_warnings += parse_warnings
        if excluded_pho_layers:
            result_warnings += (
                "已排除非開窗 PHO 層：" + ", ".join(excluded_pho_layers[:8]),
            )
        openings = _gerber_file_openings(gerber)
        layer_name = selected[0].canonical_name
    return ApertureLoadResult(
        openings=openings,
        format_id="gerber_zip",
        format_label="Gerber bundle (ZIP)",
        source_layer=layer_name,
        warnings=result_warnings,
    )


def _ipc_number(element: Any, name: str, factor: float) -> float:
    try:
        value = float(element.get(name)) * factor
    except (TypeError, ValueError) as exc:
        raise ValueError(f"IPC-2581 {name} 不是有效數字") from exc
    if not math.isfinite(value):
        raise ValueError(f"IPC-2581 {name} 含非有限數字")
    return value


def _ipc_path_points(element: Any, factor: float) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for node in element.iter():
        name = _local_name(node)
        if name == "PolyBegin":
            points = [
                (_ipc_number(node, "x", factor), _ipc_number(node, "y", factor))
            ]
        elif name == "PolyStepSegment":
            if not points:
                raise ValueError("IPC-2581 PolyStepSegment 缺少 PolyBegin")
            points.append((_ipc_number(node, "x", factor), _ipc_number(node, "y", factor)))
        elif name == "PolyStepCurve":
            if not points:
                raise ValueError("IPC-2581 PolyStepCurve 缺少 PolyBegin")
            end = (_ipc_number(node, "x", factor), _ipc_number(node, "y", factor))
            center = (
                _ipc_number(node, "centerX", factor),
                _ipc_number(node, "centerY", factor),
            )
            clockwise = str(node.get("clockwise") or "false").casefold() == "true"
            points.extend(_arc_points(points[-1], end, center, clockwise))
    return points


def _combine_contour_polygons(polygons: Sequence[BaseGeometry]) -> BaseGeometry:
    result: BaseGeometry = Polygon()
    for geometry in sorted(polygons, key=lambda item: item.area, reverse=True):
        if not result.is_empty and geometry.within(result):
            result = result.difference(geometry)
        else:
            result = result.union(geometry)
    return result


def _ipc_layer_feature_geometries(
    layer_feature: Any, factor: float
) -> tuple[list[BaseGeometry], set[str]]:
    geometries: list[BaseGeometry] = []
    unsupported: set[str] = set()
    allowed_non_geometry = {"Location", "ColorRef", "UserSpecial", "NonstandardAttribute"}
    for features in (node for node in layer_feature.iter() if _local_name(node) == "Features"):
        location_x = 0.0
        location_y = 0.0
        for child in features:
            if _local_name(child) == "Location":
                location_x = _ipc_number(child, "x", factor)
                location_y = _ipc_number(child, "y", factor)
                break
        for child in features:
            name = _local_name(child)
            geometry: BaseGeometry | None = None
            if name == "Contour":
                contour_parts: list[BaseGeometry] = []
                for polygon_node in (
                    node for node in child.iter() if _local_name(node) == "Polygon"
                ):
                    points = _ipc_path_points(polygon_node, factor)
                    if len(points) < 3:
                        raise ValueError("IPC-2581 Contour polygon 點數不足")
                    polygon = Polygon(points)
                    contour_parts.append(polygon if polygon.is_valid else polygon.buffer(0))
                geometry = _combine_contour_polygons(contour_parts)
            elif name == "Polyline":
                points = _ipc_path_points(child, factor)
                line_desc = next(
                    (node for node in child.iter() if _local_name(node) == "LineDesc"),
                    None,
                )
                if len(points) < 2 or line_desc is None:
                    raise ValueError("IPC-2581 Polyline 缺少路徑或 LineDesc")
                width = _ipc_number(line_desc, "lineWidth", factor)
                if width <= 0:
                    raise ValueError("IPC-2581 Polyline lineWidth 必須大於 0")
                line_end = str(line_desc.get("lineEnd") or "ROUND").upper()
                cap_style = 1 if line_end == "ROUND" else 2
                geometry = LineString(points).buffer(width / 2.0, cap_style=cap_style)
            elif name not in allowed_non_geometry:
                unsupported.add(name)
            if geometry is not None and not geometry.is_empty:
                if location_x or location_y:
                    geometry = affinity.translate(geometry, location_x, location_y)
                geometries.append(geometry)
    return geometries, unsupported


def _load_ipc2581(source: Path, side: str) -> ApertureLoadResult:
    if source.stat().st_size > _MAX_XML_BYTES:
        raise ValueError("IPC-2581 檔案超過 1 GiB 安全上限")
    units: str | None = None
    revision = ""
    paste_layers: set[str] = set()
    layer_geometries: dict[str, list[BaseGeometry]] = defaultdict(list)
    unsupported: set[str] = set()
    capturing: Any | None = None
    root_seen = False
    context = etree.iterparse(
        str(source),
        events=("start", "end"),
        huge_tree=True,
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
    )
    try:
        for event, element in context:
            name = _local_name(element)
            if event == "start":
                if not root_seen:
                    root_seen = True
                    if name != "IPC-2581":
                        raise ValueError("XML root 不是 IPC-2581")
                    revision = str(element.get("revision") or "")
                if name == "LayerFeature" and str(element.get("layerRef") or "") in paste_layers:
                    capturing = element
                continue
            if capturing is not None:
                if element is capturing:
                    if units not in _IPC_UNIT_TO_MM:
                        raise ValueError("IPC-2581 LayerFeature 出現於 CadHeader units 之前")
                    factor = _IPC_UNIT_TO_MM[units]
                    parsed, unknown = _ipc_layer_feature_geometries(element, factor)
                    layer_geometries[str(element.get("layerRef") or "")].extend(parsed)
                    unsupported.update(unknown)
                    element.clear()
                    capturing = None
                continue
            if name == "CadHeader":
                units = str(element.get("units") or "").upper()
                if units not in _IPC_UNIT_TO_MM:
                    raise ValueError("IPC-2581 CadHeader units 必須是 MILLIMETER、INCH 或 MICRON")
            elif name == "Layer":
                function = re.sub(r"[^A-Z]", "", str(element.get("layerFunction") or "").upper())
                layer_side = str(element.get("side") or "").upper()
                if function in {"PASTEMASK", "SOLDERPASTE", "PASTE"} and layer_side == side:
                    paste_layers.add(str(element.get("name") or ""))
            element.clear()
    except etree.XMLSyntaxError as exc:
        raise ValueError(f"IPC-2581 XML 語法錯誤：{exc}") from exc
    finally:
        del context
    if not paste_layers:
        raise ValueError(f"IPC-2581 找不到 Side={side} 的 PASTEMASK layer")
    if unsupported:
        raise ValueError("IPC-2581 Paste layer 含未支援幾何：" + ", ".join(sorted(unsupported)))
    populated = {name: items for name, items in layer_geometries.items() if items}
    if len(populated) != 1:
        raise ValueError(
            f"IPC-2581 無法唯一選出 {side} Paste layer："
            + (", ".join(sorted(populated)) or "沒有幾何")
        )
    layer_name, geometries = next(iter(populated.items()))
    openings = _clean_openings(geometries, label="IPC-2581")
    return ApertureLoadResult(
        openings=openings,
        format_id="ipc2581",
        format_label=f"IPC-2581{revision or ''}",
        source_layer=layer_name,
    )


def _layer_side_hint(name: str) -> str | None:
    normalized = re.sub(r"[^a-z0-9]+", "_", name.casefold())
    tokens = set(normalized.split("_"))
    top = bool({"top", "spt", "toppaste", "pastetop"} & tokens) or "pastetop" in normalized
    bottom = bool({"bottom", "bot", "spb", "bottompaste", "pastebottom"} & tokens)
    if top != bottom:
        return "TOP" if top else "BOTTOM"
    return None


def _dxf_paths_geometry(paths: Iterable[Any], factor: float) -> BaseGeometry:
    polygons: list[BaseGeometry] = []
    for path in paths:
        if not path.is_closed:
            raise ValueError("DXF HATCH 含未閉合 boundary")
        points = [(float(item.x) * factor, float(item.y) * factor) for item in path.flattening(0.001 / factor, 8)]
        if len(points) < 3:
            raise ValueError("DXF 閉合 boundary 點數不足")
        polygon = Polygon(points)
        polygons.append(polygon if polygon.is_valid else polygon.buffer(0))
    return _combine_contour_polygons(polygons)


def _dxf_entity_geometry(
    entity: Any, factor: float
) -> tuple[list[BaseGeometry], list[LineString]]:
    entity_type = str(entity.dxftype()).upper()
    if entity_type == "INSERT":
        geometries: list[BaseGeometry] = []
        lines: list[LineString] = []
        for virtual in entity.virtual_entities():
            child_geometries, child_lines = _dxf_entity_geometry(virtual, factor)
            geometries.extend(child_geometries)
            lines.extend(child_lines)
        return geometries, lines
    if entity_type == "CIRCLE":
        center = entity.dxf.center
        radius = float(entity.dxf.radius) * factor
        return [Point(float(center.x) * factor, float(center.y) * factor).buffer(radius)], []
    if entity_type == "HATCH":
        return [_dxf_paths_geometry(from_hatch(entity), factor)], []
    if entity_type in {"LWPOLYLINE", "POLYLINE", "ELLIPSE", "SPLINE", "ARC", "LINE"}:
        path = make_path(entity)
        points = [
            (float(item.x) * factor, float(item.y) * factor)
            for item in path.flattening(0.001 / factor, 8)
        ]
        if path.is_closed:
            if len(points) < 3:
                raise ValueError(f"DXF {entity_type} 閉合幾何點數不足")
            polygon = Polygon(points)
            return [polygon if polygon.is_valid else polygon.buffer(0)], []
        if len(points) >= 2:
            return [], [LineString(points)]
        return [], []
    if entity_type in {"SOLID", "TRACE", "3DFACE"}:
        points = []
        for name in ("vtx0", "vtx1", "vtx2", "vtx3"):
            value = entity.dxf.get(name)
            if value is not None:
                point = (float(value.x) * factor, float(value.y) * factor)
                if not points or point != points[-1]:
                    points.append(point)
        if len(points) >= 3:
            return [Polygon(points)], []
    return [], []


def _select_dxf_layer(layer_types: dict[str, Counter[str]], side: str) -> str:
    candidates = sorted(layer_types)
    if not candidates:
        raise ValueError("DXF modelspace 沒有可辨識的 2D 幾何")
    if len(candidates) == 1:
        return candidates[0]
    scored: list[tuple[int, str]] = []
    for name in candidates:
        normalized = re.sub(r"[^a-z0-9]+", "_", name.casefold())
        hint = _layer_side_hint(name)
        score = 2 if any(word in normalized for word in _PASTE_WORDS) else 0
        if hint == side:
            score += 3
        elif hint is not None:
            score -= 10
        scored.append((score, name))
    best_score = max(item[0] for item in scored)
    best = [name for score, name in scored if score == best_score and score > 0]
    if len(best) == 1:
        return best[0]
    raise ValueError(
        f"DXF 有多個幾何 layer，無法唯一選出 {side} Paste：" + ", ".join(candidates[:16])
    )


def _load_dxf(source: Path, side: str, unit_override: str | None) -> ApertureLoadResult:
    try:
        document = ezdxf.readfile(source)
    except (OSError, ezdxf.DXFError) as exc:
        raise ValueError(f"DXF 解析失敗：{exc}") from exc
    override = str(unit_override or "").strip().lower()
    unit_warning: tuple[str, ...]
    if override:
        if override not in {"mm", "inch"}:
            raise ValueError("DXF unit override must be mm or inch")
        factor = 1.0 if override == "mm" else 25.4
        unit_warning = (f"DXF 單位由使用者指定為 {override}",)
    else:
        source_units = InsertUnits(document.units)
        if source_units == InsertUnits.Unitless:
            raise ValueError("DXF 未設定 $INSUNITS；請明確選擇 mm 或 inch")
        try:
            factor = float(
                dxf_units.conversion_factor(source_units, InsertUnits.Millimeters)
            )
        except TypeError as exc:
            raise ValueError(f"DXF $INSUNITS={source_units} 無法換算為 mm") from exc
        unit_warning = ()
    geometry_types = {
        "INSERT",
        "CIRCLE",
        "HATCH",
        "LWPOLYLINE",
        "POLYLINE",
        "ELLIPSE",
        "SPLINE",
        "ARC",
        "LINE",
        "SOLID",
        "TRACE",
        "3DFACE",
    }
    layer_types: dict[str, Counter[str]] = defaultdict(Counter)
    for entity in document.modelspace():
        entity_type = str(entity.dxftype()).upper()
        if entity_type in geometry_types:
            layer_types[str(entity.dxf.get("layer", "0"))][entity_type] += 1
    selected_layer = _select_dxf_layer(layer_types, side)
    geometries: list[BaseGeometry] = []
    linework: list[LineString] = []
    ignored: Counter[str] = Counter()
    for entity in document.modelspace():
        if str(entity.dxf.get("layer", "0")) != selected_layer:
            continue
        entity_type = str(entity.dxftype()).upper()
        if entity_type not in geometry_types:
            ignored[entity_type] += 1
            continue
        parsed, lines = _dxf_entity_geometry(entity, factor)
        geometries.extend(parsed)
        linework.extend(lines)
    if linework:
        polygons, cuts, dangles, invalid = polygonize_full(linework)
        if not cuts.is_empty or not dangles.is_empty or not invalid.is_empty:
            raise ValueError("DXF 選定 layer 含未閉合 LINE/ARC/SPLINE，不能安全推定開窗")
        geometries.extend(list(polygons.geoms))
    warnings = list(unit_warning)
    if ignored:
        warnings.append(
            "DXF 選定 layer 已忽略非幾何註記："
            + ", ".join(f"{name}={count}" for name, count in sorted(ignored.items()))
        )
    return ApertureLoadResult(
        openings=_clean_openings(geometries, label="DXF"),
        format_id="dxf",
        format_label=f"DXF {document.dxfversion}",
        source_layer=selected_layer,
        warnings=tuple(warnings),
    )


def _matrix_blocks(text: str, kind: str) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    pattern = re.compile(rf"\b{re.escape(kind)}\s*\{{(.*?)\}}", re.IGNORECASE | re.DOTALL)
    for match in pattern.finditer(text):
        fields: dict[str, str] = {}
        for line in match.group(1).splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            fields[key.strip().upper()] = value.strip()
        blocks.append(fields)
    return blocks


def _odb_layer_side(layer: dict[str, str], conductive_rows: Sequence[int]) -> str | None:
    hint = _layer_side_hint(layer.get("NAME", ""))
    if hint is not None:
        return hint
    try:
        row = int(layer.get("ROW", "0"))
    except ValueError:
        return None
    if conductive_rows and row < min(conductive_rows):
        return "TOP"
    if conductive_rows and row > max(conductive_rows):
        return "BOTTOM"
    return None


def _rounded_rectangle(width: float, height: float, radius: float) -> BaseGeometry:
    if width <= 0 or height <= 0 or radius < 0 or radius > min(width, height) / 2.0:
        raise ValueError("ODB++ rounded rectangle 尺寸無效")
    if radius <= 1e-12:
        return box(-width / 2.0, -height / 2.0, width / 2.0, height / 2.0)
    return box(
        -width / 2.0 + radius,
        -height / 2.0 + radius,
        width / 2.0 - radius,
        height / 2.0 - radius,
    ).buffer(radius)


def _standard_odb_symbol(name: str, factor: float) -> BaseGeometry | None:
    number = r"([0-9]+(?:\.[0-9]+)?)"
    if match := re.fullmatch(rf"r{number}", name, re.IGNORECASE):
        return Point(0.0, 0.0).buffer(float(match.group(1)) * factor / 2.0)
    if match := re.fullmatch(rf"s{number}", name, re.IGNORECASE):
        size = float(match.group(1)) * factor
        return box(-size / 2.0, -size / 2.0, size / 2.0, size / 2.0)
    if match := re.fullmatch(
        rf"rect{number}x{number}(?:xr{number})?", name, re.IGNORECASE
    ):
        width = float(match.group(1)) * factor
        height = float(match.group(2)) * factor
        radius = float(match.group(3) or 0.0) * factor
        return _rounded_rectangle(width, height, radius)
    if match := re.fullmatch(rf"oval{number}x{number}", name, re.IGNORECASE):
        width = float(match.group(1)) * factor
        height = float(match.group(2)) * factor
        radius = min(width, height) / 2.0
        if width >= height:
            core = box(-width / 2.0 + radius, 0.0, width / 2.0 - radius, 0.0)
        else:
            core = box(0.0, -height / 2.0 + radius, 0.0, height / 2.0 - radius)
        return core.buffer(radius)
    if match := re.fullmatch(rf"di{number}x{number}", name, re.IGNORECASE):
        width = float(match.group(1)) * factor
        height = float(match.group(2)) * factor
        return Polygon([(0, height / 2), (width / 2, 0), (0, -height / 2), (-width / 2, 0)])
    return None


def _odb_orientation(tokens: Sequence[str]) -> tuple[float, bool]:
    if not tokens:
        return 0.0, False
    try:
        code = int(tokens[0])
    except ValueError as exc:
        raise ValueError(f"ODB++ orientation 無效：{' '.join(tokens)}") from exc
    if 0 <= code <= 7:
        return float((code % 4) * 90), code >= 4
    if code in {8, 9} and len(tokens) >= 2:
        return float(tokens[1]), code == 9
    raise ValueError(f"ODB++ orientation 無效：{' '.join(tokens)}")


class _OdbFeatureParser:
    def __init__(self, bundle: _ArchiveBundle, root: str) -> None:
        self.bundle = bundle
        self.root = root
        self.symbol_cache: dict[str, BaseGeometry] = {}

    @staticmethod
    def _units(text: str) -> tuple[float, float]:
        match = re.search(r"^UNITS\s*=\s*(INCH|MM)\s*$", text, re.IGNORECASE | re.MULTILINE)
        if not match:
            raise ValueError("ODB++ features 缺少 UNITS=INCH/MM")
        unit = match.group(1).upper()
        coordinate_factor = 25.4 if unit == "INCH" else 1.0
        symbol_factor = 0.0254 if unit == "INCH" else 0.001
        return coordinate_factor, symbol_factor

    @staticmethod
    def _symbols(text: str, default_factor: float) -> dict[int, tuple[str, float]]:
        symbols: dict[int, tuple[str, float]] = {}
        for line in text.splitlines():
            match = re.match(r"^\$(\d+)\s+(\S+)(?:\s+([IM]))?\s*$", line.strip())
            if not match:
                continue
            factor = default_factor
            if match.group(3) == "I":
                factor = 0.0254
            elif match.group(3) == "M":
                factor = 0.001
            symbols[int(match.group(1))] = (match.group(2), factor)
        return symbols

    def _symbol_geometry(
        self, name: str, factor: float, stack: tuple[str, ...]
    ) -> BaseGeometry:
        cache_key = f"{name.casefold()}|{factor:g}"
        if cache_key in self.symbol_cache:
            return self.symbol_cache[cache_key]
        standard = _standard_odb_symbol(name, factor)
        if standard is not None:
            self.symbol_cache[cache_key] = standard
            return standard
        if name.casefold() in stack:
            raise ValueError(f"ODB++ custom symbol 循環引用：{name}")
        member = f"{self.root}symbols/{name}/features"
        if not self.bundle.has(member):
            raise ValueError(f"ODB++ 未支援或缺少 symbol：{name}")
        custom = self.parse(
            self.bundle.read_text(member),
            stack=(*stack, name.casefold()),
        )
        geometry = unary_union(custom)
        self.symbol_cache[cache_key] = geometry
        return geometry

    def _round_diameter(
        self, symbol: tuple[str, float]
    ) -> float:
        name, factor = symbol
        match = re.fullmatch(r"r([0-9]+(?:\.[0-9]+)?)", name, re.IGNORECASE)
        if not match:
            raise ValueError(f"ODB++ line/arc 只安全支援 round symbol，收到 {name}")
        return float(match.group(1)) * factor

    @staticmethod
    def _surface(
        lines: Sequence[str], start_index: int, coordinate_factor: float
    ) -> tuple[BaseGeometry, str, int]:
        header = lines[start_index].split(";", 1)[0].split()
        if len(header) < 3:
            raise ValueError("ODB++ surface header 無效")
        polarity = header[1].upper()
        polygons: list[tuple[str, BaseGeometry]] = []
        current_type = ""
        current_points: list[tuple[float, float]] = []
        index = start_index + 1
        while index < len(lines):
            tokens = lines[index].split(";", 1)[0].split()
            index += 1
            if not tokens:
                continue
            code = tokens[0].upper()
            if code == "OB":
                if len(tokens) < 4:
                    raise ValueError("ODB++ OB record 無效")
                current_points = [
                    (float(tokens[1]) * coordinate_factor, float(tokens[2]) * coordinate_factor)
                ]
                current_type = tokens[3].upper()
            elif code == "OS":
                current_points.append(
                    (float(tokens[1]) * coordinate_factor, float(tokens[2]) * coordinate_factor)
                )
            elif code == "OC":
                end = (float(tokens[1]) * coordinate_factor, float(tokens[2]) * coordinate_factor)
                center = (float(tokens[3]) * coordinate_factor, float(tokens[4]) * coordinate_factor)
                current_points.extend(
                    _arc_points(current_points[-1], end, center, tokens[5].upper() == "Y")
                )
            elif code == "OE":
                if len(current_points) < 3:
                    raise ValueError("ODB++ surface polygon 點數不足")
                polygon = Polygon(current_points)
                polygons.append((current_type, polygon if polygon.is_valid else polygon.buffer(0)))
                current_points = []
            elif code == "SE":
                break
            else:
                raise ValueError(f"ODB++ surface 含未知 record：{code}")
        else:
            raise ValueError("ODB++ surface 缺少 SE")
        islands = [geometry for kind, geometry in polygons if kind == "I"]
        holes = [geometry for kind, geometry in polygons if kind == "H"]
        if any(kind not in {"I", "H"} for kind, _geometry in polygons):
            raise ValueError("ODB++ surface polygon type 必須是 I 或 H")
        geometry = unary_union(islands)
        if holes:
            geometry = geometry.difference(unary_union(holes))
        return geometry, polarity, index

    def parse(self, text: str, *, stack: tuple[str, ...] = ()) -> list[BaseGeometry]:
        """Parse one ODB++ feature stream into complete polygon geometry."""
        coordinate_factor, default_symbol_factor = self._units(text)
        symbols = self._symbols(text, default_symbol_factor)
        marker = text.find("#Layer features")
        if marker < 0:
            raise ValueError("ODB++ features 缺少 #Layer features")
        lines = [line.strip() for line in text[marker:].splitlines()]
        positive: list[BaseGeometry] = []
        negative: list[BaseGeometry] = []
        unsupported: Counter[str] = Counter()
        index = 0
        while index < len(lines):
            raw = lines[index]
            if not raw or raw.startswith("#"):
                index += 1
                continue
            tokens = raw.split(";", 1)[0].split()
            if not tokens:
                index += 1
                continue
            code = tokens[0].upper()
            geometry: BaseGeometry | None = None
            polarity = "P"
            if code == "P":
                if len(tokens) < 7 or tokens[3] == "-1":
                    raise ValueError("ODB++ resized/invalid pad record 尚未安全支援")
                symbol = symbols.get(int(tokens[3]))
                if symbol is None:
                    raise ValueError(f"ODB++ pad 引用未知 symbol index {tokens[3]}")
                geometry = self._symbol_geometry(symbol[0], symbol[1], stack)
                rotation, mirrored = _odb_orientation(tokens[6:])
                if mirrored:
                    geometry = affinity.scale(geometry, xfact=1.0, yfact=-1.0, origin=(0, 0))
                if rotation:
                    geometry = affinity.rotate(geometry, -rotation, origin=(0, 0))
                geometry = affinity.translate(
                    geometry,
                    xoff=float(tokens[1]) * coordinate_factor,
                    yoff=float(tokens[2]) * coordinate_factor,
                )
                polarity = tokens[4].upper()
            elif code == "L":
                if len(tokens) < 8:
                    raise ValueError("ODB++ line record 無效")
                symbol = symbols.get(int(tokens[5]))
                if symbol is None:
                    raise ValueError(f"ODB++ line 引用未知 symbol index {tokens[5]}")
                diameter = self._round_diameter(symbol)
                start = (float(tokens[1]) * coordinate_factor, float(tokens[2]) * coordinate_factor)
                end = (float(tokens[3]) * coordinate_factor, float(tokens[4]) * coordinate_factor)
                geometry = LineString([start, end]).buffer(diameter / 2.0)
                polarity = tokens[6].upper()
            elif code == "A":
                if len(tokens) < 11:
                    raise ValueError("ODB++ arc record 無效")
                symbol = symbols.get(int(tokens[7]))
                if symbol is None:
                    raise ValueError(f"ODB++ arc 引用未知 symbol index {tokens[7]}")
                diameter = self._round_diameter(symbol)
                start = (float(tokens[1]) * coordinate_factor, float(tokens[2]) * coordinate_factor)
                end = (float(tokens[3]) * coordinate_factor, float(tokens[4]) * coordinate_factor)
                center = (float(tokens[5]) * coordinate_factor, float(tokens[6]) * coordinate_factor)
                points = [start, *_arc_points(start, end, center, tokens[10].upper() == "Y")]
                geometry = LineString(points).buffer(diameter / 2.0)
                polarity = tokens[8].upper()
            elif code == "S":
                geometry, polarity, index = self._surface(lines, index, coordinate_factor)
            else:
                unsupported[code] += 1
            if geometry is not None and not geometry.is_empty:
                target = positive if polarity == "P" else negative if polarity == "N" else None
                if target is None:
                    raise ValueError(f"ODB++ polarity 必須是 P/N，收到 {polarity}")
                target.append(geometry)
            if code != "S":
                index += 1
        if unsupported:
            details = ", ".join(f"{name}={count}" for name, count in sorted(unsupported.items()))
            raise ValueError(f"ODB++ Paste layer 含未支援 feature record：{details}")
        if negative:
            return list(_polygon_parts(unary_union(positive).difference(unary_union(negative))))
        return _clean_openings(positive, label="ODB++")


def _load_odbpp(source: Path, side: str) -> ApertureLoadResult:
    with _ArchiveBundle(source) as bundle:
        matrix_files = sorted(
            entry.canonical_name
            for entry in bundle.entries.values()
            if entry.canonical_name.casefold().endswith("/matrix/matrix")
            or entry.canonical_name.casefold() == "matrix/matrix"
        )
        if len(matrix_files) != 1:
            raise ValueError("ODB++ 必須且只能有一個 matrix/matrix")
        matrix_path = matrix_files[0]
        root = matrix_path[: -len("matrix/matrix")]
        matrix = bundle.read_text(matrix_path)
        layers = _matrix_blocks(matrix, "LAYER")
        conductive_rows = [
            int(layer["ROW"])
            for layer in layers
            if layer.get("TYPE", "").upper() in {"SIGNAL", "POWER_GROUND", "MIXED"}
            and layer.get("ROW", "").isdigit()
        ]
        candidates = [
            layer
            for layer in layers
            if layer.get("TYPE", "").upper() == "SOLDER_PASTE"
            and _odb_layer_side(layer, conductive_rows) == side
        ]
        if len(candidates) != 1:
            names = ", ".join(layer.get("NAME", "") for layer in candidates)
            raise ValueError(f"ODB++ 無法唯一選出 {side} SOLDER_PASTE layer：{names or '無'}")
        layer_name = candidates[0].get("NAME", "")
        steps = [block.get("NAME", "") for block in _matrix_blocks(matrix, "STEP")]
        feature_members = [
            f"{root}steps/{step}/layers/{layer_name}/features"
            for step in steps
            if bundle.has(f"{root}steps/{step}/layers/{layer_name}/features")
        ]
        if len(feature_members) != 1:
            compressed = [
                f"{root}steps/{step}/layers/{layer_name}/features.Z"
                for step in steps
                if bundle.has(f"{root}steps/{step}/layers/{layer_name}/features.Z")
            ]
            if compressed:
                raise ValueError("ODB++ features.Z 舊式 UNIX-compress 尚未支援，請輸出未壓縮 features")
            raise ValueError(f"ODB++ 無法唯一找到 {side} Paste layer 的 features")
        parser = _OdbFeatureParser(bundle, root)
        openings = parser.parse(bundle.read_text(feature_members[0]))
    return ApertureLoadResult(
        openings=_clean_openings(openings, label="ODB++"),
        format_id="odbpp",
        format_label="ODB++Design",
        source_layer=layer_name,
    )


def load_aperture_source(
    path: str,
    *,
    side: str,
    unit_override: str | None = None,
) -> ApertureLoadResult:
    """Load a supported aperture source and return only verified geometry."""
    source = Path(path)
    side_value = _normalize_side(side)
    format_id = detect_aperture_format(source)
    if format_id == "gerber":
        return _load_single_gerber(source, side_value)
    if format_id == "gerber_zip":
        return _load_gerber_zip(source, side_value)
    if format_id == "ipc2581":
        return _load_ipc2581(source, side_value)
    if format_id == "dxf":
        return _load_dxf(source, side_value, unit_override)
    if format_id == "odbpp":
        return _load_odbpp(source, side_value)
    raise AssertionError(f"unhandled aperture format: {format_id}")


def load_gerber_openings(path: str) -> list[BaseGeometry]:
    """Backward-compatible single-Gerber loader used by existing callers/tests."""
    source = Path(path)
    if source.suffix.casefold() not in GERBER_SUFFIXES:
        raise ValueError("load_gerber_openings only accepts a single Gerber file")
    if source.suffix.casefold() == ".pho":
        declared = _gerber_declared_side(
            source.name,
            source.read_text(encoding="utf-8-sig", errors="replace"),
        )
        if declared is None:
            raise ValueError("PHO requires an explicit TOP/BOTTOM layer name")
        return _load_single_gerber(source, declared).openings
    text = source.read_text(encoding="utf-8-sig", errors="replace")
    return _gerber_file_openings(GerberFile.from_string(text, filename=source.name))
