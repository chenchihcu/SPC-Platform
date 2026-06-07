#!/usr/bin/env python3
"""Validate Gate A-F governance alignment for release gating."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


V2_1 = "GLOBAL_PLAN_FRAMEWORK_V2_1.md"
V2_2 = "GLOBAL_PLAN_FRAMEWORK_V2_2.md"

CANONICAL_ENTRYPOINTS = (
    "README.md",
    "docs/README.md",
    ".cursor/plans/README.md",
    "docs/specs/issue_resolution_workflow.md",
    "docs/specs/project_architecture.md",
    "docs/governance/GLOBAL_AGENTS_8CLASS_TEMPLATE.md",
)

GATE_ROWS = (
    ("A", "Scope"),
    ("B", "Evidence"),
    ("C", "RCA"),
    ("D", "Blast Radius"),
    ("E", "Verify"),
    ("F", "Report"),
)


@dataclass(frozen=True)
class Finding:
    path: str
    message: str
    preflight: bool = False


def _read_required(repo: Path, rel_path: str, findings: list[Finding]) -> str:
    path = repo / rel_path
    if not path.is_file():
        findings.append(Finding(rel_path, "required governance file is missing", preflight=True))
        return ""
    return path.read_text(encoding="utf-8")


def _require(text: str, rel_path: str, needle: str, message: str, findings: list[Finding]) -> None:
    if needle not in text:
        findings.append(Finding(rel_path, message))


def _check_entrypoints(repo: Path, findings: list[Finding]) -> None:
    for rel_path in CANONICAL_ENTRYPOINTS:
        text = _read_required(repo, rel_path, findings)
        if not text:
            continue
        if V2_2 not in text:
            findings.append(Finding(rel_path, f"canonical entrypoint must reference {V2_2}"))
        if V2_1 in text:
            findings.append(Finding(rel_path, f"canonical entrypoint must not reference superseded {V2_1}"))


def _check_v2_frameworks(repo: Path, findings: list[Finding]) -> None:
    v2_1_path = "docs/governance/GLOBAL_PLAN_FRAMEWORK_V2_1.md"
    v2_1 = _read_required(repo, v2_1_path, findings)
    if v2_1:
        _require(v2_1, v2_1_path, "**Superseded**", "v2.1 must be marked as superseded", findings)
        _require(v2_1, v2_1_path, V2_2, "v2.1 superseded notice must point to v2.2", findings)

    v2_2_path = "docs/governance/GLOBAL_PLAN_FRAMEWORK_V2_2.md"
    v2_2 = _read_required(repo, v2_2_path, findings)
    if not v2_2:
        return
    for needle, message in (
        ("| Gate | Name | Pass Condition | On Fail |", "v2.2 must define Gate pass/fail table"),
        ("Pass Condition", "v2.2 must define pass conditions"),
        ("On Fail", "v2.2 must define fail consequences"),
        ("Any `Pass` without evidence", "v2.2 must reject evidence-free Pass results"),
    ):
        _require(v2_2, v2_2_path, needle, message, findings)
    for key, name in GATE_ROWS:
        _require(v2_2, v2_2_path, f"| {key} | {name} |", f"v2.2 missing Gate {key} {name} row", findings)


def _check_plan_template(repo: Path, findings: list[Finding]) -> None:
    rel_path = "docs/templates/PLAN.md"
    text = _read_required(repo, rel_path, findings)
    if not text:
        return
    for needle, message in (
        ("PLAN Template v2.2", "plan template must identify the current v2.2 contract"),
        ("### Gate A~F Enforcement Table", "plan template must include Gate A~F enforcement table"),
        ("Pass Condition", "plan template must include Gate pass conditions"),
        ("Required Evidence", "plan template must include Required Evidence"),
        ("On Fail Action", "plan template must include On Fail Action"),
        ("Any Gate A~F `Pass` without evidence => treated as `Fail`", "plan template must fail evidence-free Pass results"),
    ):
        _require(text, rel_path, needle, message, findings)
    for key, name in GATE_ROWS:
        _require(text, rel_path, f"| Gate {key} | {name} |", f"plan template missing Gate {key} {name} row", findings)


def _check_governance_copies(repo: Path, findings: list[Finding]) -> None:
    for rel_path in ("docs/governance/GLOBAL_AGENTS_8CLASS_TEMPLATE.md", "docs/governance/AGENTS.md"):
        text = _read_required(repo, rel_path, findings)
        if not text:
            continue
        for needle, message in (
            ("Pass Condition", "governance copy must include Gate pass conditions"),
            ("On Fail", "governance copy must include Gate fail consequences"),
            ("Any `Pass` without evidence", "governance copy must reject evidence-free Pass results"),
        ):
            _require(text, rel_path, needle, message, findings)
        for key, name in GATE_ROWS:
            _require(text, rel_path, f"Gate {key}", f"governance copy missing Gate {key} {name}", findings)


def check(repo: Path) -> list[Finding]:
    findings: list[Finding] = []
    _check_entrypoints(repo, findings)
    _check_v2_frameworks(repo, findings)
    _check_plan_template(repo, findings)
    _check_governance_copies(repo, findings)
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Gate A-F governance alignment.")
    parser.add_argument("--repo-root", default=".", help="Repository root directory")
    args = parser.parse_args()

    repo = Path(args.repo_root).resolve()
    if not repo.is_dir():
        print(f"[ERROR] repo root is not a directory: {repo}", file=sys.stderr)
        return 2

    findings = check(repo)
    if not findings:
        print("[PASS] Governance alignment checks passed.")
        return 0

    print("[FAIL] Governance alignment check failed:")
    for finding in findings:
        print(f"- {finding.path}: {finding.message}")
    return 2 if any(f.preflight for f in findings) else 1


if __name__ == "__main__":
    raise SystemExit(main())
