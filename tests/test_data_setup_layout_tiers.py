"""DataSetupPage responsive layout breakpoints."""
from app.ui.pages.data_setup_page import layout_tier_from_width


def test_layout_tier_stacks_when_two_regions_cannot_fit() -> None:
    for width in (0, 779, 787):
        assert layout_tier_from_width(width) == 2


def test_layout_tier_wide() -> None:
    assert layout_tier_from_width(2000) == 1


def test_layout_tier_narrow() -> None:
    assert layout_tier_from_width(788) == 1
