"""
Report Intent Presets — 分析意圖套餐定義

Each preset maps a user-facing analysis intent to a recommended set of chart IDs.
The UI layer uses these to auto-select checkboxes when the user picks an intent.

min_features:
    1 = works with any number of selected features (≥1)
    2 = requires at least 2 features selected
"""
from __future__ import annotations

from typing import List, Optional, TypedDict


class IntentPreset(TypedDict):
    id: str
    label: str           # full display name (button label)
    description: str     # one-line description shown as tooltip / sub-text
    chart_ids: Optional[List[str]]  # None = use engineering defaults
    min_features: int    # minimum features required to enable this preset


INTENT_PRESETS: List[IntentPreset] = [
    {
        "id": "process_monitoring",
        "label": "製程監控",
        "description": "I-MR、Xbar-R、Trend、Rule violation（含 SPI 3F 監控）",
        "chart_ids": [
            "imr", "xbar_r", "run_chart", "ooc_analysis",
            "ewma", "cusum", "shift_detection", "drift_detection",
            "pattern_recognition", "imr_3f", "run_chart_3f", "ewma_3f", "cusum_3f",
        ],
        "min_features": 1,
    },
    {
        "id": "process_capability",
        "label": "製程能力",
        "description": "Cp/Cpk、Histogram、Spec overlay（含多特徵能力對照）",
        "chart_ids": [
            "histogram_spec", "normality", "boxplot", "boxplot_3f", "pass_fail_matrix",
        ],
        "min_features": 1,
    },
    {
        "id": "anomaly_root_cause",
        "label": "異常根源",
        "description": "Pareto、Heatmap、Top defect（含多維異常定位）",
        "chart_ids": [
            "pareto", "spatial_heatmap", "repeated_offender",
            "outlier_analysis", "anomaly_3f", "consistency_3f",
        ],
        "min_features": 1,
    },
    {
        "id": "variable_relationship",
        "label": "變數關係",
        "description": "Scatter、Correlation matrix（含熱圖/雙變量離群）",
        "chart_ids": [
            "scatter_spec", "correlation_matrix", "correlation_heatmap",
            "density", "quadrant", "bivariate_outlier", "parallel_coord",
        ],
        "min_features": 2,
    },
    {
        "id": "comparison_analysis",
        "label": "比較分析",
        "description": "Batch compare、Group compare（批次與群組差異）",
        "chart_ids": [
            "subgroup", "anova_parttype", "boxplot",
        ],
        "min_features": 1,
    },
]
