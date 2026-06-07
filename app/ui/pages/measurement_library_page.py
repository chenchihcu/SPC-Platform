"""
資料庫管理頁 (Database Management Page)

功能：
- 提供量測歷史記錄與座標產品註冊的分類管理。
- 以產品名稱、工單編號、批號（識別碼）、料號、日期範圍、關鍵字搜尋所有已上傳量測記錄
- 點選記錄即可載入量測檔（emit measurement_selected）
- 支援編輯中繼資料（產品名稱、供應商工單、醫電工單、批號識別碼、料號、備註）
- 支援刪除記錄（僅刪除 DB 記錄，不刪除本機檔案）
- 上傳量測後由 MainWindow 呼叫 save_and_refresh() 自動儲存
"""
from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

_log = logging.getLogger(__name__)

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QTabWidget,
)

from app.data.measurement_library import (
    delete_measurement_session,
    list_measurement_sessions,
    list_product_names_with_sessions,
    save_measurement_session,
    update_measurement_session,
)
from app.data.coordinate_library import (
    list_coordinate_versions,
    set_active_coordinate_version,
    delete_coordinate_version,
    update_coordinate_metadata,
)
from app.data.paste_printing_spec_library import (
    delete_paste_printing_spec_version,
    list_paste_printing_spec_versions,
    set_active_paste_printing_spec_version,
    update_paste_printing_spec_metadata,
)
from app.data.paste_printing_spec_registry import save as save_paste_printing_spec
from app.data.stencil_thickness_library import (
    delete_stencil_thickness_version,
    list_stencil_thickness_versions,
    set_active_stencil_thickness_version,
    update_stencil_thickness_metadata,
)
from app.data.stencil_thickness_registry import (
    STENCIL_NORMAL,
    STENCIL_STEPPED,
    UNIT_MODE_ABSOLUTE,
    UNIT_MODE_PERCENT,
    save as save_stencil_thickness_spec,
)
from app.data.supplier_library import (
    SupplierCodeMigrationConflictError,
    create_supplier_record,
    delete_supplier_record,
    list_supplier_codes,
    list_supplier_records,
    update_supplier_record,
)
from app.data.coordinate_registry import list_registered
from app.ui.theme import show_dark_information, show_dark_warning
from app.ui.theme.tokens import (
    SPACING_4,
    SPACING_8,
    SPACING_12,
    SPACING_16,
    BORDER,
    BORDER_SUBTLE,
    DIALOG_LIBRARY_EDIT_INIT_HEIGHT,
    DIALOG_LIBRARY_EDIT_INIT_WIDTH,
    DIALOG_MIN_WIDTH_STANDARD,
    MEAS_LIB_SHORT_FIELD_MIN_WIDTH,
    MEAS_LIB_ACTION_BUTTON_MIN_WIDTH,
    MEAS_LIB_ACTION_BUTTON_MIN_HEIGHT,
    MEAS_LIB_BUTTON_ROW_SPACING,
    MEAS_LIB_WORKORDER_MIN_WIDTH,
    STATUS_LAMP_SUCCESS,
    STATUS_LAMP_WARNING,
    TABLE_HEADER_BG,
    TEXT_DISABLED,
    TEXT_PRIMARY,
)
from app.ui.theme.layout_policy import fit_top_level_to_available
from app.ui.widgets.page_templates import (
    apply_status_accessibility,
    create_status_lamp,
    page_margins_and_spacing,
    setup_compact_title_header,
    style_table,
)
from app.ui.workflow_labels import WORKFLOW_LABEL_CHARTS, WORKFLOW_LABEL_LIBRARY


# ─────────────────────────────────────────────────────────────────────────────
# Edit Dialogs
# ─────────────────────────────────────────────────────────────────────────────


def _fit_library_edit_dialog(dialog: QDialog) -> None:
    """Apply shared top-level fitting to compact library edit dialogs."""
    fit_top_level_to_available(
        dialog,
        preferred_size=(DIALOG_LIBRARY_EDIT_INIT_WIDTH, DIALOG_LIBRARY_EDIT_INIT_HEIGHT),
        fallback_size=(DIALOG_LIBRARY_EDIT_INIT_WIDTH, DIALOG_LIBRARY_EDIT_INIT_HEIGHT),
    )


class _EditSessionDialog(QDialog):
    """編輯量測記錄中繼資料的小對話框。"""

    def __init__(self, session: Dict[str, Any], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("編輯量測記錄")
        self.setMinimumWidth(DIALOG_MIN_WIDTH_STANDARD)
        self._session_id = int(session.get("id", 0))

        layout = QVBoxLayout(self)
        layout.setSpacing(SPACING_8)

        form_widget = QWidget()
        form = QFormLayout(form_widget)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(SPACING_8)

        self.product_name_edit = QLineEdit(str(session.get("product_name", "") or ""))
        self.supplier_work_order_edit = QLineEdit(str(session.get("supplier_work_order_no", "") or ""))
        self.outsource_work_order_edit = QLineEdit(str(session.get("outsource_work_order_no", "") or ""))
        self.part_no_edit = QLineEdit(str(session.get("product_part_no", "") or ""))
        self.notes_edit = QLineEdit(str(session.get("notes", "") or ""))

        form.addRow("產品名稱：", self.product_name_edit)
        form.addRow("供應商製令工單：", self.supplier_work_order_edit)
        form.addRow("醫電製令工單：", self.outsource_work_order_edit)
        form.addRow("產品料號：", self.part_no_edit)
        form.addRow("備註：", self.notes_edit)

        # 檔案路徑（唯讀顯示）
        path_lbl = QLabel(str(session.get("file_path", "") or "—"))
        path_lbl.setProperty("class", "caption")
        path_lbl.setWordWrap(True)
        form.addRow("量測檔路徑：", path_lbl)

        layout.addWidget(form_widget)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        _fit_library_edit_dialog(self)

    def get_values(self) -> Dict[str, str]:
        """Return edited measurement-session fields."""
        return {
            "product_name": self.product_name_edit.text().strip(),
            "supplier_work_order_no": self.supplier_work_order_edit.text().strip(),
            "outsource_work_order_no": self.outsource_work_order_edit.text().strip(),
            "product_part_no": self.part_no_edit.text().strip(),
            "notes": self.notes_edit.text().strip(),
        }


class _EditCoordinateDialog(QDialog):
    """編輯座標記錄中繼資料。"""

    def __init__(self, version: Dict[str, Any], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("編輯座標記錄")
        self.setMinimumWidth(DIALOG_MIN_WIDTH_STANDARD)

        layout = QVBoxLayout(self)
        layout.setSpacing(SPACING_8)

        form_widget = QWidget()
        form = QFormLayout(form_widget)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(SPACING_8)

        self.product_name_edit = QLineEdit(str(version.get("product_name", "") or ""))
        self.part_no_edit = QLineEdit(str(version.get("product_part_no", "") or ""))

        form.addRow("產品名稱：", self.product_name_edit)
        form.addRow("產品料號：", self.part_no_edit)

        path_lbl = QLabel(str(version.get("file_path", "") or "—"))
        path_lbl.setProperty("class", "caption")
        path_lbl.setWordWrap(True)
        form.addRow("座標檔路徑：", path_lbl)

        layout.addWidget(form_widget)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        _fit_library_edit_dialog(self)

    def get_values(self) -> Dict[str, str]:
        """Return edited coordinate metadata fields."""
        return {
            "product_name": self.product_name_edit.text().strip(),
            "product_part_no": self.part_no_edit.text().strip(),
        }


class _PasteSpecForm(QWidget):
    """錫膏印刷規格表單（僅限值欄位）。"""

    def __init__(self, version: Optional[Dict[str, Any]] = None, parent=None) -> None:
        super().__init__(parent)
        v = version or {}

        form = QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(SPACING_8)

        self._limit_fields: Dict[str, QLineEdit] = {}

        header = QLabel("請設定體積/面積目標與上下限，以及高度上下限")
        header.setProperty("class", "caption")
        form.addRow("規格管制：", header)

        for metric_key, metric_label in (("volume", "體積"), ("area", "面積")):
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(SPACING_8)
            for field_key, field_label in (("lsl", "下限"), ("target", "標準值"), ("usl", "上限")):
                full_key = f"default_{metric_key}_{field_key}"
                edit = QLineEdit(str(v.get(full_key, "") or ""))
                edit.setPlaceholderText(field_label)
                edit.setFixedWidth(MEAS_LIB_WORKORDER_MIN_WIDTH)
                self._limit_fields[full_key] = edit
                row_layout.addWidget(QLabel(field_label), 0)
                row_layout.addWidget(edit, 0)
            row_layout.addStretch(1)
            form.addRow(f"{metric_label}：", row_widget)

        height_row = QWidget()
        height_row_layout = QHBoxLayout(height_row)
        height_row_layout.setContentsMargins(0, 0, 0, 0)
        height_row_layout.setSpacing(SPACING_8)
        for field_key, field_label in (("lsl", "下限"), ("usl", "上限")):
            full_key = f"default_height_{field_key}"
            edit = QLineEdit(str(v.get(full_key, "") or ""))
            edit.setPlaceholderText(field_label)
            edit.setFixedWidth(MEAS_LIB_WORKORDER_MIN_WIDTH)
            self._limit_fields[full_key] = edit
            height_row_layout.addWidget(QLabel(field_label), 0)
            height_row_layout.addWidget(edit, 0)
        height_row_layout.addStretch(1)
        form.addRow("高度：", height_row)

    @staticmethod
    def _label_for_field(field_key: str) -> str:
        metric_map = {"volume": "體積", "area": "面積", "height": "高度"}
        bound_map = {"target": "標準值", "lsl": "下限", "usl": "上限"}
        parts = field_key.split("_")
        if len(parts) >= 3:
            metric = metric_map.get(parts[1], parts[1])
            bound = bound_map.get(parts[2], parts[2])
            return f"{metric}{bound}"
        return field_key

    @staticmethod
    def _validate_limits(values: Dict[str, Any]) -> None:
        metric_map = {"volume": "體積", "area": "面積"}
        for metric in ("volume", "area"):
            lsl = float(values[f"default_{metric}_lsl"])
            target = float(values[f"default_{metric}_target"])
            usl = float(values[f"default_{metric}_usl"])
            if not (lsl <= target <= usl):
                raise ValueError(f"{metric_map[metric]} 規格需符合 下限 <= 標準值 <= 上限。")
        h_lsl = float(values["default_height_lsl"])
        h_usl = float(values["default_height_usl"])
        if h_lsl > h_usl:
            raise ValueError("高度規格需符合 下限 <= 上限。")

    def get_values(self) -> Dict[str, Any]:
        """Return validated paste-printing limit values."""
        values: Dict[str, Any] = {}
        for key, edit in self._limit_fields.items():
            text = edit.text().strip()
            label = self._label_for_field(key)
            if not text:
                raise ValueError(f"欄位「{label}」不可空白。")
            try:
                values[key] = float(text)
            except ValueError as exc:
                raise ValueError(f"欄位「{label}」必須是數字。") from exc
        self._validate_limits(values)
        return values


class _StencilSpecForm(QWidget):
    """鋼板厚度規格表單（僅限值欄位）。"""

    def __init__(self, version: Optional[Dict[str, Any]] = None, parent=None) -> None:
        super().__init__(parent)
        v = version or {}

        form = QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(SPACING_8)

        self.stencil_type_combo = QComboBox()
        self.stencil_type_combo.addItem("普通鋼板", STENCIL_NORMAL)
        self.stencil_type_combo.addItem("階梯鋼板", STENCIL_STEPPED)
        idx = self.stencil_type_combo.findData(str(v.get("stencil_type") or STENCIL_NORMAL))
        if idx >= 0:
            self.stencil_type_combo.setCurrentIndex(idx)

        self.thickness_main_edit = QLineEdit(str(v.get("thickness_main", "") or ""))
        self.thickness_precision_edit = QLineEdit(str(v.get("thickness_precision", "") or ""))

        self.precision_is_main_combo = QComboBox()
        self.precision_is_main_combo.addItem("主厚度=精密", True)
        self.precision_is_main_combo.addItem("精密厚度欄位=精密", False)
        self.precision_is_main_combo.setCurrentIndex(0 if bool(v.get("precision_is_main")) else 1)

        self.unit_mode_combo = QComboBox()
        self.unit_mode_combo.addItem("百分比(%)", UNIT_MODE_PERCENT)
        self.unit_mode_combo.addItem("絕對值", UNIT_MODE_ABSOLUTE)
        mode_idx = self.unit_mode_combo.findData(str(v.get("unit_mode") or UNIT_MODE_PERCENT))
        if mode_idx >= 0:
            self.unit_mode_combo.setCurrentIndex(mode_idx)

        self.height_denominator_edit = QLineEdit(str(v.get("height_denominator_mm", "") or ""))

        form.addRow("鋼板類型：", self.stencil_type_combo)
        form.addRow("主厚度(mm)：", self.thickness_main_edit)
        form.addRow("精密厚度(mm)：", self.thickness_precision_edit)
        form.addRow("精密對應：", self.precision_is_main_combo)
        form.addRow("Height單位模式：", self.unit_mode_combo)
        form.addRow("Height分母(mm)：", self.height_denominator_edit)

    def get_values(self) -> Dict[str, Any]:
        """Return validated stencil-thickness values."""
        stencil_type = str(self.stencil_type_combo.currentData() or STENCIL_NORMAL)
        try:
            thickness_main = float(self.thickness_main_edit.text().strip())
        except ValueError as exc:
            raise ValueError("主厚度必須為數字。") from exc
        if thickness_main <= 0:
            raise ValueError("主厚度需大於 0。")

        thickness_precision_value: Optional[float] = None
        if stencil_type == STENCIL_STEPPED:
            txt = self.thickness_precision_edit.text().strip()
            if not txt:
                raise ValueError("階梯鋼板需設定精密厚度。")
            try:
                thickness_precision_value = float(txt)
            except ValueError as exc:
                raise ValueError("精密厚度必須為數字。") from exc
        elif self.thickness_precision_edit.text().strip():
            try:
                thickness_precision_value = float(self.thickness_precision_edit.text().strip())
            except ValueError as exc:
                raise ValueError("精密厚度必須為數字。") from exc

        try:
            denominator = float(self.height_denominator_edit.text().strip())
        except ValueError as exc:
            raise ValueError("Height分母必須為數字。") from exc
        if denominator <= 0:
            raise ValueError("Height分母需大於 0。")

        return {
            "stencil_type": stencil_type,
            "thickness_main": thickness_main,
            "thickness_precision": thickness_precision_value,
            "precision_is_main": bool(self.precision_is_main_combo.currentData()),
            "unit_mode": str(self.unit_mode_combo.currentData() or UNIT_MODE_PERCENT),
            "height_denominator_mm": denominator,
        }


class _EditCombinedSpecDialog(QDialog):
    """合併編輯一個產品的錫膏印刷規格 + 鋼板厚度規格。"""

    def __init__(self, joined: Dict[str, Any], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("編輯產品規格")
        self.setMinimumWidth(DIALOG_MIN_WIDTH_STANDARD)

        paste = joined.get("paste") or {}
        stencil = joined.get("stencil") or {}
        product_name = (
            joined.get("product_name")
            or paste.get("product_name")
            or stencil.get("product_name")
            or ""
        )
        product_part_no = (
            joined.get("product_part_no")
            or paste.get("product_part_no")
            or stencil.get("product_part_no")
            or ""
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_16, SPACING_12, SPACING_16, SPACING_12)
        layout.setSpacing(SPACING_8)

        # ── 共用：產品名稱、產品料號 ──
        shared_form = QFormLayout()
        shared_form.setContentsMargins(0, 0, 0, 0)
        shared_form.setSpacing(SPACING_8)
        self.product_name_edit = QLineEdit(str(product_name))
        self.part_no_edit = QLineEdit(str(product_part_no))
        shared_form.addRow("產品名稱：", self.product_name_edit)
        shared_form.addRow("產品料號：", self.part_no_edit)
        layout.addLayout(shared_form)

        # ── 兩段子規格 tabs ──
        sub_tabs = QTabWidget()
        self._paste_form = _PasteSpecForm(paste)
        self._stencil_form = _StencilSpecForm(stencil)
        sub_tabs.addTab(self._paste_form, "錫膏印刷")
        sub_tabs.addTab(self._stencil_form, "鋼板厚度")
        layout.addWidget(sub_tabs)

        # 最後更新時間（只讀）
        paste_updated = str(paste.get("updated_at", "") or "")
        stencil_updated = str(stencil.get("updated_at", "") or "")
        if paste_updated or stencil_updated:
            updated_lbl = QLabel(
                f"最後更新：錫膏 {paste_updated or '—'}　鋼板 {stencil_updated or '—'}"
            )
            updated_lbl.setProperty("class", "caption")
            layout.addWidget(updated_lbl)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        _fit_library_edit_dialog(self)

    def get_values(self) -> Dict[str, Any]:
        """Return combined spec values; raises ValueError on validation failure."""
        product_name = self.product_name_edit.text().strip()
        product_part_no = self.part_no_edit.text().strip()
        if not product_name:
            raise ValueError("產品名稱不可空白。")
        paste_values = self._paste_form.get_values()
        stencil_values = self._stencil_form.get_values()
        paste_values.update(
            {"product_name": product_name, "product_part_no": product_part_no}
        )
        stencil_values.update(
            {"product_name": product_name, "product_part_no": product_part_no}
        )
        return {"paste": paste_values, "stencil": stencil_values}


class _EditSupplierDialog(QDialog):
    """新增/編輯供應商管理資料。"""

    def __init__(self, record: Optional[Dict[str, Any]] = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("新增供應商資料" if record is None else "編輯供應商資料")
        self.setMinimumWidth(DIALOG_MIN_WIDTH_STANDARD)
        source = record or {}
        is_new_record = record is None

        layout = QVBoxLayout(self)
        layout.setSpacing(SPACING_8)

        form_widget = QWidget()
        form = QFormLayout(form_widget)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(SPACING_8)

        supplier_code_text = str(source.get("supplier_code", "") or "")
        if is_new_record and not supplier_code_text:
            supplier_code_text = "系統自動生成"
        self.supplier_code_edit = QLineEdit(supplier_code_text)
        self.supplier_code_edit.setReadOnly(True)
        self.supplier_code_edit.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.supplier_code_edit.setProperty("class", "readOnlyInput")
        self.supplier_name_edit = QLineEdit(str(source.get("supplier_name", "") or ""))
        self.steel_plate_no_edit = QLineEdit(str(source.get("steel_plate_no", "") or ""))
        self.production_date_edit = QLineEdit(str(source.get("steel_plate_production_date", "") or ""))
        self.production_date_edit.setPlaceholderText("YYYY-MM-DD")

        form.addRow("供應商編號：", self.supplier_code_edit)
        form.addRow("供應商名稱：", self.supplier_name_edit)
        form.addRow("鋼板編號：", self.steel_plate_no_edit)
        form.addRow("鋼板生產日期：", self.production_date_edit)
        layout.addWidget(form_widget)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        _fit_library_edit_dialog(self)

    def get_values(self) -> Dict[str, str]:
        """Return edited supplier metadata fields."""
        values = {
            "supplier_name": self.supplier_name_edit.text().strip(),
            "steel_plate_no": self.steel_plate_no_edit.text().strip(),
            "steel_plate_production_date": self.production_date_edit.text().strip(),
        }
        if not values["supplier_name"]:
            raise ValueError("供應商名稱不可空白。")
        if not values["steel_plate_no"]:
            raise ValueError("鋼板編號不可空白。")
        if not values["steel_plate_production_date"]:
            raise ValueError("鋼板生產日期不可空白。")
        try:
            datetime.fromisoformat(values["steel_plate_production_date"])
        except ValueError as exc:
            raise ValueError("鋼板生產日期格式需為 YYYY-MM-DD。") from exc
        return values


# ─────────────────────────────────────────────────────────────────────────────
# Main Page
# ─────────────────────────────────────────────────────────────────────────────

_COL_NAMES = ["產品名稱", "工單編號", "料號", "上傳時間", "筆數", "量測檔", "備註"]
_COORD_COL_NAMES = ["產品名稱", "產品料號", "註冊時間", "主要版次", "列數", "座標檔路徑"]
# 規格管理（合併錫膏印刷規格 + 鋼板厚度規格）
_COMBINED_SPEC_COL_NAMES = [
    "產品名稱",
    "產品料號",
    "體積規格",
    "面積規格",
    "高度規格(%)",
    "鋼板類型",
    "主厚度",
    "精密厚度",
    "Height模式",
    "分母(mm)",
    "更新時間",
    "現用版本",
]
# (label, first_col, last_col) — visual band groupings for combined spec table header
_COMBINED_SPEC_GROUPS: List[tuple[str, int, int]] = [
    ("共用", 0, 1),
    ("錫膏印刷規格", 2, 4),
    ("鋼板厚度規格", 5, 9),
    ("狀態", 10, 11),
]
_SUPPLIER_COL_NAMES = ["供應商編號", "供應商名稱", "鋼板編號", "鋼板生產日期", "更新時間"]


def _make_item(text: str, align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter) -> QTableWidgetItem:
    it = QTableWidgetItem(text)
    it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
    it.setTextAlignment(align)
    return it


def _join_active_specs(
    paste_rows: List[Dict[str, Any]],
    stencil_rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Outer-join paste + stencil version rows on (product_name, product_part_no).

    Each output row is keyed on a (product_name, product_part_no) pair and carries
    both sub-spec dicts when present. Pure helper — no UI dependencies — so the
    join can be unit tested independently.
    """
    def _key(row: Dict[str, Any]) -> tuple[str, str]:
        return (
            str(row.get("product_name") or "").strip(),
            str(row.get("product_part_no") or "").strip(),
        )

    paste_by_key: Dict[tuple[str, str], Dict[str, Any]] = {}
    for r in paste_rows:
        k = _key(r)
        if k[0] and k not in paste_by_key:
            paste_by_key[k] = r
    stencil_by_key: Dict[tuple[str, str], Dict[str, Any]] = {}
    for r in stencil_rows:
        k = _key(r)
        if k[0] and k not in stencil_by_key:
            stencil_by_key[k] = r

    keys: List[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for r in paste_rows:
        k = _key(r)
        if k[0] and k not in seen:
            seen.add(k)
            keys.append(k)
    for r in stencil_rows:
        k = _key(r)
        if k[0] and k not in seen:
            seen.add(k)
            keys.append(k)

    joined: List[Dict[str, Any]] = []
    for product_name, product_part_no in keys:
        paste = paste_by_key.get((product_name, product_part_no))
        stencil = stencil_by_key.get((product_name, product_part_no))
        joined.append(
            {
                "product_name": product_name,
                "product_part_no": product_part_no,
                "paste": paste,
                "stencil": stencil,
            }
        )
    return joined


class _GroupedHeaderView(QHeaderView):
    """Horizontal header that paints a top band labelling consecutive column groups.

    Bands are defined as a list of (label, first_col, last_col) tuples. Each
    section's `paintSection` overlays the section's slice of the band; Qt clips
    drawing to each section, so painting the same group label rect from every
    section in the group yields a centred label across the full group span.
    """

    BAND_HEIGHT = 22

    def __init__(self, groups: List[tuple[str, int, int]], parent=None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._groups = groups
        self.setSectionsClickable(False)
        self.setHighlightSections(False)

    def sizeHint(self) -> QSize:
        """Qt override: extend default header height by BAND_HEIGHT for the group strip."""
        hint = super().sizeHint()
        hint.setHeight(hint.height() + self.BAND_HEIGHT)
        return hint

    def _group_for(self, logical_index: int) -> Optional[tuple[str, int, int]]:
        for label, first, last in self._groups:
            if first <= logical_index <= last:
                return (label, first, last)
        return None

    def _group_extent_x(self, first: int, last: int) -> tuple[int, int]:
        left = self.sectionViewportPosition(first)
        right = self.sectionViewportPosition(last) + self.sectionSize(last)
        return left, right

    def paintSection(self, painter, rect, logicalIndex) -> None:
        """Qt override: draw the column header below the group band, then paint the band slice."""
        # Paint the column header in the lower portion (skip top band height).
        lower_rect = QRect(
            rect.x(),
            rect.y() + self.BAND_HEIGHT,
            rect.width(),
            rect.height() - self.BAND_HEIGHT,
        )
        super().paintSection(painter, lower_rect, logicalIndex)

        # Top band background + bottom hairline divider.
        band_rect = QRect(rect.x(), rect.y(), rect.width(), self.BAND_HEIGHT)
        painter.save()
        painter.fillRect(band_rect, QColor(TABLE_HEADER_BG))
        painter.setPen(QColor(BORDER_SUBTLE))
        painter.drawLine(band_rect.bottomLeft(), band_rect.bottomRight())

        group = self._group_for(logicalIndex)
        if group is not None:
            label, first, last = group
            # Vertical divider on the right edge of the last column in each group.
            if logicalIndex == last:
                painter.setPen(QColor(BORDER))
                painter.drawLine(band_rect.topRight(), band_rect.bottomRight())
            # Group label: paint over the full group extent — Qt clips to this
            # section's slice, so consecutive sections compose the centred text.
            left_x, right_x = self._group_extent_x(first, last)
            label_rect = QRect(left_x, band_rect.y(), right_x - left_x, band_rect.height())
            painter.setPen(QColor(TEXT_PRIMARY))
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, label)
        painter.restore()


class MeasurementLibraryPage(QWidget):
    """
    量測資料庫管理頁：提供量測歷史記錄與座標產品註冊的分類管理。
    """

    #: 使用者選取記錄並按「載入」時發出，攜帶量測檔路徑。
    measurement_selected = Signal(str)
    #: 相容擴充：除路徑外一併傳出 session metadata（雙工單/產品/批號）。
    measurement_selected_with_context = Signal(str, dict)
    #: 使用者選取座標記錄時發出。
    coordinate_selected = Signal(str)
    #: 使用者選取規格記錄時發出（攜帶產品名稱）。
    spec_selected = Signal(str)

    def _make_search_toolbar(self) -> tuple[QFrame, QHBoxLayout]:
        toolbar = QFrame()
        toolbar.setProperty("class", "tableToolbar")
        row = QHBoxLayout(toolbar)
        row.setContentsMargins(SPACING_8, SPACING_4, SPACING_8, SPACING_4)
        row.setSpacing(SPACING_8)
        return toolbar, row

    def _add_table_action_row(
        self,
        root: QVBoxLayout,
        count_label: QLabel,
        *buttons: QPushButton,
        include_page_status: bool = False,
    ) -> None:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(MEAS_LIB_BUTTON_ROW_SPACING)
        row.addWidget(count_label, 0)
        if include_page_status:
            row.addSpacing(SPACING_8)
            row.addWidget(self.status_lamp, 0)
            row.addWidget(self.status_text, 0)
        row.addStretch(1)
        for button in buttons:
            row.addWidget(button, 0)
        root.addLayout(row)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._sessions: List[Dict[str, Any]] = []
        self.coord_page: Optional[Any] = None

        root = QVBoxLayout(self)
        page_margins_and_spacing(root)

        self.header_lbl = setup_compact_title_header(root, WORKFLOW_LABEL_LIBRARY)
        self.status_lamp = create_status_lamp()
        self.status_text = QLabel("就緒")
        self.status_text.setProperty("class", "statusIndicator")
        apply_status_accessibility(self.status_lamp, self.status_text, state="idle", text=self.status_text.text())
        
        self.tabs = QTabWidget()
        self.tabs.setObjectName("libraryTabs")
        self.tabs.setProperty("class", "secondaryTabs")
        root.addWidget(self.tabs)

        # ── Tab 1: 量測歷史記錄 ──
        meas_tab = QWidget()
        meas_root = QVBoxLayout(meas_tab)
        meas_root.setContentsMargins(0, SPACING_4, 0, 0)
        meas_root.setSpacing(SPACING_8)

        # 搜尋列
        search_card, row1 = self._make_search_toolbar()

        self._product_combo = QComboBox()
        self._product_combo.setMinimumWidth(MEAS_LIB_SHORT_FIELD_MIN_WIDTH)
        self._product_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        row1.addWidget(QLabel("產品"), 0)
        row1.addWidget(self._product_combo, 1)

        self._workorder_edit = QLineEdit()
        self._workorder_edit.setPlaceholderText("工單")
        self._workorder_edit.setMinimumWidth(MEAS_LIB_SHORT_FIELD_MIN_WIDTH)
        row1.addWidget(QLabel("工單"), 0)
        row1.addWidget(self._workorder_edit, 1)

        self._part_no_edit = QLineEdit()
        self._part_no_edit.setPlaceholderText("料號")
        self._part_no_edit.setMinimumWidth(MEAS_LIB_SHORT_FIELD_MIN_WIDTH)
        row1.addWidget(QLabel("料號"), 0)
        row1.addWidget(self._part_no_edit, 1)

        self._search_btn = QPushButton("搜尋")
        self._search_btn.setProperty("class", "secondary")
        self._search_btn.setToolTip("執行搜尋")
        self._search_btn.clicked.connect(self.refresh)
        row1.addWidget(self._search_btn)

        self._clear_btn = QPushButton("清除")
        self._clear_btn.setProperty("class", "secondary")
        self._clear_btn.setToolTip("清除所有篩選條件")
        self._clear_btn.clicked.connect(self._clear_filters)
        row1.addWidget(self._clear_btn)

        meas_root.addWidget(search_card)

        # 結果資料表
        self._table = QTableWidget(0, len(_COL_NAMES))
        self._table.setHorizontalHeaderLabels(_COL_NAMES)
        style_table(self._table, role="library")
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)

        self._table.itemDoubleClicked.connect(self._on_row_double_clicked)
        meas_root.addWidget(self._table, 1)

        self._count_lbl = QLabel("共 0 筆記錄")
        self._count_lbl.setProperty("class", "caption")

        # 操作按鈕列
        self._load_btn = QPushButton("載入量測檔")
        self._load_btn.setProperty("class", "primary")
        self._load_btn.setToolTip("載入選取的量測檔進行分析")
        self._load_btn.clicked.connect(self._on_load_clicked)

        self._edit_btn = QPushButton("編輯資料")
        self._edit_btn.setProperty("class", "secondary")
        self._edit_btn.setToolTip("編輯選取記錄的中繼資料")
        self._edit_btn.clicked.connect(self._on_edit_clicked)

        self._delete_btn = QPushButton("刪除記錄")
        self._delete_btn.setProperty("class", "danger")
        self._delete_btn.setToolTip("刪除選取的 DB 記錄")
        self._delete_btn.clicked.connect(self._on_delete_clicked)
        self._apply_uniform_action_button_size(
            self._load_btn,
            self._edit_btn,
            self._delete_btn,
        )
        self._add_table_action_row(
            meas_root,
            self._count_lbl,
            self._load_btn,
            self._edit_btn,
            self._delete_btn,
            include_page_status=True,
        )

        self.tabs.addTab(meas_tab, "量測歷史")

        # ── Tab 2: 座標歷史管理 ──
        coord_lib_tab = QWidget()
        coord_lib_root = QVBoxLayout(coord_lib_tab)
        coord_lib_root.setContentsMargins(0, SPACING_4, 0, 0)
        coord_lib_root.setSpacing(SPACING_8)

        # 座標搜尋列
        c_search_card, c_row1 = self._make_search_toolbar()

        self._c_product_combo = QComboBox()
        self._c_product_combo.setMinimumWidth(MEAS_LIB_SHORT_FIELD_MIN_WIDTH)
        self._c_product_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        c_row1.addWidget(QLabel("產品"), 0)
        c_row1.addWidget(self._c_product_combo, 1)

        self._c_part_no_edit = QLineEdit()
        self._c_part_no_edit.setPlaceholderText("料號")
        self._c_part_no_edit.setMinimumWidth(MEAS_LIB_SHORT_FIELD_MIN_WIDTH)
        c_row1.addWidget(QLabel("料號"), 0)
        c_row1.addWidget(self._c_part_no_edit, 1)

        self._c_search_btn = QPushButton("搜尋")
        self._c_search_btn.setProperty("class", "secondary")
        self._c_search_btn.clicked.connect(self.refresh_coordinates)
        c_row1.addWidget(self._c_search_btn)

        self._c_clear_btn = QPushButton("清除")
        self._c_clear_btn.setProperty("class", "secondary")
        self._c_clear_btn.clicked.connect(self._clear_coord_filters)
        c_row1.addWidget(self._c_clear_btn)

        coord_lib_root.addWidget(c_search_card)

        # 座標表格
        self._c_table = QTableWidget(0, len(_COORD_COL_NAMES))
        self._c_table.setHorizontalHeaderLabels(_COORD_COL_NAMES)
        style_table(self._c_table, role="library")
        c_hdr = self._c_table.horizontalHeader()
        c_hdr.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        c_hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self._c_table.itemDoubleClicked.connect(self._on_coord_load_clicked)
        coord_lib_root.addWidget(self._c_table, 1)

        self._c_count_lbl = QLabel("共 0 筆記錄")
        self._c_count_lbl.setProperty("class", "caption")

        # 操作按鈕
        self._c_load_btn = QPushButton("載入座標檔")
        self._c_load_btn.setProperty("class", "primary")
        self._c_load_btn.clicked.connect(self._on_coord_load_clicked)

        self._c_active_btn = QPushButton("設為現用版次")
        self._c_active_btn.setProperty("class", "secondary")
        self._c_active_btn.clicked.connect(self._on_coord_active_clicked)

        self._c_edit_btn = QPushButton("編輯資料")
        self._c_edit_btn.setProperty("class", "secondary")
        self._c_edit_btn.clicked.connect(self._on_coord_edit_clicked)

        self._c_delete_btn = QPushButton("刪除版次")
        self._c_delete_btn.setProperty("class", "danger")
        self._c_delete_btn.clicked.connect(self._on_coord_delete_clicked)
        self._apply_uniform_action_button_size(
            self._c_load_btn,
            self._c_active_btn,
            self._c_edit_btn,
            self._c_delete_btn,
        )
        self._add_table_action_row(
            coord_lib_root,
            self._c_count_lbl,
            self._c_load_btn,
            self._c_active_btn,
            self._c_edit_btn,
            self._c_delete_btn,
        )

        self.tabs.addTab(coord_lib_tab, "座標歷史")

        # ── Tab 3: 規格管理（合併錫膏印刷 + 鋼板厚度） ──
        spec_tab = QWidget()
        spec_root = QVBoxLayout(spec_tab)
        spec_root.setContentsMargins(0, SPACING_4, 0, 0)
        spec_root.setSpacing(SPACING_8)

        sp_search_card, sp_row1 = self._make_search_toolbar()

        self._sp_product_combo = QComboBox()
        self._sp_product_combo.setMinimumWidth(MEAS_LIB_SHORT_FIELD_MIN_WIDTH)
        self._sp_product_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sp_row1.addWidget(QLabel("產品"), 0)
        sp_row1.addWidget(self._sp_product_combo, 1)

        self._sp_part_no_edit = QLineEdit()
        self._sp_part_no_edit.setPlaceholderText("料號")
        self._sp_part_no_edit.setMinimumWidth(MEAS_LIB_SHORT_FIELD_MIN_WIDTH)
        sp_row1.addWidget(QLabel("料號"), 0)
        sp_row1.addWidget(self._sp_part_no_edit, 1)

        self._sp_search_btn = QPushButton("搜尋")
        self._sp_search_btn.setProperty("class", "secondary")
        self._sp_search_btn.clicked.connect(self.refresh_combined_specs)
        sp_row1.addWidget(self._sp_search_btn)

        self._sp_clear_btn = QPushButton("清除")
        self._sp_clear_btn.setProperty("class", "secondary")
        self._sp_clear_btn.clicked.connect(self._clear_combined_spec_filters)
        sp_row1.addWidget(self._sp_clear_btn)

        spec_root.addWidget(sp_search_card)

        self._sp_table = QTableWidget(0, len(_COMBINED_SPEC_COL_NAMES))
        self._sp_table.setHorizontalHeader(_GroupedHeaderView(_COMBINED_SPEC_GROUPS, self._sp_table))
        self._sp_table.setHorizontalHeaderLabels(_COMBINED_SPEC_COL_NAMES)
        style_table(self._sp_table, role="reference")
        sp_hdr = self._sp_table.horizontalHeader()
        sp_hdr.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        sp_hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        sp_hdr.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        self._sp_table.itemDoubleClicked.connect(self._on_combined_spec_load_clicked)
        spec_root.addWidget(self._sp_table, 1)

        self._sp_count_lbl = QLabel("共 0 筆記錄")
        self._sp_count_lbl.setProperty("class", "caption")

        self._sp_load_btn = QPushButton("選用此規格")
        self._sp_load_btn.setProperty("class", "primary")
        self._sp_load_btn.clicked.connect(self._on_combined_spec_load_clicked)

        self._sp_active_btn = QPushButton("設為現用規格")
        self._sp_active_btn.setProperty("class", "secondary")
        self._sp_active_btn.clicked.connect(self._on_combined_spec_active_clicked)

        self._sp_edit_btn = QPushButton("編輯資料")
        self._sp_edit_btn.setProperty("class", "secondary")
        self._sp_edit_btn.clicked.connect(self._on_combined_spec_edit_clicked)

        self._sp_delete_btn = QPushButton("刪除規格")
        self._sp_delete_btn.setProperty("class", "danger")
        self._sp_delete_btn.clicked.connect(self._on_combined_spec_delete_clicked)
        self._apply_uniform_action_button_size(
            self._sp_load_btn,
            self._sp_active_btn,
            self._sp_edit_btn,
            self._sp_delete_btn,
        )
        self._add_table_action_row(
            spec_root,
            self._sp_count_lbl,
            self._sp_load_btn,
            self._sp_active_btn,
            self._sp_edit_btn,
            self._sp_delete_btn,
        )

        self.tabs.addTab(spec_tab, "規格管理")

        # ── Tab 5: 供應商管理 ──
        supplier_tab = QWidget()
        supplier_root = QVBoxLayout(supplier_tab)
        supplier_root.setContentsMargins(0, SPACING_4, 0, 0)
        supplier_root.setSpacing(SPACING_8)

        sup_search_card, sup_row1 = self._make_search_toolbar()

        self._sup_code_combo = QComboBox()
        self._sup_code_combo.setMinimumWidth(MEAS_LIB_SHORT_FIELD_MIN_WIDTH)
        self._sup_code_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sup_row1.addWidget(QLabel("供應商編號"), 0)
        sup_row1.addWidget(self._sup_code_combo, 1)

        self._sup_name_edit = QLineEdit()
        self._sup_name_edit.setPlaceholderText("供應商名稱")
        self._sup_name_edit.setMinimumWidth(MEAS_LIB_SHORT_FIELD_MIN_WIDTH)
        sup_row1.addWidget(QLabel("供應商名稱"), 0)
        sup_row1.addWidget(self._sup_name_edit, 1)

        self._sup_plate_no_edit = QLineEdit()
        self._sup_plate_no_edit.setPlaceholderText("鋼板編號")
        self._sup_plate_no_edit.setMinimumWidth(MEAS_LIB_SHORT_FIELD_MIN_WIDTH)
        sup_row1.addWidget(QLabel("鋼板編號"), 0)
        sup_row1.addWidget(self._sup_plate_no_edit, 1)

        self._sup_search_btn = QPushButton("搜尋")
        self._sup_search_btn.setProperty("class", "secondary")
        self._sup_search_btn.clicked.connect(self.refresh_suppliers)
        sup_row1.addWidget(self._sup_search_btn)

        self._sup_clear_btn = QPushButton("清除")
        self._sup_clear_btn.setProperty("class", "secondary")
        self._sup_clear_btn.clicked.connect(self._clear_supplier_filters)
        sup_row1.addWidget(self._sup_clear_btn)

        supplier_root.addWidget(sup_search_card)

        self._sup_table = QTableWidget(0, len(_SUPPLIER_COL_NAMES))
        self._sup_table.setHorizontalHeaderLabels(_SUPPLIER_COL_NAMES)
        style_table(self._sup_table, role="library")
        sup_hdr = self._sup_table.horizontalHeader()
        sup_hdr.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        sup_hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._sup_table.itemDoubleClicked.connect(self._on_supplier_edit_clicked)
        supplier_root.addWidget(self._sup_table, 1)

        self._sup_count_lbl = QLabel("共 0 筆記錄")
        self._sup_count_lbl.setProperty("class", "caption")

        self._sup_add_btn = QPushButton("新增資料")
        self._sup_add_btn.setProperty("class", "primary")
        self._sup_add_btn.clicked.connect(self._on_supplier_add_clicked)

        self._sup_edit_btn = QPushButton("編輯資料")
        self._sup_edit_btn.setProperty("class", "secondary")
        self._sup_edit_btn.clicked.connect(self._on_supplier_edit_clicked)

        self._sup_delete_btn = QPushButton("刪除資料")
        self._sup_delete_btn.setProperty("class", "danger")
        self._sup_delete_btn.clicked.connect(self._on_supplier_delete_clicked)
        self._apply_uniform_action_button_size(
            self._sup_add_btn,
            self._sup_edit_btn,
            self._sup_delete_btn,
        )
        self._add_table_action_row(
            supplier_root,
            self._sup_count_lbl,
            self._sup_add_btn,
            self._sup_edit_btn,
            self._sup_delete_btn,
        )

        self.tabs.addTab(supplier_tab, "供應商管理")

        # Enter 鍵觸發搜尋
        for field in (self._workorder_edit, self._part_no_edit):
            field.returnPressed.connect(self.refresh)
        
        for field in (self._c_part_no_edit,):
            field.returnPressed.connect(self.refresh_coordinates)

        for field in (self._sp_part_no_edit,):
            field.returnPressed.connect(self.refresh_combined_specs)

        for field in (self._sup_name_edit, self._sup_plate_no_edit):
            field.returnPressed.connect(self.refresh_suppliers)

        self.refresh()
        registered_product_names = self._list_registered_product_names()
        self._refresh_coordinates_with_product_names(registered_product_names)
        self._refresh_combined_specs_with_product_names(registered_product_names)
        self.refresh_suppliers()

    def _set_status_state(self, state: str, message: str) -> None:
        """Update the page-level status lamp and semantic status text together."""
        self.status_lamp.setProperty("state", state)
        self.status_text.setText(message)
        apply_status_accessibility(self.status_lamp, self.status_text, state=state, text=message)
        self.status_lamp.style().unpolish(self.status_lamp)
        self.status_lamp.style().polish(self.status_lamp)
        self.status_text.style().unpolish(self.status_text)
        self.status_text.style().polish(self.status_text)

    def _apply_uniform_action_button_size(self, *buttons: QPushButton) -> None:
        for btn in buttons:
            btn.setFixedSize(
                MEAS_LIB_ACTION_BUTTON_MIN_WIDTH,
                MEAS_LIB_ACTION_BUTTON_MIN_HEIGHT,
            )

    @staticmethod
    def _list_registered_product_names() -> List[str]:
        return [str(r.get("product_name") or "") for r in list_registered()]

    @staticmethod
    def _reload_registered_product_combo(combo: QComboBox, names: List[str]) -> None:
        prev = combo.currentText()
        combo.blockSignals(True)
        try:
            combo.clear()
            combo.addItem("（全部產品）")
            for name in names:
                combo.addItem(name)
            idx = combo.findText(prev)
            if idx >= 0:
                combo.setCurrentIndex(idx)
        finally:
            combo.blockSignals(False)

    # ─── Public API ───────────────────────────────────────────────────────────

    def save_and_refresh(
        self,
        file_path: str,
        *,
        product_name: str = "",
        work_order_no: str = "",
        supplier_work_order_no: str = "",
        outsource_work_order_no: str = "",
        batch_no: str = "",
        product_part_no: str = "",
        row_count: Optional[int] = None,
        notes: str = "",
    ) -> int:
        """
        量測上傳後由外部（MainWindow）呼叫：儲存記錄並刷新頁面。
        """
        try:
            session_id = save_measurement_session(
                file_path,
                product_name=product_name,
                work_order_no="",
                supplier_work_order_no=supplier_work_order_no,
                outsource_work_order_no=outsource_work_order_no,
                batch_no=batch_no,
                product_part_no=product_part_no,
                row_count=row_count,
                notes=notes,
            )
        except (sqlite3.Error, OSError, ValueError, TypeError) as exc:
            _log.warning("measurement_library: save_and_refresh failed: %s", exc, exc_info=True)
            return -1
        self.refresh()
        return session_id

    def refresh(self) -> None:
        """依目前篩選條件重新查詢並填表。"""
        self._refresh_product_combo()

        # 下拉選單選取產品 → 精確比對；文字欄位 → LIKE 模糊比對
        product = ""
        product_exact = False
        if self._product_combo.currentIndex() > 0:
            product = str(self._product_combo.currentText() or "")
            product_exact = True

        sessions = list_measurement_sessions(
            product_name=product,
            product_name_exact=product_exact,
            work_order_no=self._workorder_edit.text().strip(),
            product_part_no=self._part_no_edit.text().strip(),
        )
        self._sessions = sessions
        self._populate_table(sessions)
        # 更新 header 狀態燈
        self._set_status_state("success" if sessions else "idle", "就緒" if sessions else "尚無記錄")

    def set_product_filter(self, product_name: str) -> None:
        """由外部設定產品篩選（通常在產品切換後連動）。"""
        idx = self._product_combo.findText(product_name)
        if idx >= 0:
            self._product_combo.setCurrentIndex(idx)
        self.refresh()

    # ─── Private helpers ──────────────────────────────────────────────────────

    def _refresh_product_combo(self) -> None:
        prev = self._product_combo.currentText()
        names = list_product_names_with_sessions()
        self._product_combo.blockSignals(True)
        try:
            self._product_combo.clear()
            self._product_combo.addItem("（全部產品）")
            for n in names:
                self._product_combo.addItem(n)
            idx = self._product_combo.findText(prev)
            if idx >= 0:
                self._product_combo.setCurrentIndex(idx)
        finally:
            self._product_combo.blockSignals(False)

    def _populate_table(self, sessions: List[Dict[str, Any]]) -> None:
        self._table.setRowCount(0)
        self._table.setRowCount(len(sessions))
        for row_idx, s in enumerate(sessions):
            # 上傳時間：截短為 YYYY-MM-DD HH:MM
            dt_raw = str(s.get("upload_datetime") or "")
            dt_short = dt_raw[:16].replace("T", " ") if dt_raw else "—"
            work_order_display = str(s.get("work_order_no") or "").strip()
            if not work_order_display:
                work_order_display = (
                    str(s.get("outsource_work_order_no") or "").strip()
                    or str(s.get("supplier_work_order_no") or "").strip()
                )

            row_count = s.get("row_count")
            row_count_str = str(row_count) if row_count is not None else "—"

            file_path = str(s.get("file_path") or "")
            file_display = os.path.basename(file_path) if file_path else "—"

            values = [
                str(s.get("product_name") or ""),
                work_order_display,
                str(s.get("product_part_no") or ""),
                dt_short,
                row_count_str,
                file_display,
                str(s.get("notes") or ""),
            ]
            for col, text in enumerate(values):
                item = _make_item(text)
                if col in (4, 5):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
                # 儲存原始 session dict 在第 0 欄 UserRole（供 edit/delete/load 取用）
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, s)
                # 儲存完整路徑在量測檔欄 ToolTip
                if col == 5:
                    item.setToolTip(file_path)
                self._table.setItem(row_idx, col, item)

        self._table.resizeRowsToContents()
        self._count_lbl.setText(f"共 {len(sessions)} 筆記錄")

    def _selected_session(self) -> Optional[Dict[str, Any]]:
        rows = self._table.selectedItems()
        if not rows:
            return None
        row = rows[0].row()
        item = self._table.item(row, 0)
        if item is None:
            return None
        data = item.data(Qt.ItemDataRole.UserRole)
        return data if isinstance(data, dict) else None

    def _build_measurement_context(self, session: Dict[str, Any]) -> Dict[str, Any]:
        supplier_work_order_no = str(session.get("supplier_work_order_no") or "").strip()
        outsource_work_order_no = str(session.get("outsource_work_order_no") or "").strip()
        legacy_work_order_no = str(session.get("work_order_no") or "").strip()
        if not outsource_work_order_no:
            outsource_work_order_no = legacy_work_order_no
        primary_work_order_no = outsource_work_order_no or supplier_work_order_no
        batch_no = str(session.get("batch_no") or "").strip() or primary_work_order_no
        session_id = session.get("id")
        session_id_int = int(session_id) if isinstance(session_id, (int, float, str)) and str(session_id).strip().isdigit() else -1
        return {
            "session_id": session_id_int,
            "product_name": str(session.get("product_name") or "").strip(),
            "product_part_no": str(session.get("product_part_no") or "").strip(),
            "work_order_no": "",
            "supplier_work_order_no": supplier_work_order_no,
            "outsource_work_order_no": outsource_work_order_no,
            "batch_no": batch_no,
        }

    def _clear_filters(self) -> None:
        self._product_combo.setCurrentIndex(0)
        self._workorder_edit.clear()
        self._part_no_edit.clear()
        self.refresh()

    # ─── Slots ────────────────────────────────────────────────────────────────

    def _on_row_double_clicked(self, _item) -> None:
        """雙擊直接載入量測檔。"""
        self._on_load_clicked()

    def _on_load_clicked(self) -> None:
        session = self._selected_session()
        if session is None:
            show_dark_warning(self, "請選擇記錄", "請先在清單中選取一筆量測記錄。")
            return
        path = str(session.get("file_path") or "")
        if not path:
            show_dark_warning(self, "路徑為空", "此記錄沒有有效的量測檔路徑。")
            return
        if not os.path.isfile(path):
            show_dark_warning(
                self, "找不到檔案",
                f"量測檔不存在於：\n{path}\n\n（檔案可能已被移動或刪除）"
            )
            return
        context = self._build_measurement_context(session)
        self.measurement_selected.emit(path)
        self.measurement_selected_with_context.emit(path, context)
        # 更新狀態燈
        self._set_status_state("loading", "解析中…")
        # 告知使用者載入為非同步，需切換至圖表頁查看結果
        show_dark_information(
            self,
            "已排隊載入",
            f"量測檔「{os.path.basename(path)}」已排入載入佇列。\n\n"
            f"請切換至「{WORKFLOW_LABEL_CHARTS}」頁面查看分析結果。"
        )

    def _on_edit_clicked(self) -> None:
        session = self._selected_session()
        if session is None:
            show_dark_warning(self, "請選擇記錄", "請先在清單中選取一筆量測記錄。")
            return
        dlg = _EditSessionDialog(session, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        vals = dlg.get_values()
        try:
            ok = update_measurement_session(
                int(session.get("id", 0)),
                product_name=vals["product_name"],
                work_order_no="",
                supplier_work_order_no=vals["supplier_work_order_no"],
                outsource_work_order_no=vals["outsource_work_order_no"],
                product_part_no=vals["product_part_no"],
                notes=vals["notes"],
            )
        except (sqlite3.Error, OSError, ValueError, TypeError) as exc:
            show_dark_warning(self, "更新失敗", str(exc))
            return
        if ok:
            self.refresh()
            show_dark_information(self, "已更新", "量測記錄已更新。")
        else:
            show_dark_warning(self, "未找到記錄", "找不到該記錄，可能已被刪除。")

    def _on_delete_clicked(self) -> None:
        session = self._selected_session()
        if session is None:
            show_dark_warning(self, "請選擇記錄", "請先在清單中選取一筆量測記錄。")
            return
        fname = os.path.basename(str(session.get("file_path") or "未知"))
        reply = QMessageBox.question(
            self,
            "確認刪除",
            f"確定要刪除記錄「{fname}」嗎？\n（本機量測檔案不會被刪除）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        session_id = session.get("id")
        if session_id is None:
            show_dark_warning(self, "無法刪除", "記錄缺少 ID。")
            return
        try:
            ok = delete_measurement_session(int(session_id))
        except (sqlite3.Error, OSError, ValueError, TypeError) as exc:
            show_dark_warning(self, "刪除失敗", str(exc))
            return
        if ok:
            self.refresh()
            show_dark_information(self, "已刪除", "量測記錄已從資料庫移除。")
        else:
            show_dark_warning(self, "未找到記錄", "找不到該記錄，可能已被刪除。")

    # ─── Coordinate Library Slots ─────────────────────────────────────────────

    def refresh_coordinates(self) -> None:
        """Refresh coordinate version rows using the current product selector."""
        self._refresh_coordinates_with_product_names(self._list_registered_product_names())

    def _refresh_coordinates_with_product_names(self, product_names: List[str]) -> None:
        """重新查詢並填寫座標管理表。"""
        self._reload_registered_product_combo(self._c_product_combo, product_names)

        product = ""
        product_exact = False
        if self._c_product_combo.currentIndex() > 0:
            product = self._c_product_combo.currentText()
            product_exact = True

        versions = list_coordinate_versions(
            product_name=product,
            product_name_exact=product_exact,
            product_part_no=self._c_part_no_edit.text().strip(),
        )

        self._c_table.setRowCount(0)
        self._c_table.setRowCount(len(versions))
        for i, v in enumerate(versions):
            dt = str(v.get("created_at") or "")[:16].replace("T", " ")
            active_str = "● 現用" if v.get("is_active") else "—"
            path = str(v.get("file_path") or "")
            
            items = [
                str(v.get("product_name") or ""),
                str(v.get("product_part_no") or ""),
                dt,
                active_str,
                str(v.get("row_count") or "—"),
                os.path.basename(path)
            ]
            for col, text in enumerate(items):
                it = _make_item(text)
                if col == 3: # 主要版次
                    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
                    if v.get("is_active"):
                        it.setForeground(Qt.GlobalColor.green)
                if col == 0:
                    it.setData(Qt.ItemDataRole.UserRole, v)
                if col == 5:
                    it.setToolTip(path)
                self._c_table.setItem(i, col, it)

        self._c_count_lbl.setText(f"共 {len(versions)} 筆記錄")

    def _clear_coord_filters(self) -> None:
        self._c_product_combo.setCurrentIndex(0)
        self._c_part_no_edit.clear()
        self.refresh_coordinates()

    def _selected_coord_version(self) -> Optional[Dict[str, Any]]:
        rows = self._c_table.selectedItems()
        if not rows:
            return None
        row = rows[0].row()
        item = self._c_table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_coord_load_clicked(self) -> None:
        v = self._selected_coord_version()
        if not v:
            show_dark_warning(self, "請選擇記錄", "請先在清單中選取一筆座標記錄。")
            return
        path = str(v.get("file_path") or "")
        if not os.path.isfile(path):
            show_dark_warning(self, "找不到檔案", f"檔案不存在：\n{path}")
            return
        # 觸發載入
        self.coordinate_selected.emit(path)
        show_dark_information(self, "已載入", f"座標檔「{os.path.basename(path)}」已載入。")

    def _on_coord_active_clicked(self) -> None:
        v = self._selected_coord_version()
        if not v:
            return
        if v.get("is_active"):
            show_dark_information(self, "提示", "此版本已是現用版本。")
            return
        if set_active_coordinate_version(int(v["id"])):
            self.refresh_coordinates()
            if self.coord_page:
                self.coord_page.refresh_registered_list()
            show_dark_information(self, "已更新", "已切換現用座標版本。")

    def _on_coord_edit_clicked(self) -> None:
        v = self._selected_coord_version()
        if not v:
            return
        dlg = _EditCoordinateDialog(v, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        vals = dlg.get_values()
        if update_coordinate_metadata(int(v["id"]), **vals):
            self.refresh_coordinates()
            if self.coord_page:
                self.coord_page.refresh_registered_list()
            show_dark_information(self, "已更新", "產品資訊已更新。")

    def _on_coord_delete_clicked(self) -> None:
        v = self._selected_coord_version()
        if not v:
            return
        if v.get("is_active"):
            show_dark_warning(self, "無法刪除", "現用版本無法刪除，請先將其他版本設為現用。")
            return
        reply = QMessageBox.question(
            self, "確認刪除", f"確定要刪除座標記錄「{os.path.basename(str(v['file_path']))}」嗎？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes and delete_coordinate_version(int(v["id"])):
            self.refresh_coordinates()
            show_dark_information(self, "已刪除", "版本記錄已移除。")

    # ─── Combined Spec (paste + stencil) Slots ────────────────────────────────

    def refresh_specs(self) -> None:
        """相容入口：導向合併規格刷新。"""
        self.refresh_combined_specs()

    def refresh_combined_specs(self) -> None:
        """Refresh combined spec rows using the current product selector."""
        self._refresh_combined_specs_with_product_names(self._list_registered_product_names())

    def _refresh_combined_specs_with_product_names(self, product_names: List[str]) -> None:
        """重新查詢並填寫合併後的規格管理表。"""
        self._reload_registered_product_combo(self._sp_product_combo, product_names)

        product = ""
        product_exact = False
        if self._sp_product_combo.currentIndex() > 0:
            product = self._sp_product_combo.currentText()
            product_exact = True

        part_no = self._sp_part_no_edit.text().strip()
        paste_versions = list_paste_printing_spec_versions(
            product_name=product,
            product_name_exact=product_exact,
            product_part_no=part_no,
        )
        stencil_versions = list_stencil_thickness_versions(
            product_name=product,
            product_name_exact=product_exact,
            product_part_no=part_no,
        )
        # Restrict to ACTIVE versions per side — the merged tab is per-product,
        # not per-version. Old inactive versions stay in DB for audit only.
        active_paste = [v for v in paste_versions if v.get("is_active")]
        active_stencil = [v for v in stencil_versions if v.get("is_active")]
        joined = _join_active_specs(active_paste, active_stencil)

        self._sp_table.setRowCount(0)
        self._sp_table.setRowCount(len(joined))
        for i, row in enumerate(joined):
            self._populate_combined_row(i, row)
        self._sp_count_lbl.setText(f"共 {len(joined)} 筆記錄")

    def _populate_combined_row(self, row_idx: int, row: Dict[str, Any]) -> None:
        paste = row.get("paste") or {}
        stencil = row.get("stencil") or {}
        product_name = str(row.get("product_name") or "")
        product_part_no = str(row.get("product_part_no") or "")

        # Paste columns (2–4)
        if paste:
            vol_text = (
                f"{(paste.get('default_volume_lsl') or 0.0):.1f}/"
                f"{(paste.get('default_volume_target') or 0.0):.1f}/"
                f"{(paste.get('default_volume_usl') or 0.0):.1f}"
            )
            area_text = (
                f"{(paste.get('default_area_lsl') or 0.0):.1f}/"
                f"{(paste.get('default_area_target') or 0.0):.1f}/"
                f"{(paste.get('default_area_usl') or 0.0):.1f}"
            )
            h_text = (
                f"{(paste.get('default_height_lsl') or 0.0):.1f}/"
                f"{(paste.get('default_height_usl') or 0.0):.1f}"
            )
        else:
            vol_text = area_text = h_text = "未建立"

        # Stencil columns (5–9)
        if stencil:
            stencil_type_text = str(stencil.get("stencil_type") or "—")
            thickness_main_text = f"{(stencil.get('thickness_main') or 0.0):.3f}"
            if stencil.get("thickness_precision") is not None:
                precision_text = f"{(stencil.get('thickness_precision') or 0.0):.3f}"
            else:
                precision_text = "—"
            unit_mode_text = str(stencil.get("unit_mode") or UNIT_MODE_PERCENT)
            denominator_text = f"{(stencil.get('height_denominator_mm') or 0.0):.3f}"
        else:
            stencil_type_text = thickness_main_text = precision_text = "未建立"
            unit_mode_text = denominator_text = "未建立"

        # Status columns (10–11): updated_at = later of the two; lamp = full/partial
        paste_updated = str(paste.get("updated_at") or "") if paste else ""
        stencil_updated = str(stencil.get("updated_at") or "") if stencil else ""
        latest = max(paste_updated, stencil_updated)
        dt_text = latest[:16].replace("T", " ") if latest else "—"

        if paste and stencil:
            active_glyph = "●"
            active_text = f"{active_glyph} 現用"
            active_color = QColor(STATUS_LAMP_SUCCESS)
        elif paste or stencil:
            active_glyph = "◐"
            missing = "鋼板" if paste else "錫膏"
            active_text = f"{active_glyph} 缺{missing}"
            active_color = QColor(STATUS_LAMP_WARNING)
        else:
            active_text = "—"
            active_color = None

        values = [
            product_name,
            product_part_no,
            vol_text,
            area_text,
            h_text,
            stencil_type_text,
            thickness_main_text,
            precision_text,
            unit_mode_text,
            denominator_text,
            dt_text,
            active_text,
        ]
        muted_paste = not paste
        muted_stencil = not stencil
        for col, text in enumerate(values):
            it = _make_item(text)
            if col in (2, 3, 4) and muted_paste:
                it.setForeground(QColor(TEXT_DISABLED))
            if col in (5, 6, 7, 8, 9) and muted_stencil:
                it.setForeground(QColor(TEXT_DISABLED))
            if col == 11:
                it.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
                if active_color is not None:
                    it.setForeground(active_color)
            if col == 10 and paste_updated and stencil_updated and paste_updated != stencil_updated:
                it.setToolTip(f"錫膏 更新：{paste_updated}\n鋼板 更新：{stencil_updated}")
            if col == 0:
                it.setData(Qt.ItemDataRole.UserRole, row)
            self._sp_table.setItem(row_idx, col, it)

    def _clear_combined_spec_filters(self) -> None:
        self._sp_product_combo.setCurrentIndex(0)
        self._sp_part_no_edit.clear()
        self.refresh_combined_specs()

    def _selected_combined_spec_row(self) -> Optional[Dict[str, Any]]:
        rows = self._sp_table.selectedItems()
        if not rows:
            return None
        row = rows[0].row()
        item = self._sp_table.item(row, 0)
        if item is None:
            return None
        data = item.data(Qt.ItemDataRole.UserRole)
        return data if isinstance(data, dict) else None

    def _on_combined_spec_load_clicked(self) -> None:
        row = self._selected_combined_spec_row()
        if not row:
            show_dark_warning(self, "請選擇記錄", "請先在清單中選取一筆規格記錄。")
            return
        product_name = str(row.get("product_name") or "")
        if not product_name:
            show_dark_warning(self, "資料錯誤", "選取的記錄缺少產品名稱。")
            return
        if not row.get("paste") or not row.get("stencil"):
            show_dark_warning(
                self,
                "規格不完整",
                f"產品「{product_name}」尚未同時建立錫膏印刷規格與鋼板厚度規格，無法選用。",
            )
            return
        self.spec_selected.emit(product_name)
        show_dark_information(self, "已選用", f"產品「{product_name}」的規格已載入。")

    def _on_combined_spec_active_clicked(self) -> None:
        row = self._selected_combined_spec_row()
        if not row:
            return
        paste = row.get("paste") or {}
        stencil = row.get("stencil") or {}
        if paste and stencil and paste.get("is_active") and stencil.get("is_active"):
            show_dark_information(self, "提示", "錫膏與鋼板規格皆已是現用版本。")
            return

        ok_paste = True
        ok_stencil = True
        if paste and not paste.get("is_active") and paste.get("id") is not None:
            ok_paste = set_active_paste_printing_spec_version(int(paste["id"]))
        if stencil and not stencil.get("is_active") and stencil.get("id") is not None:
            ok_stencil = set_active_stencil_thickness_version(int(stencil["id"]))
        self.refresh_combined_specs()
        if hasattr(self, "coord_page") and self.coord_page:
            self.coord_page.refresh_registered_list()
        if ok_paste and ok_stencil:
            show_dark_information(self, "已更新", "已將該產品的規格設為現用版本。")
        else:
            show_dark_warning(
                self,
                "部分更新失敗",
                "其中一側規格切換現用失敗，請檢查資料庫狀態。",
            )

    def _on_combined_spec_edit_clicked(self) -> None:
        row = self._selected_combined_spec_row()
        if not row:
            return
        dlg = _EditCombinedSpecDialog(row, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            vals = dlg.get_values()
        except ValueError as exc:
            show_dark_warning(self, "輸入錯誤", str(exc))
            return

        # Detect product_name / product_part_no rename. Registry save() routes
        # through upsert_product which keys on product_name_ci and drops empty
        # part_no — so renaming via save() alone would create a NEW product row
        # and silently lose part_no edits. Rename the products row in place via
        # update_*_metadata() (against any existing version_id) BEFORE save().
        old_name = str(row.get("product_name") or "")
        old_part_no = str(row.get("product_part_no") or "")
        new_name = str(vals["paste"].get("product_name") or "")
        new_part_no = str(vals["paste"].get("product_part_no") or "")
        rename_kwargs: Dict[str, Any] = {}
        if new_name and new_name != old_name:
            rename_kwargs["product_name"] = new_name
        if new_part_no != old_part_no:
            rename_kwargs["product_part_no"] = new_part_no
        if rename_kwargs:
            paste_existing = row.get("paste") or {}
            stencil_existing = row.get("stencil") or {}
            ref_id: Optional[int] = None
            ref_kind: Optional[str] = None
            if paste_existing.get("id") is not None:
                ref_id = int(paste_existing["id"])
                ref_kind = "paste"
            elif stencil_existing.get("id") is not None:
                ref_id = int(stencil_existing["id"])
                ref_kind = "stencil"
            if ref_id is not None:
                try:
                    if ref_kind == "paste":
                        update_paste_printing_spec_metadata(ref_id, **rename_kwargs)
                    else:
                        update_stencil_thickness_metadata(ref_id, **rename_kwargs)
                except (sqlite3.Error, OSError, ValueError, TypeError) as exc:
                    show_dark_warning(self, "重新命名失敗", str(exc))
                    self.refresh_combined_specs()
                    return

        paste_payload = vals["paste"]
        stencil_payload = vals["stencil"]
        try:
            paste_ok = save_paste_printing_spec(paste_payload)
            stencil_ok = save_stencil_thickness_spec(stencil_payload)
        except (sqlite3.Error, OSError, ValueError, TypeError) as exc:
            show_dark_warning(self, "更新失敗", str(exc))
            self.refresh_combined_specs()
            return
        self.refresh_combined_specs()
        if paste_ok and stencil_ok:
            show_dark_information(self, "已更新", "錫膏與鋼板規格已寫入新版本並設為現用。")
        else:
            show_dark_warning(
                self,
                "部分寫入失敗",
                f"錫膏寫入：{'成功' if paste_ok else '失敗'}；鋼板寫入：{'成功' if stencil_ok else '失敗'}",
            )

    def _on_combined_spec_delete_clicked(self) -> None:
        row = self._selected_combined_spec_row()
        if not row:
            return
        paste = row.get("paste") or {}
        stencil = row.get("stencil") or {}
        product_name = str(row.get("product_name") or "")
        if (paste and paste.get("is_active")) or (stencil and stencil.get("is_active")):
            show_dark_warning(
                self,
                "無法刪除",
                "顯示的規格為現用版本，無法刪除。請先建立並切換至其他版本後再試。",
            )
            return
        reply = QMessageBox.question(
            self,
            "確認刪除",
            f"確定要刪除產品「{product_name}」的此筆規格記錄嗎？\n（同時移除錫膏與鋼板兩側）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        deleted_any = False
        if paste and paste.get("id") is not None:
            deleted_any |= delete_paste_printing_spec_version(int(paste["id"]))
        if stencil and stencil.get("id") is not None:
            deleted_any |= delete_stencil_thickness_version(int(stencil["id"]))
        self.refresh_combined_specs()
        if deleted_any:
            show_dark_information(self, "已刪除", "規格記錄已移除。")
        else:
            show_dark_warning(self, "未找到記錄", "找不到該記錄，可能已被刪除。")

    # ─── Supplier Library Slots ──────────────────────────────────────────────

    def refresh_suppliers(self) -> None:
        """重新查詢並填寫供應商管理表。"""
        prev = self._sup_code_combo.currentText()
        try:
            codes = list_supplier_codes()
            self._sup_code_combo.blockSignals(True)
            try:
                self._sup_code_combo.clear()
                self._sup_code_combo.addItem("（全部供應商）")
                for code in codes:
                    self._sup_code_combo.addItem(code)
                idx = self._sup_code_combo.findText(prev)
                if idx >= 0:
                    self._sup_code_combo.setCurrentIndex(idx)
            finally:
                self._sup_code_combo.blockSignals(False)

            supplier_code = ""
            if self._sup_code_combo.currentIndex() > 0:
                supplier_code = self._sup_code_combo.currentText().strip()

            rows = list_supplier_records(
                supplier_code=supplier_code,
                supplier_name=self._sup_name_edit.text().strip(),
                steel_plate_no=self._sup_plate_no_edit.text().strip(),
            )
        except SupplierCodeMigrationConflictError as exc:
            self._sup_code_combo.blockSignals(True)
            try:
                self._sup_code_combo.clear()
                self._sup_code_combo.addItem("（全部供應商）")
            finally:
                self._sup_code_combo.blockSignals(False)
            self._sup_table.setRowCount(0)
            self._sup_count_lbl.setText("共 0 筆記錄")
            show_dark_warning(self, "供應商資料衝突", str(exc))
            return
        except (sqlite3.Error, ValueError) as exc:
            self._sup_code_combo.blockSignals(True)
            try:
                self._sup_code_combo.clear()
                self._sup_code_combo.addItem("（全部供應商）")
            finally:
                self._sup_code_combo.blockSignals(False)
            self._sup_table.setRowCount(0)
            self._sup_count_lbl.setText("共 0 筆記錄")
            show_dark_warning(self, "載入失敗", str(exc))
            return

        self._sup_table.setRowCount(0)
        self._sup_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            updated_at = str(row.get("updated_at") or "")[:16].replace("T", " ")
            items = [
                str(row.get("supplier_code") or ""),
                str(row.get("supplier_name") or ""),
                str(row.get("steel_plate_no") or ""),
                str(row.get("steel_plate_production_date") or ""),
                updated_at,
            ]
            for col, text in enumerate(items):
                it = _make_item(text)
                if col == 0:
                    it.setData(Qt.ItemDataRole.UserRole, row)
                if col in (3, 4):
                    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
                self._sup_table.setItem(i, col, it)
        self._sup_count_lbl.setText(f"共 {len(rows)} 筆記錄")

    def _clear_supplier_filters(self) -> None:
        self._sup_code_combo.setCurrentIndex(0)
        self._sup_name_edit.clear()
        self._sup_plate_no_edit.clear()
        self.refresh_suppliers()

    def _selected_supplier_record(self) -> Optional[Dict[str, Any]]:
        rows = self._sup_table.selectedItems()
        if not rows:
            return None
        row = rows[0].row()
        item = self._sup_table.item(row, 0)
        if item is None:
            return None
        data = item.data(Qt.ItemDataRole.UserRole)
        return data if isinstance(data, dict) else None

    def _on_supplier_add_clicked(self, _item=None) -> None:
        dlg = _EditSupplierDialog(parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            vals = dlg.get_values()
            create_supplier_record(**vals)
        except (sqlite3.Error, ValueError) as exc:
            show_dark_warning(self, "新增失敗", str(exc))
            return
        self.refresh_suppliers()
        show_dark_information(self, "已新增", "供應商資料已新增。")

    def _on_supplier_edit_clicked(self, _item=None) -> None:
        record = self._selected_supplier_record()
        if not record:
            show_dark_warning(self, "請選擇記錄", "請先在清單中選取一筆供應商資料。")
            return
        dlg = _EditSupplierDialog(record, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            vals = dlg.get_values()
            ok = update_supplier_record(int(record.get("id", 0)), **vals)
        except (sqlite3.Error, ValueError) as exc:
            show_dark_warning(self, "更新失敗", str(exc))
            return
        if ok:
            self.refresh_suppliers()
            show_dark_information(self, "已更新", "供應商資料已更新。")
        else:
            show_dark_warning(self, "未找到記錄", "找不到該記錄，可能已被刪除。")

    def _on_supplier_delete_clicked(self) -> None:
        record = self._selected_supplier_record()
        if not record:
            show_dark_warning(self, "請選擇記錄", "請先在清單中選取一筆供應商資料。")
            return
        reply = QMessageBox.question(
            self,
            "確認刪除",
            (
                f"確定要刪除供應商「{record.get('supplier_code')} / {record.get('supplier_name')}」"
                f"的鋼板「{record.get('steel_plate_no')}」資料嗎？"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            ok = delete_supplier_record(int(record.get("id", 0)))
        except (sqlite3.Error, ValueError) as exc:
            show_dark_warning(self, "刪除失敗", str(exc))
            return
        if ok:
            self.refresh_suppliers()
            show_dark_information(self, "已刪除", "供應商資料已移除。")
        else:
            show_dark_warning(self, "未找到記錄", "找不到該記錄，可能已被刪除。")
