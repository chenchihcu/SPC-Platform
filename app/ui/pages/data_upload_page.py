"""
量測資料上傳頁（步驟三）：選擇 SPI 量測 CSV 並送出路徑。
無 stepCard 包裝；欄位驗證結果由 MainWindow 經 DataSetupPage.update_meas_display 更新 lbl_path。

Redesign v2: 垂直表單結構，標籤在上、控件在下，避免窄欄擠壓文字。
"""
from PySide6 import QtWidgets
from PySide6.QtWidgets import QWidget, QLabel, QSizePolicy, QFrame
from PySide6.QtCore import Signal
from datetime import datetime
import os

from app.ui.theme import stabilize_minimum_height
from app.ui.widgets.csv_file_selector_pane import CsvFileSelectorPane
from app.ui.widgets.page_templates import (
    CsvDropZoneMixin,
    page_margins_and_spacing,
    setup_page_header_with_status,
)
from app.ui.theme.tokens import (
    SPACING_12,
    SPACING_8,
    DATA_SETUP_CARD_CONTENT_PADDING,
    DATA_SETUP_PRIMARY_CARD_MIN_HEIGHT,
    DATA_SETUP_SECONDARY_CARD_MIN_HEIGHT,
)


class DataUploadPage(CsvDropZoneMixin, QWidget):
    """上傳量測 CSV：僅路徑列與選檔按鈕；不內嵌表格預覽。"""
    meas_uploaded = Signal(str)

    def __init__(self, parent=None, embedded: bool = False) -> None:
        super().__init__(parent)
        self._embedded = embedded
        # embedded 時不再用 Maximum — 讓卡片按內容高度展開，避免表單被壓縮
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.setAcceptDrops(True)
        root = QtWidgets.QVBoxLayout(self)
        if embedded:
            root.setContentsMargins(0, 0, 0, 0)
            root.setSpacing(SPACING_8)
        else:
            page_margins_and_spacing(root)

        if not self._embedded:
            self.header_lbl, self.status_lamp, self.status_text = setup_page_header_with_status(root, "量測")

        # ── 上傳卡片（共用 CSV 選檔區塊）──
        self.file_pane = CsvFileSelectorPane(
            embedded=embedded,
            browse_text="選量測檔",
            browse_tooltip="選擇並載入 SPI 量測 CSV 至目前分析會話",
            dialog_title="選擇 SPI 量測 CSV",
            field_label="量測檔路徑 (*.csv)",
            card_title="量測檔",
            drop_hint_text="將量測 CSV 拖放至此，或按「選量測檔」",
            card_min_height=DATA_SETUP_PRIMARY_CARD_MIN_HEIGHT,
            parent=self,
        )
        self.file_pane.btn_browse.setObjectName("uploadMeasBtn")
        self.file_pane.file_selected.connect(self._accept_measurement_file)
        self.btn_browse = self.file_pane.btn_browse
        self.lbl_path = self.file_pane.lbl_path
        self.lbl_meta = self.file_pane.lbl_meta
        self.drop_zone: QFrame = self.file_pane.drop_zone
        self.drop_zone_hint = self.file_pane.drop_zone_hint
        root.addWidget(self.file_pane)

        # ── 上傳狀態卡片 ──
        if not self._embedded:
            _pad = DATA_SETUP_CARD_CONTENT_PADDING
            status_card = QFrame()
            status_card.setObjectName("stepCard")
            status_card.setMinimumHeight(DATA_SETUP_SECONDARY_CARD_MIN_HEIGHT)
            status_lay = QtWidgets.QVBoxLayout(status_card)
            status_lay.setContentsMargins(_pad, _pad, _pad, _pad)
            status_lay.setSpacing(SPACING_12)
            status_title = QLabel("載入狀態")
            status_title.setProperty("class", "stepTitle")
            status_title.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            status_lay.addWidget(status_title)
            stabilize_minimum_height(status_card, DATA_SETUP_SECONDARY_CARD_MIN_HEIGHT)
            root.addWidget(status_card)
            root.addStretch(1)

    def set_path_text(self, text: str) -> None:
        """Display the given file path in the path label widget."""
        self.file_pane.set_path_text(text)

    def set_metadata(self, filename: str | None, row_count: int | None, timestamp: str | None) -> None:
        """Update filename/row-count/timestamp status text for the loaded CSV."""
        self.file_pane.set_metadata(filename, row_count, timestamp)

    def reset_upload_state(self) -> None:
        """Reset path and metadata labels when product context changes."""
        self.file_pane.reset()

    def _accept_measurement_file(self, file_path: str) -> None:
        self._set_drop_zone_active(False)
        self.set_path_text(f"目前載入量測檔：{file_path}")
        self.set_metadata(
            os.path.basename(file_path),
            None,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        self.meas_uploaded.emit(file_path)

    def _set_drop_zone_active(self, active: bool) -> None:
        """Toggle the drop zone highlight state (drag-over feedback)."""
        self.file_pane.set_drop_zone_active(active)

    def _on_csv_dropped(self, file_path: str) -> None:
        """CsvDropZoneMixin hook: accept the dropped measurement file."""
        self._accept_measurement_file(file_path)
