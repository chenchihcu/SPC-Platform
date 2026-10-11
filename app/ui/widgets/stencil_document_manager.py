"""Searchable stencil document version manager for the specification library."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.data.coordinate_registry import list_registered
from app.data.stencil_document_library import (
    deactivate_stencil_document_version,
    delete_inactive_stencil_document_versions,
    get_stencil_document_version,
    list_stencil_document_versions,
    list_stencil_pad_nominals,
    set_active_stencil_document_version,
)
from app.ui.dialogs.stencil_document_import_dialog import StencilDocumentImportDialog
from app.ui.theme import show_dark_information, show_dark_warning
from app.ui.theme.layout_policy import fit_top_level_to_available
from app.ui.widgets.page_templates import (
    bind_table_delete_shortcut,
    confirm_action,
    confirm_double_delete,
)
from app.ui.theme.tokens import (
    DIALOG_MIN_HEIGHT_STANDARD,
    DIALOG_MIN_WIDTH_WIDE,
    DIALOG_STENCIL_PREVIEW_INIT_HEIGHT,
    DIALOG_STENCIL_PREVIEW_INIT_WIDTH,
    SPACING_8,
    SPACING_12,
)


class StencilDocumentManager(QWidget):
    versions_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(SPACING_8)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(SPACING_8)
        toolbar.addWidget(QLabel("載入產品 *"))
        self.product_combo = QComboBox()
        self.product_combo.setToolTip("選擇新開窗文件要歸屬的產品；不會改變下方清單。")
        self.product_combo.currentIndexChanged.connect(self._sync_actions)
        toolbar.addWidget(self.product_combo, 1)
        toolbar.addWidget(QLabel("Side"))
        self.side_combo = QComboBox()
        self.side_combo.addItem("全部", "")
        self.side_combo.addItem("Top", "TOP")
        self.side_combo.addItem("Bottom", "BOTTOM")
        self.side_combo.currentIndexChanged.connect(self.refresh)
        toolbar.addWidget(self.side_combo)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜尋鋼板編號 / Revision")
        self.search_edit.textChanged.connect(self.refresh)
        toolbar.addWidget(self.search_edit, 1)
        self.import_button = QPushButton("載入開窗文件")
        self.import_button.setProperty("class", "primary")
        self.import_button.setShortcut(QKeySequence.StandardKey.New)
        self.import_button.setToolTip("載入開窗文件 (Ctrl+N)；請先選擇產品")
        self.import_button.clicked.connect(self._open_import)
        toolbar.addWidget(self.import_button)
        root.addLayout(toolbar)

        self.status_label = QLabel("EMPTY：尚無開窗文件版本")
        self.status_label.setProperty("class", "statusIndicator")
        root.addWidget(self.status_label)

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            ["ID", "產品", "鋼板編號", "Revision", "Side", "狀態", "覆蓋率", "Pad 數", "建立時間"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.itemDoubleClicked.connect(self._preview)
        self.table.itemSelectionChanged.connect(self._sync_actions)
        root.addWidget(self.table, 1)

        actions = QHBoxLayout()
        actions.setSpacing(SPACING_8)
        self.count_label = QLabel("共 0 筆")
        self.count_label.setProperty("class", "caption")
        actions.addWidget(self.count_label)
        self.selection_label = QLabel("未選取")
        self.selection_label.setProperty("class", "caption")
        actions.addWidget(self.selection_label)
        actions.addStretch(1)
        self.preview_button = QPushButton("預覽")
        self.activate_button = QPushButton("設為現用")
        self.deactivate_button = QPushButton("停用回到 Raw")
        self.delete_button = QPushButton("刪除已選非現用版本")
        self.preview_button.setProperty("class", "secondary")
        self.activate_button.setProperty("class", "secondary")
        self.deactivate_button.setProperty("class", "secondary")
        self.delete_button.setProperty("class", "danger")
        self.preview_button.setShortcut(QKeySequence(Qt.Key.Key_Return))
        self.preview_button.setToolTip("預覽選取版本 (Enter)")
        self.delete_button.setToolTip("刪除已選的非現用版本 (Delete；需兩次確認)")
        self.preview_button.clicked.connect(self._preview)
        self.activate_button.clicked.connect(self._activate)
        self.deactivate_button.clicked.connect(self._deactivate)
        self.delete_button.clicked.connect(self._delete)
        for button in (
            self.preview_button,
            self.activate_button,
            self.deactivate_button,
            self.delete_button,
        ):
            actions.addWidget(button)
        root.addLayout(actions)
        bind_table_delete_shortcut(self.table, self.delete_button, can_delete=self._can_delete_selected_versions)

        self._populate_products()
        self.refresh()

    def _populate_products(self) -> None:
        current = self.product_combo.currentText().strip()
        products = {
            str(item.get("product_name") or "").strip()
            for item in list_registered()
            if str(item.get("product_name") or "").strip()
        }
        products.update(
            str(item.get("product_name") or "").strip()
            for item in list_stencil_document_versions()
            if str(item.get("product_name") or "").strip()
        )
        self.product_combo.blockSignals(True)
        self.product_combo.clear()
        self.product_combo.addItem("請選擇產品…", "")
        for product in sorted(products, key=str.casefold):
            self.product_combo.addItem(product, product)
        if current:
            index = self.product_combo.findText(current)
            if index >= 0:
                self.product_combo.setCurrentIndex(index)
        self.product_combo.blockSignals(False)

    def set_product_name(self, product_name: str) -> None:
        """Select a product and refresh its document history."""
        self._populate_products()
        index = self.product_combo.findText((product_name or "").strip())
        if index >= 0:
            self.product_combo.setCurrentIndex(index)
        elif product_name:
            self.product_combo.setEditText(product_name)
        self.refresh()

    def refresh(self, *_args: Any) -> None:
        """Reload version rows for side/search filters without changing import product."""
        side = str(self.side_combo.currentData() or "")
        search = self.search_edit.text().strip().casefold()
        rows = list_stencil_document_versions(side=side)
        if search:
            rows = [
                row
                for row in rows
                if search
                in " ".join(
                    [
                        str(row.get("product_name") or ""),
                        str(row.get("stencil_no") or ""),
                        str(row.get("revision") or ""),
                    ]
                ).casefold()
            ]
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            validation = row.get("validation_summary") or {}
            coverage = float(validation.get("coverage") or 0.0) * 100.0
            values = [
                str(row.get("id") or ""),
                str(row.get("product_name") or ""),
                str(row.get("stencil_no") or ""),
                str(row.get("revision") or ""),
                str(row.get("side") or ""),
                "ACTIVE" if int(row.get("is_active") or 0) else "INACTIVE",
                f"{coverage:.2f}%",
                str(row.get("nominal_count") or 0),
                str(row.get("created_at") or ""),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, int(row["id"]))
                self.table.setItem(row_index, column, item)
        self.count_label.setText(f"共 {len(rows)} 筆")
        if not rows:
            self.status_label.setText("EMPTY：目前篩選條件沒有開窗文件版本")
        elif any(int(row.get("is_active") or 0) for row in rows):
            self.status_label.setText("SUCCESS：已有現用開窗版本；分析仍依 Side 與覆蓋率判定")
        else:
            self.status_label.setText("WARNING：有版本但目前沒有現用版本，分析維持 Raw / VERIFY")
        self._sync_actions()

    def _selected_version_ids(self) -> list[int]:
        """Return unique IDs represented by the selected table rows."""
        ids: list[int] = []
        for model_index in self.table.selectionModel().selectedRows():
            item = self.table.item(model_index.row(), 0)
            if item is not None:
                ids.append(int(item.data(Qt.ItemDataRole.UserRole)))
        return sorted(set(ids))

    def _selected_version_id(self) -> int | None:
        """Return one selected version ID, otherwise show a safe selection prompt."""
        ids = self._selected_version_ids()
        if len(ids) != 1:
            return None
        return ids[0]

    def _sync_actions(self, *_args: Any) -> None:
        """Keep buttons and keyboard actions aligned with the current selection."""
        ids = self._selected_version_ids() if self.table.selectionModel() else []
        selected_count = len(ids)
        self.selection_label.setText(f"已選 {selected_count} 筆" if selected_count else "未選取")
        self.import_button.setEnabled(bool(self.product_combo.currentData()))
        self.preview_button.setEnabled(selected_count == 1)
        self.activate_button.setEnabled(selected_count == 1)
        self.deactivate_button.setEnabled(selected_count == 1)
        self.delete_button.setEnabled(self._can_delete_selected_versions())

    def _can_delete_selected_versions(self) -> bool:
        """Return whether every selected document version is safe to delete."""
        ids = self._selected_version_ids() if self.table.selectionModel() else []
        selected_states: list[str] = []
        if self.table.selectionModel():
            for index in self.table.selectionModel().selectedRows():
                status_item = self.table.item(index.row(), 5)
                if status_item is not None:
                    selected_states.append(status_item.text())
        return bool(ids) and all(state == "INACTIVE" for state in selected_states)

    def _open_import(self) -> None:
        product = str(self.product_combo.currentData() or "").strip()
        if not product:
            show_dark_warning(self, "請選擇產品", "載入前請先選擇單一產品。")
            return
        dialog = StencilDocumentImportDialog(product, self)
        dialog.version_created.connect(lambda _version_id: self._after_change())
        dialog.exec()

    def _after_change(self) -> None:
        self._populate_products()
        self.refresh()
        self.versions_changed.emit()

    def _preview(self, *_args: Any) -> None:
        version_id = self._selected_version_id()
        if version_id is None:
            show_dark_warning(self, "尚未選取", "請選擇一筆開窗版本。")
            return
        version = get_stencil_document_version(version_id)
        if not version:
            show_dark_warning(self, "版本不存在", "資料可能已由其他操作更新。")
            self.refresh()
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(f"開窗版本預覽｜{version['product_name']} Rev {version['revision']}")
        dialog.setMinimumSize(DIALOG_MIN_WIDTH_WIDE, DIALOG_MIN_HEIGHT_STANDARD)
        root = QVBoxLayout(dialog)
        root.setContentsMargins(SPACING_12, SPACING_12, SPACING_12, SPACING_12)
        validation = version.get("validation_summary") or {}
        transform = version.get("coordinate_transform") or {}
        details = QLabel(
            f"鋼板：{version.get('stencil_no') or '—'}｜Side：{version['side']}｜"
            f"狀態：{'ACTIVE' if version['is_active'] else 'INACTIVE'}\n"
            f"Gerber：{version['gerber_path']}\nPad CSV：{version['pad_csv_path']}\n"
            f"SHA-256：{str(version['gerber_sha256'])[:16]}… / {str(version['pad_csv_sha256'])[:16]}…\n"
            f"Transform：{transform}\n"
            f"Coverage：{int(validation.get('matched_pads') or 0)}/"
            f"{int(validation.get('total_pads') or 0)}；Parser：{version['parser_version']}"
        )
        details.setWordWrap(True)
        details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        root.addWidget(details)
        nominals = list_stencil_pad_nominals(version_id)
        table = QTableWidget(len(nominals), 8)
        table.setHorizontalHeaderLabels(
            ["RefDes", "Pad", "Side", "Windows", "Area mm²", "Thickness mm", "Volume mm³", "狀態"]
        )
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        for row_index, nominal in enumerate(nominals):
            values = [
                nominal.get("refdes"),
                nominal.get("pad"),
                nominal.get("side"),
                nominal.get("opening_count"),
                nominal.get("nominal_area_mm2"),
                nominal.get("resolved_thickness_mm"),
                nominal.get("nominal_volume_mm3"),
                nominal.get("match_status"),
            ]
            for column, value in enumerate(values):
                table.setItem(row_index, column, QTableWidgetItem(str(value if value is not None else "—")))
        root.addWidget(table, 1)
        close_button = QPushButton("關閉")
        close_button.clicked.connect(dialog.accept)
        root.addWidget(close_button, 0, Qt.AlignmentFlag.AlignRight)
        fit_top_level_to_available(
            dialog,
            preferred_size=(
                DIALOG_STENCIL_PREVIEW_INIT_WIDTH,
                DIALOG_STENCIL_PREVIEW_INIT_HEIGHT,
            ),
            fallback_size=(
                DIALOG_STENCIL_PREVIEW_INIT_WIDTH,
                DIALOG_STENCIL_PREVIEW_INIT_HEIGHT,
            ),
        )
        dialog.exec()

    def _activate(self) -> None:
        version_id = self._selected_version_id()
        if version_id is None:
            show_dark_warning(self, "尚未選取", "請選擇要啟用的版本。")
            return
        if not confirm_action(
            self,
            "確認切換現用開窗版本",
            "啟用後，後續分析會依此版本與 Side 計算百分比。是否繼續？",
        ):
            return
        try:
            changed = set_active_stencil_document_version(version_id)
        except ValueError as exc:
            show_dark_warning(self, "版本不可啟用", str(exc))
            return
        if changed:
            show_dark_information(self, "已啟用", "現用開窗版本已切換。")
            self._after_change()

    def _deactivate(self) -> None:
        version_id = self._selected_version_id()
        if version_id is None:
            show_dark_warning(self, "尚未選取", "請選擇要停用的版本。")
            return
        if confirm_action(
            self,
            "停用開窗版本",
            "停用後將回到 Raw 趨勢分析，規格型統計會顯示 VERIFY。是否繼續？",
        ) and deactivate_stencil_document_version(version_id):
            self._after_change()

    def _delete(self) -> None:
        version_ids = self._selected_version_ids()
        if not version_ids:
            show_dark_warning(self, "尚未選取", "請選擇要刪除的非現用版本。")
            return
        selected_versions = [
            get_stencil_document_version(version_id) for version_id in version_ids
        ]
        active_ids = [
            version_id
            for version_id, version in zip(version_ids, selected_versions)
            if version is None or int(version.get("is_active") or 0)
        ]
        if active_ids:
            show_dark_warning(self, "不可刪除", "現用或已不存在的版本不能刪除；請只選取非現用版本。")
            return
        # Data Deletion Safety (AGENTS.md): both prompts must be confirmed.
        if not confirm_double_delete(
            self,
            f"即將刪除 {len(version_ids)} 筆非現用版本及其受管檔案。是否繼續？",
            first_title="刪除開窗版本（1/2）",
            second_message=f"再次確認：將刪除 {len(version_ids)} 筆，且動作無法復原。",
            second_title="刪除開窗版本（2/2）",
        ):
            return
        try:
            deleted_ids = delete_inactive_stencil_document_versions(version_ids)
        except ValueError as exc:
            show_dark_warning(self, "不可刪除", str(exc))
            return
        if deleted_ids:
            show_dark_information(self, "已刪除", f"已刪除 {len(deleted_ids)} 筆非現用開窗版本。")
            self._after_change()
