"""CoordValidationWorker: background coordinate sniff validation."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")


def test_coord_validation_worker_emits_finished_for_valid_snippet(tmp_path: Path) -> None:
    from app.ui.pages.coordinate_manager_page import CoordValidationWorker

    csv_path = tmp_path / "coord.csv"
    csv_path.write_text("RefDes,X,Y\nR1,1.0,2.0\n", encoding="utf-8")

    worker = CoordValidationWorker(str(csv_path))
    emitted: list[tuple[object, ...]] = []

    def _capture(*args: object) -> None:
        emitted.append(args)

    worker.finished.connect(_capture)
    worker.run()

    assert len(emitted) == 1
    fp, is_valid, missing, total_rows = emitted[0]
    assert fp == str(csv_path)
    assert is_valid is True
    assert missing == []
    assert total_rows == 1
