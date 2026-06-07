"""
量測資料上傳頁（步驟三）：選擇 SPI 量測 CSV 並送出路徑。
無 stepCard 包裝；欄位驗證結果由 MainWindow 經 DataSetupPage.update_meas_display 更新 lbl_path。

Redesign v2: 垂直表單結構，標籤在上、控件在下，避免窄欄擠壓文字。
"""
from PySide6 import QtWidgets
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QFileDialog,
    QSizePolicy, QFrame,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFontMetrics
from datetime import datetime
import os
from typing import cast

from app.ui.theme import stabilize_minimum_height
from app.ui.widgets.page_templates import (
    form_field_row,
    page_margins_and_spacing,
    set_drop_zone_active,
    setup_page_header_with_status,
)
from app.ui.theme.tokens import (
    EMPTY_MEAS_FILE,
    SPACING_12,
    SPACING_8,
    DATA_SETUP_CARD_CONTENT_PADDING,
    DATA_SETUP_CARD_SECTION_GAP,
    DATA_SETUP_PRIMARY_CARD_MIN_HEIGHT,
    DATA_SETUP_SECONDARY_CARD_MIN_HEIGHT,
    DATA_SETUP_PATH_ACTION_MIN_WIDTH,
    DATA_SETUP_TABLE_LABEL_WIDTH,
    DATA_SETUP_TABLE_ROW_MIN_HEIGHT,
    PATH_LABEL_ELIDE_MIN_W,
    PATH_LABEL_ELIDE_MARGIN,
    DATA_SETUP_COMPACT_PATH_MIN_WIDTH,
    DATA_SETUP_COMPACT_META_LABEL_WIDTH,
    DATA_SETUP_COMPACT_HINT_LABEL_WIDTH,
    DATA_SETUP_DROP_ZONE_MIN_HEIGHT,
)





class DataUploadPage(QWidget):
    """上傳量測 CSV：僅路徑列與選檔按鈕；不內嵌表格預覽。"""
    meas_uploaded = Signal(str)

    def __init__(self, parent=None, embedded: bool = False) -> None:
        super().__init__(parent)
        self._embedded = embedded
        # embedded 時不再用 Maximum — 讓卡片按內容高度展開，避免表單被壓縮
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.setAcceptDrops(True)
        self._raw_path_text = f"目前載入量測檔：{EMPTY_MEAS_FILE}"
        self.drop_zone: QFrame = cast(QFrame, self)
        root = QtWidgets.QVBoxLayout(self)
        if embedded:
            root.setContentsMargins(0, 0, 0, 0)
            root.setSpacing(SPACING_8)
        else:
            page_margins_and_spacing(root)

        if not self._embedded:
            self.header_lbl, self.status_lamp, self.status_text = setup_page_header_with_status(root, "量測")

        # ── 上傳卡片 ──
        upload_card = QFrame()
        if self._embedded:
            upload_card.setObjectName("")
            upload_card.setFrameShape(QFrame.Shape.NoFrame)
        else:
            upload_card.setObjectName("stepCard")
            upload_card.setMinimumHeight(DATA_SETUP_PRIMARY_CARD_MIN_HEIGHT)
        upload_lay = QtWidgets.QVBoxLayout(upload_card)
        _pad = 0 if self._embedded else DATA_SETUP_CARD_CONTENT_PADDING
        upload_lay.setContentsMargins(_pad, _pad, _pad, _pad)
        upload_lay.setSpacing(DATA_SETUP_CARD_SECTION_GAP)

        if not self._embedded:
            step3_title = QLabel("量測檔")
            step3_title.setProperty("class", "stepTitle")
            step3_title.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            upload_lay.addWidget(step3_title)

        # 量測檔路徑
        self.lbl_path = QLabel("尚未選擇")
        self.lbl_path.setProperty("class", "caption")
        # Path text is always shown in single-line elide mode.
        self.lbl_path.setWordWrap(False)
        self.lbl_path.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_path.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.lbl_path.setToolTip(self._raw_path_text)
        self.btn_browse = QPushButton("選量測檔")
        self.btn_browse.setProperty("class", "secondary")
        self.btn_browse.setObjectName("uploadMeasBtn")
        self.btn_browse.setMinimumWidth(DATA_SETUP_PATH_ACTION_MIN_WIDTH)
        self.btn_browse.setToolTip("選擇量測 CSV")
        self.btn_browse.setAccessibleName("選量測檔")
        self.btn_browse.clicked.connect(self._open_file_dialog)

        # ── 橫向高密度排版：將檔案選取與統計放在一行 ──
        if self._embedded:
            # Row 1: Measurement File Selection & Metadata (High density)
            row_file = QtWidgets.QHBoxLayout()
            row_file.setContentsMargins(0, 0, 0, 0)
            row_file.setSpacing(SPACING_12)

            self.btn_browse = QPushButton("選量測檔")
            self.btn_browse.setProperty("class", "secondary")
            self.btn_browse.setMinimumWidth(DATA_SETUP_PATH_ACTION_MIN_WIDTH)
            self.btn_browse.setToolTip("選擇 SPI 量測 CSV")
            self.btn_browse.setAccessibleName("選量測檔")
            self.btn_browse.clicked.connect(self._open_file_dialog)
            row_file.addWidget(self.btn_browse, 0)

            self.lbl_meta = QLabel("列數：--")
            self.lbl_meta.setProperty("class", "caption")
            self.lbl_meta.setFixedWidth(DATA_SETUP_COMPACT_META_LABEL_WIDTH)
            row_file.addWidget(self.lbl_meta, 0)

            self.drop_zone_hint = QLabel("可拖放 CSV")
            self.drop_zone_hint.setProperty("class", "caption")
            self.drop_zone_hint.setFixedWidth(DATA_SETUP_COMPACT_HINT_LABEL_WIDTH)
            row_file.addWidget(self.drop_zone_hint, 0)

            self.lbl_path = QLabel("尚未選擇")
            self.lbl_path.setProperty("class", "caption")
            self.lbl_path.setWordWrap(False)
            self.lbl_path.setMinimumWidth(DATA_SETUP_COMPACT_PATH_MIN_WIDTH)
            row_file.addWidget(self.lbl_path, 1)

            row_file.addStretch(1)
            root.addLayout(row_file)

            self.drop_zone = cast(QFrame, self)  # Make parent handle it
            
        else:
            upload_lay.addLayout(
                form_field_row(
                    "量測檔路徑 (*.csv)",
                    self.lbl_path,
                    self.btn_browse,
                    label_min_width=DATA_SETUP_TABLE_LABEL_WIDTH,
                    row_min_height=DATA_SETUP_TABLE_ROW_MIN_HEIGHT,
                    action_min_width=DATA_SETUP_PATH_ACTION_MIN_WIDTH,
                )
            )
            
            self.lbl_meta = QLabel("檔名：-- | 列數：-- | 時間：--")
            self.lbl_meta.setProperty("class", "caption")
            upload_lay.addWidget(self.lbl_meta)
            

        if not self._embedded:
            # 拖放提示區：明確標示可拖入 CSV
            self.drop_zone = QFrame()
            self.drop_zone.setProperty("class", "dropZone")
            self.drop_zone.setMinimumHeight(DATA_SETUP_DROP_ZONE_MIN_HEIGHT)
            drop_zone_lay = QtWidgets.QVBoxLayout(self.drop_zone)
            drop_zone_lay.setContentsMargins(SPACING_8, SPACING_8, SPACING_8, SPACING_8)
            drop_zone_lay.setSpacing(0)
            self.drop_zone_hint = QLabel("將量測 CSV 拖放至此，或按「選量測檔」")
            self.drop_zone_hint.setProperty("class", "caption")
            self.drop_zone_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.drop_zone_hint.setWordWrap(True)
            drop_zone_lay.addWidget(self.drop_zone_hint)
            upload_lay.addWidget(self.drop_zone)

        # 此卡片僅一個可聚焦按鈕，預設 Tab 順序即可。勿使用 setTabOrder(btn, btn)：
        # Qt 6 會同時印出 "Could not parse application stylesheet"（誤報）與無效順序。

        if not self._embedded:
            stabilize_minimum_height(upload_card, DATA_SETUP_PRIMARY_CARD_MIN_HEIGHT)
        root.addWidget(upload_card)

        # ── 上傳狀態卡片 ──
        if not self._embedded:
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
        if not self._embedded:
            root.addStretch(1)

    def _open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "選擇 SPI 量測 CSV", "", "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            self._accept_measurement_file(file_path)

    def resizeEvent(self, event) -> None:
        """Adjust layout on widget resize."""
        super().resizeEvent(event)
        self._refresh_elided_path()

    def set_path_text(self, text: str) -> None:
        """Display the given file path in the path label widget."""
        self._raw_path_text = text or ""
        self.lbl_path.setToolTip(self._raw_path_text)
        self._refresh_elided_path()

    def set_metadata(self, filename: str | None, row_count: int | None, timestamp: str | None) -> None:
        """Update filename/row-count/timestamp status text for the loaded CSV."""
        name_txt = filename or "--"
        row_txt = str(row_count) if row_count is not None and row_count >= 0 else "--"
        time_txt = timestamp or "--"
        self.lbl_meta.setText(f"列數：{row_txt}")
        if filename:
            self.drop_zone_hint.setText(f"已載入：{filename}")
            self.lbl_path.setToolTip(f"檔名：{name_txt} | 時間：{time_txt}")
        else:
            self.drop_zone_hint.setText("可拖放 CSV" if self._embedded else "將量測 CSV 拖放至此，或按「選量測檔」")

    def reset_upload_state(self) -> None:
        """Reset path and metadata labels when product context changes."""
        self._raw_path_text = ""
        self._refresh_elided_path()
        self.set_metadata(None, None, None)
        self.drop_zone_hint.setText("可拖放 CSV" if self._embedded else "將量測 CSV 拖放至此，或按「選量測檔」")

    def _accept_measurement_file(self, file_path: str) -> None:
        self._set_drop_zone_active(False)
        self.set_path_text(f"目前載入量測檔：{file_path}")
        self.set_metadata(
            os.path.basename(file_path),
            None,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        self.meas_uploaded.emit(file_path)

    def _refresh_elided_path(self) -> None:
        raw = self._raw_path_text or ""
        if not raw:
            self.lbl_path.setText("尚未選擇")
            return
        body = raw
        if "：" in raw:
            _, body = raw.split("：", 1)
            body = body.strip()
        metrics = QFontMetrics(self.lbl_path.font())
        usable = max(PATH_LABEL_ELIDE_MIN_W, self.lbl_path.width() - PATH_LABEL_ELIDE_MARGIN)
        self.lbl_path.setText(metrics.elidedText(body, Qt.TextElideMode.ElideMiddle, usable))

    def _set_drop_zone_active(self, active: bool) -> None:
        """Toggle the drop zone highlight state (drag-over feedback)."""
        set_drop_zone_active(self.drop_zone, active)

    def dragEnterEvent(self, event) -> None:
        """Accept drag only for local CSV files and highlight the drop zone."""
        mime = event.mimeData()
        if mime and mime.hasUrls():
            for url in mime.urls():
                if url.isLocalFile() and url.toLocalFile().lower().endswith(".csv"):
                    self._set_drop_zone_active(True)
                    event.acceptProposedAction()
                    return
        self._set_drop_zone_active(False)
        event.ignore()

    def dropEvent(self, event) -> None:
        """Handle a dropped CSV file."""
        mime = event.mimeData()
        if not mime or not mime.hasUrls():
            self._set_drop_zone_active(False)
            event.ignore()
            return
        for url in mime.urls():
            if url.isLocalFile():
                file_path = url.toLocalFile()
                if file_path.lower().endswith(".csv"):
                    self._set_drop_zone_active(False)
                    self._accept_measurement_file(file_path)
                    event.acceptProposedAction()
                    return
        self._set_drop_zone_active(False)
        event.ignore()

    def dragLeaveEvent(self, event) -> None:
        """Reset drop zone highlight when the drag cursor leaves."""
        self._set_drop_zone_active(False)
        super().dragLeaveEvent(event)
