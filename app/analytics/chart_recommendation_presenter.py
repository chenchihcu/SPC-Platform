"""
chart_recommendation_presenter.py
----------------------------------
Reads the pre-computed diagnostic_evidence_matrix from the analysis payload
and converts it into:
  - chip_groups : list of feature-grouped recommendation entries for the UI chip strip
  - chart_status: per chart_id badge state for accordion checkbox decoration

This module is pure data logic — no Qt imports.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

# Badge state constants (used as QSS property values)
STATUS_RECOMMENDED = "recommended"       # evidence_state=support, severity warning/error
STATUS_AVAILABLE_WEAK = "available_weak" # analyzed but evidence neutral/refute
STATUS_INSUFFICIENT = "insufficient_data"# missing-data or unavailable
STATUS_NOT_APPLICABLE = "not_applicable" # feature count not satisfied


def _as_dict(v: Any) -> Dict[str, Any]:
    return v if isinstance(v, dict) else {}


def _as_list(v: Any) -> List[Any]:
    return v if isinstance(v, list) else []


def _feature_label(feature_set: Sequence[str]) -> str:
    parts = [str(f).strip() for f in feature_set if str(f).strip()]
    return " + ".join(parts) if parts else "（全特徵）"


def _best_status(candidates: Sequence[Mapping[str, Any]], chart_id: str) -> str:
    """Return the highest-priority badge status for chart_id across all feature sets."""
    best = STATUS_NOT_APPLICABLE
    priority = {
        STATUS_RECOMMENDED: 0,
        STATUS_AVAILABLE_WEAK: 1,
        STATUS_INSUFFICIENT: 2,
        STATUS_NOT_APPLICABLE: 3,
    }
    for c in candidates:
        if str(c.get("chart_id") or "") != chart_id:
            continue
        avail = str(c.get("availability") or "")
        state = str(c.get("evidence_state") or "")
        sev = str(c.get("severity") or "")

        if state == "support" and sev in {"warning", "error"}:
            cand_status = STATUS_RECOMMENDED
        elif avail == "analyzed" and state in {"refute", "neutral"}:
            cand_status = STATUS_AVAILABLE_WEAK
        elif avail in {"missing-data", "unavailable"}:
            cand_status = STATUS_INSUFFICIENT
        else:
            cand_status = STATUS_NOT_APPLICABLE

        if priority.get(cand_status, 9) < priority.get(best, 9):
            best = cand_status
    return best


def _is_feature_set_relevant(feature_set: Sequence[str], display_features: Sequence[str]) -> bool:
    """Return True if all members of feature_set are present in display_features."""
    if not feature_set:
        return True
    disp = set(display_features)
    return all(f in disp for f in feature_set)


def get_chart_recommendations(
    payload: Mapping[str, Any],
    display_features: Sequence[str],
) -> Dict[str, Any]:
    """
    Build chip_groups and chart_status from the diagnostic_evidence_matrix in payload.

    display_features: the features currently displayed in ChartAnalysisPage
      (may differ from payload["selected_features"] when user expands display).

    Returns:
      {
        "chip_groups": [
          {
            "feature_label": "Height",
            "chart_entries": [
              {"chart_id": "imr", "chart_name": "個別值與移動極差圖",
               "severity": "warning", "metric_snapshot": "OOC=3/40"},
              ...
            ],
          },
          ...
        ],
        "chart_status": {"imr": "recommended", "scatter_spec": "not_applicable", ...},
      }
    """
    matrix = _as_dict(_as_dict(payload).get("diagnostic_evidence_matrix"))
    candidates: List[Mapping[str, Any]] = _as_list(matrix.get("candidates"))
    summary = _as_dict(matrix.get("summary"))
    top_evidence: List[Mapping[str, Any]] = _as_list(summary.get("top_evidence"))

    # --- chart_status: best badge for each chart_id --------------------
    chart_status: Dict[str, str] = {}
    for c in candidates:
        cid = str(c.get("chart_id") or "")
        if not cid:
            continue
        if cid not in chart_status:
            chart_status[cid] = STATUS_NOT_APPLICABLE
        avail = str(c.get("availability") or "")
        state = str(c.get("evidence_state") or "")
        sev = str(c.get("severity") or "")
        priority = {
            STATUS_RECOMMENDED: 0,
            STATUS_AVAILABLE_WEAK: 1,
            STATUS_INSUFFICIENT: 2,
            STATUS_NOT_APPLICABLE: 3,
        }
        if state == "support" and sev in {"warning", "error"}:
            cand_status = STATUS_RECOMMENDED
        elif avail == "analyzed" and state in {"refute", "neutral"}:
            cand_status = STATUS_AVAILABLE_WEAK
        elif avail in {"missing-data", "unavailable"}:
            cand_status = STATUS_INSUFFICIENT
        else:
            cand_status = STATUS_NOT_APPLICABLE

        if priority.get(cand_status, 9) < priority.get(chart_status.get(cid, STATUS_NOT_APPLICABLE), 9):
            chart_status[cid] = cand_status

    # --- chip_groups: from top_evidence filtered by display_features ----
    # Group by feature_set so chips read "Height → I-MR" or "Volume+Area → 關聯熱圖"
    group_map: Dict[str, Dict[str, Any]] = {}  # feature_label → group

    for item in top_evidence:
        cid = str(item.get("chart_id") or "")
        chart_name = str(item.get("chart_name") or cid)
        feature_set: List[str] = _as_list(item.get("feature_set"))
        severity = str(item.get("severity") or "info")
        metric = str(item.get("metric_snapshot") or "")
        dimension_label = str(item.get("dimension_label") or "")

        if not _is_feature_set_relevant(feature_set, display_features or []):
            continue
        if not cid:
            continue

        flabel = _feature_label(feature_set)
        if flabel not in group_map:
            group_map[flabel] = {"feature_label": flabel, "feature_set": feature_set, "chart_entries": []}
        group_map[flabel]["chart_entries"].append(
            {
                "chart_id": cid,
                "chart_name": chart_name,
                "severity": severity,
                "metric_snapshot": metric,
                "dimension_label": dimension_label,
            }
        )

    # Also include next_chart_ids that have STATUS_RECOMMENDED but didn't make top_evidence
    next_ids: List[str] = _as_list(summary.get("next_chart_ids"))
    recommended_from_candidates = {
        cid for cid, st in chart_status.items() if st == STATUS_RECOMMENDED
    }
    top_ids = {str(item.get("chart_id") or "") for item in top_evidence}

    for cid in next_ids:
        if cid in top_ids or cid not in recommended_from_candidates:
            continue
        # find candidate to get feature_set
        for c in candidates:
            if str(c.get("chart_id") or "") == cid and str(c.get("evidence_state") or "") == "support":
                feature_set = _as_list(c.get("feature_set"))
                if not _is_feature_set_relevant(feature_set, display_features or []):
                    continue
                flabel = _feature_label(feature_set)
                if flabel not in group_map:
                    group_map[flabel] = {"feature_label": flabel, "feature_set": feature_set, "chart_entries": []}
                from app.analytics.chart_registry import get_chart_display_name
                group_map[flabel]["chart_entries"].append(
                    {
                        "chart_id": cid,
                        "chart_name": get_chart_display_name(cid, "zh_only"),
                        "severity": str(c.get("severity") or "info"),
                        "metric_snapshot": str(c.get("metric_snapshot") or ""),
                        "dimension_label": "",
                    }
                )
                break

    chip_groups = list(group_map.values())

    return {
        "chip_groups": chip_groups,
        "chart_status": chart_status,
    }
