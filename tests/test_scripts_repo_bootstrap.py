from __future__ import annotations

import sys
from pathlib import Path

from scripts.repo_bootstrap import ensure_repo_root_on_sys_path


def test_ensure_repo_root_on_sys_path_inserts_once() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    root_str = str(repo_root.resolve())
    original_count = sys.path.count(root_str)

    resolved = ensure_repo_root_on_sys_path(repo_root)
    ensure_repo_root_on_sys_path(repo_root)

    assert resolved == repo_root.resolve()
    assert sys.path[0] == root_str
    assert sys.path.count(root_str) == max(1, original_count)
