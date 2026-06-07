"""Single-source interpretation dictionary for DiagnosticPage dashboard layers."""

from __future__ import annotations

from typing import Any

_DIAGNOSTIC_INTERPRETATIONS: tuple[dict[str, str], ...] = (
    {
        "layer_key": "layer_1_alarm",
        "title": "1. 警報與健康狀態（layer_1_alarm）",
        "icon": "🚨",
        "illustration": "diag_health.png",
        "purpose": "快速判斷製程是否在受控範圍內，先看是否有立即風險。",
        "how_to_read": "先看問題類別與 OOC 比率，再看漂移比例與群聚數；若同時升高，代表異常不是偶發。",
        "threshold_meaning": "OOC/OOS 趨近 0 表示穩定；漂移比例接近或超過 1.0 代表均值偏移風險提升。",
        "suggested_action": "高警報時先凍結受影響批次，優先核查印刷參數、刮刀與鋼網污染狀態。",
    },
    {
        "layer_key": "layer_2_kpi",
        "title": "2. KPI 品質績效（layer_2_kpi）",
        "icon": "📊",
        "purpose": "以良率、DPMO、Sigma 量化目前製程品質表現。",
        "how_to_read": "良率越高越好，DPMO 越低越好，Sigma 越高越穩定；三者需同時觀察避免單指標誤判。",
        "threshold_meaning": "若良率下降且 DPMO 上升，通常表示異常已進入可見缺陷層級。",
        "suggested_action": "對比前一批次與同料號歷史基線，確認是短期波動或系統性退化。",
    },
    {
        "layer_key": "layer_3_info",
        "title": "3. 樣本與資料覆蓋（layer_3_info）",
        "icon": "🔍",
        "purpose": "確認統計判讀是否有足夠樣本與變異資訊支撐。",
        "how_to_read": "先看樣本數，再看全距；樣本不足時，任何結論都要標註不確定性。",
        "threshold_meaning": "樣本太少或全距異常窄時，可能出現過度樂觀的能力指標。",
        "suggested_action": "若資料覆蓋不足，先擴充取樣區段再做正式處置決策。",
    },
    {
        "layer_key": "layer_4_defect_structure",
        "title": "4. 缺陷結構與空間特徵（layer_4_defect_structure）",
        "icon": "🕸️",
        "illustration": "diag_cluster.png",
        "purpose": "辨識異常是隨機散佈還是群聚型態，幫助根因定位。",
        "how_to_read": "看異常型態、群聚係數與 Top 異常位號；重複位號通常指向固定設備或程式路徑問題。",
        "threshold_meaning": "群聚係數升高代表異常更集中，通常比隨機分布更具工程處置價值。",
        "suggested_action": "針對高頻位號執行點位複驗，並比對鋼網開孔與刮刀路徑一致性。",
    },
    {
        "layer_key": "layer_5_spec_analysis",
        "title": "5. 規格與能力分析（layer_5_spec_analysis）",
        "icon": "📐",
        "illustration": "diag_spec.png",
        "purpose": "檢查均值與變異是否在規格帶內，並評估 Cp/Cpk 能力。",
        "how_to_read": "先看 Cpk，再看 Cp 與 mean shift；Cpk 低時表示偏移或波動已影響規格風險。",
        "threshold_meaning": "Cpk 越接近 1.33 以上通常越穩健；若 OOS 比率同時上升，需立即處置。",
        "suggested_action": "先判斷偏移型（中心偏）或變異型（散佈大），再選擇調機或治具/材料改善。",
    },
    {
        "layer_key": "layer_6_product_context",
        "title": "6. 產品與工單背景（layer_6_product_context）",
        "icon": "📦",
        "purpose": "把統計結果連回產品、工單與批量情境，避免脫離製造上下文。",
        "how_to_read": "確認產品、供應商/醫電工單、批量與鋼網資訊，對照異常是否集中於特定工單條件。",
        "threshold_meaning": "若異常只發生在特定工單或鋼網條件，代表可縮小排查範圍。",
        "suggested_action": "建立工單分層追蹤，將高風險條件加入下一輪預警規則。",
    },
    {
        "layer_key": "layer_7_engineering_info",
        "title": "7. 工程統計摘要（layer_7_engineering_info）",
        "icon": "🛠️",
        "purpose": "提供均值與標準差等基礎統計，補齊工程判讀底層證據。",
        "how_to_read": "均值偏離目標且標準差放大時，代表製程中心與穩定度同時惡化。",
        "threshold_meaning": "標準差相對規格帶持續升高時，能力指標通常會連動下降。",
        "suggested_action": "優先檢查製程參數漂移來源，再以短週期再取樣確認修正效果。",
    },
)


def get_diagnostic_interpretation_registry() -> list[dict[str, str]]:
    """Return a copy of the diagnostic interpretation dictionary."""
    return [dict(item) for item in _DIAGNOSTIC_INTERPRETATIONS]


def build_diagnostic_interpretation_sections(layers: dict[str, Any] | None = None) -> list[dict[str, str]]:
    """Return dialog-ready sections for layer_1..layer_7 with current-state notes."""
    layer_payload = layers or {}
    sections: list[dict[str, str]] = []
    for item in _DIAGNOSTIC_INTERPRETATIONS:
        layer_key = item["layer_key"]
        current_line = _build_current_state_line(layer_key, layer_payload.get(layer_key))
        body = (
            f"用途：{item['purpose']}\n\n"
            f"如何解讀：{item['how_to_read']}\n\n"
            f"門檻含意：{item['threshold_meaning']}\n\n"
            f"建議動作：{item['suggested_action']}\n\n"
            f"{current_line}"
        )
        sections.append({
            "title": item["title"],
            "body": body,
            "layer_key": layer_key,
            "icon": item.get("icon", ""),
            "illustration": item.get("illustration", ""),
        })
    return sections


def _build_current_state_line(layer_key: str, layer_data: Any) -> str:
    if not isinstance(layer_data, dict) or not layer_data:
        return "目前狀態：NoData（尚未完成分析，可先依本段解讀框架建立判讀邏輯）。"

    if layer_key == "layer_1_alarm":
        return (
            "目前值："
            f"問題類別={layer_data.get('issue_type_display_zh', '—')}；"
            f"OOC={_fmt_pct(layer_data.get('ooc_rate'))}；"
            f"漂移比={_fmt_num(layer_data.get('max_drift_ratio'))}。"
        )

    if layer_key == "layer_2_kpi":
        return (
            "目前值："
            f"Yield={_fmt_pct(layer_data.get('yield_pct'), already_percent=True)}；"
            f"DPMO={_fmt_num(layer_data.get('dpmo'))}；"
            f"Sigma={_fmt_num(layer_data.get('sigma_level'))}。"
        )

    if layer_key == "layer_3_info":
        return (
            "目前值："
            f"樣本數={layer_data.get('sample_size', '—')}；"
            f"全距={_fmt_num(layer_data.get('range'))}。"
        )

    if layer_key == "layer_4_defect_structure":
        return (
            "目前值："
            f"型態={layer_data.get('defect_pattern_zh', '—')}；"
            f"群聚係數={_fmt_pct(layer_data.get('cluster_ratio'))}。"
        )

    if layer_key == "layer_5_spec_analysis":
        return (
            "目前值："
            f"Cp={_fmt_num(layer_data.get('cp'))}；"
            f"Cpk={_fmt_num(layer_data.get('cpk'))}；"
            f"OOS={_fmt_pct(layer_data.get('oos_rate'))}。"
        )

    if layer_key == "layer_6_product_context":
        return (
            "目前值："
            f"產品={layer_data.get('product_name', '—')}；"
            f"供應商工單={layer_data.get('supplier_work_order_no', '—')}；"
            f"醫電工單={layer_data.get('outsource_work_order_no') or layer_data.get('work_order_no', '—')}。"
        )

    if layer_key == "layer_7_engineering_info":
        return (
            "目前值："
            f"mean={_fmt_num(layer_data.get('mean'))}；"
            f"std={_fmt_num(layer_data.get('std'))}。"
        )

    return "目前狀態：Ready。"


def _fmt_num(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.4g}"
    except (TypeError, ValueError):
        return str(value)


def _fmt_pct(value: Any, *, already_percent: bool = False) -> str:
    if value is None:
        return "—"
    try:
        n = float(value)
    except (TypeError, ValueError):
        return str(value)
    if already_percent:
        return f"{n:.2f}%"
    return f"{n * 100:.2f}%"
