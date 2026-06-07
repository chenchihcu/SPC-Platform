"""CLI entry: run the SPC cross-validation matrix.

Usage (from project root)::

    python .claude/skills/spc-validation-matrix/scripts/run_matrix.py \\
        [--fixture normal_baseline] \\
        [--engines imr,histogram_spec,...] \\
        [--features Volume,Area,Height] \\
        [--filters full,top10pct,by_part_type] \\
        [--arities 1,2,3] \\
        [--output Outputs/cross_validation_<timestamp>] \\
        [--skip-export] [--quick]

Defaults to ``normal_baseline`` × all engines × full feature/filter/arity coverage.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

# Make project root + scripts dir importable regardless of CWD
SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPTS_DIR.parents[3]  # .claude/skills/spc-validation-matrix/scripts -> project root
for _p in (str(PROJECT_ROOT), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Flat-import siblings (after sys.path setup)
from engine_invoker import (  # noqa: E402
    apply_filter,
    check_contract_and_stats,
    check_data_renderability,
    compute_payload_for_cell,
    load_fixture,
    resolve_slice_for_cell,
)
from export_validator import export_pptx, export_xlsx  # noqa: E402
from matrix_builder import (  # noqa: E402
    DEFAULT_ARITIES,
    DEFAULT_FEATURES,
    DEFAULT_FILTERS,
    Cell,
    build_matrix,
    list_engines,
)
from perf_monitor import run_with_watchdog  # noqa: E402
from report_writer import (  # noqa: E402
    write_failure_artifact,
    write_matrix_csv,
    write_summary_md,
)


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


THRESHOLD_PER_ENGINE_S = _env_float("SPC_VALIDATION_ENGINE_TIMEOUT_S", 30.0)
THRESHOLD_PEAK_MB = _env_float("SPC_VALIDATION_ENGINE_PEAK_MB", 2048.0)
THRESHOLD_MATRIX_TIMEOUT_S = _env_float("SPC_VALIDATION_MATRIX_TIMEOUT_S", 600.0)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SPC cross-validation matrix runner.")
    parser.add_argument("--fixture", default="normal_baseline")
    parser.add_argument(
        "--fixtures",
        default=None,
        help="Comma-separated list. Overrides --fixture if given.",
    )
    parser.add_argument("--engines", default=None, help="Comma-separated chart_ids.")
    parser.add_argument(
        "--features",
        default=",".join(DEFAULT_FEATURES),
        help=f"Comma-separated. Default: {','.join(DEFAULT_FEATURES)}",
    )
    parser.add_argument(
        "--filters",
        default=",".join(DEFAULT_FILTERS),
        help=f"Comma-separated. Default: {','.join(DEFAULT_FILTERS)}",
    )
    parser.add_argument(
        "--arities",
        default=",".join(str(a) for a in DEFAULT_ARITIES),
        help="Comma-separated subset of 1,2,3.",
    )
    parser.add_argument("--output", default=None, help="Output directory.")
    parser.add_argument(
        "--skip-export",
        action="store_true",
        help="Skip PPTX/XLSX export validation.",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Reduced sweep: filters=full, arities=1,2 (~smaller cell count).",
    )
    return parser.parse_args(argv)


def _ensure_output_dir(arg_output: str | None) -> Path:
    if arg_output:
        out = Path(arg_output)
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        out = PROJECT_ROOT / "Outputs" / f"cross_validation_{ts}"
    out.mkdir(parents=True, exist_ok=True)
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    fixtures = (
        [s.strip() for s in args.fixtures.split(",") if s.strip()]
        if args.fixtures
        else [args.fixture]
    )
    features = [s.strip() for s in args.features.split(",") if s.strip()]
    filters = (
        ["full"] if args.quick else [s.strip() for s in args.filters.split(",") if s.strip()]
    )
    arities = (
        [1, 2] if args.quick else [int(s) for s in args.arities.split(",") if s.strip()]
    )
    engines = (
        [s.strip() for s in args.engines.split(",") if s.strip()]
        if args.engines
        else list_engines()
    )

    output_dir = _ensure_output_dir(args.output)
    print(f"[spc-validation-matrix] output → {output_dir}", flush=True)
    print(
        f"[spc-validation-matrix] fixtures={fixtures} arities={arities} "
        f"features={features} filters={filters} engines={len(engines)}",
        flush=True,
    )
    print(
        f"[spc-validation-matrix] timeouts: per_cell={THRESHOLD_PER_ENGINE_S}s "
        f"peak={THRESHOLD_PEAK_MB}MB matrix={THRESHOLD_MATRIX_TIMEOUT_S}s",
        flush=True,
    )

    cells = build_matrix(fixtures, arities, features, filters, engines)
    print(f"[spc-validation-matrix] built {len(cells)} cells", flush=True)

    rows: list[dict[str, object]] = []
    payload_cache: dict[tuple[str, tuple[str, ...], str], object] = {}
    spec_by_fixture: dict[str, dict[str, object]] = {}
    df_by_fixture: dict[str, object] = {}
    # Pin one (fixture, arity) → (features, filter) for export validation; chart_ids accumulate
    # only from the same (features, filter) so they all resolve in the saved payload.
    payload_for_export: dict[
        tuple[str, int],
        dict[str, object],
    ] = {}

    golden_root = PROJECT_ROOT / "golden_dataset"
    wall_t0 = time.perf_counter()

    for cell in cells:
        if (time.perf_counter() - wall_t0) > THRESHOLD_MATRIX_TIMEOUT_S:
            rows.append(_skip_row(cell, "matrix wall-clock budget exhausted"))
            continue

        # --- load fixture once
        if cell.fixture not in df_by_fixture:
            try:
                df, spec = load_fixture(golden_root, cell.fixture)
            except BaseException as exc:
                rows.append(_skip_row(cell, f"load_fixture: {type(exc).__name__}: {exc}"))
                continue
            df_by_fixture[cell.fixture] = df
            spec_by_fixture[cell.fixture] = spec
        df = df_by_fixture[cell.fixture]
        spec = spec_by_fixture[cell.fixture]

        # Skip cells whose primary feature isn't in the joined frame
        if cell.features and cell.features[0] not in getattr(df, "columns", []):
            rows.append(_skip_row(cell, f"feature '{cell.features[0]}' not in fixture"))
            continue

        # --- compute or reuse payload
        cache_key = (cell.fixture, cell.features, cell.filter_name)
        if cache_key not in payload_cache:
            filtered_df = apply_filter(df, cell.filter_name, cell.features[0])
            outcome = run_with_watchdog(
                compute_payload_for_cell,
                filtered_df,
                list(cell.features),
                spec,
                timeout_s=THRESHOLD_PER_ENGINE_S * 5.0,
                peak_mb_limit=THRESHOLD_PEAK_MB,
            )
            if outcome.status in ("STALL", "OVERLOAD"):
                payload_cache[cache_key] = outcome
            elif outcome.status == "ERROR":
                payload_cache[cache_key] = outcome
            else:
                payload_obj, payload_err = outcome.result  # type: ignore[misc]
                if payload_obj is None:
                    payload_cache[cache_key] = outcome  # treat as ERROR-ish
                    outcome.status = "ERROR"
                    outcome.error = payload_err or outcome.error or "no payload"
                else:
                    payload_cache[cache_key] = (outcome, payload_obj)
                    # Stash one payload per (fixture, arity) for export validation;
                    # only accumulate chart_ids that share the chosen (features, filter)
                    # so they all resolve in this exact payload.
                    export_key = (cell.fixture, cell.arity)
                    if export_key not in payload_for_export:
                        payload_for_export[export_key] = {
                            "payload": payload_obj,
                            "spec": spec,
                            "key": (cell.features, cell.filter_name),
                            "chart_ids": [cell.chart_id],
                        }
                    elif payload_for_export[export_key]["key"] == (
                        cell.features, cell.filter_name
                    ):
                        ids = payload_for_export[export_key]["chart_ids"]  # type: ignore[index]
                        if cell.chart_id not in ids:  # type: ignore[operator]
                            ids.append(cell.chart_id)  # type: ignore[union-attr]

        payload_entry = payload_cache[cache_key]
        if not isinstance(payload_entry, tuple):
            outcome = payload_entry
            rows.append(_outcome_row(cell, outcome))
            continue

        outcome, payload_obj = payload_entry
        # --- resolve slice + check contract + render
        try:
            slice_dict = resolve_slice_for_cell(payload_obj, cell.chart_id, list(cell.features))
        except BaseException as exc:
            rows.append(
                _row(
                    cell,
                    status="ERROR",
                    duration_ms=int(outcome.duration_s * 1000),
                    peak_mb=round(outcome.peak_mb, 1),
                    contract_ok=False,
                    stats_ok=False,
                    chart_render_ok=False,
                    error=f"resolve: {type(exc).__name__}: {exc}",
                )
            )
            write_failure_artifact(
                _row_to_dict(cell), {}, traceback.format_exc(), output_dir
            )
            continue

        contract_ok, stats_ok, contract_err = check_contract_and_stats(slice_dict)
        render_ok, render_err = check_data_renderability(slice_dict)
        all_ok = contract_ok and stats_ok and render_ok
        status = "PASS" if all_ok else "FAIL"
        err = contract_err or render_err
        if not all_ok:
            write_failure_artifact(_row_to_dict(cell), slice_dict, "", output_dir)

        rows.append(
            _row(
                cell,
                status=status,
                duration_ms=int(outcome.duration_s * 1000),
                peak_mb=round(outcome.peak_mb, 1),
                contract_ok=contract_ok,
                stats_ok=stats_ok,
                chart_render_ok=render_ok,
                error=err,
            )
        )

    # --- export validation phase (per fixture × arity, scoped to chosen (features,filter))
    if not args.skip_export:
        exports_dir = output_dir / "exports"
        for (fixture, arity), info in payload_for_export.items():
            payload_obj = info["payload"]  # type: ignore[assignment]
            spec_e = info["spec"]  # type: ignore[assignment]
            chosen_features, chosen_filter = info["key"]  # type: ignore[misc]
            chart_ids = info["chart_ids"]  # type: ignore[assignment]
            features_str = "+".join(chosen_features)  # type: ignore[arg-type]
            pptx_path = exports_dir / f"{fixture}__{arity}f__{features_str}__{chosen_filter}.pptx"
            xlsx_path = exports_dir / f"{fixture}__{arity}f__{features_str}__{chosen_filter}.xlsx"
            ok_p, err_p = export_pptx(payload_obj, spec_e, pptx_path, chart_ids)  # type: ignore[arg-type]
            ok_x, err_x = export_xlsx(payload_obj, xlsx_path)  # type: ignore[arg-type]
            export_ok = ok_p and ok_x
            export_err = "; ".join(filter(None, [err_p, err_x]))

            for row in rows:
                if (
                    row["fixture"] == fixture
                    and row["arity"] == arity
                    and row["features"] == features_str
                    and row["filter"] == chosen_filter
                ):
                    row["export_ok"] = export_ok
                    if not export_ok and not row.get("error"):
                        row["error"] = f"export: {export_err}"
                    if not export_ok and row["status"] == "PASS":
                        row["status"] = "FAIL"

    wall_clock = time.perf_counter() - wall_t0
    csv_path = write_matrix_csv(rows, output_dir)
    md_path = write_summary_md(rows, output_dir, wall_clock)

    print(f"[spc-validation-matrix] wrote {csv_path}", flush=True)
    print(f"[spc-validation-matrix] wrote {md_path}", flush=True)
    print(f"[spc-validation-matrix] wall-clock: {wall_clock:.1f}s", flush=True)
    return 0


def _row(
    cell: Cell,
    *,
    status: str,
    duration_ms: int,
    peak_mb: float,
    contract_ok: bool = False,
    stats_ok: bool = False,
    chart_render_ok: bool = False,
    error: str = "",
) -> dict[str, object]:
    return {
        "fixture": cell.fixture,
        "arity": cell.arity,
        "features": cell.features_str(),
        "chart_id": cell.chart_id,
        "filter": cell.filter_name,
        "status": status,
        "duration_ms": duration_ms,
        "peak_mb": peak_mb,
        "contract_ok": contract_ok,
        "stats_ok": stats_ok,
        "chart_render_ok": chart_render_ok,
        "export_ok": "",
        "error": error,
    }


def _row_to_dict(cell: Cell) -> dict[str, object]:
    return {
        "fixture": cell.fixture,
        "arity": cell.arity,
        "features": cell.features_str(),
        "features_list": list(cell.features),
        "chart_id": cell.chart_id,
        "filter": cell.filter_name,
    }


def _skip_row(cell: Cell, reason: str) -> dict[str, object]:
    return _row(
        cell,
        status="SKIP",
        duration_ms=0,
        peak_mb=0.0,
        contract_ok=False,
        stats_ok=False,
        chart_render_ok=False,
        error=reason,
    )


def _outcome_row(cell: Cell, outcome) -> dict[str, object]:  # type: ignore[no-untyped-def]
    return _row(
        cell,
        status=outcome.status,
        duration_ms=int(outcome.duration_s * 1000),
        peak_mb=round(outcome.peak_mb, 1),
        contract_ok=False,
        stats_ok=False,
        chart_render_ok=False,
        error=outcome.error,
    )


if __name__ == "__main__":
    raise SystemExit(main())
