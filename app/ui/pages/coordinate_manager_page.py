"""
座標管理頁：步驟一（依產品載入座標）＋ 座標檔設定（匯入新座標並綁定產品）。
無 stepCard 包裝，以標題與垂直間距分段。

Redesign v2: 垂直表單結構，標籤在上、控件在下，避免窄欄擠壓文字。
"""
from PySide6 import QtWidgets
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QFileDialog, QLineEdit, QComboBox, QFrame,
    QGridLayout, QHBoxLayout,
    QSizePolicy,
)
from PySide6.QtCore import Signal, Qt, QThread, QTimer
from PySide6.QtGui import QFontMetrics, QGuiApplication, QCursor
from app.data.session_store import SessionStore
from datetime import datetime
import os
from typing import Optional, cast

from app.ui.theme import show_dark_warning, show_dark_information, stabilize_minimum_height
from app.ui.widgets.page_templates import (
    form_field_row,
    page_margins_and_spacing,
    set_drop_zone_active,
    setup_page_header_with_status,
)
from app.ui.theme.tokens import (
    EMPTY_COORD_SET, SPACING_12, SPACING_8, DATA_SETUP_CARD_CONTENT_PADDING, DATA_SETUP_CARD_SECTION_GAP,
    DATA_SETUP_PRIMARY_CARD_MIN_HEIGHT, DATA_SETUP_SECONDARY_CARD_MIN_HEIGHT,
    FORM_COMBO_MIN_WIDTH,
    DATA_SETUP_PRODUCT_COMBO_MIN_WIDTH,
    DATA_SETUP_FIELD_MAX_WIDTH,
    DATA_SETUP_PATH_ACTION_MIN_WIDTH,
    DATA_SETUP_TABLE_LABEL_WIDTH,
    DATA_SETUP_TABLE_ROW_MIN_HEIGHT,
    PATH_LABEL_ELIDE_MIN_W,
    PATH_LABEL_ELIDE_MARGIN,
    DATA_SETUP_COMPACT_PATH_MIN_WIDTH,
    DATA_SETUP_COMPACT_HINT_LABEL_WIDTH,
    DATA_SETUP_COMPACT_META_LABEL_WIDTH,
)
from app.data.coordinate_registry import (
    list_registered,
    register as registry_register,
    get_path_by_product_name,
)
from app.data.mapping.schema_mapper import SchemaMapper
import pandas as pd


class CoordValidationWorker(QThread):
    """Asynchronously validates a coordinate file snippet (first 1000 rows)."""
    finished = Signal(str, bool, list, int)  # file_path, is_valid, missing_required, total_rows

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path

    def run(self) -> None:
        """Execute the background task."""
        try:
            if self.isInterruptionRequested():
                return
            # Audit Item 115: Background IO for initial validation
            df = pd.read_csv(self.file_path, nrows=1000, encoding="utf-8")
            if self.isInterruptionRequested():
                return
            mapped_df, _, _ = SchemaMapper.map_columns(df, SchemaMapper.COORDINATE_ALIASES)
            is_valid, missing_required = SchemaMapper.validate_coordinate_schema(mapped_df)
            total_rows = len(df)
            if self.isInterruptionRequested():
                return
            self.finished.emit(self.file_path, is_valid, missing_required or [], total_rows)
        except (
            pd.errors.EmptyDataError,
            pd.errors.ParserError,
            UnicodeDecodeError,
            OSError,
            ValueError,
            TypeError,
            KeyError,
        ):
            self.finished.emit(self.file_path, False, ["檔案讀取錯誤"], 0)


class CoordinateManagerPage(QWidget):
    """
    UI Page providing mechanisms to upload and verify Map Coordinates.
    Supports binding coord file to product name so it can be auto-loaded by product later.
    """
    coord_uploaded = Signal(str)
    product_name_selected = Signal(str)
    registry_changed = Signal()

    def __init__(self, parent=None, embedded: bool = False) -> None:
        super().__init__(parent)
        self._embedded = embedded
        self._use_external_product = False
        # embedded 時不再用 Maximum — 讓卡片按內容高度展開，避免表單被壓縮
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.setAcceptDrops(True)
        self.current_coord_path = ""  # 由 MainWindow 在載入完成時設定
        self._raw_path_text = f"目前載入座標檔：{EMPTY_COORD_SET}"
        self.drop_zone: QFrame = cast(QFrame, self)
        root = QtWidgets.QVBoxLayout(self)
        if embedded:
            root.setContentsMargins(0, 0, 0, 0)
            root.setSpacing(SPACING_8)
        else:
            page_margins_and_spacing(root)
        _pad = DATA_SETUP_CARD_CONTENT_PADDING

        if not self._embedded:
            self.header_lbl, self.status_lamp, self.status_text = setup_page_header_with_status(root, "座標")

        # ── 橫向高密度排版：將所有檔案資訊與統計放在一行 ──
        if self._embedded:
            # Row 1: Coordinate File Selection & Metadata (High density)
            row_file = QHBoxLayout()
            row_file.setContentsMargins(0, 0, 0, 0)
            row_file.setSpacing(SPACING_12)

            self.btn_browse = QPushButton("選座標檔")
            self.btn_browse.setProperty("class", "secondary")
            self.btn_browse.setMinimumWidth(DATA_SETUP_PATH_ACTION_MIN_WIDTH)
            row_file.addWidget(self.btn_browse, 0)
            self.btn_browse.setToolTip("選擇座標 CSV")
            self.btn_browse.setAccessibleName("選座標檔")

            # Metadata info
            self.lbl_meta = QLabel("列數：--")
            self.lbl_meta.setProperty("class", "caption")
            self.lbl_meta.setFixedWidth(DATA_SETUP_COMPACT_META_LABEL_WIDTH)
            row_file.addWidget(self.lbl_meta, 0)

            # Inline drop hint
            self.drop_zone_hint = QLabel("可拖放 CSV")
            self.drop_zone_hint.setProperty("class", "caption")
            self.drop_zone_hint.setFixedWidth(DATA_SETUP_COMPACT_HINT_LABEL_WIDTH)
            row_file.addWidget(self.drop_zone_hint, 0)

            self.lbl_path = QLabel(EMPTY_COORD_SET)
            self.lbl_path.setProperty("class", "caption")
            self.lbl_path.setWordWrap(False)
            self.lbl_path.setMinimumWidth(DATA_SETUP_COMPACT_PATH_MIN_WIDTH)
            row_file.addWidget(self.lbl_path, 1)

            row_file.addStretch(1)
            root.addLayout(row_file)
            
            # Row 2: Binding section (Accordion header)
            # Row 2: Product selection (for when not using external product mode)
            self._product_row_container = QtWidgets.QWidget()
            row_prod = QHBoxLayout(self._product_row_container)
            row_prod.setContentsMargins(0, 0, 0, 0)
            row_prod.setSpacing(SPACING_12)
            row_prod.addWidget(QLabel("產品"), 0)
            self.product_combo = QComboBox()
            self.product_combo.setMinimumWidth(DATA_SETUP_PRODUCT_COMBO_MIN_WIDTH)
            row_prod.addWidget(self.product_combo, 0)
            self.btn_load_by_product = QPushButton("載入")
            self.btn_load_by_product.setProperty("class", "secondary")
            row_prod.addWidget(self.btn_load_by_product, 0)
            row_prod.addStretch(1)
            root.addWidget(self._product_row_container)

            # Hook up slots
            self.btn_browse.clicked.connect(self._open_file_dialog)
            self.btn_load_by_product.clicked.connect(self._on_load_by_product_clicked)
            self.drop_zone = cast(QFrame, self)
            content_lay = root
        else:
            # Standalone page preserves multi-card large layout
            # ── 步驟一：選擇產品 ──────────────────────────────────
            step1_card = QFrame()
            self._product_row_container = step1_card
            step1_card.setObjectName("stepCard")
            step1_card.setProperty("class", "accentBlue")
            step1_card.setMinimumHeight(DATA_SETUP_PRIMARY_CARD_MIN_HEIGHT)
            step1_lay = QtWidgets.QVBoxLayout(step1_card)
            step1_lay.setContentsMargins(_pad, _pad, _pad, _pad)
            step1_lay.setSpacing(DATA_SETUP_CARD_SECTION_GAP)

            step1_title = QLabel("選擇產品")
            step1_title.setProperty("class", "stepTitle")
            step1_lay.addWidget(step1_title)

            self.product_combo = QComboBox()
            self.product_combo.setMinimumWidth(FORM_COMBO_MIN_WIDTH)
            self.product_combo.setMaximumWidth(DATA_SETUP_FIELD_MAX_WIDTH)
            self.btn_load_by_product = QPushButton("載入")
            self.btn_load_by_product.setProperty("class", "secondary")
            self.btn_load_by_product.clicked.connect(self._on_load_by_product_clicked)
            
            step1_lay.addLayout(
                form_field_row(
                    "產品", self.product_combo, self.btn_load_by_product,
                    label_min_width=DATA_SETUP_TABLE_LABEL_WIDTH,
                    row_min_height=DATA_SETUP_TABLE_ROW_MIN_HEIGHT,
                    action_min_width=DATA_SETUP_PATH_ACTION_MIN_WIDTH,
                )
            )
            stabilize_minimum_height(step1_card, DATA_SETUP_PRIMARY_CARD_MIN_HEIGHT)
            root.addWidget(step1_card)

            # ── 座標檔設定（ standalone 模式區塊）────────────────────────────
            step2_card = QFrame()
            step2_card.setObjectName("stepCard")
            step2_card.setProperty("class", "accentRed")
            step2_card.setMinimumHeight(DATA_SETUP_SECONDARY_CARD_MIN_HEIGHT)
            step2_lay = QtWidgets.QVBoxLayout(step2_card)
            step2_lay.setContentsMargins(_pad, _pad, _pad, _pad)
            step2_lay.setSpacing(DATA_SETUP_CARD_SECTION_GAP)

            step2_title = QLabel("座標檔設定")
            step2_title.setProperty("class", "stepTitle")
            step2_lay.addWidget(step2_title)

            # 座標檔路徑
            self.lbl_path = QLabel(EMPTY_COORD_SET)
            self.lbl_path.setProperty("class", "caption")
            self.lbl_path.setWordWrap(False)
            self.lbl_path.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.lbl_path.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.btn_browse = QPushButton("選座標檔")
            self.btn_browse.setProperty("class", "secondary")
            self.btn_browse.setMinimumWidth(DATA_SETUP_PATH_ACTION_MIN_WIDTH)
            self.btn_browse.clicked.connect(self._open_file_dialog)

            step2_lay.addLayout(
                form_field_row(
                    "座標檔", self.lbl_path, self.btn_browse,
                    label_min_width=DATA_SETUP_TABLE_LABEL_WIDTH,
                    row_min_height=DATA_SETUP_TABLE_ROW_MIN_HEIGHT,
                    action_min_width=DATA_SETUP_PATH_ACTION_MIN_WIDTH,
                )
            )
            self.lbl_meta = QLabel("檔名：-- | 列數：-- | 時間：--")
            self.lbl_meta.setProperty("class", "caption")
            step2_lay.addWidget(self.lbl_meta)

            # 拖放提示區
            self.drop_zone = QFrame()
            self.drop_zone.setProperty("class", "dropZone")
            drop_zone_lay = QtWidgets.QVBoxLayout(self.drop_zone)
            drop_zone_lay.setContentsMargins(SPACING_8, SPACING_8, SPACING_8, SPACING_8)
            self.drop_zone_hint = QLabel("拖放座標 CSV，或按「選座標檔」")
            self.drop_zone_hint.setProperty("class", "caption")
            self.drop_zone_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            drop_zone_lay.addWidget(self.drop_zone_hint)
            step2_lay.addWidget(self.drop_zone)
            stabilize_minimum_height(step2_card, DATA_SETUP_SECONDARY_CARD_MIN_HEIGHT)
            root.addWidget(step2_card)
            content_lay = step2_lay


        # 綁定座標 → 產品（embedded 模式收合為手風琴，減少視覺噪音）
        if self._embedded:
            self._btn_bind_section = QPushButton("綁定產品")
            self._btn_bind_section.setProperty("class", "accordionHeader")
            self._btn_bind_section.setCheckable(True)
            self._btn_bind_section.setChecked(False)
            self._btn_bind_section.setToolTip("將座標檔綁定到產品")
            content_lay.addWidget(self._btn_bind_section)
        else:
            bind_section_title = QLabel("指定產品")
            bind_section_title.setProperty("class", "sectionTitle")
            bind_section_title.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            content_lay.addWidget(bind_section_title)

        self.bind_section_btn = getattr(self, "_btn_bind_section", None) # Expose for discovery

        self._bind_container = QWidget()
        bind_inner = QtWidgets.QVBoxLayout(self._bind_container)
        bind_inner.setContentsMargins(0, 0, 0, 0)
        bind_inner.setSpacing(SPACING_8)

        # 產品名稱 / 料號 / 儲存
        self.product_name_edit = QLineEdit()
        self.product_name_edit.setPlaceholderText("輸入產品名稱")
        self.product_name_edit.setMinimumWidth(DATA_SETUP_PRODUCT_COMBO_MIN_WIDTH)
        self.product_name_edit.setMaximumWidth(DATA_SETUP_FIELD_MAX_WIDTH)
        self.product_part_no_edit = QLineEdit()
        self.product_part_no_edit.setPlaceholderText("輸入料號（選填）")
        self.product_part_no_edit.setMinimumWidth(DATA_SETUP_PRODUCT_COMBO_MIN_WIDTH)
        self.product_part_no_edit.setMaximumWidth(DATA_SETUP_FIELD_MAX_WIDTH)
        self.btn_register = QPushButton("儲存綁定")
        self.btn_register.setProperty("class", "secondary")
        self.btn_register.setToolTip("儲存座標與產品綁定")
        self.btn_register.setMinimumWidth(DATA_SETUP_PATH_ACTION_MIN_WIDTH)
        self.btn_register.setMaximumWidth(DATA_SETUP_PATH_ACTION_MIN_WIDTH)
        self.btn_register.clicked.connect(self._on_register_clicked)

        if self._embedded:
            # 單行橫排：[名稱 input] [料號 input] [儲存]
            form_area = QtWidgets.QVBoxLayout()
            form_area.setSpacing(SPACING_8)
            form_area.setContentsMargins(0, 0, 0, 0)
            bind_row = QHBoxLayout()
            bind_row.setSpacing(SPACING_8)
            bind_row.setContentsMargins(0, 0, 0, 0)
            bind_row.addWidget(self.product_name_edit, 0) # 0 stretch for left align
            bind_row.addWidget(self.product_part_no_edit, 0)
            bind_row.addWidget(self.btn_register, 0)
            bind_row.addStretch(1) # Pushes items to left
            bind_inner.addLayout(bind_row)
        else:
            # Grid layout for standalone page
            self._bind_grid = QGridLayout()
            self._bind_grid.setContentsMargins(0, 0, 0, 0)
            self._bind_grid.setHorizontalSpacing(SPACING_8)
            self._bind_grid.setVerticalSpacing(SPACING_8)
            self._bind_grid.addWidget(QLabel("產品名稱"), 0, 0)
            self._bind_grid.addWidget(self.product_name_edit, 0, 1)
            self._bind_grid.addWidget(QLabel("料號"), 1, 0)
            self._bind_grid.addWidget(self.product_part_no_edit, 1, 1)
            self._bind_grid.addWidget(self.btn_register, 2, 1)
            bind_inner.addLayout(self._bind_grid)
        if self._embedded:
            self._bind_container.setVisible(False)
            self._btn_bind_section.toggled.connect(self._bind_container.setVisible)
        content_lay.addWidget(self._bind_container)

        if not embedded:
            root.addStretch(1)
        
        self._store = SessionStore()
        self.refresh_registered_list()
        self._validation_worker: Optional[CoordValidationWorker] = None
        # Monotonic counter so rapid re-validation does not apply a stale worker result.
        self._coord_validation_seq: int = 0

        # Audit Item 117: Set proper tab order for form accessibility
        self.setTabOrder(self.product_combo, self.btn_load_by_product)
        self.setTabOrder(self.btn_load_by_product, self.btn_browse)
        self.setTabOrder(self.btn_browse, self.product_name_edit)
        self.setTabOrder(self.product_name_edit, self.product_part_no_edit)
        self.setTabOrder(self.product_part_no_edit, self.btn_register)
        self.setTabOrder(self.btn_browse, self.product_name_edit)
        self.setTabOrder(self.product_name_edit, self.product_part_no_edit)
        self.setTabOrder(self.product_part_no_edit, self.btn_register)

    # ── public API (unchanged) ────────────────────────────────

    def set_current_coord_path(self, path: str) -> None:
        """由 MainWindow 在座標載入完成時呼叫，供「儲存至註冊表」使用。"""
        self.current_coord_path = path or ""

    def set_external_product_mode(self, enabled: bool) -> None:
        """當 DataSetupPage 提供全域產品選擇時，隱藏此區重複選擇列。"""
        self._use_external_product = bool(enabled)
        self._product_row_container.setVisible(not self._use_external_product)

    def set_selected_product(self, product_name: str) -> None:
        """由上層指定目前產品（同步內部產品下拉）。"""
        if not product_name:
            self.product_combo.setCurrentIndex(0)
            return
        idx = self.product_combo.findData(product_name)
        if idx >= 0:
            self.product_combo.setCurrentIndex(idx)

    def selected_product(self) -> str:
        """Return the currently selected product key from the dropdown."""
        return str(self.product_combo.currentData() or "")

    def show_registration(self, show: bool = True) -> None:
        """Toggle the visibility of the product-coordinate binding section and focus input."""
        if hasattr(self, "_btn_bind_section"):
            self._btn_bind_section.setChecked(show)
        self._bind_container.setVisible(show)
        if show:
            self.product_name_edit.setFocus()
            # Ensure it's scrolled into view if needed by host

    def reset_upload_state(self) -> None:
        """產品切換時清空座標檔狀態，避免跨產品誤用。"""
        self.current_coord_path = ""
        self.set_path_text(f"目前載入座標檔：{EMPTY_COORD_SET}")
        self.set_metadata(None, None, None)

    def set_path_text(self, text: str) -> None:
        """Display the given file path in the path label widget."""
        self._raw_path_text = text or ""
        self.lbl_path.setToolTip(self._raw_path_text)
        self._refresh_elided_path()

    def set_metadata(self, filename: str | None, row_count: int | None, timestamp: str | None) -> None:
        """Update filename/row-count/timestamp metadata shown under the upload card."""
        name_txt = filename or "--"
        row_txt = str(row_count) if row_count is not None and row_count >= 0 else "--"
        time_txt = timestamp or "--"
        self.lbl_meta.setText(f"列數：{row_txt}")
        if filename:
            self.lbl_path.setToolTip(f"檔名：{name_txt} | 時間：{time_txt}")

    def refresh_registered_list(self) -> None:
        """重新從註冊表載入清單，更新下拉與列表。"""
        entries = list_registered()
        self.product_combo.clear()
        self.product_combo.addItem("請選擇產品…", None)
        for e in entries:
            name = (e.get("product_name") or "").strip()
            if name:
                self.product_combo.addItem(name, name)

    # ── private slots (unchanged) ─────────────────────────────


    def _on_register_clicked(self) -> None:
        name = self.product_name_edit.text().strip()
        if not name:
            show_dark_warning(self, "無法儲存", "請輸入產品名稱。")
            return
        if not self.current_coord_path:
            show_dark_warning(
                self, "無法儲存",
                "請先載入座標檔，再儲存。"
            )
            return
        part_no = self.product_part_no_edit.text().strip()
        row_count = getattr(self, "current_coord_row_count", None)
        if registry_register(name, self.current_coord_path, part_no, row_count=row_count):
            self.refresh_registered_list()
            self.registry_changed.emit()
            show_dark_information(self, "已儲存", f"已將座標檔綁定至「{name}」。")
        else:
            show_dark_warning(self, "儲存失敗", "寫入註冊表失敗，請檢查權限。")

    def _on_load_by_product_clicked(self) -> None:
        self.load_selected_product_coord()

    def load_selected_product_coord(self) -> bool:
        """Emit the registered coordinate file path for the selected product."""
        name = self.product_combo.currentData()
        if not name:
            show_dark_warning(self, "請選擇產品", "請先選擇已註冊產品。")
            return False
        path = get_path_by_product_name(name)
        if not path:
            show_dark_warning(self, "無法載入", f"找不到產品「{name}」的座標檔。")
            return False
        self._set_lamp("loading", "載入中…")
        self.product_name_selected.emit(name)
        self.coord_uploaded.emit(path)
        return True


    def _open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "選擇 Gerber/CAD 匯出件 (*.csv)", "", "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            self._start_validation(file_path)

    def _start_validation(self, file_path: str) -> None:
        self.current_coord_path = file_path
        self._set_drop_zone_active(False)
        self.set_path_text(f"目前載入座標檔：{file_path}（驗證中…）")
        self.set_metadata(
            os.path.basename(file_path),
            None,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        self._set_lamp("loading", "驗證中…")

        # Audit Item 115: Move to background thread
        self._coord_validation_seq += 1
        seq = self._coord_validation_seq
        if self._validation_worker and self._validation_worker.isRunning():
            # Pop wait cursor from the previous validation before stacking another (Pass 131).
            QGuiApplication.restoreOverrideCursor()
            self._validation_worker.requestInterruption()
            # Prefer cooperative stop; avoid terminate() unless stuck (unsafe for Qt state).
            if not self._validation_worker.wait(5000):
                self._validation_worker.terminate()
                self._validation_worker.wait(1000)

        self._validation_worker = CoordValidationWorker(file_path, self)

        def _on_validation_complete(
            fp: str, iv: bool, mr: list, tr: int, *, _seq: int = seq
        ) -> None:
            if _seq != self._coord_validation_seq:
                return
            QGuiApplication.restoreOverrideCursor()
            self._on_validation_finished(fp, iv, mr, tr)

        self._validation_worker.finished.connect(_on_validation_complete)
        _vw = self._validation_worker
        self._validation_worker.finished.connect(
            lambda w=_vw: setattr(self, "_validation_worker", None)
            if self._validation_worker is w
            else None
        )
        self._validation_worker.finished.connect(self._validation_worker.deleteLater)
        # MANDATORY: WaitCursor while validation runs (paired with restore in _on_validation_complete).
        QGuiApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
        self._validation_worker.start()

    def _on_validation_finished(self, file_path: str, is_valid: bool, missing_required: list, total_rows: int):
        self.current_coord_row_count = total_rows
        if is_valid:
            self.set_path_text(
                f"目前載入座標檔：{file_path}（有效，{total_rows} 列）"
            )
            self._set_lamp("ok", f"座標有效（{total_rows} 列）")
            # Embedded Data Setup: auto-expand binding section after successful validation.
            if self._embedded and hasattr(self, "_btn_bind_section"):
                self._btn_bind_section.setChecked(True)
                # Defer focus until bind container is visible (toggled → setVisible).
                QTimer.singleShot(0, self._focus_embedded_product_name_edit)
        else:
            missing_txt = ", ".join(missing_required) if missing_required else "未知"
            self.set_path_text(f"目前載入座標檔：{file_path}（缺少欄位：{missing_txt}）")
            self._set_lamp("error", f"缺少欄位：{missing_txt}")
        self.set_metadata(
            os.path.basename(file_path),
            total_rows if total_rows > 0 else None,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        self.coord_uploaded.emit(file_path)

    def _focus_embedded_product_name_edit(self) -> None:
        """Move keyboard focus to product name after bind section is shown (embedded only)."""
        if not self._embedded:
            return
        self.product_name_edit.setFocus(Qt.FocusReason.OtherFocusReason)

    def dragEnterEvent(self, event) -> None:
        """Accept drag only for local CSV files and highlight drop zone."""
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
        """Handle dropped CSV file and trigger coordinate validation."""
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
                    self._start_validation(file_path)
                    event.acceptProposedAction()
                    return
        self._set_drop_zone_active(False)
        event.ignore()

    def dragLeaveEvent(self, event) -> None:
        """Reset drop-zone highlight when drag leaves the coordinate card."""
        self._set_drop_zone_active(False)
        super().dragLeaveEvent(event)

    def resizeEvent(self, event) -> None:
        """Adjust layout on widget resize."""
        super().resizeEvent(event)
        self._refresh_elided_path()

    def _set_lamp(self, state_name: str, message: str) -> None:
        """Update the status indicator lamp and label if they exist (standalone mode)."""
        if not hasattr(self, "status_lamp") or not self.status_lamp:
            return
        state_map = {"ok": "success", "error": "warning", "loading": "loading", "idle": "idle"}
        state = state_map.get(state_name, "idle")
        self.status_lamp.setProperty("state", state)
        self.status_lamp.style().unpolish(self.status_lamp)
        self.status_lamp.style().polish(self.status_lamp)
        if hasattr(self, "status_text") and self.status_text:
            self.status_text.setText(message)

    def _set_drop_zone_active(self, active: bool) -> None:
        """Apply visual feedback to the drop zone when dragging files over it."""
        if not hasattr(self, "drop_zone") or not self.drop_zone:
            return
        set_drop_zone_active(self.drop_zone, active)

    def _refresh_elided_path(self) -> None:
        raw = self._raw_path_text or ""
        if not raw:
            self.lbl_path.setText("")
            return
        # 只顯示路徑部分（去掉 prefix）
        body = raw
        if "：" in raw:
            _, body = raw.split("：", 1)
            body = body.strip()
        metrics = QFontMetrics(self.lbl_path.font())
        usable = max(PATH_LABEL_ELIDE_MIN_W, self.lbl_path.width() - PATH_LABEL_ELIDE_MARGIN)
        self.lbl_path.setText(metrics.elidedText(body, Qt.TextElideMode.ElideMiddle, usable))
