"""
multi_signal_diagnosis.py
=========================
Multi-Signal Correlation Diagnosis for SMT SPI SPC reports.

Diagnostic logic:
  1. Collect anomaly signals by chart type from diagnostics list
  2. Classify anomaly type: Shift / Drift / Local / Cluster / Variation_increase / Non-normal
  3. Analyze cross-signal correlations (pattern matching)
  4. Map combined anomaly patterns → process cause hypotheses
  5. Generate recommended check items per cause category
  6. Return structured result dict for report rendering

Constraint: this is a report-layer module only.
Do NOT import from app.analytics.* — consume only the `diagnostics` list
already produced by the analytics pipeline.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from app.services import spi_process_kb_matcher as _kb_m
from app.services.spi_process_kb_loader import (
    SPIProcessKnowledgeBase,
    load_spi_process_kb,
)

logger = logging.getLogger(__name__)

# ── 1. Signal collection ──────────────────────────────────────────────────────

# rule_id keyword → chart type label shown in report
_RULE_TO_CHART: Dict[str, str] = {
    "cusum":      "CUSUM",
    "ewma":       "EWMA",
    "spc":        "SPC Control Chart",
    "trend":      "Trend Chart",
    "histogram":  "Histogram",
    "normality":  "Histogram",
    "heatmap":    "Heatmap",
    "spatial":    "Heatmap",
    "scatter":    "Scatter Plot",
    "component":  "Component Ranking",
    "ranking":    "Component Ranking",
    "gage":       "GR&R Chart",
    "grr":        "GR&R Chart",
    "variance":   "Variance Decomposition",
    "variation":  "Variance Decomposition",
}

# rule_id keyword → anomaly type
_RULE_TO_ANOMALY_TYPE: Dict[str, str] = {
    "cusum":      "Drift",
    "trend":      "Drift",
    "drift":      "Drift",
    "ewma":       "Shift",
    "shift":      "Shift",
    "ooc":        "Shift",
    "outlier":    "Shift",
    "spc":        "Shift",
    "cluster":    "Cluster",
    "component":  "Cluster",
    "scatter":    "Cluster",
    "heatmap":    "Local",
    "spatial":    "Local",
    "local":      "Local",
    "histogram":  "Non-normal",
    "normality":  "Non-normal",
    "non_normal": "Non-normal",
    "variance":   "Variation_increase",
    "variation":  "Variation_increase",
    "gage":       "Variation_increase",
    "grr":        "Variation_increase",
}

# Anomaly type → Chinese label
_ANOMALY_TYPE_ZH: Dict[str, str] = {
    "Drift":               "漸進漂移 Drift",
    "Shift":               "突發偏移 Shift",
    "Local":               "局部異常 Local",
    "Cluster":             "區域群聚 Cluster",
    "Variation_increase":  "變異放大 Variation Increase",
    "Non-normal":          "非常態分布 Non-normal",
}


def _match_keyword(text: str, mapping: Dict[str, str]) -> Optional[str]:
    """Case-insensitive partial-match lookup against keyword mapping."""
    tl = text.lower()
    for kw, val in mapping.items():
        if kw in tl:
            return val
    return None


def collect_signals(diagnostics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Step 1 — Collect anomaly signals from diagnostics, tagged by chart type and
    anomaly type.  Info-level entries are skipped.

    Returns list of signal dicts:
      {feature, rule_id, severity, chart_type, anomaly_type,
       anomaly_type_zh, summary}
    """
    signals: List[Dict[str, Any]] = []
    for d in diagnostics:
        if not isinstance(d, dict):
            continue
        sev = str(d.get("severity", "info")).lower()
        if sev == "info":
            continue
        rule_id = str(d.get("rule_id", "") or "")
        feature = str(
            d.get("feature_label", "") or d.get("feature", "") or ""
        ).strip()
        chart_type  = _match_keyword(rule_id, _RULE_TO_CHART)      or "SPC Control Chart"
        anomaly_type = _match_keyword(rule_id, _RULE_TO_ANOMALY_TYPE) or "Shift"
        signals.append({
            "feature":        feature,
            "rule_id":        rule_id,
            "severity":       sev,
            "chart_type":     chart_type,
            "anomaly_type":   anomaly_type,
            "anomaly_type_zh": _ANOMALY_TYPE_ZH.get(anomaly_type, anomaly_type),
            "summary":        str(d.get("summary", "") or ""),
        })
    return signals


# ── 2. Primary anomaly type classification ────────────────────────────────────

def classify_primary_anomaly_type(signals: List[Dict[str, Any]]) -> str:
    """
    Step 2 — Determine dominant anomaly type (error-level first, then warning,
    then frequency).
    """
    if not signals:
        return "Unknown"
    for sev in ("error", "warning"):
        types = [s["anomaly_type"] for s in signals if s["severity"] == sev]
        if types:
            return max(set(types), key=types.count)
    return signals[0]["anomaly_type"]


# ── 3. Cross-signal correlation analysis ─────────────────────────────────────

# Each rule: (required anomaly_type set, zh_pattern_label, detail_text)
# Evaluated in order; first matching rule wins.
_CORRELATION_RULES: List[Tuple[Set[str], str, str]] = [
    (
        {"Drift", "Non-normal"},
        "系統性漂移 + 分布異常",
        "CUSUM / Trend 顯示製程中心持續偏移，Histogram 同時呈非常態分布。"
        "異常具方向性，屬系統性原因而非隨機波動；能力指標（Cpk）可能低估實際風險。",
    ),
    (
        {"Drift", "Cluster"},
        "漸進漂移 + 區域群聚",
        "趨勢圖顯示全域漂移，Heatmap / Component Ranking 同時出現局部群聚。"
        "可能同時存在全域原因（如鋼網整體磨損）與局部原因（如特定開口堵塞）。",
    ),
    (
        {"Drift", "Local"},
        "漸進漂移 + 局部異常",
        "製程中心漸進偏移，同時 Heatmap 顯示特定 Pad 位置持續異常。"
        "建議同步確認鋼網整體狀態與局部開口情形。",
    ),
    (
        {"Shift", "Cluster"},
        "突發偏移 + 區域群聚",
        "SPC / EWMA 顯示突發性偏移，Heatmap 顯示特定區域異常集中。"
        "與換料、換鋼網或 PCB 翹曲導致局部對位偏差高度相關。",
    ),
    (
        {"Shift", "Non-normal"},
        "突發偏移 + 分布異常",
        "製程在某時間點突然偏移，且分布呈非常態（可能雙峰）。"
        "需確認是否為物料批次混用或換料前後資料混合所致。",
    ),
    (
        {"Local", "Cluster"},
        "局部異常 + 區域群聚",
        "Heatmap 顯示特定 Pad 或區域異常高度集中。"
        "通常與鋼網局部堵塞、PCB 局部翹曲或印刷對位系統性偏差相關。",
    ),
    (
        {"Drift"},
        "單純漸進漂移",
        "CUSUM / Trend 訊號顯示製程中心隨時間緩慢偏移。"
        "屬典型磨耗型（鋼網磨損）或刮刀參數漂移型異常。",
    ),
    (
        {"Shift"},
        "單純突發偏移",
        "SPC / EWMA 顯示製程在某時間點突然偏移。"
        "與物料批次更換、鋼網更換或設備操作條件變更高度相關。",
    ),
    (
        {"Variation_increase"},
        "變異放大",
        "Variance Decomposition / GR&R 顯示總變異增大。"
        "可能來自量測系統退化（GR&R 過大）或製程本身穩定性下降。",
    ),
    (
        {"Non-normal"},
        "非常態分布",
        "Histogram / normality test 顯示資料分布偏離常態。"
        "Cpk / Ppk 估算可能失準，能力評估需輔以非常態統計方法。",
    ),
]


def analyze_correlations(signals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Step 3 — Match signal set against correlation rule table.

    Returns:
      pattern_label         - zh label of matched pattern
      pattern_detail        - engineering explanation
      anomaly_types_present - sorted list of distinct anomaly types
      chart_types_present   - sorted list of distinct chart types triggered
      signal_count          - total number of signals
    """
    anomaly_types: Set[str] = {s["anomaly_type"] for s in signals}
    chart_types   = sorted({s["chart_type"] for s in signals})

    matched_label  = "多訊號複合異常"
    matched_detail = (
        "偵測到多個異常訊號，建議整合 CUSUM、SPC、Heatmap 等多圖表進行綜合判讀，"
        "不可僅憑單一統計指標作出製程判斷。"
    )

    for required, label, detail in _CORRELATION_RULES:
        if required.issubset(anomaly_types):
            matched_label  = label
            matched_detail = detail
            break

    return {
        "pattern_label":          matched_label,
        "pattern_detail":         matched_detail,
        "anomaly_types_present":  sorted(anomaly_types),
        "chart_types_present":    chart_types,
        "signal_count":           len(signals),
    }


# ── 4. Process cause hypothesis ───────────────────────────────────────────────

# (frozenset of anomaly_types, causes list)
# Each cause: (category_label, zh_description)
_CAUSE_TABLE: List[Tuple[FrozenSet[str], List[Tuple[str, str]]]] = [
    (
        frozenset({"Drift", "Non-normal"}),
        [
            ("Stencil / 鋼網",       "鋼網磨損伴隨開口形變，印刷量分布逐漸偏斜且非對稱。"),
            ("Squeegee / 刮刀",      "刮刀磨損不均，導致漂移且分布偏態。"),
            ("Solder Paste / 錫膏",  "錫膏流變特性異常，印刷量分布呈非常態。"),
        ],
    ),
    (
        frozenset({"Drift", "Cluster"}),
        [
            ("Stencil / 鋼網",   "鋼網整體磨損（全域漂移）且局部開口堵塞（群聚）並存。"),
            ("Squeegee / 刮刀",  "刮刀壓力分布不均，整體趨勢偏移合併局部印刷不足。"),
            ("Environment / 環境", "環境溫溼度長時間漂移，同時導致特定 Pad 位置印刷異常。"),
        ],
    ),
    (
        frozenset({"Drift", "Local"}),
        [
            ("Stencil / 鋼網",  "鋼網整體磨損（漂移）+ 局部特定開口異常（Local）。"),
            ("PCB / 基板",      "PCB 翹曲隨批次累積加劇，特定位置始終接觸不良。"),
        ],
    ),
    (
        frozenset({"Shift", "Cluster"}),
        [
            ("PCB / 基板",       "PCB 翹曲或厚度不均，換料後局部區域印刷量突變。"),
            ("Alignment / 對位", "換鋼網/換料後對位校正不足，特定 Pad 群聚偏移。"),
            ("Stencil / 鋼網",   "換鋼網後局部張力不均，特定位置印刷突發異常。"),
        ],
    ),
    (
        frozenset({"Shift", "Non-normal"}),
        [
            ("Solder Paste / 錫膏", "錫膏批次更換導致特性突變，分布呈雙峰（換料前後混合）。"),
            ("PCB / 基板",          "PCB 批次混用（厚度不一），導致偏移並呈非常態。"),
        ],
    ),
    (
        frozenset({"Local", "Cluster"}),
        [
            ("Stencil / 鋼網",   "鋼網特定位置開口堵塞（錫膏殘留或開口變形）。"),
            ("PCB / 基板",       "PCB 局部翹曲或表面汙染影響特定 Pad 印刷。"),
            ("Alignment / 對位", "印刷對位在特定方向呈系統性偏差。"),
        ],
    ),
    (
        frozenset({"Drift"}),
        [
            ("Stencil / 鋼網",   "鋼網開口隨累積印刷次數逐漸磨損堵塞，錫膏量持續下降。"),
            ("Squeegee / 刮刀",  "刮刀壓力或速度隨時間偏移，印刷厚度緩慢改變。"),
            ("Environment / 環境", "環境溫溼度長時間漂移，影響錫膏黏度。"),
        ],
    ),
    (
        frozenset({"Shift"}),
        [
            ("Solder Paste / 錫膏", "錫膏批次更換導致黏度或印刷特性突變。"),
            ("Stencil / 鋼網",      "鋼網更換後對位參數未重新校正。"),
            ("Alignment / 對位",    "印刷機對位基準突發性偏移（Mark 識別異常）。"),
        ],
    ),
    (
        frozenset({"Variation_increase"}),
        [
            ("Measurement / 量測系統", "SPI 設備 GR&R 過大，量測本身的變異已不可忽略。"),
            ("Squeegee / 刮刀",        "刮刀磨損不均或刮板彎曲，導致批內印刷變異增大。"),
            ("Solder Paste / 錫膏",    "錫膏攪拌不均或超出使用時限，黏度不穩定。"),
        ],
    ),
    (
        frozenset({"Non-normal"}),
        [
            ("Solder Paste / 錫膏", "錫膏印刷量呈雙峰或偏態，可能為混料或雙刮刀效應。"),
            ("PCB / 基板",          "PCB 批次混用（厚度差異）導致分布非常態。"),
        ],
    ),
]


def _best_cause_key(anomaly_types: Set[str]) -> FrozenSet[str]:
    """Return the cause table key that is a subset of anomaly_types with most elements."""
    best: FrozenSet[str] = frozenset()
    best_len = -1
    for key, _ in _CAUSE_TABLE:
        if key.issubset(anomaly_types) and len(key) > best_len:
            best = key
            best_len = len(key)
    return best


def generate_cause_hypothesis(
    signals: List[Dict[str, Any]],
    correlation: Dict[str, Any],
) -> List[Dict[str, str]]:
    """
    Step 4 — Generate process cause hypotheses.
    Returns list of {category, description}.
    """
    anomaly_types: Set[str] = set(correlation.get("anomaly_types_present", []))
    best_key = _best_cause_key(anomaly_types)

    for key, causes in _CAUSE_TABLE:
        if key == best_key:
            return [{"category": cat, "description": desc} for cat, desc in causes]

    # Fallback: generic SMT SPI causes
    return [
        {"category": "Stencil / 鋼網",      "description": "確認鋼網開口尺寸與磨損狀況。"},
        {"category": "Squeegee / 刮刀",     "description": "確認刮刀壓力、速度與磨損情形。"},
        {"category": "Solder Paste / 錫膏", "description": "確認錫膏批次、黏度與使用時間。"},
    ]


# ── 5. Recommended check items ────────────────────────────────────────────────

_CHECK_ITEMS_BY_CATEGORY: Dict[str, List[str]] = {
    "Stencil / 鋼網": [
        "目視檢查鋼網開口是否有堵塞、殘留錫膏或變形",
        "量測鋼網開口尺寸（比對設計值，注意磨損量）",
        "確認鋼網清潔頻率與清潔效果（擦拭紙清潔記錄）",
        "查詢鋼網累積印刷次數（比對壽命管控閾值）",
    ],
    "Squeegee / 刮刀": [
        "確認前後刮刀壓力設定值（與製程 SOP 比對）",
        "目視檢查刮刀邊緣磨損情形（是否缺口或彎曲）",
        "確認刮刀速度與角度設定",
        "記錄刮刀更換日期與累積使用次數",
    ],
    "Solder Paste / 錫膏": [
        "確認錫膏批次號、製造日期與開封日期",
        "確認錫膏冷藏取出後的回溫時間（是否符合規範）",
        "量測或確認錫膏黏度（黏度計或 slump test）",
        "確認錫膏攪拌時間與方式是否依 SOP 執行",
    ],
    "PCB / 基板": [
        "量測 PCB 翹曲量（四角與中心，比對規格上限）",
        "確認 PCB 批次號與供應商",
        "目視或量測 PCB 表面汙染或氧化情形",
        "確認支撐針位置設定（防止印刷時 PCB 變形）",
    ],
    "Alignment / 對位": [
        "確認印刷機 Fiducial Mark 辨識品質與對位精度",
        "執行對位精度驗證（使用測試板印刷並量測偏移）",
        "確認機台夾具是否鬆動或磨損",
        "回查最近換鋼網後的對位校正記錄",
    ],
    "Environment / 環境": [
        "記錄印刷區域溫溼度數據（24 小時趨勢圖）",
        "確認錫膏使用環境溫溼度是否符合材料規格",
        "確認空調系統運作狀態與維護記錄",
    ],
    "Measurement / 量測系統": [
        "執行 SPI 設備 GR&R 驗證（確認量測系統本身的穩定性）",
        "確認 SPI 設備上次校準日期是否在有效期內",
        "比對 SPI 量測結果與人工切片量測結果（交叉驗證）",
    ],
}


def generate_check_items(
    causes: List[Dict[str, str]],
    max_per_category: int = 3,
) -> List[Dict[str, Any]]:
    """
    Step 5 — Generate recommended check items from cause hypotheses.
    Returns list of {category, items: List[str]}.
    """
    result: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for cause in causes:
        cat = cause["category"]
        if cat in seen:
            continue
        seen.add(cat)
        items = _CHECK_ITEMS_BY_CATEGORY.get(cat, [])[:max_per_category]
        if items:
            result.append({"category": cat, "items": items})
    return result


# ── 6. Top-level entry point ──────────────────────────────────────────────────

def run_multi_signal_diagnosis(
    diagnostics: List[Dict[str, Any]],
    *,
    kb_bundle: Optional[SPIProcessKnowledgeBase] = None,
) -> Dict[str, Any]:
    """
    Run the full multi-signal correlation diagnosis pipeline.

    Args:
        diagnostics: List of diagnostic dicts from the analytics pipeline.
        kb_bundle: Optional preloaded SPI process knowledge base (for tests).

    Returns dict with keys:
        signals               - list of detected anomaly signals (chart/type tagged)
        primary_anomaly_type  - dominant anomaly type string (e.g. "Drift")
        primary_anomaly_type_zh - Chinese label
        correlation           - cross-signal correlation result dict
        cause_hypotheses      - list of {category, description}
        check_items           - list of {category, items: [str]}
        has_multi_signal      - True if 2+ distinct chart types involved
        kb_load_status        - ok | partial | empty (SPI process KB JSON bundle)
        kb_load_messages      - loader warnings
        kb_matched_rules      - top heuristic matches to R-rules (if KB loaded)
        kb_chart_lookup_hits  - chart/signal quick-matrix rows (if any)
    """
    signals               = collect_signals(diagnostics)
    primary_anomaly_type  = classify_primary_anomaly_type(signals)
    correlation           = analyze_correlations(signals)
    causes                = generate_cause_hypothesis(signals, correlation)
    check_items           = generate_check_items(causes)
    distinct_charts: Set[str] = {s["chart_type"] for s in signals}

    kb_load_status = "empty"
    kb_load_messages: List[str] = []
    kb_matched_rules: List[Dict[str, Any]] = []
    kb_chart_lookup_hits: List[Dict[str, Any]] = []
    kb_inspection_rows: List[Dict[str, Any]] = []

    if kb_bundle is None:
        kb, kb_report = load_spi_process_kb()
        kb_load_status = kb_report.status
        kb_load_messages = list(kb_report.messages)
        if kb_report.messages:
            logger.warning("SPI process KB load: %s — %s", kb_report.status, kb_report.messages)
    else:
        kb = kb_bundle
        kb_load_status = "ok"

    if kb.multi_signal_rules:
        kb_matched_rules = _kb_m.match_multi_signal_rules(
            kb.multi_signal_rules,
            signals,
            primary_anomaly_type,
            top_n=5,
            min_score=1,
        )
        # Enrich causes with top rule hypotheses (read-only narrative)
        if kb_matched_rules:
            top = kb_matched_rules[0]
            for line in top.get("cause_hypotheses", [])[:4]:
                if isinstance(line, str) and line.strip():
                    causes.insert(
                        0,
                        {
                            "category": f"KnowledgeBase / {top.get('rule_id', 'R?')}",
                            "description": line.strip(),
                        },
                    )

    spi_dim = _kb_m.infer_spi_dimension_from_signals(signals)
    mrows = _kb_m.find_dimension_matrix_rows(
        kb.dimension_abnormality_matrix,
        spi_dim,
        primary_anomaly_type,
    )
    matrix_causes = _kb_m.build_matrix_cause_hypotheses(mrows)
    if matrix_causes:
        causes = matrix_causes + causes

    if kb.chart_signal_lookup:
        kb_chart_lookup_hits = _kb_m.match_chart_signal_lookup(
            kb.chart_signal_lookup,
            signals,
        )

    cause_cats = [str(c.get("category", "")) for c in causes]
    if kb.inspection_checklist:
        kb_inspection_rows = _kb_m.merge_inspection_checklist_items(
            kb.inspection_checklist,
            cause_cats,
            limit=6,
        )
        if kb_inspection_rows:
            lines = [
                f"{r.get('inspection_item', '—')} — 門檻: {r.get('normal_threshold', '—')} "
                f"({r.get('measurement_method', '—')})"
                for r in kb_inspection_rows
            ]
            check_items.append(
                {
                    "category": "KnowledgeBase / 檢查門檻",
                    "items": lines,
                }
            )

    causes = causes[:25]

    return {
        "signals":                signals,
        "primary_anomaly_type":   primary_anomaly_type,
        "primary_anomaly_type_zh": _ANOMALY_TYPE_ZH.get(
            primary_anomaly_type, primary_anomaly_type
        ),
        "correlation":            correlation,
        "cause_hypotheses":       causes,
        "check_items":            check_items,
        "has_multi_signal":       len(distinct_charts) >= 2,
        "kb_load_status":         kb_load_status,
        "kb_load_messages":       kb_load_messages,
        "kb_matched_rules":       kb_matched_rules,
        "kb_chart_lookup_hits":   kb_chart_lookup_hits,
        "kb_spi_dimension_inferred": spi_dim,
    }
