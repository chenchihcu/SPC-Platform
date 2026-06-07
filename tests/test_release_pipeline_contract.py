"""Release pipeline contract guard for Watchlist #7."""

from __future__ import annotations

from pathlib import Path


def test_ci_workflow_keeps_pytest_and_release_check_ext_contract() -> None:
    repo = Path(__file__).resolve().parents[1]
    workflow = repo / ".github" / "workflows" / "pytest.yml"
    text = workflow.read_text(encoding="utf-8")

    pytest_cmd = "python -m pytest -q"
    release_cmd = "python scripts/release_check.py --skip-ruff --skip-mypy --with-release-ext"

    assert pytest_cmd in text
    assert release_cmd in text
    assert text.index(pytest_cmd) < text.index(release_cmd)
