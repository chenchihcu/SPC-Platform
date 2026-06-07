"""Tests for DiagnosticPage (unified process diagnosis dashboard)."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QTableWidget, QHeaderView
from PySide6.QtCore import Qt

from app.services.diagnostic_evidence_matrix import build_diagnostic_evidence_matrix
from app.ui.theme.tokens import (
    DIAGNOSTIC_MATRIX_EVIDENCE_DIM_COL_WIDTH,
    DIAGNOSTIC_MATRIX_FAMILY_COL_WIDTH,
    DIAGNOSTIC_MATRIX_GAP_COUNT_COL_WIDTH,
    DIAGNOSTIC_MATRIX_MAX_VISIBLE_ROWS,
    DIAGNOSTIC_MATRIX_STATUS_COL_WIDTH,
    DIAGNOSTIC_MATRIX_VERDICT_COL_WIDTH,
    FONT_SIZE_DASH_LABEL,
    FONT_SIZE_PROCESS_DASH_KPI,
    FONT_SIZE_PROCESS_DASH_KPI_MEDIUM,
    FONT_SIZE_PROCESS_DASH_STAT,
    TABLE_ROW_MIN_HEIGHT,
)
from app.ui.pages.diagnostic_page import DiagnosticPage
from tests.test_diagnostic_evidence_matrix import _payload


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _minimal_dashboard_payload() -> dict:
    return {
        "summary": {
            "process": {
                "dashboard_layers": {
                    "layer_1_alarm": {
                        "issue_type_display_zh": "正常",
                        "issue_type_state": "Info",
                        "ooc_rate": 0.01,
                        "ooc_rate_state": "Info",
                        "ooc_count": 0,
                        "max_drift_ratio": 0.2,
                        "max_drift_ratio_state": "Info",
                        "anomaly_cluster_count": 0,
                        "anomaly_cluster_state": "Info",
                    },
                    "layer_2_kpi": {
                        "yield_pct": 98.5,
                        "dpmo": 120.0,
                        "sigma_level": 4.2,
                    },
                    "layer_3_info": {"sample_size": 120, "range": 15.0},
                    "layer_4_defect_structure": {
                        "defect_pattern_zh": "隨機分布",
                        "cluster_ratio": 0.01,
                        "cluster_state": "Info",
                        "top_oos_refdes": [],
                    },
                    "layer_5_spec_analysis": {
                        "cpk": 1.4,
                        "cp": 1.5,
                        "usl": 110.0,
                        "lsl": 90.0,
                        "target": 100.0,
                        "oos_rate": 0.0,
                        "mean_shift_pct": 2.0,
                        "spec_tightness_level": "OK",
                    },
                    "layer_6_product_context": {
                        "product_name": "Demo",
                        "supplier_work_order_no": "SUP-WO-1",
                        "outsource_work_order_no": "OUT-WO-1",
                        "work_order_no": "OUT-WO-1",
                        "batch_no": "OUT-WO-1",
                        "batch_qty": "120",
                        "stencil_type": "—",
                        "stencil_thickness": "—",
                    },
                    "layer_7_engineering_info": {
                        "mean": 99.0,
                        "std": 2.5,
                    },
                    "layer_8_diagnosis": {
                        "priority": "low",
                        "issue_type_display_zh": "正常",
                        "root_cause_zh": "製程符合穩定預期。",
                        "recommended_action_zh": "維持現有監控。",
                    },
                }
            }
        }
    }


def _diagnostic_matrix_payload() -> dict:
    payload = _payload(
        ["Volume", "Area", "Height"],
        cpk=0.82,
        cp=1.8,
        ooc=3,
        normal=False,
        drift=True,
        corr=0.85,
        cluster_ratio=0.071,
        pass_rates=[90.0, 100.0, 100.0],
    )
    payload["diagnostic_evidence_matrix"] = build_diagnostic_evidence_matrix(payload)
    return payload


def _table_for_tab(page: DiagnosticPage, qapp: QApplication, title: str) -> QTableWidget:
    tab_index = next(
        idx
        for idx in range(page._matrix_tabs.count())
        if page._matrix_tabs.tabText(idx) == title
    )
    page._matrix_tabs.setCurrentIndex(tab_index)
    qapp.processEvents()
    tables = page._matrix_tabs.widget(tab_index).findChildren(QTableWidget)
    assert tables
    return tables[0]


def _tab_blank_height(page: DiagnosticPage, qapp: QApplication, title: str) -> int:
    tab_index = next(
        idx
        for idx in range(page._matrix_tabs.count())
        if page._matrix_tabs.tabText(idx) == title
    )
    page._matrix_tabs.setCurrentIndex(tab_index)
    qapp.processEvents()
    tab = page._matrix_tabs.widget(tab_index)
    children = [child for child in tab.children() if hasattr(child, "geometry")]
    bottom = max((child.geometry().y() + child.geometry().height()) for child in children)
    return max(0, tab.height() - bottom)


def _header_width_need(table: QTableWidget, col: int) -> int:
    header_item = table.horizontalHeaderItem(col)
    assert header_item is not None
    return table.horizontalHeader().fontMetrics().horizontalAdvance(header_item.text()) + 24


def _label_width_need(label: QLabel) -> int:
    return label.fontMetrics().horizontalAdvance(label.text()) + 28


def _table_viewport_blank(table: QTableWidget) -> int:
    row_height = sum(table.rowHeight(row) for row in range(table.rowCount()))
    return max(0, table.viewport().height() - row_height)


def _total_column_width(table: QTableWidget) -> int:
    return sum(table.columnWidth(col) for col in range(table.columnCount()))


def _last_column_right_edge(table: QTableWidget) -> int:
    last_col = table.columnCount() - 1
    return table.columnViewportPosition(last_col) + table.columnWidth(last_col)


def test_diagnostic_page_update_table_sets_status(qapp) -> None:
    page = DiagnosticPage()
    page.update_table(_minimal_dashboard_payload())
    assert "分析完成" in page._status_lbl.text()


def test_diagnostic_page_uses_report_layout_and_source_labels(qapp) -> None:
    page = DiagnosticPage()
    page.update_table(_minimal_dashboard_payload())
    qapp.processEvents()

    assert page._title_lbl.text() == "製程統計分析"
    report_panels = [
        frame for frame in page.findChildren(QFrame)
        if frame.objectName() == "processStatReport"
    ]
    assert len(report_panels) == 1
    assert not [
        frame for frame in page.findChildren(QFrame)
        if frame.objectName() in {"processDashCard", "processAlarmCard"}
    ]

    section_labels = [
        label.text()
        for label in page.findChildren(QLabel)
        if label.property("class") == "processReportSectionLabel"
    ]
    assert section_labels == [
        "狀態 → 製程狀態摘要",
        "規格/能力 → 製程能力統計",
        "穩定性/資料範圍 → 量測與缺陷透視",
        "診斷與對策 → 工程結論",
        "背景 → 工單與鋼網資訊",
    ]
    assert page._fields["alarm"]["oos_rate"].property("sourceLayer") == "layer_5_spec_analysis"
    assert page._fields["alarm"]["oos_rate"].property("valueState") == "good"
    assert page._fields["kpi"]["yield"].property("valueState") == "warning"
    assert page._fields["kpi"]["cpk"].property("valueState") == "warning"
    assert (
        FONT_SIZE_PROCESS_DASH_KPI
        == FONT_SIZE_PROCESS_DASH_KPI_MEDIUM
        == FONT_SIZE_PROCESS_DASH_STAT
        == FONT_SIZE_DASH_LABEL
    )
    assert page._fields["kpi"]["cpk"].property("class") == "processDashStatSmall"
    page.close()


def test_copy_full_summary_includes_dashboard_lines(qapp) -> None:
    page = DiagnosticPage()
    page.update_table(_minimal_dashboard_payload())
    page._copy_full_summary()
    text = QApplication.clipboard().text()
    assert "SMT SPI 製程統計分析報告" in text
    assert "Cpk" in text or "cpk" in text.lower()
    assert "產品：Demo" in text
    assert "供應商製令工單：SUP-WO-1" in text
    assert "醫電製令工單：OUT-WO-1" in text
    assert "批量：120" in text


def test_diagnostic_matrix_tabs_render_with_readable_column_widths(qapp: QApplication) -> None:
    page = DiagnosticPage()
    page.resize(1980, 1180)
    page.show()
    page.update_table(_diagnostic_matrix_payload())
    qapp.processEvents()

    assert [page._matrix_tabs.tabText(idx) for idx in range(page._matrix_tabs.count())] == [
        "總覽",
        "組合矩陣",
        "證據矩陣",
        "關聯判讀",
        "圖表連動",
        "對策建議",
        "資料背景",
    ]

    combo = _table_for_tab(page, qapp, "組合矩陣")
    assert combo.columnWidth(2) >= max(
        DIAGNOSTIC_MATRIX_FAMILY_COL_WIDTH,
        _header_width_need(combo, 2),
    )
    assert combo.columnWidth(3) >= max(
        DIAGNOSTIC_MATRIX_STATUS_COL_WIDTH,
        _header_width_need(combo, 3),
    )
    assert combo.columnWidth(5) >= _header_width_need(combo, 5)
    assert combo.columnWidth(5) >= DIAGNOSTIC_MATRIX_VERDICT_COL_WIDTH

    evidence = _table_for_tab(page, qapp, "證據矩陣")
    assert evidence.columnWidth(0) >= DIAGNOSTIC_MATRIX_FAMILY_COL_WIDTH
    for col in range(1, evidence.columnCount()):
        assert evidence.columnWidth(col) >= max(
            DIAGNOSTIC_MATRIX_EVIDENCE_DIM_COL_WIDTH,
            _header_width_need(evidence, col),
        )

    linkage = _table_for_tab(page, qapp, "圖表連動")
    assert [
        linkage.horizontalHeaderItem(col).text()
        for col in range(linkage.columnCount())
    ] == ["建議圖表", "判讀結果", "由哪個證據觸發", "要確認/排除", "看完後下一步"]
    assert linkage.rowCount() > 0
    trigger_texts = [
        linkage.item(row, 2).text()
        for row in range(linkage.rowCount())
        if linkage.item(row, 2) is not None
    ]
    purpose_texts = [
        linkage.item(row, 3).text()
        for row in range(linkage.rowCount())
        if linkage.item(row, 3) is not None
    ]
    assert any(text and text != "—" for text in trigger_texts)
    assert any("確認" in text or "排除" in text for text in purpose_texts)
    assert linkage.horizontalHeader().sectionResizeMode(4) == QHeaderView.ResizeMode.Stretch
    assert linkage.columnWidth(4) >= _header_width_need(linkage, 4)

    data_context = _table_for_tab(page, qapp, "資料背景")
    assert data_context.columnWidth(1) >= max(
        DIAGNOSTIC_MATRIX_GAP_COUNT_COL_WIDTH,
        _header_width_need(data_context, 1),
    )
    page.close()


def test_evidence_matrix_rightmost_column_visible_in_standard_width(
    qapp: QApplication,
) -> None:
    page = DiagnosticPage()
    page.resize(1024, 900)
    page.show()
    page.update_table(_diagnostic_matrix_payload())
    qapp.processEvents()

    evidence = _table_for_tab(page, qapp, "證據矩陣")
    assert evidence.horizontalHeaderItem(evidence.columnCount() - 1).text() == "資料信心"
    assert _last_column_right_edge(evidence) <= evidence.viewport().width() + 1
    assert evidence.horizontalScrollBar().maximum() == 0
    page.close()


def test_evidence_matrix_uses_table_scrollbar_when_narrow(
    qapp: QApplication,
) -> None:
    page = DiagnosticPage()
    page.resize(760, 820)
    page.show()
    page.update_table(_diagnostic_matrix_payload())
    qapp.processEvents()

    evidence = _table_for_tab(page, qapp, "證據矩陣")
    assert evidence.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded
    assert _total_column_width(evidence) > evidence.viewport().width()
    assert evidence.horizontalScrollBar().maximum() > 0
    page.close()


def test_diagnostic_matrix_formats_metrics_and_subdues_low_value_states(
    qapp: QApplication,
) -> None:
    page = DiagnosticPage()
    page.resize(1980, 1180)
    page.show()
    page.update_table(_diagnostic_matrix_payload())
    qapp.processEvents()

    combo = _table_for_tab(page, qapp, "組合矩陣")
    metric_texts = [
        combo.item(row, 6).text()
        for row in range(combo.rowCount())
        if combo.item(row, 6) is not None
    ]
    assert "OOC 3/20 (15.0%)" in metric_texts
    assert "Cpk 0.82 / Cp 1.80" in metric_texts

    analyzed_badges = [
        combo.cellWidget(row, 3)
        for row in range(combo.rowCount())
        if combo.cellWidget(row, 3) is not None
        and combo.cellWidget(row, 3).property("state") == "analyzed"
    ]
    assert analyzed_badges
    assert all(badge.property("tone") == "subtle" for badge in analyzed_badges)

    evidence = _table_for_tab(page, qapp, "證據矩陣")
    no_data_badges = [
        evidence.cellWidget(row, col)
        for row in range(evidence.rowCount())
        for col in range(1, evidence.columnCount())
        if evidence.cellWidget(row, col) is not None
        and evidence.cellWidget(row, col).property("state") == "no-data"
    ]
    assert no_data_badges
    assert all(badge.text() == "—" for badge in no_data_badges)
    page.close()


def test_diagnostic_matrix_tables_use_content_height_and_internal_scroll(
    qapp: QApplication,
) -> None:
    page = DiagnosticPage()
    page.resize(1024, 900)
    page.show()
    page.update_table(_diagnostic_matrix_payload())
    qapp.processEvents()

    combo = _table_for_tab(page, qapp, "組合矩陣")
    assert combo.rowCount() > DIAGNOSTIC_MATRIX_MAX_VISIBLE_ROWS
    assert combo.verticalScrollBar().maximum() > 0
    assert combo.height() < TABLE_ROW_MIN_HEIGHT * (DIAGNOSTIC_MATRIX_MAX_VISIBLE_ROWS + 8)

    data_context = _table_for_tab(page, qapp, "資料背景")
    assert data_context.rowCount() <= 3
    assert _table_viewport_blank(data_context) < TABLE_ROW_MIN_HEIGHT * 2
    assert _tab_blank_height(page, qapp, "圖表連動") < TABLE_ROW_MIN_HEIGHT * 3
    page.close()


def test_actions_tab_uses_aligned_numbered_rows(qapp: QApplication) -> None:
    page = DiagnosticPage()
    page.resize(1024, 900)
    page.show()
    page.update_table(_diagnostic_matrix_payload())
    qapp.processEvents()

    tab_index = next(
        idx
        for idx in range(page._matrix_tabs.count())
        if page._matrix_tabs.tabText(idx) == "對策建議"
    )
    page._matrix_tabs.setCurrentIndex(tab_index)
    qapp.processEvents()
    tab = page._matrix_tabs.widget(tab_index)
    bullet_lists = [
        frame
        for frame in tab.findChildren(QFrame)
        if frame.objectName() == "diagnosticBulletList"
    ]
    assert len(bullet_lists) >= 3
    index_labels = [
        label
        for label in tab.findChildren(QLabel)
        if label.property("class") == "diagnosticBulletIndex"
    ]
    text_labels = [
        label
        for label in tab.findChildren(QLabel)
        if label.property("class") == "diagnosticBulletText"
    ]
    assert index_labels
    assert text_labels
    assert all(label.text().endswith(".") for label in index_labels)
    assert all(not label.text().startswith("1. ") for label in text_labels)
    assert all(label.wordWrap() for label in text_labels)
    page.close()


def test_diagnostic_page_uses_plain_language_for_refute_states(
    qapp: QApplication,
) -> None:
    page = DiagnosticPage()
    page.resize(1980, 1180)
    page.show()
    payload = _payload(["Volume"], cpk=1.6, cp=1.8)
    payload["diagnostic_evidence_matrix"] = build_diagnostic_evidence_matrix(payload)
    page.update_table(payload)
    qapp.processEvents()

    combo = _table_for_tab(page, qapp, "組合矩陣")
    badge_texts = [
        combo.cellWidget(row, 5).text()
        for row in range(combo.rowCount())
        if combo.cellWidget(row, 5) is not None
    ]
    joined = "\n".join(badge_texts)
    assert "不支持此假設" in joined
    assert "反證" not in joined

    refute_badges = [
        combo.cellWidget(row, 5)
        for row in range(combo.rowCount())
        if combo.cellWidget(row, 5) is not None
        and combo.cellWidget(row, 5).property("state") == "refute"
    ]
    assert refute_badges
    assert all(combo.columnWidth(5) >= _label_width_need(badge) for badge in refute_badges)

    evidence = _table_for_tab(page, qapp, "證據矩陣")
    compact_refute_badges = [
        evidence.cellWidget(row, col)
        for row in range(evidence.rowCount())
        for col in range(1, evidence.columnCount())
        if evidence.cellWidget(row, col) is not None
        and evidence.cellWidget(row, col).property("state") == "refute"
    ]
    assert compact_refute_badges
    assert all(badge.text().startswith("不支持 ") for badge in compact_refute_badges)
    assert all("不支持此假設" in badge.toolTip() for badge in compact_refute_badges)
    page.close()
