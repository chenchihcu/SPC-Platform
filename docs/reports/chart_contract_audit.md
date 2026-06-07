# Chart Contract Audit

This document records contract alignment across:

- Registry contracts in `app/analytics/chart_registry.py`
- Analysis payload assembly in `app/viewmodels/chart_analysis_viewmodel.py` (`compute_analysis_payload`)
- Analytics modules: `app/analytics/*_engine.py`, `analysis_cards_engine.py`, `summary_engine.py`, `normality_engine.py`, and shared helpers (`statistical_utils.py`, `ooc_utils.py`, etc.)
- Chart rendering in `app/charts/*_chart.py`
- Reference table in `app/ui/pages/data_management_page.py`

Decision baseline:

1. `docs/governance/SPC_RULES.md`
2. NIST / ISO / AIAG references
3. Engine implementation
4. UI text and reference descriptions

**治理與變更流程**：契約／計畫／程式三者如何對齊、何時必須先更新規格再改碼，見 **`docs/specs/spec_maintenance_and_alignment.md`**（尤其 §1、§5、§6）。

## High-risk mismatches (implemented)

1. `bivariate_outlier`
   - Issue: Description referenced Mahalanobis/robust covariance semantics while implementation was axis-wise IQR OR rule.
   - Risk: Users may interpret marginal-threshold outliers as multivariate distance outliers.
   - Action: Upgrade engine to multivariate distance and align chart/description.

2. `pareto`
   - Issue: No-spec path used hardcoded thresholds tied to legacy percentage scale.
   - Risk: Misclassification under mixed units and non-percentage scales.
   - Action: Require spec/control limits for standard classification; return explicit non-computable state otherwise.

3. `cusum`
   - Issue: Target fallback to data mean was implicit when target/spec midpoint deviated strongly.
   - Risk: Monitoring objective silently shifts from engineering target to sample mean.
   - Action: Expose fallback metadata and render fallback annotation in chart.

## Medium-risk mismatches (implemented)

1. `pass_fail_matrix`
   - Issue: Name/description used matrix semantics while chart renders pass-rate summary bars.
   - Action: Align naming/description to summary semantics.

2. `anomaly_3f`
   - Issue: Description implied model variants (e.g. isolation forest) while implementation uses mean absolute z-score.
   - Action: Align formula text to implemented method.

3. Feature badges vs required feature count
   - Issue: Specific chart badges drifted from registry required feature count.
   - Action: Add contract tests for shared IDs and align reference badges.

## Verification status (2026-04-02)

The above contract actions are now reflected in code and regression tests:

- `tests/test_bivariate_outlier_engine.py`
- `tests/test_pareto_engine.py`
- `tests/test_cusum_engine.py`
- `tests/test_chart_contract_alignment.py`

## Sample-integrity convergence (2026-04-02)

Owner escalation required a full sweep of "partial sample display" distortion paths.
The following contract actions are now implemented and regression-protected:

1. `run_chart`
   - Prior risk: large-N display downsampling could show only a subset.
   - Action: default full-data display (`displayed_n == n`, `sampled_for_display=False`).
   - Verification: `tests/test_run_chart_engine.py`, `tests/test_chart_performance_baseline.py`.

2. `parallel_coord`
   - Prior risk: fixed `max_points=500` random sampling could distort visible population.
   - Action: default full-data display; keep `max_points` for backward-compatible signature only.
   - Verification: `tests/test_parallel_coord_engine.py`, `tests/test_chart_performance_baseline.py`.

3. `normality`
   - Prior risk: `N>5000` used sampled Shapiro test (`tested_n < total_n`).
   - Action: full-data testing path for large-N with explicit `test_name`, `tested_n`, `total_n`.
   - Verification: `tests/test_normality_engine.py`, `tests/test_chart_sample_integrity.py`.

4. `spatial_heatmap`
   - Prior risk: grid aggregation not transparently disclosed to chart/report consumers.
   - Action: expose `n/displayed_n/sampled_for_display/sampling_method/aggregation_bins` and on-chart aggregation annotation.
   - Verification: `tests/test_spatial_engine_sampling.py`, `tests/test_chart_sample_integrity.py`.

5. `repeated_offender`
   - Prior risk: implicit default `top_n=20` truncated offender ranking.
   - Action: default full ranking (no implicit truncation); if `top_n` is requested, truncation is metadata-visible and chart-annotated.
   - Verification: `tests/test_repeated_offender_engine.py`, `tests/test_chart_sample_integrity.py`.

## Deliverables linked to this audit

- Engine changes:
  - `app/analytics/bivariate_outlier_engine.py`
  - `app/analytics/pareto_engine.py`
  - `app/analytics/cusum_engine.py`
- Chart/UI text changes:
  - `app/charts/bivariate_outlier_chart.py`
  - `app/charts/cusum_chart.py`
  - `app/analytics/chart_registry.py`
  - `app/ui/pages/data_management_page.py`
- Tests:
  - `tests/test_bivariate_outlier_engine.py`
  - `tests/test_pareto_engine.py`
  - `tests/test_cusum_engine.py`
  - `tests/test_chart_contract_alignment.py`
