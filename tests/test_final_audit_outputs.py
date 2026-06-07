from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _load_final_audit_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "run_final_audit_suite.py"
    spec = importlib.util.spec_from_file_location("run_final_audit_suite", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load run_final_audit_suite module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _gate_result(module: ModuleType, *, key: str, phase: str, status: str, required: bool = True):
    return module.GateResult(
        key=key,
        phase=phase,
        command=f"python -m {key}",
        status=status,
        return_code=0 if status == "pass" else 1,
        duration_sec=1.23,
        log_file=f"Outputs/final_audit/mock/{key}.log",
        summary="ok" if status == "pass" else "mock failure",
        required=required,
    )


def test_overall_status_is_strict() -> None:
    module = _load_final_audit_module()
    pass_gate = _gate_result(module, key="ruff_all", phase="baseline", status="pass")
    fail_gate = _gate_result(module, key="pytest_full", phase="baseline", status="fail")
    na_gate = _gate_result(module, key="qt_policy_audit", phase="qt_policy", status="not_available", required=False)

    assert module._overall_status([pass_gate], 0) == "pass"
    assert module._overall_status([fail_gate], 0) == "fail"
    assert module._overall_status([na_gate], 0) == "fail"
    assert module._overall_status([pass_gate], 1) == "fail"


def test_deliverable_docs_are_generated(tmp_path: Path) -> None:
    module = _load_final_audit_module()
    report_path = tmp_path / "Outputs" / "final_audit" / "mock" / "report.md"
    summary_path = tmp_path / "Outputs" / "final_audit" / "mock" / "summary.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("# mock report\n", encoding="utf-8")
    summary_path.write_text('{"overall": "fail"}\n', encoding="utf-8")

    gates = [
        _gate_result(module, key="ruff_all", phase="baseline", status="pass"),
        _gate_result(module, key="qt_policy_audit", phase="qt_policy", status="fail", required=False),
    ]
    findings = [
        module.ExceptionFinding(file="app/services/report_service.py", line=474, kind="broad_exception"),
        module.ExceptionFinding(file="app/services/report_service.py", line=498, kind="broad_exception"),
    ]
    summary = module._summarize_exception_findings(findings)

    module._write_deliverable_docs(
        repo_root=tmp_path,
        timestamp="20260403_120000",
        profile="full",
        overall="fail",
        gate_results=gates,
        exception_summary=summary,
        exception_findings=findings,
        report_path=report_path,
        summary_path=summary_path,
    )

    targets = [
        tmp_path / "docs" / "AUDIT_REPORT.md",
        tmp_path / "docs" / "REMEDIATION_PLAN.md",
        tmp_path / "docs" / "ROOT_CAUSE_ANALYSIS.md",
        tmp_path / "docs" / "REGRESSION_TEST_PLAN.md",
    ]
    for path in targets:
        assert path.exists(), f"missing deliverable: {path}"
        text = path.read_text(encoding="utf-8")
        assert "Failed Gate" in text
        assert "Root Cause" in text
        assert "Fix" in text
        assert "Rerun Evidence" in text
