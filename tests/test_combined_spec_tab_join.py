"""Unit tests for the combined-spec UI join helper.

The join is pure (no Qt or DB dependencies) and is the seam through which
data from `paste_printing_spec_versions` and `stencil_thickness_versions`
is merged into a single per-product row in the 規格管理 tab.
"""
from __future__ import annotations

from app.ui.pages.measurement_library_page import _join_active_specs


def _paste(product_name: str, part_no: str = "", **extra) -> dict:
    return {
        "id": extra.pop("id", 1),
        "product_name": product_name,
        "product_part_no": part_no,
        "is_active": extra.pop("is_active", 1),
        "updated_at": extra.pop("updated_at", "2026-04-22T13:45:00"),
        **extra,
    }


def _stencil(product_name: str, part_no: str = "", **extra) -> dict:
    return {
        "id": extra.pop("id", 1),
        "product_name": product_name,
        "product_part_no": part_no,
        "is_active": extra.pop("is_active", 1),
        "updated_at": extra.pop("updated_at", "2026-04-22T13:45:00"),
        **extra,
    }


def test_join_both_sides_present_yields_one_row_per_product() -> None:
    paste = [_paste("x3000", "301-000100124")]
    stencil = [_stencil("x3000", "301-000100124")]
    rows = _join_active_specs(paste, stencil)
    assert len(rows) == 1
    row = rows[0]
    assert row["product_name"] == "x3000"
    assert row["product_part_no"] == "301-000100124"
    assert row["paste"] is paste[0]
    assert row["stencil"] is stencil[0]


def test_join_paste_only_keeps_row_with_missing_stencil() -> None:
    paste = [_paste("only-paste", "PN1")]
    rows = _join_active_specs(paste, [])
    assert len(rows) == 1
    assert rows[0]["paste"] is paste[0]
    assert rows[0]["stencil"] is None


def test_join_stencil_only_keeps_row_with_missing_paste() -> None:
    stencil = [_stencil("only-stencil", "PN2")]
    rows = _join_active_specs([], stencil)
    assert len(rows) == 1
    assert rows[0]["paste"] is None
    assert rows[0]["stencil"] is stencil[0]


def test_join_empty_inputs_returns_empty_list() -> None:
    assert _join_active_specs([], []) == []


def test_join_skips_blank_product_names() -> None:
    paste = [_paste("", "PN3")]
    stencil = [_stencil("", "PN3")]
    assert _join_active_specs(paste, stencil) == []


def test_join_preserves_paste_first_then_stencil_only_order() -> None:
    paste = [_paste("alpha", "A"), _paste("beta", "B")]
    stencil = [_stencil("alpha", "A"), _stencil("gamma", "G")]
    rows = _join_active_specs(paste, stencil)
    names = [r["product_name"] for r in rows]
    # alpha + beta (from paste order) then gamma (stencil-only newcomer)
    assert names == ["alpha", "beta", "gamma"]
    # Joined alpha picked up both sides
    assert rows[0]["paste"] is paste[0]
    assert rows[0]["stencil"] is stencil[0]
    # beta has paste but no stencil
    assert rows[1]["paste"] is paste[1]
    assert rows[1]["stencil"] is None
    # gamma has stencil but no paste
    assert rows[2]["paste"] is None
    assert rows[2]["stencil"] is stencil[1]


def test_join_keys_on_part_no_so_same_name_diff_part_stay_separate() -> None:
    paste = [_paste("dup", "PN-A"), _paste("dup", "PN-B")]
    stencil = [_stencil("dup", "PN-B")]
    rows = _join_active_specs(paste, stencil)
    assert len(rows) == 2
    # PN-A row: paste only
    assert rows[0]["product_part_no"] == "PN-A"
    assert rows[0]["stencil"] is None
    # PN-B row: both sides
    assert rows[1]["product_part_no"] == "PN-B"
    assert rows[1]["paste"] is paste[1]
    assert rows[1]["stencil"] is stencil[0]
