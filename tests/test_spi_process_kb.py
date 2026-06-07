"""Tests for SPI process knowledge base loader, matcher, and diagnosis integration."""
from __future__ import annotations

import json

import pytest

from app.services import multi_signal_diagnosis as msd
from app.services.spi_process_kb_loader import (
    CANONICAL_SPI_KB_WORKBOOK_BASENAME,
    SPIProcessKnowledgeBase,
    default_kb_dir,
    load_spi_process_kb,
)
from app.services.spi_process_kb_matcher import (
    map_internal_abnormality_to_matrix_label,
    match_chart_signal_lookup,
    match_multi_signal_rules,
    merge_inspection_checklist_items,
)


def test_canonical_workbook_basename() -> None:
    assert CANONICAL_SPI_KB_WORKBOOK_BASENAME == "SPI_製程對應知識庫_v1.0.xlsx"


def test_manifest_records_reference_workbook() -> None:
    mpath = default_kb_dir() / "manifest.json"
    assert mpath.is_file()
    with open(mpath, encoding="utf-8") as f:
        man = json.load(f)
    assert man.get("source_xlsx_basename") == CANONICAL_SPI_KB_WORKBOOK_BASENAME


def test_default_kb_dir_exists() -> None:
    d = default_kb_dir()
    assert d.is_dir()
    assert (d / "multi_signal_rules.json").is_file()


def test_load_spi_process_kb_ok() -> None:
    kb, rep = load_spi_process_kb()
    assert rep.status in ("ok", "partial", "empty")
    assert isinstance(kb.multi_signal_rules, list)
    if kb.multi_signal_rules:
        assert kb.multi_signal_rules[0].get("rule_id", "").startswith("R")


def test_match_multi_signal_rules_nonempty() -> None:
    kb, _ = load_spi_process_kb()
    if not kb.multi_signal_rules:
        pytest.skip("no rules in bundle")
    diagnostics = [
        {
            "severity": "warning",
            "rule_id": "heatmap_volume_ooc",
            "feature_label": "Volume",
            "summary": "heatmap cluster",
        },
        {
            "severity": "error",
            "rule_id": "spc_r1_violation",
            "feature_label": "Volume",
            "summary": "violation",
        },
    ]
    signals = msd.collect_signals(diagnostics)
    primary = msd.classify_primary_anomaly_type(signals)
    matched = match_multi_signal_rules(
        kb.multi_signal_rules,
        signals,
        primary,
        top_n=3,
        min_score=1,
    )
    assert isinstance(matched, list)


def test_dimension_matrix_label_mapping() -> None:
    assert map_internal_abnormality_to_matrix_label("Local") == "Cluster"
    assert map_internal_abnormality_to_matrix_label("Variation_increase") == "Variation"


def test_merge_inspection_checklist() -> None:
    checklist = [
        {
            "process_category": "Stencil",
            "inspection_item": "AR",
            "measurement_method": "calc",
            "normal_threshold": "≥0.66",
            "priority_stars": 5,
            "remarks": "",
        }
    ]
    out = merge_inspection_checklist_items(
        checklist,
        ["Stencil / 鋼網", "Other"],
        limit=3,
    )
    assert len(out) == 1


def test_run_multi_signal_diagnosis_kb_keys() -> None:
    out = msd.run_multi_signal_diagnosis([])
    assert "kb_load_status" in out
    assert "kb_matched_rules" in out
    assert "kb_chart_lookup_hits" in out


def test_run_multi_signal_diagnosis_injected_empty_kb() -> None:
    empty = SPIProcessKnowledgeBase()
    out = msd.run_multi_signal_diagnosis([], kb_bundle=empty)
    assert out["kb_load_status"] == "ok"
    assert out["kb_matched_rules"] == []


def test_chart_signal_lookup_match() -> None:
    kb, _ = load_spi_process_kb()
    if not kb.chart_signal_lookup:
        pytest.skip("no chart lookup")
    signals = [
        {
            "chart_type": "CUSUM",
            "anomaly_type": "Drift",
            "anomaly_type_zh": "",
            "severity": "warning",
            "feature": "Volume",
            "rule_id": "cusum_drift",
            "summary": "downward",
        }
    ]
    hits = match_chart_signal_lookup(kb.chart_signal_lookup, signals)
    assert isinstance(hits, list)
