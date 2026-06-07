"""release_report traceability: plan module index value shapes."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_release_check_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "release_check.py"
    spec = importlib.util.spec_from_file_location("_release_check_under_test", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_release_validation_plan_modules_values_are_str_or_list_of_str() -> None:
    mod = _load_release_check_module()
    idx = mod._release_plan_module_index()
    for key, val in idx.items():
        assert isinstance(key, str) and len(key) == 1, key
        if isinstance(val, str):
            assert val.strip(), key
        elif isinstance(val, list):
            assert val, key
            assert all(isinstance(x, str) and x.strip() for x in val), key
        else:
            raise AssertionError(f"{key}: expected str or list[str], got {type(val)}")


def test_release_ext_test_paths_non_empty_and_expected() -> None:
    mod = _load_release_check_module()
    paths = tuple(mod._RELEASE_EXT_TEST_PATHS)
    assert paths, "_RELEASE_EXT_TEST_PATHS should not be empty"
    expected = {
        "tests/test_data_contract_code_alignment.py",
        "tests/test_spec_resolver_master_db_e2e.py",
        "tests/test_release_check_plan_modules.py",
    }
    assert set(paths) == expected
