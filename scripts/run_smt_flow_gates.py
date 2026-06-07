#!/usr/bin/env python3
"""
SMT SPI flow gates: run lint (if available), typecheck (if available), and pytest.
Emit a compact gate report for self-heal loops. See AGENTS.md and smt-spi-self-heal skill.
Usage: python scripts/run_smt_flow_gates.py --repo-root <path>
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _repo_root(path: str) -> Path:
    root = Path(path).resolve()
    if not root.is_dir():
        raise SystemExit(f"Not a directory: {root}")
    return root


def _run(cmd: list[str], cwd: Path, capture: bool = True) -> tuple[int, str]:
    r = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    out = (r.stdout or "") + (r.stderr or "")
    return r.returncode, out.strip()


def _emit(text: str) -> None:
    """Print safely on Windows consoles that cannot encode all lint output."""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    sys.stdout.buffer.write((text + "\n").encode(encoding, errors="replace"))


def gate_pytest(repo: Path) -> tuple[str, str]:
    """Run pytest on tests/."""
    code, out = _run([sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"], repo)
    if code == 0:
        return "pass", out.splitlines()[-1] if out else "ok"
    return "fail", out or f"exit {code}"


def gate_ruff(repo: Path) -> tuple[str, str]:
    """Run ruff check if available."""
    code, _ = _run([sys.executable, "-c", "import ruff"], repo)
    if code != 0:
        return "not_available", "ruff not installed"
    code, out = _run([sys.executable, "-m", "ruff", "check", "app/", "tests/"], repo)
    if code == 0:
        return "pass", "ok"
    return "fail", out or f"exit {code}"


def gate_mypy(repo: Path) -> tuple[str, str]:
    """Run mypy if available and config exists."""
    if not (repo / "pyproject.toml").exists() and not (repo / "mypy.ini").exists():
        return "not_available", "no mypy config"
    code, _ = _run([sys.executable, "-c", "import mypy"], repo)
    if code != 0:
        return "not_available", "mypy not installed"
    code, out = _run([sys.executable, "-m", "mypy", "app/", "--no-error-summary"], repo)
    if code == 0:
        return "pass", "ok"
    return "fail", out or f"exit {code}"


def main() -> None:
    ap = argparse.ArgumentParser(description="Run SMT flow gates")
    ap.add_argument("--repo-root", default=".", help="Repository root directory")
    args = ap.parse_args()
    repo = _repo_root(args.repo_root)

    gates = [
        ("pytest", gate_pytest),
        ("ruff", gate_ruff),
        ("mypy", gate_mypy),
    ]
    results: list[tuple[str, str, str]] = []
    for name, fn in gates:
        status, detail = fn(repo)
        results.append((name, status, detail))

    # Compact report
    all_pass = not any(status == "fail" for _, status, _ in results)
    for name, status, detail in results:
        if status == "not_available":
            _emit(f"[{name}] not_available: {detail}")
        elif status == "pass":
            _emit(f"[{name}] pass")
        else:
            _emit(f"[{name}] fail: {detail[:200]}{'...' if len(detail) > 200 else ''}")

    if all_pass:
        _emit("GATES: all available gates passed.")
    else:
        _emit("GATES: one or more gates failed.")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
