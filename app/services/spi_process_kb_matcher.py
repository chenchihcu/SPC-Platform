"""
Match runtime diagnostics signals to SPI process KB rules (R001…) and matrix rows.

Heuristic scoring: chart keywords + process-type alignment + multi-chart presence.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Set, Tuple

# KB process_type_classification → internal anomaly family keywords
_PROCESS_TYPE_TO_ANOMALY: Dict[str, Tuple[str, ...]] = {
    "Local Issue": ("Local", "Cluster"),
    "Global Drift": ("Drift",),
    "Global Shift": ("Shift",),
    "Variation Issue": ("Variation_increase", "Non-normal", "Shift", "Local", "Cluster"),
}

_CHART_KEYWORDS = (
    "heatmap",
    "cusum",
    "ewma",
    "spc",
    "histogram",
    "trend",
    "scatter",
    "normality",
    "run chart",
    "run_chart",
    "component",
    "pareto",
    "anova",
    "grr",
    "gage",
    "variance",
    "i-mr",
    "imr",
    "control chart",
    "boxplot",
    "offset",
)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).lower()).strip()


def _chart_keywords_from_signals(signals: List[Dict[str, Any]]) -> Set[str]:
    found: Set[str] = set()
    for s in signals:
        ct = _norm(str(s.get("chart_type", "")))
        summary = _norm(str(s.get("summary", "")))
        rid = _norm(str(s.get("rule_id", "")))
        blob = f"{ct} {summary} {rid}"
        for kw in _CHART_KEYWORDS:
            if kw in blob:
                found.add(kw)
    return found


def _rule_text_blob(rule: Dict[str, Any]) -> str:
    parts = [
        str(rule.get("signal_a", "")),
        str(rule.get("signal_b", "")),
        str(rule.get("trigger_description", "")),
        str(rule.get("spatial_temporal_condition", "")),
    ]
    return _norm(" ".join(parts))


def _score_rule_against_signals(
    rule: Dict[str, Any],
    signals: List[Dict[str, Any]],
    primary_anomaly_type: str,
) -> Tuple[int, str]:
    """
    Return (score, confidence_label). Higher is better.
    """
    blob = _rule_text_blob(rule)
    score = 0
    kw_hits = _chart_keywords_from_signals(signals)
    for kw in kw_hits:
        if kw in blob:
            score += 2

    pclass = str(rule.get("process_type_classification", ""))
    expected = _PROCESS_TYPE_TO_ANOMALY.get(pclass, ())
    if expected and primary_anomaly_type in expected:
        score += 3
    elif pclass == "Variation Issue" and primary_anomaly_type in (
        "Variation_increase",
        "Non-normal",
        "Shift",
    ):
        score += 2

    if len(set(s.get("chart_type", "") for s in signals)) >= 2:
        score += 1

    if score >= 6:
        conf = "high"
    elif score >= 3:
        conf = "medium"
    else:
        conf = "low"
    return score, conf


def match_multi_signal_rules(
    rules: List[Dict[str, Any]],
    signals: List[Dict[str, Any]],
    primary_anomaly_type: str,
    *,
    top_n: int = 5,
    min_score: int = 1,
) -> List[Dict[str, Any]]:
    """Return top matching rules with scores (for kb_matched_rules)."""
    ranked: List[Tuple[int, str, Dict[str, Any]]] = []
    for rule in rules:
        rid = str(rule.get("rule_id", ""))
        if not rid:
            continue
        sc, conf = _score_rule_against_signals(rule, signals, primary_anomaly_type)
        if sc >= min_score:
            ranked.append(
                (
                    sc,
                    conf,
                    {
                        "rule_id": rid,
                        "match_score": sc,
                        "match_confidence": conf,
                        "process_type_classification": rule.get(
                            "process_type_classification", ""
                        ),
                        "summary": str(rule.get("trigger_description", ""))[:240],
                        "priority_inspection_items": str(
                            rule.get("priority_inspection_items", "")
                        ),
                        "cause_hypotheses": list(rule.get("cause_hypotheses", []) or []),
                    },
                )
            )
    ranked.sort(key=lambda x: (-x[0], x[1]))
    return [r[2] for r in ranked[:top_n]]


def map_internal_abnormality_to_matrix_label(internal: str) -> str:
    return {
        "Drift": "Drift",
        "Shift": "Shift",
        "Cluster": "Cluster",
        "Local": "Cluster",
        "Non-normal": "Non-normal",
        "Variation_increase": "Variation",
    }.get(internal, "Drift")


def find_dimension_matrix_rows(
    matrix: List[Dict[str, Any]],
    spi_dimension: str,
    internal_abnormality: str,
) -> List[Dict[str, Any]]:
    """Return rows matching Volume/Height and matrix abnormality label."""
    dim = _norm(spi_dimension)
    abn = _norm(map_internal_abnormality_to_matrix_label(internal_abnormality))
    out: List[Dict[str, Any]] = []
    for row in matrix:
        if _norm(str(row.get("spi_dimension", ""))) != dim:
            continue
        if _norm(str(row.get("abnormality_type", ""))) != abn:
            continue
        out.append(row)
    return out


def infer_spi_dimension_from_signals(signals: List[Dict[str, Any]]) -> str:
    """Infer Volume vs Height from feature/summary text."""
    blob = " ".join(
        str(s.get("feature", "")) + str(s.get("summary", "")) for s in signals
    ).lower()
    if "height" in blob or "高度" in blob:
        return "Height"
    return "Volume"


def build_matrix_cause_hypotheses(
    matrix_rows: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """Flatten matrix row cells into category/description lines."""
    cols = [
        ("Stencil / 鋼網", "stencil"),
        ("Squeegee / 刮刀", "squeegee"),
        ("Solder Paste / 錫膏", "paste"),
        ("PCB / Pad", "pcb_pad"),
        ("Alignment / 對位", "alignment"),
        ("Environment / 環境", "environment"),
    ]
    out: List[Dict[str, str]] = []
    for row in matrix_rows:
        for label, key in cols:
            val = str(row.get(key, "") or "").strip()
            if val:
                out.append({"category": f"KnowledgeBase / {label}", "description": val})
    return out


def match_chart_signal_lookup(
    lookups: List[Dict[str, Any]],
    signals: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Match KB chart rows when chart_type appears in signal chart_type or summary."""
    hits: List[Dict[str, Any]] = []
    for entry in lookups:
        ct = _norm(str(entry.get("chart_type", "")))
        if not ct:
            continue
        for s in signals:
            sig_ct = _norm(str(s.get("chart_type", "")))
            summary = _norm(str(s.get("summary", "")))
            if ct not in sig_ct and ct not in summary:
                continue
            hits.append(
                {
                    "chart_type": entry.get("chart_type"),
                    "observed_signal": entry.get("observed_signal"),
                    "rule_ids": list(entry.get("rule_ids", [])),
                    "process_type": entry.get("process_type"),
                    "urgency": entry.get("urgency"),
                    "likely_causes": [
                        c
                        for c in (
                            entry.get("likely_cause_1"),
                            entry.get("likely_cause_2"),
                            entry.get("likely_cause_3"),
                        )
                        if c
                    ],
                }
            )
            break
    return hits


def merge_inspection_checklist_items(
    checklist: List[Dict[str, Any]],
    cause_categories: List[str],
    *,
    limit: int = 6,
) -> List[Dict[str, Any]]:
    """
    Pick checklist rows whose process_category appears in cause category strings.
    """
    picked: List[Dict[str, Any]] = []
    cats_lower = [c.lower() for c in cause_categories]
    for row in checklist:
        pc = str(row.get("process_category", "")).lower()
        if pc and any(pc in cl or cl in pc for cl in cats_lower):
            picked.append(
                {
                    "process_category": row.get("process_category"),
                    "inspection_item": row.get("inspection_item"),
                    "measurement_method": row.get("measurement_method"),
                    "normal_threshold": row.get("normal_threshold"),
                    "priority_stars": row.get("priority_stars"),
                    "remarks": row.get("remarks"),
                }
            )
        if len(picked) >= limit:
            break
    return picked
