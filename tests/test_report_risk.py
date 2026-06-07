from app.services.report_risk import (
    build_risk_assessment,
    compute_risk_level,
    normalize_pptx_severity,
    normalize_process_verdict,
    risk_level_display,
    summarize_risk_signals,
)


def test_normalize_pptx_severity_aliases() -> None:
    assert normalize_pptx_severity("HIGH") == "error"
    assert normalize_pptx_severity("warn") == "warning"
    assert normalize_pptx_severity("unknown", priority="medium") == "warning"


def test_summarize_risk_signals_prefers_diagnostics() -> None:
    hints = [{"severity": "error"}, {"severity": "warning"}]
    diagnostics = [{"severity": "warning"}]
    summary = summarize_risk_signals(hints=hints, diagnostics=diagnostics)
    assert summary["error_count"] == 0
    assert summary["warning_count"] == 1
    assert summary["total_count"] == 1


def test_summarize_risk_signals_counts_high_priority_in_diagnostics() -> None:
    summary = summarize_risk_signals(
        diagnostics=[
            {"severity": "warning", "priority": "high"},
            {"severity": "info", "priority": "high"},
        ]
    )
    assert summary["high_priority_count"] == 2


def test_compute_risk_level_honors_process_floor() -> None:
    level = compute_risk_level([], process={"verdict": "不可接受"}, diagnostics=[])
    assert level == "HIGH"
    assert normalize_process_verdict("可接受") == "ACCEPTABLE"
    assert risk_level_display("MEDIUM") == "中風險 (Medium)"


def test_compute_risk_level_uses_diagnostic_priority_escalation() -> None:
    level = compute_risk_level(
        [],
        process={"verdict": "可接受"},
        diagnostics=[
            {"severity": "info", "priority": "high"},
            {"severity": "info", "priority": "high"},
        ],
    )
    assert level == "HIGH"


def test_build_risk_assessment_returns_unified_snapshot() -> None:
    assessment = build_risk_assessment(
        process={"verdict": "待改善"},
        diagnostics=[{"severity": "warning", "priority": "high"}],
    )
    assert assessment["level"] == "MEDIUM"
    assert assessment["level_display"] == "中風險 (Medium)"
    assert assessment["warning_count"] == 1
    assert assessment["high_priority_count"] == 1
    assert assessment["verdict"] == "待改善"
