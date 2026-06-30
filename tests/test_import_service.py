import pandas as pd

from app.data.session_store import SessionStore
from app.services import import_service


def _fresh_store() -> SessionStore:
    store = SessionStore()
    store.clear()
    return store


def test_dataloader_empty_paths_use_empty_dataframes_and_blank_batch_qty() -> None:
    store = _fresh_store()
    worker = import_service.DataLoaderWorker(coord_path="", meas_path="")
    worker.store = store

    worker.run()

    assert isinstance(store.coord_df, pd.DataFrame)
    assert store.coord_df.empty
    assert store.coord_meta.get("is_valid") is False

    assert isinstance(store.meas_df, pd.DataFrame)
    assert store.meas_df.empty
    assert store.meas_meta.get("is_valid") is False

    assert store.workorder_master.get("batch_qty") == ""
    assert isinstance(store.joined_df, pd.DataFrame)
    assert store.joined_df.empty
    assert store.relation_meta.get("can_do_spatial") is False


def test_dataloader_batch_qty_uses_unique_board_count_when_boardno_exists(monkeypatch) -> None:
    seen_suppliers: list[str] = []

    class _FakeCoordinateLoader:
        def load(self, _path: str):
            return pd.DataFrame({"RefDes": ["R1"], "X": [1.0], "Y": [2.0]}), {"is_valid": True}

    class _FakeMeasurementLoader:
        def load(self, _path: str, supplier: str = ""):
            seen_suppliers.append(supplier)
            df = pd.DataFrame(
                {
                    "BoardNo": ["B1", "B1", "B2", "B3"],
                    "RefDes": ["R1", "R1", "R1", "R1"],
                    "Volume": [100.0, 101.0, 99.0, 102.0],
                }
            )
            return df, {"is_valid": True}

    def _fake_join(coord_df: pd.DataFrame, meas_df: pd.DataFrame):
        joined = meas_df.copy()
        joined["X"] = 1.0
        joined["Y"] = 2.0
        return joined, {"match_rate": 1.0, "can_do_spatial": True}

    monkeypatch.setattr(import_service, "CoordinateLoader", _FakeCoordinateLoader)
    monkeypatch.setattr(import_service, "MeasurementLoader", _FakeMeasurementLoader)
    monkeypatch.setattr(import_service.JoinEngine, "join", staticmethod(_fake_join))

    store = _fresh_store()
    store.workorder_master["supplier"] = "振順豐"
    worker = import_service.DataLoaderWorker(coord_path="coord.csv", meas_path="meas.csv")
    worker.store = store

    worker.run()

    assert seen_suppliers == ["振順豐"]
    assert store.workorder_master.get("batch_qty") == "3"
    assert store.relation_meta.get("can_do_spatial") is True
    assert isinstance(store.joined_df, pd.DataFrame)
    assert len(store.joined_df) == 4


def test_dataloader_batch_qty_falls_back_to_row_count_without_boardno(monkeypatch) -> None:
    class _FakeCoordinateLoader:
        def load(self, _path: str):
            return pd.DataFrame({"RefDes": ["R1"], "X": [1.0], "Y": [2.0]}), {"is_valid": True}

    class _FakeMeasurementLoader:
        def load(self, _path: str, supplier: str = ""):
            _ = supplier
            df = pd.DataFrame({"RefDes": ["R1", "R2", "R3"], "Volume": [1.0, 2.0, 3.0]})
            return df, {"is_valid": True}

    def _fake_join(coord_df: pd.DataFrame, meas_df: pd.DataFrame):
        return meas_df.copy(), {"match_rate": 0.5, "can_do_spatial": True}

    monkeypatch.setattr(import_service, "CoordinateLoader", _FakeCoordinateLoader)
    monkeypatch.setattr(import_service, "MeasurementLoader", _FakeMeasurementLoader)
    monkeypatch.setattr(import_service.JoinEngine, "join", staticmethod(_fake_join))

    store = _fresh_store()
    worker = import_service.DataLoaderWorker(coord_path="coord.csv", meas_path="meas.csv")
    worker.store = store

    worker.run()

    assert store.workorder_master.get("batch_qty") == "3"
    assert store.relation_meta.get("can_do_spatial") is True
