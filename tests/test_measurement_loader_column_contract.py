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


def _write_zhen_shun_feng_top_csv(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                (
                    "Component ID,PAD ID,"
                    "Volume(mm)1,Height(mm)1,Area(mm)1,"
                    "Volume(mm)2,Height(mm)2,Area(mm)2"
                ),
                "C1_1,1,0.01391,0.0823,0.16899,0.01386,0.0805,0.17211",
                "U2_1,15,0.00158,0.0534,0.02957,0.00215,0.0700,0.03078",
            ]
        ),
        encoding="utf-8",
    )


def test_zhen_shun_feng_top_profile_maps_mm_wide_format_when_supplier_matches(tmp_path: Path) -> None:
    p = tmp_path / "top.csv"
    _write_zhen_shun_feng_top_csv(p)

    df, meta = MeasurementLoader().load(str(p), supplier="振順豐")

    assert meta["is_valid"] is True
    assert meta["vendor_profile"] == "zhen_shun_feng_top_mm"
    assert meta["vendor_profile_activation"] == "supplier"
    assert meta["raw_rows"] == 2
    assert meta["raw_columns"] == 8
    assert meta["total_rows"] == 4
    assert meta["board_count"] == 2
    assert meta["mapping"] == {
        "RefDes": "Component ID",
        "Pad": "PAD ID",
        "Volume": "Volume(mm)",
        "Height": "Height(mm)",
        "Area": "Area(mm)",
        "BoardNo": "BoardNo",
    }
    assert meta["unmapped_columns"] == []
    assert meta["measurement_units"] == {"Volume": "mm", "Height": "mm", "Area": "mm"}
    assert set(["RefDes", "Pad", "Volume", "Height", "Area", "BoardNo", "PartType"]) <= set(df.columns)
    assert df["BoardNo"].tolist() == ["Board_1", "Board_1", "Board_2", "Board_2"]
    assert df["Pad"].tolist() == ["1", "15", "1", "15"]
    assert df["Volume"].notna().sum() == 4


def test_zhen_shun_feng_top_profile_does_not_apply_without_supplier_or_path_hint(tmp_path: Path) -> None:
    p = tmp_path / "top.csv"
    _write_zhen_shun_feng_top_csv(p)

    _df, meta = MeasurementLoader().load(str(p))

    assert meta["is_valid"] is False
    assert meta["vendor_profile"] == ""
    assert "Measurement (Volume, Area, or Height)" in (meta.get("missing_required") or [])


def test_zhen_shun_feng_top_profile_can_activate_from_path_when_supplier_is_empty(tmp_path: Path) -> None:
    p = tmp_path / "振順豐_TOP.csv"
    _write_zhen_shun_feng_top_csv(p)

    _df, meta = MeasurementLoader().load(str(p))

    assert meta["is_valid"] is True
    assert meta["vendor_profile"] == "zhen_shun_feng_top_mm"
    assert meta["vendor_profile_activation"] == "path"


def test_zhen_shun_feng_top_profile_reports_missing_metric_group(tmp_path: Path) -> None:
    p = tmp_path / "top.csv"
    p.write_text(
        "\n".join(
            [
                "Component ID,PAD ID,Volume(mm)1,Height(mm)1",
                "C1_1,1,0.01391,0.0823",
            ]
        ),
        encoding="utf-8",
    )

    df, meta = MeasurementLoader().load(str(p), supplier="振順豐")

    assert df.empty
    assert meta["is_valid"] is False
    assert meta["vendor_profile"] == "zhen_shun_feng_top_mm"
    assert "Area(mm)1" in (meta.get("missing_required") or [])
    assert "signature error" in str(meta.get("error") or "")
