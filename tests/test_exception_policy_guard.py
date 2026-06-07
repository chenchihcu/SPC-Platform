from __future__ import annotations

import ast
from pathlib import Path


def _is_exception_name(node: ast.expr | None, name: str) -> bool:
    if isinstance(node, ast.Name):
        return node.id == name
    if isinstance(node, ast.Tuple):
        return any(_is_exception_name(element, name) for element in node.elts)
    return False


def test_app_exception_handlers_are_narrow() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    app_root = repo_root / "app"
    findings: list[str] = []

    for path in sorted(app_root.rglob("*.py")):
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(path))
        rel = path.relative_to(repo_root).as_posix()

        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            lineno = getattr(node, "lineno", 1)
            if node.type is None:
                findings.append(f"{rel}:{lineno} bare except is not allowed")
            elif _is_exception_name(node.type, "Exception"):
                findings.append(f"{rel}:{lineno} except Exception is not allowed")

    assert findings == [], "Broad exception policy violations:\n" + "\n".join(findings)
