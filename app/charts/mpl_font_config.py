"""
Matplotlib CJK font configuration for correct display of Traditional Chinese
and other CJK characters in chart titles, axis labels, and tick labels.
Uses bundled + system fallback fonts.

中文優先字體策略：確保圖表內的中文標題、軸標籤、標記都能正確顯示。
"""
import sys
import matplotlib
from matplotlib import font_manager
from app.bootstrap.font_runtime import register_mpl_bundled_fonts
from app.ui.theme.tokens import CHART_FONT_BASE, CHART_FONT_TITLE, CHART_FONT_LABEL

# Font priority: 中文優先 — Noto Sans TC (跨平台) → 平台原生繁中 → 簡中 fallback
# 與 tokens.FONT_FAMILY 保持一致的優先順序
_CJK_FONTS_COMMON = ["Noto Sans TC", "Noto Sans CJK TC"]

_CJK_FONTS_PLATFORM = []
if sys.platform == "win32":
    _CJK_FONTS_PLATFORM = ["Microsoft JhengHei", "Microsoft YaHei", "SimHei"]
elif sys.platform == "darwin":
    _CJK_FONTS_PLATFORM = ["PingFang TC", "Heiti TC", "PingFang SC", "STHeiti"]
else:
    _CJK_FONTS_PLATFORM = ["WenQuanYi Micro Hei", "Droid Sans Fallback"]

_FALLBACK_FONT = "DejaVu Sans"


def _dedupe_keep_order(fonts: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for font in fonts:
        if not font or font in seen:
            continue
        seen.add(font)
        deduped.append(font)
    return deduped


def _cjk_font_candidates() -> list[str]:
    """Return bundled-first CJK candidates with platform fallback."""
    bundled = register_mpl_bundled_fonts()
    return _dedupe_keep_order(bundled + _CJK_FONTS_COMMON + _CJK_FONTS_PLATFORM + [_FALLBACK_FONT])


def _available_cjk_fonts() -> list[str]:
    """Return candidate CJK fonts that exist on this system."""
    try:
        available = {f.name for f in font_manager.fontManager.ttflist}
        return [f for f in _cjk_font_candidates() if f in available]
    except (OSError, RuntimeError):
        return _cjk_font_candidates()


def _build_font_sans_serif(current: list[str], preferred: list[str]) -> list[str]:
    """Build rcParams['font.sans-serif'] with CJK preferred and DejaVu tail fallback."""
    cjk_preferred = [f for f in preferred if f != _FALLBACK_FONT]
    tail = [f for f in current if f not in cjk_preferred and f != _FALLBACK_FONT]
    ordered = cjk_preferred + tail
    if _FALLBACK_FONT in preferred or _FALLBACK_FONT in current:
        ordered.append(_FALLBACK_FONT)
    return _dedupe_keep_order(ordered)


def setup_mpl_cjk_font() -> None:
    """Set matplotlib rcParams for CJK-capable fonts. Idempotent; safe to call multiple times."""
    fonts_to_use = _available_cjk_fonts()
    current = list(matplotlib.rcParams.get("font.sans-serif", []))
    matplotlib.rcParams["font.sans-serif"] = _build_font_sans_serif(current=current, preferred=fonts_to_use)
    matplotlib.rcParams["font.family"] = ["sans-serif"]
    matplotlib.rcParams["axes.unicode_minus"] = False
    # 圖表文字基礎字級（與 UI tokens 保持協調）
    matplotlib.rcParams["font.size"] = CHART_FONT_BASE
    matplotlib.rcParams["axes.titlesize"] = CHART_FONT_TITLE
    matplotlib.rcParams["axes.labelsize"] = CHART_FONT_LABEL
