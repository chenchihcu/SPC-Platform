"""DataSetupPage 固定單欄門檻（layout_tier_from_width）。"""
from app.ui.pages.data_setup_page import layout_tier_from_width
from app.ui.theme.tokens import DATA_SETUP_BREAKPOINT_2COL, DATA_SETUP_BREAKPOINT_3COL


def test_layout_tier_boundaries() -> None:
    assert layout_tier_from_width(DATA_SETUP_BREAKPOINT_2COL - 1) == 1
    assert layout_tier_from_width(DATA_SETUP_BREAKPOINT_2COL) == 1
    assert layout_tier_from_width(DATA_SETUP_BREAKPOINT_3COL - 1) == 1
    assert layout_tier_from_width(DATA_SETUP_BREAKPOINT_3COL) == 1


def test_layout_tier_wide() -> None:
    assert layout_tier_from_width(2000) == 1


def test_layout_tier_narrow() -> None:
    assert layout_tier_from_width(0) == 1
