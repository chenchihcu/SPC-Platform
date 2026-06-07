"""
產品鋼板規格編輯器：鋼板類型、厚度、階梯時精密 RefDes 勾選。
RefDes 清單來自 SessionStore.coord_df；需先依產品名稱載入座標。

無 stepCard 包裝，以垂直間距分段。

Redesign v2: 垂直表單結構，標籤在上、控件在下，避免窄欄壓縮。
"""
from __future__ import annotations
import typing

from PySide6 import QtWidgets
from PySide6.QtWidgets import (
    QWidget, QLineEdit,
    QComboBox, QPushButton, QLabel, QCheckBox, QFrame, QSizePolicy,
    QScrollArea, QBoxLayout,
)
from PySide6.QtCore import Signal, Qt

from app.ui.theme import stabilize_minimum_height
from app.ui.widgets.page_templates import form_field_row
from app.ui.theme.tokens import (
    SPACING_16,
    SPACING_12,
    SPACING_8,
    SPACING_4,
    DATA_SETUP_CARD_CONTENT_PADDING,
    DATA_SETUP_CARD_SECTION_GAP,
    DATA_SETUP_PRIMARY_CARD_MIN_HEIGHT,
    FORM_COMBO_MIN_WIDTH,
    DATA_SETUP_FIELD_MAX_WIDTH,
    DATA_SETUP_NUMERIC_FIELD_MAX_WIDTH,
    DATA_SETUP_PATH_ACTION_MIN_WIDTH,
    DATA_SETUP_TABLE_LABEL_WIDTH,
    DATA_SETUP_TABLE_ROW_MIN_HEIGHT,
    STENCIL_NUMERIC_MIN_WIDTH,
    STENCIL_NUMERIC_MAX_WIDTH,
    STENCIL_ACTION_BUTTON_WIDTH,
    STENCIL_LABEL_MIN_WIDTH,
    REFDES_SCROLL_COMPACT_MAX_H,
)
from app.data.coordinate_registry import list_registered
from app.data.product_spec_registry import (
    get as get_product_spec,
    save as save_product_spec,
    STENCIL_NORMAL,
    STENCIL_STEPPED,
)
from app.data.stencil_assignment_registry import (
    list_precision_refdes,
    save_assignments,
)





class StencilSpecEditor(QWidget):
    """產品鋼板規格：類型、厚度、階梯時精密套用元件勾選。"""
    spec_saved = Signal(str)  # product_name
    manage_requested = Signal()
    thickness_validity_changed = Signal(bool)
    THICKNESS_MIN_MM = 0.05
    THICKNESS_MAX_MM = 0.50

    def __init__(self, parent=None, embedded: bool = False) -> None:
        super().__init__(parent)
        self._embedded = embedded
        self._use_external_product = False
        # embedded 時不再用 Maximum — 讓卡片按內容高度展開，避免表單被壓縮
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(SPACING_8 if embedded else SPACING_16)

        main_card = QFrame()
        if self._embedded:
            # Embedded in Data Setup table: no card chrome.
            main_card.setObjectName("")
            main_card.setFrameShape(QFrame.Shape.NoFrame)
        else:
            main_card.setObjectName("stepCard")
            main_card.setMinimumHeight(DATA_SETUP_PRIMARY_CARD_MIN_HEIGHT)
        card_lay = QtWidgets.QVBoxLayout(main_card)
        _pad = 0 if self._embedded else DATA_SETUP_CARD_CONTENT_PADDING
        card_lay.setContentsMargins(_pad, _pad, _pad, _pad)
        card_lay.setSpacing(DATA_SETUP_CARD_SECTION_GAP)

        # ── 標題 ──
        if not self._embedded:
            title = QLabel("鋼板規格")
            title.setProperty("class", "stepTitle")
            title.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            card_lay.addWidget(title)

            desc = QLabel("設定鋼板類型與厚度參數。階梯鋼板可指定精密區域元件。")
            desc.setProperty("class", "caption")
            desc.setWordWrap(True)
            desc.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
            card_lay.addWidget(desc)

        # ── 表單 ──
        # 共用控件建立
        self.product_combo = QComboBox()
        self.product_combo.setMinimumWidth(FORM_COMBO_MIN_WIDTH)
        self.product_combo.setMaximumWidth(DATA_SETUP_FIELD_MAX_WIDTH)
        self.product_combo.currentIndexChanged.connect(self._on_product_changed)
        self.btn_load_spec = QPushButton("載入")
        self.btn_load_spec.setProperty("class", "secondary")
        self.btn_load_spec.clicked.connect(self.load_selected_product_spec)

        self.type_combo = QComboBox()
        self.type_combo.addItem("普通鋼板", STENCIL_NORMAL)
        self.type_combo.addItem("階梯鋼板", STENCIL_STEPPED)
        self.type_combo.setMinimumWidth(FORM_COMBO_MIN_WIDTH)
        self.type_combo.setMaximumWidth(DATA_SETUP_FIELD_MAX_WIDTH)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)

        self.thickness_main = QLineEdit()
        self.thickness_main.setPlaceholderText("0.12")
        self.thickness_main.setToolTip("鋼板主厚度 (mm)")
        self.thickness_main.textChanged.connect(self._validate_thickness_field)

        self.thickness_precision = QLineEdit()
        self.thickness_precision.setPlaceholderText("0.08")
        self.thickness_precision.setToolTip("精密區域厚度 (mm)")

        self.precision_which = QComboBox()
        self.precision_which.addItem("主厚度即精密", True)
        self.precision_which.addItem("使用精密欄位", False)
        self.precision_which.setMinimumWidth(FORM_COMBO_MIN_WIDTH)
        self.precision_which.setMaximumWidth(DATA_SETUP_FIELD_MAX_WIDTH)

        self.thickness_validation_lbl = QLabel("")
        self.thickness_validation_lbl.setProperty("class", "caption")

        if self._embedded:
            # ── 嵌入模式：水平標籤緊湊排版，厚度並排 ──
            self.thickness_main.setMinimumWidth(FORM_COMBO_MIN_WIDTH)
            self.thickness_main.setMaximumWidth(DATA_SETUP_FIELD_MAX_WIDTH)
            self.thickness_precision.setMinimumWidth(FORM_COMBO_MIN_WIDTH)
            self.thickness_precision.setMaximumWidth(DATA_SETUP_FIELD_MAX_WIDTH)
            
            # Control limits fields
            self.vol_target = QLineEdit()
            self.vol_lsl = QLineEdit()
            self.vol_usl = QLineEdit()
            self.area_target = QLineEdit()
            self.area_lsl = QLineEdit()
            self.area_usl = QLineEdit()
            self.height_target = QLineEdit()
            self.height_lsl = QLineEdit()
            self.height_usl = QLineEdit()
            for le in [self.vol_target, self.vol_lsl, self.vol_usl, self.area_target, self.area_lsl, self.area_usl, self.height_target, self.height_lsl, self.height_usl]:
                le.setMinimumWidth(STENCIL_NUMERIC_MIN_WIDTH)
                le.setMaximumWidth(STENCIL_NUMERIC_MAX_WIDTH)

            # ── 橫向高密度摘要欄 ──
            self._summary_container = QFrame()
            self._summary_container.setProperty("class", "specSummaryRow")
            sum_lay = QtWidgets.QHBoxLayout(self._summary_container)
            sum_lay.setContentsMargins(SPACING_8, SPACING_4, SPACING_8, SPACING_4)
            sum_lay.setSpacing(SPACING_16)
            
            self.summary_spec_lbl = QLabel("規格：請先選擇或新增產品")
            self.summary_spec_lbl.setProperty("class", "specSummaryText")
            sum_lay.addWidget(self.summary_spec_lbl, 0)

            self.btn_manage_spec = QPushButton("管理規格")
            self.btn_manage_spec.setProperty("class", "secondary")
            self.btn_manage_spec.setFixedWidth(STENCIL_ACTION_BUTTON_WIDTH)
            self.btn_manage_spec.setToolTip("管理錫膏印刷與鋼板厚度規格")
            self.btn_manage_spec.clicked.connect(self.manage_requested.emit)
            sum_lay.addStretch(1) # Stretch in middle to push button right
            sum_lay.addWidget(self.btn_manage_spec, 0)
            
            # ── 橫向高密度排版：將類型與厚度放在一行 ──
            self._inputs_container = QFrame()
            _in_root = QtWidgets.QVBoxLayout(self._inputs_container)
            _in_root.setContentsMargins(0, 0, 0, 0)
            _in_root.setSpacing(SPACING_8)

            params_row = QtWidgets.QHBoxLayout()
            params_row.setSpacing(SPACING_12)
            params_row.setContentsMargins(0, 0, 0, 0)
            
            lbl_cap = QLabel("鋼板")
            lbl_cap.setProperty("class", "caption")
            lbl_cap.setMinimumWidth(STENCIL_LABEL_MIN_WIDTH)
            params_row.addWidget(lbl_cap, 0)

            # 類型
            params_row.addWidget(QLabel("類型"), 0)
            params_row.addWidget(self.type_combo, 1)

            # 主厚度
            params_row.addWidget(QLabel("主厚(mm)"), 0)
            params_row.addWidget(self.thickness_main, 1)

            # 精密厚度 + 精密對應 (僅階梯鋼板顯示)
            self._precision_container = QFrame()
            self._precision_container.setFrameShape(QFrame.Shape.NoFrame)
            _pc_lay = QtWidgets.QHBoxLayout(self._precision_container)
            _pc_lay.setContentsMargins(0, 0, 0, 0)
            _pc_lay.setSpacing(SPACING_8)

            _pc_lay.addWidget(QLabel("精密(mm)"), 0)
            _pc_lay.addWidget(self.thickness_precision, 1)
            _pc_lay.addWidget(QLabel("對應"), 0)
            _pc_lay.addWidget(self.precision_which, 1)

            params_row.addWidget(self._precision_container, 3)
            
            # Save button moved to end of params row in embedded mode to save vertical space
            self.btn_save = QPushButton("儲存")
            self.btn_save.setProperty("class", "primary")
            self.btn_save.setMinimumWidth(STENCIL_LABEL_MIN_WIDTH)
            self.btn_save.clicked.connect(self._save_spec)
            params_row.addWidget(self.btn_save, 0)

            params_row.addStretch(1)
            _in_root.addLayout(params_row)

            # ── 規格限也採用橫向分布 ──
            limits_area = QtWidgets.QHBoxLayout()
            limits_area.setSpacing(SPACING_12)
            limits_area.setContentsMargins(0, 0, 0, 0)
            
            lbl_limit_cap = QLabel("限值")
            lbl_limit_cap.setProperty("class", "caption")
            lbl_limit_cap.setMinimumWidth(STENCIL_LABEL_MIN_WIDTH)
            limits_area.addWidget(lbl_limit_cap, 0)

            def _add_compact_limit_block(label, target_le, lsl_le, usl_le):
                lay = QtWidgets.QHBoxLayout()
                lay.setSpacing(SPACING_4)
                lbl = QLabel(label)
                lbl.setProperty("class", "caption")
                lay.addWidget(lbl)
                
                lsl_le.setPlaceholderText("LSL")
                target_le.setPlaceholderText("Tgt")
                usl_le.setPlaceholderText("USL")
                lay.addWidget(lsl_le)
                lay.addWidget(target_le)
                lay.addWidget(usl_le)
                limits_area.addLayout(lay)

            _add_compact_limit_block("V%", self.vol_target, self.vol_lsl, self.vol_usl)
            _add_compact_limit_block("A%", self.area_target, self.area_lsl, self.area_usl)
            _add_compact_limit_block("H%", self.height_target, self.height_lsl, self.height_usl)
            limits_area.addStretch(1)
            _in_root.addLayout(limits_area)
            
            # Assemble embedded root
            root.addWidget(self._summary_container)
            root.addWidget(self._inputs_container)

            form_area = None # Already added to root
            self._summary_mode = True
            self._update_embedded_visibility()

        else:
            self.thickness_main.setMaximumWidth(DATA_SETUP_NUMERIC_FIELD_MAX_WIDTH)
            self.thickness_precision.setMaximumWidth(DATA_SETUP_NUMERIC_FIELD_MAX_WIDTH)
            # ── 獨立頁模式：標籤在上、控件在下 ──
            form_area = QtWidgets.QVBoxLayout()
            form_area.setSpacing(SPACING_16)
            form_area.setContentsMargins(0, 0, 0, 0)
            material_group = QLabel("鋼板類型")
            material_group.setProperty("class", "specGroupLabel")
            form_area.addWidget(material_group)
            self._product_row_container = QFrame()
            self._product_row_container.setFrameShape(QFrame.Shape.NoFrame)
            _product_row_lay = QtWidgets.QVBoxLayout(self._product_row_container)
            _product_row_lay.setContentsMargins(0, 0, 0, 0)
            _product_row_lay.setSpacing(0)
            _product_row_lay.addLayout(
                form_field_row("產品名稱", self.product_combo, self.btn_load_spec,
                               label_min_width=DATA_SETUP_TABLE_LABEL_WIDTH,
                               row_min_height=DATA_SETUP_TABLE_ROW_MIN_HEIGHT,
                               action_min_width=DATA_SETUP_PATH_ACTION_MIN_WIDTH)
            )
            form_area.addWidget(self._product_row_container)
            form_area.addLayout(
                form_field_row("鋼板類型", self.type_combo,
                               label_min_width=DATA_SETUP_TABLE_LABEL_WIDTH,
                               row_min_height=DATA_SETUP_TABLE_ROW_MIN_HEIGHT))
            dimensions_group = QLabel("厚度參數")
            dimensions_group.setProperty("class", "specGroupLabel")
            form_area.addWidget(dimensions_group)
            form_area.addLayout(
                form_field_row("鋼板主厚度 (mm)", self.thickness_main,
                               label_min_width=DATA_SETUP_TABLE_LABEL_WIDTH,
                               row_min_height=DATA_SETUP_TABLE_ROW_MIN_HEIGHT))
            form_area.addLayout(
                form_field_row("精密區域厚度 (mm)", self.thickness_precision,
                               label_min_width=DATA_SETUP_TABLE_LABEL_WIDTH,
                               row_min_height=DATA_SETUP_TABLE_ROW_MIN_HEIGHT))
            form_area.addLayout(
                form_field_row("精密對應", self.precision_which,
                               label_min_width=DATA_SETUP_TABLE_LABEL_WIDTH,
                               row_min_height=DATA_SETUP_TABLE_ROW_MIN_HEIGHT))

        if form_area:
            card_lay.addLayout(form_area)
        if not self._embedded:
            card_lay.addWidget(self.thickness_validation_lbl)

        # ── RefDes 勾選區 ──
        # 將精密元件勾選區也改為更緊湊的佈局
        self.refdes_container = QFrame()
        self.refdes_container.setFrameShape(QFrame.Shape.NoFrame)
        refdes_row = QtWidgets.QHBoxLayout(self.refdes_container)
        refdes_row.setSpacing(SPACING_12)
        refdes_row.setContentsMargins(0, 0, 0, 0)
        
        refdes_label_lay = QtWidgets.QVBoxLayout()
        refdes_label_lay.setSpacing(SPACING_4)
        refdes_title = QLabel("精密元件")
        refdes_title.setProperty("class", "caption")
        refdes_label_lay.addWidget(refdes_title)
        self.refdes_hint = QLabel("請先載入座標檔")
        self.refdes_hint.setProperty("class", "caption")
        refdes_label_lay.addWidget(self.refdes_hint)
        refdes_row.addLayout(refdes_label_lay, 0)

        scroll_widget = QFrame()
        scroll_widget.setFrameShape(QFrame.Shape.NoFrame)
        self.refdes_check_layout = QtWidgets.QHBoxLayout(scroll_widget)
        self.refdes_check_layout.setContentsMargins(SPACING_4, 0, SPACING_4, 0)
        self.refdes_check_layout.setSpacing(SPACING_8)
        
        self.refdes_scroll = QScrollArea()
        self.refdes_scroll.setWidgetResizable(True)
        self.refdes_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.refdes_scroll.setMaximumHeight(REFDES_SCROLL_COMPACT_MAX_H) # 極致壓縮高度
        self.refdes_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.refdes_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.refdes_scroll.setWidget(scroll_widget)
        refdes_row.addWidget(self.refdes_scroll, 1)

        if self._embedded:
            root.addWidget(self.refdes_container)
        else:
            card_lay.addWidget(self.refdes_container)

        # ── 儲存按鈕 ──
        if not self._embedded:
            self.btn_save = QPushButton("儲存鋼板規格")
            self.btn_save.setProperty("class", "primary")
            self.btn_save.clicked.connect(self._save_spec)
            card_lay.addWidget(self.btn_save)
        if not self._embedded:
            stabilize_minimum_height(main_card, DATA_SETUP_PRIMARY_CARD_MIN_HEIGHT)
        root.addWidget(main_card)
        if not embedded:
            root.addStretch(1)

        self._refdes_checkboxes: dict[str, QCheckBox] = {}
        self._populate_products()
        self._on_type_changed()
        self._validate_thickness_field()

        # Audit Item 117: Set proper tab order for form accessibility.
        # In embedded mode product_combo / btn_load_spec are not added to any
        # layout, so they have no top-level-window ancestor yet — including them
        # in setTabOrder triggers "must be in the same window" Qt warnings.
        if not self._embedded:
            self.setTabOrder(self.product_combo, self.btn_load_spec)
            self.setTabOrder(self.btn_load_spec, self.type_combo)
        self.setTabOrder(self.type_combo, self.thickness_main)
        self.setTabOrder(self.thickness_main, self.thickness_precision)
        self.setTabOrder(self.thickness_precision, self.precision_which)
        self.setTabOrder(self.precision_which, self.refdes_scroll)
        self.setTabOrder(self.refdes_scroll, self.btn_save)
        self._on_type_changed()

    def _update_embedded_visibility(self) -> None:
        """根據是否為摘要模式切換嵌入控制的可視性。"""
        if not self._embedded:
            return
        self._summary_container.setVisible(self._summary_mode)
        self._inputs_container.setVisible(not self._summary_mode)
        
        # ── 動態調整驗證標籤位置，確保摘要模式下併入一行 ──
        if self._summary_mode:
            # 加入摘要列 (插在文字與按鈕之間)
            lay = typing.cast(QBoxLayout, self._summary_container.layout())
            lay.insertWidget(1, self.thickness_validation_lbl)
        else:
            # 加入輸入區域底部
            lay = typing.cast(QBoxLayout, self._inputs_container.layout())
            lay.addWidget(self.thickness_validation_lbl)
        self.thickness_validation_lbl.setVisible(True)

    def set_summary_mode(self, enabled: bool) -> None:
        """供主頁面調用，切換「摘要顯示」或「完整編輯」模式。"""
        self._summary_mode = bool(enabled)
        self._update_embedded_visibility()

    def _on_type_changed(self) -> None:
        is_stepped = self.type_combo.currentData() == STENCIL_STEPPED
        if self._embedded:
            # 嵌入模式：直接隱藏精密欄位以節省垂直空間
            self._precision_container.setVisible(is_stepped)
        else:
            self.thickness_precision.setEnabled(is_stepped)
            self.precision_which.setEnabled(is_stepped)
            
        # 切換 RefDes 勾選區的可視性
        self.refdes_container.setVisible(is_stepped)

    def _on_product_changed(self) -> None:
        pass

    def set_external_product_mode(self, enabled: bool) -> None:
        """Toggle visibility of the internal product selector row.

        In embedded mode the product row is never built, so guard the
        attribute access to avoid AttributeError.
        """
        self._use_external_product = bool(enabled)
        if hasattr(self, "_product_row_container"):
            self._product_row_container.setVisible(not self._use_external_product)

    def set_selected_product(self, product_name: str) -> None:
        """Select the matching product in the combobox when provided externally."""
        if not product_name:
            self.product_combo.setCurrentIndex(0)
            return
        idx = self.product_combo.findData(product_name)
        if idx >= 0:
            self.product_combo.setCurrentIndex(idx)

    def selected_product(self) -> str:
        """Return selected product name from combobox data."""
        return str(self.product_combo.currentData() or "")

    def reset_for_product_change(self) -> None:
        """Reset spec fields and precision RefDes selection for new product context."""
        self.type_combo.setCurrentIndex(0)
        self.thickness_main.clear()
        self.thickness_precision.clear()
        self.thickness_main.setPlaceholderText("0.12")
        self.thickness_precision.setPlaceholderText("0.08")
        self._clear_refdes_inner()
        self.refdes_hint.setText("請先載入座標檔以取得 RefDes 清單。")
        self.refdes_hint.setVisible(True)
        self._validate_thickness_field()

    def has_valid_main_thickness(self) -> bool:
        """Check whether main thickness field is a valid value in allowed range."""
        txt = (self.thickness_main.text() or self.thickness_main.placeholderText() or "").strip()
        try:
            value = float(txt)
        except ValueError:
            return False
        return self.THICKNESS_MIN_MM <= value <= self.THICKNESS_MAX_MM

    def _validate_thickness_field(self) -> None:
        is_valid = self.has_valid_main_thickness()
        if is_valid:
            self.thickness_validation_lbl.setText(
                f"主厚度有效（{self.THICKNESS_MIN_MM:.2f} - {self.THICKNESS_MAX_MM:.2f} mm）"
            )
            self.thickness_validation_lbl.setProperty("valueState", "good")
        else:
            self.thickness_validation_lbl.setText(
                f"主厚度需介於 {self.THICKNESS_MIN_MM:.2f} - {self.THICKNESS_MAX_MM:.2f} mm"
            )
            self.thickness_validation_lbl.setProperty("valueState", "bad")
        self.thickness_validation_lbl.style().unpolish(self.thickness_validation_lbl)
        self.thickness_validation_lbl.style().polish(self.thickness_validation_lbl)
        self.thickness_validity_changed.emit(is_valid)

    def _populate_products(self) -> None:
        self.product_combo.clear()
        self.product_combo.addItem("請選擇產品…", None)
        for e in list_registered():
            name = (e.get("product_name") or "").strip()
            if name:
                self.product_combo.addItem(name, name)

    def refresh_products(self) -> None:
        """由外部呼叫以更新產品下拉清單。"""
        self._populate_products()

    def refresh_refdes_list(self) -> None:
        """由外部呼叫（座標載入完成後）以從 coord_df 更新 RefDes 勾選清單。"""
        from app.data.session_store import SessionStore
        store = SessionStore()
        product_name = (store.workorder_master or {}).get("product_name") or ""
        if product_name:
            idx = self.product_combo.findData(product_name)
            if idx >= 0:
                self.product_combo.setCurrentIndex(idx)
        coord_df = getattr(store, "coord_df", None)
        if coord_df is None or coord_df.empty or "RefDes" not in coord_df.columns:
            self._refdes_checkboxes.clear()
            self.refdes_hint.setText("請先載入座標檔以取得 RefDes 清單。")
            self.refdes_hint.setVisible(True)
            self._clear_refdes_inner()
            return
        refdes_list = sorted(coord_df["RefDes"].astype(str).unique().tolist())
        if not refdes_list:
            self.refdes_hint.setText("目前座標檔無 RefDes。")
            self.refdes_hint.setVisible(True)
            self._clear_refdes_inner()
            return
        self.refdes_hint.setVisible(False)
        precision_set = set(list_precision_refdes(product_name)) if product_name else set()
        self._clear_refdes_inner()
        self._refdes_checkboxes = {}
        for r in refdes_list:
            cb = QCheckBox(r)
            cb.setChecked(r in precision_set)
            self._refdes_checkboxes[r] = cb
            self.refdes_check_layout.addWidget(cb)
        self.refdes_check_layout.addStretch()

    def load_selected_product_spec(self) -> None:
        """Public API to load and render spec for current selected product."""
        self._load_selected_product_spec_impl()

    def _clear_refdes_inner(self) -> None:
        while self.refdes_check_layout.count():
            item = self.refdes_check_layout.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._refdes_checkboxes = {}

    def _load_selected_product_spec_impl(self) -> None:
        product_name = self.product_combo.currentData()
        if not product_name:
            if self._embedded:
                self.summary_spec_lbl.setText("<b>規格：</b>請先選擇或新增產品")
                self.set_summary_mode(True)
            return
        spec = get_product_spec(product_name)
        if not spec:
            self.thickness_main.clear()
            self.thickness_precision.clear()
            self.thickness_main.setPlaceholderText("0.12")
            self.thickness_precision.setPlaceholderText("0.08")
            self.type_combo.setCurrentIndex(0)
            if self._embedded:
                self.summary_spec_lbl.setText("<b>規格：</b>尚未設定（請按「管理規格」新增）")
                self.set_summary_mode(True)
            return
        self.thickness_main.setText(str(spec.get("thickness_main", "")))
        self.thickness_precision.setText(str(spec.get("thickness_precision", "")) if spec.get("thickness_precision") is not None else "")
        stencil_type = (spec.get("stencil_type") or STENCIL_NORMAL).strip().lower()
        idx = self.type_combo.findData(stencil_type)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)
        self.precision_which.setCurrentIndex(0 if spec.get("precision_is_main") else 1)

        # Load control limits — only exist in embedded mode.
        if self._embedded:
            self.vol_target.setText(str(spec.get("default_volume_target", 100.0)))
            self.vol_lsl.setText(str(spec.get("default_volume_lsl", 70.0)))
            self.vol_usl.setText(str(spec.get("default_volume_usl", 150.0)))
            self.area_target.setText(str(spec.get("default_area_target", 100.0)))
            self.area_lsl.setText(str(spec.get("default_area_lsl", 70.0)))
            self.area_usl.setText(str(spec.get("default_area_usl", 150.0)))
            self.height_target.setText(str(spec.get("default_height_target", 100.0)))
            self.height_lsl.setText(str(spec.get("default_height_lsl", 70.0)))
            self.height_usl.setText(str(spec.get("default_height_usl", 140.0)))
            
            # Update Summary Label
            t_main = spec.get("thickness_main", 0.12)
            s_type = "階梯" if stencil_type == STENCIL_STEPPED else "普通"
            v_l, v_u = spec.get("default_volume_lsl", 70), spec.get("default_volume_usl", 150)
            a_l, a_u = spec.get("default_area_lsl", 70), spec.get("default_area_usl", 150)
            h_l, h_u = spec.get("default_height_lsl", 70), spec.get("default_height_usl", 140)
            summary = (
                f"<b>規格：</b>{s_type} {t_main}mm | "
                f"<b>限值：</b>V:{v_l}-{v_u}% / A:{a_l}-{a_u}% / H:{h_l}-{h_u}%"
            )
            self.summary_spec_lbl.setText(summary)
            # 預設載入現有產品時進入摘要模式
            self.set_summary_mode(True)
        
        self.refresh_refdes_list()

    def _save_spec(self) -> None:
        product_name = self.product_combo.currentData()
        if not product_name:
            from app.ui.theme import show_dark_warning
            show_dark_warning(self, "無法儲存", "請選擇產品名稱。")
            return
        if not self.has_valid_main_thickness():
            from app.ui.theme import show_dark_warning
            show_dark_warning(
                self,
                "無法儲存",
                f"主厚度需介於 {self.THICKNESS_MIN_MM:.2f} - {self.THICKNESS_MAX_MM:.2f} mm。",
            )
            return
        try:
            t_main = float(self.thickness_main.text() or self.thickness_main.placeholderText() or "0.12")
        except ValueError:
            from app.ui.theme import show_dark_warning
            show_dark_warning(self, "無法儲存", "主厚度必須為數字。")
            return
        stencil_type = self.type_combo.currentData() or STENCIL_NORMAL
        t_precision = None
        if stencil_type == STENCIL_STEPPED:
            try:
                t_precision = float(self.thickness_precision.text() or self.thickness_precision.placeholderText() or "0.08")
            except ValueError:
                from app.ui.theme import show_dark_warning
                show_dark_warning(self, "無法儲存", "階梯鋼板時精密厚度必須為數字。")
                return
        precision_is_main = self.precision_which.currentData()
        # Control-limit fields only exist in embedded mode; fall back to
        # sensible defaults when running as a standalone (non-embedded) widget.
        spec = {
            "product_name": product_name,
            "stencil_type": stencil_type,
            "thickness_main": t_main,
            "thickness_precision": t_precision,
            "precision_is_main": bool(precision_is_main),
            "default_volume_target": float(self.vol_target.text() or 100.0) if self._embedded else 100.0,
            "default_volume_lsl": float(self.vol_lsl.text() or 70.0) if self._embedded else 70.0,
            "default_volume_usl": float(self.vol_usl.text() or 150.0) if self._embedded else 150.0,
            "default_area_target": float(self.area_target.text() or 100.0) if self._embedded else 100.0,
            "default_area_lsl": float(self.area_lsl.text() or 70.0) if self._embedded else 70.0,
            "default_area_usl": float(self.area_usl.text() or 150.0) if self._embedded else 150.0,
            "default_height_target": float(self.height_target.text() or 100.0) if self._embedded else 100.0,
            "default_height_lsl": float(self.height_lsl.text() or 70.0) if self._embedded else 70.0,
            "default_height_usl": float(self.height_usl.text() or 140.0) if self._embedded else 140.0,
        }
        if not save_product_spec(spec):
            from app.ui.theme import show_dark_warning
            show_dark_warning(self, "儲存失敗", "寫入規格檔失敗。")
            return
        if stencil_type == STENCIL_STEPPED:
            precision_refdes = [r for r, cb in getattr(self, "_refdes_checkboxes", {}).items() if cb.isChecked()]
            from app.data.session_store import SessionStore
            store = SessionStore()
            coord_path = (store.coord_meta or {}).get("filepath") or ""
            save_assignments(product_name, precision_refdes, coord_path)
        else:
            # Audit Item 112: Clear previous assignments if changed back to NORMAL
            from app.data.stencil_assignment_registry import clear_by_product
            clear_by_product(product_name)
        from app.ui.theme import show_dark_information
        show_dark_information(self, "已儲存", f"已儲存「{product_name}」鋼板規格。")
        self.spec_saved.emit(product_name)
