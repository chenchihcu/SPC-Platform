from __future__ import annotations

import importlib.util
import csv
import sys
from pathlib import Path
from types import ModuleType


def _load_runner() -> ModuleType:
    path = (
        Path(__file__).resolve().parents[1]
        / ".claude"
        / "skills"
        / "spc-validation-matrix"
        / "scripts"
        / "run_matrix.py"
    )
    module_name = "_spc_validation_matrix_runner_test"
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    original_sys_path = list(sys.path)
    sys.path.insert(0, str(path.parent))
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = original_sys_path
    return module


RUNNER = _load_runner()


def test_quick_mode_keeps_all_supported_arities():
    assert RUNNER._selected_arities("1,2", quick=True) == [1, 2, 3]
    assert RUNNER._selected_arities("1,3", quick=False) == [1, 3]


def test_matrix_exit_code_blocks_every_failure_status():
    assert RUNNER._result_exit_code([]) == 1
    assert RUNNER._result_exit_code([{"status": "PASS"}, {"status": "SKIP"}]) == 0
    for status in ("FAIL", "ERROR", "STALL", "OVERLOAD", "UNKNOWN", ""):
        assert RUNNER._result_exit_code([{"status": "PASS"}, {"status": status}]) == 1


def _single_cell():
    return RUNNER.Cell(
        fixture="normal_baseline",
        arity=1,
        features=("Volume",),
        chart_id="imr",
        filter_name="full",
    )


def _matrix_statuses(output_dir: Path) -> list[str]:
    with (output_dir / "matrix.csv").open(encoding="utf-8", newline="") as handle:
        return [row["status"] for row in csv.DictReader(handle)]


def test_matrix_wall_clock_exhaustion_is_blocking_stall(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(RUNNER, "build_matrix", lambda *_args, **_kwargs: [_single_cell()])
    monkeypatch.setattr(RUNNER, "THRESHOLD_MATRIX_TIMEOUT_S", -1.0)
    output_dir = tmp_path / "matrix_timeout"

    exit_code = RUNNER.main(["--quick", "--skip-export", "--output", str(output_dir)])

    assert exit_code == 1
    assert _matrix_statuses(output_dir) == ["STALL"]


def test_fixture_load_failure_is_blocking_error(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(RUNNER, "build_matrix", lambda *_args, **_kwargs: [_single_cell()])

    def _raise_fixture_error(*_args, **_kwargs):
        raise ValueError("corrupt fixture")

    monkeypatch.setattr(RUNNER, "load_fixture", _raise_fixture_error)
    output_dir = tmp_path / "fixture_error"

    exit_code = RUNNER.main(["--quick", "--skip-export", "--output", str(output_dir)])

    assert exit_code == 1
    assert _matrix_statuses(output_dir) == ["ERROR"]
