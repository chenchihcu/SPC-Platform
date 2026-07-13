"""Gate A-F governance alignment is part of the release gate."""

from __future__ import annotations

from pathlib import Path

from scripts.check_governance_alignment import check


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_governance_alignment_check_passes() -> None:
    """Validate Gate A-F governance alignment by importing check() directly.

    Avoids ``subprocess.run(capture_output=True)`` which triggers
    ``DuplicateHandle`` → ``WinError 50`` on certain Windows environments
    (the underlying ``check()`` function is safe to call in-process).
    """
    findings = check(_repo_root())
    assert not findings, _findings_message(findings)


def _findings_message(findings: list) -> str:
    lines = ["[FAIL] Governance alignment check failed:"]
    for f in findings:
        lines.append(f"  - {f.path}: {f.message}")
    return "\n".join(lines)
