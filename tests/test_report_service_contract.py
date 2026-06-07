from app.services.report_service import ReportService


def test_report_service_exposes_pptx_only_export_contract() -> None:
    svc = ReportService()
    assert hasattr(svc, "generate_pptx_report")
    assert not hasattr(svc, "generate_report_with_charts")
    assert not hasattr(svc, "generate_comprehensive_report")
