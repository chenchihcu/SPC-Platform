"""Master-data parity audit script smoke test."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    repo = Path(__file__).resolve().parents[1]
    path = repo / "scripts" / "master_data_parity_audit.py"
    spec = importlib.util.spec_from_file_location("_master_data_parity_audit_under_test", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_master_data_parity_audit_builds_structured_report() -> None:
    repo = Path(__file__).resolve().parents[1]
    mod = _load_module()
    report = mod.build_parity_report(repo)

    assert "summary" in report
    summary = report["summary"]
    assert "total_mismatch_count" in summary
    assert "coordinate_mismatch_count" in summary
    assert "spec_mismatch_count" in summary
    assert "assignment_mismatch_count" in summary
    assert "coordinate" in report
    assert "spec" in report
    assert "assignment" in report
