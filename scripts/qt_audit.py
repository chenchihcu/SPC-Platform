#!/usr/bin/env python3
"""
qt_audit.py — SPC Platform Code Quality Audit

Scans the project for Qt/PySide6-specific and general Python quality issues.
All categories must report 0 before delivery (see AI_RULES.md).

Usage:
    python scripts/qt_audit.py [app_dir]

    app_dir defaults to 'app/' relative to this script's parent directory.

Exit codes:
    0 — all checks pass
    1 — one or more issues found
"""

import ast
import os
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EXCLUDE_DIRS = {"__pycache__", ".git", ".venv", "venv", "node_modules"}


def iter_py_files(root: Path, exclude_tokens: bool = False):
    """Yield all .py files under root, skipping excluded dirs."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for f in filenames:
            if not f.endswith(".py"):
                continue
            path = Path(dirpath) / f
            if exclude_tokens and path.name == "tokens.py":
                continue
            yield path


def read(path: Path) -> str:
    """Read file safely."""
    return path.read_text(encoding="utf-8", errors="replace")


def safe_print(text: str = "", *, stream=None) -> None:
    """Print text safely on non-UTF8 consoles (e.g. cp950)."""
    out = stream or sys.stdout
    message = str(text)
    encoding = getattr(out, "encoding", None) or "utf-8"
    try:
        out.write(message + "\n")
    except UnicodeEncodeError:
        safe = message.encode(encoding, errors="replace").decode(encoding, errors="replace")
        out.write(safe + "\n")


# ---------------------------------------------------------------------------
# Check 1: Raw hex values outside tokens.py
# ---------------------------------------------------------------------------

def check_raw_hex(root: Path) -> list[dict]:
    issues = []
    for path in iter_py_files(root, exclude_tokens=True):
        src = read(path)
        hits = re.findall(r"[\"'](#[0-9A-Fa-f]{6})[\"']", src)
        if hits:
            issues.append({"file": str(path), "count": len(hits), "values": list(set(hits))})
    return issues


# ---------------------------------------------------------------------------
# Check 2: Magic pixel values (setFixedWidth/Height, setMinimumHeight with bare int > 0)
# ---------------------------------------------------------------------------

def check_magic_px(root: Path) -> list[dict]:
    issues = []
    pattern = re.compile(
        r"\.(setFixedWidth|setFixedHeight|setMinimumHeight|setMinimumWidth"
        r"|setMaximumWidth|setMaximumHeight)\(([1-9]\d*)\)"
    )
    for path in iter_py_files(root, exclude_tokens=True):
        src = read(path)
        hits = pattern.findall(src)
        if hits:
            issues.append({"file": str(path), "calls": hits})
    return issues


# ---------------------------------------------------------------------------
# Check 3: Syntax errors
# ---------------------------------------------------------------------------

def check_syntax(root: Path) -> list[dict]:
    issues = []
    for path in iter_py_files(root):
        src = read(path)
        try:
            ast.parse(src)
        except SyntaxError as e:
            issues.append({"file": str(path), "error": str(e)})
    return issues


# ---------------------------------------------------------------------------
# Check 4: Bare except clauses
# ---------------------------------------------------------------------------

def check_bare_except(root: Path) -> list[dict]:
    issues = []
    for path in iter_py_files(root):
        src = read(path)
        lines = src.splitlines()
        hits = []
        for i, line in enumerate(lines, 1):
            if re.match(r"\s*except\s*:", line):
                hits.append(i)
        if hits:
            issues.append({"file": str(path), "lines": hits})
    return issues


# ---------------------------------------------------------------------------
# Check 5: Debug print() statements
# ---------------------------------------------------------------------------

def check_debug_prints(root: Path) -> list[dict]:
    issues = []
    for path in iter_py_files(root):
        src = read(path)
        lines = src.splitlines()
        hits = []
        for i, line in enumerate(lines, 1):
            if re.match(r"\s*print\(", line):
                hits.append((i, line.strip()[:80]))
        if hits:
            issues.append({"file": str(path), "lines": hits})
    return issues


# ---------------------------------------------------------------------------
# Check 6: Public methods without docstrings
# ---------------------------------------------------------------------------

def check_missing_docstrings(root: Path) -> list[dict]:
    issues = []
    for path in iter_py_files(root):
        src = read(path)
        lines = src.splitlines()
        hits = []
        i = 0
        while i < len(lines):
            line = lines[i]
            m = re.match(r"\s{4}def ([a-z][a-zA-Z0-9_]+)\(self", line)
            if m and not m.group(1).startswith("_"):
                name = m.group(1)
                j = i + 1
                while j < len(lines) and lines[j].strip() == "":
                    j += 1
                has_doc = j < len(lines) and lines[j].strip().startswith('"""')
                if not has_doc:
                    hits.append((i + 1, name))
            i += 1
        if hits:
            issues.append({"file": str(path), "methods": hits})
    return issues


# ---------------------------------------------------------------------------
# Check 7: QSS — widgets with :hover but missing :disabled (Qt state matrix)
# ---------------------------------------------------------------------------

def check_qss_state_matrix(root: Path) -> list[dict]:
    """Find QSS widget selectors that have :hover but are missing :disabled."""
    # These widget types have no meaningful disabled state in Qt — exempt from check
    DISABLED_EXEMPT = {"QScrollBar", "QSplitter", "QTableView", "QHeaderView", "QAbstractScrollArea"}

    issues = []
    qss_files = list(Path(root).rglob("*stylesheet*.py")) + list(Path(root).rglob("*dark_*.py"))

    for path in qss_files:
        src = read(path)
        selectors = re.findall(r"^\s*([^\n{]+)\{", src, re.MULTILINE)
        selectors = [s.strip().strip("'\"f") for s in selectors]

        with_hover: set[str] = set()
        with_disabled: set[str] = set()

        for s in selectors:
            m = re.match(r"^(Q\w+|#\w+)", s)
            if not m:
                continue
            base = m.group(1)
            if base in DISABLED_EXEMPT:
                continue
            if ":hover" in s:
                with_hover.add(base)
            if ":disabled" in s or "[disabled" in s:
                with_disabled.add(base)

        missing = sorted(with_hover - with_disabled)
        if missing:
            issues.append({"file": str(path), "missing_disabled": missing})

    return issues


# ---------------------------------------------------------------------------
# Check 8: QSS unsupported CSS properties
# ---------------------------------------------------------------------------

UNSUPPORTED_QSS_PROPERTIES = (
    "animation",
    "box-shadow",
    "opacity",
    "outline",
    "text-transform",
    "transform",
    "transition",
)


def _iter_qss_files(root: Path) -> list[Path]:
    candidates = list(Path(root).rglob("*stylesheet*.py")) + list(Path(root).rglob("*dark_*.py"))
    return sorted(set(candidates))


def _strip_css_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", lambda match: "\n" * match.group(0).count("\n"), text, flags=re.S)


def check_unsupported_qss_properties(root: Path) -> list[dict]:
    """Find CSS properties that Qt QSS ignores or handles inconsistently."""
    issues = []
    property_pattern = re.compile(
        r"^\s*(" + "|".join(re.escape(prop) for prop in UNSUPPORTED_QSS_PROPERTIES) + r")\s*:",
        re.MULTILINE,
    )
    for path in _iter_qss_files(root):
        src = _strip_css_comments(read(path))
        hits = []
        for i, line in enumerate(src.splitlines(), 1):
            match = property_pattern.match(line)
            if match:
                hits.append((i, match.group(1)))
        if hits:
            issues.append({"file": str(path), "lines": hits})
    return issues


# ---------------------------------------------------------------------------
# Check 9: f-string CSS with Python `or` logic (silent fallback bug)
# ---------------------------------------------------------------------------

def check_fstring_or_logic(root: Path) -> list[dict]:
    """Detect f-string CSS generation using `or` between token names (T-1 silent bug)."""
    issues = []
    pattern = re.compile(r"f['\"].*\{([A-Z_]+\s+or\s+[A-Z_]+)\}.*['\"]")
    for path in iter_py_files(root):
        src = read(path)
        hits = pattern.findall(src)
        if hits:
            issues.append({"file": str(path), "patterns": hits})
    return issues


# ---------------------------------------------------------------------------
# Check 10: Methods missing return type annotations
# ---------------------------------------------------------------------------

def check_missing_return_types(root: Path) -> list[dict]:
    """Find public methods with no -> return type annotation."""
    issues = []
    for path in iter_py_files(root):
        src = read(path)
        lines = src.splitlines()
        hits = []
        for i, line in enumerate(lines, 1):
            m = re.match(r"\s{4}def ([a-zA-Z_][a-zA-Z0-9_]+)\(self[^)]*\)\s*:", line)
            if m:
                name = m.group(1)
                if not name.startswith("_") and "->" not in line:
                    hits.append((i, name))
        if hits:
            issues.append({"file": str(path), "methods": hits})
    return issues


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

CHECKS = [
    ("raw_hex_outside_tokens",    "Raw hex (#RRGGBB) outside tokens.py",     check_raw_hex),
    ("magic_pixel_values",        "Magic pixel values (bare int in setXxx)",  check_magic_px),
    ("syntax_errors",             "Python syntax errors",                      check_syntax),
    ("bare_except",               "Bare except: clauses",                      check_bare_except),
    ("debug_prints",              "Debug print() statements",                  check_debug_prints),
    ("missing_docstrings",        "Public methods without docstrings",         check_missing_docstrings),
    ("qss_state_matrix",          "QSS widgets with :hover missing :disabled", check_qss_state_matrix),
    ("unsupported_qss_properties", "Unsupported Qt QSS CSS properties",         check_unsupported_qss_properties),
    ("fstring_or_logic",          "f-string CSS with `or` fallback bug",       check_fstring_or_logic),
    ("missing_return_types",      "Public methods missing -> return type",     check_missing_return_types),
]


def run_audit(app_dir: Path) -> int:
    """Run all checks. Returns total issue count."""
    total_issues = 0
    results = []

    for key, label, fn in CHECKS:
        issues = fn(app_dir)
        file_count = len(issues)
        results.append((key, label, file_count, issues))
        total_issues += file_count

    # Report
    max_label = max(len(label) for _, label, _, _ in results)
    safe_print()
    safe_print("  Qt Audit Results")
    safe_print("  " + "-" * (max_label + 20))
    for key, label, count, issues in results:
        icon = "PASS" if count == 0 else "FAIL"
        status = "OK" if count == 0 else f"{count} file(s)"
        safe_print(f"  {icon:<4}  {label:<{max_label}}  {status}")
        if count > 0 and "--verbose" in sys.argv:
            for item in issues:
                f = item.get("file", "?")
                detail = (
                    item.get("values") or item.get("calls") or item.get("lines") or
                    item.get("methods") or item.get("patterns") or item.get("missing_disabled") or
                    item.get("error", "")
                )
                safe_print(f"       {f}")
                if isinstance(detail, list):
                    for d in detail[:5]:
                        safe_print(f"         {d}")
    safe_print()
    if total_issues == 0:
        safe_print("  ALL CLEAR - ready for delivery")
    else:
        safe_print(f"  {total_issues} categories have issues - run with --verbose for details")
    safe_print()
    return total_issues


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        app_dir = Path(args[0])
    else:
        # Default: 'app/' relative to this script's parent
        app_dir = Path(__file__).parent.parent / "app"

    if not app_dir.exists():
        safe_print(f"Error: directory not found: {app_dir}", stream=sys.stderr)
        sys.exit(2)

    safe_print(f"\n  Scanning: {app_dir.resolve()}")
    issue_count = run_audit(app_dir)
    sys.exit(0 if issue_count == 0 else 1)


if __name__ == "__main__":
    main()
