---
name: spc-db-chart-semantics-validator
description: "用真實 SQLite session、量測/座標檔與 active spec 驗證 SPC 圖表統計語意。Use when 在本 repo 檢查圖表統計值、修正 chart payload/registry/resolver 或 density/dual/triple feature 語意。Do NOT use for 組合式矩陣掃描（改用 spc-validation-matrix）、通用 schema（改用 design-database-schema）或 analytics 引擎契約（改用 analytics-engine-contract）。"
---

# SPC DB Chart Semantics Validator

Use this skill when chart output correctness matters more than contract/renderability alone.

## Gate

Run from the project root:

```powershell
.venv\Scripts\python.exe scripts\validate_db_chart_semantics.py --db data\spc_master.db --latest-session --output Outputs\db_chart_semantics_current --quiet
```

When a specific real session is known, prefer exact replay:

```powershell
.venv\Scripts\python.exe scripts\validate_db_chart_semantics.py --db data\spc_master.db --session-id <id> --output Outputs\db_chart_semantics_current --quiet
```

The script opens SQLite with URI read-only mode plus `PRAGMA query_only=ON`, loads the measurement file, active coordinate file, and active paste/stencil specs, joins with `JoinEngine`, computes payloads through `compute_analysis_payload`, resolves chart slices through `chart_registry.resolve_chart_payload`, and writes `summary.json` below `Outputs/`. Output paths outside `Outputs/` are rejected. Setup/runtime failures write an `ERROR` summary and return exit code 2.

## What This Catches

- Chart availability says a chart is usable but resolver returns invalid.
- Single-feature SPC/capability/run/EWMA/CUSUM/spatial statistics drift from joined dataframe recomputation.
- Dual-feature precomputed pair payloads are missing or numerically inconsistent.
- Density mode regresses from the required `1F=univariate`, `2F=bivariate`, or `3F=multi_feature_univariate` semantics.
- Triple-feature semantics drift, including `consistency_3f` denominator filtering, pointwise Hotelling T²/UCL/OOC checks, and Radar group-mean recomputation.
- Deterministic LISA local-I/z-score/lag semantics drift; Monte Carlo p-values are checked for contract and derived classification consistency rather than exact equality.

## Non-Negotiable Rules

- Do not treat payload contract PASS or chart renderability PASS as proof of statistical correctness.
- Independently recompute expected values from the joined dataframe; do not compare one engine output to another engine output.
- Before aggregation, sanitize `np.inf` and `-np.inf` with `.replace([np.inf, -np.inf], np.nan).dropna()`.
- Respect each engine's sample definition. Example: trend/SPC statistics use the analysis order selected by `detect_order_col`; `consistency_3f` removes non-positive ratio inputs.
- Do not change SPC formulas, constants, or thresholds to make the gate pass.

## Interpreting Failures

- `available_resolver_mismatch_count > 0`: inspect `chart_registry.is_chart_available_for_selection`, chart catalog `required_feature_count`, and resolver fallback behavior.
- `pair_expansion_failure_count > 0`: inspect `payload["dual_parameters"]`, pair key ordering, and resolver support for feature pairs.
- `statistical_semantic_failure_count > 0`: compare the named check to the engine's documented valid-sample and ordering definition before changing code.

Finish by recording whether this gate should become part of the route for the changed surface.
# Selected semantic checks

Use `--checks resolver,single,pair,three,density` as one comma-separated selector. Default `all` preserves the full gate; choose only invalidated groups for V1/V2.
