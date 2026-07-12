from __future__ import annotations

from typing import Any, Dict, List


def format_pptx_evidence_lines(evidence: Dict[str, Any], limit: int = 4) -> List[str]:
    """Convert structured evidence into concise display lines for PPTX slides."""
    if not isinstance(evidence, dict) or not evidence:
        return []
    label_map = {
        "cp": "Cp",
        "cpk": "Cpk",
        "cv": "CV",
        "decline_ratio": "Decline Ratio",
        "dominant_share": "Dominant Share",
        "edge_oos_ratio": "Edge OOS Ratio",
        "mean": "Mean",
        "mean_target_ratio": "Mean/Target",
        "ooc_count": "OOC Count",
        "ooc_ratio": "OOC Ratio",
        "p_value": "p-value",
        "sample_n": "Sample N",
        "sigma_st": "Sigma (ST)",
        "threshold": "Threshold",
        "total_n": "Total N",
        "variance_ratio": "Variance Ratio",
    }
    percent_ratio_keys = {
        "decline_ratio",
        "dominant_share",
        "edge_oos_ratio",
        "mean_target_ratio",
        "ooc_ratio",
    }
    times_ratio_keys = {"variance_ratio"}
    lines: List[str] = []
    for key, value in evidence.items():
        if value is None:
            continue
        label = label_map.get(key, key.replace("_", " ").title())
        if isinstance(value, float):
            if key in percent_ratio_keys or key in {"cv"}:
                value_text = f"{value:.1%}"
            elif key in times_ratio_keys:
                value_text = f"{value:.2f}x"
            else:
                value_text = f"{value:.3f}"
        else:
            value_text = str(value)
        lines.append(f"{label}: {value_text}")
        if len(lines) >= limit:
            break
    return lines


def format_pptx_ipc_lines(ipc_refs: Any, limit: int = 2) -> List[str]:
    """Convert IPC reference metadata into compact text lines."""
    if not isinstance(ipc_refs, list):
        return []
    out: List[str] = []
    for ref in ipc_refs:
        if not isinstance(ref, dict):
            continue
        std = str(ref.get("std", "")).strip()
        clause = str(ref.get("clause", "")).strip()
        summary_zh = str(ref.get("summary_zh", "")).strip()
        text = " ".join(part for part in (f"[{std}]" if std else "", clause, summary_zh) if part)
        if text:
            out.append(text)
        if len(out) >= limit:
            break
    return out

