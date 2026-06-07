"""Process statistics report page (DiagnosticPage).
Merges dashboard layer metrics and diagnostic advice into a report-style output.
Follows specs for layers, tokens, and UI state semantics.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt, Signal
from app.ui.pages.diagnostic_matrix_page import DiagnosticMatrixPage

from app.ui.theme.tokens import (
    PAGE_CONTENT_MARGIN,
    SPACING_4,
    SPACING_8,
    SPACING_12,
    PAGE_HEADER_BOTTOM_SPACING,
)
from app.ui.widgets.page_templates import create_status_lamp
from app.analytics.dashboard_layers_display import (
    cpk_judgment_zh,
    cpk_state_ui,
    dpmo_state_ui,
    drift_insight_message,
    fmt_dashboard_value,
    get_tone_and_status,
    ooc_state_ui,
    oos_state_ui,
    outlier_observation_message,
    priority_state_ui,
    process_stat_report_plain_lines,
    top_refdes_line,
    value_state_from_layer_state,
    yield_state_ui,
)
from app.analytics.diagnostic_interpretation_registry import (
    build_diagnostic_interpretation_sections,
)
from app.ui.dialogs.interpretation_dialog import InterpretationDialog
from app.ui.widgets.process_dashboard_cards import (
    add_report_metric,
    add_report_section,
    apply_value_state,
    build_process_report_panel,
    feature_label_zh,
    set_alarm_tone,
    set_value_text,
)
from app.services.diagnostic_excel_exporter import export_diagnostic_summary_xlsx


class DiagnosticPage(QWidget):
    """
    Unified process statistics report page.

    Layout Hierarchy:
    1. Header: Page Title + Global Status + Actions
    2. Body (Scrollable):
       a. Process statistics report panel
    """

    navigate_to_chart = Signal(str, list)

    def __init__(self, parent=None, *, show_matrix_tabs: bool = True) -> None:
        super().__init__(parent)
        self._last_payload: dict[str, Any] = {}
        self._interpretation_dialog = InterpretationDialog(self)
        
        self._matrix_page = DiagnosticMatrixPage(self)
        self._matrix_tabs = self._matrix_page._matrix_tabs
        self._matrix_page.navigate_to_chart.connect(self.navigate_to_chart.emit)
        
        # Internal registry for widget updates (structured by section key)
        self._fields: dict[str, dict[str, QLabel]] = {
            "alarm": {}, "kpi": {}, "spec": {}, "eng": {}, 
            "data": {}, "diag": {}, "defect": {}, "prod": {}
        }

        # Main Layout
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 1. Header Toolbar
        self._header = QFrame()
        self._header.setProperty("class", "headerToolbar")
        self._header.setProperty("headerRole", "utilityHeader")
        self._header.setProperty("headerDensity", "compact")
        header_lay = QHBoxLayout(self._header)
        header_lay.setContentsMargins(PAGE_CONTENT_MARGIN, SPACING_4, PAGE_CONTENT_MARGIN, SPACING_4)
        header_lay.setSpacing(SPACING_8)
        
        self._title_lbl = QLabel("製程統計分析")
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

        self._interpret_btn = QPushButton("解讀")
        self._interpret_btn.setProperty("class", "secondary")
        self._interpret_btn.setToolTip("開啟 layer_1~layer_7 指標解讀（用途/判讀/門檻/建議）")
        self._interpret_btn.clicked.connect(self._open_diagnostic_interpretation)
        header_lay.addWidget(self._interpret_btn)
        
        self._copy_all_btn = QPushButton("匯出 Excel")
        self._copy_all_btn.setProperty("class", "secondary")
        self._copy_all_btn.clicked.connect(self._export_excel_report)
        header_lay.addWidget(self._copy_all_btn)
        
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

        self._init_dashboard_sections()
        
        if show_matrix_tabs:
            self._body_lay.addWidget(self._matrix_tabs)
        self._body_lay.addStretch(1)

    def _init_dashboard_sections(self):
        """Construct a report-style process statistics page."""
        report, grid = build_process_report_panel("製程統計分析報告輸出")
        self._alarm_card = report
        self._diag_box = report

        row = 0
        add_report_section(grid, row, "狀態 → 製程狀態摘要")
        row += 1
        d = self._fields["alarm"]
        d["status_zh"] = add_report_metric(grid, row, 0, "分析結論", "layer_1_alarm", tier="medium")
        d["issue_type"] = add_report_metric(
            grid,
            row,
            1,
            "問題類別",
            "layer_1_alarm + layer_8_diagnosis",
            tier="medium",
        )
        d["ooc_rate"] = add_report_metric(grid, row, 2, "OOC 比率", "layer_1_alarm", tier="medium")
        d["oos_rate"] = add_report_metric(
            grid,
            row,
            3,
            "OOS 比率 (規格)",
            "layer_5_spec_analysis",
            tier="medium",
        )
        d["oos_rate"].setToolTip("主特徵量測值超出規格上下限之比例（依規格比較計算）")
        row += 1
        d["shift"] = add_report_metric(
            grid,
            row,
            0,
            "均值偏移 (%)",
            "layer_5_spec_analysis + layer_1_alarm",
        )
        d["cluster"] = add_report_metric(grid, row, 1, "群集等級", "layer_1_alarm")
        d["driver"] = add_report_metric(grid, row, 2, "驅動特徵", "layer_3_info", colspan=2)

        row += 1
        add_report_section(grid, row, "規格/能力 → 製程能力統計")
        row += 1
        k = self._fields["kpi"]
        s = self._fields["spec"]
        e = self._fields["eng"]
        k["cpk"] = add_report_metric(grid, row, 0, "Cpk (主特徵)", "layer_5_spec_analysis", tier="medium")
        s["cp"] = add_report_metric(grid, row, 1, "Cp", "layer_5_spec_analysis", tier="medium")
        e["judgment"] = add_report_metric(
            grid,
            row,
            2,
            "製程能力判讀",
            "layer_5_spec_analysis",
            colspan=2,
        )
        row += 1
        s["usl"] = add_report_metric(grid, row, 0, "USL", "layer_5_spec_analysis")
        s["lsl"] = add_report_metric(grid, row, 1, "LSL", "layer_5_spec_analysis")
        s["tgt"] = add_report_metric(grid, row, 2, "目標", "layer_5_spec_analysis")
        s["mean"] = add_report_metric(grid, row, 3, "均值", "layer_7_engineering_info")
        row += 1
        s["std"] = add_report_metric(grid, row, 0, "標準差", "layer_7_engineering_info")
        s["tightness"] = add_report_metric(
            grid,
            row,
            1,
            "規格緊度",
            "layer_5_spec_analysis",
            colspan=3,
        )

        row += 1
        add_report_section(grid, row, "穩定性/資料範圍 → 量測與缺陷透視")
        row += 1
        k["yield"] = add_report_metric(grid, row, 0, "良率 (Yield)", "layer_2_kpi", tier="medium")
        k["yield"].setToolTip("所有規格特徵均在公差內的列數比例（綜合良率；依規格比較）")
        k["dpmo"] = add_report_metric(grid, row, 1, "DPMO", "layer_2_kpi", tier="medium")
        k["dpmo"].setToolTip("每百萬機會之缺陷數（基於特徵×量測點之總機會數，含所有特徵違規事件）")
        k["sigma"] = add_report_metric(grid, row, 2, "Sigma 水準", "layer_2_kpi")
        e["sample"] = add_report_metric(grid, row, 3, "樣本數", "layer_3_info")
        row += 1
        e["range"] = add_report_metric(grid, row, 0, "全距", "layer_3_info")
        f = self._fields["defect"]
        f["pattern"] = add_report_metric(grid, row, 1, "異常空間型態", "layer_4_defect_structure")
        f["cluster"] = add_report_metric(grid, row, 2, "群聚係數", "layer_4_defect_structure")
        f["drift_insight"] = add_report_metric(grid, row, 3, "趨勢偏離發現", "layer_1_alarm")
        row += 1
        f["top_ref"] = add_report_metric(
            grid,
            row,
            0,
            "Top 5 異常位號",
            "layer_4_defect_structure",
            colspan=2,
        )
        f["outlier"] = add_report_metric(
            grid,
            row,
            2,
            "量測數值離群觀察",
            "layer_1_alarm + layer_3_info",
            colspan=2,
        )

        row += 1
        add_report_section(grid, row, "診斷與對策 → 工程結論")
        row += 1
        di = self._fields["diag"]
        di["priority"] = add_report_metric(grid, row, 0, "優先級", "layer_8_diagnosis", tier="medium")
        di["type"] = add_report_metric(grid, row, 1, "問題型態", "layer_8_diagnosis", colspan=3)
        row += 1
        di["cause"] = add_report_metric(grid, row, 0, "可能根因分析", "layer_8_diagnosis", colspan=4)
        row += 1
        di["action"] = add_report_metric(grid, row, 0, "建議工程對策", "layer_8_diagnosis", colspan=4)

        row += 1
        add_report_section(grid, row, "背景 → 工單與鋼網資訊")
        row += 1
        p = self._fields["prod"]
        p["name"] = add_report_metric(grid, row, 0, "產品", "layer_6_product_context")
        p["supplier_wo"] = add_report_metric(grid, row, 1, "供應商製令工單", "layer_6_product_context")
        p["outsource_wo"] = add_report_metric(grid, row, 2, "醫電製令工單", "layer_6_product_context")
        p["batch_qty"] = add_report_metric(grid, row, 3, "批量", "layer_6_product_context")
        row += 1
        p["stencil"] = add_report_metric(grid, row, 0, "鋼網 ID", "layer_6_product_context", colspan=2)
        p["thick"] = add_report_metric(grid, row, 2, "厚度", "layer_6_product_context", colspan=2)

        self._body_lay.addWidget(report)

    def update_table(self, payload: dict[str, Any]) -> None:
        """Populate the process statistics dashboard from the analysis payload."""
        self._last_payload = payload or {}
        summary = self._last_payload.get("summary", {})
        process = summary.get("process", {})
        layers = process.get("dashboard_layers", {})
        
        if not layers:
            self._lamp.setProperty("state", "idle")
            self._status_lbl.setText("尚待分析數據...")
            return

        # 1. Extract layer data
        l1 = layers.get("layer_1_alarm", {})
        l2 = layers.get("layer_2_kpi", {})
        l3 = layers.get("layer_3_info", {})
        l4 = layers.get("layer_4_defect_structure", {})
        l5 = layers.get("layer_5_spec_analysis", {})
        l6 = layers.get("layer_6_product_context", {})
        l7 = layers.get("layer_7_engineering_info", {})
        l8 = layers.get("layer_8_diagnosis", {})

        # 2. Update Global Status
        tone, status_zh = get_tone_and_status(l1)
        set_alarm_tone(self._alarm_card, tone)
        self._lamp.setProperty("state", "success" if tone == "normal" else tone)
        self._lamp.style().unpolish(self._lamp)
        self._lamp.style().polish(self._lamp)
        self._status_lbl.setText("分析完成")
        
        # 3. Fill Alarm
        a = self._fields["alarm"]
        set_value_text(a["issue_type"], str(l8.get("issue_type_display_zh") or l1.get("issue_type_display_zh") or "—"))
        apply_value_state(a["issue_type"], str(l1.get("issue_type_state") or "Info"))
        set_value_text(a["ooc_rate"], fmt_dashboard_value(l1.get("ooc_rate"), "pct"))
        apply_value_state(a["ooc_rate"], ooc_state_ui(l1.get("ooc_rate"), l1.get("ooc_rate_state")))
        set_value_text(a["oos_rate"], fmt_dashboard_value(l5.get("oos_rate"), "pct"))
        apply_value_state(a["oos_rate"], oos_state_ui(l5.get("oos_rate")))
        set_value_text(a["shift"], fmt_dashboard_value(l5.get("mean_shift_pct"), "num"))
        apply_value_state(
            a["shift"],
            value_state_from_layer_state(l1.get("max_drift_ratio_state")),
        )
        set_value_text(a["status_zh"], status_zh)
        if tone == "normal":
            _status_state = "Normal"
        elif tone == "critical":
            _status_state = "Alarm"
        else:
            _status_state = "Warning"
        apply_value_state(a["status_zh"], _status_state)
        set_value_text(a["cluster"], str(l1.get("anomaly_cluster_count") or "—"))
        apply_value_state(a["cluster"], str(l1.get("anomaly_cluster_state") or "Info"))
        set_value_text(a["driver"], feature_label_zh(l3.get("driver_feature")))
        apply_value_state(a["driver"], "Info")

        # 4. Fill KPI (Prioritize Primary Cpk over Avg for transparency)
        k = self._fields["kpi"]
        cpk_v = l5.get("cpk") # Primary feature Cpk
        set_value_text(k["cpk"], fmt_dashboard_value(cpk_v))
        apply_value_state(k["cpk"], cpk_state_ui(cpk_v))
        set_value_text(k["yield"], fmt_dashboard_value(l2.get("yield_pct"), "yield_pct"))
        apply_value_state(k["yield"], yield_state_ui(l2.get("yield_pct")))
        set_value_text(k["dpmo"], fmt_dashboard_value(l2.get("dpmo"), "num"))
        apply_value_state(k["dpmo"], dpmo_state_ui(l2.get("dpmo")))
        set_value_text(k["sigma"], fmt_dashboard_value(l2.get("sigma_level"), "num"))
        apply_value_state(k["sigma"], "neutral")

        # 5. Fill Spec & Detail
        s = self._fields["spec"]
        set_value_text(s["usl"], fmt_dashboard_value(l5.get("usl")))
        set_value_text(s["lsl"], fmt_dashboard_value(l5.get("lsl")))
        set_value_text(s["tgt"], fmt_dashboard_value(l5.get("target")))
        set_value_text(s["mean"], fmt_dashboard_value(l7.get("mean")))
        set_value_text(s["std"], fmt_dashboard_value(l7.get("std")))
        set_value_text(s["cp"], fmt_dashboard_value(l5.get("cp")))
        apply_value_state(s["cp"], cpk_state_ui(l5.get("cp")))
        _TIGHTNESS_ZH = {
            "high_capability": "高能力（≥1.67）",
            "typical": "一般（1.33–1.67）",
            "improvement_needed": "需改善（<1.33）",
        }
        _raw_tightness = l5.get("spec_tightness_level")
        set_value_text(s["tightness"], _TIGHTNESS_ZH.get(_raw_tightness, "—") if _raw_tightness else "—")
        apply_value_state(s["tightness"], "Info")

        e = self._fields["eng"]
        set_value_text(e["sample"], str(l3.get("sample_size") or "—"))
        set_value_text(e["range"], fmt_dashboard_value(l3.get("range")))
        set_value_text(e["judgment"], cpk_judgment_zh(cpk_v))
        apply_value_state(e["judgment"], cpk_state_ui(cpk_v))

        # 6. Fill Diagnosis (Primary Action Center)
        diag = self._fields["diag"]
        prio = str(l8.get("priority") or "low").lower()
        if prio == "high":
            _prio_label, _prio_alarm, _prio_state = "高 (High)", "Alarm", "bad"
        elif prio == "medium":
            _prio_label, _prio_alarm, _prio_state = "中 (Mid)", "Warning", "warning"
        else:
            _prio_label, _prio_alarm, _prio_state = "低 (Low)", "Normal", "neutral"
        set_value_text(diag["priority"], _prio_label)
        apply_value_state(diag["priority"], _prio_alarm)
        set_value_text(diag["type"], str(l8.get("issue_type_display_zh") or "—"))
        apply_value_state(diag["type"], priority_state_ui(l8.get("priority")))
        set_value_text(diag["cause"], str(l8.get("root_cause_zh") or "製程符合穩定預期。"))
        set_value_text(diag["action"], str(l8.get("recommended_action_zh") or "維持現有監控。"))
        apply_value_state(diag["cause"], _prio_state)
        apply_value_state(diag["action"], _prio_state)

        # 7. Defect & Context
        f = self._fields["defect"]
        set_value_text(f["pattern"], str(l4.get("defect_pattern_zh") or "隨機分布"))
        apply_value_state(f["pattern"], "Info")
        set_value_text(f["cluster"], fmt_dashboard_value(l4.get("cluster_ratio"), "pct"))
        apply_value_state(f["cluster"], str(l4.get("cluster_state") or "Info"))
        
        drift_v = l1.get("max_drift_ratio")
        drift_msg = drift_insight_message(drift_v)
        set_value_text(f["drift_insight"], drift_msg)
        apply_value_state(f["drift_insight"], "Alarm" if (drift_v or 0) >= 1.0 else "Info")

        set_value_text(f["top_ref"], top_refdes_line(l4.get("top_oos_refdes")))

        ooc_c = l1.get("ooc_count") or 0
        set_value_text(
            f["outlier"],
            outlier_observation_message(ooc_c, l3.get("range"), l5.get("spec_range")),
        )

        p = self._fields["prod"]
        set_value_text(p["name"], str(l6.get("product_name") or "—"))
        set_value_text(
            p["supplier_wo"],
            str(l6.get("supplier_work_order_no") or "—"),
        )
        set_value_text(
            p["outsource_wo"],
            str(l6.get("outsource_work_order_no") or l6.get("work_order_no") or "—"),
        )
        set_value_text(p["batch_qty"], str(l6.get("batch_qty") or "—"))
        set_value_text(p["stencil"], str(l6.get("stencil_type") or "—"))
        set_value_text(p["thick"], str(l6.get("stencil_thickness") or "—"))
        
        # 8. Update Footer
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._updated_lbl.setText(f"最後更新: {now}")
        self._matrix_page.update_hints(payload)

    def _copy_full_summary(self):
        """Build text summary including all critical dashboard facts."""
        summary = self._last_payload.get("summary", {})
        layers = summary.get("process", {}).get("dashboard_layers", {})
        parts = [f"【SMT SPI 製程統計分析報告 - {datetime.now().strftime('%Y-%m-%d')}】"]
        parts.extend(process_stat_report_plain_lines(layers if isinstance(layers, dict) else {}))
        QApplication.clipboard().setText("\n".join(parts))

    def _open_diagnostic_interpretation(self) -> None:
        """Open layer-by-layer interpretation dialog for the diagnostic dashboard."""
        layers = (
            (self._last_payload or {})
            .get("summary", {})
            .get("process", {})
            .get("dashboard_layers", {})
        )
        sections = build_diagnostic_interpretation_sections(layers if isinstance(layers, dict) else {})

        context_lines = [
            "互動模式：預設隱藏說明，按鈕開啟完整解讀視窗。",
        ]
        if not isinstance(layers, dict) or not layers:
            context_lines.append("目前狀態：NoData（尚未完成分析，僅顯示判讀框架）。")
        else:
            issue_type = str((layers.get("layer_1_alarm") or {}).get("issue_type_display_zh") or "—")
            context_lines.append(f"目前問題類別：{issue_type}")

        self._interpretation_dialog.open_for_diagnostic(
            sections=sections,
            context_lines=context_lines,
        )

    def _export_excel_report(self) -> None:
        """Export dashboard summary as a styled xlsx report."""
        summary = self._last_payload.get("summary", {})
        layers = summary.get("process", {}).get("dashboard_layers", {})
        if not layers:
            QMessageBox.information(self, "無可匯出資料", "目前尚未有分析結果，請先完成分析。")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "匯出 Excel 報告",
            "SMT_SPI_製程統計分析報告.xlsx",
            "Excel 檔案 (*.xlsx)",
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path = f"{path}.xlsx"

        try:
            export_diagnostic_summary_xlsx(self._last_payload, path)
        except (OSError, ValueError) as exc:  # pragma: no cover - UI fallback path
            QMessageBox.critical(self, "匯出失敗", f"無法匯出 Excel 報告：{exc}")
            return

        QMessageBox.information(self, "匯出完成", f"已匯出 Excel 報告：\n{path}")

    # Compatibility shim for orchestrated analysis updates
    def update_hints(self, payload: dict[str, Any]) -> None:
        """Compatibility wrapper that forwards analysis payload to dashboard rendering."""
        self.update_table(payload)
