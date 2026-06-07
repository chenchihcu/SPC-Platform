from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


_RULE_FAILURE_MODE_MAP: Dict[str, List[str]] = {
    "volume_decline_along_board": ["paste_drying"],
    "edge_spatial_cluster": ["printer_alignment_shift", "spatial_oos"],
    "footprint_variance_imbalance": ["aperture_mismatch"],
    "consistent_volume_high": ["squeegee_pressure"],
    "consistent_volume_low": ["squeegee_pressure"],
    "cusum_trend_drift": ["instability"],
    "cusum_local_shift": ["instability"],
    "localized_deviation_bias": ["localized_stencil_wear", "squeegee_pressure"],
    "cpk_below_threshold": ["instability", "squeegee_pressure"],
    "normality_test_fail": ["instability"],
    "high_cv": ["instability"],
}


def collect_pptx_actions(
    payload: Dict[str, Any],
    *,
    rule_id: Optional[str] = None,
    limit: int = 3,
) -> List[str]:
    """Collect deduplicated, action-oriented suggestions for one diagnostic slide."""
    actions: List[str] = []
    seen: set[str] = set()

    if rule_id:
        try:
            from app.analytics.failure_mode_library import get_failure_mode

            for failure_mode_id in _RULE_FAILURE_MODE_MAP.get(rule_id, []):
                failure_mode = get_failure_mode(failure_mode_id)
                if not failure_mode:
                    continue
                for text in failure_mode.get("recommended_actions", []):
                    action_text = str(text).strip()
                    if not action_text or action_text in seen:
                        continue
                    actions.append(action_text)
                    seen.add(action_text)
                    if len(actions) >= limit:
                        return actions
        except ImportError as exc:
            logger.warning(
                "collect_pptx_actions: failure_mode_library unavailable; using fallback suggestions. rule_id=%s error=%s",
                rule_id,
                exc,
            )

    try:
        from app.analytics.optimization_suggestions import get_optimization_suggestions
    except ImportError:
        return actions

    for item in get_optimization_suggestions(payload):
        if item.get("source") != "failure_mode":
            continue
        text = str(item.get("text", "")).strip()
        if not text or text in seen:
            continue
        actions.append(text)
        seen.add(text)
        if len(actions) >= limit:
            break
    return actions
