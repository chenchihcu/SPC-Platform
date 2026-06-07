"""Attach statistical_signals, diagnosis_engine, process_risk, knowledge_inference to analysis payload."""

from __future__ import annotations

from typing import Any, Dict

from app.analytics.diagnosis_engine import build_diagnosis_engine
from app.analytics.statistical_signals import build_statistical_signals
from app.services.diagnostic_evidence_matrix import build_diagnostic_evidence_matrix
from app.services.knowledge_inference_engine import run_knowledge_inference
from app.services.process_risk_model import compute_process_risk


def enrich_analysis_payload(payload: Dict[str, Any]) -> None:
    """
    Mutate payload in place: unified diagnosis contract for UI and reports.

    Safe to call when ``payload['summary']`` exists (all successful compute_analysis_payload paths).
    """
    if not isinstance(payload, dict):
        return
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        return
    process = summary.setdefault("process", {})
    if not isinstance(process, dict):
        return

    signals = build_statistical_signals(payload)
    payload["statistical_signals"] = signals

    diagnosis = build_diagnosis_engine(signals, summary)
    process["diagnosis_engine"] = diagnosis

    pr = compute_process_risk(signals, diagnosis)
    process["process_risk"] = pr

    payload["knowledge_inference"] = run_knowledge_inference(signals, diagnosis, summary)

    matrix = build_diagnostic_evidence_matrix(payload)
    payload["diagnostic_evidence_matrix"] = matrix
