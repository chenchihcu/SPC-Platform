"""Four-step multi-format stencil aperture + Pad CSV import wizard."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QColor, QBrush, QPen, QPolygonF
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.data.stencil_document_library import (
    activation_blockers,
    create_stencil_document_version,
)
from app.services.stencil_aperture_loader import (
    ApertureLoadResult,
    load_aperture_source,
)
from app.services.stencil_document_service import (
    PARSER_VERSION,
    ImportAnalysis,
    PadDefinition,
    analyze_stencil_import,
    load_pad_csv,
)
from app.ui.theme import show_dark_information, show_dark_warning
from app.ui.theme.layout_policy import fit_top_level_to_available
from app.ui.theme.tokens import (
    DIALOG_MIN_HEIGHT_STANDARD,
    DIALOG_MIN_WIDTH_WIDE,
    DIALOG_STENCIL_IMPORT_INIT_HEIGHT,
    DIALOG_STENCIL_IMPORT_INIT_WIDTH,
    SPACING_4,
    SPACING_8,
    SPACING_12,
    SPACING_16,
    STENCIL_PREVIEW_COSMETIC_PEN_WIDTH,
    STENCIL_PREVIEW_OPENING_ALPHA,
    STENCIL_PREVIEW_OPENING_OUTLINE,
    STENCIL_PREVIEW_PAD_OUTLINE,
)


class StencilDocumentImportDialog(QDialog):
    version_created = Signal(int)

    def __init__(self, product_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.product_name = (product_name or "").strip()
        self.setWindowTitle("載入鋼板開窗文件")
        self.setMinimumSize(DIALOG_MIN_WIDTH_WIDE, DIALOG_MIN_HEIGHT_STANDARD)
        self._pads: list[PadDefinition] = []
        self._openings: list[Any] = []
        self._analysis: ImportAnalysis | None = None
        self._aperture_result: ApertureLoadResult | None = None
        self._aperture_cache_key: tuple[str, str, str] | None = None
        self._match_cache_key: tuple[str, str, str, str, str] | None = None
        self._non_component_indexes: set[int] = set()

        root = QVBoxLayout(self)
        root.setContentsMargins(SPACING_16, SPACING_16, SPACING_16, SPACING_16)
        root.setSpacing(SPACING_12)
        self.step_label = QLabel()
        self.step_label.setProperty("class", "stepTitle")
        root.addWidget(self.step_label)

        self.pages = QStackedWidget()
        root.addWidget(self.pages, 1)
        self.pages.addWidget(self._build_file_page())
        self.pages.addWidget(self._build_mapping_page())
        self.pages.addWidget(self._build_overlay_page())
        self.pages.addWidget(self._build_summary_page())

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.back_button = QPushButton("上一步")
        self.back_button.setProperty("class", "secondary")
        self.back_button.clicked.connect(self._back)
        self.next_button = QPushButton("下一步")
        self.next_button.setProperty("class", "primary")
        self.next_button.clicked.connect(self._next)
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setProperty("class", "secondary")
        self.cancel_button.clicked.connect(self.reject)
        actions.addWidget(self.back_button)
        actions.addWidget(self.next_button)
        actions.addWidget(self.cancel_button)
        root.addLayout(actions)
        self.pages.currentChanged.connect(self._sync_step)
        self._sync_step(0)
        fit_top_level_to_available(
            self,
            preferred_size=(
                DIALOG_STENCIL_IMPORT_INIT_WIDTH,
                DIALOG_STENCIL_IMPORT_INIT_HEIGHT,
            ),
            fallback_size=(
                DIALOG_STENCIL_IMPORT_INIT_WIDTH,
                DIALOG_STENCIL_IMPORT_INIT_HEIGHT,
            ),
        )

    def _build_file_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(SPACING_12)
        intro = QLabel(
            f"產品：{self.product_name or '未指定'}。來源檔會複製到受管資料夾，原檔移動後仍可重播。"
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        form = QFormLayout()
        form.setSpacing(SPACING_8)
        self.stencil_no_edit = QLineEdit()
        self.stencil_no_edit.setPlaceholderText("例如 ST-VS80-001")
        self.revision_edit = QLineEdit()
        self.revision_edit.setPlaceholderText("例如 A")
        self.side_combo = QComboBox()
        self.side_combo.addItem("Top", "TOP")
        self.side_combo.addItem("Bottom", "BOTTOM")
        self.aperture_edit = QLineEdit()
        self.aperture_edit.setReadOnly(True)
        self.aperture_edit.setAccessibleName("鋼板開窗幾何文件")
        # Retain the old widget attribute for test/plugin compatibility.
        self.gerber_edit = self.aperture_edit
        self.csv_edit = QLineEdit()
        self.csv_edit.setReadOnly(True)
        form.addRow("鋼板編號", self.stencil_no_edit)
        form.addRow("Revision *", self.revision_edit)
        form.addRow("Side *", self.side_combo)
        form.addRow(
            "開窗幾何文件 *",
            self._path_row(self.aperture_edit, self._browse_aperture),
        )
        form.addRow("Pad CSV *", self._path_row(self.csv_edit, self._browse_csv))
        layout.addLayout(form)
        formats = QLabel(
            "支援：Gerber 單檔/ZIP、IPC-2581、ODB++ archive、DXF。"
            "Centroid、Mount data、BOM 僅屬 Pad/元件輔助資料，不會當成開窗幾何。"
        )
        formats.setWordWrap(True)
        formats.setProperty("class", "caption")
        layout.addWidget(formats)
        layout.addStretch(1)
        return page

    def _build_mapping_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(SPACING_8)
        fixed = QLabel(
            "固定欄位契約：RefDes, Pad, X, Y, Width, Height, Rotation, Side。"
            "Pad 以文字載入，保留前導零。"
        )
        fixed.setWordWrap(True)
        layout.addWidget(fixed)
        unit_row = QHBoxLayout()
        unit_row.addWidget(QLabel("CSV 座標/尺寸單位"))
        self.unit_combo = QComboBox()
        self.unit_combo.addItem("mm", "mm")
        self.unit_combo.addItem("inch", "inch")
        unit_row.addWidget(self.unit_combo)
        unit_row.addWidget(QLabel("DXF 單位"))
        self.aperture_unit_combo = QComboBox()
        self.aperture_unit_combo.setAccessibleName("DXF 開窗單位")
        self.aperture_unit_combo.addItem("依 $INSUNITS", "")
        self.aperture_unit_combo.addItem("mm", "mm")
        self.aperture_unit_combo.addItem("inch", "inch")
        self.aperture_unit_combo.setToolTip(
            "只有 DXF 未設定或需覆寫 $INSUNITS 時使用；其他格式自帶單位。"
        )
        unit_row.addWidget(self.aperture_unit_combo)
        self.load_csv_button = QPushButton("驗證並預覽 CSV")
        self.load_csv_button.setProperty("class", "secondary")
        self.load_csv_button.clicked.connect(self._load_csv_preview)
        unit_row.addWidget(self.load_csv_button)
        unit_row.addStretch(1)
        layout.addLayout(unit_row)
        self.mapping_status = QLabel("尚未驗證 CSV")
        self.mapping_status.setProperty("class", "statusIndicator")
        layout.addWidget(self.mapping_status)
        self.pad_preview = QTableWidget(0, 8)
        self.pad_preview.setHorizontalHeaderLabels(list(("RefDes", "Pad", "X mm", "Y mm", "W mm", "H mm", "Rotation", "Side")))
        self.pad_preview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.pad_preview.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.pad_preview, 1)
        return page

    def _build_overlay_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(SPACING_8)
        self.overlay_status = QLabel("尚未產生疊圖")
        self.overlay_status.setWordWrap(True)
        self.overlay_status.setProperty("class", "statusIndicator")
        layout.addWidget(self.overlay_status)
        legend = QLabel(
            "疊圖圖例：Pad 為外框，Paste 開窗為填色；"
            "實際判定以右側文字例外清單與驗證摘要為準。"
        )
        legend.setWordWrap(True)
        legend.setProperty("class", "caption")
        layout.addWidget(legend)
        body = QHBoxLayout()
        self.overlay_scene = QGraphicsScene(self)
        self.overlay_view = QGraphicsView(self.overlay_scene)
        body.addWidget(self.overlay_view, 2)
        right = QVBoxLayout()
        right.addWidget(QLabel("例外清單（狀態同時以文字呈現）"))
        self.exception_table = QTableWidget(0, 3)
        self.exception_table.setHorizontalHeaderLabels(["類型", "索引", "處置"])
        self.exception_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.exception_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.exception_table.horizontalHeader().setStretchLastSection(True)
        right.addWidget(self.exception_table, 1)
        self.non_component_button = QPushButton("將選取額外開窗標記為 NON_COMPONENT")
        self.non_component_button.setProperty("class", "secondary")
        self.non_component_button.clicked.connect(self._mark_non_component)
        right.addWidget(self.non_component_button)
        self.overlay_confirm = QCheckBox("我已核對 Pad 與開窗疊圖、方向及 Side")
        self.overlay_confirm.stateChanged.connect(self._update_summary)
        right.addWidget(self.overlay_confirm)
        body.addLayout(right, 1)
        layout.addLayout(body, 1)
        return page

    def _build_summary_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(SPACING_12)
        self.summary_label = QLabel("尚未完成驗證")
        self.summary_label.setWordWrap(True)
        self.summary_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.summary_label)
        self.activate_checkbox = QCheckBox("儲存後立即設為此產品/Side 的現用版本")
        layout.addWidget(self.activate_checkbox)
        note = QLabel(
            "版本建立後不可直接修改。若需修正文件，請建立新 Revision；停用現用版本可回到 raw 趨勢分析。"
        )
        note.setWordWrap(True)
        note.setProperty("class", "caption")
        layout.addWidget(note)
        layout.addStretch(1)
        return page

    def _path_row(self, edit: QLineEdit, callback: Any) -> QWidget:
        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(SPACING_4)
        row.addWidget(edit, 1)
        button = QPushButton("瀏覽")
        button.setProperty("class", "secondary")
        button.clicked.connect(callback)
        row.addWidget(button)
        return widget

    def _browse_aperture(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "選擇鋼板開窗幾何文件",
            "",
            "開窗幾何 (*.gtp *.gbp *.gbr *.ger *.pho *.zip *.xml *.ipc2581 "
            "*.tgz *.tar.gz *.tar *.dxf);;Gerber (*.gtp *.gbp *.gbr *.ger *.zip);;"
            "Legacy PHO (*.pho);;"
            "IPC-2581 (*.xml *.ipc2581);;ODB++ (*.tgz *.tar.gz *.tar *.zip);;"
            "DXF (*.dxf)",
        )
        if path:
            self.aperture_edit.setText(path)
            self._aperture_result = None
            self._aperture_cache_key = None
            self._match_cache_key = None
            self._non_component_indexes.clear()


    def _browse_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "選擇 Pad CSV", "", "CSV (*.csv)")
        if path:
            self.csv_edit.setText(path)
            self._match_cache_key = None
            self._non_component_indexes.clear()

    def _sync_step(self, index: int) -> None:
        labels = [
            "步驟 1/4｜選擇文件與版本",
            "步驟 2/4｜CSV 欄位與單位映射",
            "步驟 3/4｜開窗幾何 / Pad 疊圖與例外分類",
            "步驟 4/4｜驗證摘要與確認啟用",
        ]
        self.step_label.setText(labels[index])
        self.back_button.setEnabled(index > 0)
        self.next_button.setText("儲存版本" if index == 3 else "下一步")
        if index == 2:
            QTimer.singleShot(0, self._fit_overlay_view)

    def _back(self) -> None:
        self.pages.setCurrentIndex(max(0, self.pages.currentIndex() - 1))

    def _next(self) -> None:
        index = self.pages.currentIndex()
        if index == 0:
            if not self.product_name:
                show_dark_warning(self, "無法繼續", "請先在資料設定選擇產品。")
                return
            if (
                not self.revision_edit.text().strip()
                or not self.aperture_edit.text()
                or not self.csv_edit.text()
            ):
                show_dark_warning(
                    self,
                    "文件不足",
                    "Revision、開窗幾何文件與 Pad CSV 為必要欄位。",
                )
                return
            self.pages.setCurrentIndex(1)
            return
        if index == 1:
            if not self._load_csv_preview():
                return
            if not self._parse_and_match():
                return
            self.pages.setCurrentIndex(2)
            return
        if index == 2:
            self._update_summary()
            self.pages.setCurrentIndex(3)
            return
        self._save_version()

    def _load_csv_preview(self) -> bool:
        try:
            self._pads = load_pad_csv(
                self.csv_edit.text(),
                unit=str(self.unit_combo.currentData()),
                side=str(self.side_combo.currentData()),
            )
        except (OSError, ValueError) as exc:
            self._set_status(self.mapping_status, f"ERROR：{exc}", "error")
            show_dark_warning(self, "Pad CSV 驗證失敗", str(exc))
            return False
        self.pad_preview.setRowCount(min(len(self._pads), 200))
        for row_index, pad in enumerate(self._pads[:200]):
            values = [
                pad.refdes,
                pad.pad,
                f"{pad.x_mm:.6f}",
                f"{pad.y_mm:.6f}",
                f"{pad.width_mm:.6f}",
                f"{pad.height_mm:.6f}",
                f"{pad.rotation_deg:g}",
                pad.side,
            ]
            for column, value in enumerate(values):
                self.pad_preview.setItem(row_index, column, QTableWidgetItem(value))
        suffix = "（僅顯示前 200 列）" if len(self._pads) > 200 else ""
        self._set_status(
            self.mapping_status,
            f"SUCCESS：{len(self._pads)} 個 Pad，鍵值唯一{suffix}",
            "success",
        )
        return True

    def _parse_and_match(self) -> bool:
        self._set_status(
            self.overlay_status,
            "LOADING：正在解析開窗幾何與計算 Pad 匹配…",
            "loading",
        )
        try:
            cache_key = (
                self.aperture_edit.text(),
                str(self.side_combo.currentData()),
                str(self.aperture_unit_combo.currentData()),
            )
            match_key = (
                *cache_key,
                self.csv_edit.text(),
                str(self.unit_combo.currentData()),
            )
            if self._match_cache_key != match_key:
                self._non_component_indexes.clear()
                self._match_cache_key = match_key
            if self._aperture_result is None or self._aperture_cache_key != cache_key:
                self._aperture_result = load_aperture_source(
                    self.aperture_edit.text(),
                    side=cache_key[1],
                    unit_override=cache_key[2] or None,
                )
                self._aperture_cache_key = cache_key
            self._openings = self._aperture_result.openings
            self._analysis = analyze_stencil_import(
                product_name=self.product_name,
                side=str(self.side_combo.currentData()),
                pads=self._pads,
                openings=self._openings,
                non_component_opening_indexes=self._non_component_indexes,
            )
        except (OSError, ValueError, RuntimeError) as exc:
            self._set_status(self.overlay_status, f"ERROR：{exc}", "error")
            show_dark_warning(self, "開窗幾何解析或匹配失敗", str(exc))
            return False
        self._analysis.validation_summary.update(
            {
                "aperture_format": self._aperture_result.format_id,
                "aperture_format_label": self._aperture_result.format_label,
                "aperture_source_layer": self._aperture_result.source_layer,
                "aperture_warnings": list(self._aperture_result.warnings),
            }
        )
        self._render_overlay()
        self._render_exceptions()
        summary = self._analysis.validation_summary
        status_state = "warning" if activation_blockers(summary) else "success"
        status_prefix = "WARNING" if status_state == "warning" else "SUCCESS"
        self._set_status(
            self.overlay_status,
            f"{status_prefix}：Pad {summary['matched_pads']}/{summary['total_pads']}；"
            f"歧義開窗 {summary['ambiguous_openings']}；未分類額外開窗 "
            f"{summary['unclassified_extra_openings']}。"
            f"來源 {self._aperture_result.format_label} / "
            f"{self._aperture_result.source_layer}；系統候選仍需人工確認。",
            status_state,
        )
        return True

    @staticmethod
    def _set_status(label: QLabel, text: str, state: str) -> None:
        label.setText(text)
        label.setProperty("state", state)
        label.style().unpolish(label)
        label.style().polish(label)
        label.update()

    def _render_overlay(self) -> None:
        self.overlay_scene.clear()
        if not self._analysis:
            return
        pad_pen = QPen(QColor(STENCIL_PREVIEW_PAD_OUTLINE))
        pad_pen.setWidth(STENCIL_PREVIEW_COSMETIC_PEN_WIDTH)
        opening_color = QColor(STENCIL_PREVIEW_OPENING_OUTLINE)
        opening_pen = QPen(opening_color)
        opening_pen.setWidth(STENCIL_PREVIEW_COSMETIC_PEN_WIDTH)
        opening_fill = QColor(opening_color)
        opening_fill.setAlpha(STENCIL_PREVIEW_OPENING_ALPHA)
        opening_brush = QBrush(opening_fill)
        for geometry in self._analysis.transformed_openings:
            self._add_geometry(geometry, opening_pen, opening_brush)
        for pad in self._pads:
            self._add_geometry(pad.geometry(), pad_pen, QBrush(Qt.BrushStyle.NoBrush))
        self._fit_overlay_view()

    def _fit_overlay_view(self) -> None:
        bounds = self.overlay_scene.itemsBoundingRect()
        if bounds.isValid() and not bounds.isEmpty():
            self.overlay_view.fitInView(bounds, Qt.AspectRatioMode.KeepAspectRatio)

    def showEvent(self, event: Any) -> None:
        """Fit overlay geometry after the dialog receives its final native size."""
        super().showEvent(event)
        QTimer.singleShot(0, self._fit_overlay_view)

    def resizeEvent(self, event: Any) -> None:
        """Keep the overlay legible when the import dialog is resized."""
        super().resizeEvent(event)
        if self.pages.currentIndex() == 2:
            QTimer.singleShot(0, self._fit_overlay_view)

    def _add_geometry(self, geometry: Any, pen: QPen, brush: QBrush) -> None:
        geoms = list(geometry.geoms) if geometry.geom_type == "MultiPolygon" else [geometry]
        for geom in geoms:
            points = [QtCorePoint(x, -y) for x, y in geom.exterior.coords]
            self.overlay_scene.addPolygon(QPolygonF(points), pen, brush)

    def _render_exceptions(self) -> None:
        self.exception_table.setRowCount(0)
        if not self._analysis:
            return
        summary = self._analysis.validation_summary
        rows: list[tuple[str, str, str]] = []
        rows.extend(("AMBIGUOUS", str(index), "必須修正資料/對齊") for index in summary["ambiguous_opening_indexes"])
        rows.extend(("EXTRA", str(index), "待人工分類") for index in summary["extra_opening_indexes"])
        rows.extend(("UNMATCHED_PAD", key, "不得靜默排除") for key in summary["unmatched_pads"])
        rows.extend(("NON_COMPONENT", str(index), "已人工排除") for index in summary["non_component_openings"])
        self.exception_table.setRowCount(len(rows))
        for row_index, values in enumerate(rows):
            for column, value in enumerate(values):
                self.exception_table.setItem(row_index, column, QTableWidgetItem(value))

    def _mark_non_component(self) -> None:
        row = self.exception_table.currentRow()
        if row < 0:
            show_dark_warning(self, "尚未選取", "請先選取一筆 EXTRA 開窗。")
            return
        type_item = self.exception_table.item(row, 0)
        index_item = self.exception_table.item(row, 1)
        if not type_item or type_item.text() != "EXTRA" or not index_item:
            show_dark_warning(self, "不可分類", "只有 EXTRA 開窗可以標記 NON_COMPONENT。")
            return
        self._non_component_indexes.add(int(index_item.text()))
        self._parse_and_match()

    def _update_summary(self) -> None:
        if not self._analysis:
            return
        summary = dict(self._analysis.validation_summary)
        summary["overlay_confirmed"] = self.overlay_confirm.isChecked()
        summary["requires_user_overlay_confirmation"] = True
        blockers = activation_blockers(summary)
        status = "VERIFY" if blockers else "VALID"
        source_text = "尚未解析"
        parser_version = PARSER_VERSION
        warning_text = "無"
        if self._aperture_result is not None:
            source_text = (
                f"{self._aperture_result.format_label} / "
                f"{self._aperture_result.source_layer}"
            )
            parser_version = self._aperture_result.parser_version
            warning_text = (
                "；".join(self._aperture_result.warnings)
                if self._aperture_result.warnings
                else "無"
            )
        self.summary_label.setText(
            f"狀態：{status}\n"
            f"產品 / Side / Revision：{self.product_name} / {self.side_combo.currentData()} / "
            f"{self.revision_edit.text().strip()}\n"
            f"Pad 覆蓋：{summary['matched_pads']}/{summary['total_pads']} "
            f"({summary['coverage'] * 100:.2f}%)\n"
            f"歧義：{summary['ambiguous_openings']}；未分類額外："
            f"{summary['unclassified_extra_openings']}；缺厚度：{summary['missing_thickness_pads']}\n"
            f"開窗來源：{source_text}\n"
            f"來源警告：{warning_text}\n"
            f"啟用阻擋：{'；'.join(blockers) if blockers else '無'}\n"
            f"Parser：{parser_version}"
        )
        self.activate_checkbox.setEnabled(not blockers)
        if blockers:
            self.activate_checkbox.setChecked(False)

    def _save_version(self) -> None:
        if not self._analysis:
            return
        summary = dict(self._analysis.validation_summary)
        summary["overlay_confirmed"] = self.overlay_confirm.isChecked()
        summary["requires_user_overlay_confirmation"] = True
        try:
            parser_version = (
                self._aperture_result.parser_version
                if self._aperture_result is not None
                else PARSER_VERSION
            )
            version_id = create_stencil_document_version(
                product_name=self.product_name,
                stencil_no=self.stencil_no_edit.text().strip(),
                revision=self.revision_edit.text().strip(),
                side=str(self.side_combo.currentData()),
                gerber_source=self.aperture_edit.text(),
                pad_csv_source=self.csv_edit.text(),
                coordinate_transform=self._analysis.transform,
                validation_summary=summary,
                parser_version=parser_version,
                nominals=self._analysis.nominals,
                activate=self.activate_checkbox.isChecked(),
            )
        except (OSError, ValueError, RuntimeError) as exc:
            show_dark_warning(self, "儲存失敗", str(exc))
            return
        show_dark_information(
            self,
            "版本已建立",
            f"版本 ID {version_id} 已儲存"
            + ("並啟用。" if self.activate_checkbox.isChecked() else "（未啟用）。"),
        )
        self.version_created.emit(version_id)
        self.accept()


def QtCorePoint(x: float, y: float):
    """Small local helper keeps geometry conversion readable."""
    from PySide6.QtCore import QPointF

    return QPointF(float(x), float(y))
