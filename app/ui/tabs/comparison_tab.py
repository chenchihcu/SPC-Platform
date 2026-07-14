from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox
from PySide6.QtCore import Qt
from app.charts.boxplot_chart import BoxplotChart
from app.analytics.chart_registry import (
    CHART_GROUP_VARIANT_LABELS,
    format_chart_description,
    format_chart_description_compact,
    select_chart_group_variant,
)
from app.ui.theme.tokens import SPACING_SM


class ComparisonTab(QWidget):
    """
    Renders group comparison (boxplot).

    Grouping is determined automatically by the analysis engine based on
    the sidebar filter state (RefDes / PartType / board).  There is no
    in-chart Part Type selector; use the sidebar 「類型」 filter to
    drill into a specific footprint group.

    Supports two modes forwarded from ChartAnalysisPage:
    - Single-feature  : board or RefDes grouping; hints shown when relevant.
    - Multi-feature   : pass merged payload directly to BoxplotChart.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)

        self.lbl_desc = QLabel(format_chart_description_compact("boxplot"))
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setProperty("class", "chartDescCompact")
        self.lbl_desc.setToolTip(format_chart_description("boxplot"))
        self.lbl_desc.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        layout.addWidget(self.lbl_desc)

        self._group_row = QWidget(self)
        group_layout = QHBoxLayout(self._group_row)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.addWidget(QLabel("分組方式："))
        self.group_combo = QComboBox(self._group_row)
        self.group_combo.setAccessibleName("箱型圖分組方式")
        self.group_combo.currentIndexChanged.connect(self._on_group_changed)
        group_layout.addWidget(self.group_combo)
        group_layout.addStretch(1)
        self._group_row.setVisible(False)
        layout.addWidget(self._group_row)

        # Context hint (shown for board-grouping mode)
        self._hint_label = QLabel()
        self._hint_label.setWordWrap(True)
        self._hint_label.setProperty("class", "caption")
        self._hint_label.setVisible(False)
        layout.addWidget(self._hint_label)

        self.chart_view = BoxplotChart(self)
        layout.addWidget(self.chart_view, 1)

        self._last_payload: dict = {}

    # ── update_data ───────────────────────────────────────────────────

    def update_data(self, boxplot_json: dict) -> None:
        """Dispatch to multi-feature or single-feature rendering."""
        if (boxplot_json or {}).get("_multi_feature"):
            self._update_multi_feature(boxplot_json)
        else:
            self._update_single_feature(boxplot_json)

    def _update_multi_feature(self, boxplot_json: dict) -> None:
        """Multi-feature mode: render merged payload directly."""
        features: list[str] = boxplot_json.get("_features", [])
        desc_ctx = {"target_col": " + ".join(features) if features else ""}
        self.lbl_desc.setText(format_chart_description_compact("boxplot", desc_ctx))
        self.lbl_desc.setToolTip(format_chart_description("boxplot", desc_ctx))

        self._last_payload = boxplot_json
        self._group_row.setVisible(False)
        self._hint_label.setVisible(False)
        self.chart_view.draw_chart(boxplot_json)

    def _update_single_feature(self, boxplot_json: dict) -> None:
        """Single-feature mode: render with contextual grouping hint."""
        ctx = (boxplot_json or {}).get("analysis_context", {})
        desc_ctx = {"target_col": ctx.get("target_col")}
        self.lbl_desc.setText(format_chart_description_compact("boxplot", desc_ctx))
        self.lbl_desc.setToolTip(format_chart_description("boxplot", desc_ctx))

        self._last_payload = boxplot_json or {}
        self._refresh_group_selector()
        active_payload = select_chart_group_variant(
            self._last_payload, self.group_combo.currentData()
        )

        grouping_mode: str = active_payload.get("_grouping_mode", "")
        group_col: str = active_payload.get("_group_col", "")
        refdes: str = self._last_payload.get("_ctx_refdes", "")
        part_type: str = self._last_payload.get("_ctx_part_type", "")

        if grouping_mode == "board":
            _col_label = (
                "板號" if group_col == "BoardNo"
                else "面板編號" if group_col == "PanelId"
                else group_col
            )
            _hint = f"目前以{_col_label}（{group_col}）分組比較"
            if refdes:
                _hint += f"：{refdes}"
            elif part_type:
                _hint += f"：{part_type}"
            self._hint_label.setText(_hint)
            self._hint_label.setVisible(True)
        elif grouping_mode == "refdes" and part_type:
            self._hint_label.setText(f"類型篩選：{part_type}，以 RefDes 分組")
            self._hint_label.setVisible(True)
        else:
            self._hint_label.setVisible(False)

        self.chart_view.draw_chart(active_payload)

    def _refresh_group_selector(self) -> None:
        previous = self.group_combo.currentData() or "default"
        variants = self._last_payload.get("_group_variants", {})
        keys = ["default", *[key for key in ("pad", "image") if key in variants]]
        self.group_combo.blockSignals(True)
        try:
            self.group_combo.clear()
            for key in keys:
                self.group_combo.addItem(CHART_GROUP_VARIANT_LABELS[key], key)
            selected = self.group_combo.findData(previous)
            self.group_combo.setCurrentIndex(selected if selected >= 0 else 0)
        finally:
            self.group_combo.blockSignals(False)
        self._group_row.setVisible(len(keys) > 1)

    def _on_group_changed(self, _index: int) -> None:
        if not self._last_payload:
            return
        self._update_single_feature(self._last_payload)
