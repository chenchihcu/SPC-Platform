from __future__ import annotations

import copy
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.analytics.moran_i_engine import MoranIEngine
from app.analytics.multivariate_spc_engine import MultivariateSPCEngine
from app.analytics.radar_payload_helper import build_radar_from_dataframe_groups
from scripts import validate_db_chart_semantics as validator


def _valid_density(mode: str, **data: object) -> dict:
    return {
        "metadata": {"is_valid": True, "error": ""},
        "data": {"mode": mode, **data},
        "statistics": {},
    }


def _density_payloads() -> tuple[dict[int, dict], list[str]]:
    features = ["Volume", "Area", "Height"]
    per_feature = {
        feature: {"density": _valid_density("univariate", values=[1.0, 2.0])}
        for feature in features
    }
    payloads = {
        1: {
            "selected_features": ["Volume"],
            "density": _valid_density("univariate", values=[1.0, 2.0]),
            "parameters": per_feature,
            "dual_parameters": {
                "Volume+Area": {
                "density": _valid_density(
                    "bivariate",
                    x=[1.0, 2.0],
                    y=[3.0, 4.0],
                    col_x="Volume",
                    col_y="Area",
                )
                }
            },
        },
        2: {
            "selected_features": ["Volume", "Area"],
            "density": _valid_density(
                "bivariate",
                x=[1.0, 2.0],
                y=[3.0, 4.0],
                col_x="Volume",
                col_y="Area",
            ),
            "parameters": per_feature,
        },
        3: {
            "selected_features": features,
            "density": {
                "metadata": {"is_valid": False, "error": "三特徵改用逐特徵密度"},
                "data": {},
                "statistics": {},
            },
            "parameters": per_feature,
        },
    }
    return payloads, features


def test_density_semantics_are_asserted_for_one_two_and_three_features():
    payloads, features = _density_payloads()

    modes, checks = validator._validate_density_semantics(payloads, features)

    assert modes == validator.EXPECTED_DENSITY_MODES
    assert all(check["status"] == "PASS" for check in checks)
    assert "density" in validator.PAIR_EXPANSION_CHARTS


def test_density_semantic_mismatch_is_a_failure():
    payloads, features = _density_payloads()
    payloads[2]["density"] = _valid_density("univariate", values=[1.0, 2.0])

    _, checks = validator._validate_density_semantics(payloads, features)

    failed = [check for check in checks if check["status"] == "FAIL"]
    assert {check["name"] for check in failed} == {
        "density_mode.2f_density",
        "density_mode.2f_pair_semantics",
    }


def test_missing_pair_density_fails_closed_and_is_reported():
    payloads, features = _density_payloads()
    payloads[1]["dual_parameters"] = {}

    resolved = validator._resolve(payloads[1], "density", features[:2])
    _, failures = validator._build_pair_expansion_rows(payloads[1], features)

    assert resolved["metadata"]["is_valid"] is False
    density_failure = next(
        row
        for row in failures
        if row["chart_id"] == "density" and row["pair"] == features[:2]
    )
    assert density_failure["density_mode"] == "unknown"
    assert density_failure["semantic_valid"] is False


def test_wrong_pair_density_fails_resolver_and_independent_semantic_check():
    payloads, features = _density_payloads()
    wrong_density = payloads[1]["dual_parameters"]["Volume+Area"]["density"]
    wrong_density["data"]["col_y"] = "Height"

    resolved = validator._resolve(payloads[1], "density", features[:2])
    _, failures = validator._build_pair_expansion_rows(payloads[1], features)

    assert resolved["metadata"]["is_valid"] is False
    density_failure = next(
        row
        for row in failures
        if row["chart_id"] == "density" and row["pair"] == features[:2]
    )
    assert density_failure["semantic_valid"] is False
    assert validator._bivariate_density_matches_pair(wrong_density, features[:2]) is False


def test_three_feature_density_requires_every_selected_child():
    payloads, features = _density_payloads()
    payloads = copy.deepcopy(payloads)
    del payloads[3]["parameters"]["Height"]

    _, checks = validator._validate_density_semantics(payloads, features)

    failed_names = {check["name"] for check in checks if check["status"] == "FAIL"}
    assert "density_mode.3f.features.mismatch_count" in failed_names
    assert "density_mode.3f.Height.present" in failed_names
    assert "density_mode.3f.Height.is_valid" in failed_names
    assert "density_mode.3f.Height.mode" in failed_names


def test_hotelling_point_order_mutation_is_detected():
    rng = np.random.default_rng(23)
    joined_df = pd.DataFrame(
        rng.normal(size=(24, 3)),
        columns=["Volume", "Area", "Height"],
    )
    hotelling = MultivariateSPCEngine.compute_hotelling_t2(
        joined_df,
        ["Volume", "Area", "Height"],
    )
    payload = {"hotelling_t2": hotelling}

    baseline_checks = validator._validate_three_feature_semantics(
        joined_df,
        payload,
        ["Volume", "Area", "Height"],
    )
    baseline_hotelling = [
        check for check in baseline_checks if check["name"].startswith("3f.hotelling_t2")
    ]
    assert baseline_hotelling
    assert all(check["status"] == "PASS" for check in baseline_hotelling)

    mutated = copy.deepcopy(payload)
    mutated["hotelling_t2"]["data"]["t2_values"].reverse()
    mutated_checks = validator._validate_three_feature_semantics(
        joined_df,
        mutated,
        ["Volume", "Area", "Height"],
    )
    point_check = next(
        check
        for check in mutated_checks
        if check["name"] == "3f.hotelling_t2.t2_values.max_abs_error"
    )
    assert point_check["status"] == "FAIL"


def test_radar_group_mean_mutation_is_detected():
    joined_df = pd.DataFrame(
        {
            "RefDes": ["U1", "U1", "U2", "U2"],
            "Volume": [1.0, 3.0, 5.0, 7.0],
            "Area": [2.0, 4.0, 6.0, 8.0],
            "Height": [3.0, 5.0, 7.0, 9.0],
        }
    )
    radar = build_radar_from_dataframe_groups(
        joined_df,
        ["Volume", "Area", "Height"],
    )
    payload = {"radar": radar}

    baseline = validator._validate_radar_semantics(
        joined_df,
        payload,
        ["Volume", "Area", "Height"],
    )
    assert all(check["status"] == "PASS" for check in baseline)

    payload["radar"]["data"]["series"][0]["values"][0] += 1.0
    mutated = validator._validate_radar_semantics(
        joined_df,
        payload,
        ["Volume", "Area", "Height"],
    )
    value_check = next(
        check for check in mutated if check["name"] == "3f.radar.values.max_abs_error"
    )
    assert value_check["status"] == "FAIL"


def test_lisa_deterministic_field_mutation_is_detected():
    rng = np.random.default_rng(29)
    joined_df = pd.DataFrame(
        {
            "X": np.arange(16, dtype=float) % 4,
            "Y": np.arange(16, dtype=float) // 4,
            "Volume": rng.normal(size=16),
        }
    )
    lisa = MoranIEngine.compute_local_moran_i(
        joined_df[["X", "Y"]],
        joined_df["Volume"],
        k=3,
    )
    one_feature_payload = {"parameters": {"Volume": {"lisa": lisa}}}
    spec = {"volume": {"target": 0.0, "lsl": -10.0, "usl": 10.0}}

    baseline = validator._validate_single_feature_semantics(
        joined_df,
        one_feature_payload,
        ["Volume"],
        spec,
    )
    lisa_checks = [check for check in baseline if ".lisa." in check["name"]]
    assert lisa_checks
    assert all(check["status"] == "PASS" for check in lisa_checks)

    mutated_payload = copy.deepcopy(one_feature_payload)
    mutated_payload["parameters"]["Volume"]["lisa"]["data"]["local_i"].reverse()
    mutated = validator._validate_single_feature_semantics(
        joined_df,
        mutated_payload,
        ["Volume"],
        spec,
    )
    local_i_check = next(
        check
        for check in mutated
        if check["name"] == "Volume.lisa.local_i.max_abs_error"
    )
    assert local_i_check["status"] == "FAIL"


def test_readonly_connection_enables_sqlite_query_only(tmp_path: Path):
    db_path = tmp_path / "semantic.db"
    with sqlite3.connect(db_path) as writable:
        writable.execute("CREATE TABLE sample (value INTEGER)")

    readonly = None
    with validator._connect_readonly(db_path) as connection:
        readonly = connection
        assert readonly.execute("PRAGMA query_only").fetchone()[0] == 1
        with pytest.raises(sqlite3.OperationalError):
            readonly.execute("INSERT INTO sample VALUES (1)")
    assert readonly is not None
    with pytest.raises(sqlite3.ProgrammingError):
        readonly.execute("SELECT 1")


def test_output_directory_must_remain_under_outputs(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(validator, "REPO_ROOT", tmp_path)

    assert validator._resolve_output_dir("Outputs/db_semantics") == (
        tmp_path / "Outputs" / "db_semantics"
    ).resolve()
    with pytest.raises(ValueError, match="must stay within"):
        validator._resolve_output_dir("outside")
    with pytest.raises(ValueError, match="must stay within"):
        validator._resolve_output_dir(str(tmp_path.parent / "outside"))


def test_output_directory_rejects_symlink_escape(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(validator, "REPO_ROOT", tmp_path)
    outputs = tmp_path / "Outputs"
    outputs.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    link = outputs / "escape"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlink unavailable: {exc}")

    with pytest.raises(ValueError, match="must stay within"):
        validator._resolve_output_dir("Outputs/escape/result")


def test_error_exit_writes_machine_readable_summary(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(validator, "REPO_ROOT", tmp_path)

    def _raise_validation_error(_args):
        raise FileNotFoundError("measurement file missing")

    monkeypatch.setattr(validator, "run_validation", _raise_validation_error)

    exit_code = validator.main(["--output", "Outputs/error_case", "--quiet"])

    assert exit_code == 2
    summary = json.loads(
        (tmp_path / "Outputs" / "error_case" / "summary.json").read_text(encoding="utf-8")
    )
    assert summary["status"] == "ERROR"
    assert summary["failures"] == 1
    assert summary["error"]["type"] == "FileNotFoundError"


def test_invalid_output_returns_error_contract_in_safe_fallback(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(validator, "REPO_ROOT", tmp_path)

    exit_code = validator.main(["--output", "outside", "--quiet"])

    assert exit_code == 2
    summary_path = tmp_path / "Outputs" / "db_chart_semantics_error" / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["status"] == "ERROR"
    assert summary["failures"] == 1
    assert summary["requested_output"] == "outside"
    assert summary["error"]["type"] == "ValueError"
    assert "Traceback" not in capsys.readouterr().out


def test_error_contract_survives_unavailable_fallback(monkeypatch, capsys):
    def _reject_every_output(_raw_output: str) -> Path:
        raise ValueError("all output paths unavailable")

    monkeypatch.setattr(validator, "_resolve_output_dir", _reject_every_output)

    exit_code = validator.main(["--output", "outside", "--quiet"])

    assert exit_code == 2
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "ERROR"
    assert output["failures"] == 1
    assert output["summary"] is None
    assert output["error"]["type"] == "ValueError"
    assert output["summary_error"]["type"] == "ValueError"
