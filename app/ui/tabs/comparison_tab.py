from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from app.charts.boxplot_chart import BoxplotChart
from app.analytics.chart_registry import format_chart_description, format_chart_description_compact
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
        self._hint_label.setVisible(False)
        self.chart_view.draw_chart(boxplot_json)

    def _update_single_feature(self, boxplot_json: dict) -> None:
        """Single-feature mode: render with contextual grouping hint."""
        ctx = (boxplot_json or {}).get("analysis_context", {})
        desc_ctx = {"target_col": ctx.get("target_col")}
        self.lbl_desc.setText(format_chart_description_compact("boxplot", desc_ctx))
        self.lbl_desc.setToolTip(format_chart_description("boxplot", desc_ctx))

        self._last_payload = boxplot_json or {}

        grouping_mode: str = self._last_payload.get("_grouping_mode", "")
        group_col: str = self._last_payload.get("_group_col", "")
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

        self.chart_view.draw_chart(self._last_payload)
