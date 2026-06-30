from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
    QStyle,
)

from app.analytics.chart_registry import (
    get_chart_display_name,
    get_text_summary_charts,
    resolve_chart_payload,
)
from app.ui.theme.tokens import (
    SPACING_4,
    SPACING_8,
    STAT_DATA_CONTEXT_MAX_HEIGHT,
    STAT_DATA_HEADER_MAX_HEIGHT,
    STAT_DATA_ITEM_COLUMN_WIDTH,
    STAT_DATA_METRIC_COLUMN_WIDTH,
    STAT_DATA_PRIMARY_COLUMN_WIDTH,
    STAT_DATA_SOURCE_COLUMN_WIDTH,
    STAT_DATA_STATUS_COLUMN_WIDTH,
    STAT_DATA_TABLE_HEADER_BUFFER,
    STAT_DATA_ICON_SIZE,
    STAT_DATA_TABLE_MIN_VISIBLE_ROWS,
    STAT_DATA_TABLE_ROW_HEIGHT,
)
from app.ui.widgets.page_templates import (
    create_status_badge,
    empty_state_label,
    page_margins_and_spacing,
    setup_compact_title_header,
    style_table,
)
from app.utils.constants import FEATURE_COLUMNS
from app.utils.numeric_utils import safe_float, safe_int


@dataclass(frozen=True)
class StatisticsSummaryRow:
    chart_id: str
    title: str
    status: str
    status_state: str
    primary: str
    metric: str
    threshold: str
    source: str
    summary: str
    icon: QStyle.StandardPixmap


class StatisticsDataPage(QWidget):
    """One-page data browser for text-only statistical summary outputs."""

    _COLUMNS = ["項目", "狀態", "主要數值", "比率/幅度", "門檻", "資料來源", "摘要"]

    _ICON_BY_ID: dict[str, QStyle.StandardPixmap] = {
        "ooc_analysis": QStyle.StandardPixmap.SP_MessageBoxWarning,
        "shift_detection": QStyle.StandardPixmap.SP_ArrowRight,
        "drift_detection": QStyle.StandardPixmap.SP_BrowserReload,
        "outlier_analysis": QStyle.StandardPixmap.SP_FileDialogDetailedView,
    }
    _STATUS_RANK = {
        "alarm": 3,
        "alarm drift": 3,
        "persistent shift": 3,
        "warning": 2,
        "warning drift": 2,
        "local shift": 2,
        "normal": 1,
        "stable": 1,
        "none": 1,
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._last_payload: dict[str, Any] = {}
        self._active_features: list[str] = []
        self._row_by_chart_id: dict[str, int] = {}
        self._pending_select_chart_id = ""

        layout = QVBoxLayout(self)
        page_margins_and_spacing(layout)
        header_label = setup_compact_title_header(layout, "統計資料")
        header_frame = header_label.parentWidget()
        if header_frame is not None:
            header_frame.setMaximumHeight(STAT_DATA_HEADER_MAX_HEIGHT)
            header_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.context_strip = QLabel("尚未載入分析資料")
        self.context_strip.setWordWrap(False)
        self.context_strip.setProperty("class", "chartDetailsStrip")
        self.context_strip.setMaximumHeight(STAT_DATA_CONTEXT_MAX_HEIGHT)
        self.context_strip.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.context_strip)

        self.table = QTableWidget(0, len(self._COLUMNS))
        self.table.setObjectName("statisticsDataTable")
        self.table.setHorizontalHeaderLabels(self._COLUMNS)
        self.table.setIconSize(QSize(STAT_DATA_ICON_SIZE, STAT_DATA_ICON_SIZE))
        self.table.setAlternatingRowColors(True)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.verticalHeader().setDefaultSectionSize(STAT_DATA_TABLE_ROW_HEIGHT)
        self.table.verticalHeader().setMinimumSectionSize(STAT_DATA_TABLE_ROW_HEIGHT)
        self.table.setWordWrap(True)
        style_table(self.table, role="diagnostic")
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table.setMinimumHeight(
            STAT_DATA_TABLE_ROW_HEIGHT * STAT_DATA_TABLE_MIN_VISIBLE_ROWS
            + STAT_DATA_TABLE_HEADER_BUFFER
        )
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, STAT_DATA_ITEM_COLUMN_WIDTH)
        self.table.setColumnWidth(1, STAT_DATA_STATUS_COLUMN_WIDTH)
        self.table.setColumnWidth(2, STAT_DATA_PRIMARY_COLUMN_WIDTH)
        self.table.setColumnWidth(3, STAT_DATA_METRIC_COLUMN_WIDTH)
        self.table.setColumnWidth(5, STAT_DATA_SOURCE_COLUMN_WIDTH)
        layout.addWidget(self.table, 1)

        self.empty_hint = empty_state_label("請先完成分析")
        self.empty_hint.setVisible(True)
        layout.addWidget(self.empty_hint)

        self._populate_rows([])

    def update_all_statistics(self, payload: dict) -> None:
        """Refresh the text-summary browser from the current analysis payload."""
        self._last_payload = payload or {}
        self._active_features = self._resolve_active_features(self._last_payload)
        rows = self._build_summary_rows()
        self._populate_rows(rows)
        self._sync_context_strip(rows)
        self.empty_hint.setVisible(not rows)
        if self._pending_select_chart_id:
            self.select_summary(self._pending_select_chart_id)

    def select_summary(self, chart_id: str, feature_set: list[str] | None = None) -> None:
        """Highlight a summary row, used by diagnostic cross-page navigation."""
        self._pending_select_chart_id = chart_id
        if feature_set:
            self._active_features = [str(f) for f in feature_set if str(f).strip()]
        row = self._row_by_chart_id.get(chart_id)
        if row is None:
            return
        self.table.selectRow(row)
        self.table.setCurrentCell(row, 0)

    def _resolve_active_features(self, payload: dict[str, Any]) -> list[str]:
        selected = [str(f) for f in (payload or {}).get("selected_features", []) if str(f).strip()]
        params = (payload or {}).get("parameters", {}) or {}
        if isinstance(params, dict) and params:
            ordered = [feature for feature in FEATURE_COLUMNS if feature in params]
            if ordered:
                return ordered
        return selected

    def _build_summary_rows(self) -> list[StatisticsSummaryRow]:
        if not self._last_payload:
            return []
        feature_scope = self._active_features or list((self._last_payload or {}).get("selected_features") or [])
        rows: list[StatisticsSummaryRow] = []
        for item in get_text_summary_charts(feature_scope):
            chart_id = str(item.get("id") or "")
            data = resolve_chart_payload(
                self._last_payload,
                chart_id,
                features=feature_scope,
                context="ui",
            )
            rows.append(self._row_from_payload(chart_id, data))
        return rows

    def _row_from_payload(self, chart_id: str, payload: dict[str, Any]) -> StatisticsSummaryRow:
        if not (payload.get("metadata") or {}).get("is_valid", False):
            reason = str((payload.get("metadata") or {}).get("error") or "資料不足。")
            return StatisticsSummaryRow(
                chart_id=chart_id,
                title=get_chart_display_name(chart_id, lang="zh_only"),
                status="資料不足",
                status_state="nodata",
                primary="資料不足",
                metric="—",
                threshold="—",
                source=self._source_label(payload),
                summary=reason,
                icon=self._ICON_BY_ID.get(chart_id, QStyle.StandardPixmap.SP_MessageBoxInformation),
            )

        feature_payloads = payload.get("_feature_data") if isinstance(payload.get("_feature_data"), dict) else None
        if feature_payloads:
            payloads = [p for p in feature_payloads.values() if isinstance(p, dict)]
        else:
            payloads = [payload]

        if chart_id == "ooc_analysis":
            return self._build_count_ratio_row(
                chart_id,
                payloads,
                count_key="ooc_count",
                total_keys=("n",),
                ratio_key="ooc_ratio",
                status_key="severity",
                primary_label="OOC",
                threshold="warning > 0%, alarm >= 10%",
            )
        if chart_id == "shift_detection":
            return self._build_count_ratio_row(
                chart_id,
                payloads,
                count_key="ooc_count",
                total_keys=("n",),
                ratio_key="ooc_ratio",
                status_key="shift_level",
                primary_label="CUSUM OOC",
                threshold="Local > 0%, Persistent >= 10%",
            )
        if chart_id == "drift_detection":
            return self._build_drift_row(chart_id, payloads, payload)
        if chart_id == "outlier_analysis":
            return self._build_count_ratio_row(
                chart_id,
                payloads,
                count_key="outlier_count",
                total_keys=("total_n", "n"),
                ratio_key="outlier_ratio",
                status_key="level",
                primary_label="Outliers",
                threshold="warning > 3%, alarm >= 10%",
            )
        return self._build_generic_row(chart_id, payload)

    def _build_count_ratio_row(
        self,
        chart_id: str,
        payloads: list[dict[str, Any]],
        *,
        count_key: str,
        total_keys: tuple[str, ...],
        ratio_key: str,
        status_key: str,
        primary_label: str,
        threshold: str,
    ) -> StatisticsSummaryRow:
        count_total = 0
        n_total = 0
        status_values: list[str] = []
        summary_lines: list[str] = []
        for payload in payloads:
            data = payload.get("data") or {}
            stats = payload.get("statistics") or {}
            count = self._first_int(data, stats, keys=(count_key,))
            n_value = self._first_int(data, stats, keys=total_keys)
            if count is not None:
                count_total += count
            if n_value is not None:
                n_total += n_value
            status_values.append(str(data.get(status_key) or ""))
            summary_lines.extend(str(x) for x in data.get("summary_lines", []) if str(x).strip())

        ratio = (count_total / n_total) if n_total else None
        status = self._dominant_status(status_values) or "Normal"
        return StatisticsSummaryRow(
            chart_id=chart_id,
            title=get_chart_display_name(chart_id, lang="zh_only"),
            status=self._status_label(status),
            status_state=self._status_state(status),
            primary=f"{primary_label}: {count_total}/{n_total}" if n_total else f"{primary_label}: UNKNOWN/VERIFY",
            metric=f"{ratio:.1%}" if ratio is not None else "UNKNOWN/VERIFY",
            threshold=threshold,
            source=self._source_label(None),
            summary="；".join(summary_lines[:3]) if summary_lines else "—",
            icon=self._ICON_BY_ID.get(chart_id, QStyle.StandardPixmap.SP_MessageBoxInformation),
        )

    def _build_drift_row(
        self,
        chart_id: str,
        payloads: list[dict[str, Any]],
        original_payload: dict[str, Any],
    ) -> StatisticsSummaryRow:
        max_drift: float | None = None
        center_line: float | None = None
        status_values: list[str] = []
        summary_lines: list[str] = []
        for payload in payloads:
            data = payload.get("data") or {}
            stats = payload.get("statistics") or {}
            drift = safe_float(data.get("drift_abs", stats.get("drift_abs")))
            if drift is not None and (max_drift is None or abs(drift) > abs(max_drift)):
                max_drift = drift
                center_line = safe_float(data.get("cl", stats.get("cl")))
            status_values.append(str(data.get("trend_level") or ""))
            summary_lines.extend(str(x) for x in data.get("summary_lines", []) if str(x).strip())

        status = self._dominant_status(status_values) or "Stable"
        rel = None
        if max_drift is not None and center_line is not None:
            denom = abs(center_line) if abs(center_line) > 1e-9 else 1.0
            rel = max_drift / denom
        return StatisticsSummaryRow(
            chart_id=chart_id,
            title=get_chart_display_name(chart_id, lang="zh_only"),
            status=self._status_label(status),
            status_state=self._status_state(status),
            primary=f"Max |EWMA-CL|: {max_drift:.4f}" if max_drift is not None else "Max |EWMA-CL|: UNKNOWN/VERIFY",
            metric=f"{rel:.1%} of CL" if rel is not None else "UNKNOWN/VERIFY",
            threshold="warning >= 10%, alarm >= 20% of CL",
            source=self._source_label(original_payload),
            summary="；".join(summary_lines[:3]) if summary_lines else "—",
            icon=self._ICON_BY_ID.get(chart_id, QStyle.StandardPixmap.SP_MessageBoxInformation),
        )

    def _build_generic_row(self, chart_id: str, payload: dict[str, Any]) -> StatisticsSummaryRow:
        data = payload.get("data") or {}
        summary = "；".join(str(x) for x in data.get("summary_lines", []) if str(x).strip()) or "—"
        return StatisticsSummaryRow(
            chart_id=chart_id,
            title=get_chart_display_name(chart_id, lang="zh_only"),
            status="已產生",
            status_state="success",
            primary="已產生",
            metric="—",
            threshold="—",
            source=self._source_label(payload),
            summary=summary,
            icon=self._ICON_BY_ID.get(chart_id, QStyle.StandardPixmap.SP_MessageBoxInformation),
        )

    def _populate_rows(self, rows: list[StatisticsSummaryRow]) -> None:
        self.table.setRowCount(len(rows))
        self._row_by_chart_id.clear()
        for row_idx, row in enumerate(rows):
            self._row_by_chart_id[row.chart_id] = row_idx
            self.table.setCellWidget(row_idx, 0, self._name_cell(row))
            self.table.setCellWidget(row_idx, 1, create_status_badge(row.status, row.status_state))
            for col_idx, value in enumerate(
                (row.primary, row.metric, row.threshold, row.source, row.summary),
                start=2,
            ):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row_idx, col_idx, item)
            self.table.setRowHeight(row_idx, STAT_DATA_TABLE_ROW_HEIGHT)

    def _name_cell(self, row: StatisticsSummaryRow) -> QWidget:
        cell = QFrame()
        cell.setProperty("class", "statDataNameCell")
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(SPACING_4, SPACING_4, SPACING_4, SPACING_4)
        layout.setSpacing(SPACING_8)
        icon_label = QLabel()
        icon_label.setFixedSize(STAT_DATA_ICON_SIZE, STAT_DATA_ICON_SIZE)
        app = QApplication.instance()
        if isinstance(app, QApplication):
            icon = app.style().standardIcon(row.icon)
            icon_label.setPixmap(icon.pixmap(STAT_DATA_ICON_SIZE, STAT_DATA_ICON_SIZE))
        icon_label.setAccessibleName("")
        icon_label.setAccessibleDescription("裝飾性統計資料圖示，請以相鄰項目名稱為準。")
        layout.addWidget(icon_label)
        title = QLabel(row.title)
        title.setProperty("class", "caption")
        title.setToolTip(row.title)
        layout.addWidget(title, 1)
        return cell

    def _sync_context_strip(self, rows: list[StatisticsSummaryRow]) -> None:
        if not self._last_payload:
            self.context_strip.setText("尚未載入分析資料")
            return
        features = " / ".join(self._active_features) if self._active_features else "未指定"
        ready = sum(1 for row in rows if row.status_state not in {"nodata", "error"})
        text = (
            f"統計資料 | 特徵: {features} | 已產生: {ready}/{len(rows)} 項 | "
            "來源: 文字摘要統計輸出"
        )
        self.context_strip.setText(text)
        self.context_strip.setToolTip(text)

    def _source_label(self, payload: dict[str, Any] | None) -> str:
        features = " / ".join(self._active_features) if self._active_features else "未指定"
        if payload and payload.get("_multi_feature"):
            feature_list = payload.get("_features") or self._active_features
            features = " / ".join(str(x) for x in feature_list)
        return f"特徵: {features}"

    def _dominant_status(self, values: list[str]) -> str:
        best = ""
        best_rank = -1
        for value in values:
            normalized = value.strip().lower()
            rank = self._STATUS_RANK.get(normalized, 0)
            if rank > best_rank:
                best = value.strip()
                best_rank = rank
        return best

    def _status_state(self, status: str) -> str:
        normalized = status.strip().lower()
        rank = self._STATUS_RANK.get(normalized, 0)
        if rank >= 3:
            return "error"
        if rank == 2:
            return "warning"
        if normalized in {"", "unknown", "verify"}:
            return "nodata"
        return "success"

    def _status_label(self, status: str) -> str:
        normalized = status.strip().lower()
        rank = self._STATUS_RANK.get(normalized, 0)
        if rank >= 3:
            return "異常"
        if rank == 2:
            return "警告"
        if normalized in {"normal", "stable", "none"}:
            return "正常"
        if normalized in {"", "unknown", "verify"}:
            return "資料不足"
        return status or "資料不足"

    @staticmethod
    def _first_int(data: dict[str, Any], stats: dict[str, Any], *, keys: tuple[str, ...]) -> int | None:
        for key in keys:
            value = data.get(key)
            if value is None:
                value = stats.get(key)
            converted = safe_int(value)
            if converted is not None:
                return converted
        return None
