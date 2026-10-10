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


def _seed_percent_stencil(monkeypatch: pytest.MonkeyPatch, product: str) -> None:
    """Percent-mode stencil (thickness 0.06mm) — the mis-configured case."""
    monkeypatch.setattr(
        "app.services.spec_resolver.get_paste_printing_spec",
        lambda name: {
            "product_name": product,
            "default_volume_target": 100.0,
            "default_volume_lsl": 50.0,
            "default_volume_usl": 170.0,
            "default_area_target": 100.0,
            "default_area_lsl": 70.0,
            "default_area_usl": 170.0,
            "default_height_lsl": 50.0,
            "default_height_usl": 170.0,
        }
        if str(name).strip() == product
        else None,
    )
    monkeypatch.setattr(
        "app.services.spec_resolver.get_stencil_thickness_spec",
        lambda name: {
            "product_name": product,
            "stencil_type": "normal",
            "thickness_main": 0.06,
            "thickness_precision": None,
            "precision_is_main": False,
            "unit_mode": "percent",
            "height_denominator_mm": 0.06,
        }
        if str(name).strip() == product
        else None,
    )


def test_mm_measurement_units_force_absolute_height_over_percent_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Loader-declared mm Height data must resolve absolute mm limits even when
    the stencil flag still says percent (root cause of the SPI report bug)."""
    product = "MmDataPercentFlag"
    _seed_percent_stencil(monkeypatch, product)

    wo, err = resolve_workorder_spec(product, measurement_units={"Height": "mm"})
    assert err is None and wo is not None
    h = wo["height"]
    assert h["target"] == "0.06"
    assert h["lsl"] == "0.03"
    assert h["usl"] == "0.102"
    # Volume/Area have no conversion path — they stay in percent.
    assert wo["volume"]["usl"] == "170.0"


def test_no_measurement_units_keeps_percent_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without declared units, the stored percent flag is honored unchanged."""
    product = "MmDataPercentFlag"
    _seed_percent_stencil(monkeypatch, product)

    wo, err = resolve_workorder_spec(product)
    assert err is None and wo is not None
    assert wo["height"]["usl"] == "170.0"
    assert wo["height"]["lsl"] == "50.0"
