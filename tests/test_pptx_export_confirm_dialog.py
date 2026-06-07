"""Tests for PPTX export confirmation helper and gallery page estimate."""

from app.ui.dialogs.pptx_export_confirm_dialog import (
    build_pptx_export_confirmation_body_lines,
    estimate_gallery_pages,
)


def test_estimate_gallery_pages_matches_pptx_builder_formula() -> None:
    assert estimate_gallery_pages(0) == 0
    assert estimate_gallery_pages(1) == 1
    assert estimate_gallery_pages(4) == 1
    assert estimate_gallery_pages(5) == 2
    assert estimate_gallery_pages(8) == 2


def test_build_pptx_export_confirmation_body_lines_fallback_and_distribution_note() -> None:
    lines = build_pptx_export_confirmation_body_lines(
        ["histogram_spec", "boxplot"],
        using_fallback=True,
    )
    text = "\n".join(lines)
    assert "未勾選任何圖表" in text
    assert "預估畫廊頁數：1 頁" in text
    assert "敘事頁「分布分析」：是" in text
    assert "工程報告固定包含" in text


def test_build_pptx_export_confirmation_body_lines_explicit_selection() -> None:
    lines = build_pptx_export_confirmation_body_lines(
        ["imr"],
        using_fallback=False,
    )
    text = "\n".join(lines)
    assert "依目前勾選" in text
    assert "未勾選任何圖表" not in text
