# Engine Inventory — `spc-validation-matrix`

`app/analytics/chart_registry.py::CHART_CATALOG` is the single source of truth.
Do not preserve a hand-maintained chart count in this skill; the count drifts whenever chart IDs are added or removed.

## Inspect the Live Inventory

Run from the project root:

```powershell
.venv\Scripts\python.exe -c "from app.analytics.chart_registry import CHART_CATALOG; print(len(CHART_CATALOG)); print([e['id'] for e in CHART_CATALOG])"
```

The matrix runner uses `scripts/matrix_builder.py::list_engines()` at runtime, so new chart IDs are included automatically when `CHART_CATALOG` is updated.

## Arity Compatibility

Compatibility is computed at runtime:

```text
chart_id in MULTI_FEATURE_FAMILIES -> arity >= 1
chart_id in DUAL_AT_LEAST_TWO      -> arity >= 2
otherwise                          -> arity == required_feature_count
```

Keep this aligned with `chart_registry.is_chart_available_for_selection()`.
If a chart is exactly 2F, do not document it as `>=2`; a mismatch here can make reports count a chart as available while the resolver returns invalid.

## Known Matrix Boundaries

- Fixtures without coordinates make `spatial_heatmap` invalid or skipped by design.
- Fixtures without `PartType` can make `pareto`, `pass_fail_matrix`, or `anova_parttype` invalid; this can still be contract-correct.
- Fixtures without `BoardNo`/`PanelId` make trend charts fall back to index order.
