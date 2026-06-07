"""Reusable card + KPI grid cells for the process diagnostic dashboard (`DiagnosticPage`)."""

from __future__ import annotations

from typing import Literal, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from app.ui.theme.tokens import (
    PROCESS_DASH_CARD_MARGIN,
    PROCESS_DASH_GRID_H_SPACING,
    PROCESS_DASH_GRID_V_SPACING,
    PROCESS_DASH_SECTION_GAP,
    SPACING_4,
)
from app.analytics.dashboard_layers_display import feature_label_zh

KpiTier = Literal["large", "medium", "small"]

__all__ = [
    "KpiTier",
    "feature_label_zh",
    "build_process_card",
    "build_alarm_summary_card",
    "build_process_report_panel",
    "add_report_section",
    "add_report_metric",
    "set_alarm_tone",
    "add_kpi_cell",
    "apply_value_state",
    "set_value_text",
]


def build_process_card(title: str) -> Tuple[QFrame, QGridLayout]:
    """Standard elevated card with bold title and inner grid (2–4 columns)."""
    card = QFrame()
    card.setObjectName("processDashCard")
    outer = QVBoxLayout(card)
    m = PROCESS_DASH_CARD_MARGIN
    outer.setContentsMargins(m, m, m, m)
    outer.setSpacing(PROCESS_DASH_SECTION_GAP)

    title_lbl = QLabel(title)
    title_lbl.setWordWrap(True)
    title_lbl.setProperty("class", "processDashCardTitle")
    outer.addWidget(title_lbl)

    grid = QGridLayout()
    grid.setHorizontalSpacing(PROCESS_DASH_GRID_H_SPACING)
    grid.setVerticalSpacing(PROCESS_DASH_GRID_V_SPACING)
    outer.addLayout(grid)
    return card, grid


def build_alarm_summary_card(title: str) -> Tuple[QFrame, QGridLayout]:
    """Alarm card: whole-frame background follows alarmTone (QSS)."""
    card = QFrame()
    card.setObjectName("processAlarmCard")
    card.setProperty("alarmTone", "normal")
    outer = QVBoxLayout(card)
    m = PROCESS_DASH_CARD_MARGIN
    outer.setContentsMargins(m, m, m, m)
    outer.setSpacing(PROCESS_DASH_SECTION_GAP)

    title_lbl = QLabel(title)
    title_lbl.setWordWrap(True)
    title_lbl.setProperty("class", "processDashCardTitle")
    outer.addWidget(title_lbl)

    grid = QGridLayout()
    grid.setHorizontalSpacing(PROCESS_DASH_GRID_H_SPACING)
    grid.setVerticalSpacing(PROCESS_DASH_GRID_V_SPACING)
    outer.addLayout(grid)
    return card, grid


def build_process_report_panel(title: str) -> Tuple[QFrame, QGridLayout]:
    """Flat report panel for process-statistics output."""
    panel = QFrame()
    panel.setObjectName("processStatReport")
    panel.setProperty("alarmTone", "normal")
    outer = QVBoxLayout(panel)
    m = PROCESS_DASH_CARD_MARGIN
    outer.setContentsMargins(m, m, m, m)
    outer.setSpacing(PROCESS_DASH_SECTION_GAP)

    title_lbl = QLabel(title)
    title_lbl.setWordWrap(True)
    title_lbl.setProperty("class", "processReportTitle")
    title_lbl.setMinimumWidth(0)
    title_lbl.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
    outer.addWidget(title_lbl)

    grid = QGridLayout()
    grid.setHorizontalSpacing(PROCESS_DASH_GRID_H_SPACING)
    grid.setVerticalSpacing(PROCESS_DASH_GRID_V_SPACING)
    for col in range(4):
        grid.setColumnStretch(col, 1)
    outer.addLayout(grid)
    return panel, grid


def add_report_section(grid: QGridLayout, row: int, title: str) -> None:
    label = QLabel(title)
    label.setWordWrap(True)
    label.setProperty("class", "processReportSectionLabel")
    label.setMinimumWidth(0)
    label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
    grid.addWidget(label, row, 0, 1, 4)


def add_report_metric(
    grid: QGridLayout,
    row: int,
    col: int,
    label_zh: str,
    source_layer: str,
    *,
    colspan: int = 1,
    tier: KpiTier = "small",
) -> QLabel:
    """Add a table-like report metric with a visible data-source label."""
    cell = QFrame()
    cell.setProperty("class", "processReportMetric")
    cell.setProperty("sourceLayer", source_layer)
    cell.setMinimumWidth(0)
    cell.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    lay = QVBoxLayout(cell)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(SPACING_4)

    lab = QLabel(label_zh)
    lab.setProperty("class", "processDashFieldLabel")
    lab.setWordWrap(True)
    lab.setMinimumWidth(0)
    lab.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    val = QLabel("—")
    val.setTextFormat(Qt.TextFormat.PlainText)
    val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    val.setWordWrap(True)
    val.setMinimumWidth(0)
    val.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
    val.setProperty("class", "processDashStatSmall")
    val.setProperty("valueState", "neutral")
    val.setProperty("sourceLayer", source_layer)

    src = QLabel(source_layer)
    src.setTextFormat(Qt.TextFormat.PlainText)
    src.setWordWrap(True)
    src.setProperty("class", "processReportSource")
    src.setMinimumWidth(0)
    src.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    tooltip = f"{label_zh}｜資料來源：{source_layer}"
    cell.setToolTip(tooltip)
    lab.setToolTip(tooltip)
    val.setToolTip(tooltip)
    src.setToolTip(tooltip)

    lay.addWidget(lab)
    lay.addWidget(val)
    lay.addWidget(src)
    grid.addWidget(cell, row, col, 1, colspan)
    return val


def set_alarm_tone(card: QFrame, tone: str) -> None:
    safe = tone if tone in ("normal", "warning", "critical") else "normal"
    card.setProperty("alarmTone", safe)
    card.style().unpolish(card)
    card.style().polish(card)


def add_kpi_cell(
    grid: QGridLayout,
    row: int,
    col: int,
    label_zh: str,
    *,
    colspan: int = 1,
    tier: KpiTier = "medium",
) -> QLabel:
    """Add label + value column; returns the value QLabel for updates."""
    cell = QWidget()
    lay = QVBoxLayout(cell)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(SPACING_4)

    lab = QLabel(label_zh)
    lab.setProperty("class", "processDashFieldLabel")
    lab.setWordWrap(True)

    val = QLabel("—")
    val.setTextFormat(Qt.TextFormat.PlainText)
    val.setWordWrap(True)
    tier_class = {
        "large": "processDashKpiValueLarge",
        "medium": "processDashKpiValueMedium",
        "small": "processDashStatSmall",
    }[tier]
    val.setProperty("class", tier_class)
    val.setProperty("valueState", "neutral")

    lay.addWidget(lab)
    lay.addWidget(val)
    grid.addWidget(cell, row, col, 1, colspan)
    return val


def apply_value_state(val: QLabel, state: str | None) -> None:
    """Map layer_*_state strings OR direct QSS valueState to QLabel property.

    Accepts both layer state strings ("Normal"/"Warning"/"Alarm"/"Info")
    and direct QSS valueState strings ("good"/"warning"/"bad"/"neutral").
    """
    key = state or "Info"
    _direct = {"good", "warning", "bad", "neutral"}
    if key in _direct:
        qss_state = key
    else:
        m = {"Normal": "good", "Warning": "warning", "Alarm": "bad", "Info": "neutral"}
        qss_state = m.get(key, "neutral")
    val.setProperty("valueState", qss_state)
    val.style().unpolish(val)
    val.style().polish(val)


def set_value_text(val: QLabel, text: str) -> None:
    val.setText(text)
