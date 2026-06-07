"""Build validation_report.json from pytest JUnit XML and repository metadata."""

from __future__ import annotations

import json
import logging
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validation.report_schema import REPORT_SCHEMA_VERSION

logger = logging.getLogger(__name__)

# Ordered rules: first matching prefix wins (classname + function name blob).
_SECTION_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("non_computable_validation", ("test_non_computable",)),
    ("deterministic_validation", ("test_determinism",)),
    ("feature_switch_validation", ("test_feature_switch",)),
    (
        "dataset_validation",
        (
            "test_join_conservation",
            "test_data_contract_golden",
            "test_manifest_release",
            "test_no_coords",
        ),
    ),
    ("spec_validation", ("test_partial_spec", "test_spec_stencil")),
    ("chart_validation", ("test_resolve_chart_payload", "test_chart_transparency")),
    ("report_validation", ("test_report_pptx",)),
    ("kpi_validation", ("test_dashboard_layers", "test_analysis_payload")),
)

# Substrings that indicate a test "belongs" in statistical bucket by convention (for unmapped count).
_STATISTICAL_KNOWN_PREFIXES: tuple[str, ...] = (
    "test_phase1_infrastructure",
    "test_spc_rules",
    "test_step4_tolerance",
    "test_three_feature",
    "test_cache_state",
    "test_performance_regression",
)

SECTION_IDS: tuple[str, ...] = (
    "dataset_validation",
    "statistical_validation",
    "spec_validation",
    "kpi_validation",
    "chart_validation",
    "report_validation",
    "feature_switch_validation",
    "non_computable_validation",
    "deterministic_validation",
)


@dataclass(frozen=True)
class ParsedCase:
    classname: str
    name: str
    time_sec: float | None
    outcome: str  # passed | failed | error | skipped
    message: str | None


def _case_blob(classname: str, name: str) -> str:
    return f"{classname}.{name}"


def section_for_case(classname: str, name: str) -> str:
    """Map JUnit case to validation section; unmatched → statistical_validation."""
    blob = _case_blob(classname, name)
    for section, prefixes in _SECTION_RULES:
        if any(p in blob for p in prefixes):
            return section
    return "statistical_validation"


def _is_known_statistical_blob(blob: str) -> bool:
    return any(p in blob for p in _STATISTICAL_KNOWN_PREFIXES)


def summarize_sections(cases: list[ParsedCase]) -> tuple[dict[str, Any], dict[str, Any], int]:
    """
    Build nine section objects and final_result; return (sections_dict, final_result, unmapped_tests_count).

    Sections dict keys follow SECTION_IDS order in output (caller may reorder).
    """
    by_section: dict[str, list[ParsedCase]] = {sid: [] for sid in SECTION_IDS}
    unmapped = 0

    for c in cases:
        sid = section_for_case(c.classname, c.name)
        by_section[sid].append(c)
        if sid == "statistical_validation":
            blob = _case_blob(c.classname, c.name)
            if not _is_known_statistical_blob(blob):
                unmapped += 1

    sections_out: dict[str, Any] = {}
    for sid in SECTION_IDS:
        scases = by_section[sid]
        tests_run = len(scases)
        n_failed = sum(1 for x in scases if x.outcome == "failed")
        n_errors = sum(1 for x in scases if x.outcome == "error")
        n_skipped = sum(1 for x in scases if x.outcome == "skipped")
        failed_nodeids: list[str] = []
        for x in scases:
            if x.outcome in ("failed", "error"):
                failed_nodeids.append(_node_id(x.classname, x.name))
        bad = n_failed + n_errors
        status = "PASS" if bad == 0 else "FAIL"
        sections_out[sid] = {
            "status": status,
            "tests_run": tests_run,
            "failed": n_failed,
            "errors": n_errors,
            "skipped": n_skipped,
            "failed_nodeids": failed_nodeids,
        }

    all_pass = all(sections_out[sid]["status"] == "PASS" for sid in SECTION_IDS)
    final_result = {
        "status": "PASS" if all_pass else "FAIL",
        "release_allowed": all_pass,
    }
    return sections_out, final_result, unmapped


def _parse_junit_xml(path: Path) -> tuple[list[ParsedCase], dict[str, int]]:
    root = ET.parse(path).getroot()
    cases: list[ParsedCase] = []
    counts = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}

    suites = root.findall("testsuite") if root.tag == "testsuites" else [root]

    for suite in suites:
        for case in suite.findall("testcase"):
            counts["tests"] += 1
            classname = case.get("classname") or ""
            name = case.get("name") or ""
            t_raw = case.get("time")
            time_sec = float(t_raw) if t_raw is not None else None
            msg = None
            outcome = "passed"
            fail_el = case.find("failure")
            if fail_el is not None:
                outcome = "failed"
                counts["failures"] += 1
                msg = (fail_el.get("message") or fail_el.text or "").strip() or "failure"
            else:
                err_el = case.find("error")
                if err_el is not None:
                    outcome = "error"
                    counts["errors"] += 1
                    msg = (err_el.get("message") or err_el.text or "").strip() or "error"
                elif case.find("skipped") is not None:
                    outcome = "skipped"
                    counts["skipped"] += 1
            cases.append(
                ParsedCase(
                    classname=classname,
                    name=name,
                    time_sec=time_sec,
                    outcome=outcome,
                    message=msg,
                )
            )
    return cases, counts


def _node_id(classname: str, name: str) -> str:
    if classname and name:
        return f"{classname}::{name}"
    return name or classname or "unknown"


def build_report(
    *,
    repo_root: Path,
    junit_path: Path,
    pytest_exit_code: int,
    golden_profile: str,
    extra_pytest_args: list[str] | None = None,
) -> dict[str, Any]:
    cases, junit_counts = _parse_junit_xml(junit_path)

    golden_env = os.environ.get("GOLDEN_DATASET_ROOT", "").strip()
    if golden_env:
        golden_root = Path(golden_env).expanduser().resolve()
    else:
        golden_root = (repo_root / "golden_dataset").resolve()

    tolerance_path = golden_root / "golden_tolerance.json"
    manifest_path = golden_root / "normal_baseline" / "expected" / "manifest.json"
    dataset_version = ""
    try:
        manifest_doc = json.loads(manifest_path.read_text(encoding="utf-8"))
        dataset_version = str(manifest_doc.get("dataset_version") or "")
    except (OSError, json.JSONDecodeError, TypeError):
        logger.warning("Failed to load dataset manifest: %s", manifest_path, exc_info=True)

    sections_flat, final_result, unmapped_count = summarize_sections(cases)

    tests_out: list[dict[str, Any]] = []
    failed_tests: list[dict[str, Any]] = []
    for c in cases:
        nid = _node_id(c.classname, c.name)
        sec = section_for_case(c.classname, c.name)
        entry = {
            "nodeid": nid,
            "outcome": c.outcome,
            "duration_sec": c.time_sec,
            "message": c.message,
            "section": sec,
        }
        tests_out.append(entry)
        if c.outcome in ("failed", "error"):
            failed_tests.append({"nodeid": nid, "outcome": c.outcome, "message": c.message})

    pytest_ok = pytest_exit_code == 0
    section_ok = bool(final_result.get("release_allowed"))
    release_allowed = pytest_ok and section_ok
    final_result = {
        "status": "PASS" if release_allowed else "FAIL",
        "release_allowed": release_allowed,
    }

    overall = "PASS" if release_allowed else "FAIL"

    # Top-level keys: metadata, then sections in spec order, then diagnostics.
    report_doc: dict[str, Any] = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository_root": str(repo_root.resolve()),
        "golden_profile": golden_profile,
        "dataset_version": dataset_version,
        "golden_dataset_root": str(golden_root),
        "tolerance_policy_path": str(tolerance_path) if tolerance_path.is_file() else None,
        "pytest_exit_code": pytest_exit_code,
        "overall_status": overall,
        "junit_summary": junit_counts,
        "pytest_extra_args": list(extra_pytest_args or []),
        "unmapped_tests_count": unmapped_count,
        "tolerance_comparison_note": "Per-test numeric tolerances use golden_dataset/golden_tolerance.json via tests/release_validation/helpers/tolerance.py",
    }

    for sid in SECTION_IDS:
        report_doc[sid] = sections_flat[sid]

    report_doc["final_result"] = final_result
    report_doc["tests"] = tests_out
    report_doc["failed_tests"] = failed_tests

    return report_doc


def write_report(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
