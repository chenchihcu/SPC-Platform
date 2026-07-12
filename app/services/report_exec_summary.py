from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional


def _try_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_executive_summary_pptx_data(
    summary_data: Dict[str, Any],
    diagnostics: Optional[List[Dict[str, Any]]] = None,
    risk_assessment: Optional[Dict[str, Any]] = None,
    *,
    generate_one_liner_fn: Callable[..., str],
    generate_risk_sentence_fn: Callable[..., str],
    derive_stability_verdict_fn: Callable[..., tuple],
    requires_immediate_action_fn: Callable[..., bool],
    anomaly_type_label_fn: Callable[[str], str],
    derive_process_state_fn: Optional[Callable[..., str]] = None,
    derive_problem_type_fn: Optional[Callable[..., str]] = None,
    problem_type_zh_fn: Optional[Callable[[str], str]] = None,
    generate_spi_narrative_fn: Optional[Callable[..., str]] = None,
    decision_narrative: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Compute structured data for the PPTX Executive Summary slide.

    Returns a dict with keys used directly by _build_slide_executive_summary()
    and _build_slide_core_diagnosis() in pptx_report_builder.
    """
    process = summary_data.get("process", {}) if isinstance(summary_data, dict) else {}
    diags = diagnostics if isinstance(diagnostics, list) else []
    ra = risk_assessment if isinstance(risk_assessment, dict) else {}

    verdict = str(process.get("verdict", "—") or "—")
    risk_level = str(ra.get("level", "LOW") or "LOW").upper()
    risk_display = str(ra.get("level_display", risk_level) or risk_level)
    error_count = int(ra.get("error_count", 0) or 0)

    stability_verdict, drift_feature, ooc_ratio = derive_stability_verdict_fn(diags)

    # Normality: check evidence_lines for "Is Normal: False"
    normality_passed = True
    for diag in diags:
        rule_id = str(diag.get("rule_id", "") or "").lower()
        if "normal" in rule_id:
            for ev_line in (diag.get("evidence_lines") or []):
                if "false" in str(ev_line).lower() and "normal" in str(ev_line).lower():
                    normality_passed = False
                    break
        if not normality_passed:
            break

    # Primary anomaly
    primary_diag = diags[0] if diags else {}
    primary_feature = str(
        primary_diag.get("feature_label", "")
        or drift_feature
        or ""
    ).strip()
    primary_rule_id = str(primary_diag.get("rule_id", "") or "").lower()
    anomaly_type = anomaly_type_label_fn(primary_rule_id)

    one_liner = generate_one_liner_fn(
        verdict=verdict,
        risk_level=risk_level,
        stability_verdict=stability_verdict,
        primary_feature=primary_feature,
        primary_rule_id=primary_rule_id,
    )

    risk_sentence = generate_risk_sentence_fn(
        verdict=verdict,
        risk_level=risk_level,
        stability_verdict=stability_verdict,
        normality_passed=normality_passed,
        primary_feature=primary_feature,
    )

    needs_action = requires_immediate_action_fn(
        risk_level=risk_level,
        stability_verdict=stability_verdict,
        error_count=error_count,
    )

    # Priority check directions: top 3 deduplicated actions from leading diagnostics
    check_dirs: List[str] = []
    seen_dirs: set = set()
    for diag in diags[:3]:
        for action in (diag.get("recommended_actions") or [])[:2]:
            text = str(action or "").strip()
            if text and text not in seen_dirs:
                check_dirs.append(text)
                seen_dirs.add(text)
            if len(check_dirs) >= 3:
                break
        if len(check_dirs) >= 3:
            break

    # Min Cpk string
    min_cpk_raw = _try_float(process.get("min_cpk"))
    min_cpk_measure = str(process.get("min_cpk_measure", "") or "").strip()
    if min_cpk_raw is not None:
        min_cpk_str = (
            f"{min_cpk_measure} / Cpk={min_cpk_raw:.3f}"
            if min_cpk_measure
            else f"Cpk={min_cpk_raw:.3f}"
        )
    else:
        min_cpk_str = "—"

    # ── SMT SPI process state & problem type (new fields) ───────────────────
    process_state = "穩定"
    if derive_process_state_fn is not None:
        process_state = derive_process_state_fn(
            diags, stability_verdict=stability_verdict
        )

    problem_type = "Unknown"
    if derive_problem_type_fn is not None:
        problem_type = derive_problem_type_fn(diags)

    problem_type_label = problem_type_zh_fn(problem_type) if problem_type_zh_fn else problem_type

    spi_narrative = ""
    if generate_spi_narrative_fn is not None:
        spi_narrative = generate_spi_narrative_fn(
            process_state=process_state,
            problem_type=problem_type,
            primary_feature=primary_feature,
            risk_level=risk_level,
            ooc_ratio=ooc_ratio,
        )

    dn = decision_narrative if isinstance(decision_narrative, dict) else {}
    core_dn = str(dn.get("core_diagnosis_zh") or "").strip()
    if core_dn:
        spi_narrative = f"{core_dn}\n\n{spi_narrative}".strip() if spi_narrative else core_dn
    risk_dn = str(dn.get("risk_paragraph_zh") or "").strip()
    if risk_dn:
        risk_sentence = risk_dn
    action_dn = str(dn.get("action_hint_zh") or "").strip()
    if action_dn:
        check_dirs.insert(0, action_dn[:280])

    return {
        "one_liner": one_liner,
        "verdict": verdict,
        "risk_level": risk_level,
        "risk_display": risk_display,
        "requires_action": needs_action,
        "primary_feature": primary_feature,
        "anomaly_type": anomaly_type,
        "stability_verdict": stability_verdict,
        "ooc_ratio": ooc_ratio,
        "risk_sentence": risk_sentence,
        "check_directions": check_dirs,
        "min_cpk_str": min_cpk_str,
        "min_cpk_value": min_cpk_raw,
        "normality_passed": normality_passed,
        "error_count": error_count,
        "warning_count": int(ra.get("warning_count", 0) or 0),
        # SMT SPI specific
        "process_state": process_state,
        "problem_type": problem_type,
        "problem_type_label": problem_type_label,
        "spi_narrative": spi_narrative,
    }
