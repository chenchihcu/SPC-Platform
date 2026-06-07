"""Watchlist #7 optional A: measurement CSV alias / required columns / invalid file (column-level)."""

from __future__ import annotations

from pathlib import Path

from app.data.loaders.measurement_loader import MeasurementLoader


def test_measurement_loader_maps_component_alias_to_refdes(tmp_path: Path) -> None:
    p = tmp_path / "m.csv"
    p.write_text("Component,BoardNo,Volume\nR1,B1,10.5\n", encoding="utf-8")
    df, meta = MeasurementLoader().load(str(p))
    assert meta["is_valid"] is True
    assert "RefDes" in df.columns
    assert meta["mapping"].get("RefDes") == "Component"
    assert df["RefDes"].iloc[0] == "R1"


def test_measurement_loader_rejects_missing_measurement_column(tmp_path: Path) -> None:
    p = tmp_path / "m.csv"
    p.write_text("RefDes,BoardNo\nR1,B1\n", encoding="utf-8")
    _df, meta = MeasurementLoader().load(str(p))
    assert meta["is_valid"] is False
    assert "Measurement (Volume, Area, or Height)" in (meta.get("missing_required") or [])


def test_measurement_loader_rejects_missing_board_and_time(tmp_path: Path) -> None:
    p = tmp_path / "m.csv"
    p.write_text("RefDes,Volume\nR1,10\n", encoding="utf-8")
    _df, meta = MeasurementLoader().load(str(p))
    assert meta["is_valid"] is False
    assert "Identifier (BoardNo or Time)" in (meta.get("missing_required") or [])


def test_measurement_loader_file_not_found() -> None:
    df, meta = MeasurementLoader().load(str(Path("/nonexistent/measurements_xyz.csv")))
    assert df.empty
    assert meta["is_valid"] is False
    assert "not found" in meta.get("error", "").lower()


def test_measurement_loader_utf8_decode_error_reports_meta(tmp_path: Path) -> None:
    p = tmp_path / "bad.csv"
    p.write_bytes(b"RefDes,BoardNo,Volume\nR1,B1,\xff\n")
    _df, meta = MeasurementLoader().load(str(p))
    assert meta["is_valid"] is False
    err = (meta.get("error") or "").lower()
    assert "utf-8" in err or "decode" in err
