from app.services.report_exec_summary import build_executive_summary_html


def test_build_executive_summary_html_renders_medium_risk_badge() -> None:
    html = build_executive_summary_html(
        hints=[],
        ro_payload={},
        summary_data={"process": {"verdict": "可接受"}},
        total_n=120,
        batch_qty=20,
        diagnostics=[{"severity": "warning"}],
        compute_risk_level_fn=lambda *_args, **_kwargs: "MEDIUM",
    )
    assert "MEDIUM 中風險" in html


def test_build_executive_summary_html_links_repeated_offender_anchor() -> None:
    html = build_executive_summary_html(
        hints=[],
        ro_payload={"metadata": {"is_valid": True}, "data": {"labels": ["R1"], "counts": [5]}},
        summary_data={"process": {}},
        total_n=10,
        batch_qty=1,
        primary_feature="Volume",
        compute_risk_level_fn=lambda *_args, **_kwargs: "LOW",
    )
    assert "#ro-volume" in html


def test_build_executive_summary_html_prefers_risk_assessment_level() -> None:
    html = build_executive_summary_html(
        hints=[],
        ro_payload={},
        summary_data={"process": {"verdict": "可接受"}},
        total_n=10,
        batch_qty=1,
        diagnostics=[],
        risk_assessment={"level": "HIGH"},
        compute_risk_level_fn=lambda *_args, **_kwargs: "LOW",
    )
    assert "HIGH 高風險" in html


def test_build_executive_summary_html_includes_decision_narrative_block() -> None:
    html = build_executive_summary_html(
        hints=[],
        ro_payload={},
        summary_data={"process": {"verdict": "可接受"}},
        total_n=10,
        batch_qty=1,
        diagnostics=[],
        risk_assessment={"level": "LOW"},
        decision_narrative={
            "core_diagnosis_zh": "範圍【Global】；型態【漂移】。",
            "risk_paragraph_zh": "製程風險等級：LOW。測試理由。",
            "action_hint_zh": "先檢查鋼板與刮刀。",
        },
        compute_risk_level_fn=lambda *_args, **_kwargs: "LOW",
    )
    assert "製程語言摘要" in html
    assert "核心診斷" in html and "範圍【Global】" in html
    assert "風險研判" in html and "LOW" in html
    assert "行動提示" in html and "鋼板" in html


def test_build_executive_summary_html_includes_dual_workorder_kpi() -> None:
    html = build_executive_summary_html(
        hints=[],
        ro_payload={},
        summary_data={"process": {"verdict": "可接受"}},
        total_n=10,
        batch_qty=20,
        supplier_work_order_no="SUP-WO-01",
        outsource_work_order_no="OUT-WO-88",
        diagnostics=[],
        risk_assessment={"level": "LOW"},
        compute_risk_level_fn=lambda *_args, **_kwargs: "LOW",
    )
    assert "供應商製令工單" in html
    assert "醫電製令工單" in html
    assert "SUP-WO-01" in html
    assert "OUT-WO-88" in html


def test_build_executive_summary_html_tolerates_non_numeric_process_kpis() -> None:
    html = build_executive_summary_html(
        hints=[],
        ro_payload={},
        summary_data={
            "process": {
                "verdict": "可接受",
                "min_cpk": "N/A",
                "overall_yield_pct": "unknown",
            }
        },
        total_n=10,
        batch_qty=1,
        diagnostics=[],
        risk_assessment={"level": "LOW"},
        compute_risk_level_fn=lambda *_args, **_kwargs: "LOW",
    )
    assert "最低 Cpk" in html and "—" in html
    assert "整體良率" in html and "—" in html
