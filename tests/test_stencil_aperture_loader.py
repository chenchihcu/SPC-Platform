from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path

import ezdxf
import pytest
from ezdxf import units as dxf_units

from app.services.stencil_aperture_loader import (
    detect_aperture_format,
    load_aperture_source,
)


def _rect_gerber(*, side: str | None = None) -> str:
    lines = ["G04 stencil test*"]
    if side:
        lines.append(f"%TF.FileFunction,Paste,{side}*%")
    lines.extend(
        [
            "%FSLAX46Y46*%",
            "%MOMM*%",
            "%ADD10R,0.600000X0.300000*%",
            "D10*",
            "X0000000000Y0000000000D03*",
            "M02*",
        ]
    )
    return "\n".join(lines)


def _legacy_pho(layer_name: str) -> str:
    return "\n".join(
        [
            "*",
            "%LPD*%",
            f"%LN{layer_name}.pho*%",
            "%FSLAX24Y24*%",
            "%MOMM*%",
            "%AD*%",
            "%AD*%",
            "%ADD10C,0.1*%",
            "G75*",
            "G54D10*",
            "G1X10000Y0D2*",
            "G3X0Y10000I-10000D1*",
            "G1X10000*",
            "M2*",
        ]
    )


def _write_odb_archive(path: Path, *, feature_record: str = "P 0 0 0 P 0 0") -> None:
    matrix = """STEP {
ROW=1
COL=1
NAME=pcb
}
LAYER {
ROW=1
CONTEXT=BOARD
TYPE=SOLDER_PASTE
NAME=SPT
}
LAYER {
ROW=2
CONTEXT=BOARD
TYPE=SIGNAL
NAME=TOP
}
LAYER {
ROW=3
CONTEXT=BOARD
TYPE=SOLDER_PASTE
NAME=SPB
}
"""
    features = f"""UNITS=MM
$0 rect600x300
#Layer features
{feature_record}
"""
    members = {
        "job/matrix/matrix": matrix.encode("ascii"),
        "job/steps/pcb/layers/SPT/features": features.encode("ascii"),
        "job/steps/pcb/layers/SPB/features": features.encode("ascii"),
    }
    if path.suffix.casefold() == ".zip":
        with zipfile.ZipFile(path, "w") as archive:
            for name, content in members.items():
                archive.writestr(name, content)
        return
    with tarfile.open(path, mode="w:gz") as archive:
        for name, content in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))


def _write_ipc2581(path: Path, feature_xml: str, units: str = "MM") -> None:
    path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<IPC-2581 revision="C">
  <CadData>
    <CadHeader units="{units}" />
    <Layer name="PASTETOP" layerFunction="PASTEMASK" side="TOP" />
    <Layer name="PASTEBOT" layerFunction="PASTEMASK" side="BOTTOM" />
    <Step>
      <LayerFeature layerRef="PASTETOP">
        <Set>
          <Features>{feature_xml}</Features>
        </Set>
      </LayerFeature>
    </Step>
  </CadData>
</IPC-2581>
""",
        encoding="utf-8",
    )


def test_single_gerber_preserves_legacy_geometry_and_side_metadata(tmp_path: Path) -> None:
    source = tmp_path / "board.gtp"
    source.write_text(_rect_gerber(side="Top"), encoding="ascii")

    result = load_aperture_source(str(source), side="TOP")

    assert result.format_id == "gerber"
    assert result.source_layer == "board.gtp"
    assert result.warnings == ()
    assert sum(item.area for item in result.openings) == pytest.approx(0.18, rel=1e-5)
    with pytest.raises(ValueError, match="與匯入 Side=BOTTOM 不符"):
        load_aperture_source(str(source), side="BOTTOM")


def test_standard_gerber_name_ending_in_top_is_not_misclassified(tmp_path: Path) -> None:
    source = tmp_path / "desktop.gbr"
    source.write_text(_rect_gerber(), encoding="ascii")

    result = load_aperture_source(str(source), side="BOTTOM")

    assert result.warnings == ("Gerber 未帶可辨識 Side metadata；必須以疊圖人工確認",)


def test_gerber_zip_selects_only_requested_paste_side(tmp_path: Path) -> None:
    source = tmp_path / "gerbers.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("layers/paste_top.gtp", _rect_gerber(side="Top"))
        archive.writestr("layers/paste_bottom.gbp", _rect_gerber(side="Bot"))

    result = load_aperture_source(str(source), side="BOTTOM")

    assert detect_aperture_format(source) == "gerber_zip"
    assert result.format_id == "gerber_zip"
    assert result.source_layer == "layers/paste_bottom.gbp"
    assert sum(item.area for item in result.openings) == pytest.approx(0.18, rel=1e-5)


def test_legacy_pho_normalizes_only_disclosed_dialect_and_side(tmp_path: Path) -> None:
    source = tmp_path / "SMDTOP.pho"
    source.write_text(_legacy_pho("SMDTOP"), encoding="ascii")

    result = load_aperture_source(str(source), side="TOP")

    assert detect_aperture_format(source) == "gerber"
    assert result.format_label == "Legacy Gerber/Photoplotter (.pho)"
    assert result.source_layer == "SMDTOP.pho"
    assert result.openings
    assert result.warnings == (
        "Legacy PHO 正規化：G-code=3、D-code=2、隱含 D=1、缺省 I/J=0/1、空 AD=2",
    )
    with pytest.raises(ValueError, match="與匯入 Side=BOTTOM 不符"):
        load_aperture_source(str(source), side="BOTTOM")


@pytest.mark.parametrize("layer", ["TXTTOP", "TXTBOT"])
def test_legacy_pho_rejects_text_reference_layers(tmp_path: Path, layer: str) -> None:
    source = tmp_path / f"{layer}.pho"
    source.write_text(_legacy_pho(layer), encoding="ascii")

    with pytest.raises(ValueError, match="文字參考層，不是鋼板開窗層"):
        load_aperture_source(
            str(source), side="TOP" if layer.endswith("TOP") else "BOTTOM"
        )


def test_legacy_pho_rejects_unknown_layer_role(tmp_path: Path) -> None:
    source = tmp_path / "BOARD.pho"
    source.write_text(_legacy_pho("BOARD"), encoding="ascii")

    with pytest.raises(ValueError, match="無法.*確認為 SMD/Paste 開窗層"):
        load_aperture_source(str(source), side="TOP")


def test_gerber_zip_excludes_text_pho_and_selects_smd_pho(tmp_path: Path) -> None:
    source = tmp_path / "legacy-pho.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("layers/SMDTOP.pho", _legacy_pho("SMDTOP"))
        archive.writestr("layers/TXTTOP.pho", _legacy_pho("TXTTOP"))

    result = load_aperture_source(str(source), side="TOP")

    assert result.source_layer == "layers/SMDTOP.pho"
    assert result.openings
    assert any("Legacy PHO 正規化" in warning for warning in result.warnings)
    assert any("TXTTOP.pho" in warning for warning in result.warnings)


def test_archive_path_traversal_is_rejected(tmp_path: Path) -> None:
    source = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("../paste.gtp", _rect_gerber())

    with pytest.raises(ValueError, match="不安全路徑"):
        detect_aperture_format(source)


def test_ipc2581_contour_is_loaded_in_millimetres(tmp_path: Path) -> None:
    source = tmp_path / "board.xml"
    _write_ipc2581(
        source,
        """<Contour><Polygon>
          <PolyBegin x="-0.3" y="-0.15" />
          <PolyStepSegment x="0.3" y="-0.15" />
          <PolyStepSegment x="0.3" y="0.15" />
          <PolyStepSegment x="-0.3" y="0.15" />
          <PolyStepSegment x="-0.3" y="-0.15" />
        </Polygon></Contour>""",
    )

    result = load_aperture_source(str(source), side="TOP")

    assert result.format_id == "ipc2581"
    assert result.format_label == "IPC-2581C"
    assert result.source_layer == "PASTETOP"
    assert sum(item.area for item in result.openings) == pytest.approx(0.18)


@pytest.mark.parametrize(
    ("units", "scale"),
    [("MILLIMETER", 1.0), ("INCH", 25.4), ("MICRON", 0.001)],
)
def test_ipc2581_standard_units_are_converted_to_millimetres(
    tmp_path: Path, units: str, scale: float
) -> None:
    source = tmp_path / f"board-{units}.xml"
    _write_ipc2581(
        source,
        """<Contour><Polygon>
          <PolyBegin x="-3" y="-1.5" />
          <PolyStepSegment x="3" y="-1.5" />
          <PolyStepSegment x="3" y="1.5" />
          <PolyStepSegment x="-3" y="1.5" />
          <PolyStepSegment x="-3" y="-1.5" />
        </Polygon></Contour>""",
        units=units,
    )

    result = load_aperture_source(str(source), side="TOP")

    assert sum(item.area for item in result.openings) == pytest.approx(18.0 * scale * scale)


def test_ipc2581_accepts_bounded_exporter_arc_quantization(tmp_path: Path) -> None:
    source = tmp_path / "quantized-arc.ipc2581"
    _write_ipc2581(
        source,
        """<Polyline>
          <PolyBegin x="1" y="0" />
          <PolyStepCurve x="0" y="1.000254" centerX="0" centerY="0" clockwise="false" />
          <LineDesc lineWidth="0.1" lineEnd="ROUND" />
        </Polyline>""",
    )

    result = load_aperture_source(str(source), side="TOP")

    assert result.openings
    assert sum(item.area for item in result.openings) > 0.15


def test_ipc2581_rejects_unknown_paste_geometry(tmp_path: Path) -> None:
    source = tmp_path / "unknown.xml"
    _write_ipc2581(source, '<Circle diameter="1" />')

    with pytest.raises(ValueError, match="未支援幾何.*Circle"):
        load_aperture_source(str(source), side="TOP")


def test_dxf_closed_paste_layer_uses_declared_units(tmp_path: Path) -> None:
    source = tmp_path / "stencil.dxf"
    document = ezdxf.new("R2013")
    document.units = dxf_units.MM
    document.layers.add("Paste_Top")
    document.modelspace().add_lwpolyline(
        [(-0.3, -0.15), (0.3, -0.15), (0.3, 0.15), (-0.3, 0.15)],
        close=True,
        dxfattribs={"layer": "Paste_Top"},
    )
    document.saveas(source)

    result = load_aperture_source(str(source), side="TOP")

    assert result.format_id == "dxf"
    assert result.source_layer == "Paste_Top"
    assert result.warnings == ()
    assert sum(item.area for item in result.openings) == pytest.approx(0.18)


def test_dxf_unitless_requires_explicit_override(tmp_path: Path) -> None:
    source = tmp_path / "unitless.dxf"
    document = ezdxf.new("R2013")
    document.header["$INSUNITS"] = 0
    document.modelspace().add_circle((0, 0), radius=0.5)
    document.saveas(source)

    with pytest.raises(ValueError, match="INSUNITS"):
        load_aperture_source(str(source), side="TOP")

    result = load_aperture_source(str(source), side="TOP", unit_override="mm")
    assert result.warnings == ("DXF 單位由使用者指定為 mm",)
    assert sum(item.area for item in result.openings) == pytest.approx(
        3.141592653589793 * 0.5**2,
        rel=2e-3,
    )


@pytest.mark.parametrize("suffix", [".tgz", ".zip"])
def test_odbpp_archive_selects_solder_paste_layer(
    tmp_path: Path, suffix: str
) -> None:
    source = tmp_path / f"board{suffix}"
    _write_odb_archive(source)

    result = load_aperture_source(str(source), side="TOP")

    assert detect_aperture_format(source) == "odbpp"
    assert result.format_id == "odbpp"
    assert result.source_layer == "SPT"
    assert sum(item.area for item in result.openings) == pytest.approx(0.18)


def test_odbpp_rejects_unknown_feature_record(tmp_path: Path) -> None:
    source = tmp_path / "unknown.tgz"
    _write_odb_archive(source, feature_record="B 0 0 0")

    with pytest.raises(ValueError, match="未支援 feature record.*B=1"):
        load_aperture_source(str(source), side="TOP")
