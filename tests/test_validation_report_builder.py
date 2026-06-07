"""Unit tests for validation.report_builder (sections, JUnit parse, release_allowed)."""

from __future__ import annotations

from pathlib import Path

from validation.report_builder import (
    SECTION_IDS,
    ParsedCase,
    build_report,
    section_for_case,
    summarize_sections,
)


def test_section_for_case_priority_feature_switch_before_kpi() -> None:
    blob_class = "tests.release_validation.test_analysis_payload_golden"
    assert section_for_case(blob_class, "test_feature_switch_matches_baseline") == "feature_switch_validation"
    assert section_for_case(blob_class, "test_analysis_payload_matches_baseline") == "kpi_validation"


def test_section_for_case_fallback_statistical() -> None:
    assert (
        section_for_case("tests.release_validation.test_phase1_infrastructure", "test_something")
        == "statistical_validation"
    )


def test_summarize_sections_all_pass_release_allowed() -> None:
    cases = [
        ParsedCase("m.test_data_contract_golden", "test_foo", 0.1, "passed", None),
        # Fallback statistical bucket without any _STATISTICAL_KNOWN_PREFIXES substring in blob.
        ParsedCase("m.test_future_release_only", "test_bar", 0.1, "passed", None),
    ]
    sections, final, unmapped = summarize_sections(cases)
    assert len(sections) == len(SECTION_IDS)
    assert sections["dataset_validation"]["tests_run"] == 1
    assert sections["dataset_validation"]["status"] == "PASS"
    assert sections["statistical_validation"]["tests_run"] == 1
    assert final["release_allowed"] is True
    assert final["status"] == "PASS"
    assert unmapped == 1  # statistical case without known statistical substring


def test_summarize_sections_fail_blocks_release() -> None:
    cases = [
        ParsedCase("m.test_manifest_release_contract", "test_x", 0.1, "failed", "boom"),
    ]
    sections, final, _unmapped = summarize_sections(cases)
    assert sections["dataset_validation"]["status"] == "FAIL"
    assert sections["dataset_validation"]["failed"] == 1
    assert sections["dataset_validation"]["failed_nodeids"]
    assert final["release_allowed"] is False
    assert final["status"] == "FAIL"


def test_build_report_from_minimal_junit(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    junit = tmp_path / "junit.xml"
    junit.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" errors="0" failures="0" skipped="0" tests="1">
    <testcase classname="tests.release_validation.test_no_coords_golden" name="test_foo" time="0.01"/>
  </testsuite>
</testsuites>
""",
        encoding="utf-8",
    )
    (repo / "golden_dataset").mkdir()
    (repo / "golden_dataset" / "normal_baseline" / "expected").mkdir(parents=True)
    (repo / "golden_dataset" / "normal_baseline" / "expected" / "manifest.json").write_text(
        '{"dataset_version": "t"}\n', encoding="utf-8"
    )

    doc = build_report(
        repo_root=repo,
        junit_path=junit,
        pytest_exit_code=0,
        golden_profile="default",
        extra_pytest_args=[],
    )
    assert doc["schema_version"] == "2"
    assert doc["dataset_validation"]["tests_run"] == 1
    assert doc["final_result"]["release_allowed"] is True
    assert doc["unmapped_tests_count"] == 0
    assert "modules" not in doc
    assert doc["tests"][0]["section"] == "dataset_validation"


def test_build_report_pytest_nonzero_denies_release_even_if_junit_clean(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    junit = tmp_path / "junit.xml"
    junit.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" errors="0" failures="0" skipped="0" tests="1">
    <testcase classname="a.b" name="test_ok" time="0.01"/>
  </testsuite>
</testsuites>
""",
        encoding="utf-8",
    )
    (repo / "golden_dataset").mkdir()
    (repo / "golden_dataset" / "normal_baseline" / "expected").mkdir(parents=True)
    (repo / "golden_dataset" / "normal_baseline" / "expected" / "manifest.json").write_text(
        "{}", encoding="utf-8"
    )

    doc = build_report(repo_root=repo, junit_path=junit, pytest_exit_code=1, golden_profile="x", extra_pytest_args=[])
    assert doc["final_result"]["release_allowed"] is False
    assert doc["overall_status"] == "FAIL"
