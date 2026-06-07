from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scripts import import_spi_process_kb_xlsx as importer


def _mk_sheet_df(sheet: str) -> pd.DataFrame:
    if sheet == "rules":
        return pd.DataFrame(
            [
                {
                    "rule_id": "R001",
                    "signal_a": "A",
                    "signal_b": "B",
                    "cause_hypotheses": "Cause1;Cause2",
                    "confidence_stars": "3",
                }
            ]
        )
    if sheet == "matrix":
        return pd.DataFrame(
            [
                {
                    "spi_dimension": "Volume",
                    "abnormality_type": "Drift",
                    "stencil": "ok",
                }
            ]
        )
    if sheet == "checklist":
        return pd.DataFrame(
            [
                {
                    "process_category": "Stencil",
                    "inspection_item": "AR",
                    "priority_stars": "3",
                }
            ]
        )
    if sheet == "chart":
        return pd.DataFrame(
            [
                {
                    "chart_type": "CUSUM",
                    "observed_signal": "Drift",
                    "rule_ids": "R001",
                }
            ]
        )
    raise ValueError(f"unexpected sheet: {sheet}")


def test_import_spi_kb_returns_nonzero_when_required_sheet_fails(
    tmp_path: Path, monkeypatch
) -> None:
    xlsx = tmp_path / "kb.xlsx"
    xlsx.write_text("dummy", encoding="utf-8")
    out_dir = tmp_path / "out"

    def _fake_read(_xlsx: Path, sheet: str, *, header: int = 0):
        if sheet == "rules":
            raise ValueError("Worksheet named 'rules' not found")
        return _mk_sheet_df(sheet)

    monkeypatch.setattr(importer, "_read_sheet", _fake_read)
    rc = importer.main(
        [
            str(xlsx),
            "--out",
            str(out_dir),
            "--sheet-rules",
            "rules",
            "--sheet-matrix",
            "matrix",
            "--sheet-checklist",
            "checklist",
            "--sheet-chart",
            "chart",
            "--header-row",
            "0",
        ]
    )

    assert rc == 1
    report = (out_dir / "import_report.txt").read_text(encoding="utf-8")
    assert "sheet_missing_or_error:rules:" in report


def test_import_spi_kb_success_writes_manifest(tmp_path: Path, monkeypatch) -> None:
    xlsx = tmp_path / "kb.xlsx"
    xlsx.write_text("dummy", encoding="utf-8")
    out_dir = tmp_path / "out"

    def _fake_read(_xlsx: Path, sheet: str, *, header: int = 0):
        return _mk_sheet_df(sheet)

    monkeypatch.setattr(importer, "_read_sheet", _fake_read)
    rc = importer.main(
        [
            str(xlsx),
            "--out",
            str(out_dir),
            "--sheet-rules",
            "rules",
            "--sheet-matrix",
            "matrix",
            "--sheet-checklist",
            "checklist",
            "--sheet-chart",
            "chart",
            "--header-row",
            "0",
        ]
    )

    assert rc == 0
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["source_xlsx_basename"] == "kb.xlsx"
    assert "import_report" in manifest
