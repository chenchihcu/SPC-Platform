from __future__ import annotations

from pathlib import Path
import shutil
import sqlite3

import pandas as pd
import pytest
from shapely.geometry import box

from app.data import master_data_db
from app.data.stencil_document_library import (
    create_stencil_document_version,
    deactivate_stencil_document_version,
    delete_inactive_stencil_document_version,
    delete_inactive_stencil_document_versions,
    get_active_stencil_document,
    list_stencil_document_versions,
    set_active_stencil_document_version,
)
from app.data.stencil_thickness_registry import save as save_stencil_spec
from app.data.coordinate_registry import remove_by_product_name
from app.services.stencil_document_service import (
    PARSER_VERSION,
    PadDefinition,
    analyze_stencil_import,
    derive_percentage_dataframe,
    load_gerber_openings,
    load_pad_csv,
)


@pytest.fixture()
def isolated_master_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_file = tmp_path / "spc_master.db"
    monkeypatch.setenv("SPC_MASTER_DB_PATH", str(db_file))
    master_data_db._INITIALIZED = False
    master_data_db.init_db()
    yield db_file
    master_data_db._INITIALIZED = False


def _write_rect_gerber(path: Path, width_mm: float = 0.6, height_mm: float = 0.3) -> None:
    path.write_text(
        "\n".join(
            [
                "G04 stencil test*",
                "%FSLAX46Y46*%",
                "%MOMM*%",
                f"%ADD10R,{width_mm:.6f}X{height_mm:.6f}*%",
                "D10*",
                "X0000000000Y0000000000D03*",
                "M02*",
            ]
        ),
        encoding="ascii",
    )


def test_legacy_cascade_fk_migrates_to_restrict_with_backup_replay(
    tmp_path: Path,
) -> None:
    database = tmp_path / "legacy.db"
    backup = tmp_path / "legacy.before-migration.db"
    with sqlite3.connect(database) as conn:
        conn.executescript(
            """
            CREATE TABLE products (id INTEGER PRIMARY KEY);
            CREATE TABLE stencil_document_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                stencil_no TEXT NOT NULL DEFAULT '',
                revision TEXT NOT NULL,
                side TEXT NOT NULL CHECK(side IN ('TOP', 'BOTTOM')),
                gerber_path TEXT NOT NULL,
                pad_csv_path TEXT NOT NULL,
                gerber_sha256 TEXT NOT NULL,
                pad_csv_sha256 TEXT NOT NULL,
                coordinate_transform_json TEXT NOT NULL DEFAULT '{}',
                validation_summary_json TEXT NOT NULL DEFAULT '{}',
                parser_version TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 0 CHECK(is_active IN (0, 1)),
                FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
            );
            CREATE TABLE stencil_pad_nominals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version_id INTEGER NOT NULL,
                refdes TEXT NOT NULL,
                pad TEXT NOT NULL,
                side TEXT NOT NULL CHECK(side IN ('TOP', 'BOTTOM')),
                opening_count INTEGER NOT NULL DEFAULT 0,
                nominal_area_mm2 REAL,
                resolved_thickness_mm REAL,
                nominal_volume_mm3 REAL,
                match_status TEXT NOT NULL,
                unmatched_reason TEXT NOT NULL DEFAULT '',
                preview_geometry_json TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY(version_id) REFERENCES stencil_document_versions(id)
                    ON DELETE CASCADE,
                UNIQUE(version_id, side, refdes, pad)
            );
            INSERT INTO products(id) VALUES(7);
            INSERT INTO stencil_document_versions(
                id, product_id, stencil_no, revision, side, gerber_path,
                pad_csv_path, gerber_sha256, pad_csv_sha256,
                coordinate_transform_json, validation_summary_json,
                parser_version, created_at, is_active
            ) VALUES(
                11, 7, 'ST-7', 'A', 'TOP', 'paste.gtp', 'pads.csv',
                'g-hash', 'c-hash', '{}', '{}', 'fixture', '2026-07-16', 1
            );
            INSERT INTO stencil_pad_nominals(
                id, version_id, refdes, pad, side, opening_count,
                nominal_area_mm2, resolved_thickness_mm, nominal_volume_mm3,
                match_status, unmatched_reason, preview_geometry_json
            ) VALUES(19, 11, 'U1', '01', 'TOP', 1, 0.18, 0.06, 0.0108,
                     'MATCHED', '', '{}');
            """
        )
    shutil.copy2(database, backup)

    with sqlite3.connect(database) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        master_data_db._ensure_stencil_document_fk_contract(conn)
        version_fk = conn.execute(
            "PRAGMA foreign_key_list('stencil_document_versions')"
        ).fetchone()
        assert version_fk is not None and version_fk[6] == "RESTRICT"
        assert conn.execute(
            "SELECT id, product_id FROM stencil_document_versions"
        ).fetchone() == (11, 7)
        assert conn.execute(
            "SELECT id, version_id, refdes, pad FROM stencil_pad_nominals"
        ).fetchone() == (19, 11, "U1", "01")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("DELETE FROM products WHERE id = 7")

    with sqlite3.connect(backup) as restored:
        backup_fk = restored.execute(
            "PRAGMA foreign_key_list('stencil_document_versions')"
        ).fetchone()
        assert backup_fk is not None and backup_fk[6] == "CASCADE"
        assert restored.execute(
            "SELECT COUNT(*) FROM stencil_document_versions"
        ).fetchone()[0] == 1


def _write_circle_gerber(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "G04 circle test*",
                "%FSLAX46Y46*%",
                "%MOMM*%",
                "%ADD10C,0.200000*%",
                "D10*",
                "X0000000000Y0000000000D03*",
                "M02*",
            ]
        ),
        encoding="ascii",
    )


def _write_macro_gerber(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "G04 macro test*",
                "%FSLAX46Y46*%",
                "%MOMM*%",
                "%AMRECT*21,1,0.600000,0.300000,0,0,0*%",
                "%ADD10RECT*%",
                "D10*",
                "X0000000000Y0000000000D03*",
                "M02*",
            ]
        ),
        encoding="ascii",
    )


def _write_region_gerber(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "G04 region test*",
                "%FSLAX46Y46*%",
                "%MOMM*%",
                "G36*",
                "X0000000000Y0000000000D02*",
                "X0000600000Y0000000000D01*",
                "X0000600000Y0000300000D01*",
                "X0000000000Y0000300000D01*",
                "X0000000000Y0000000000D01*",
                "G37*",
                "M02*",
            ]
        ),
        encoding="ascii",
    )


def _write_pad_csv(path: Path, *, unit_side: str = "TOP") -> None:
    path.write_text(
        "RefDes,Pad,X,Y,Width,Height,Rotation,Side\n"
        f"U1,01,0,0,0.6,0.3,0,{unit_side}\n",
        encoding="utf-8",
    )


def _full_summary() -> dict[str, object]:
    return {
        "total_pads": 1,
        "matched_pads": 1,
        "coverage": 1.0,
        "duplicate_pad_rows": 0,
        "ambiguous_openings": 0,
        "unclassified_extra_openings": 0,
        "missing_thickness_pads": 0,
        "unmatched_pads": [],
        "requires_user_overlay_confirmation": False,
    }


def _nominal() -> dict[str, object]:
    return {
        "refdes": "U1",
        "pad": "01",
        "side": "TOP",
        "opening_count": 1,
        "nominal_area_mm2": 0.18,
        "resolved_thickness_mm": 0.06,
        "nominal_volume_mm3": 0.0108,
        "match_status": "MATCHED",
        "unmatched_reason": "",
        "preview_geometry": {},
    }


def test_load_pad_csv_preserves_leading_zero_and_converts_inches(tmp_path: Path) -> None:
    csv_path = tmp_path / "pads.csv"
    csv_path.write_text(
        "RefDes,Pad,X,Y,Width,Height,Rotation,Side\n"
        "U1,001,1,2,0.1,0.2,90,BOTTOM\n",
        encoding="utf-8",
    )

    pads = load_pad_csv(str(csv_path), unit="inch", side="BOTTOM")

    assert pads[0].pad == "001"
    assert pads[0].x_mm == pytest.approx(25.4)
    assert pads[0].height_mm == pytest.approx(5.08)
    assert pads[0].side == "BOTTOM"


def test_load_pad_csv_rejects_duplicate_pad_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "pads.csv"
    csv_path.write_text(
        "RefDes,Pad,X,Y,Width,Height,Rotation,Side\n"
        "U1,01,0,0,1,1,0,TOP\n"
        "U1,01,1,0,1,1,0,TOP\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="重複"):
        load_pad_csv(str(csv_path), unit="mm", side="TOP")


def test_gerber_rectangle_area_and_window_union(
    isolated_master_db: Path, tmp_path: Path
) -> None:
    gerber = tmp_path / "paste.gtp"
    _write_rect_gerber(gerber)
    assert save_stencil_spec(
        {
            "product_name": "P1",
            "stencil_type": "normal",
            "thickness_main": 0.06,
            "unit_mode": "absolute",
        }
    )
    openings = load_gerber_openings(str(gerber))
    pad = PadDefinition("U1", "01", 0.0, 0.0, 0.6, 0.3, 0.0, "TOP")

    result = analyze_stencil_import(
        product_name="P1", side="TOP", pads=[pad], openings=openings
    )

    assert len(openings) == 1
    assert openings[0].area == pytest.approx(0.18, rel=1e-5)
    assert result.validation_summary["matched_pads"] == 1
    assert result.nominals[0]["nominal_area_mm2"] == pytest.approx(0.18, rel=1e-5)
    assert result.nominals[0]["nominal_volume_mm3"] == pytest.approx(0.0108, rel=1e-5)

    split_result = analyze_stencil_import(
        product_name="P1",
        side="TOP",
        pads=[pad],
        openings=[box(-0.3, -0.15, -0.02, 0.15), box(0.02, -0.15, 0.3, 0.15)],
    )
    assert split_result.nominals[0]["opening_count"] == 2
    assert split_result.nominals[0]["nominal_area_mm2"] == pytest.approx(0.168)


@pytest.mark.parametrize(
    ("writer", "expected_area"),
    [
        (_write_circle_gerber, pytest.approx(3.141592653589793 * 0.1**2, rel=2e-3)),
        (_write_macro_gerber, pytest.approx(0.18, rel=1e-5)),
        (_write_region_gerber, pytest.approx(0.18, rel=1e-5)),
    ],
)
def test_gerber_circle_macro_and_region(
    tmp_path: Path, writer, expected_area
) -> None:
    path = tmp_path / "shape.gtp"
    writer(path)
    openings = load_gerber_openings(str(path))
    assert sum(opening.area for opening in openings) == expected_area


def test_bottom_mirror_candidate_is_selected(isolated_master_db: Path) -> None:
    assert save_stencil_spec(
        {"product_name": "BOTTOM-P", "stencil_type": "normal", "thickness_main": 0.1}
    )
    pads = [
        PadDefinition("U1", "1", 0.0, 0.0, 0.3, 0.3, 0.0, "BOTTOM"),
        PadDefinition("U1", "2", 2.0, 0.0, 0.3, 0.3, 0.0, "BOTTOM"),
        PadDefinition("U1", "3", 0.5, 1.0, 0.3, 0.3, 0.0, "BOTTOM"),
    ]
    openings = [
        box(-0.15, -0.15, 0.15, 0.15),
        box(-2.15, -0.15, -1.85, 0.15),
        box(-0.65, 0.85, -0.35, 1.15),
    ]
    result = analyze_stencil_import(
        product_name="BOTTOM-P", side="BOTTOM", pads=pads, openings=openings
    )
    assert result.transform["mirrored"] is True
    assert result.validation_summary["matched_pads"] == 3


def test_ambiguous_opening_missing_thickness_and_non_component_classification(
    isolated_master_db: Path,
) -> None:
    pads = [
        PadDefinition("U1", "1", 0.0, 0.0, 1.0, 1.0, 0.0, "TOP"),
        PadDefinition("U1", "2", 0.5, 0.0, 1.0, 1.0, 0.0, "TOP"),
    ]
    ambiguous = analyze_stencil_import(
        product_name="NO-SPEC",
        side="TOP",
        pads=pads,
        openings=[box(-0.25, -0.5, 0.75, 0.5)],
    )
    assert ambiguous.validation_summary["ambiguous_openings"] == 1
    assert ambiguous.validation_summary["matched_pads"] == 0

    assert save_stencil_spec(
        {"product_name": "EXTRA", "stencil_type": "normal", "thickness_main": 0.1}
    )
    one_pad = [PadDefinition("U1", "1", 0.0, 0.0, 0.4, 0.4, 0.0, "TOP")]
    openings = [box(-0.2, -0.2, 0.2, 0.2), box(4.0, 4.0, 4.2, 4.2)]
    extra = analyze_stencil_import(
        product_name="EXTRA", side="TOP", pads=one_pad, openings=openings
    )
    assert extra.validation_summary["unclassified_extra_openings"] == 1
    excluded = analyze_stencil_import(
        product_name="EXTRA",
        side="TOP",
        pads=one_pad,
        openings=openings,
        non_component_opening_indexes=extra.validation_summary["extra_opening_indexes"],
    )
    assert excluded.validation_summary["unclassified_extra_openings"] == 0


def test_overlapping_windows_use_union_not_sum(isolated_master_db: Path) -> None:
    assert save_stencil_spec(
        {"product_name": "OVERLAP", "stencil_type": "normal", "thickness_main": 0.1}
    )
    pad = PadDefinition("U1", "1", 0.0, 0.0, 1.0, 1.0, 0.0, "TOP")
    result = analyze_stencil_import(
        product_name="OVERLAP",
        side="TOP",
        pads=[pad],
        openings=[box(-0.4, -0.2, 0.1, 0.2), box(-0.1, -0.2, 0.4, 0.2)],
    )
    assert result.nominals[0]["opening_count"] == 2
    assert result.nominals[0]["nominal_area_mm2"] == pytest.approx(0.32)


def test_version_lifecycle_is_side_scoped_and_active_delete_is_blocked(
    isolated_master_db: Path, tmp_path: Path
) -> None:
    gerber = tmp_path / "source.gtp"
    csv_path = tmp_path / "pads.csv"
    _write_rect_gerber(gerber)
    _write_pad_csv(csv_path)

    version_id = create_stencil_document_version(
        product_name="P1",
        stencil_no="ST-001",
        revision="A",
        side="TOP",
        gerber_source=str(gerber),
        pad_csv_source=str(csv_path),
        coordinate_transform={"rotation_deg": 0, "scale": 1.0},
        validation_summary=_full_summary(),
        parser_version=PARSER_VERSION,
        nominals=[_nominal()],
        activate=True,
    )

    active = get_active_stencil_document("P1", "TOP")
    assert active is not None and active["id"] == version_id
    assert Path(active["gerber_path"]).is_file()
    assert Path(active["pad_csv_path"]).is_file()
    assert len(list_stencil_document_versions("P1", "TOP")) == 1
    assert remove_by_product_name("P1") is False
    with pytest.raises(ValueError, match="active"):
        delete_inactive_stencil_document_version(version_id)

    master_data_db._INITIALIZED = False
    replayed = get_active_stencil_document("P1", "TOP")
    assert replayed is not None and replayed["id"] == version_id
    backup = tmp_path / "spc_master.backup.db"
    shutil.copy2(isolated_master_db, backup)
    with sqlite3.connect(backup) as conn:
        assert conn.execute("SELECT COUNT(*) FROM stencil_document_versions").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM stencil_pad_nominals").fetchone()[0] == 1

    assert deactivate_stencil_document_version(version_id)
    managed_dir = Path(active["gerber_path"]).parent
    assert delete_inactive_stencil_document_version(version_id)
    assert not managed_dir.exists()
    with master_data_db.db_conn() as conn:
        actions = [
            row[0]
            for row in conn.execute(
                """
                SELECT action FROM audit_events
                WHERE entity_type = 'stencil_document_version' AND entity_id = ?
                ORDER BY id
                """,
                (str(version_id),),
            ).fetchall()
        ]
    assert actions == ["create", "deactivate", "delete"]


@pytest.mark.parametrize("suffix", [".dxf", ".pho"])
def test_version_library_preserves_generic_aperture_source_suffix(
    isolated_master_db: Path, tmp_path: Path, suffix: str
) -> None:
    aperture = tmp_path / f"source{suffix}"
    csv_path = tmp_path / "pads.csv"
    aperture.write_text("managed source fixture", encoding="utf-8")
    _write_pad_csv(csv_path)

    version_id = create_stencil_document_version(
        product_name="P1",
        stencil_no="ST-001",
        revision=suffix.removeprefix(".").upper(),
        side="TOP",
        gerber_source=str(aperture),
        pad_csv_source=str(csv_path),
        coordinate_transform={"rotation_deg": 0, "scale": 1.0},
        validation_summary=_full_summary(),
        parser_version=PARSER_VERSION,
        nominals=[_nominal()],
        activate=False,
    )

    stored = next(
        item for item in list_stencil_document_versions("P1", "TOP")
        if item["id"] == version_id
    )
    assert Path(stored["gerber_path"]).name == f"aperture{suffix}"


def test_nonactivatable_version_cannot_be_activated(
    isolated_master_db: Path, tmp_path: Path
) -> None:
    gerber = tmp_path / "source.gtp"
    csv_path = tmp_path / "pads.csv"
    _write_rect_gerber(gerber)
    _write_pad_csv(csv_path)
    summary = _full_summary()
    summary.update({"matched_pads": 0, "coverage": 0.0})
    version_id = create_stencil_document_version(
        product_name="P1",
        stencil_no="ST-001",
        revision="VERIFY",
        side="TOP",
        gerber_source=str(gerber),
        pad_csv_source=str(csv_path),
        coordinate_transform={},
        validation_summary=summary,
        parser_version=PARSER_VERSION,
        nominals=[{**_nominal(), "match_status": "UNMATCHED"}],
        activate=False,
    )
    with pytest.raises(ValueError, match="not activatable"):
        set_active_stencil_document_version(version_id)


def test_batch_delete_rejects_mixed_active_selection_without_partial_delete(
    isolated_master_db: Path, tmp_path: Path
) -> None:
    gerber = tmp_path / "source.gtp"
    csv_path = tmp_path / "pads.csv"
    _write_rect_gerber(gerber)
    _write_pad_csv(csv_path)
    active_id = create_stencil_document_version(
        product_name="P1",
        stencil_no="ST-001",
        revision="A",
        side="TOP",
        gerber_source=str(gerber),
        pad_csv_source=str(csv_path),
        coordinate_transform={"rotation_deg": 0, "scale": 1.0},
        validation_summary=_full_summary(),
        parser_version=PARSER_VERSION,
        nominals=[_nominal()],
        activate=True,
    )
    inactive_id = create_stencil_document_version(
        product_name="P1",
        stencil_no="ST-001",
        revision="B",
        side="TOP",
        gerber_source=str(gerber),
        pad_csv_source=str(csv_path),
        coordinate_transform={"rotation_deg": 0, "scale": 1.0},
        validation_summary=_full_summary(),
        parser_version=PARSER_VERSION,
        nominals=[_nominal()],
        activate=False,
    )

    with pytest.raises(ValueError, match="active"):
        delete_inactive_stencil_document_versions([active_id, inactive_id])
    assert {row["id"] for row in list_stencil_document_versions("P1", "TOP")} == {
        active_id,
        inactive_id,
    }

    assert delete_inactive_stencil_document_versions([inactive_id]) == [inactive_id]
    assert [row["id"] for row in list_stencil_document_versions("P1", "TOP")] == [active_id]


def test_nominal_with_blank_key_cannot_be_activated(
    isolated_master_db: Path, tmp_path: Path
) -> None:
    gerber = tmp_path / "source.gtp"
    csv_path = tmp_path / "pads.csv"
    _write_rect_gerber(gerber)
    _write_pad_csv(csv_path)
    version_id = create_stencil_document_version(
        product_name="P1",
        stencil_no="ST-001",
        revision="BLANK-KEY",
        side="TOP",
        gerber_source=str(gerber),
        pad_csv_source=str(csv_path),
        coordinate_transform={},
        validation_summary=_full_summary(),
        parser_version=PARSER_VERSION,
        nominals=[{**_nominal(), "pad": ""}],
        activate=False,
    )
    with pytest.raises(ValueError, match="not activatable"):
        set_active_stencil_document_version(version_id)


def test_acceptance_percentage_example_and_incomplete_coverage_contract(
    isolated_master_db: Path, tmp_path: Path
) -> None:
    gerber = tmp_path / "source.gtp"
    csv_path = tmp_path / "pads.csv"
    _write_rect_gerber(gerber)
    _write_pad_csv(csv_path)
    create_stencil_document_version(
        product_name="VS80",
        stencil_no="ST-080",
        revision="A",
        side="TOP",
        gerber_source=str(gerber),
        pad_csv_source=str(csv_path),
        coordinate_transform={"rotation_deg": 0, "mirrored": False, "scale": 1.0},
        validation_summary=_full_summary(),
        parser_version=PARSER_VERSION,
        nominals=[_nominal()],
        activate=True,
    )
    raw = pd.DataFrame(
        {
            "BaseRefDes": ["U1"],
            "Pad": ["01"],
            "Volume": [0.01391],
            "Area": [0.16899],
            "Height": [0.0823],
        }
    )
    result = derive_percentage_dataframe(
        raw,
        product_name="VS80",
        side="TOP",
        measurement_units={"Volume": "mm3", "Area": "mm2", "Height": "mm"},
    )
    assert result.metadata["value_domain"] == "percent"
    assert result.metadata["coverage"] == 1.0
    assert result.dataframe.loc[0, "Volume"] == pytest.approx(128.80, abs=0.01)
    assert result.dataframe.loc[0, "Area"] == pytest.approx(93.88, abs=0.01)
    assert result.dataframe.loc[0, "Height"] == pytest.approx(137.17, abs=0.01)
    pd.testing.assert_frame_equal(
        raw,
        pd.DataFrame(
            {
                "BaseRefDes": ["U1"],
                "Pad": ["01"],
                "Volume": [0.01391],
                "Area": [0.16899],
                "Height": [0.0823],
            }
        ),
    )

    incomplete = pd.concat(
        [raw, raw.assign(BaseRefDes="U2", Pad="02")], ignore_index=True
    )
    blocked = derive_percentage_dataframe(
        incomplete,
        product_name="VS80",
        side="TOP",
        measurement_units={"Volume": "mm3", "Area": "mm2", "Height": "mm"},
    )
    assert blocked.metadata["value_domain"] == "raw"
    assert blocked.metadata["verify"] is True
    assert blocked.metadata["coverage"] == pytest.approx(0.5)
    assert "U2/02" in blocked.metadata["unmatched_pads"]
    pd.testing.assert_frame_equal(blocked.dataframe, incomplete)


def test_missing_raw_reading_stays_nan_and_keeps_percent_domain(
    isolated_master_db: Path, tmp_path: Path
) -> None:
    gerber = tmp_path / "source.gtp"
    csv_path = tmp_path / "pads.csv"
    _write_rect_gerber(gerber)
    _write_pad_csv(csv_path)
    create_stencil_document_version(
        product_name="VS80",
        stencil_no="ST-080",
        revision="A",
        side="TOP",
        gerber_source=str(gerber),
        pad_csv_source=str(csv_path),
        coordinate_transform={"rotation_deg": 0, "mirrored": False, "scale": 1.0},
        validation_summary=_full_summary(),
        parser_version=PARSER_VERSION,
        nominals=[_nominal()],
        activate=True,
    )
    # Non-default index labels: derived rows must stay aligned with the caller.
    raw = pd.DataFrame(
        {
            "BaseRefDes": ["U1", "U1"],
            "Pad": ["01", "01"],
            "Volume": [0.01391, 0.01391],
            "Area": [0.16899, 0.16899],
            "Height": [0.0823, float("nan")],
        },
        index=[10, 20],
    )
    result = derive_percentage_dataframe(
        raw,
        product_name="VS80",
        side="TOP",
        measurement_units={"Volume": "mm3", "Area": "mm2", "Height": "mm"},
    )
    assert result.metadata["value_domain"] == "percent"
    assert result.metadata["verify"] is False
    assert list(result.dataframe.index) == [10, 20]
    assert result.dataframe.loc[10, "Height"] == pytest.approx(137.17, abs=0.01)
    assert pd.isna(result.dataframe.loc[20, "Height"])
    assert result.dataframe.loc[20, "Volume"] == pytest.approx(128.80, abs=0.01)
