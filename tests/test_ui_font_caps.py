import re

from app.ui.theme.dark_stylesheet import get_dark_stylesheet
from app.ui.theme.tokens import (
    BUTTON_MIN_HEIGHT,
    CONTROL_DENSE_SECTION_TITLE_PT,
    DATA_SETUP_DENSE_CAPTION_FONT_SIZE,
    DATA_SETUP_DENSE_CONTROL_FONT_SIZE,
    DATA_SETUP_DENSE_FORM_LABEL_FONT_SIZE,
    DATA_SETUP_DENSE_STEP_TITLE_FONT_SIZE,
    FONT_SIZE_BODY,
    FONT_SIZE_CAPTION,
    FONT_SIZE_TITLE,
    FORM_PAGE_CONTENT_MAX_WIDTH,
    INPUT_MIN_HEIGHT,
    LABEL_ROW_MIN_HEIGHT,
    MAX_UI_FONT_PT,
    PAGE_HEADER_BOTTOM_SPACING,
    PRIMARY_ACTION_TOP_SPACING,
    SECTION_TITLE_MIN_HEIGHT,
    SIDEBAR_SECTION_TITLE_FONT_SIZE,
    TWO_COLUMN_CONTENT_SPACING,
    TYPO_APP_TITLE_PT,
    TYPO_PAGE_TITLE_PT,
    TYPO_SECTION_TITLE_PT,
)


def test_ui_font_tokens_are_capped_to_max_ui_font() -> None:
    for value in (
        TYPO_APP_TITLE_PT,
        TYPO_PAGE_TITLE_PT,
        TYPO_SECTION_TITLE_PT,
        FONT_SIZE_TITLE,
        FONT_SIZE_BODY,
        SIDEBAR_SECTION_TITLE_FONT_SIZE,
        DATA_SETUP_DENSE_STEP_TITLE_FONT_SIZE,
        DATA_SETUP_DENSE_CONTROL_FONT_SIZE,
        CONTROL_DENSE_SECTION_TITLE_PT,
    ):
        assert value <= MAX_UI_FONT_PT


def test_stylesheet_font_sizes_do_not_exceed_max_ui_font() -> None:
    stylesheet = get_dark_stylesheet()
    sizes = [float(match) for match in re.findall(r"font-size:\s*([0-9.]+)pt;", stylesheet)]
    assert sizes
    assert max(sizes) <= MAX_UI_FONT_PT


# Guardrail: after remediation, rendered stylesheet should keep 500/600 at zero.
# This prevents regressions that reintroduce synthetic CJK strokes on Windows.
_STYLESHEET_FONT_WEIGHT_500_BASELINE = 0
_STYLESHEET_FONT_WEIGHT_600_BASELINE = 0


def test_stylesheet_cjk_risky_font_weight_counts_do_not_increase() -> None:
    stylesheet = get_dark_stylesheet()
    n500 = len(re.findall(r"font-weight:\s*500\b", stylesheet))
    n600 = len(re.findall(r"font-weight:\s*600\b", stylesheet))
    assert n500 <= _STYLESHEET_FONT_WEIGHT_500_BASELINE, (
        f"font-weight:500 occurrences in get_dark_stylesheet() increased to {n500} "
        f"(baseline {_STYLESHEET_FONT_WEIGHT_500_BASELINE}). Reduce or document remediation per AGENTS.md §4."
    )
    assert n600 <= _STYLESHEET_FONT_WEIGHT_600_BASELINE, (
        f"font-weight:600 occurrences in get_dark_stylesheet() increased to {n600} "
        f"(baseline {_STYLESHEET_FONT_WEIGHT_600_BASELINE}). Reduce or document remediation per AGENTS.md §4."
    )


def test_compact_density_tokens_baseline() -> None:
    # Redesign v2: 層次分明的字級體系，title > body > caption
    assert FONT_SIZE_BODY <= 12       # body 適中（11pt）
    assert FONT_SIZE_TITLE <= MAX_UI_FONT_PT
    assert FONT_SIZE_TITLE > FONT_SIZE_BODY  # 確保 title > body 層次
    assert FONT_SIZE_CAPTION <= 10
    assert BUTTON_MIN_HEIGHT <= 34    # 提升可點擊區域（32px）
    assert INPUT_MIN_HEIGHT <= 30
    assert LABEL_ROW_MIN_HEIGHT <= 22  # bumped from 20 for CJK readability at high DPI
    assert SECTION_TITLE_MIN_HEIGHT <= 28
    assert PAGE_HEADER_BOTTOM_SPACING <= 10
    assert TWO_COLUMN_CONTENT_SPACING <= 12
    assert PRIMARY_ACTION_TOP_SPACING <= 10
    assert FORM_PAGE_CONTENT_MAX_WIDTH >= 900


def test_data_setup_text_is_readable_in_compact_mode() -> None:
    # Redesign v2: dense 模式字級修正 — 不應比 body 大，但仍需可讀
    assert DATA_SETUP_DENSE_CAPTION_FONT_SIZE >= 9.5     # 說明文字最小可讀
    assert DATA_SETUP_DENSE_FORM_LABEL_FONT_SIZE >= 10.5  # 表單標籤最小可讀
