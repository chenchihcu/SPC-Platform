from __future__ import annotations

import importlib.util
import os
import sys
from typing import Callable

from app.bootstrap.runtime_env import ensure_home_env

_REQUIRED_MODULES: tuple[str, ...] = (
    "app.ui.pages.diagnostic_page",
)


def _runtime_context_lines() -> list[str]:
    return [
        f"python_executable={sys.executable}",
        f"python_version={sys.version.split()[0]}",
        f"cwd={os.getcwd()}",
        f"script_dir={os.path.dirname(os.path.abspath(__file__))}",
    ]


def _missing_required_modules() -> list[str]:
    missing: list[str] = []
    for module_name in _REQUIRED_MODULES:
        if importlib.util.find_spec(module_name) is None:
            missing.append(module_name)
    return missing


def _load_run_app() -> Callable[[], None]:
    from app.ui.main_window import run_app

    return run_app


def _print_startup_error(title: str, details: list[str]) -> None:
    print(title, file=sys.stderr)
    for line in details:
        print(f" - {line}", file=sys.stderr)


def main() -> int:
    ensure_home_env()

    missing_modules = _missing_required_modules()
    if missing_modules:
        _print_startup_error(
            "Startup preflight failed: required modules are missing.",
            [f"missing_module={name}" for name in missing_modules]
            + _runtime_context_lines()
            + ["hint=Run from repository root and verify file copy integrity."],
        )
        return 1

    try:
        run_app = _load_run_app()
    except ModuleNotFoundError as exc:
        _print_startup_error(
            "Startup import failed (ModuleNotFoundError).",
            [f"exception={exc}"]
            + _runtime_context_lines()
            + ["hint=Check interpreter/environment and repository path consistency."],
        )
        return 1

    run_app()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
