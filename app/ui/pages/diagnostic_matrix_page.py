"""Diagnostic evidence matrix page (DiagnosticMatrixPage).
Displays the structured diagnostic evidence matrix tabs:
Overview, Combination Matrix, Evidence Matrix, Correlation,
Chart Linkage, Actions, and Data Context.

Extracted from DiagnosticPage to allow independent sidebar navigation.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt, QTimer, Signal

from app.ui.theme.tokens import (
    PAGE_CONTENT_MARGIN,
    SPACING_4,
    SPACING_8,
    SPACING_12,
    SPACING_16,
    PAGE_HEADER_BOTTOM_SPACING,
    TABLE_ROW_MIN_HEIGHT,
    DIAGNOSTIC_MATRIX_MAX_ROW_HEIGHT,
    DIAGNOSTIC_MATRIX_MAX_VISIBLE_ROWS,
    DIAGNOSTIC_MATRIX_MIN_SECTION_WIDTH,
    DIAGNOSTIC_MATRIX_MIN_VISIBLE_ROWS,
    DIAGNOSTIC_MATRIX_TABLE_EXTRA_HEIGHT,
    DIAGNOSTIC_MATRIX_FEATURE_COL_WIDTH,
    DIAGNOSTIC_MATRIX_CHART_COL_WIDTH,
    DIAGNOSTIC_MATRIX_FAMILY_COL_WIDTH,
    DIAGNOSTIC_MATRIX_STATUS_COL_WIDTH,
    DIAGNOSTIC_MATRIX_DIMENSION_COL_WIDTH,
    DIAGNOSTIC_MATRIX_VERDICT_COL_WIDTH,
    DIAGNOSTIC_MATRIX_METRIC_COL_WIDTH,
    DIAGNOSTIC_MATRIX_REASON_COL_WIDTH,
    DIAGNOSTIC_MATRIX_EVIDENCE_DIM_COL_WIDTH,
    DIAGNOSTIC_MATRIX_GAP_COUNT_COL_WIDTH,
    DIAGNOSTIC_MATRIX_LINK_REASON_COL_WIDTH,
)
from app.ui.widgets.page_templates import create_status_lamp, style_table
from app.services.diagnostic_evidence_matrix import build_readable_diagnostic_tabs
from app.analytics.chart_registry import get_chart_display_name as _get_chart_display_name

_COMBINATION_DISPLAY_LIMIT = 80
_LINKAGE_DISPLAY_LIMIT = 12
_TOP_EVIDENCE_LIMIT = 5
_READABLE_DISPLAY_LIMIT = 12

_STATE_LABELS = {
    "support": "支持",
    "refute": "不支持此假設",
    "neutral": "中性",
    "unavailable": "資料不足/不可判讀",
}
_AVAILABILITY_LABELS = {
    "analyzed": "已分析",
    "available-not-selected": "可用未選",
    "unavailable": "不可用",
    "not-applicable": "不適用",
    "missing-data": "缺資料",
}
_STATE_SORT = {"support": 0, "refute": 1, "neutral": 2, "unavailable": 3}
_AVAILABILITY_SORT = {
    "analyzed": 0,
    "available-not-selected": 1,
    "missing-data": 2,
    "unavailable": 3,
    "not-applicable": 4,
}
_SEVERITY_SORT = {"error": 0, "warning": 1, "info": 2}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _display(value: Any) -> str:
    if value in (None, "", []):
        return "—"
    return str(value)


def _feature_text(value: Any) -> str:
    if isinstance(value, list):
        parts = [str(item).strip() for item in value if str(item).strip()]
        return " + ".join(parts) if parts else "—"
    return _display(value)


def _normalize_metric_text(value: Any) -> str:
    text = _display(value)
    if text == "—" or "feature count not applicable" in text:
        return "—"
    return text.replace("；", ";")


class DiagnosticMatrixPage(QWidget):
    """
    Diagnostic evidence matrix page (DiagnosticMatrixPage).
    Displays the structured diagnostic evidence matrix tabs:
    Overview, Combination Matrix, Evidence Matrix, Correlation,
    Chart Linkage, Actions, and Data Context.
    """

    navigate_to_chart = Signal(str, list)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._last_payload: dict[str, Any] = {}
        self._matrix_tab_layouts: dict[str, QVBoxLayout] = {}

        # Main Layout
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header Toolbar
        self._header = QFrame()
        self._header.setProperty("class", "headerToolbar")
        self._header.setProperty("headerRole", "utilityHeader")
        self._header.setProperty("headerDensity", "compact")
        header_lay = QHBoxLayout(self._header)
        header_lay.setContentsMargins(PAGE_CONTENT_MARGIN, SPACING_4, PAGE_CONTENT_MARGIN, SPACING_4)
        header_lay.setSpacing(SPACING_8)

        self._title_lbl = QLabel("診斷證據矩陣")
        self._title_lbl.setProperty("class", "pageTitle")
        header_lay.addWidget(self._title_lbl)

        # Global Status Lamp
        self._lamp = create_status_lamp()
        header_lay.addWidget(self._lamp)

        self._status_lbl = QLabel("就緒")
        self._status_lbl.setProperty("class", "statusIndicator")
        header_lay.addWidget(self._status_lbl)

        header_lay.addStretch(1)

        self._updated_lbl = QLabel("最後更新: —")
        self._updated_lbl.setProperty("class", "diagUpdatedLabel")
        header_lay.addWidget(self._updated_lbl)

        root.addWidget(self._header)
        root.addSpacing(PAGE_HEADER_BOTTOM_SPACING)

        # Body (Scrollable)
        self._body_widget = QWidget()
        self._body_lay = QVBoxLayout(self._body_widget)
        self._body_lay.setContentsMargins(PAGE_CONTENT_MARGIN, SPACING_8, PAGE_CONTENT_MARGIN, SPACING_8)
        self._body_lay.setSpacing(SPACING_12)
        
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setWidget(self._body_widget)
        root.addWidget(self._scroll, 1)

        self._init_matrix_tabs()
        self._body_lay.addStretch(1)

    def _init_matrix_tabs(self) -> None:
        """Tabs for the combination/evidence diagnosis matrix."""
        self._matrix_tabs = QTabWidget()
        self._matrix_tabs.setProperty("class", "secondaryTabs processMatrixTabs")
        self._matrix_tabs.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Maximum,
        )
        self._matrix_tabs.tabBar().setExpanding(False)
        self._matrix_tabs.currentChanged.connect(self._sync_matrix_tabs_height)
        tab_defs = [
            ("overview", "總覽"),
            ("combination_matrix", "組合矩陣"),
            ("evidence_matrix", "證據矩陣"),
            ("correlation", "關聯判讀"),
            ("chart_linkage", "圖表連動"),
            ("actions", "對策建議"),
            ("data_context", "資料背景"),
        ]
        for key, title in tab_defs:
            page = QWidget()
            lay = QVBoxLayout(page)
            lay.setContentsMargins(SPACING_12, SPACING_12, SPACING_12, SPACING_12)
            lay.setSpacing(SPACING_12)
            self._matrix_tab_layouts[key] = lay
            self._matrix_tabs.addTab(page, title)
        self._body_lay.addWidget(self._matrix_tabs)

    def _sync_matrix_tabs_height(self, *_args: Any) -> None:
        try:
            widget = self._matrix_tabs.currentWidget()
            layout = widget.layout() if widget is not None else None
            if layout is None:
                return
            layout.activate()
            tab_bar_height = self._matrix_tabs.tabBar().sizeHint().height()
            pane_padding = SPACING_16
            height = tab_bar_height + layout.sizeHint().height() + pane_padding
            self._matrix_tabs.setMinimumHeight(height)
            self._matrix_tabs.setMaximumHeight(height)
            self._matrix_tabs.updateGeometry()
        except RuntimeError:
            pass

    def _clear_layout(self, layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)  # type: ignore[arg-type]

    def _section(self, layout: QVBoxLayout, title: str) -> QVBoxLayout:
        frame = QFrame()
        frame.setObjectName("diagnosticSection")
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        root = QVBoxLayout(frame)
        root.setContentsMargins(SPACING_12, SPACING_12, SPACING_12, SPACING_12)
        root.setSpacing(SPACING_8)
        label = QLabel(title)
        label.setProperty("class", "diagnosticSectionTitle")
        root.addWidget(label)
        layout.addWidget(frame)
        return root

    def _plain_label(self, text: str, *, muted: bool = False) -> QLabel:
        label = QLabel(text)
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setWordWrap(True)
        label.setProperty("class", "diagnosticMutedText" if muted else "diagnosticBodyText")
        return label

    def _badge(self, text: str, state: str = "neutral") -> QLabel:
        badge = QLabel(text)
        badge.setProperty("class", "diagnosticBadge")
        badge.setProperty("state", state)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setMinimumWidth(0)
        badge.setWordWrap(True)
        badge.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        return badge

    def _add_banner(
        self,
        layout: QVBoxLayout,
        title: str,
        body: str,
        badges: list[tuple[str, str, str]],
    ) -> None:
        frame = QFrame()
        frame.setObjectName("diagnosticBanner")
        root = QVBoxLayout(frame)
        root.setContentsMargins(SPACING_12, SPACING_12, SPACING_12, SPACING_12)
        root.setSpacing(SPACING_8)
        title_label = QLabel(title)
        title_label.setProperty("class", "diagnosticSectionTitle")
        root.addWidget(title_label)
        root.addWidget(self._plain_label(body))
        badge_row = QHBoxLayout()
        badge_row.setSpacing(SPACING_8)
        for label, value, state in badges:
            badge_row.addWidget(self._badge(f"{label}: {value}", state))
        badge_row.addStretch(1)
        root.addLayout(badge_row)
        layout.addWidget(frame)

    def _add_metric_grid(self, layout: QVBoxLayout, metrics: list[tuple[str, Any]]) -> None:
        frame = QFrame()
        frame.setObjectName("diagnosticMetricGrid")
        grid = QGridLayout(frame)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(SPACING_8)
        grid.setVerticalSpacing(SPACING_8)
        for idx, (label_text, value) in enumerate(metrics):
            tile = QFrame()
            tile.setObjectName("diagnosticMetricTile")
            tile_lay = QVBoxLayout(tile)
            tile_lay.setContentsMargins(SPACING_8, SPACING_8, SPACING_8, SPACING_8)
            tile_lay.setSpacing(SPACING_4)
            label = QLabel(label_text)
            label.setProperty("class", "diagnosticMetricLabel")
            val = QLabel(_display(value))
            val.setProperty("class", "diagnosticMetricValue")
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            tile_lay.addWidget(label)
            tile_lay.addWidget(val)
            grid.addWidget(tile, idx // 4, idx % 4)
        layout.addWidget(frame)

    def _table_item(self, value: Any, *, tooltip: str = "") -> QTableWidgetItem:
        display = _display(value)
        item = QTableWidgetItem(display)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        if tooltip or len(display) > 24:
            item.setToolTip(tooltip or display)
        return item

    def _build_table(self, headers: list[str]) -> QTableWidget:
        table = QTableWidget(0, len(headers))
        table.setObjectName("diagnosticMatrixTable")
        table.setHorizontalHeaderLabels(headers)
        style_table(table, role="diagnostic")
        table.horizontalHeader().setMinimumSectionSize(DIAGNOSTIC_MATRIX_MIN_SECTION_WIDTH)
        return table

    def _fit_table_height(
        self,
        table: QTableWidget,
        *,
        min_rows: int = DIAGNOSTIC_MATRIX_MIN_VISIBLE_ROWS,
        max_rows: int = DIAGNOSTIC_MATRIX_MAX_VISIBLE_ROWS,
    ) -> None:
        rows = table.rowCount()
        table.resizeRowsToContents()
        for row in range(rows):
            table.setRowHeight(
                row,
                min(max(table.rowHeight(row), TABLE_ROW_MIN_HEIGHT), DIAGNOSTIC_MATRIX_MAX_ROW_HEIGHT),
            )
        visible_rows = min(max(rows, min_rows), max_rows)
        measured_rows = min(rows, visible_rows)
        row_height = sum(
            max(table.rowHeight(row), TABLE_ROW_MIN_HEIGHT)
            for row in range(measured_rows)
        )
        if visible_rows > measured_rows:
            row_height += (visible_rows - measured_rows) * TABLE_ROW_MIN_HEIGHT
        header_height = max(table.horizontalHeader().height(), TABLE_ROW_MIN_HEIGHT)
        scroll_height = table.horizontalScrollBar().sizeHint().height()
        frame_height = table.frameWidth() * 2
        height = (
            header_height
            + row_height
            + scroll_height
            + frame_height
            + DIAGNOSTIC_MATRIX_TABLE_EXTRA_HEIGHT
        )
        table.setMinimumHeight(height)
        table.setMaximumHeight(height)

    def _configure_table_columns(
        self,
        table: QTableWidget,
        widths: dict[int, int],
        *,
        stretch_cols: set[int] | None = None,
        fixed_cols: set[int] | None = None,
        minimum_section_width: int = DIAGNOSTIC_MATRIX_MIN_SECTION_WIDTH,
    ) -> None:
        header = table.horizontalHeader()
        header.setMinimumSectionSize(minimum_section_width)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        stretch_cols = stretch_cols or set()
        fixed_cols = fixed_cols or set()

        for col, width in widths.items():
            table.setColumnWidth(col, width)
            header.resizeSection(col, width)
        for col in fixed_cols:
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
        for col in stretch_cols:
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)

    def _readable_rows(self, matrix: dict[str, Any], key: str) -> list[dict[str, str]]:
        rows = build_readable_diagnostic_tabs(matrix).get(key, [])
        return [row for row in rows if isinstance(row, dict)]

    def _render_readable_table(
        self,
        layout: QVBoxLayout,
        title: str,
        rows: list[dict[str, str]],
        *,
        limit: int = _READABLE_DISPLAY_LIMIT,
    ) -> None:
        if not rows:
            return
        section = self._section(layout, title)
        shown = rows[:limit]
        table = self._build_table(["項目", "判讀結果", "說明", "證據來源", "下一步"])
        table.setRowCount(len(shown))
        self._configure_table_columns(
            table,
            {
                0: DIAGNOSTIC_MATRIX_CHART_COL_WIDTH,
                1: DIAGNOSTIC_MATRIX_VERDICT_COL_WIDTH,
                2: DIAGNOSTIC_MATRIX_REASON_COL_WIDTH,
                3: DIAGNOSTIC_MATRIX_METRIC_COL_WIDTH,
                4: DIAGNOSTIC_MATRIX_LINK_REASON_COL_WIDTH,
            },
            stretch_cols={2, 3, 4},
            fixed_cols={0, 1},
        )
        for row_idx, row in enumerate(shown):
            table.setItem(row_idx, 0, self._table_item(row.get("title")))
            table.setItem(row_idx, 1, self._table_item(row.get("result_zh")))
            table.setItem(row_idx, 2, self._table_item(row.get("reason_zh")))
            table.setItem(row_idx, 3, self._table_item(row.get("evidence_zh")))
            table.setItem(row_idx, 4, self._table_item(row.get("next_action_zh")))
        self._fit_table_height(table)
        section.addWidget(table)

    def _set_badge_cell(
        self,
        table: QTableWidget,
        row: int,
        col: int,
        text: str,
        state: str,
        *,
        subtle: bool = False,
    ) -> None:
        badge = self._badge(text, state)
        if subtle:
            badge.setProperty("tone", "subtle")
        badge.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        table.setCellWidget(row, col, badge)

    def _format_metric_snapshot(self, value: Any) -> str:
        text = _normalize_metric_text(value)
        if text == "—":
            return text

        ooc_match = re.search(r"\bOOC=([^;]+)", text)
        ratio_match = re.search(r"\bratio=([^;]+)", text)
        if ooc_match and ratio_match:
            return f"OOC {ooc_match.group(1).strip()} ({ratio_match.group(1).strip()})"

        cpk_match = re.search(r"\bCpk=([^;]+)", text)
        cp_match = re.search(r"\bCp=([^;]+)", text)
        if cpk_match and cp_match:
            return f"Cpk {cpk_match.group(1).strip()} / Cp {cp_match.group(1).strip()}"

        cp_only_match = re.search(r"\bCp=([^;]+)", text)
        std_spec_match = re.search(r"\bstd/spec=([^;]+)", text)
        if cp_only_match and std_spec_match:
            return f"Cp {cp_only_match.group(1).strip()} / std/spec {std_spec_match.group(1).strip()}"

        cluster_match = re.search(r"\bcluster=([^;]+)", text)
        top_refs_match = re.search(r"\btop refs=([^;]+)", text)
        if cluster_match and top_refs_match:
            return f"群聚 {cluster_match.group(1).strip()} / Top refs {top_refs_match.group(1).strip()}"

        normality_match = re.search(r"\bnormality p=([^;]+)", text)
        if normality_match:
            return f"常態 p {normality_match.group(1).strip()}"

        max_fail_match = re.search(r"\bmax fail=([^;]+)", text)
        fail_count_match = re.search(r"\bfail count=([^;]+)", text)
        if max_fail_match and fail_count_match:
            return f"Fail {max_fail_match.group(1).strip()} / count {fail_count_match.group(1).strip()}"

        trend_match = re.search(r"\btrend=([^;]+)", text)
        if trend_match:
            return f"漂移 {trend_match.group(1).strip()}"

        return _display(value)

    def _metric_item(self, value: Any) -> QTableWidgetItem:
        raw = _display(value)
        formatted = self._format_metric_snapshot(value)
        tooltip = f"原始關鍵數值: {raw}" if raw != formatted else ""
        return self._table_item(formatted, tooltip=tooltip)

    def _state_label(self, state: Any) -> str:
        key = str(state or "")
        return _STATE_LABELS.get(key, _display(state))

    def _matrix_cell_state_label(self, state: Any) -> str:
        key = str(state or "")
        if key == "refute":
            return "不支持"
        if key == "unavailable":
            return "資料不足"
        return self._state_label(key)

    def _availability_label(self, candidate: dict[str, Any]) -> str:
        label = candidate.get("availability_label_zh")
        if label:
            return str(label)
        key = str(candidate.get("availability") or "")
        return _AVAILABILITY_LABELS.get(key, _display(key))

    def _dimension_label(self, matrix: dict[str, Any], dimension: Any) -> str:
        key = str(dimension or "")
        labels = _as_dict(matrix.get("dimension_labels"))
        return str(labels.get(key) or key or "—")

    def _translated_reason(self, raw_reason: Any, candidate: dict[str, Any]) -> str:
        reason = str(raw_reason or "").strip()
        availability = str(candidate.get("availability") or "")
        if not reason:
            if availability == "available-not-selected":
                return "圖表可用但本次未選取"
            if availability == "not-applicable":
                return "特徵數或圖表條件不適用"
            return "—"

        if "feature count not applicable" in reason:
            required = candidate.get("required_feature_count")
            current = len(_as_list(candidate.get("feature_set")))
            if required:
                return f"需 {required} 個特徵，目前 {current} 個"
            return "特徵數不足，無法套用此圖表"

        match = re.search(r"requires\s+(\d+)\s+feature", reason)
        if match:
            required = match.group(1)
            current = len(_as_list(candidate.get("feature_set")))
            return f"需 {required} 個特徵，目前 {current} 個"

        translations = {
            "payload missing": "payload 無資料",
            "payload empty": "payload 為空",
            "payload invalid": "payload 標記為不可用",
            "available-not-selected": "圖表可用但本次未選取",
            "not-applicable": "特徵數或圖表條件不適用",
            "missing-data": "缺少圖表資料",
            "unavailable": "圖表資料不可用",
        }
        return translations.get(reason, reason)

    def _candidate_reason(self, candidate: dict[str, Any]) -> str:
        availability = str(candidate.get("availability") or "")
        if availability == "analyzed":
            return "—"
        reason = candidate.get("missing_reason") or candidate.get("metric_snapshot")
        return self._translated_reason(reason, candidate)

    def _candidate_sort_key(self, candidate: dict[str, Any]) -> tuple[int, int, int, float]:
        state = str(candidate.get("evidence_state") or "")
        availability = str(candidate.get("availability") or "")
        severity = str(candidate.get("severity") or "")
        try:
            relevance = float(candidate.get("relevance") or 0)
        except (TypeError, ValueError):
            relevance = 0.0
        return (
            _STATE_SORT.get(state, 9),
            _AVAILABILITY_SORT.get(availability, 9),
            _SEVERITY_SORT.get(severity, 9),
            -relevance,
        )

    def _evidence_row(self, item: dict[str, Any]) -> QWidget:
        row = QFrame()
        row.setObjectName("diagnosticEvidenceRow")
        lay = QHBoxLayout(row)
        lay.setContentsMargins(SPACING_8, SPACING_8, SPACING_8, SPACING_8)
        lay.setSpacing(SPACING_8)
        state = str(item.get("evidence_state") or "support")
        if not item.get("evidence_state") and item.get("severity") == "error":
            state = "support"
        lay.addWidget(self._badge(self._state_label(state), state))
        text = (
            f"{_display(item.get('chart_name'))} / {_feature_text(item.get('feature_set'))} | "
            f"{_display(item.get('dimension_label') or item.get('evidence_dimension') or item.get('dimension'))} | "
            f"{_display(item.get('metric_snapshot'))}"
        )
        lay.addWidget(self._plain_label(text), 1)
        return row

    def _diagnostic_limitations(
        self,
        summary: dict[str, Any],
        coverage: dict[str, Any],
    ) -> list[str]:
        confidence = _as_dict(summary.get("confidence"))
        support_count = int(confidence.get("support_candidate_count") or 0)
        family_count = int(confidence.get("support_family_count") or 0)
        dimension_count = int(confidence.get("support_dimension_count") or 0)
        limits: list[str] = []
        if support_count == 0:
            limits.append("目前未形成可支持製程異常的組合證據。")
        if support_count and (family_count < 2 or dimension_count < 2):
            limits.append("支持證據仍集中在單一圖表分類或單一證據維度，不足以單獨定根因。")
        counts = _as_dict(coverage.get("availability_counts"))
        missing = int(counts.get("missing-data") or 0)
        unavailable = int(counts.get("unavailable") or 0)
        if missing or unavailable:
            limits.append(f"仍有缺資料/不可用組合 {missing + unavailable} 筆，需補強後再升高診斷信心。")
        return limits or ["目前未發現會限制判讀信心的主要資料缺口。"]

    def _render_fallback_tab(self, layout: QVBoxLayout, lines: list[Any]) -> None:
        text_lines = [str(line) for line in lines if str(line).strip()]
        section = self._section(layout, "目前沒有可顯示項目")
        section.addWidget(self._plain_label("\n".join(text_lines) if text_lines else "—", muted=True))

    def _add_bullets(self, layout: QVBoxLayout, lines: list[str]) -> None:
        if not lines:
            return
        list_frame = QFrame()
        list_frame.setObjectName("diagnosticBulletList")
        grid = QGridLayout(list_frame)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(SPACING_8)
        grid.setVerticalSpacing(SPACING_4)
        for idx, line in enumerate(lines, start=1):
            index = QLabel(f"{idx}.")
            index.setProperty("class", "diagnosticBulletIndex")
            index.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
            text = QLabel(line)
            text.setTextFormat(Qt.TextFormat.PlainText)
            text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            text.setWordWrap(True)
            text.setProperty("class", "diagnosticBulletText")
            grid.addWidget(index, idx - 1, 0)
            grid.addWidget(text, idx - 1, 1)
        grid.setColumnStretch(1, 1)
        layout.addWidget(list_frame)

    def _add_info_pairs(self, layout: QVBoxLayout, pairs: list[tuple[str, Any]]) -> None:
        grid_frame = QFrame()
        grid_frame.setObjectName("diagnosticInfoGrid")
        grid = QGridLayout(grid_frame)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(SPACING_12)
        grid.setVerticalSpacing(SPACING_8)
        for row, (label_text, value) in enumerate(pairs):
            label = QLabel(label_text)
            label.setProperty("class", "diagnosticMetricLabel")
            val = QLabel(_display(value))
            val.setProperty("class", "diagnosticBodyText")
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            val.setWordWrap(True)
            grid.addWidget(label, row, 0)
            grid.addWidget(val, row, 1)
        layout.addWidget(grid_frame)

    def _source_tooltip(self, sources: list[Any]) -> str:
        lines: list[str] = []
        for source in sources:
            item = _as_dict(source)
            if not item:
                continue
            lines.append(
                f"{_display(item.get('chart_name'))} / {_feature_text(item.get('feature_set'))}: "
                f"{_display(item.get('metric_snapshot'))}"
            )
        return "\n".join(lines)

    def _flatten_check_items(self, relation: dict[str, Any]) -> list[str]:
        out: list[str] = []
        for group in _as_list(relation.get("check_items")):
            item = _as_dict(group)
            category = _display(item.get("category"))
            for check in _as_list(item.get("items"))[:3]:
                out.append(f"{category}：{check}")
        return out

    def _reason_counts(self, candidates: list[Any]) -> list[tuple[str, int]]:
        counts: dict[str, int] = {}
        for raw in candidates:
            candidate = _as_dict(raw)
            if not candidate:
                continue
            reason = self._candidate_reason(candidate)
            if reason == "—":
                continue
            counts[reason] = counts.get(reason, 0) + 1
        return sorted(counts.items(), key=lambda item: (-item[1], item[0]))

    def _render_overview(self, layout: QVBoxLayout, matrix: dict[str, Any], fallback: list[Any]) -> None:
        summary = _as_dict(matrix.get("summary"))
        coverage = _as_dict(matrix.get("coverage"))
        if not summary and not coverage:
            self._render_fallback_tab(layout, fallback)
            return

        confidence = _as_dict(summary.get("confidence"))
        confidence_level = str(confidence.get("level") or "neutral")
        confidence_state = {
            "high": "support",
            "medium": "warning",
            "low": "neutral",
            "observation": "neutral",
        }.get(confidence_level, "neutral")
        scope = _as_dict(matrix.get("filter_scope"))
        self._add_banner(
            layout,
            "診斷結論",
            _display(summary.get("verdict_zh")),
            [
                ("信心", _display(confidence.get("label_zh")), confidence_state),
                ("覆蓋", _display(summary.get("coverage_line_zh")), "neutral"),
                ("範圍", _display(scope.get("scope_zh") or "全批/全元件"), "neutral"),
            ],
        )

        counts = _as_dict(coverage.get("availability_counts"))
        self._add_metric_grid(
            layout,
            [
                ("候選組合", coverage.get("candidate_count", 0)),
                ("適用組合", coverage.get("applicable_candidate_count", 0)),
                ("已覆蓋組合", coverage.get("covered_candidate_count", 0)),
                (
                    "缺資料/不可用",
                    f"{int(counts.get('missing-data') or 0)} / {int(counts.get('unavailable') or 0)}",
                ),
            ],
        )

        evidence = self._section(layout, "主要證據")
        top = [_as_dict(item) for item in _as_list(summary.get("top_evidence")) if _as_dict(item)]
        if top:
            for item in top[:_TOP_EVIDENCE_LIMIT]:
                evidence.addWidget(self._evidence_row(item))
        else:
            evidence.addWidget(self._plain_label("目前未形成可支持製程異常的組合證據。", muted=True))

        limits = self._section(layout, "診斷限制")
        self._add_bullets(limits, self._diagnostic_limitations(summary, coverage))
        self._render_readable_table(
            layout,
            "白話判讀",
            self._readable_rows(matrix, "overview"),
            limit=5,
        )

    def _render_combination_matrix(
        self,
        layout: QVBoxLayout,
        matrix: dict[str, Any],
        fallback: list[Any],
    ) -> None:
        raw_candidates = _as_list(matrix.get("candidates"))
        candidates = [_as_dict(item) for item in raw_candidates if _as_dict(item)]
        if not candidates:
            self._render_fallback_tab(layout, fallback)
            return

        candidates.sort(key=self._candidate_sort_key)
        shown = candidates[:_COMBINATION_DISPLAY_LIMIT]
        table = self._build_table(["特徵", "圖表", "圖表分類", "適用狀態", "證據維度", "判讀", "關鍵數值", "不適用/缺資料原因"])
        table.setRowCount(len(shown))
        self._configure_table_columns(
            table,
            {
                0: DIAGNOSTIC_MATRIX_FEATURE_COL_WIDTH,
                1: DIAGNOSTIC_MATRIX_CHART_COL_WIDTH,
                2: DIAGNOSTIC_MATRIX_FAMILY_COL_WIDTH,
                3: DIAGNOSTIC_MATRIX_STATUS_COL_WIDTH,
                4: DIAGNOSTIC_MATRIX_DIMENSION_COL_WIDTH,
                5: DIAGNOSTIC_MATRIX_VERDICT_COL_WIDTH,
                6: DIAGNOSTIC_MATRIX_METRIC_COL_WIDTH,
                7: DIAGNOSTIC_MATRIX_REASON_COL_WIDTH,
            },
            stretch_cols={1, 6, 7},
            fixed_cols={2, 3, 4, 5},
        )

        for row, candidate in enumerate(shown):
            state = str(candidate.get("evidence_state") or "neutral")
            availability = str(candidate.get("availability") or "unavailable")
            metric = _normalize_metric_text(candidate.get("metric_snapshot"))
            values = [
                _feature_text(candidate.get("feature_set")),
                candidate.get("chart_name"),
                candidate.get("chart_family"),
                None,
                self._dimension_label(matrix, candidate.get("evidence_dimension")),
                None,
                None,
                self._candidate_reason(candidate),
            ]
            for col, value in enumerate(values):
                if col in (3, 5):
                    continue
                if col == 6:
                    table.setItem(row, col, self._metric_item(metric))
                else:
                    table.setItem(row, col, self._table_item(value))
            self._set_badge_cell(
                table,
                row,
                3,
                self._availability_label(candidate),
                availability,
                subtle=availability == "analyzed",
            )
            self._set_badge_cell(table, row, 5, self._state_label(state), state)
            payload_path = str(candidate.get("payload_path") or "")
            if payload_path:
                metric_item = table.item(row, 6)
                if metric_item is not None:
                    current_tip = metric_item.toolTip()
                    metric_item.setToolTip(
                        f"{current_tip}\nPayload: {payload_path}".strip()
                    )

        self._fit_table_height(table)
        layout.addWidget(table)
        layout.addWidget(
            self._plain_label(
                f"目前顯示前 {len(shown)} 筆 / 全部 {len(candidates)} 筆；排序：支持與不支持假設優先，缺資料與不適用置後。",
                muted=True,
            )
        )
        self._render_readable_table(
            layout,
            "白話判讀",
            self._readable_rows(matrix, "combination_matrix"),
        )

    def _render_evidence_matrix(
        self,
        layout: QVBoxLayout,
        matrix: dict[str, Any],
        fallback: list[Any],
    ) -> None:
        rows = [_as_dict(item) for item in _as_list(matrix.get("evidence_matrix")) if _as_dict(item)]
        dims = [str(dim) for dim in _as_list(matrix.get("dimension_order")) if str(dim).strip()]
        if not rows or not dims:
            self._render_fallback_tab(layout, fallback)
            return

        headers = ["圖表分類", *(self._dimension_label(matrix, dim) for dim in dims)]
        table = self._build_table(headers)
        table.setRowCount(len(rows))
        widths = {0: DIAGNOSTIC_MATRIX_FAMILY_COL_WIDTH}
        widths.update(
            {col: DIAGNOSTIC_MATRIX_EVIDENCE_DIM_COL_WIDTH for col in range(1, len(headers))}
        )
        self._configure_table_columns(
            table,
            widths,
            stretch_cols=set(range(1, len(headers))),
            fixed_cols={0},
            minimum_section_width=DIAGNOSTIC_MATRIX_EVIDENCE_DIM_COL_WIDTH,
        )

        for row_idx, row in enumerate(rows):
            table.setItem(row_idx, 0, self._table_item(row.get("chart_family")))
            cells = _as_dict(row.get("cells"))
            for col_idx, dim in enumerate(dims, start=1):
                cell = _as_dict(cells.get(dim))
                state = str(cell.get("state") or "neutral")
                count = int(cell.get("support_count") or cell.get("count") or 0)
                label = "—" if count == 0 else f"{self._matrix_cell_state_label(state)} {count}"
                badge_state = "no-data" if count == 0 else state
                badge = self._badge(label, badge_state)
                tooltip = self._source_tooltip(_as_list(cell.get("top_sources")))
                full_state = f"{self._state_label(state)} {count}" if count else "無證據"
                badge.setToolTip(f"{full_state}\n{tooltip}".strip() if tooltip else full_state)
                table.setCellWidget(row_idx, col_idx, badge)

        self._fit_table_height(table)
        layout.addWidget(table)
        layout.addWidget(self._plain_label("儲存格數字為該分類與證據維度的候選組合數；滑鼠停留可看代表圖表。", muted=True))
        self._render_readable_table(
            layout,
            "矩陣判讀說明",
            self._readable_rows(matrix, "evidence_matrix"),
            limit=16,
        )

    def _render_correlation(
        self,
        layout: QVBoxLayout,
        matrix: dict[str, Any],
        fallback: list[Any],
    ) -> None:
        relation = _as_dict(matrix.get("relation"))
        summary = _as_dict(matrix.get("summary"))
        coverage = _as_dict(matrix.get("coverage"))
        corr = _as_dict(relation.get("correlation"))
        if not relation and not corr:
            self._render_fallback_tab(layout, fallback)
            return

        self._add_banner(
            layout,
            "關聯模式",
            _display(corr.get("pattern_detail")),
            [
                ("模式", _display(corr.get("pattern_label")), "support"),
                ("訊號", _display(corr.get("signal_count")), "neutral"),
            ],
        )

        causes = [_as_dict(item) for item in _as_list(relation.get("cause_hypotheses")) if _as_dict(item)]
        cause_section = self._section(layout, "根因假設")
        if causes:
            table = self._build_table(["類別", "說明"])
            table.setRowCount(len(causes))
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            for row, cause in enumerate(causes):
                table.setItem(row, 0, self._table_item(cause.get("category")))
                table.setItem(row, 1, self._table_item(cause.get("description")))
            self._fit_table_height(table)
            cause_section.addWidget(table)
        else:
            cause_section.addWidget(self._plain_label("目前沒有足夠關聯訊號形成根因假設。", muted=True))

        limit_section = self._section(layout, "信心限制與衝突訊號")
        conflicts = [str(item) for item in _as_list(summary.get("conflicts")) if str(item).strip()]
        lines = conflicts or self._diagnostic_limitations(summary, coverage)
        self._add_bullets(limit_section, lines)
        self._render_readable_table(
            layout,
            "白話判讀",
            self._readable_rows(matrix, "correlation"),
        )

    def _next_step_reason(self, candidate: dict[str, Any]) -> str:
        dimension = str(candidate.get("evidence_dimension") or "")
        reasons = {
            "capability_risk": "確認規格邊界、Cp/Cpk 與失效比例是否集中在此特徵。",
            "center_shift": "確認中心偏移是否連續發生，並回查對位、刮刀與印刷條件。",
            "variation": "確認變異放大是否由設備、材料或量測系統造成。",
            "stability_drift": "確認漂移是否跨時間延續，避免只看單點異常。",
            "local_cluster": "回查 OOC/OOS 是否集中在特定位號、區域或 PCB 條件。",
            "distribution": "確認非常態或偏態是否影響能力判讀可信度。",
            "multi_feature_correlation": "確認特徵間連動是否對應相同製程來源。",
            "data_confidence": "補強資料完整性後再升高判讀信心。",
        }
        return reasons.get(dimension, "回看此圖表以補強製程異常鏈判讀。")

    def _render_chart_linkage(
        self,
        layout: QVBoxLayout,
        matrix: dict[str, Any],
        fallback: list[Any],
    ) -> None:
        rows = self._readable_rows(matrix, "chart_linkage")
        if not rows:
            self._render_fallback_tab(layout, fallback)
            return

        section = self._section(layout, "下一步圖表")
        table = self._build_table(["建議圖表", "判讀結果", "由哪個證據觸發", "要確認/排除", "看完後下一步"])
        shown = rows[:_LINKAGE_DISPLAY_LIMIT]
        table.setRowCount(len(shown))
        self._configure_table_columns(
            table,
            {
                0: DIAGNOSTIC_MATRIX_CHART_COL_WIDTH,
                1: DIAGNOSTIC_MATRIX_VERDICT_COL_WIDTH,
                2: DIAGNOSTIC_MATRIX_METRIC_COL_WIDTH,
                3: DIAGNOSTIC_MATRIX_METRIC_COL_WIDTH,
                4: DIAGNOSTIC_MATRIX_LINK_REASON_COL_WIDTH,
            },
            stretch_cols={2, 3, 4},
            fixed_cols={0, 1},
        )
        for row_idx, row in enumerate(shown):
            table.setItem(row_idx, 0, self._table_item(row.get("title")))
            table.setItem(row_idx, 1, self._table_item(row.get("result_zh")))
            table.setItem(row_idx, 2, self._table_item(row.get("source_zh")))
            table.setItem(row_idx, 3, self._table_item(row.get("reason_zh")))
            table.setItem(row_idx, 4, self._table_item(row.get("next_action_zh")))
        self._fit_table_height(table)
        section.addWidget(table)

        # Navigation chips: "→ 前往圖表頁" for each next_chart_id
        summary = _as_dict(_as_dict(matrix).get("summary"))
        next_ids: list[str] = [str(x) for x in _as_list(summary.get("next_chart_ids")) if str(x).strip()]
        top_ev = _as_list(summary.get("top_evidence"))
        feat_by_chart = {str(item.get("chart_id") or ""): _as_list(item.get("feature_set")) for item in top_ev if isinstance(item, dict)}

        if next_ids:
            chip_container = QWidget()
            chip_layout = QHBoxLayout(chip_container)
            chip_layout.setContentsMargins(0, SPACING_4, 0, 0)
            chip_layout.setSpacing(SPACING_4)
            chip_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
            nav_label = QLabel("→ 前往圖表頁檢視：")
            chip_layout.addWidget(nav_label)
            for chart_id in next_ids[:_LINKAGE_DISPLAY_LIMIT]:
                chart_name = _get_chart_display_name(chart_id, "zh_only")
                feature_set = feat_by_chart.get(chart_id, [])
                btn = QPushButton(chart_name)
                btn.setProperty("class", "recoChip")
                btn.setToolTip(f"前往圖表頁並選取：{chart_name}")
                btn.clicked.connect(
                    lambda _checked=False, cid=chart_id, fs=list(feature_set):
                        self.navigate_to_chart.emit(cid, fs)
                )
                chip_layout.addWidget(btn)
            chip_layout.addStretch(1)
            section.addWidget(chip_container)

    def _render_actions(self, layout: QVBoxLayout, matrix: dict[str, Any], fallback: list[Any]) -> None:
        relation = _as_dict(matrix.get("relation"))
        candidates = [_as_dict(item) for item in _as_list(matrix.get("candidates")) if _as_dict(item)]
        support = [item for item in candidates if item.get("evidence_state") == "support"]
        support.sort(key=self._candidate_sort_key)
        if not relation and not candidates:
            self._render_fallback_tab(layout, fallback)
            return

        urgent = [
            (
                f"{_display(item.get('chart_name'))} / {_feature_text(item.get('feature_set'))}："
                f"回查 {_display(item.get('metric_snapshot'))}"
            )
            for item in support
            if str(item.get("severity") or "") in {"error", "warning"}
        ][:5]
        if not urgent and support:
            urgent = [
                f"{_display(item.get('chart_name'))} / {_feature_text(item.get('feature_set'))}：確認支持證據來源。"
                for item in support[:3]
            ]
        if not urgent:
            urgent = ["先補資料/補圖表判讀，不直接判根因。"]

        checks = self._flatten_check_items(relation)
        if not checks:
            checks = [
                "確認鋼板厚度、錫膏批次、刮刀壓力與印刷條件是否與 SOP 一致。",
                "回查 OOC/OOS 是否集中於特定位號、區域或時間窗口。",
            ]

        neutral = [
            f"{_display(item.get('chart_name'))} / {_feature_text(item.get('feature_set'))}：維持監控。"
            for item in candidates
            if item.get("evidence_state") == "neutral" and item.get("availability") == "analyzed"
        ][:5]
        if not neutral:
            neutral = ["維持現有監控，等待新增批次資料後重跑診斷。"]

        self._add_bullets(self._section(layout, "立即確認"), urgent)
        self._add_bullets(self._section(layout, "補充檢查"), checks[:8])
        self._add_bullets(self._section(layout, "持續監控"), neutral)
        self._render_readable_table(
            layout,
            "白話判讀",
            self._readable_rows(matrix, "actions"),
        )

    def _render_data_context(
        self,
        layout: QVBoxLayout,
        matrix: dict[str, Any],
        fallback: list[Any],
    ) -> None:
        coverage = _as_dict(matrix.get("coverage"))
        candidates = _as_list(matrix.get("candidates"))
        if not coverage and not candidates:
            self._render_fallback_tab(layout, fallback)
            return

        scope = _as_dict(matrix.get("filter_scope"))
        scope_section = self._section(layout, "資料範圍")
        self._add_info_pairs(
            scope_section,
            [
                ("產品/線別", "；".join(part for part in [str(scope.get("product") or ""), str(scope.get("line") or "")] if part) or "—"),
                ("批次/範圍", scope.get("batch") or "全批"),
                ("元件/類別", "；".join(part for part in [str(scope.get("refdes") or ""), str(scope.get("part_type") or "")] if part) or "全元件"),
                ("時間", f"{scope.get('time_start') or '—'} ~ {scope.get('time_end') or '—'}"),
            ],
        )

        counts = _as_dict(coverage.get("availability_counts"))
        self._add_metric_grid(
            layout,
            [
                ("候選組合", coverage.get("candidate_count", len(candidates))),
                ("適用組合", coverage.get("applicable_candidate_count", 0)),
                ("已覆蓋組合", coverage.get("covered_candidate_count", 0)),
                ("不適用", counts.get("not-applicable", 0)),
                ("缺資料", counts.get("missing-data", 0)),
                ("不可用", counts.get("unavailable", 0)),
                ("可用未選", counts.get("available-not-selected", 0)),
                ("已分析", counts.get("analyzed", 0)),
            ],
        )

        gap_section = self._section(layout, "缺口原因")
        reason_counts = self._reason_counts(candidates)
        if reason_counts:
            table = self._build_table(["原因", "筆數"])
            shown = reason_counts[:10]
            table.setRowCount(len(shown))
            self._configure_table_columns(
                table,
                {0: DIAGNOSTIC_MATRIX_REASON_COL_WIDTH, 1: DIAGNOSTIC_MATRIX_GAP_COUNT_COL_WIDTH},
                stretch_cols={0},
                fixed_cols={1},
            )
            for row, (reason, count) in enumerate(shown):
                table.setItem(row, 0, self._table_item(reason))
                table.setItem(row, 1, self._table_item(count))
            self._fit_table_height(table)
            gap_section.addWidget(table)
        else:
            gap_section.addWidget(self._plain_label("目前沒有主要缺資料或不適用原因。", muted=True))

        tech_section = self._section(layout, "技術資訊")
        display_mode = _as_dict(matrix.get("display_mode"))
        self._add_info_pairs(
            tech_section,
            [
                ("Schema", matrix.get("schema_version")),
                ("特徵數", matrix.get("selected_feature_count")),
                ("特徵", _feature_text(matrix.get("selected_features"))),
                ("Display mode", "；".join(f"{key}={value}" for key, value in display_mode.items()) or "—"),
            ],
        )
        self._render_readable_table(
            layout,
            "白話判讀",
            self._readable_rows(matrix, "data_context"),
        )

    def update_hints(self, payload: dict[str, Any]) -> None:
        """Update the matrix tabs from the analysis payload."""
        self._last_payload = payload or {}
        matrix = self._last_payload.get("diagnostic_evidence_matrix")
        if not matrix:
            self._lamp.setProperty("state", "idle")
            self._status_lbl.setText("尚待分析數據...")
            self._lamp.style().unpolish(self._lamp)
            self._lamp.style().polish(self._lamp)
            self._update_matrix_tabs(None)
            return

        self._lamp.setProperty("state", "success")
        self._lamp.style().unpolish(self._lamp)
        self._lamp.style().polish(self._lamp)
        self._status_lbl.setText("分析完成")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._updated_lbl.setText(f"最後更新: {now}")
        self._update_matrix_tabs(matrix)

    def _update_matrix_tabs(self, matrix: Any) -> None:
        """Render the diagnostic evidence matrix from structured payload fields."""
        matrix_dict = _as_dict(matrix)
        tabs = _as_dict(matrix_dict.get("tabs"))
        renderers = {
            "overview": self._render_overview,
            "combination_matrix": self._render_combination_matrix,
            "evidence_matrix": self._render_evidence_matrix,
            "correlation": self._render_correlation,
            "chart_linkage": self._render_chart_linkage,
            "actions": self._render_actions,
            "data_context": self._render_data_context,
        }
        for key, layout in self._matrix_tab_layouts.items():
            self._clear_layout(layout)
            fallback = _as_list(tabs.get(key))
            renderer = renderers.get(key)
            if not matrix_dict or renderer is None:
                self._render_fallback_tab(layout, fallback or ["—"])
                continue
            renderer(layout, matrix_dict, fallback)
        self._matrix_tabs.updateGeometry()
        self._sync_matrix_tabs_height()
        QTimer.singleShot(0, self._sync_matrix_tabs_height)
