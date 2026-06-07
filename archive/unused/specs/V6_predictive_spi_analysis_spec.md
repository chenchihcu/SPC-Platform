# V6.0 — Predictive SPI Engineering Analysis

## Objective

Enable process risk detection **before** SPC violations occur.
The system remains an SPI-only engineering analysis tool.

## Current State (V5.0)

The platform already provides:
- I-MR, EWMA, CUSUM control charts
- Cp/Cpk/Pp/Ppk capability analysis
- Component Pareto ranking
- Spatial heatmap & clustering
- Anomaly classification & root cause hints
- Failure mode library

Engineers currently discover problems **after** violations (OOS, UCL/LCL exceeded, paste drying progressed).

## Constraints

1. SPI data only. No AOI, ICT, or yield database integration.
2. Analysis tool only. No automatic process decisions.
3. Do not modify existing analytics engines (spc_engine, ewma_engine, cusum_engine, etc.).
4. Do not modify SPI import pipeline (loaders/, mapping/, validation/).
5. No persistent database — v2 uses in-memory SessionStore. Predictive results stored in SessionStore cache or exported as JSON/CSV.
6. Line/Product comparison requires `line` field in SPI CSV. If absent, disable that feature gracefully.

## Modules (3 core)

### Module 1: Predictive Drift Engine

Extend beyond current EWMA/CUSUM by computing forward-looking risk indicators.

**New file:** `app/analytics/drift_engine.py`

**Inputs:** Measurement DataFrame (same as existing engines), EWMA/CUSUM payload from current engines.

**Outputs** (unified format):
```python
{
    "chart_type": "PredictiveDrift",
    "data": {
        "ewma_slope": [...],           # EWMA trend slope per window
        "rolling_variance": [...],     # Rolling variance (window=20)
        "rolling_skewness": [...],     # Distribution shape change
        "rolling_kurtosis": [...],     # Tail behavior change
        "cusum_magnitude": [...],      # Cumulative shift magnitude
        "drift_risk_score": float,     # 0.0 ~ 1.0 composite score
    },
    "statistics": {
        "trend_direction": "increasing" | "decreasing" | "stable",
        "variance_trend": "growing" | "shrinking" | "stable",
        "risk_level": "LOW" | "MEDIUM" | "HIGH",
    },
    "metadata": {
        "is_valid": bool,
        "target_col": str,
        "window_size": int,
        "min_samples_required": 20,
    }
}
```

**Detection targets:**
- Slow volume drift (stencil wear)
- Gradual stencil contamination (variance growth)
- Paste drying trend (mean shift + variance increase)

### Module 2: Pre-OOS Risk Scoring

Compute probability of upcoming SPC violations per component.

**New file:** `app/analytics/risk_score_engine.py`

**Inputs:** Filtered DataFrame + drift engine output + capability payload.

**Outputs:**
```python
{
    "chart_type": "RiskScore",
    "data": {
        "component_risks": [
            {
                "refdes": "U14",
                "risk_level": "HIGH",
                "risk_score": 0.82,
                "reasons": ["variance_increasing", "ewma_drift"],
                "projected_cpk": 0.95,
                "current_cpk": 1.21,
            },
            ...
        ],
        "top_risk_components": ["U14", "C33", "R7"],
    },
    "statistics": {
        "high_risk_count": int,
        "medium_risk_count": int,
        "total_scored": int,
    },
    "metadata": {"is_valid": bool, "min_samples_per_component": 10}
}
```

**Risk indicators:**
- Increasing variance
- EWMA slope away from target
- Histogram skewness change
- Cpk projected to drop below 1.0

### Module 3: Early Warning Dashboard

New UI page summarizing predictive analysis results.

**New file:** `app/ui/pages/early_warning_page.py`

**Display panels:**
- Top drifting components (table: RefDes, risk score, reason, projected Cpk)
- Drift trend chart (EWMA slope + rolling variance over board sequence)
- Risk distribution (bar chart: HIGH / MEDIUM / LOW counts)
- Heatmap overlay: spatial view colored by risk score (if coordinate data available)

**Integration:**
- Register as page 8 in main_window.py navigation (分析 group)
- Subscribe to `chart_vm.data_ready` signal
- Read predictive payload from SessionStore

## Deferred Modules

These are valuable but not required for V6.0 core delivery:

| Module | Reason to defer |
|---|---|
| Component Stability Ranking | Pareto + Risk Scoring already cover ranking; add later if engineers need a dedicated view |
| Line / Product Comparison | Requires `line` field in CSV that may not exist; implement after confirming data availability |

## Implementation Phases

### Phase 1: Drift Engine + Dashboard MVP
- Implement `drift_engine.py` with rolling stats
- Implement `early_warning_page.py` with drift trend chart
- Wire into `compute_analysis_payload()` as independent call
- Add to SessionStore cache with dedicated namespace

**Deliverable:** Engineers can see drift trends on the Early Warning page.

### Phase 2: Risk Scoring Integration
- Implement `risk_score_engine.py`
- Add component risk table to Early Warning Dashboard
- Add risk heatmap overlay (if coordinates available)
- Extend CSV export to include risk scores

**Deliverable:** Engineers can identify high-risk components before OOS occurs.

### Phase 3: Validation & Performance
- Test with real factory datasets (10k, 50k, 100k+ rows)
- Tune risk score thresholds based on historical OOS correlation
- Optimize: ensure predictive calculation runs in background QThread
- Add unit tests for all new engines

**Deliverable:** Validated, production-ready predictive analysis.

## Architecture Fit

```
app/analytics/
├── spc_engine.py              (unchanged)
├── ewma_engine.py             (unchanged)
├── cusum_engine.py            (unchanged)
├── capability_engine.py       (unchanged)
├── ... (24 existing engines)  (unchanged)
├── drift_engine.py            (NEW)
└── risk_score_engine.py       (NEW)

app/ui/pages/
├── chart_analysis_page.py     (unchanged)
├── ... (6 existing pages)     (unchanged)
└── early_warning_page.py      (NEW)
```

`compute_analysis_payload()` remains untouched.
New function: `compute_predictive_payload()` in viewmodel, called in parallel.

## Verification Criteria

| Criterion | Target |
|---|---|
| Early detection lead time | Drift warning issued >= 3 board sequences before UCL/LCL violation |
| Risk score accuracy | Components scored HIGH have OOS within 50 boards in >= 60% of cases |
| Dashboard load time | < 3 seconds for 100,000 measurement rows |
| Existing feature regression | Zero — all current SPC/capability/spatial analysis unchanged |
| Minimum sample requirement | Graceful degradation message when < 20 data points |
