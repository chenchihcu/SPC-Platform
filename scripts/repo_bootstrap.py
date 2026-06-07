from __future__ import annotations

import sys
from pathlib import Path


def ensure_repo_root_on_sys_path(repo_root: Path) -> Path:
    """Ensure deterministic repo-root import bootstrap for script entrypoints."""
    root = repo_root.resolve()
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    return root
