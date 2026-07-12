"""DataSetupPage 固定單欄門檻（layout_tier_from_width）。"""
from app.ui.pages.data_setup_page import layout_tier_from_width


def test_layout_tier_is_fixed_single_column_across_breakpoint_range() -> None:
    # 歷史 2/3 欄斷點（980 / 1080）已移除；固定密集單欄下任何寬度都應回傳 tier 1。
    for width in (979, 980, 1079, 1080):
        assert layout_tier_from_width(width) == 1


def test_layout_tier_wide() -> None:
    assert layout_tier_from_width(2000) == 1


def test_layout_tier_narrow() -> None:
    assert layout_tier_from_width(0) == 1
