from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path


DOC_GLOBS = ("README.md", "docs/**/*.md", "pyproject.toml")
PRODUCTION_SOURCE_DIRS = ("src", "app")
BYTECODE_PATTERNS = (
    "SourcelessFileLoader",
    "main_window_base.cpython-314.pyc",
    "_load_base_module(",
)
CHART_SKIP_CALLS = (
    "save_pareto",
    "save_grouped_boxplot",
    "save_xbar_r_chart",
    "save_line_machine_cpk_heatmap",
    "save_grouped_fail_rate",
)
SPC_ENTRY_PREFIXES = ("compute_", "analyze", "calculate_", "detect_", "build_radar_")
SPC_INVENTORY_EXTRA_FILES = {"chart_analysis_viewmodel.py"}


def _iter_files(root: Path, globs: tuple[str, ...]) -> list[Path]:
    files: set[Path] = set()
    for pattern in globs:
        files.update(root.glob(pattern))
    return sorted(path for path in files if path.is_file())


def _iter_production_python_files(root: Path) -> list[Path]:
    files: set[Path] = set()
    for directory_name in PRODUCTION_SOURCE_DIRS:
        directory = root / directory_name
        if directory.is_dir():
            files.update(directory.rglob("*.py"))
    return sorted(path for path in files if path.is_file())


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _relative_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def scan_source_codepoints(root: Path) -> list[str]:
    findings: list[str] = []
    for path in _iter_production_python_files(root):
        for line_number, line in enumerate(_read_text(path).splitlines(), start=1):
            bad = sorted({f"U+{ord(char):04X}" for char in line if 0xE000 <= ord(char) <= 0xF8FF or ord(char) == 0xFFFD})
            if bad:
                findings.append(f"source-codepoints|{_relative_posix(path, root)}:{line_number}|{' '.join(bad)}")
    return findings


def scan_bytecode_coupling(root: Path) -> list[str]:
    findings: list[str] = []
    paths = sorted(set(_iter_production_python_files(root) + _iter_files(root, DOC_GLOBS)))
    for path in paths:
        text = _read_text(path)
        for pattern in BYTECODE_PATTERNS:
            for line_number, line in enumerate(text.splitlines(), start=1):
                if pattern in line:
                    findings.append(f"bytecode-coupling|{_relative_posix(path, root)}:{line_number}|{pattern}")
    return findings


def scan_broad_exception_handlers(root: Path) -> list[str]:
    findings: list[str] = []
    pattern = re.compile(r"^\s*except Exception(?:\s+as\s+\w+)?:")
    allowed_locations = {
        (Path("src/spc_tool_1/storage/db.py"), 228),
    }
    for path in _iter_production_python_files(root):
        for line_number, line in enumerate(_read_text(path).splitlines(), start=1):
            if pattern.match(line):
                relative_path = path.relative_to(root)
                if (relative_path, line_number) in allowed_locations:
                    continue
                findings.append(f"broad-except|{relative_path.as_posix()}:{line_number}|{line.strip()}")
    return findings


def scan_silent_chart_skips(root: Path) -> list[str]:
    findings: list[str] = []
    for path in _iter_production_python_files(root):
        lines = _read_text(path).splitlines()
        recent_chart_call: tuple[int, str] | None = None
        for line_number, line in enumerate(lines, start=1):
            stripped = line.strip()
            for call_name in CHART_SKIP_CALLS:
                if f"{call_name}(" in stripped:
                    recent_chart_call = (line_number, call_name)
            if stripped.startswith("except ValueError:") or stripped.startswith("except Exception:"):
                if recent_chart_call is not None and line_number - recent_chart_call[0] <= 8:
                    findings.append(
                        f"silent-chart-skip|{_relative_posix(path, root)}:{line_number}|{recent_chart_call[1]} hidden by {stripped}"
                    )
            if stripped and not stripped.startswith(("except ", "save_")) and recent_chart_call is not None and line_number - recent_chart_call[0] > 12:
                recent_chart_call = None
    return findings


def _is_spc_inventory_path(path: Path) -> bool:
    lowered_parts = {part.lower() for part in path.parts}
    stem = path.stem.lower()
    return bool(
        lowered_parts.intersection({"analytics", "statistics", "statistical", "spc"})
        or path.name in SPC_INVENTORY_EXTRA_FILES
        or "spc" in stem
        or "statistic" in stem
    )


def collect_spc_statistical_entries(root: Path) -> list[str]:
    """Inventory candidate SPC/statistical entrypoints without changing exit status."""
    entries: list[str] = []
    for path in _iter_production_python_files(root):
        relative_path = path.relative_to(root)
        relative_text = relative_path.as_posix()
        if not _is_spc_inventory_path(relative_path):
            continue
        try:
            tree = ast.parse(_read_text(path), filename=str(path))
        except SyntaxError as exc:
            entries.append(f"spc-stat-entry-parse-error|{relative_text}:{exc.lineno or 1}|{exc.msg}")
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(SPC_ENTRY_PREFIXES):
                entries.append(f"spc-stat-entry|{relative_text}:{node.lineno}|{node.name}")
            elif isinstance(node, ast.ClassDef):
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name.startswith(SPC_ENTRY_PREFIXES):
                        entries.append(
                            f"spc-stat-entry|{relative_text}:{child.lineno}|{node.name}.{child.name}"
                        )
    return entries


def _contains_nonfinite_replace(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if not isinstance(child, ast.Call) or not isinstance(child.func, ast.Attribute):
            continue
        if child.func.attr != "replace":
            continue
        if any(isinstance(item, ast.Attribute) and item.attr == "inf" for item in ast.walk(child)):
            return True
    return False


def _has_post_dropna_nonfinite_replace(
    node: ast.Call,
    parent_by_child: dict[ast.AST, ast.AST],
) -> bool:
    current: ast.AST = node
    while current in parent_by_child:
        parent = parent_by_child[current]
        if isinstance(parent, ast.Attribute) and parent.value is current:
            current = parent
            continue
        if isinstance(parent, ast.Call) and parent.func is current:
            if (
                isinstance(current, ast.Attribute)
                and current.attr == "replace"
                and any(
                    isinstance(item, ast.Attribute) and item.attr == "inf"
                    for argument in (*parent.args, *(keyword.value for keyword in parent.keywords))
                    for item in ast.walk(argument)
                )
            ):
                return True
            current = parent
            continue
        return False
    return False


def _assigned_name_for_call_chain(
    node: ast.Call,
    parent_by_child: dict[ast.AST, ast.AST],
) -> str | None:
    current: ast.AST = node
    while current in parent_by_child:
        parent = parent_by_child[current]
        if isinstance(parent, ast.Attribute) and parent.value is current:
            current = parent
            continue
        if isinstance(parent, ast.Call) and parent.func is current:
            current = parent
            continue
        if isinstance(parent, (ast.Assign, ast.AnnAssign)) and parent.value is current:
            targets = parent.targets if isinstance(parent, ast.Assign) else [parent.target]
            if len(targets) == 1 and isinstance(targets[0], ast.Name):
                return targets[0].id
        return None
    return None


def _name_use_reaches_nonfinite_replace(
    node: ast.Name,
    parent_by_child: dict[ast.AST, ast.AST],
) -> bool:
    current: ast.AST = node
    while current in parent_by_child:
        parent = parent_by_child[current]
        if isinstance(parent, ast.Attribute) and parent.value is current:
            current = parent
            continue
        if isinstance(parent, ast.Call) and parent.func is current:
            if (
                isinstance(current, ast.Attribute)
                and current.attr == "replace"
                and any(
                    isinstance(item, ast.Attribute) and item.attr == "inf"
                    for argument in (*parent.args, *(keyword.value for keyword in parent.keywords))
                    for item in ast.walk(argument)
                )
            ):
                return True
            current = parent
            continue
        return False
    return False


def _dropna_result_only_flows_to_nonfinite_replace(
    node: ast.Call,
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    parent_by_child: dict[ast.AST, ast.AST],
) -> bool:
    assigned_name = _assigned_name_for_call_chain(node, parent_by_child)
    if assigned_name is None:
        return False
    uses = [
        item
        for item in ast.walk(function)
        if isinstance(item, ast.Name)
        and isinstance(item.ctx, ast.Load)
        and item.id == assigned_name
        and item.lineno >= node.lineno
    ]
    return bool(uses) and all(
        _name_use_reaches_nonfinite_replace(use, parent_by_child)
        for use in uses
    )


def _raw_slice_aliases(function: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    aliases: set[str] = set()
    assignments = sorted(
        (
            node
            for node in ast.walk(function)
            if isinstance(node, (ast.Assign, ast.AnnAssign))
        ),
        key=lambda node: node.lineno,
    )
    for assignment in assignments:
        value = assignment.value
        if value is None:
            continue
        originates_from_slice = not _contains_nonfinite_replace(value) and any(
            isinstance(item, ast.Subscript)
            or isinstance(item, ast.Name) and item.id in aliases
            for item in ast.walk(value)
        )
        targets = assignment.targets if isinstance(assignment, ast.Assign) else [assignment.target]
        for target in targets:
            if not isinstance(target, ast.Name):
                continue
            if originates_from_slice:
                aliases.add(target.id)
            else:
                aliases.discard(target.id)
    return aliases


def scan_unsanitized_statistical_dropna(root: Path) -> list[str]:
    """Flag raw analytics slices that drop NaN but can still retain +/-inf."""
    findings: list[str] = []
    for path in _iter_production_python_files(root):
        relative_path = path.relative_to(root)
        relative_text = relative_path.as_posix()
        if "analytics" not in {part.lower() for part in relative_path.parts}:
            continue
        try:
            tree = ast.parse(_read_text(path), filename=str(path))
        except SyntaxError:
            continue
        seen: set[int] = set()
        for function in ast.walk(tree):
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not function.name.startswith(SPC_ENTRY_PREFIXES):
                continue
            parent_by_child = {
                child: parent
                for parent in ast.walk(function)
                for child in ast.iter_child_nodes(parent)
            }
            raw_slice_aliases = _raw_slice_aliases(function)
            for node in ast.walk(function):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                    continue
                if node.func.attr != "dropna" or node.lineno in seen:
                    continue
                source = node.func.value
                originates_from_slice = any(
                    isinstance(item, ast.Subscript)
                    or isinstance(item, ast.Name) and item.id in raw_slice_aliases
                    for item in ast.walk(source)
                )
                if not originates_from_slice:
                    continue
                if (
                    _contains_nonfinite_replace(source)
                    or _has_post_dropna_nonfinite_replace(node, parent_by_child)
                    or _dropna_result_only_flows_to_nonfinite_replace(
                        node, function, parent_by_child
                    )
                ):
                    continue
                seen.add(node.lineno)
                findings.append(
                    f"spc-unsanitized-dropna|{relative_text}:{node.lineno}|"
                    f"{function.name} drops NaN without explicit +/-inf sanitization"
                )
    return findings


def scan_root_temp_artifacts(root: Path) -> list[str]:
    findings: list[str] = []
    for path in sorted(root.iterdir(), key=lambda item: item.name.lower()):
        name = path.name
        if name == "tmp":
            continue
        if name.startswith(".tmp") or name.startswith("tmp") or name == "decompiled":
            findings.append(f"root-temp-artifact|{name}|move under tmp/")
        elif path.is_file() and name.endswith(".pyc") and name.startswith("main_window"):
            findings.append(f"root-temp-artifact|{name}|move under tmp/")
    return findings


def scan_metadata_runtime_mismatches(root: Path) -> list[str]:
    findings: list[str] = []
    pyproject_path = root / "pyproject.toml"
    readme_path = root / "README.md"
    if pyproject_path.is_file():
        pyproject_text = _read_text(pyproject_path)
        requires_python_match = re.search(r'requires-python\s*=\s*"([^"]+)"', pyproject_text)
        requires_python = requires_python_match.group(1) if requires_python_match else ""
    else:
        requires_python = ""

    if readme_path.is_file():
        readme_text = _read_text(readme_path)
        if requires_python == ">=3.12" and "Python 3.14" in readme_text:
            findings.append("metadata-runtime-mismatch|README.md|README still claims Python 3.14 is required for desktop")
        if "main_window_base.cpython-314.pyc" in readme_text:
            findings.append("metadata-runtime-mismatch|README.md|README still documents checked-in desktop bytecode as a runtime dependency")

    docs_path = root / "docs" / "outstanding-items.md"
    if docs_path.is_file():
        docs_text = _read_text(docs_path)
        if "main_window_base.cpython-314.pyc" in docs_text:
            findings.append("metadata-runtime-mismatch|docs/outstanding-items.md|Outstanding items still describe unresolved desktop bytecode coupling")

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic SPC repo quality scanner.")
    parser.add_argument("repo_root", nargs="?", default=".", help="Repository root to scan")
    parser.add_argument(
        "--inventory-spc",
        action="store_true",
        help="Print candidate SPC/statistical compute entrypoints before quality findings",
    )
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    scanners = (
        scan_source_codepoints,
        scan_bytecode_coupling,
        scan_broad_exception_handlers,
        scan_silent_chart_skips,
        scan_unsanitized_statistical_dropna,
        scan_root_temp_artifacts,
        scan_metadata_runtime_mismatches,
    )

    findings: list[str] = []
    if args.inventory_spc:
        for entry in collect_spc_statistical_entries(root):
            print(entry)
    for scanner in scanners:
        findings.extend(scanner(root))

    if findings:
        for finding in findings:
            print(finding)
        return 1

    print("OK|no-findings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
