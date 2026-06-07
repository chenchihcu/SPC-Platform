#!/usr/bin/env python3
"""
Import SPI_製程對應知識庫_v1.0.xlsx into data/spi_process_kb/v1/*.json

The **reference workbook** for v1 is ``SPI_製程對應知識庫_v1.0.xlsx`` (see
``app.services.spi_process_kb_loader.CANONICAL_SPI_KB_WORKBOOK_BASENAME``).

Requires: pandas, openpyxl (see docs/reference/requirements.txt)

Example:
  python scripts/import_spi_process_kb_xlsx.py path/to/SPI_製程對應知識庫_v1.0.xlsx \\
    --out data/spi_process_kb/v1
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from zipfile import BadZipFile

try:
    from scripts.repo_bootstrap import ensure_repo_root_on_sys_path
except ImportError:  # pragma: no cover - script entry fallback
    from repo_bootstrap import ensure_repo_root_on_sys_path

# Deterministic source-tree bootstrap for script execution and test imports.
_REPO_ROOT = ensure_repo_root_on_sys_path(Path(__file__).resolve().parents[1])

from app.services.spi_process_kb_loader import CANONICAL_SPI_KB_WORKBOOK_BASENAME
from app.utils.io_utils import atomic_save_json, atomic_save_text

_SHEET_READ_EXCEPTIONS = (FileNotFoundError, OSError, ValueError, KeyError, BadZipFile)


def _parse_star_rating(raw: Any) -> int:
    if isinstance(raw, str) and raw.count("★"):
        return min(5, raw.count("★"))
    try:
        return int(float(raw)) if raw else 3
    except ValueError:
        return 3


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_sheet(
    xlsx: Path,
    sheet: str,
    *,
    header: int = 0,
) -> Any:
    import pandas as pd

    return pd.read_excel(xlsx, sheet_name=sheet, engine="openpyxl", header=header)


def import_multi_signal_rules(df: Any) -> List[Dict[str, Any]]:
    """Expect columns aligned with KB export (English or Chinese)."""
    rows: List[Dict[str, Any]] = []
    col = {str(c).strip(): c for c in df.columns}

    def col_get(r: Any, *names: str) -> str:
        for n in names:
            if n in col:
                v = r[col[n]]
                if v is None or (isinstance(v, float) and str(v) == "nan"):
                    return ""
                return str(v).strip()
        return ""

    def col_get_list(r: Any, *names: str) -> List[str]:
        raw = col_get(r, *names)
        if not raw:
            return []
        parts = [p.strip() for p in raw.replace("；", ";").split(";") if p.strip()]
        if len(parts) <= 1:
            parts = [p.strip() for p in raw.split("\n") if p.strip()]
        return parts

    for _, r in df.iterrows():
        rid = col_get(r, "rule_id", "規則 ID", "規則ID")
        if not rid:
            continue
        ch = col_get_list(
            r,
            "cause_hypotheses",
            "製程原因假說（優先順序）",
            "製程原因假說(優先順序)",
            "製程原因假說",
        )
        stars_raw = col_get(r, "confidence_stars", "信心度")
        stars = _parse_star_rating(stars_raw)
        rows.append(
            {
                "rule_id": rid,
                "signal_a": col_get(r, "signal_a", "訊號 A（主訊號）", "訊號 A (主訊號)", "訊號A"),
                "signal_b": col_get(r, "signal_b", "訊號 B（輔訊號）", "訊號 B (輔訊號)", "訊號B"),
                "spatial_temporal_condition": col_get(
                    r, "spatial_temporal_condition", "空間/時間條件"
                ),
                "trigger_description": col_get(
                    r, "trigger_description", "觸發條件說明"
                ),
                "process_type_classification": col_get(
                    r, "process_type_classification", "製程型態分類"
                ),
                "cause_hypotheses": ch or ["(import: please fill causes)"],
                "confidence_stars": max(1, min(5, stars)),
                "priority_inspection_items": col_get(
                    r, "priority_inspection_items", "優先檢查項目"
                ),
            }
        )
    return rows


def import_dimension_matrix(df: Any) -> List[Dict[str, Any]]:
    import re as _re

    col = {str(c).strip(): c for c in df.columns}
    rows: List[Dict[str, Any]] = []

    def g(r: Any, *names: str) -> str:
        for n in names:
            if n in col:
                v = r[col[n]]
                if v is None or (isinstance(v, float) and str(v) == "nan"):
                    return ""
                s = str(v).replace("\n", " ").strip()
                return "" if s == "—" else s
        return ""

    def _dim_key(raw: str) -> str:
        """Normalize 'Volume （錫膏體積）' or 'Volume\n（錫膏體積）' → 'Volume'."""
        # g() already replaces \n with space; split on first space or fullwidth paren
        return _re.split(r"[（\s\n]", raw)[0].strip()

    def _abn_key(raw: str) -> str:
        """Normalize 'Drift（漸進）'→'Drift', 'Shift↓（面積縮小）'→'Shift', 'Non-normal （非常態）'→'Non-normal'."""
        return _re.split(r"[（↓↑\s\n]", raw)[0].strip()

    for _, r in df.iterrows():
        dim_raw = g(r, "spi_dimension", "SPI 量測維度", "量測維度")
        abn_raw = g(r, "abnormality_type", "異常型態")
        if not dim_raw or not abn_raw:
            continue
        rows.append(
            {
                "spi_dimension": _dim_key(dim_raw),
                "abnormality_type": _abn_key(abn_raw),
                "stencil": g(r, "stencil", "Stencil（鋼板）", "Stencil", "鋼板"),
                "squeegee": g(r, "squeegee", "Squeegee（刮刀）", "Squeegee", "刮刀"),
                "paste": g(r, "paste", "Paste（錫膏）", "Paste", "錫膏"),
                "pcb_pad": g(r, "pcb_pad", "PCB / Pad", "PCB/Pad"),
                "alignment": g(r, "alignment", "Alignment（對位）", "Alignment", "對位"),
                "environment": g(r, "environment", "Environment（環境）", "Environment", "環境"),
            }
        )
    return rows


def import_inspection_checklist(df: Any) -> List[Dict[str, Any]]:
    col = {str(c).strip(): c for c in df.columns}
    rows: List[Dict[str, Any]] = []

    def g(r: Any, *names: str) -> str:
        for n in names:
            if n in col:
                v = r[col[n]]
                if v is None or (isinstance(v, float) and str(v) == "nan"):
                    return ""
                return str(v).strip()
        return ""

    for _, r in df.iterrows():
        cat = g(r, "process_category", "製程類別")
        # Normalize multi-line cell: '🔲 Stencil\n（鋼板）' → '🔲 Stencil（鋼板）'
        cat = cat.replace("\n", "").strip()
        item = g(r, "inspection_item", "檢查項目")
        if not cat or not item:
            continue
        pr = g(r, "priority_stars", "優先順序")
        stars = _parse_star_rating(pr)
        rows.append(
            {
                "process_category": cat,
                "inspection_item": item,
                "measurement_method": g(r, "measurement_method", "量測/確認方法"),
                "normal_threshold": g(r, "normal_threshold", "正常門檻值"),
                "priority_stars": max(1, min(5, stars)),
                "remarks": g(r, "remarks", "備註"),
            }
        )
    return rows


def import_chart_lookup(df: Any) -> List[Dict[str, Any]]:
    col = {str(c).strip(): c for c in df.columns}
    rows: List[Dict[str, Any]] = []

    def g(r: Any, *names: str) -> str:
        for n in names:
            if n in col:
                v = r[col[n]]
                if v is None or (isinstance(v, float) and str(v) == "nan"):
                    return ""
                return str(v).strip()
        return ""

    for _, r in df.iterrows():
        ct = g(r, "chart_type", "圖表類型")
        obs = g(r, "observed_signal", "觀察到的異常訊號")
        if not ct or not obs:
            continue
        rid_raw = g(r, "rule_ids", "對應規則 ID", "對應規則ID")
        rule_ids: List[str] = []
        for part in rid_raw.replace(",", " ").replace(";", " ").replace("/", " ").split():
            part = part.strip()
            if part.upper().startswith("R"):
                rule_ids.append(part.upper().replace("R", "R").replace("r", "R"))
        if rule_ids and not rule_ids[0].startswith("R"):
            rule_ids = [f"R{x}" if x.isdigit() else x for x in rule_ids]
        rows.append(
            {
                "chart_type": ct,
                "observed_signal": obs,
                "likely_cause_1": g(r, "likely_cause_1", "最可能原因 #1", "最可能原因#1"),
                "likely_cause_2": g(r, "likely_cause_2", "最可能原因 #2", "最可能原因#2"),
                "likely_cause_3": g(r, "likely_cause_3", "最可能原因 #3", "最可能原因#3"),
                "rule_ids": rule_ids or ["R000"],
                "process_type": g(r, "process_type", "製程型態"),
                "urgency": g(r, "urgency", "緊急程度"),
            }
        )
    return rows


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Import SPI process KB xlsx to JSON bundle.")
    p.add_argument(
        "xlsx",
        type=Path,
        help=f"Path to workbook (canonical name: {CANONICAL_SPI_KB_WORKBOOK_BASENAME})",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=_REPO_ROOT / "data" / "spi_process_kb" / "v1",
        help="Output directory for JSON files",
    )
    # v1.0 workbook (repo-root SPI_製程對應知識庫_v1.0.xlsx) uses emoji-prefixed sheet
    # names and a title row; use --header-row 0 with legacy sheet names if needed.
    p.add_argument(
        "--sheet-rules",
        default="🔗 多訊號關聯規則",
        help="Sheet name for multi-signal rules (legacy: 多訊號關聯診斷規則表)",
    )
    p.add_argument(
        "--sheet-matrix",
        default="📊 訊號×異常×原因",
        help="Sheet for dimension matrix (legacy: 三維對應表)",
    )
    p.add_argument(
        "--sheet-checklist",
        default="🔧 製程原因檢查清單",
        help="Sheet for inspection checklist (legacy: 檢查項目門檻)",
    )
    p.add_argument(
        "--sheet-chart",
        default="⚡ 訊號速查矩陣",
        help="Sheet for chart lookup (legacy: 圖表速查矩陣)",
    )
    p.add_argument(
        "--header-row",
        type=int,
        default=1,
        help="0-based pandas header row index (1 = skip one title row; legacy flat sheets: 0)",
    )
    args = p.parse_args(argv)

    if not args.xlsx.is_file():
        print(f"error: file not found: {args.xlsx}", file=sys.stderr)
        return 2

    try:
        import pandas as pd  # noqa: F401
    except ImportError:
        print("error: pandas is required", file=sys.stderr)
        return 2

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    report_lines: List[str] = []

    sha = _sha256(args.xlsx)

    required_sheet_failures: List[str] = []

    def safe_read(sheet: str) -> Any:
        try:
            return _read_sheet(args.xlsx, sheet, header=args.header_row)
        except _SHEET_READ_EXCEPTIONS as e:
            report_lines.append(f"sheet_missing_or_error:{sheet}:{e}")
            required_sheet_failures.append(sheet)
            return None

    bundles: Dict[str, Any] = {}

    df_rules = safe_read(args.sheet_rules)
    if df_rules is not None:
        rules = import_multi_signal_rules(df_rules)
        bundles["multi_signal_rules"] = {"entries": rules}
        report_lines.append(f"multi_signal_rules:{len(rules)}_rows")

    df_mat = safe_read(args.sheet_matrix)
    if df_mat is not None:
        mat = import_dimension_matrix(df_mat)
        bundles["dimension_abnormality_matrix"] = {"entries": mat}
        report_lines.append(f"dimension_matrix:{len(mat)}_rows")

    df_chk = safe_read(args.sheet_checklist)
    if df_chk is not None:
        chk = import_inspection_checklist(df_chk)
        bundles["inspection_checklist"] = {"entries": chk}
        report_lines.append(f"inspection_checklist:{len(chk)}_rows")

    df_chart = safe_read(args.sheet_chart)
    if df_chart is not None:
        cl = import_chart_lookup(df_chart)
        bundles["chart_signal_lookup"] = {"entries": cl}
        report_lines.append(f"chart_signal_lookup:{len(cl)}_rows")

    for name, payload in bundles.items():
        path = out / f"{name}.json"
        if not atomic_save_json(str(path), payload, indent=2):
            print(f"error: failed to write {path}", file=sys.stderr)
            return 1

    manifest = {
        "schema_version": "1.0.0",
        "kb_version": "v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_xlsx_basename": args.xlsx.name,
        "canonical_workbook_basename": CANONICAL_SPI_KB_WORKBOOK_BASENAME,
        "source_xlsx_sha256": sha,
        "import_report": report_lines,
        "description": (
            "SPI process knowledge base bundle; authoritative Excel: "
            + CANONICAL_SPI_KB_WORKBOOK_BASENAME
        ),
    }
    manifest_path = out / "manifest.json"
    if not atomic_save_json(str(manifest_path), manifest, indent=2):
        print(f"error: failed to write {manifest_path}", file=sys.stderr)
        return 1

    report_path = out / "import_report.txt"
    if not atomic_save_text(str(report_path), "\n".join(report_lines) + "\n"):
        print(f"error: failed to write {report_path}", file=sys.stderr)
        return 1

    if required_sheet_failures:
        missing = ",".join(required_sheet_failures)
        print(
            f"error: required sheets failed to load: {missing}",
            file=sys.stderr,
        )
        return 1

    print(f"Wrote bundle to {out}")
    print("\n".join(report_lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
