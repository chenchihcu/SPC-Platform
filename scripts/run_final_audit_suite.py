#!/usr/bin/env python3
"""
Run the final SPC/SPI audit suite and emit a consolidated report.

This script combines:
- Baseline quality gates (ruff, mypy, pytest)
- Statistical and chart/feature interaction regression packs
- UI runtime contract checks
- Performance guard tests
- Qt-focused static policy audit
- Exception policy scans (broad/silent handlers)

Outputs are written to: Outputs/final_audit/<timestamp>/
"""
from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Gate:
    key: str
    phase: str
    command: list[str]
    timeout_sec: int = 1200
    required: bool = True


@dataclass
class GateResult:
    key: str
    phase: str
    command: str
    status: str
    return_code: int
    duration_sec: float
    log_file: str
    summary: str
    required: bool


@dataclass
class ExceptionFinding:
    file: str
    line: int
    kind: str


def _build_gates(profile: str, python_exe: str) -> list[Gate]:
    full = [
        Gate("ruff_all", "baseline", [python_exe, "-m", "ruff", "check", "."]),
        Gate("mypy_app", "baseline", [python_exe, "-m", "mypy", "app"]),
        Gate("pytest_full", "baseline", [python_exe, "-m", "pytest", "-q"], timeout_sec=2400),
        Gate(
            "pytest_statistics_pack",
            "statistical_correctness",
            [
                python_exe,
                "-m",
                "pytest",
                "-q",
                "tests/test_spc_engine.py",
                "tests/test_capability_engine.py",
                "tests/test_normality_engine.py",
                "tests/test_statistical_utils.py",
                "tests/test_anova_engine.py",
                "tests/test_summary_engine_defect_metrics.py",
                "tests/test_phase1_chart_consistency.py",
                "tests/test_phase2_normalization_policy.py",
            ],
        ),
        Gate(
            "pytest_chart_feature_pack",
            "chart_feature_cross",
            [
                python_exe,
                "-m",
                "pytest",
                "-q",
                "tests/test_feature_interaction_logic.py",
                "tests/test_chart_contract_alignment.py",
                "tests/test_chart_payload_parity_matrix.py",
                "tests/test_chart_output_matrix.py",
                "tests/test_chart_registry_acceptance.py",
                "tests/test_chart_render_registry.py",
                "tests/test_chart_selector_overrides.py",
                "tests/test_analysis_orchestrator.py",
            ],
        ),
        Gate(
            "pytest_release_validation_pack",
            "release_validation",
            [python_exe, "-m", "pytest", "-q", "tests/release_validation"],
            timeout_sec=2400,
        ),
        Gate(
            "pytest_ui_runtime_pack",
            "ui_runtime",
            [
                python_exe,
                "-m",
                "pytest",
                "-q",
                "tests/test_ui_runtime_diagnostics.py",
                "tests/test_ui_geometry_stability.py",
                "tests/test_control_panel_layout.py",
                "tests/test_data_setup_layout_tiers.py",
                "tests/test_chart_visual_readability.py",
            ],
        ),
        Gate(
            "pytest_performance_pack",
            "performance_baseline",
            [python_exe, "-m", "pytest", "-q", "tests/test_chart_performance_baseline.py"],
        ),
        Gate(
            "qt_policy_audit",
            "qt_policy",
            [python_exe, "scripts/qt_audit.py", "app"],
            required=False,
        ),
    ]

    quick = [
        Gate("ruff_all", "baseline", [python_exe, "-m", "ruff", "check", "."]),
        Gate("mypy_app", "baseline", [python_exe, "-m", "mypy", "app"]),
        full[3],
        full[4],
        full[5],
        full[7],
        full[8],
    ]
    return full if profile == "full" else quick


def _classify_nonzero_output(output: str) -> str:
    lowered = output.lower()
    unavailable_signals = (
        "no module named",
        "is not recognized as an internal or external command",
        "module not found",
        "command not found",
    )
    if any(sig in lowered for sig in unavailable_signals):
        return "not_available"
    return "fail"


def _tail_text(text: str, max_lines: int = 30) -> str:
    lines = text.splitlines()
    if not lines:
        return "(no output)"
    return "\n".join(lines[-max_lines:])


def _sanitize_log_name(value: str) -> str:
    safe = []
    for ch in value:
        if ch.isalnum() or ch in {"-", "_"}:
            safe.append(ch)
        else:
            safe.append("_")
    return "".join(safe).strip("_")


def _run_gate(gate: Gate, repo_root: Path, run_dir: Path) -> GateResult:
    log_name = f"{_sanitize_log_name(gate.phase)}__{_sanitize_log_name(gate.key)}.log"
    log_path = run_dir / log_name
    start = time.perf_counter()
    output = ""
    return_code = -1
    status = "fail"
    try:
        completed = subprocess.run(
            gate.command,
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=gate.timeout_sec,
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        return_code = completed.returncode
        status = "pass" if return_code == 0 else _classify_nonzero_output(output)
    except FileNotFoundError as exc:
        output = str(exc)
        status = "not_available"
    except subprocess.TimeoutExpired as exc:
        partial = ((exc.stdout or "") + (exc.stderr or "")).strip()
        output = f"timeout after {gate.timeout_sec}s\n{partial}"
        status = "fail"
    duration = time.perf_counter() - start
    log_path.write_text(output, encoding="utf-8", errors="replace")
    summary = "ok" if status == "pass" else _tail_text(output, max_lines=12)
    return GateResult(
        key=gate.key,
        phase=gate.phase,
        command=" ".join(gate.command),
        status=status,
        return_code=return_code,
        duration_sec=round(duration, 2),
        log_file=str(log_path),
        summary=summary,
        required=gate.required,
    )


def _is_exception_name(node: ast.expr | None, value: str) -> bool:
    return isinstance(node, ast.Name) and node.id == value


def _is_silent_handler(body: list[ast.stmt]) -> bool:
    if not body:
        return False
    for stmt in body:
        if isinstance(stmt, ast.Pass):
            continue
        if isinstance(stmt, ast.Continue):
            continue
        if isinstance(stmt, ast.Return) and stmt.value is None:
            continue
        if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Constant) and stmt.value.value is None:
            continue
        return False
    return True


def _scan_exception_policy(repo_root: Path) -> list[ExceptionFinding]:
    findings: list[ExceptionFinding] = []
    app_root = repo_root / "app"
    if not app_root.exists():
        return findings

    for path in sorted(app_root.rglob("*.py")):
        rel = str(path.relative_to(repo_root)).replace("\\", "/")
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
        except SyntaxError:
            findings.append(ExceptionFinding(file=rel, line=1, kind="syntax_error"))
            continue
        except OSError:
            findings.append(ExceptionFinding(file=rel, line=1, kind="read_error"))
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            line = getattr(node, "lineno", 1)
            is_bare = node.type is None
            is_broad = is_bare or _is_exception_name(node.type, "Exception")
            if is_broad:
                findings.append(ExceptionFinding(file=rel, line=line, kind="broad_exception"))
                if _is_silent_handler(node.body):
                    findings.append(ExceptionFinding(file=rel, line=line, kind="silent_exception"))
    return findings


def _summarize_exception_findings(findings: list[ExceptionFinding]) -> dict[str, Any]:
    by_kind: dict[str, int] = {}
    for item in findings:
        by_kind[item.kind] = by_kind.get(item.kind, 0) + 1
    return {
        "total": len(findings),
        "by_kind": by_kind,
    }


def _overall_status(results: list[GateResult], exception_total: int) -> str:
    # Strict final-audit gate: any non-pass gate or exception finding fails the run.
    if any(item.status != "pass" for item in results):
        return "fail"
    if exception_total > 0:
        return "fail"
    return "pass"


def _phase_skill_map() -> dict[str, list[str]]:
    return {
        "baseline": ["code-audit"],
        "statistical_correctness": ["spc-code-audit"],
        "chart_feature_cross": ["spc-chart-ui", "smt-spi-self-heal"],
        "release_validation": ["spc-chart-ui", "smt-spi-self-heal", "qa-auto-engineer"],
        "ui_runtime": ["playwright-interactive", "playwright"],
        "performance_baseline": ["spc-chart-ui", "smt-spi-self-heal"],
        "qt_policy": ["code-audit"],
        "static_scan": ["code-audit", "spc-code-audit"],
    }


def _write_markdown_report(
    path: Path,
    timestamp: str,
    profile: str,
    overall: str,
    gate_results: list[GateResult],
    exception_summary: dict[str, Any],
    exception_findings: list[ExceptionFinding],
    max_findings: int,
) -> None:
    lines: list[str] = []
    lines.append("# Final Audit Report")
    lines.append("")
    lines.append(f"- Timestamp: `{timestamp}`")
    lines.append(f"- Profile: `{profile}`")
    lines.append(f"- Overall: `{overall}`")
    lines.append("")
    lines.append("## Gate Results")
    lines.append("")
    lines.append("| Phase | Gate | Status | Required | Seconds | Log |")
    lines.append("|---|---|---|---|---:|---|")
    for item in gate_results:
        log_file = item.log_file.replace("\\", "/")
        lines.append(
            f"| {item.phase} | {item.key} | {item.status} | {str(item.required).lower()} | {item.duration_sec:.2f} | `{log_file}` |"
        )
    lines.append("")

    lines.append("## Exception Policy Scan (app/)")
    lines.append("")
    lines.append(f"- Total findings: `{exception_summary.get('total', 0)}`")
    by_kind = exception_summary.get("by_kind", {})
    if by_kind:
        for kind in sorted(by_kind):
            lines.append(f"- `{kind}`: `{by_kind[kind]}`")
    else:
        lines.append("- no findings")
    lines.append("")

    if exception_findings:
        lines.append(f"Top findings (max {max_findings}):")
        for item in exception_findings[:max_findings]:
            lines.append(f"- `{item.kind}` at `{item.file}:{item.line}`")
        lines.append("")

    lines.append("## Skill Loop Suggestions")
    lines.append("")
    phase_to_skills = _phase_skill_map()
    failed_or_blocked = [x for x in gate_results if x.status != "pass"]
    if not failed_or_blocked and exception_summary.get("total", 0) == 0:
        lines.append("- no remediation loop required")
    else:
        for item in failed_or_blocked:
            skills = ", ".join(phase_to_skills.get(item.phase, ["code-audit"]))
            lines.append(f"- `{item.phase}` -> {skills}")
        if exception_summary.get("total", 0) > 0:
            skills = ", ".join(phase_to_skills.get("static_scan", ["code-audit"]))
            lines.append(f"- `static_scan` -> {skills}")
    lines.append("")

    lines.append("## MCP Execution Matrix")
    lines.append("")
    lines.append("- `shell_command` + `filesystem`: deterministic gate execution, source scan, artifact persistence.")
    lines.append("- `playwright-interactive` / `playwright`: UI path replay for multi-feature real-time cross-analysis.")
    lines.append("- `web` + `openai_docs`: dependency and external contract verification when needed.")
    lines.append("- `database` + `chart`: optional structured evidence tables and trend visualization.")
    lines.append("- `figma`: optional UI contract parity checks for design-to-implementation drift.")
    lines.append("")
    lines.append("Reference: `docs/specs/final_audit_suite.md`")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def _write_deliverable_docs(
    *,
    repo_root: Path,
    timestamp: str,
    profile: str,
    overall: str,
    gate_results: list[GateResult],
    exception_summary: dict[str, Any],
    exception_findings: list[ExceptionFinding],
    report_path: Path,
    summary_path: Path,
) -> None:
    docs_dir = repo_root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    failed_gates = [item for item in gate_results if item.status != "pass"]
    exception_total = int(exception_summary.get("total", 0) or 0)
    by_kind = exception_summary.get("by_kind", {}) if isinstance(exception_summary, dict) else {}

    finding_by_file: dict[str, int] = {}
    for finding in exception_findings:
        key = finding.file
        finding_by_file[key] = finding_by_file.get(key, 0) + 1
    ranked_files = sorted(finding_by_file.items(), key=lambda x: (-x[1], x[0]))

    gate_table_lines = [
        "| Gate | Phase | Status | Return Code | Required |",
        "|---|---|---|---:|---|",
    ]
    for item in gate_results:
        gate_table_lines.append(
            f"| {item.key} | {item.phase} | {item.status} | {item.return_code} | {str(item.required).lower()} |"
        )

    failed_gate_lines = []
    for item in failed_gates:
        failed_gate_lines.append(f"- `{item.phase}:{item.key}` -> `{item.status}`")
        failed_gate_lines.append(f"  - Root Cause (from gate output): `{item.summary}`")
        failed_gate_lines.append("  - Fix: apply minimal scoped patch, then rerun full audit suite.")
    if not failed_gate_lines:
        failed_gate_lines.append("- None")

    exception_file_lines = [f"- `{file}`: `{count}` finding(s)" for file, count in ranked_files[:30]]
    if not exception_file_lines:
        exception_file_lines = ["- None"]

    rerun_commands = [
        "python -m ruff check .",
        "python -m mypy app",
        "python -m pytest -q",
        "python scripts/run_final_audit_suite.py --repo-root . --profile full",
    ]
    rerun_lines = [f"- `{cmd}`" for cmd in rerun_commands]

    audit_report_lines = [
        "# AUDIT_REPORT",
        "",
        f"- Timestamp: `{timestamp}`",
        f"- Profile: `{profile}`",
        f"- Overall: `{overall}`",
        f"- Exception findings: `{exception_total}`",
        "",
        "## Gate Matrix",
        "",
        *gate_table_lines,
        "",
        "## Failed Gate",
        "",
        *failed_gate_lines,
        "",
        "## Root Cause",
        "",
        f"- Exception by kind: `{by_kind}`",
        *exception_file_lines,
        "",
        "## Fix",
        "",
        "- Keep statistical definitions aligned with `docs/governance/SPC_RULES.md`.",
        "- Keep chart/data-flow contract aligned with `docs/reports/chart_contract_audit.md` and `docs/specs/data_contract.md`.",
        "- Narrow exception handlers and preserve existing fallback/log behavior.",
        "",
        "## Rerun Evidence",
        "",
        f"- Summary JSON: `{summary_path.as_posix()}`",
        f"- Run report: `{report_path.as_posix()}`",
        "- Commands:",
        *rerun_lines,
        "",
    ]

    remediation_lines = [
        "# REMEDIATION_PLAN",
        "",
        "- Objective: drive audit to `overall=pass` with `exception_scan.summary.total=0`.",
        f"- Current overall: `{overall}`",
        "",
        "## Failed Gate",
        "",
        *failed_gate_lines,
        "",
        "## Root Cause",
        "",
        f"- Total exception findings: `{exception_total}`",
        "- Highest-impact modules (by finding count):",
        *exception_file_lines,
        "",
        "## Minimal Fix",
        "",
        "- Replace broad `except Exception` and bare `except:` with narrow exception classes per module risk.",
        "- Keep existing fallback return shape and logging message format.",
        "- Replace raw UI constants with token constants; add missing method docstrings for qt_policy checks.",
        "",
        "## Rerun Evidence",
        "",
        f"- Last run summary: `{summary_path.as_posix()}`",
        f"- Last run markdown: `{report_path.as_posix()}`",
        "",
    ]

    root_cause_lines = [
        "# ROOT_CAUSE_ANALYSIS",
        "",
        f"- Audit timestamp: `{timestamp}`",
        f"- Overall: `{overall}`",
        "",
        "## Failed Gate",
        "",
        *failed_gate_lines,
        "",
        "## Root Cause",
        "",
        "- Gate-level root cause is extracted from each gate tail output (see Failed Gate section).",
        "- Exception policy root cause is broad/implicit exception handling in analytics/report/UI paths.",
        "- Affected modules:",
        *exception_file_lines,
        "",
        "## Minimal Fix",
        "",
        "- Narrow exception classes to expected I/O/import/type/value/runtime errors by code path.",
        "- Preserve behavior compatibility by keeping fallback payloads and log emission unchanged.",
        "",
        "## Rerun Evidence",
        "",
        f"- `summary.json`: `{summary_path.as_posix()}`",
        f"- `report.md`: `{report_path.as_posix()}`",
        "",
    ]

    regression_lines = [
        "# REGRESSION_TEST_PLAN",
        "",
        f"- Timestamp: `{timestamp}`",
        "- Overall target: `pass`",
        "",
        "## Required Regression Tests",
        "",
        "- `tests/test_qt_audit_cli_stability.py`",
        "- `tests/test_exception_policy_guard.py`",
        "- `tests/test_final_audit_outputs.py`",
        "",
        "## Validation Commands",
        "",
        *rerun_lines,
        "",
        "## Failed Gate",
        "",
        *failed_gate_lines,
        "",
        "## Root Cause",
        "",
        f"- Exception summary: `{by_kind}`",
        "",
        "## Fix",
        "",
        "- Apply minimal patches only to failing modules, then rerun full suite.",
        "",
        "## Rerun Evidence",
        "",
        f"- Summary artifact: `{summary_path.as_posix()}`",
        f"- Markdown artifact: `{report_path.as_posix()}`",
        "",
    ]

    (docs_dir / "AUDIT_REPORT.md").write_text("\n".join(audit_report_lines), encoding="utf-8")
    (docs_dir / "REMEDIATION_PLAN.md").write_text("\n".join(remediation_lines), encoding="utf-8")
    (docs_dir / "ROOT_CAUSE_ANALYSIS.md").write_text("\n".join(root_cause_lines), encoding="utf-8")
    (docs_dir / "REGRESSION_TEST_PLAN.md").write_text("\n".join(regression_lines), encoding="utf-8")


def _to_json_compatible(results: list[GateResult]) -> list[dict[str, Any]]:
    data: list[dict[str, Any]] = []
    for item in results:
        data.append(
            {
                "key": item.key,
                "phase": item.phase,
                "status": item.status,
                "required": item.required,
                "return_code": item.return_code,
                "duration_sec": item.duration_sec,
                "command": item.command,
                "log_file": item.log_file,
                "summary": item.summary,
            }
        )
    return data


def _print_console_summary(
    overall: str,
    report_path: Path,
    summary_path: Path,
    gate_results: list[GateResult],
    exception_summary: dict[str, Any],
) -> None:
    print(f"FINAL_AUDIT: {overall}")
    for item in gate_results:
        print(f"[{item.phase}:{item.key}] {item.status} ({item.duration_sec:.2f}s)")
    print(f"EXCEPTION_SCAN: total={exception_summary.get('total', 0)} by_kind={exception_summary.get('by_kind', {})}")
    print(f"REPORT_MD: {report_path}")
    print(f"SUMMARY_JSON: {summary_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run final audit suite")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--output-root", default="Outputs/final_audit", help="Directory for audit artifacts")
    parser.add_argument("--profile", choices=("full", "quick"), default="full")
    parser.add_argument("--max-findings", type=int, default=40)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    if not repo_root.exists() or not repo_root.is_dir():
        print(f"Invalid repo root: {repo_root}", file=sys.stderr)
        return 2

    output_root = (repo_root / args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = output_root / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    gates = _build_gates(args.profile, sys.executable)
    results = [_run_gate(gate, repo_root, run_dir) for gate in gates]

    exception_findings = _scan_exception_policy(repo_root)
    exception_summary = _summarize_exception_findings(exception_findings)
    overall = _overall_status(results, int(exception_summary.get("total", 0) or 0))

    summary_payload = {
        "timestamp": timestamp,
        "profile": args.profile,
        "overall": overall,
        "gates": _to_json_compatible(results),
        "exception_scan": {
            "summary": exception_summary,
            "findings": [
                {"file": x.file, "line": x.line, "kind": x.kind}
                for x in exception_findings
            ],
        },
    }
    summary_path = run_dir / "summary.json"
    summary_path.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    report_path = run_dir / "report.md"
    _write_markdown_report(
        report_path,
        timestamp=timestamp,
        profile=args.profile,
        overall=overall,
        gate_results=results,
        exception_summary=exception_summary,
        exception_findings=exception_findings,
        max_findings=max(1, args.max_findings),
    )
    _write_deliverable_docs(
        repo_root=repo_root,
        timestamp=timestamp,
        profile=args.profile,
        overall=overall,
        gate_results=results,
        exception_summary=exception_summary,
        exception_findings=exception_findings,
        report_path=report_path,
        summary_path=summary_path,
    )

    _print_console_summary(overall, report_path, summary_path, results, exception_summary)
    return 0 if overall == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
