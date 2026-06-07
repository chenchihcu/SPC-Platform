"""Stepped stencil spec resolution (B): DB-free checks via resolver import targets."""

from __future__ import annotations

import pytest

from app.data.stencil_assignment_registry import PROFILE_MAIN, PROFILE_PRECISION
from app.services.spec_resolver import (
    can_run_analysis,
    resolve_height_spec_by_refdes,
    resolve_workorder_spec,
)

_PRODUCT = "GoldenReleaseStepped"

_STEPPED_MASTER: dict[str, object] = {
    "stencil_type": "stepped",
    "thickness_main": 0.12,
    "thickness_precision": 0.08,
    "precision_is_main": False,
    "unit_mode": "percent",
    "height_denominator_mm": 0.12,
    "default_volume_target": 100.0,
    "default_volume_lsl": 70.0,
    "default_volume_usl": 150.0,
    "default_area_target": 100.0,
    "default_area_lsl": 70.0,
    "default_area_usl": 150.0,
    "default_height_lsl": 70.0,
    "default_height_usl": 140.0,
}


def _patch_stepped_master(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.spec_resolver.get_stencil_thickness_spec",
        lambda name: _STEPPED_MASTER if str(name).strip() == _PRODUCT else None,
    )
    monkeypatch.setattr(
        "app.services.spec_resolver.get_paste_printing_spec",
        lambda name: _STEPPED_MASTER if str(name).strip() == _PRODUCT else None,
    )


def test_stepped_without_precision_assignment_blocks_resolve(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_stepped_master(monkeypatch)
    monkeypatch.setattr(
        "app.services.spec_resolver.has_any_precision_assignment",
        lambda _name: False,
    )
    wo, err = resolve_workorder_spec(_PRODUCT)
    assert wo is None
    assert err is not None
    assert "階梯鋼板" in err

    ok, msg = can_run_analysis(_PRODUCT)
    assert ok is False
    assert msg and "階梯鋼板" in msg


def test_stepped_with_precision_resolves_workorder_spec(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_stepped_master(monkeypatch)
    monkeypatch.setattr(
        "app.services.spec_resolver.has_any_precision_assignment",
        lambda _name: True,
    )
    wo, err = resolve_workorder_spec(_PRODUCT)
    assert err is None
    assert wo is not None
    assert set(wo.keys()) >= {"volume", "area", "height"}
    for key in ("volume", "area", "height"):
        block = wo[key]
        assert isinstance(block, dict)
        assert {"usl", "lsl", "target"} <= set(block.keys())


def test_resolve_height_spec_by_refdes_stepped_is_consistent_under_product_level_denominator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_stepped_master(monkeypatch)

    def _profile(_product: str, refdes: str) -> str:
        return PROFILE_PRECISION if refdes == "R1" else PROFILE_MAIN

    monkeypatch.setattr("app.services.spec_resolver.get_profile_by_refdes", _profile)
    out = resolve_height_spec_by_refdes(_PRODUCT, ["R1", "R2"])
    assert out["R1"] == {"target": 100.0, "lsl": 70.0, "usl": 140.0}
    assert out["R2"] == {"target": 100.0, "lsl": 70.0, "usl": 140.0}


def test_resolve_height_spec_by_refdes_normal_single_height(monkeypatch: pytest.MonkeyPatch) -> None:
    normal_master = {**_STEPPED_MASTER, "stencil_type": "normal"}
    monkeypatch.setattr(
        "app.services.spec_resolver.get_stencil_thickness_spec",
        lambda name: normal_master if str(name).strip() == _PRODUCT else None,
    )
    monkeypatch.setattr(
        "app.services.spec_resolver.get_paste_printing_spec",
        lambda name: normal_master if str(name).strip() == _PRODUCT else None,
    )
    out = resolve_height_spec_by_refdes(_PRODUCT, ["R1", "R2"])
    expected = {"target": 100.0, "lsl": 70.0, "usl": 140.0}
    assert out["R1"] == expected
    assert out["R2"] == expected
