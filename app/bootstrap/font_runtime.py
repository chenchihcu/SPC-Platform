from __future__ import annotations

from pathlib import Path
from typing import Iterable

_BUNDLED_FONT_FILES: tuple[str, ...] = ("NotoSansTC-VF.ttf",)
_BUNDLED_FONT_DIR = Path(__file__).resolve().parents[1] / "assets" / "fonts"

_MPL_REGISTERED_FAMILIES: list[str] | None = None
_QT_REGISTERED_FAMILIES: list[str] | None = None


def _dedupe_keep_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def bundled_font_paths() -> list[Path]:
    """Return existing bundled font paths in stable order."""
    return [(_BUNDLED_FONT_DIR / name) for name in _BUNDLED_FONT_FILES if (_BUNDLED_FONT_DIR / name).is_file()]


def register_mpl_bundled_fonts() -> list[str]:
    """Register bundled fonts for Matplotlib and return discovered family names."""
    global _MPL_REGISTERED_FAMILIES
    if _MPL_REGISTERED_FAMILIES is not None:
        return list(_MPL_REGISTERED_FAMILIES)

    try:
        from matplotlib import font_manager
    except (ImportError, OSError, RuntimeError):
        _MPL_REGISTERED_FAMILIES = []
        return []

    families: list[str] = []
    for path in bundled_font_paths():
        try:
            font_manager.fontManager.addfont(str(path))
        except (OSError, RuntimeError, ValueError):
            continue
        try:
            families.append(font_manager.FontProperties(fname=str(path)).get_name())
        except (OSError, RuntimeError, ValueError):
            continue

    _MPL_REGISTERED_FAMILIES = _dedupe_keep_order(families)
    return list(_MPL_REGISTERED_FAMILIES)


def register_qt_bundled_fonts() -> list[str]:
    """Register bundled fonts for Qt and return discovered family names."""
    global _QT_REGISTERED_FAMILIES
    if _QT_REGISTERED_FAMILIES is not None:
        return list(_QT_REGISTERED_FAMILIES)

    try:
        from PySide6.QtGui import QFontDatabase
    except ImportError:
        _QT_REGISTERED_FAMILIES = []
        return []

    families: list[str] = []
    for path in bundled_font_paths():
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id < 0:
            continue
        try:
            families.extend(QFontDatabase.applicationFontFamilies(font_id))
        except (RuntimeError, TypeError, ValueError):
            continue

    _QT_REGISTERED_FAMILIES = _dedupe_keep_order(families)
    return list(_QT_REGISTERED_FAMILIES)


def preferred_qt_font_family() -> str:
    """
    Return the preferred UI font family available on this runtime.

    Priority:
    1) Bundled CJK font families
    2) Common Windows CJK families
    3) Default to Noto Sans TC as the semantic target
    """
    preferred = register_qt_bundled_fonts() + [
        "Noto Sans TC",
        "Microsoft JhengHei UI",
        "Microsoft JhengHei",
        "Microsoft YaHei",
    ]
    preferred = _dedupe_keep_order(preferred)

    try:
        from PySide6.QtGui import QFontDatabase

        available = set(QFontDatabase.families())
        for family in preferred:
            if family in available:
                return family
    except (RuntimeError, TypeError, ValueError):
        pass

    return preferred[0] if preferred else "Noto Sans TC"
