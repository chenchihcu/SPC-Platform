"""
Shared display helpers for `process.dashboard_layers` (Process Diagnosis Dashboard).

Used by DiagnosticPage and PPTX/HTML reports to avoid UI vs export drift.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, TypedDict

_MEASURE_ZH = {"Volume": "體積", "Area": "面積", "Height": "高度"}


class ProcessStatReportRow(TypedDict):
    key: str
    label: str
    value: str
    state: str
    source: str
    meaning: str


class ProcessStatReportSection(TypedDict):
    key: str
    title: str
    rows: List[ProcessStatReportRow]


def feature_label_zh(name: object) -> str:
    if name is None or name == "":
        return "—"
    s = str(name)
    return _MEASURE_ZH.get(s, s)


def fmt_dashboard_value(val: Any, kind: str = "num") -> str:
    if val is None or val == "":
        return "—"
    try:
        num = float(val)
    except (ValueError, TypeError):
        return str(val)

    if kind == "pct":
        return f"{num * 100:.2f}%"
    if kind == "yield_pct":
        return f"{num:.2f}%"
    return f"{num:.3f}"


def get_tone_and_status(layer1: Dict[str, Any]) -> Tuple[str, str]:
    states = [
        layer1.get("ooc_rate_state"),
        layer1.get("cpk_below_133_state"),
        layer1.get("max_drift_ratio_state"),
        layer1.get("anomaly_cluster_state"),
    ]
    if any(s == "Alarm" for s in states):
        return "critical", "製程狀態異常：嚴重"
    if any(s == "Warning" for s in states):
        return "warning", "製程狀態警報：警告"
    return "normal", "製程狀態穩定：正常"


def cpk_state_ui(cpk: Any) -> str:
    """State token for dashboard KPI coloring (matches DiagnosticPage)."""
    if cpk is None:
        return "Info"
    try:
        v = float(cpk)
    except (ValueError, TypeError):
        return "Info"
    if v >= 1.67:
        return "Normal"
    if v >= 1.33:
        return "Warning"
    return "Alarm"


def cpk_judgment_zh(cpk: Any) -> str:
    if cpk is None:
        return "—"
    try:
        v = float(cpk)
    except (ValueError, TypeError):
        return "—"
    if v >= 1.67:
        return "良好 (Cpk ≥ 1.67)"
    if v >= 1.33:
        return "監控 (1.33 ≤ Cpk < 1.67)"
    return "須處置 (Cpk < 1.33)"


def value_state_from_layer_state(state: Any) -> str:
    """Normalize layer state strings to UI/export severity tokens."""
    key = str(state or "").strip()
    if key in {"good", "warning", "bad", "neutral"}:
        return key
    mapping = {
        "Normal": "good",
        "Warning": "warning",
        "Alarm": "bad",
        "Info": "neutral",
    }
    return mapping.get(key, "neutral")


def value_state_label_zh(state: str) -> str:
    return {
        "good": "正常",
        "warning": "監控",
        "bad": "需處置",
        "neutral": "參考",
    }.get(state, "參考")


def ooc_state_ui(ooc_rate: Any, layer_state: Any = None) -> str:
    layer_token = value_state_from_layer_state(layer_state)
    if layer_token != "neutral":
        return layer_token
    try:
        ratio = float(ooc_rate)
    except (TypeError, ValueError):
        return "neutral"
    if ratio >= 0.10:
        return "bad"
    if ratio >= 0.03:
        return "warning"
    return "good"


def oos_state_ui(oos_rate: Any) -> str:
    """Spec violations are action-required when any OOS rate is present."""
    try:
        ratio = float(oos_rate)
    except (TypeError, ValueError):
        return "neutral"
    return "bad" if ratio > 0 else "good"


def yield_state_ui(yield_pct: Any) -> str:
    try:
        value = float(yield_pct)
    except (TypeError, ValueError):
        return "neutral"
    if 0.0 <= value <= 1.0:
        value *= 100.0
    if value >= 99.0:
        return "good"
    if value >= 95.0:
        return "warning"
    return "bad"


def dpmo_state_ui(dpmo: Any) -> str:
    try:
        value = float(dpmo)
    except (TypeError, ValueError):
        return "neutral"
    if value <= 100:
        return "good"
    if value <= 10000:
        return "warning"
    return "bad"


def priority_state_ui(priority: Any) -> str:
    prio = str(priority or "low").lower()
    if prio == "high":
        return "bad"
    if prio == "medium":
        return "warning"
    return "good"


def priority_display_zh(priority: Any) -> str:
    prio = str(priority or "low").lower()
    if prio == "high":
        return "高 (High)"
    if prio == "medium":
        return "中 (Mid)"
    return "低 (Low)"


def drift_insight_message(max_drift_ratio: Any) -> str:
    drift_v: Optional[float] = None
    if max_drift_ratio is not None:
        try:
            drift_v = float(max_drift_ratio)
        except (ValueError, TypeError):
            drift_v = None
    if drift_v is None:
        return "製程趨勢穩定"
    if drift_v >= 1.0:
        return "顯著均值漂移(>100%)"
    if drift_v >= 0.8:
        return "潛在持續偏移(>80%)"
    return "製程趨勢穩定"


def outlier_observation_message(
    ooc_count: Any,
    range_v: Any,
    spec_range: Any,
) -> str:
    try:
        ooc_c = int(ooc_count or 0)
    except (TypeError, ValueError):
        ooc_c = 0
    outlier_msg = "數值分佈集中" if ooc_c < 2 else f"存在 {ooc_c} 處離群點"
    try:
        rv = float(range_v) if range_v is not None else None
        sr = float(spec_range) if spec_range is not None else None
    except (TypeError, ValueError):
        rv, sr = None, None
    if rv is not None and sr is not None and sr > 0 and rv > sr * 0.8:
        outlier_msg += " / 高屏寬佔比"
    return outlier_msg


def top_refdes_line(top_refs: Any) -> str:
    if not isinstance(top_refs, list) or not top_refs:
        return "無"
    parts = []
    for r in top_refs[:5]:
        if not isinstance(r, dict):
            continue
        parts.append(f"{r.get('id')}({r.get('oos_count')})")
    return "、".join(parts) if parts else "無"


def extract_dashboard_layers(process: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(process, dict):
        return {}
    dl = process.get("dashboard_layers")
    return dl if isinstance(dl, dict) else {}


def _layer_dict(layers: Dict[str, Any], key: str) -> Dict[str, Any]:
    raw = layers.get(key)
    return raw if isinstance(raw, dict) else {}


def _report_row(
    key: str,
    label: str,
    value: str,
    state: str,
    source: str,
    meaning: str,
) -> ProcessStatReportRow:
    return {
        "key": key,
        "label": label,
        "value": value,
        "state": state,
        "source": source,
        "meaning": meaning,
    }


def _tightness_zh(value: Any) -> str:
    mapping = {
        "high_capability": "高能力 (>=1.67)",
        "typical": "一般 (1.33-1.67)",
        "improvement_needed": "需改善 (<1.33)",
        "OK": "OK",
    }
    return mapping.get(str(value), "—") if value not in (None, "") else "—"


def _status_state_from_tone(tone: str) -> str:
    if tone == "critical":
        return "bad"
    if tone == "warning":
        return "warning"
    return "good"


def build_process_stat_report_sections(
    layers: Dict[str, Any],
) -> List[ProcessStatReportSection]:
    """Shared report order for DiagnosticPage, Excel, and PPTX output."""
    l1 = _layer_dict(layers, "layer_1_alarm")
    l2 = _layer_dict(layers, "layer_2_kpi")
    l3 = _layer_dict(layers, "layer_3_info")
    l4 = _layer_dict(layers, "layer_4_defect_structure")
    l5 = _layer_dict(layers, "layer_5_spec_analysis")
    l6 = _layer_dict(layers, "layer_6_product_context")
    l7 = _layer_dict(layers, "layer_7_engineering_info")
    l8 = _layer_dict(layers, "layer_8_diagnosis")

    tone, status_zh = get_tone_and_status(l1)
    issue = str(l8.get("issue_type_display_zh") or l1.get("issue_type_display_zh") or "—")
    cpk_v = l5.get("cpk")
    ooc_state = ooc_state_ui(l1.get("ooc_rate"), l1.get("ooc_rate_state"))
    oos_state = oos_state_ui(l5.get("oos_rate"))
    drift_state = value_state_from_layer_state(l1.get("max_drift_ratio_state"))
    if drift_state == "neutral":
        try:
            drift_state = "bad" if float(l1.get("max_drift_ratio") or 0) >= 1.0 else "good"
        except (TypeError, ValueError):
            drift_state = "neutral"
    cluster_state = value_state_from_layer_state(
        l1.get("anomaly_cluster_state") or l4.get("cluster_state")
    )

    status_rows = [
        _report_row(
            "status_zh",
            "分析結論",
            status_zh,
            _status_state_from_tone(tone),
            "layer_1_alarm",
            "整合 OOC、Cpk、偏移與群聚狀態。",
        ),
        _report_row(
            "issue_type",
            "問題類別",
            issue,
            value_state_from_layer_state(l1.get("issue_type_state")),
            "layer_1_alarm + layer_8_diagnosis",
            "製程異常分類或正常類別。",
        ),
        _report_row(
            "ooc_rate",
            "OOC 比率",
            fmt_dashboard_value(l1.get("ooc_rate"), "pct"),
            ooc_state,
            "layer_1_alarm",
            "管制界限外比例。",
        ),
        _report_row(
            "oos_rate",
            "OOS 比率 (規格)",
            fmt_dashboard_value(l5.get("oos_rate"), "pct"),
            oos_state,
            "layer_5_spec_analysis",
            "超出 USL/LSL 規格比例。",
        ),
        _report_row(
            "shift",
            "均值偏移 (%)",
            fmt_dashboard_value(l5.get("mean_shift_pct"), "num"),
            drift_state,
            "layer_5_spec_analysis + layer_1_alarm",
            "均值相對目標或規格中心偏移。",
        ),
        _report_row(
            "cluster",
            "群集等級",
            str(l1.get("anomaly_cluster_count") if l1.get("anomaly_cluster_count") is not None else "—"),
            cluster_state,
            "layer_1_alarm",
            "空間/時間異常群聚數。",
        ),
        _report_row(
            "driver",
            "驅動特徵",
            feature_label_zh(l3.get("driver_feature")),
            "neutral",
            "layer_3_info",
            "主導此輪判讀的量測特徵。",
        ),
    ]

    capability_rows = [
        _report_row("cpk", "Cpk (主特徵)", fmt_dashboard_value(cpk_v), value_state_from_layer_state(cpk_state_ui(cpk_v)), "layer_5_spec_analysis", "製程中心化與規格能力。"),
        _report_row("cp", "Cp", fmt_dashboard_value(l5.get("cp")), value_state_from_layer_state(cpk_state_ui(l5.get("cp"))), "layer_5_spec_analysis", "製程分散相對規格寬度。"),
        _report_row("judgment", "製程能力判讀", cpk_judgment_zh(cpk_v), value_state_from_layer_state(cpk_state_ui(cpk_v)), "layer_5_spec_analysis", "能力門檻判讀。"),
        _report_row("usl", "USL", fmt_dashboard_value(l5.get("usl")), "neutral", "layer_5_spec_analysis", "規格上限。"),
        _report_row("lsl", "LSL", fmt_dashboard_value(l5.get("lsl")), "neutral", "layer_5_spec_analysis", "規格下限。"),
        _report_row("target", "目標", fmt_dashboard_value(l5.get("target")), "neutral", "layer_5_spec_analysis", "目標值或規格中心。"),
        _report_row("mean", "均值", fmt_dashboard_value(l7.get("mean")), "neutral", "layer_7_engineering_info", "量測平均值。"),
        _report_row("std", "標準差", fmt_dashboard_value(l7.get("std")), "neutral", "layer_7_engineering_info", "短期分散程度。"),
        _report_row("tightness", "規格緊度", _tightness_zh(l5.get("spec_tightness_level")), "neutral", "layer_5_spec_analysis", "規格相對製程能力的緊度摘要。"),
    ]

    top_refs = l4.get("top_oos_refdes")
    top_ref_state = "bad" if isinstance(top_refs, list) and len(top_refs) > 0 else "good"
    outlier_state = ooc_state if ooc_state in {"bad", "warning"} else "neutral"
    stability_rows = [
        _report_row("yield", "良率 (Yield)", fmt_dashboard_value(l2.get("yield_pct"), "yield_pct"), yield_state_ui(l2.get("yield_pct")), "layer_2_kpi", "所有規格特徵在公差內的列數比例。"),
        _report_row("dpmo", "DPMO", fmt_dashboard_value(l2.get("dpmo"), "num"), dpmo_state_ui(l2.get("dpmo")), "layer_2_kpi", "每百萬機會缺陷數。"),
        _report_row("sigma", "Sigma 水準", fmt_dashboard_value(l2.get("sigma_level"), "num"), "neutral", "layer_2_kpi", "缺陷率換算之 Sigma 表現。"),
        _report_row("sample", "樣本數", str(l3.get("sample_size") if l3.get("sample_size") is not None else "—"), "neutral", "layer_3_info", "本次分析量測筆數。"),
        _report_row("range", "全距", fmt_dashboard_value(l3.get("range")), "neutral", "layer_3_info", "最大值與最小值距離。"),
        _report_row("pattern", "異常空間型態", str(l4.get("defect_pattern_zh") or "隨機分布"), cluster_state, "layer_4_defect_structure", "缺陷分布型態。"),
        _report_row("cluster_ratio", "群聚係數", fmt_dashboard_value(l4.get("cluster_ratio"), "pct"), cluster_state, "layer_4_defect_structure", "異常點群聚比例。"),
        _report_row("drift_insight", "趨勢偏離發現", drift_insight_message(l1.get("max_drift_ratio")), drift_state, "layer_1_alarm", "CUSUM/趨勢偏移摘要。"),
        _report_row("top_ref", "Top 5 異常位號", top_refdes_line(top_refs), top_ref_state, "layer_4_defect_structure", "OOS 次數最高的 RefDes。"),
        _report_row("outlier", "量測數值離群觀察", outlier_observation_message(l1.get("ooc_count"), l3.get("range"), l5.get("spec_range")), outlier_state, "layer_1_alarm + layer_3_info", "離群點與高屏寬佔比觀察。"),
    ]

    diag_state = priority_state_ui(l8.get("priority"))
    diagnosis_rows = [
        _report_row("priority", "優先級", priority_display_zh(l8.get("priority")), diag_state, "layer_8_diagnosis", "工程處置優先度。"),
        _report_row("type", "問題型態", str(l8.get("issue_type_display_zh") or "—"), diag_state if diag_state != "good" else "neutral", "layer_8_diagnosis", "診斷層問題型態。"),
        _report_row("cause", "可能根因分析", str(l8.get("root_cause_zh") or "製程符合穩定預期。"), diag_state if diag_state != "good" else "neutral", "layer_8_diagnosis", "製程統計證據收斂出的可能根因。"),
        _report_row("action", "建議工程對策", str(l8.get("recommended_action_zh") or "維持現有監控。"), diag_state if diag_state != "good" else "neutral", "layer_8_diagnosis", "現場工程確認與改善方向。"),
    ]

    context_rows = [
        _report_row("product", "產品", str(l6.get("product_name") or "—"), "neutral", "layer_6_product_context", "產品或料號背景。"),
        _report_row("supplier_wo", "供應商製令工單", str(l6.get("supplier_work_order_no") or "—"), "neutral", "layer_6_product_context", "供應商工單。"),
        _report_row("outsource_wo", "醫電製令工單", str(l6.get("outsource_work_order_no") or l6.get("work_order_no") or "—"), "neutral", "layer_6_product_context", "內部/外包工單。"),
        _report_row("batch_qty", "批量", str(l6.get("batch_qty") or "—"), "neutral", "layer_6_product_context", "生產批量。"),
        _report_row("stencil", "鋼網 ID", str(l6.get("stencil_type") or "—"), "neutral", "layer_6_product_context", "鋼網型號或 ID。"),
        _report_row("thickness", "厚度", str(l6.get("stencil_thickness") or "—"), "neutral", "layer_6_product_context", "鋼網厚度。"),
    ]

    return [
        {"key": "status", "title": "狀態 → 製程狀態摘要", "rows": status_rows},
        {"key": "capability", "title": "規格/能力 → 製程能力統計", "rows": capability_rows},
        {"key": "stability", "title": "穩定性/資料範圍 → 量測與缺陷透視", "rows": stability_rows},
        {"key": "diagnosis", "title": "診斷與對策 → 工程結論", "rows": diagnosis_rows},
        {"key": "context", "title": "背景 → 工單與鋼網資訊", "rows": context_rows},
    ]


def process_stat_report_plain_lines(layers: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    for section in build_process_stat_report_sections(layers):
        lines.append(f"【{section['title']}】")
        lines.extend(
            f"{row['label']}：{row['value']}（{row['source']}）"
            for row in section["rows"]
        )
    return lines


def _report_section_lines(layers: Dict[str, Any], section_key: str) -> List[str]:
    for section in build_process_stat_report_sections(layers):
        if section["key"] == section_key:
            return [f"【製程統計分析｜{section['title']}】"] + [
                f"{row['label']}：{row['value']}" for row in section["rows"]
            ]
    return ["【製程統計分析】", "資料不足"]


def _selected_report_lines(
    layers: Dict[str, Any],
    section_key: str,
    row_keys: List[str],
    title: str,
) -> List[str]:
    for section in build_process_stat_report_sections(layers):
        if section["key"] != section_key:
            continue
        row_map = {row["key"]: row for row in section["rows"]}
        lines = [title]
        lines.extend(
            f"{row_map[key]['label']}：{row_map[key]['value']}"
            for key in row_keys
            if key in row_map
        )
        return lines
    return [title, "資料不足"]


def pptx_alarm_health_lines(layers: Dict[str, Any]) -> List[str]:
    return _report_section_lines(layers, "status")


def pptx_kpi_capability_lines(layers: Dict[str, Any]) -> List[str]:
    return _selected_report_lines(
        layers,
        "capability",
        ["cpk", "cp", "judgment", "usl", "lsl", "target"],
        "【製程統計分析｜規格/能力】",
    )


def pptx_engineering_data_lines(layers: Dict[str, Any]) -> List[str]:
    return _selected_report_lines(
        layers,
        "stability",
        ["yield", "dpmo", "sigma", "sample", "range"],
        "【製程統計分析｜穩定性/資料範圍】",
    )


def pptx_layer8_diagnosis_lines(layers: Dict[str, Any]) -> List[str]:
    return _report_section_lines(layers, "diagnosis")


def pptx_defect_structure_lines(layers: Dict[str, Any]) -> List[str]:
    return _selected_report_lines(
        layers,
        "stability",
        ["pattern", "cluster_ratio", "drift_insight", "top_ref", "outlier"],
        "【製程統計分析｜缺陷與量測透視】",
    )


def pptx_product_context_lines(layers: Dict[str, Any]) -> List[str]:
    return _report_section_lines(layers, "context")


def pptx_stability_dashboard_lines(layers: Dict[str, Any]) -> List[str]:
    status_lines = _selected_report_lines(
        layers,
        "status",
        ["ooc_rate", "cluster"],
        "【製程統計分析｜穩定性指標】",
    )
    stability_lines = _selected_report_lines(
        layers,
        "stability",
        ["drift_insight"],
        "【製程統計分析｜穩定性指標】",
    )
    return status_lines + stability_lines[1:]
