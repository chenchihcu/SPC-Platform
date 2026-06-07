"""
Process optimization suggestions: aggregates root cause hints and failure mode
recommended actions for UI or report. Read-only from payload.
"""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def get_optimization_suggestions(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Return list of actionable improvement steps from failure mode library.
    Each item: { source: "failure_mode", text: str, failure_mode_id: str, ... }.

    NOTE: Root-cause observation hints are intentionally NOT duplicated here;
    they are rendered separately via infer_root_cause_hints() in the report.
    """
    out: List[Dict[str, Any]] = []
    try:
        from app.analytics.root_cause_engine import infer_root_cause_hints
        from app.analytics.anomaly_classifier import classify_anomalies
        from app.analytics.failure_mode_library import get_failure_mode
        from app.analytics.ipc_reference_library import get_ipc_references_by_failure_mode

        for hint in infer_root_cause_hints(payload):
            text = hint.get("hint")
            if not text:
                continue
            out.append({
                "source": "root_cause",
                "text": text,
                "rule_id": hint.get("rule_id"),
                "confidence": hint.get("confidence"),
                "priority": hint.get("priority"),
                "ipc_refs": hint.get("ipc_refs", []),
                "evidence": hint.get("evidence", {}),
            })

        for a in classify_anomalies(payload):
            fid = a.get("suggested_failure_mode_id")
            if not fid:
                continue
            fm = get_failure_mode(fid)
            if not fm:
                continue
            for act in fm.get("recommended_actions", []):
                out.append({
                    "source": "failure_mode",
                    "text": act,
                    "failure_mode_id": fid,
                    "confidence": a.get("confidence"),
                    "priority": "high" if (a.get("confidence") or 0.0) >= 0.7 else "medium",
                    "ipc_refs": get_ipc_references_by_failure_mode(fid),
                    "evidence": {"indicators": a.get("indicators", [])},
                })
    except (ImportError, AttributeError, KeyError, TypeError, ValueError, RuntimeError) as e:
        logger.debug("建議措施彙總失敗，建議清單將不包含此段: %s", e)
    return out
