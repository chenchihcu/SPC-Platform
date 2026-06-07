from PySide6.QtCore import QThread, Signal
import pandas as pd
from app.data.loaders.coordinate_loader import CoordinateLoader
from app.data.loaders.measurement_loader import MeasurementLoader
from app.data.relation.join_engine import JoinEngine
from app.data.session_store import SessionStore

class DataLoaderWorker(QThread):
    """
    Background worker thread to offload heavy CSV parsing and pandas joining.
    Prevents UI thread freezing on >100k data sets. 
    """
    progress_changed = Signal(str)
    progress_value_changed = Signal(int)  # 0-100
    finished = Signal(bool, str) # success flag, status msg
    
    def __init__(self, coord_path: str = "", meas_path: str = ""):
        super().__init__()
        self.coord_path = coord_path
        self.meas_path = meas_path
        self.store = SessionStore()
        self._is_cancelled = False
        
    def cancel(self) -> None:
        """Set cancellation flag to abort the run (Pass 145)."""
        self._is_cancelled = True
        self.progress_value_changed.emit(-2) # Hide

    def _finish_if_cancelled(self) -> bool:
        if not self._is_cancelled:
            return False
        self.finished.emit(False, "Cancelled")
        return True

    def run(self) -> None:
        """Execute the background task."""
        try:
            if self._finish_if_cancelled():
                return
            # Load Coordinates
            self.progress_changed.emit("載入座標檔中 (Loading Coordinates)...")
            self.progress_value_changed.emit(10)
            if self.coord_path:
                coord_loader = CoordinateLoader()
                self.store.coord_df, self.store.coord_meta = coord_loader.load(self.coord_path)
            else:
                self.store.coord_df, self.store.coord_meta = pd.DataFrame(), {"is_valid": False}
            
            if self._finish_if_cancelled():
                return
            self.progress_value_changed.emit(40)
                
            # Load Measurements
            self.progress_changed.emit("載入量測檔中 (Loading Measurements)...")
            if self.meas_path:
                meas_loader = MeasurementLoader()
                self.store.meas_df, self.store.meas_meta = meas_loader.load(self.meas_path)
            else:
                self.store.meas_df, self.store.meas_meta = pd.DataFrame(), {"is_valid": False}

            self.progress_value_changed.emit(70)

            # Batch qty: single source from measurement data (unique board count or total rows)
            if self.store.workorder_master is None:
                self.store.workorder_master = {}
            if self.store.meas_df is not None and not self.store.meas_df.empty:
                if "BoardNo" in self.store.meas_df.columns:
                    self.store.workorder_master["batch_qty"] = str(self.store.meas_df["BoardNo"].nunique())
                else:
                    self.store.workorder_master["batch_qty"] = str(len(self.store.meas_df))
            else:
                self.store.workorder_master["batch_qty"] = ""

            if self._finish_if_cancelled():
                return

            # Data Join
            self.progress_changed.emit("執行資料關聯 (Joining Datasets)...")
            self.progress_value_changed.emit(85)
            if self.store.coord_meta.get("is_valid") and self.store.meas_meta.get("is_valid"):
                self.store.joined_df, self.store.relation_meta = JoinEngine.join(self.store.coord_df, self.store.meas_df)
            else:
                self.store.joined_df = self.store.meas_df if self.store.meas_df is not None else None
                self.store.relation_meta = {"match_rate": 0.0, "can_do_spatial": False, "error": "Cannot join"}
                
            if self._finish_if_cancelled():
                return

            self.progress_value_changed.emit(100)
            self.progress_changed.emit("載入完成 (Load Complete)")
            self.finished.emit(True, "Success")

        except (
            pd.errors.EmptyDataError,
            pd.errors.ParserError,
            UnicodeDecodeError,
            OSError,
            ValueError,
            TypeError,
            KeyError,
            RuntimeError,
        ) as e:
            # 任何未預期例外：集中回報清楚錯誤訊息給 UI / 呼叫端
            msg = f"資料載入失敗: {e}"
            self.store.meas_meta = {"is_valid": False, "error": msg}
            self.store.coord_meta = {"is_valid": False, "error": msg}
            self.store.relation_meta = {"match_rate": 0.0, "can_do_spatial": False, "error": msg}
            self.finished.emit(False, msg)
