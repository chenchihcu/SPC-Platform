"""
chart_router.py
---------------
圖表可用性判斷模組 — SMT SPI/SPC 統計分析平台（PySide6 版）

判斷層級（由外到內，任一層未通過即停止）：
    Layer 0 : 量測記錄已載入
    Layer 1 : 欄位映射已完成
    Layer 2+4 : 座標檔/元件指標已載入  → 影響空間熱圖
    Layer 3 : 分析批次已設定           → 影響時序類圖表（I-MR、趨勢圖、EWMA、CUSUM）
    Layer 5 : 元件類型已設定           → 影響柏拉圖、Pass/Fail 矩陣
    Layer 6 : 量測選取數(1/2/3)        → 決定基本可用圖表集合（以 🔒 顯示，非隱藏）

公開介面：
    get_available_charts(ctx: ChartContext) -> ChartResult
    get_condition_blocked_ids(ctx: ChartContext) -> frozenset[str]
    ROUTER_TO_REGISTRY_ID : dict[str, str]  — router key → chart_registry ID 對照
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# 常數：所有圖表定義
# ---------------------------------------------------------------------------

ALL_CHARTS: dict[str, str] = {
    # 單選（n=1）
    "imr":           "個別值與移動極差圖（I-MR）",
    "run_chart":     "趨勢圖（Run Chart）",
    "ewma":          "指數加權移動平均圖（EWMA）",
    "cusum":         "累積和管制圖（CUSUM）",
    "histogram":     "分布與能力（Histogram）",
    "normality":     "常態分析（Normality）",
    "repeatability": "重複異常點分析（Repeatability）",
    # 雙選（n=2）
    "density_1":     "密度圖（Density）",
    "scatter":       "散點與規格區（Scatter）",
    "quadrant":      "四象限（Quadrant）",
    "bivariate":     "雙變量離群（Bivariate Outlier）",
    "subgroup":      "子群比較（Subgroup Comparison）",
    # 三選（n=3）
    "anomaly":       "三特徵異常分數（Anomaly Score）",
    "consistency":   "多特徵一致性（Consistency）",
    "parallel":      "平行座標（Parallel Coordinates）",
    "passfail":      "過關/失敗矩陣（Pass/Fail）",
    # 共用（需額外條件）
    "boxplot":       "箱型圖（Boxplot）",
    "heatmap":       "空間熱圖（Spatial Heatmap）",
    "pareto":        "柏拉圖（Pareto）",
}

# 各圖表所需的最低量測選取數
CHART_MIN_N: dict[str, int] = {
    "imr": 1, "run_chart": 1, "ewma": 1, "cusum": 1,
    "histogram": 1, "normality": 1,
    "repeatability": 1, "density_1": 2,
    "scatter": 2, "quadrant": 2, "bivariate": 2, "subgroup": 2,
    "anomaly": 3, "consistency": 3, "parallel": 3, "passfail": 3,
    "boxplot": 1, "heatmap": 1, "pareto": 1,
}

TEMPORAL_CHARTS: frozenset[str] = frozenset({"imr", "run_chart", "ewma", "cusum"})
SPATIAL_CHARTS:  frozenset[str] = frozenset({"heatmap"})
TYPE_CHARTS:     frozenset[str] = frozenset({"pareto", "passfail"})

# chart_router key → project chart_registry ID 對照表
ROUTER_TO_REGISTRY_ID: dict[str, str] = {
    "imr":           "imr",
    "run_chart":     "run_chart",
    "ewma":          "ewma",
    "cusum":         "cusum",
    "histogram":     "histogram_spec",
    "normality":     "normality",
    "repeatability": "repeated_offender",
    "density_1":     "density",
    "scatter":       "scatter_spec",
    "quadrant":      "quadrant",
    "bivariate":     "bivariate_outlier",
    "subgroup":      "subgroup",
    "anomaly":       "anomaly_3f",
    "consistency":   "consistency_3f",
    "parallel":      "parallel_coord",
    "passfail":      "pass_fail_matrix",
    "boxplot":       "boxplot",
    "heatmap":       "spatial_heatmap",
    "pareto":        "pareto",
}


# ---------------------------------------------------------------------------
# 資料結構
# ---------------------------------------------------------------------------

@dataclass
class ChartContext:
    """所有判斷條件，由呼叫端從 UI 狀態組裝後傳入。"""
    # Layer 0-1：資料狀態（必要前提）
    meas_loaded:        bool   # 量測記錄：已載入且非空
    mapping_done:       bool   # 欄位映射：is_valid=True
    # Layer 2+4：座標（coord_loaded = 座標檔已載入 AND 元件指標已設定）
    coord_loaded:       bool
    # Layer 3：時序
    has_batch:          bool   # 分析批次：非「全部」且非空
    # Layer 5：分類
    has_component_type: bool   # 元件類型：非「全部」且非空
    # Layer 6：量測選取數
    n_selected:         int    # 1 / 2 / 3


@dataclass
class ChartResult:
    """get_available_charts() 的完整回傳結果。"""
    available:    list[str] = field(default_factory=list)
    blocked:      list[str] = field(default_factory=list)
    block_reason: Optional[str] = None   # Layer 0/1 全擋時的說明
    warnings:     list[str] = field(default_factory=list)  # 部分條件缺失說明


# ---------------------------------------------------------------------------
# 核心判斷邏輯
# ---------------------------------------------------------------------------

def get_available_charts(ctx: ChartContext) -> ChartResult:
    """依 ChartContext 判斷每張圖表可用性，回傳 ChartResult。"""
    result = ChartResult()

    # ── Layer 0 ──────────────────────────────────────────────────────────
    if not ctx.meas_loaded:
        result.block_reason = "量測記錄未載入，請先完成資料準備。"
        result.blocked = list(ALL_CHARTS.keys())
        return result

    # ── Layer 1 ──────────────────────────────────────────────────────────
    if not ctx.mapping_done:
        result.block_reason = "欄位映射未完成，請先完成欄位對應設定。"
        result.blocked = list(ALL_CHARTS.keys())
        return result

    # ── Layer 3-5：條件警告（不阻擋全部圖表，但隱藏特定圖表）────────────
    if not ctx.has_batch:
        result.warnings.append("「分析批次」未設定 → I-MR、趨勢圖、EWMA、CUSUM 已隱藏")
    if not ctx.coord_loaded:
        result.warnings.append("「座標檔/元件指標」未設定 → 空間熱圖已隱藏")
    if not ctx.has_component_type:
        result.warnings.append("「元件類型」未設定 → 柏拉圖、Pass/Fail 矩陣已隱藏")

    # ── Layer 6：逐一判斷每張圖表 ────────────────────────────────────────
    for key in ALL_CHARTS:
        if _is_available(key, ctx):
            result.available.append(key)
        else:
            result.blocked.append(key)

    return result


def _is_available(key: str, ctx: ChartContext) -> bool:
    """單一圖表可用性判斷，回傳 True = 可顯示。"""
    if ctx.n_selected < CHART_MIN_N.get(key, 1):
        return False
    if key in TEMPORAL_CHARTS and not ctx.has_batch:
        return False
    if key in SPATIAL_CHARTS and not ctx.coord_loaded:
        return False
    if key in TYPE_CHARTS and not ctx.has_component_type:
        return False
    return True


def get_condition_blocked_ids(ctx: ChartContext) -> frozenset[str]:
    """
    回傳因資料條件（Layer 0-5）而應被「隱藏」的 router key 集合。
    不含 Layer 6（特徵數不符），那些以 🔒 顯示而非隱藏。

    UI 使用此函式決定哪些圖表從清單中移除（而非灰化）。
    """
    if not ctx.meas_loaded or not ctx.mapping_done:
        return frozenset(ALL_CHARTS.keys())

    blocked: set[str] = set()
    if not ctx.has_batch:
        blocked.update(TEMPORAL_CHARTS)
    if not ctx.coord_loaded:
        blocked.update(SPATIAL_CHARTS)
    if not ctx.has_component_type:
        blocked.update(TYPE_CHARTS)
    return frozenset(blocked)
