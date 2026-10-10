from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "scan_repo_quality.py"
SPEC = importlib.util.spec_from_file_location("scan_repo_quality", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
SCANNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCANNER)


def _write_engine(repo: Path, source: str) -> None:
    path = repo / "app" / "analytics" / "example_engine.py"
    path.parent.mkdir(parents=True)
    path.write_text(source, encoding="utf-8")


def test_scanner_discovers_app_broad_exception(tmp_path: Path) -> None:
    _write_engine(
        tmp_path,
        "def compute_metric(df):\n"
        "    try:\n"
        "        return df\n"
        "    except Exception:\n"
        "        return None\n",
    )

    findings = SCANNER.scan_broad_exception_handlers(tmp_path)

    assert findings == [
        "broad-except|app/analytics/example_engine.py:4|except Exception:"
    ]


def test_scanner_flags_unsanitized_app_statistical_dropna(tmp_path: Path) -> None:
    _write_engine(
        tmp_path,
        "def compute_metric(df):\n"
        "    return df[['Volume']].dropna()\n",
    )

    findings = SCANNER.scan_unsanitized_statistical_dropna(tmp_path)

    assert findings == [
        "spc-unsanitized-dropna|app/analytics/example_engine.py:2|"
        "compute_metric drops NaN without explicit +/-inf sanitization"
    ]


def test_scanner_accepts_explicit_nonfinite_sanitization(tmp_path: Path) -> None:
    _write_engine(
        tmp_path,
        "import numpy as np\n"
        "def compute_metric(df):\n"
        "    return df[['Volume']].replace([np.inf, -np.inf], np.nan).dropna()\n",
    )

    assert SCANNER.scan_unsanitized_statistical_dropna(tmp_path) == []


def test_scanner_flags_unsanitized_slice_alias(tmp_path: Path) -> None:
    _write_engine(
        tmp_path,
        "def compute_metric(df):\n"
        "    raw = df[['Volume']]\n"
        "    return raw.dropna()\n",
    )

    findings = SCANNER.scan_unsanitized_statistical_dropna(tmp_path)

    assert findings == [
        "spc-unsanitized-dropna|app/analytics/example_engine.py:3|"
        "compute_metric drops NaN without explicit +/-inf sanitization"
    ]


def test_scanner_accepts_replace_after_dropna_in_same_return_chain(
    tmp_path: Path,
) -> None:
    _write_engine(
        tmp_path,
        "import numpy as np\n"
        "def compute_metric(df):\n"
        "    return df[['Volume']].dropna().replace([np.inf, -np.inf], np.nan)\n",
    )

    assert SCANNER.scan_unsanitized_statistical_dropna(tmp_path) == []


def test_scanner_does_not_accept_replace_in_sibling_argument(
    tmp_path: Path,
) -> None:
    _write_engine(
        tmp_path,
        "import numpy as np\n"
        "def compute_metric(df, other, combine):\n"
        "    return combine(\n"
        "        df[['Volume']].dropna(),\n"
        "        other.replace([np.inf, -np.inf], np.nan),\n"
        "    )\n",
    )

    findings = SCANNER.scan_unsanitized_statistical_dropna(tmp_path)

    assert findings == [
        "spc-unsanitized-dropna|app/analytics/example_engine.py:4|"
        "compute_metric drops NaN without explicit +/-inf sanitization"
    ]


def test_scanner_accepts_dropna_result_sanitized_through_single_alias(
    tmp_path: Path,
) -> None:
    _write_engine(
        tmp_path,
        "import numpy as np\n"
        "def compute_metric(df):\n"
        "    raw = df[['Volume']]\n"
        "    dropped = raw.dropna()\n"
        "    clean = dropped.replace([np.inf, -np.inf], np.nan)\n"
        "    return clean\n",
    )

    assert SCANNER.scan_unsanitized_statistical_dropna(tmp_path) == []


def test_scanner_accepts_multiline_sanitized_chain(tmp_path: Path) -> None:
    _write_engine(
        tmp_path,
        "import numpy as np\n"
        "def compute_metric(df):\n"
        "    return (\n"
        "        df[['Volume']]\n"
        "        .replace([np.inf, -np.inf], np.nan)\n"
        "        .dropna()\n"
        "    )\n",
    )

    assert SCANNER.scan_unsanitized_statistical_dropna(tmp_path) == []


def test_scanner_does_not_taint_alias_created_from_sanitized_slice(
    tmp_path: Path,
) -> None:
    _write_engine(
        tmp_path,
        "import numpy as np\n"
        "def compute_metric(df):\n"
        "    clean = df[['Volume']].replace([np.inf, -np.inf], np.nan).dropna()\n"
        "    grouped = clean.groupby('Volume').mean()\n"
        "    return grouped.dropna()\n",
    )

    assert SCANNER.scan_unsanitized_statistical_dropna(tmp_path) == []


def test_spc_inventory_lists_app_compute_entrypoint(tmp_path: Path) -> None:
    _write_engine(tmp_path, "def compute_metric(df):\n    return df\n")

    entries = SCANNER.collect_spc_statistical_entries(tmp_path)

    assert entries == [
        "spc-stat-entry|app/analytics/example_engine.py:1|compute_metric"
    ]
