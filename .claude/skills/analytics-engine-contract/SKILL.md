---
name: analytics-engine-contract
version: 1.0.0
description: 分析引擎契約 — 定義本專案所有 analytics engine(SPCEngine、CapabilityEngine、NormalityEngine 等)共通的回傳結構、guard 模式與測試慣例。Use this skill 當使用者要新增 engine、檢查 engine 回傳值、為 engine 撰寫測試,或除錯 is_valid / chart_type / metadata 欄位。觸發詞包含「engine」「analytics 契約」「is_valid」「chart_type」「statistics」「metadata」「return structure」。
---

# Analytics Engine Contract — Universal Skill

Defines the standard return structure, guard pattern, and testing conventions for all analytics engines in this project. Every engine (`SPCEngine`, `CapabilityEngine`, `NormalityEngine`, etc.) follows this contract. Use this when adding a new engine or verifying an existing one.

## When to Use

- Adding a new analytics computation engine
- Reviewing or debugging an engine's return value
- Writing tests for any analytics engine
- Keywords: engine, compute, is_valid, chart_type, analytics, statistics, metadata

---

## Standard Return Structure

Every engine method returns exactly this shape:

```python
{
    "chart_type": str,          # e.g. "I-MR", "Capability", "Normality"
    "data":       dict,         # chart-renderable arrays/values; {} on failure
    "statistics": dict,         # computed metrics (mean, ucl, lcl, cpk…); {} on failure
    "metadata": {
        "is_valid": bool,       # True = render chart; False = show placeholder
        "error":    str,        # "" on success; human-readable message on failure
        # optional extra keys (e.g. target_col, usl, lsl, risk_level)
    }
}
```

**Rules:**
- `is_valid=False` → `data` and `statistics` MUST be `{}` (never partial)
- `is_valid=True` → `error` MUST be `""` (never leave a stale message)
- `chart_type` is always the first key and never changes per engine

---

## Standard Guard Pattern

All engines use the same three-layer guard before computation:

```python
@staticmethod
def compute_xxx(data: pd.Series, ...) -> Dict[str, Any]:

    # Guard 1 — SPC validity (N >= 10, sigma > 0)
    is_valid, msg = StatisticalUtils.is_valid_for_spc(data)
    if not is_valid:
        return _invalid("ChartType", msg)

    # Guard 2 — Required parameters (e.g. USL/LSL)
    if usl is None or lsl is None:
        return _invalid("ChartType", "Missing USL or LSL.")

    # Guard 3 — Degenerate inputs (e.g. USL == LSL)
    if usl == lsl:
        return _invalid("ChartType", "USL 與 LSL 相同，製程能力無法定義。")

    # --- safe to compute below ---
    valid_data = data.dropna()
    ...
```

### Helper (not yet extracted — inline the dict for now)

```python
def _invalid(chart_type: str, error: str) -> dict:
    return {
        "chart_type": chart_type,
        "data": {},
        "statistics": {},
        "metadata": {"is_valid": False, "error": error},
    }
```

---

## StatisticalUtils Reference

```python
from app.analytics.statistical_utils import StatisticalUtils

# Validation gate — use before any computation
ok, msg = StatisticalUtils.is_valid_for_spc(series)
# ok=False when: empty, N < 10, or std == 0

# Moving range — returns Series of length N (NaN at index 0)
mr = StatisticalUtils.calculate_moving_range(series)
mr_bar = mr.mean()          # NaN-safe; pandas skips NaN by default
sigma = mr_bar / 1.128      # d2 constant for individual charts (I-MR)
```

**Important**: `calculate_moving_range` returns `data.diff().abs()` — same length as input, NaN at position 0. Use `mr.dropna()` only when you need the raw list; `.mean()` handles NaN automatically.

---

## DataFrame-Based Engines (n=2 or n=3)

For multi-feature engines (`BivariateOutlierEngine`, `ParallelCoordEngine`, etc.) that take a `pd.DataFrame`:

```python
@staticmethod
def compute_xxx(df: pd.DataFrame, cols: List[str], ...) -> Dict[str, Any]:

    # Guard: empty
    if df is None or df.empty:
        return _invalid("ChartType", "無資料。")

    # Guard: missing columns
    missing = [c for c in cols if c not in df.columns]
    if missing:
        return _invalid("ChartType", f"缺少欄位: {missing}.")

    valid = df[cols].dropna()
    if valid.empty:
        return _invalid("ChartType", "無有效資料。")

    # --- safe to compute ---
```

---

## Single-Feature Pre-Computed Cache (`parameters[col]`)

When `compute_analysis_payload()` runs in n=1 mode (one selected feature), it pre-computes **all** single-feature engines for every available feature column and stores them under `payload["parameters"]`:

```python
payload["parameters"] = {
    "Volume": {
        "spc":               {...},   # SPCEngine.compute_imr()
        "cap":               {...},   # CapabilityEngine.compute_capability()
        "dist":              {...},   # DistributionEngine.compute_histogram()
        "box":               {...},   # BoxEngine.compute_box()
        "normality":         {...},   # NormalityEngine.compute_normality()
        "ewma":              {...},   # EWMAEngine.compute_ewma()
        "cusum":             {...},   # CUSUMEngine.compute_cusum()
        "run_chart":         {...},   # RunChartEngine.compute_run_chart()
        "subgroup":          {...},   # SubgroupEngine.compute_subgroup()
        "repeated_offender": {...},   # RepeatedOffenderEngine.compute_repeated_offender()
        "pareto":            {...},   # ParetoEngine.compute_pareto()
        "spatial":           {...},   # SpatialEngine.compute_spatial()
    },
    "Area":   { ... same 12 keys ... },
    "Height": { ... same 12 keys ... },
}
```

**Routing**: `chart_analysis_page._PARAM_KEY_FOR_CHART` maps every `chart_id` → the key in this dict. `_resolve_chart_data(chart_id)` returns `parameters[_display_feature][key]` for instant feature switching without re-analysis.

**Applies only when n=1**. For n=2 or n=3 selections, `payload["parameters"]` is absent.

---

## Resolved Slice Shape (`get_feature_payload_slice`)

`chart_registry.get_feature_payload_slice(payload, chart_id, feature)` resolves the per-chart slice that downstream renderers consume. **Most** chart_ids return the standard engine result `{chart_type, data, statistics, metadata}` shape — these can be validated directly against the contract.

**Exception — `chart_id == "imr"`**: returns a **payload-shaped** dict, not an engine result. See `app/analytics/chart_registry.py` (search for `if chart_id == "imr":`):

```python
# imr slice = a synthetic mini-payload, NOT an engine result
{
    ...payload top-level keys...,
    "spc":  {...},   # SPCEngine.compute_imr() result (engine-shaped)
    "cap":  {...},   # CapabilityEngine.compute_capability() result
    "dist": {...},   # DistributionEngine.compute_histogram() result
}
```

Validators / consumers **must not** assume `slice["chart_type"]` / `slice["metadata"]` for `chart_id == "imr"`. Instead:
- Check `slice["spc"]` (and `cap`/`dist`) as the real engine results.
- The `spc-validation-matrix` skill handles this in `engine_invoker.check_data_renderability()` (allows composite slice with empty top-level `data`).

---

## Engine Inventory

| Engine class | Method | chart_type | Min N | Key statistics |
|---|---|---|---|---|
| `SPCEngine` | `compute_imr` | `"I-MR"` | 10 | cl, ucl, lcl, sigma, mr_bar |
| `CapabilityEngine` | `compute_capability` | `"Capability"` | 10 | cp, cpk, pp, ppk, sigma_st, sigma_lt |
| `NormalityEngine` | `compute_normality` | `"Normality"` | 3 | p_value, is_normal, test_name |
| `EWMAEngine` | `compute_ewma` | `"EWMA"` | 10 | cl, ucl, lcl, lambda |
| `CUSUMEngine` | `compute_cusum` | `"CUSUM"` | 10 | target, k, h |
| `RunChartEngine` | `compute_run_chart` | `"RunChart"` | none | center_line |
| `DistributionEngine` | `compute_distribution` | `"Distribution"` | 10 | mean, std, bins |
| `ParetoEngine` | `compute_pareto` | `"Pareto"` | 1 row | categories, counts |
| `ScatterEngine` | `compute_scatter` | `"Scatter"` | — | n |
| `SubgroupEngine` | `compute_subgroup` | `"Subgroup"` | — | groups |
| `DensityEngine` | `compute_density` | `"Density"` | — | n |
| `QuadrantEngine` | `compute_quadrant` | `"Quadrant"` | — | quadrant_counts |
| `RepeatedOffenderEngine` | `compute_repeated_offender` | `"RepeatedOffender"` | — | n_offenders |
| `PassFailEngine` | `compute_pass_fail` | `"PassFail"` | 1 row | n_total; pass_rates are **0–100** (%) |
| `BivariateOutlierEngine` | `compute_bivariate_outlier` | `"BivariateOutlier"` | — | n, n_outliers |
| `ParallelCoordEngine` | `compute_parallel_coord` | `"ParallelCoord"` | — | n_points, n_displayed |
| `Anomaly3FEngine` | `compute_anomaly_3f` | `"Anomaly3F"` | — | n, mean_score, max_score |
| `Consistency3FEngine` | `compute_consistency_3f` | `"Consistency3F"` | — | n, mean_diff, std_diff |

---

## Testing Conventions

Every engine test file follows this structure:

```python
# 1. Happy path — structure check
def test_returns_required_structure():
    result = Engine.compute_xxx(...)
    assert result["chart_type"] == "ExpectedType"
    assert "data" in result
    assert "statistics" in result
    assert "metadata" in result

# 2. Happy path — is_valid=True
def test_valid_with_sufficient_data():
    assert result["metadata"]["is_valid"] is True

# 3. Data key presence (guard with is_valid check)
def test_data_keys_present():
    if result["metadata"]["is_valid"]:
        assert "key_a" in result["data"]

# 4. Error cases — always check is_valid=False
def test_empty_df_returns_invalid():
    result = Engine.compute_xxx(empty_df, ...)
    assert result["metadata"]["is_valid"] is False

def test_missing_column_returns_invalid():
    result = Engine.compute_xxx(df_missing_col, ...)
    assert result["metadata"]["is_valid"] is False
```

**Key rules for test authors:**
- Never assert on `result["data"]` without first checking `is_valid`
- `pass_rates` are percentages — assert `0 <= r <= 100`, not `0 <= r <= 1`
- `calculate_moving_range` returns length N (not N-1); use `.dropna()` for value checks
- `is_normal` from NormalityEngine is `np.bool_`, not Python `bool` — use `isinstance(x, (bool, np.bool_))`
- Statistical tests (normality, outlier detection) are probabilistic — avoid asserting specific outcomes on random seeds; assert structure and types only

---

## Common Mistakes

❌ **Do NOT**:
- Return partial `data` or `statistics` on failure — always `{}`
- Leave `"error": ""` when `is_valid=False`
- Assume `calculate_moving_range` returns N-1 values
- Assert `pass_rates <= 1.0` (they're percentages)
- Assert `is_normal is True` for randomly generated data

✅ **DO**:
- Call `StatisticalUtils.is_valid_for_spc()` as the first guard in every SPC engine
- Use `data.dropna()` before any computation
- Use `mr.mean()` directly (NaN-safe); only call `mr.dropna()` when building lists
- Store `target_col` in metadata for all single-feature engines
