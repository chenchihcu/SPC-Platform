"""Watchlist #1: DataLoaderWorker QThread.start() + finished signal (not synchronous run())."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from app.data.session_store import SessionStore
from app.services.import_service import DataLoaderWorker


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_data_loader_worker_loads_golden_csvs_via_qthread(qapp, tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    golden = repo_root / "golden_dataset" / "normal_baseline"
    coord = golden / "coords.csv"
    meas = golden / "measurements.csv"
    assert coord.is_file() and meas.is_file()

    store = SessionStore()
    store.clear()
    try:
        worker = DataLoaderWorker(str(coord), str(meas))
        outcomes: list[tuple[bool, str]] = []

        def _on_finished(ok: bool, msg: str) -> None:
            outcomes.append((ok, msg))

        worker.finished.connect(_on_finished)
        loop = QEventLoop()
        worker.finished.connect(loop.quit)
        QTimer.singleShot(120_000, loop.quit)

        worker.start()
        loop.exec()

        assert outcomes, "expected finished signal before timeout"
        assert outcomes[0][0] is True, outcomes[0][1]
        assert store.meas_meta.get("is_valid") is True
        assert store.coord_meta.get("is_valid") is True
        assert store.joined_df is not None
        assert len(store.joined_df) > 0
    finally:
        store.clear()


def test_data_loader_worker_cancel_before_start_emits_finished(qapp) -> None:
    worker = DataLoaderWorker("", "")
    outcomes: list[tuple[bool, str]] = []
    worker.finished.connect(lambda ok, msg: outcomes.append((ok, msg)))
    loop = QEventLoop()
    worker.finished.connect(loop.quit)
    QTimer.singleShot(10_000, loop.quit)

    worker.cancel()
    worker.start()
    loop.exec()

    assert outcomes == [(False, "Cancelled")]
