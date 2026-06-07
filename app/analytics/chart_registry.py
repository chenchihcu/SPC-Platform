"""
Chart registry: compatibility between selected features and chart types.
Used by ViewModel and UI to determine which charts are available and to show
incompatible_reason when the current selection does not match.
Phase 2: category, payload_key, get_charts_by_category, get_payload_slice.
Phase 3: use unified message constants from app.utils.constants.
Display names (Chinese-first) and 4-section description metadata are unified here.
"""
from typing import List, Optional, Dict, Any

from app.utils.constants import (
    MSG_INCOMPATIBLE_AT_LEAST_ONE,
    MSG_INCOMPATIBLE_SINGLE,
    MSG_INCOMPATIBLE_DUAL,
    MSG_INCOMPATIBLE_TRIPLE,
    MSG_UNKNOWN_CHART,
)

# Required feature count: 1 = single feature only, 2 = exactly two, 3 = exactly three
REQUIRED_SINGLE = 1
REQUIRED_DUAL = 2
REQUIRED_TRIPLE = 3

# Categories for left-side grouping
CATEGORY_SINGLE = "單特徵製程"
CATEGORY_DUAL = "雙特徵關聯"
CATEGORY_TRIPLE = "三特徵綜合"
# 分布／箱型／常態：一至多特徵並列（與「僅單特徵」管制圖區隔）
CATEGORY_DIST_AT_LEAST_ONE = "分布與能力（一至多特徵）"
CATEGORY_AT_LEAST_TWO = "關聯分析（至少雙特徵）"
CATEGORY_ANALYSIS_AT_LEAST_ONE = "異常分析（一至多特徵）"

# Workflow-driven UI: section order and labels for SPC Analysis Workspace
WORKFLOW_SECTION_ORDER = [
    "global_overview",
    "pareto",
    "footprint_comparison",
    "pcb_heatmap",
    "correlation",
    "trend_drift",
    "multi_feature",
]
WORKFLOW_SECTION_LABELS: Dict[str, str] = {
    "global_overview": "GLOBAL OVERVIEW",
    "pareto": "PARETO",
    "footprint_comparison": "FOOTPRINT COMPARISON",
    "pcb_heatmap": "PCB HEATMAP",
    "correlation": "CORRELATION",
    "trend_drift": "TREND DRIFT",
    "multi_feature": "MULTI-FEATURE",
}
# UI 頂部選單：工程決策五大分類（單一分析目的）
CHART_UI_GROUPS_ORDER = ["製程監控", "製程能力", "異常根源", "變數關係", "比較分析"]
CHART_UI_GROUP_BY_ID: Dict[str, str] = {
    "imr": "製程監控",
    "xbar_r": "製程監控",
    "run_chart": "製程監控",
    "ewma": "製程監控",
    "cusum": "製程監控",
    "ooc_analysis": "製程監控",
    "shift_detection": "製程監控",
    "drift_detection": "製程監控",
    "pattern_recognition": "製程監控",
    "imr_3f": "製程監控",
    "run_chart_3f": "製程監控",
    "ewma_3f": "製程監控",
    "cusum_3f": "製程監控",
    "histogram_spec": "製程能力",
    "normality": "製程能力",
    "boxplot": "製程能力",
    "boxplot_3f": "製程能力",
    "pass_fail_matrix": "製程能力",
    "pareto": "異常根源",
    "spatial_heatmap": "異常根源",
    "repeated_offender": "異常根源",
    "outlier_analysis": "異常根源",
    "anomaly_3f": "異常根源",
    "consistency_3f": "異常根源",
    "scatter_spec": "變數關係",
    "correlation_matrix": "變數關係",
    "correlation_heatmap": "變數關係",
    "density": "變數關係",
    "quadrant": "變數關係",
    "bivariate_outlier": "變數關係",
    "parallel_coord": "變數關係",
    "subgroup": "比較分析",
    "anova_parttype": "比較分析",
}
# 簡化名稱（頂部 checkbox 顯示）；tooltip 用 get_chart_display_name 或 CHART_DESCRIPTIONS
CHART_SHORT_NAMES: Dict[str, str] = {
    "imr": "I-MR",
    "xbar_r": "Xb-R",
    "run_chart": "Trend",
    "ewma": "EWMA",
    "cusum": "CSUM",
    "histogram_spec": "Cp/Cpk",
    "boxplot": "箱型圖",
    "normality": "常態性",
    "density": "密度圖",
    "scatter_spec": "散點圖",
    "correlation_matrix": "關聯矩陣",
    "correlation_heatmap": "熱圖",
    "anova_parttype": "群組比較",
    "ooc_analysis": "規則違反",
    "shift_detection": "偏移偵測",
    "drift_detection": "漂移偵測",
    "outlier_analysis": "離群分析",
    "pattern_recognition": "規則辨識",
    "subgroup": "批次比",
    "quadrant": "四象限",
    "spatial_heatmap": "空間圖",
    "pareto": "柏拉圖",
    "repeated_offender": "Top缺陷",
    "bivariate_outlier": "雙離群",
    "anomaly_3f": "特徵異常",
    "consistency_3f": "一致性",
    "parallel_coord": "平行座標",
    "pass_fail_matrix": "合格表",
    "imr_3f": "IM3F",
    "run_chart_3f": "趨勢3F",
    "ewma_3f": "EW3F",
    "cusum_3f": "CS3F",
    "boxplot_3f": "箱型3F",
}
# 常用組合 preset：常態分析、箱型圖、X‑R、X‑S（X‑R 對應 imr，X‑S 用 run_chart 或 subgroup 暫以 run_chart 代表趨勢）
PRESET_FAVORITE_CHART_IDS = ["normality", "boxplot", "imr", "run_chart"]

# chart_id -> workflow_section for left-list grouping
WORKFLOW_SECTION_BY_CHART: Dict[str, str] = {
    "imr": "global_overview",
    "xbar_r": "global_overview",
    "run_chart": "global_overview",
    "subgroup": "global_overview",
    "repeated_offender": "global_overview",
    "histogram_spec": "global_overview",
    "normality": "global_overview",
    "ooc_analysis": "global_overview",
    "shift_detection": "global_overview",
    "drift_detection": "global_overview",
    "pattern_recognition": "global_overview",
    "pareto": "pareto",
    "boxplot": "footprint_comparison",
    "spatial_heatmap": "pcb_heatmap",
    "scatter_spec": "correlation",
    "correlation_matrix": "correlation",
    "correlation_heatmap": "correlation",
    "anova_parttype": "correlation",
    "quadrant": "correlation",
    "bivariate_outlier": "correlation",
    "outlier_analysis": "correlation",
    "density": "correlation",
    "ewma": "trend_drift",
    "cusum": "trend_drift",
    "anomaly_3f": "multi_feature",
    "consistency_3f": "multi_feature",
    "parallel_coord": "multi_feature",
    "pass_fail_matrix": "multi_feature",
    "imr_3f": "multi_feature",
    "run_chart_3f": "multi_feature",
    "ewma_3f": "multi_feature",
    "cusum_3f": "multi_feature",
    "boxplot_3f": "multi_feature",
}

# Standard 4-section description placeholder when section not applicable
_DEFAULT_SECTION = "—"
_MSG_INCOMPATIBLE_DATA = "目前特徵選定與此圖表不相容，請於元件/量測選定頁調整為單選/雙選/三選。"

# payload_key: str for single key, or tuple of str for composite (dist, cap)
# name = display name (Chinese-first) for backward compat; display_name_zh / display_name_en for get_chart_display_name
CHART_CATALOG = [
    # Main flow: Process Monitoring
    {"id": "imr", "required_feature_count": REQUIRED_SINGLE, "name": "個別值與移動極差圖（I-MR）", "display_name_zh": "個別值與移動極差圖", "display_name_en": "I-MR", "category": CATEGORY_SINGLE, "payload_key": "spc", "incompatible_reason": MSG_INCOMPATIBLE_SINGLE},
    {"id": "xbar_r", "required_feature_count": REQUIRED_SINGLE, "name": "Xbar-R 管制圖", "display_name_zh": "Xbar-R 管制圖", "display_name_en": "Xbar-R", "category": CATEGORY_SINGLE, "payload_key": "xbar_r", "incompatible_reason": MSG_INCOMPATIBLE_SINGLE},
    {"id": "run_chart", "required_feature_count": REQUIRED_SINGLE, "name": "趨勢圖（Run Chart）", "display_name_zh": "趨勢圖", "display_name_en": "Run Chart", "category": CATEGORY_SINGLE, "payload_key": "run_chart", "incompatible_reason": MSG_INCOMPATIBLE_SINGLE},
    {"id": "ewma", "required_feature_count": REQUIRED_SINGLE, "name": "指數加權移動平均圖（EWMA）", "display_name_zh": "指數加權移動平均圖", "display_name_en": "EWMA", "category": CATEGORY_SINGLE, "payload_key": "ewma", "incompatible_reason": MSG_INCOMPATIBLE_SINGLE},
    {"id": "cusum", "required_feature_count": REQUIRED_SINGLE, "name": "累積和管制圖（CUSUM）", "display_name_zh": "累積和管制圖", "display_name_en": "CUSUM", "category": CATEGORY_SINGLE, "payload_key": "cusum", "incompatible_reason": MSG_INCOMPATIBLE_SINGLE},

    # Main flow: Distribution
    {"id": "histogram_spec", "required_feature_count": REQUIRED_SINGLE, "name": "分布與能力（Histogram & Capability，一至多特徵）", "display_name_zh": "分布與能力（一至多特徵）", "display_name_en": "Histogram & Capability (1–3 features)", "category": CATEGORY_DIST_AT_LEAST_ONE, "payload_key": ("dist", "cap"), "incompatible_reason": MSG_INCOMPATIBLE_AT_LEAST_ONE},
    {"id": "boxplot", "required_feature_count": REQUIRED_SINGLE, "name": "箱型圖（Boxplot，一至多特徵）", "display_name_zh": "箱型圖（一至多特徵）", "display_name_en": "Boxplot (1–3 features)", "category": CATEGORY_DIST_AT_LEAST_ONE, "payload_key": "box", "incompatible_reason": MSG_INCOMPATIBLE_AT_LEAST_ONE},
    {"id": "normality", "required_feature_count": REQUIRED_SINGLE, "name": "常態分析（Normality，一至多特徵）", "display_name_zh": "常態分析（一至多特徵）", "display_name_en": "Normality (1–3 features)", "category": CATEGORY_DIST_AT_LEAST_ONE, "payload_key": "normality", "incompatible_reason": MSG_INCOMPATIBLE_AT_LEAST_ONE},
    {"id": "density", "required_feature_count": REQUIRED_SINGLE, "name": "密度圖（Density，一至多特徵）", "display_name_zh": "密度圖（一至多特徵）", "display_name_en": "Density (1–3 features)", "category": CATEGORY_DIST_AT_LEAST_ONE, "payload_key": "density", "incompatible_reason": MSG_INCOMPATIBLE_AT_LEAST_ONE},

    # Main flow: Association
    {"id": "scatter_spec", "required_feature_count": REQUIRED_DUAL, "name": "散點與規格區（Scatter+Spec）", "display_name_zh": "散點與規格區", "display_name_en": "Scatter+Spec", "category": CATEGORY_AT_LEAST_TWO, "payload_key": "scatter_spec", "incompatible_reason": MSG_INCOMPATIBLE_DUAL},
    {"id": "correlation_matrix", "required_feature_count": REQUIRED_DUAL, "name": "關聯矩陣（Correlation Matrix）", "display_name_zh": "關聯矩陣", "display_name_en": "Correlation Matrix", "category": CATEGORY_AT_LEAST_TWO, "payload_key": "correlation_matrix", "incompatible_reason": MSG_INCOMPATIBLE_DUAL},
    {"id": "correlation_heatmap", "required_feature_count": REQUIRED_DUAL, "name": "關聯熱圖（Correlation Heatmap）", "display_name_zh": "關聯熱圖", "display_name_en": "Correlation Heatmap", "category": CATEGORY_AT_LEAST_TWO, "payload_key": "correlation_heatmap", "incompatible_reason": MSG_INCOMPATIBLE_DUAL},
    {"id": "anova_parttype", "required_feature_count": REQUIRED_SINGLE, "name": "ANOVA（PartType）", "display_name_zh": "ANOVA（PartType）", "display_name_en": "ANOVA (PartType)", "category": CATEGORY_ANALYSIS_AT_LEAST_ONE, "payload_key": "anova_parttype", "incompatible_reason": MSG_INCOMPATIBLE_AT_LEAST_ONE},

    # Main flow: Anomaly
    {"id": "ooc_analysis", "required_feature_count": REQUIRED_SINGLE, "name": "失控分析（OOC Analysis）", "display_name_zh": "失控分析", "display_name_en": "OOC Analysis", "category": CATEGORY_ANALYSIS_AT_LEAST_ONE, "payload_key": "ooc_analysis", "incompatible_reason": MSG_INCOMPATIBLE_AT_LEAST_ONE},
    {"id": "shift_detection", "required_feature_count": REQUIRED_SINGLE, "name": "偏移偵測（Shift Detection）", "display_name_zh": "偏移偵測", "display_name_en": "Shift Detection", "category": CATEGORY_ANALYSIS_AT_LEAST_ONE, "payload_key": "shift_detection", "incompatible_reason": MSG_INCOMPATIBLE_AT_LEAST_ONE},
    {"id": "drift_detection", "required_feature_count": REQUIRED_SINGLE, "name": "漂移偵測（Drift Detection）", "display_name_zh": "漂移偵測", "display_name_en": "Drift Detection", "category": CATEGORY_ANALYSIS_AT_LEAST_ONE, "payload_key": "drift_detection", "incompatible_reason": MSG_INCOMPATIBLE_AT_LEAST_ONE},
    {"id": "outlier_analysis", "required_feature_count": REQUIRED_SINGLE, "name": "離群分析（Outlier Analysis）", "display_name_zh": "離群分析", "display_name_en": "Outlier Analysis", "category": CATEGORY_ANALYSIS_AT_LEAST_ONE, "payload_key": "outlier_analysis", "incompatible_reason": MSG_INCOMPATIBLE_AT_LEAST_ONE},
    {"id": "pattern_recognition", "required_feature_count": REQUIRED_SINGLE, "name": "規則辨識（Pattern Recognition）", "display_name_zh": "規則辨識", "display_name_en": "Pattern Recognition", "category": CATEGORY_ANALYSIS_AT_LEAST_ONE, "payload_key": "pattern_recognition", "incompatible_reason": MSG_INCOMPATIBLE_AT_LEAST_ONE},

    # Advanced legacy charts (retained)
    {"id": "subgroup", "required_feature_count": REQUIRED_SINGLE, "name": "子群比較（Subgroup Comparison）", "display_name_zh": "子群比較", "display_name_en": "Subgroup Comparison", "category": CATEGORY_SINGLE, "payload_key": "subgroup", "incompatible_reason": MSG_INCOMPATIBLE_SINGLE},
    {"id": "repeated_offender", "required_feature_count": REQUIRED_SINGLE, "name": "重複異常點分析（Repeated Offender）", "display_name_zh": "重複異常點分析", "display_name_en": "Repeated Offender", "category": CATEGORY_SINGLE, "payload_key": "repeated_offender", "incompatible_reason": MSG_INCOMPATIBLE_SINGLE},
    {"id": "spatial_heatmap", "required_feature_count": REQUIRED_SINGLE, "name": "空間熱圖（Spatial Heatmap）", "display_name_zh": "空間熱圖", "display_name_en": "Spatial Heatmap", "category": CATEGORY_SINGLE, "payload_key": "spatial", "incompatible_reason": MSG_INCOMPATIBLE_SINGLE},
    {"id": "pareto", "required_feature_count": REQUIRED_SINGLE, "name": "柏拉圖（Pareto）", "display_name_zh": "柏拉圖", "display_name_en": "Pareto", "category": CATEGORY_SINGLE, "payload_key": "pareto", "incompatible_reason": MSG_INCOMPATIBLE_SINGLE},
    {"id": "quadrant", "required_feature_count": REQUIRED_DUAL, "name": "四象限（Quadrant）", "display_name_zh": "四象限", "display_name_en": "Quadrant", "category": CATEGORY_DUAL, "payload_key": "quadrant", "incompatible_reason": MSG_INCOMPATIBLE_DUAL},
    {"id": "bivariate_outlier", "required_feature_count": REQUIRED_DUAL, "name": "雙變量離群（Bivariate Outlier）", "display_name_zh": "雙變量離群", "display_name_en": "Bivariate Outlier", "category": CATEGORY_DUAL, "payload_key": "bivariate_outlier", "incompatible_reason": MSG_INCOMPATIBLE_DUAL},
    {"id": "anomaly_3f", "required_feature_count": REQUIRED_TRIPLE, "name": "三特徵異常分數（Anomaly 3F）", "display_name_zh": "三特徵異常分數", "display_name_en": "Anomaly 3F", "category": CATEGORY_TRIPLE, "payload_key": "anomaly_3f", "incompatible_reason": MSG_INCOMPATIBLE_TRIPLE},
    {"id": "consistency_3f", "required_feature_count": REQUIRED_TRIPLE, "name": "多特徵一致性（Consistency 3F）", "display_name_zh": "多特徵一致性", "display_name_en": "Consistency 3F", "category": CATEGORY_TRIPLE, "payload_key": "consistency_3f", "incompatible_reason": MSG_INCOMPATIBLE_TRIPLE},
    {"id": "parallel_coord", "required_feature_count": REQUIRED_TRIPLE, "name": "平行座標（Parallel Coordinates）", "display_name_zh": "平行座標", "display_name_en": "Parallel Coordinates", "category": CATEGORY_TRIPLE, "payload_key": "parallel_coord", "incompatible_reason": MSG_INCOMPATIBLE_TRIPLE},
    {"id": "pass_fail_matrix", "required_feature_count": REQUIRED_TRIPLE, "name": "過關/失敗摘要（Pass/Fail Summary）", "display_name_zh": "過關/失敗摘要", "display_name_en": "Pass/Fail Summary", "category": CATEGORY_TRIPLE, "payload_key": "pass_fail_matrix", "incompatible_reason": MSG_INCOMPATIBLE_TRIPLE},
    {"id": "imr_3f", "required_feature_count": REQUIRED_TRIPLE, "name": "三特徵 I-MR 並列（I-MR 3F）", "display_name_zh": "三特徵 I-MR 並列", "display_name_en": "I-MR 3F", "category": CATEGORY_TRIPLE, "payload_key": "parameters", "incompatible_reason": MSG_INCOMPATIBLE_TRIPLE},
    {"id": "run_chart_3f", "required_feature_count": REQUIRED_TRIPLE, "name": "三特徵趨勢圖並列（Run Chart 3F）", "display_name_zh": "三特徵趨勢圖並列", "display_name_en": "Run Chart 3F", "category": CATEGORY_TRIPLE, "payload_key": "parameters", "incompatible_reason": MSG_INCOMPATIBLE_TRIPLE},
    {"id": "ewma_3f", "required_feature_count": REQUIRED_TRIPLE, "name": "三特徵 EWMA 並列（EWMA 3F）", "display_name_zh": "三特徵 EWMA 並列", "display_name_en": "EWMA 3F", "category": CATEGORY_TRIPLE, "payload_key": "parameters", "incompatible_reason": MSG_INCOMPATIBLE_TRIPLE},
    {"id": "cusum_3f", "required_feature_count": REQUIRED_TRIPLE, "name": "三特徵 CUSUM 並列（CUSUM 3F）", "display_name_zh": "三特徵 CUSUM 並列", "display_name_en": "CUSUM 3F", "category": CATEGORY_TRIPLE, "payload_key": "parameters", "incompatible_reason": MSG_INCOMPATIBLE_TRIPLE},
    {"id": "boxplot_3f", "required_feature_count": REQUIRED_TRIPLE, "name": "三特徵箱型概覽（Boxplot 3F）", "display_name_zh": "三特徵箱型概覽", "display_name_en": "Boxplot 3F", "category": CATEGORY_TRIPLE, "payload_key": "parameters", "incompatible_reason": MSG_INCOMPATIBLE_TRIPLE},
]

# Cache: chart_id -> chart entry (eliminates repeated linear searches)
_CATALOG_BY_ID: dict[str, dict] = {
    chart_id: e
    for e in CHART_CATALOG
    for chart_id in [str(e.get("id", "")).strip()]
    if chart_id
}

# Fixed order for left list and stacked workspace (index = stack index)
# Order follows the five decision categories:
# 1) 製程監控 -> 2) 製程能力 -> 3) 異常根源 -> 4) 變數關係 -> 5) 比較分析
CHART_ORDER = [
    # 製程監控
    "imr", "xbar_r", "run_chart", "ooc_analysis", "shift_detection", "drift_detection", "pattern_recognition",
    "ewma", "cusum", "imr_3f", "run_chart_3f", "ewma_3f", "cusum_3f",
    # 製程能力
    "histogram_spec", "normality", "boxplot", "boxplot_3f", "pass_fail_matrix",
    # 異常根源
    "pareto", "spatial_heatmap", "repeated_offender", "outlier_analysis", "anomaly_3f", "consistency_3f",
    # 變數關係
    "scatter_spec", "correlation_matrix", "correlation_heatmap", "density", "quadrant", "bivariate_outlier", "parallel_coord",
    # 比較分析
    "subgroup", "anova_parttype",
]

# Root-cause flow metadata (aligned to 5 decision categories)
ROOT_CAUSE_FLOW_ORDER: list[dict[str, Any]] = [
    {
        "stage_id": "process_monitoring",
        "label": "製程監控",
        "chart_ids": [
            "imr", "xbar_r", "run_chart", "ooc_analysis", "shift_detection", "drift_detection",
            "pattern_recognition", "ewma", "cusum", "imr_3f", "run_chart_3f", "ewma_3f", "cusum_3f",
        ],
    },
    {
        "stage_id": "process_capability",
        "label": "製程能力",
        "chart_ids": ["histogram_spec", "normality", "boxplot", "boxplot_3f", "pass_fail_matrix"],
    },
    {
        "stage_id": "anomaly_root_cause",
        "label": "異常根源",
        "chart_ids": ["pareto", "spatial_heatmap", "repeated_offender", "outlier_analysis", "anomaly_3f", "consistency_3f"],
    },
    {
        "stage_id": "variable_relationship",
        "label": "變數關係",
        "chart_ids": ["scatter_spec", "correlation_matrix", "correlation_heatmap", "density", "quadrant", "bivariate_outlier", "parallel_coord"],
    },
    {
        "stage_id": "comparison_analysis",
        "label": "比較分析",
        "chart_ids": ["subgroup", "anova_parttype"],
    },
]

CHART_ROOT_CAUSE_STAGE_BY_ID: Dict[str, str] = {
    chart_id: stage["stage_id"]
    for stage in ROOT_CAUSE_FLOW_ORDER
    for chart_id in stage["chart_ids"]
}

CHART_NEXT_STEP_BY_ID: Dict[str, list[str]] = {
    "ewma": ["drift_detection", "cusum", "xbar_r"],
    "ewma_3f": ["cusum_3f", "imr_3f"],
    "drift_detection": ["cusum", "shift_detection"],
    "cusum": ["shift_detection", "imr", "run_chart"],
    "cusum_3f": ["imr_3f", "run_chart_3f"],
    "shift_detection": ["imr", "ooc_analysis"],
    "xbar_r": ["imr", "ooc_analysis"],
    "imr": ["ooc_analysis", "pattern_recognition", "run_chart"],
    "imr_3f": ["run_chart_3f", "anomaly_3f", "consistency_3f"],
    "ooc_analysis": ["pattern_recognition", "histogram_spec", "pareto"],
    "run_chart": ["histogram_spec", "pareto", "correlation_matrix"],
    "run_chart_3f": ["boxplot_3f", "anomaly_3f", "scatter_spec"],
    "histogram_spec": ["normality", "boxplot", "pareto"],
    "boxplot": ["pareto", "subgroup", "anova_parttype"],
    "pareto": ["spatial_heatmap", "repeated_offender", "scatter_spec"],
    "spatial_heatmap": ["repeated_offender", "scatter_spec", "subgroup"],
    "correlation_matrix": ["correlation_heatmap", "bivariate_outlier", "anova_parttype"],
    "scatter_spec": ["correlation_matrix", "quadrant", "anova_parttype"],
}

# 4-section description texts: definition, formula, data_source, smt_interpretation (single source for chart description area)
CHART_DESCRIPTIONS: Dict[str, Dict[str, str]] = {
    "imr": {
        "definition_text": "個別值（I）與移動極差（MR）管制圖，用於監控單一量測特徵的製程穩定性；可觀察趨勢、突變與超出管制界線的點。",
        "formula_text": "中心線 CL = 個別值平均；UCL/LCL = 平均 ± 3×標準差。移動極差 MR = |x_i − x_{i−1}|，MR 圖 CL = MR 平均，UCL = 3.267×MR 平均。",
        "data_source_text": "單一量測特徵（Volume / Area / Height），依板序或時間排列。",
        "smt_interpretation_text": "SPI 錫膏量／高度／面積的逐點與極差變化；可判讀少錫、多錫、漂移、突變或設備不穩。判讀問題：是否已超出管制界線、MR 是否同時放大。下一步：回看 Run Chart 對齊異常區段。",
    },
    "run_chart": {
        "definition_text": "板序或時間 vs 量測值趨勢圖，用於觀察連續點之走向與異常跳動。",
        "formula_text": "本圖主要為視覺分布／趨勢呈現，無單一固定統計公式。",
        "data_source_text": "單一量測特徵，依板序（BoardNo）或時間順序排列。",
        "smt_interpretation_text": "可協助判讀製程漂移、突變、週期性變化；板序 vs Volume 可偵測錫膏乾涸等隨生產順序之變化。判讀問題：異常從哪個樣本序開始。下一步：搭配 Pareto/Heatmap 進行定位。",
    },
    "subgroup": {
        "definition_text": "依子群（如板號、站位）比較量測分布，檢視組間差異。",
        "formula_text": "本圖主要為視覺分布／組間比較，無單一固定統計公式。",
        "data_source_text": "單一量測特徵，需有分組欄位（如 BoardNo）。",
        "smt_interpretation_text": "可判讀板間差異、站位效應或類型差異。",
    },
    "repeated_offender": {
        "definition_text": "標示重複出現異常的板位或元件，找出反覆超出規格或管制界線的點。",
        "formula_text": "本圖主要為異常標記與計次，無單一固定統計公式。",
        "data_source_text": "單一量測特徵，需板位／元件識別。",
        "smt_interpretation_text": "可協助鎖定重複異常的 PCB 位置或元件，利於製程改善。",
    },
    "histogram_spec": {
        "definition_text": "量測值分布直方圖與規格界線（USL/LSL），用於觀察分布形態與規格符合度。",
        "formula_text": "直方圖為次數分布；Cp = (USL−LSL)/(6σ)，Cpk = min((USL−μ)/(3σ), (μ−LSL)/(3σ))。",
        "data_source_text": "一至三個量測特徵（選定頁可複選）；各特徵需有規格上下限以計算能力指標。",
        "smt_interpretation_text": "可判讀錫膏量／高度／面積的分布是否居中、是否偏規格、是否有雙峰或偏態。",
    },
    "boxplot": {
        "definition_text": "箱型圖顯示四分位數、中位數與離群值，用於比較多組或單一特徵的分布。",
        "formula_text": "Q1/Q2/Q3 為 25%/50%/75% 分位數；IQR = Q3−Q1；離群定義常為 Q1−1.5×IQR 或 Q3+1.5×IQR 外。",
        "data_source_text": "一至三個量測特徵（選定頁可複選）；可依板號／元件分組比較。",
        "smt_interpretation_text": "可判讀組間水平差異、偏態與離群點，利於元件或板位比較。",
    },
    "normality": {
        "definition_text": "常態性檢定與 Q-Q 圖，檢視量測資料是否符合常態分布。",
        "formula_text": "常採 Shapiro-Wilk 或常態 Q-Q 圖；若 p > 0.05 常視為不拒絕常態。",
        "data_source_text": "一至三個量測特徵（選定頁可複選）；各特徵需有足夠有效量測值以進行檢定。",
        "smt_interpretation_text": "若非常態，後續 Cp/Cpk 或管制圖解讀需謹慎；可協助選擇適當的統計方法。",
    },
    "spatial_heatmap": {
        "definition_text": "在 PCB 版面或板位上以顏色表示量測值分布，用於空間異常定位。",
        "formula_text": "本圖主要為空間視覺化，無單一固定統計公式。",
        "data_source_text": "單一量測特徵，需有座標（X/Y）或板位資訊。",
        "smt_interpretation_text": "可判讀局部少錫、多錫、刮刀或印刷方向造成的空間 pattern。",
    },
    "pareto": {
        "definition_text": "柏拉圖依發生頻率或影響程度排序，找出關鍵少數的異常類型或位置。",
        "formula_text": "長條為缺陷計數，折線為累積百分比；缺陷分類以 USL/LSL 規格界線判定。",
        "data_source_text": "單一量測特徵，需提供 USL/LSL 規格界線以進行標準缺陷分類。",
        "smt_interpretation_text": "可協助聚焦改善重點，優先處理影響最大的異常來源。",
    },
    "ewma": {
        "definition_text": "指數加權移動平均圖，對近期資料權重較高，利於偵測小偏移；用於趨勢漂移偵測。",
        "formula_text": "EWMA_t = λ×x_t + (1−λ)×EWMA_{t−1}；管制界線依 λ 與 σ 計算。",
        "data_source_text": "單一量測特徵，依板序或時間排序。",
        "smt_interpretation_text": "可偵測錫膏乾涸、鋼板污染、刮刀磨損等緩慢劣化；較 I-MR 對小偏移敏感。判讀問題：是否出現小幅但持續的漂移。下一步：切換 CUSUM 確認偏移是否累積。",
    },
    "cusum": {
        "definition_text": "累積和管制圖，累積偏離目標之量，利於偵測小幅度持續偏移；用於趨勢漂移偵測。",
        "formula_text": "CUSUM+ = max(0, CUSUM+_{t−1} + x_t − kσ)；CUSUM− 同理；k 為 slack，決策界線為 ±hσ。",
        "data_source_text": "單一量測特徵，目標值優先：spec target > spec midpoint > data mean；若偏差過大會回退為 data mean 並標示來源。",
        "smt_interpretation_text": "可判讀製程是否持續偏向規格一側；有助於錫膏乾涸、鋼板污染等緩慢劣化之早期預警。判讀問題：偏移是否為持續累積而非偶發。下一步：切換 I-MR 驗證是否已失控。",
    },
    "scatter_spec": {
        "definition_text": "兩特徵散點圖與規格區，檢視雙變量關係與規格符合性；用於相關分析（Volume vs Height/Area）。",
        "formula_text": "本圖主要為雙變量視覺化與規格區呈現，無單一固定統計公式。",
        "data_source_text": "兩個量測特徵；建議以 Volume 為 X 或 Y，搭配 Height/Area。",
        "smt_interpretation_text": "可判讀體積與面積／高度之關聯、規格區內外分布；有助於偵測錫膏塌陷、鋼板堵塞、開孔匹配問題。",
    },
    "quadrant": {
        "definition_text": "以兩特徵為軸分成四象限，標示各點所屬象限，利於相關分析與異常區辨。",
        "formula_text": "本圖主要為象限分類與視覺呈現，無單一固定統計公式。",
        "data_source_text": "兩個量測特徵；建議以 Volume 搭配 Height 或 Area。",
        "smt_interpretation_text": "可判讀雙特徵組合的區域分布（如高體積高面積、低體積低面積）與異常象限；輔助錫膏塌陷／鋼板問題診斷。",
    },
    "bivariate_outlier": {
        "definition_text": "雙變量離群偵測，標示在兩特徵聯合分布下偏離主群的點。",
        "formula_text": "以平方馬氏距離 d² 判定離群；當 d² > χ²(df=2, α) 時標記為離群點。",
        "data_source_text": "兩個量測特徵；建議以 Volume 搭配 Height/Area。",
        "smt_interpretation_text": "可鎖定體積─面積／高度組合異常的點，利於個案追查與相關異常診斷。",
    },
    "density": {
        "definition_text": "雙變量密度或 Hexbin 圖，顯示兩特徵的聯合分布密度；用於 Volume vs Height/Area 相關分析。",
        "formula_text": "本圖主要為密度估計或計數格視覺化，無單一固定統計公式。",
        "data_source_text": "兩個量測特徵；建議以 Volume 搭配 Height 或 Area。",
        "smt_interpretation_text": "可判讀雙特徵的聚集區與稀疏區，輔助規格或製程設定；有助於錫膏塌陷、鋼板堵塞等相關模式判讀。",
    },
    "anomaly_3f": {
        "definition_text": "以三特徵（如 Volume、Area、Height）計算異常分數，標示多維偏離的點。",
        "formula_text": "各特徵先做 z-score，異常分數 = mean(|z_V|, |z_A|, |z_H|)。",
        "data_source_text": "三個量測特徵（Volume、Area、Height）。",
        "smt_interpretation_text": "可判讀三維組合異常的錫膏點，利於綜合體積／面積／高度的一致性檢查。",
    },
    "consistency_3f": {
        "definition_text": "多特徵一致性視覺化，檢視三特徵間的關係與一致性。",
        "formula_text": "ratio = Volume/Area；diff = z(ratio) − z(Height)；|diff| 越大表示一致性越差。",
        "data_source_text": "三個量測特徵（Volume、Area、Height）。",
        "smt_interpretation_text": "可判讀元件在體積／面積／高度上是否一致、是否有單一特徵偏離。",
    },
    "parallel_coord": {
        "definition_text": "平行座標圖，每筆資料為一折線跨越多軸（特徵），用於多變量模式比較。",
        "formula_text": "本圖主要為多維視覺化，無單一固定統計公式。",
        "data_source_text": "三個量測特徵（Volume、Area、Height），可採樣顯示。",
        "smt_interpretation_text": "可判讀多特徵剖面、群聚與異常線型，利於元件或板位比對。",
    },
    "pass_fail_matrix": {
        "definition_text": "過關／失敗摘要，以三特徵規格結果彙總各特徵的合格率。",
        "formula_text": "依各特徵 USL/LSL 判定 Pass/Fail；統計 pass_count、fail_count 與 pass_rate%。",
        "data_source_text": "三個量測特徵與對應規格（USL/LSL）。",
        "smt_interpretation_text": "可快速比較三特徵的合格率差異，利於優先鎖定風險特徵。",
    },
    "imr_3f": {
        "definition_text": "三特徵並列 I-MR 管制圖：Height / Area / Volume 各自獨立一列，共用 X 軸，方便比較哪個特徵最早超出管制界限。",
        "formula_text": "同 I-MR 單特徵（CL = 均值，UCL/LCL = ±3σ，MR UCL = 3.267 × MR̄）；三列獨立計算各自的界限。",
        "data_source_text": "三個量測特徵（Volume、Area、Height），依板序或時間排列。",
        "smt_interpretation_text": "可判斷問題是單一特徵異常還是整體印刷製程異常；體積異常是否伴隨高度或面積一起失控。判讀問題：三特徵是否同時進入失控狀態。下一步：切換 run_chart_3f 對齊樣本區段。",
    },
    "run_chart_3f": {
        "definition_text": "三特徵並列趨勢圖：Height / Area / Volume 各自獨立一列，共用 X 軸（板序 / 樣本序）；支援 Z-score 標準化模式。",
        "formula_text": "本圖主要為時間序列視覺化，無單一固定統計公式；Z-score 模式將每個特徵轉換為（x − mean）/ σ。",
        "data_source_text": "三個量測特徵，依板序（BoardNo）或時間順序排列；Z-score 模式可消除不同量綱影響。",
        "smt_interpretation_text": "可比較三特徵是否同步漂移、哪個特徵最早出現異常趨勢；Z-score 模式下可直接觀察偏移幅度與分散程度的相對差異。判讀問題：每片 PCS 在三特徵的變化是否同步。下一步：切換 anomaly_3f / consistency_3f 驗證多特徵機制。",
    },
    "ewma_3f": {
        "definition_text": "三特徵並列 EWMA 管制圖：Height / Area / Volume 各自獨立一列，共用 X 軸；支援相對偏移正規化模式。",
        "formula_text": "同 EWMA 單特徵（EWMA_t = λ·x_t + (1−λ)·EWMA_{t−1}）；三列獨立計算；正規化模式以管制界限範圍縮放。",
        "data_source_text": "三個量測特徵，依板序或時間排序。",
        "smt_interpretation_text": "可偵測哪個特徵最早開始漂移；漸進式偏移是否同步；適合早期預警鋼板污染、錫膏乾涸等緩慢劣化。判讀問題：哪個特徵先發生慢性偏移。下一步：切換 cusum_3f 確認是否持續累積。",
    },
    "cusum_3f": {
        "definition_text": "三特徵並列 CUSUM 管制圖：Height / Area / Volume 各自獨立一列，共用 X 軸；可比較三特徵的累積偏移方向與起始點。",
        "formula_text": "同 CUSUM 單特徵（C+ = max(0, C+_{t-1} + x_t − k)，C− 同理）；三列獨立計算各自決策界限 h。",
        "data_source_text": "三個量測特徵，需有目標值，依板序或時間排列。",
        "smt_interpretation_text": "可判讀哪個特徵最早開始持續偏移；三特徵是否在相同區段一起偏向同側；適合鋼板污染、機台補償漂移等早期預警。判讀問題：偏移是否在同一 PCS 區段同步累積。下一步：切換 imr_3f 驗證失控型態。",
    },
    "boxplot_3f": {
        "definition_text": "三特徵整體箱型圖概覽：一次展示 Height / Area / Volume 各自整體分布的箱型圖（不依元件分組），方便直接比較三特徵的中位數、IQR 與離群值。",
        "formula_text": "Q1/Q2/Q3 為 25%/50%/75% 分位數；IQR = Q3−Q1；離群定義為 Q1−1.5×IQR 或 Q3+1.5×IQR 外。",
        "data_source_text": "三個量測特徵全部資料，不依元件分組；支援標準化模式（% of median）以消除量綱差異。",
        "smt_interpretation_text": "可快速比較三特徵的穩定度差異；誰的離群點最多、誰的波動最大、誰的中位數偏移最嚴重。",
    },
}


def get_chart_display_name(chart_id: str, lang: str = "zh_first") -> str:
    """Return display name for chart_id: Chinese-first with English in parens. All user-facing chart names use this."""
    entry = _CATALOG_BY_ID.get(chart_id)
    if not entry:
        return chart_id
    zh = entry.get("display_name_zh", "")
    en = entry.get("display_name_en", "")
    if not zh and not en:
        return entry.get("name", chart_id)
    if lang == "zh_only":
        return zh or en or chart_id
    return f"{zh}（{en}）" if zh and en else (zh or en or chart_id)


def get_chart_description_sections(chart_id: str) -> Dict[str, str]:
    """Return the 4-section description dict with non-empty placeholders."""
    default = {
        "definition_text": _DEFAULT_SECTION,
        "formula_text": _DEFAULT_SECTION,
        "data_source_text": _DEFAULT_SECTION,
        "smt_interpretation_text": _DEFAULT_SECTION,
    }
    sections = CHART_DESCRIPTIONS.get(chart_id, {})
    return {k: sections.get(k, _DEFAULT_SECTION) or _DEFAULT_SECTION for k in default}


def format_chart_description_compact(chart_id: str, context: Optional[Dict[str, Any]] = None) -> str:
    """Return a 1–2 line compact description for above-chart display (definition + current selection)."""
    sections = get_chart_description_sections(chart_id)
    ctx = context or {}
    definition = sections["definition_text"] or ""
    suffix = ""
    if ctx.get("is_incompatible"):
        suffix = _MSG_INCOMPATIBLE_DATA
    elif ctx.get("selected_features") and isinstance(ctx["selected_features"], (list, tuple)):
        suffix = "目前選定：" + "、".join(ctx["selected_features"])
    elif ctx.get("target_col"):
        suffix = "目前選定欄位：" + str(ctx["target_col"])
    if suffix:
        return f"{definition}　{suffix}"
    return definition


def format_chart_description(chart_id: str, context: Optional[Dict[str, Any]] = None) -> str:
    """Format the standard 4-section description string. context may contain target_col, selected_features, is_incompatible, has_data for dynamic data_source line."""
    sections = get_chart_description_sections(chart_id)
    ctx = context or {}
    data_src = sections["data_source_text"]
    if ctx.get("is_incompatible"):
        data_src = _MSG_INCOMPATIBLE_DATA
    elif ctx.get("target_col"):
        data_src = data_src.rstrip("。") + "；目前選定欄位：" + str(ctx["target_col"]) + "。"
    elif ctx.get("selected_features") and isinstance(ctx["selected_features"], (list, tuple)):
        data_src = data_src.rstrip("。") + "；目前選定：" + "、".join(ctx["selected_features"]) + "。"
    parts = [
        "圖表定義說明：",
        sections["definition_text"] or _DEFAULT_SECTION,
        "計算公式說明：",
        sections["formula_text"] or _DEFAULT_SECTION,
        "抓取數值說明：",
        data_src or _DEFAULT_SECTION,
        "SMT 製程統計說明：",
        sections["smt_interpretation_text"] or _DEFAULT_SECTION,
    ]
    return "\n\n".join(parts)


def build_chart_interpretation_sections(
    chart_id: str,
    context: Optional[Dict[str, Any]] = None,
    render_status: Optional[Dict[str, str]] = None,
) -> List[Dict[str, str]]:
    """Return full chart interpretation sections for dialog rendering."""
    sections = get_chart_description_sections(chart_id)
    ctx = context or {}

    data_src = sections["data_source_text"] or _DEFAULT_SECTION
    if ctx.get("is_incompatible"):
        data_src = _MSG_INCOMPATIBLE_DATA
    elif ctx.get("target_col"):
        data_src = data_src.rstrip("。") + f"；目前選定欄位：{ctx['target_col']}。"
    elif ctx.get("selected_features") and isinstance(ctx["selected_features"], (list, tuple)):
        selected = "、".join(str(x) for x in ctx["selected_features"] if str(x).strip())
        if selected:
            data_src = data_src.rstrip("。") + f"；目前選定：{selected}。"

    status = str((render_status or {}).get("status") or "NoData").strip() or "NoData"
    reason = str((render_status or {}).get("reason") or "").strip()
    status_line = f"圖卡狀態：{status}"
    if reason:
        status_line += f"；原因：{reason}"
    data_src = f"{data_src}\n\n{status_line}"

    ill = ""
    if chart_id in ("imr", "run_chart", "xbar_r"):
        ill = "chart_monitoring.png"
    elif chart_id in ("histogram_spec", "capacity_trend"):
        ill = "chart_capability.png"

    return [
        {"title": "圖表用途", "body": sections["definition_text"] or _DEFAULT_SECTION, "illustration": ill},
        {"title": "計算函數/公式說明", "body": sections["formula_text"] or _DEFAULT_SECTION},
        {"title": "資料抓取/來源", "body": data_src},
        {"title": "SMT判讀與下一步", "body": sections["smt_interpretation_text"] or _DEFAULT_SECTION},
    ]


def is_chart_available_for_selection(chart_id: str, selected_features: List[str]) -> bool:
    """Return True if the chart is available for the given selected_features count."""
    entry = _CATALOG_BY_ID.get(chart_id)
    if not entry:
        return False
    # These chart families support 1..N feature rendering through shared resolver.
    if chart_id in {
        "histogram_spec",
        "normality",
        "boxplot",
        "density",
        "anova_parttype",
        "ooc_analysis",
        "shift_detection",
        "drift_detection",
        "outlier_analysis",
        "pattern_recognition",
    }:
        return len(selected_features) >= 1
    if chart_id in {"scatter_spec", "correlation_matrix", "correlation_heatmap"}:
        return len(selected_features) >= 2
    return entry["required_feature_count"] == len(selected_features)


def get_incompatible_reason(chart_id: str, selected_features: List[str]) -> Optional[str]:
    """Return the reason string when chart is not available; None when available."""
    if is_chart_available_for_selection(chart_id, selected_features):
        return None
    entry = _CATALOG_BY_ID.get(chart_id)
    if not entry:
        return MSG_UNKNOWN_CHART
    return entry["incompatible_reason"]


def get_incompatible_short_reason(chart_id: str, selected_features: List[str]) -> Optional[str]:
    """Return a short badge string when chart is not available (e.g. '需 2 特徵', '需 3 特徵'); None when available."""
    if is_chart_available_for_selection(chart_id, selected_features):
        return None
    entry = _CATALOG_BY_ID.get(chart_id)
    if not entry:
        return None
    if chart_id in {
        "histogram_spec",
        "normality",
        "boxplot",
        "density",
        "anova_parttype",
        "ooc_analysis",
        "shift_detection",
        "drift_detection",
        "outlier_analysis",
        "pattern_recognition",
    }:
        return "至少 1 特徵"
    if chart_id in {"scatter_spec", "correlation_matrix", "correlation_heatmap"}:
        return "至少 2 特徵"
    n = entry.get("required_feature_count", 1)
    if n == REQUIRED_SINGLE:
        return "需 1 特徵"
    if n == REQUIRED_DUAL:
        return "需 2 特徵"
    if n == REQUIRED_TRIPLE:
        return "需 3 特徵"
    return f"需 {n} 特徵"


def get_charts_by_category(
    selected_features: Optional[List[str]] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Return charts grouped by category. Each chart dict includes id, name (from get_chart_display_name), category,
    required_feature_count, and (if selected_features given) available: bool, incompatible_reason.
    """
    result: Dict[str, List[Dict[str, Any]]] = {}
    for entry in _CATALOG_BY_ID.values():
        cat = entry.get("category", "")
        if cat not in result:
            result[cat] = []
        item = {k: v for k, v in entry.items()}
        item["name"] = get_chart_display_name(entry["id"])
        if selected_features is not None:
            item["available"] = is_chart_available_for_selection(entry["id"], selected_features)
            item["incompatible_reason"] = get_incompatible_reason(entry["id"], selected_features) or ""
            item["incompatible_short_reason"] = get_incompatible_short_reason(entry["id"], selected_features) or ""
        result[cat].append(item)
    return result


def get_charts_by_ui_group(
    selected_features: Optional[List[str]] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    依五大 UI 分類（製程監控、製程能力、異常根源、變數關係、比較分析）回傳圖表清單。
    用於頂部圖表選單；每項含 id, short_name, name (tooltip), available, incompatible_reason。
    """
    result: Dict[str, List[Dict[str, Any]]] = {g: [] for g in CHART_UI_GROUPS_ORDER}
    for chart_id in CHART_ORDER:
        group = CHART_UI_GROUP_BY_ID.get(chart_id)
        if not group or group not in result:
            continue
        entry = _CATALOG_BY_ID.get(chart_id)
        if not entry:
            continue
        item = {
            "id": chart_id,
            "short_name": CHART_SHORT_NAMES.get(chart_id, entry.get("display_name_zh", chart_id)),
            "name": get_chart_display_name(chart_id),
            "root_cause_stage": CHART_ROOT_CAUSE_STAGE_BY_ID.get(chart_id, ""),
            "next_chart_ids": CHART_NEXT_STEP_BY_ID.get(chart_id, []),
        }
        if selected_features is not None:
            item["available"] = is_chart_available_for_selection(chart_id, selected_features)
            item["incompatible_reason"] = get_incompatible_reason(chart_id, selected_features) or ""
        result[group].append(item)
    return result


def get_charts_by_root_cause_flow(
    selected_features: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Return chart groups in engineering root-cause flow order.
    Each item: {stage_id, label, charts:[...]} where chart entries include
    id, name, short_name, available, incompatible_reason, next_chart_ids.
    """
    grouped_ui = get_charts_by_ui_group(selected_features)
    chart_item_by_id: Dict[str, Dict[str, Any]] = {}
    for group_items in grouped_ui.values():
        for item in group_items:
            chart_item_by_id[item["id"]] = item

    flow_groups: List[Dict[str, Any]] = []
    for stage in ROOT_CAUSE_FLOW_ORDER:
        charts: List[Dict[str, Any]] = []
        for chart_id in stage["chart_ids"]:
            if chart_id in chart_item_by_id:
                charts.append(chart_item_by_id[chart_id])
        flow_groups.append(
            {
                "stage_id": stage["stage_id"],
                "label": stage["label"],
                "charts": charts,
            }
        )
    return flow_groups


def get_payload_slice(payload: Dict[str, Any], chart_id: str) -> Any:
    """
    Return the payload slice for the given chart_id (dict or composite for histogram/capability).
    For histogram_spec and capability: merge dist + cap into one dict (dist with usl/lsl from cap).
    Always include "parameters" field if present (for parameter selector support in tabs).
    """
    entry = _CATALOG_BY_ID.get(chart_id)
    if not entry:
        return {}

    key = entry.get("payload_key")
    if key is None:
        result = {}
    elif isinstance(key, (list, tuple)):
        # (dist, cap) -> merge for HistogramChart/DistributionCapabilityTab
        dist = payload.get(key[0], {}) or {}
        cap = payload.get(key[1], {}) or {}
        result = dict(dist)
        if cap:
            meta = cap.get("metadata", {})
            result["usl"] = meta.get("usl")
            result["lsl"] = meta.get("lsl")
            result.setdefault("analysis_context", {})
            if cap.get("analysis_context"):
                result["analysis_context"] = cap["analysis_context"]
    else:
        val = payload.get(key)
        if val is None:
            # Chart not computed for this feature count — show informative incompatible placeholder
            _reason = get_incompatible_reason(chart_id, payload.get("selected_features") or [])
            return {
                "metadata": {
                    "is_valid": False,
                    "incompatible": True,
                    "error": _reason or "此圖表需選擇不同數量的特徵。",
                },
                "analysis_context": {},
            }
        result = val if isinstance(val, dict) else {}

    # Inject fields only for boxplot chart (comparison_tab consumes them)
    if chart_id == "boxplot":
        if "parameters" in payload:
            result["parameters"] = payload["parameters"]
        for _ctx_key in ("_ctx_refdes", "_ctx_part_type", "_ctx_batch"):
            if _ctx_key in payload:
                result[_ctx_key] = payload[_ctx_key]

    return result


def _mark_feature_fallback(
    fallback: Dict[str, Any],
    *,
    reason: str,
    feature: str,
) -> Dict[str, Any]:
    meta = fallback.get("metadata")
    merged_meta = dict(meta) if isinstance(meta, dict) else {}
    merged_meta["fallback_used"] = True
    merged_meta["fallback_reason"] = reason
    merged_meta["requested_feature"] = feature
    fallback["metadata"] = merged_meta
    return fallback


def get_feature_payload_slice(payload: Dict[str, Any], chart_id: str, feature: str) -> Dict[str, Any]:
    """
    Return chart payload for a specific feature from payload["parameters"].
    Falls back to global get_payload_slice() when per-feature data is missing.
    """
    params = (payload or {}).get("parameters", {}) or {}
    feat = params.get(feature) if feature else None
    if not isinstance(feat, dict):
        fallback = get_payload_slice(payload, chart_id)
        if isinstance(fallback, dict):
            _mark_feature_fallback(
                fallback,
                reason="feature_not_found",
                feature=feature,
            )
        return fallback

    if chart_id == "imr":
        synth = dict(payload or {})
        for key in ("spc", "cap", "dist"):
            if key in feat:
                synth[key] = feat[key]
        return synth

    if chart_id == "histogram_spec":
        dist = feat.get("dist", {}) or {}
        cap = feat.get("cap", {}) or {}
        if isinstance(dist, dict) and dist:
            result = dict(dist)
            cap_meta = cap.get("metadata", {}) if isinstance(cap, dict) else {}
            result["usl"] = cap_meta.get("usl")
            result["lsl"] = cap_meta.get("lsl")
            result["target"] = cap_meta.get("target")
            cap_stats = cap.get("statistics", {}) if isinstance(cap, dict) else {}
            if cap_stats:
                fd_stats = dict(result.get("statistics", {}))
                fd_stats["cpk"] = cap_stats.get("cpk")
                fd_stats["ppk"] = cap_stats.get("ppk")
                result["statistics"] = fd_stats
            return result
        fallback = get_payload_slice(payload, chart_id)
        if isinstance(fallback, dict):
            _mark_feature_fallback(
                fallback,
                reason="feature_histogram_missing",
                feature=feature,
            )
        return fallback

    entry = _CATALOG_BY_ID.get(chart_id) or {}
    payload_key = entry.get("payload_key")
    if isinstance(payload_key, str) and payload_key in feat and isinstance(feat.get(payload_key), dict):
        return feat[payload_key]

    fallback = get_payload_slice(payload, chart_id)
    if isinstance(fallback, dict):
        _mark_feature_fallback(
            fallback,
            reason="feature_payload_key_missing",
            feature=feature,
        )
    return fallback


def get_multi_feature_payload_slice(
    payload: Dict[str, Any],
    chart_id: str,
    features: List[str],
    normalized: bool = False,
) -> Dict[str, Any]:
    """
    Return merged multi-feature payload for single-feature chart families.
    Uses get_feature_payload_slice() to keep UI/report payload logic consistent.
    """
    if not features:
        return get_payload_slice(payload, chart_id)

    feature_data: Dict[str, Dict[str, Any]] = {}
    for feature in features:
        fd = get_feature_payload_slice(payload, chart_id, feature)
        if isinstance(fd, dict) and fd.get("metadata", {}).get("is_valid", False):
            feature_data[feature] = fd

    valid_features = [f for f in features if f in feature_data]
    if not valid_features:
        return get_feature_payload_slice(payload, chart_id, features[0])
    if len(valid_features) == 1:
        return get_feature_payload_slice(payload, chart_id, valid_features[0])

    base = dict(feature_data[valid_features[0]])
    base["_multi_feature"] = True
    base["_features"] = valid_features
    base["_normalized"] = normalized
    base["_feature_data"] = feature_data
    return base


_3F_PARALLEL_PK: Dict[str, str] = {
    "run_chart_3f": "run_chart",
    "imr_3f": "spc",
    "ewma_3f": "ewma",
    "cusum_3f": "cusum",
    "boxplot_3f": "box",
}


def _ensure_chart_payload_schema(chart_id: str, result: Any) -> Dict[str, Any]:
    """Normalize payload shape for UI/report single-source consumption."""
    base = result if isinstance(result, dict) else {}
    normalized: Dict[str, Any] = dict(base)
    normalized["chart_type"] = normalized.get("chart_type") or chart_id
    normalized["data"] = normalized.get("data") if isinstance(normalized.get("data"), dict) else {}
    normalized["statistics"] = normalized.get("statistics") if isinstance(normalized.get("statistics"), dict) else {}
    normalized["analysis_context"] = normalized.get("analysis_context") if isinstance(normalized.get("analysis_context"), dict) else {}
    meta = normalized.get("metadata")
    if not isinstance(meta, dict):
        meta = {}
    if "is_valid" not in meta:
        meta["is_valid"] = bool(base)
    meta.setdefault("error", "" if meta.get("is_valid") else "無資料。")
    normalized["metadata"] = meta
    return normalized


def _resolve_3f_parallel_payload(payload: Dict[str, Any], chart_id: str, normalized: bool = False) -> Dict[str, Any]:
    params = (payload or {}).get("parameters", {}) or {}
    if not params:
        return {
            "metadata": {"is_valid": False, "error": "無特徵參數資料，請先執行分析。"},
            "analysis_context": {},
        }
    pk = _3F_PARALLEL_PK.get(chart_id)
    if not pk:
        return {
            "metadata": {"is_valid": False, "error": f"不支援的 3F 圖表: {chart_id}"},
            "analysis_context": {},
        }

    feature_data: Dict[str, Dict[str, Any]] = {}
    if chart_id == "boxplot_3f":
        for feat, fp in params.items():
            if pk not in fp:
                continue
            fd = fp.get(pk) or {}
            cap_meta = ((fp.get("cap") or {}).get("metadata") or {})
            merged = dict(fd)
            merged["usl"] = cap_meta.get("usl")
            merged["lsl"] = cap_meta.get("lsl")
            feature_data[feat] = merged
        if not feature_data:
            return {"metadata": {"is_valid": False, "error": "無箱型圖資料。"}, "analysis_context": {}}
        return {
            "metadata": {"is_valid": True},
            "analysis_context": {},
            "_overview_3f": True,
            "_features": list(feature_data.keys()),
            "_normalized": normalized,
            "_feature_data": feature_data,
        }

    for feat, fp in params.items():
        if pk in fp and isinstance(fp.get(pk), dict):
            feature_data[feat] = fp.get(pk)
    if not feature_data:
        return {"metadata": {"is_valid": False, "error": f"無 '{pk}' 資料，請確認已執行分析。"}, "analysis_context": {}}
    return {
        "metadata": {"is_valid": True},
        "analysis_context": {},
        "_multi_feature": True,
        "_features": list(feature_data.keys()),
        "_normalized": normalized,
        "_feature_data": feature_data,
    }


def resolve_chart_payload(
    payload: Dict[str, Any],
    chart_id: str,
    features: Optional[List[str]] = None,
    normalized: bool = False,
    context: str = "ui",
) -> Dict[str, Any]:
    """
    Single-source payload resolver for both UI and report paths.
    Keeps 1F/2F/3F selection, fallback semantics, and schema normalization consistent.
    """
    _ = context  # reserved for future context-specific diagnostics
    if chart_id in _3F_PARALLEL_PK:
        return _ensure_chart_payload_schema(chart_id, _resolve_3f_parallel_payload(payload or {}, chart_id, normalized=normalized))

    selected = list((payload or {}).get("selected_features") or [])
    active_features = list(features or selected)
    if not active_features:
        return _ensure_chart_payload_schema(chart_id, get_payload_slice(payload or {}, chart_id))

    if len(active_features) == 1:
        return _ensure_chart_payload_schema(chart_id, get_feature_payload_slice(payload or {}, chart_id, active_features[0]))

    entry = _CATALOG_BY_ID.get(chart_id, {})
    required_count = entry.get("required_feature_count", REQUIRED_SINGLE)
    if required_count != REQUIRED_SINGLE:
        payload_n = len(selected)
        if payload_n == 1:
            if required_count == REQUIRED_DUAL and len(active_features) == 2:
                dual_params = (payload or {}).get("dual_parameters", {}) or {}
                f0, f1 = active_features[0], active_features[1]
                pair_data = dual_params.get(f"{f0}+{f1}") or dual_params.get(f"{f1}+{f0}")
                if isinstance(pair_data, dict) and chart_id in pair_data:
                    return _ensure_chart_payload_schema(chart_id, pair_data.get(chart_id))
            elif required_count == REQUIRED_TRIPLE and len(active_features) == 3:
                triple_params = (payload or {}).get("triple_parameters", {}) or {}
                if chart_id in triple_params:
                    return _ensure_chart_payload_schema(chart_id, triple_params.get(chart_id))
        return _ensure_chart_payload_schema(chart_id, get_payload_slice(payload or {}, chart_id))

    if chart_id == "imr" and len(active_features) != 1:
        reason = get_incompatible_reason("imr", active_features) or "此圖表僅支援單一特徵。"
        return _ensure_chart_payload_schema(chart_id, {
            "metadata": {"is_valid": False, "incompatible": True, "error": reason},
            "analysis_context": {},
        })

    if chart_id == "histogram_spec":
        return _ensure_chart_payload_schema(
            chart_id,
            get_multi_feature_payload_slice(payload or {}, chart_id, active_features, normalized=normalized),
        )

    if chart_id == "density" and len(active_features) >= 2:
        # Prefer dual-feature density payload when available; otherwise fallback to
        # per-feature univariate density merge.
        direct = get_payload_slice(payload or {}, chart_id)
        if isinstance(direct, dict) and direct.get("metadata", {}).get("is_valid", False):
            return _ensure_chart_payload_schema(chart_id, direct)

    payload_key = entry.get("payload_key")
    if isinstance(payload_key, str):
        return _ensure_chart_payload_schema(
            chart_id,
            get_multi_feature_payload_slice(payload or {}, chart_id, active_features, normalized=normalized),
        )
    return _ensure_chart_payload_schema(chart_id, get_feature_payload_slice(payload or {}, chart_id, active_features[0]))
