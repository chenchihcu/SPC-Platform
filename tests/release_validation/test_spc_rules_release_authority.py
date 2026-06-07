"""D: docs/governance/SPC_RULES.md remains the statistical authority artifact (release gate)."""

from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_spc_rules_authority_file_present_and_substantive() -> None:
    path = _repo_root() / "docs" / "governance" / "SPC_RULES.md"
    assert path.is_file(), f"missing authority spec: {path}"
    text = path.read_text(encoding="utf-8")
    assert len(text) >= 5000, "docs/governance/SPC_RULES.md unexpectedly small; confirm governance copy is intact"
    # Escaped-heading style in repo copy uses backslash before '#'
    assert "\\# 7. Cp" in text or "# 7. Cp" in text, "expected Cp capability section heading"
    assert "I-MR" in text, "expected I-MR control-chart taxonomy"
    assert "Capability metrics" in text or "capability" in text.lower(), "expected capability narrative"


def test_spec_maintenance_doc_references_spc_rules() -> None:
    path = _repo_root() / "docs" / "specs" / "spec_maintenance_and_alignment.md"
    assert path.is_file(), f"missing: {path}"
    body = path.read_text(encoding="utf-8")
    assert "SPC_RULES" in body, "maintenance spec should name SPC_RULES authority"
