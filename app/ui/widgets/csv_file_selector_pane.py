"""
CSV 選檔區塊：座標頁與量測頁共用的「選檔按鈕 + 路徑 + 列數 + 拖放提示」。

- embedded：單行高密度排版（按鈕 / 列數 / 拖放提示 / 路徑），無外框。
- standalone：本身即 stepCard（標題 + form_field_row + 列數 + dropZone）；
  `content_layout()` 供宿主頁面在卡片內追加區段。

選檔（對話框或拖放）一律經 `file_selected` 發出，由宿主頁面決定後續動作。
"""
from __future__ import annotations

from PySide6 import QtWidgets
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from app.ui.theme.tokens import (
    DATA_SETUP_CARD_CONTENT_PADDING,
    DATA_SETUP_CARD_SECTION_GAP,
    DATA_SETUP_COMPACT_HINT_LABEL_WIDTH,
    DATA_SETUP_COMPACT_META_LABEL_WIDTH,
    DATA_SETUP_COMPACT_PATH_MIN_WIDTH,
    DATA_SETUP_DROP_ZONE_MIN_HEIGHT,
    DATA_SETUP_PATH_ACTION_MIN_WIDTH,
    DATA_SETUP_TABLE_LABEL_WIDTH,
    DATA_SETUP_TABLE_ROW_MIN_HEIGHT,
    EMPTY_CSV_PATH_TEXT,
    PATH_LABEL_ELIDE_MARGIN,
    PATH_LABEL_ELIDE_MIN_W,
    SPACING_8,
    SPACING_12,
)
from app.ui.widgets.page_templates import (
    CsvDropZoneMixin,
    form_field_row,
    set_drop_zone_active,
)

_EMBEDDED_DROP_HINT = "可拖放 CSV"


class CsvFileSelectorPane(CsvDropZoneMixin, QFrame):
    """Browse button, elided path label, row-count meta and drop hint for one CSV input."""

    file_selected = Signal(str)

    def __init__(
        self,
        *,
        embedded: bool,
        browse_text: str,
        browse_tooltip: str,
        dialog_title: str,
        field_label: str,
        card_title: str,
        drop_hint_text: str,
        card_min_height: int,
        card_accent: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._embedded = embedded
        self._dialog_title = dialog_title
        self._default_hint = _EMBEDDED_DROP_HINT if embedded else drop_hint_text
        self._raw_path_text = ""
        self._hint_text = self._default_hint
        self.setAcceptDrops(True)

        self.btn_browse = QPushButton(browse_text)
        self.btn_browse.setProperty("class", "secondary")
        self.btn_browse.setMinimumWidth(DATA_SETUP_PATH_ACTION_MIN_WIDTH)
        self.btn_browse.setToolTip(browse_tooltip)
        self.btn_browse.setAccessibleName(browse_text)
        self.btn_browse.clicked.connect(self._open_file_dialog)

        self.lbl_path = QLabel(EMPTY_CSV_PATH_TEXT)
        self.lbl_path.setProperty("class", "caption")
        # Path text is always shown in single-line elide mode.
        self.lbl_path.setWordWrap(False)

        self.lbl_meta = QLabel("列數：--")
        self.lbl_meta.setProperty("class", "caption")

        self.drop_zone_hint = QLabel(self._default_hint)
        self.drop_zone_hint.setProperty("class", "caption")

        lay = QtWidgets.QVBoxLayout(self)
        self._content_layout = lay
        if embedded:
            self.setObjectName("")
            self.setFrameShape(QFrame.Shape.NoFrame)
            # Single compact row: never absorb the host region's spare height.
            self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(SPACING_8)
            row = QtWidgets.QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(SPACING_12)
            row.addWidget(self.btn_browse, 0)
            self.lbl_meta.setFixedWidth(DATA_SETUP_COMPACT_META_LABEL_WIDTH)
            row.addWidget(self.lbl_meta, 0)
            self.drop_zone_hint.setFixedWidth(DATA_SETUP_COMPACT_HINT_LABEL_WIDTH)
            row.addWidget(self.drop_zone_hint, 0)
            self.lbl_path.setMinimumWidth(DATA_SETUP_COMPACT_PATH_MIN_WIDTH)
            row.addWidget(self.lbl_path, 1)
            row.addStretch(1)
            lay.addLayout(row)
            # Compact row has no dedicated drop frame; the pane carries the state.
            self.drop_zone: QFrame = self
        else:
            self.setObjectName("stepCard")
            if card_accent:
                self.setProperty("class", card_accent)
            self.setMinimumHeight(card_min_height)
            pad = DATA_SETUP_CARD_CONTENT_PADDING
            lay.setContentsMargins(pad, pad, pad, pad)
            lay.setSpacing(DATA_SETUP_CARD_SECTION_GAP)

            title = QLabel(card_title)
            title.setProperty("class", "stepTitle")
            title.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            lay.addWidget(title)

            self.lbl_path.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.lbl_path.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            lay.addLayout(
                form_field_row(
                    field_label,
                    self.lbl_path,
                    self.btn_browse,
                    label_min_width=DATA_SETUP_TABLE_LABEL_WIDTH,
                    row_min_height=DATA_SETUP_TABLE_ROW_MIN_HEIGHT,
                    action_min_width=DATA_SETUP_PATH_ACTION_MIN_WIDTH,
                )
            )
            lay.addWidget(self.lbl_meta)

            self.drop_zone = QFrame()
            self.drop_zone.setProperty("class", "dropZone")
            self.drop_zone.setMinimumHeight(DATA_SETUP_DROP_ZONE_MIN_HEIGHT)
            drop_lay = QtWidgets.QVBoxLayout(self.drop_zone)
            drop_lay.setContentsMargins(SPACING_8, SPACING_8, SPACING_8, SPACING_8)
            drop_lay.setSpacing(0)
            self.drop_zone_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.drop_zone_hint.setWordWrap(True)
            drop_lay.addWidget(self.drop_zone_hint)
            lay.addWidget(self.drop_zone)
        self._refresh_elided_path()

    def content_layout(self) -> QtWidgets.QVBoxLayout:
        """Return the pane layout so a host can append sections inside the card."""
        return self._content_layout

    def set_path_text(self, text: str) -> None:
        """Display `text` (optionally `前綴：路徑`) in the elided path label."""
        self._raw_path_text = text or ""
        self.lbl_path.setToolTip(self._raw_path_text)
        self._refresh_elided_path()

    def set_metadata(self, filename: str | None, row_count: int | None, timestamp: str | None) -> None:
        """Update row-count text, the drop hint and the path tooltip for the loaded CSV."""
        row_txt = str(row_count) if row_count is not None and row_count >= 0 else "--"
        self.lbl_meta.setText(f"列數：{row_txt}")
        if filename:
            self._set_hint_text(f"已載入：{filename}")
            self.lbl_path.setToolTip(f"檔名：{filename} | 時間：{timestamp or '--'}")
        else:
            self._set_hint_text(self._default_hint)

    def reset(self) -> None:
        """Clear path, metadata and hint back to the empty state."""
        self.set_path_text("")
        self.set_metadata(None, None, None)

    def set_drop_zone_active(self, active: bool) -> None:
        """Toggle the shared drag-over highlight on the drop zone."""
        set_drop_zone_active(self.drop_zone, active)

    def resizeEvent(self, event) -> None:
        """Re-elide path/hint text after the pane width changes."""
        super().resizeEvent(event)
        self._refresh_elided_path()
        self._set_hint_text(self._hint_text)

    # ── CsvDropZoneMixin hooks ────────────────────────────────

    def _set_drop_zone_active(self, active: bool) -> None:
        self.set_drop_zone_active(active)

    def _on_csv_dropped(self, file_path: str) -> None:
        self.file_selected.emit(file_path)

    # ── internals ─────────────────────────────────────────────

    def _open_file_dialog(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, self._dialog_title, "", "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            self.file_selected.emit(file_path)

    def _set_hint_text(self, text: str) -> None:
        self._hint_text = text
        self.drop_zone_hint.setToolTip("" if text == self._default_hint else text)
        if not self._embedded:
            self.drop_zone_hint.setText(text)  # standalone hint word-wraps
            return
        # Embedded hint has a fixed width: elide long file names, full text stays in tooltip.
        metrics = QFontMetrics(self.drop_zone_hint.font())
        usable = max(PATH_LABEL_ELIDE_MIN_W, self.drop_zone_hint.width() - PATH_LABEL_ELIDE_MARGIN)
        self.drop_zone_hint.setText(metrics.elidedText(text, Qt.TextElideMode.ElideMiddle, usable))

    def _refresh_elided_path(self) -> None:
        raw = self._raw_path_text
        if not raw:
            self.lbl_path.setText(EMPTY_CSV_PATH_TEXT)
            return
        # 只顯示路徑部分（去掉「目前載入…檔：」前綴）
        body = raw.split("：", 1)[1].strip() if "：" in raw else raw
        metrics = QFontMetrics(self.lbl_path.font())
        usable = max(PATH_LABEL_ELIDE_MIN_W, self.lbl_path.width() - PATH_LABEL_ELIDE_MARGIN)
        self.lbl_path.setText(metrics.elidedText(body, Qt.TextElideMode.ElideMiddle, usable))
