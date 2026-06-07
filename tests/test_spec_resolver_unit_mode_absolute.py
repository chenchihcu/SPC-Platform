from __future__ import annotations

import pytest

from app.services.spec_resolver import resolve_workorder_spec


def test_resolve_workorder_spec_converts_height_limits_for_absolute_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    product = "AbsUnitProduct"
    monkeypatch.setattr(
        "app.services.spec_resolver.get_paste_printing_spec",
        lambda name: {
            "product_name": product,
            "default_volume_target": 100.0,
            "default_volume_lsl": 70.0,
            "default_volume_usl": 150.0,
            "default_area_target": 100.0,
            "default_area_lsl": 70.0,
            "default_area_usl": 150.0,
            "default_height_lsl": 80.0,
            "default_height_usl": 120.0,
        }
        if str(name).strip() == product
        else None,
    )
    monkeypatch.setattr(
        "app.services.spec_resolver.get_stencil_thickness_spec",
        lambda name: {
            "product_name": product,
            "stencil_type": "normal",
            "thickness_main": 0.12,
            "thickness_precision": None,
            "precision_is_main": False,
            "unit_mode": "absolute",
            "height_denominator_mm": 0.20,
        }
        if str(name).strip() == product
        else None,
    )

    wo, err = resolve_workorder_spec(product)
    assert err is None
    assert wo is not None
    h = wo["height"]
    assert h["target"] == "0.2"
    assert h["lsl"] == "0.16"
    assert h["usl"] == "0.24"
