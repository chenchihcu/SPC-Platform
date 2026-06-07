"""
Heuristic process diagnosis for the engineering dashboard (not SPC formula authority).

Thresholds are engineering defaults; tune via constants below. See docs/decision-log.md.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TypedDict
from app.analytics.ooc_utils import first_group_share

# --- Thresholds (documented; not from docs/governance/SPC_RULES.md) ---
THRESHOLDS_VERSION = "2026-04-05"
THRESH_MEAN_SHIFT_ABS_PCT = 30.0  # |mean_shift_pct| vs spec width (already in %)
THRESH_STD_SPEC_RATIO = 0.30
THRESH_CLUSTER_RATIO = 0.05
STEP_STENCIL_OOS_VS_OVERALL_MULT = 1.5
STEP_STENCIL_OOS_MIN_ABSOLUTE = 0.01
CP_HIGH_FOR_OFFSET = 1.67
CPK_LOW_FOR_OFFSET = 1.33
CP_LOW_VARIATION = 1.33
OOS_RATE_HIGH = 0.02  # 2%
OOS_RATE_MEDIUM = 0.005  # 0.5%
CPK_ACCEPTABLE_FOR_SPEC_TIGHT = 1.33
TOP_GROUP_CONCENTRATION = 0.50  # first group oos_count / total_oos

IssueType = Literal[
    "unknown",
    "mixed",
    "process_center_shift",
    "variation_too_large",
    "local_cluster",
    "step_stencil",
    "process_offset",
    "variation_problem",
    "spec_too_tight",
]

Priority = Literal["low", "medium", "high"]

DefectPattern = Literal[
    "same_component",
    "same_location",
    "same_panel_area",
    "step_stencil_area",
    "random",
    "mixed",
    "unknown",
]


class ProcessDiagnosisInputs(TypedDict, total=False):
    mean_shift_pct: Optional[float]
    std_spec_ratio: Optional[float]
    cp: Optional[float]
    cpk: Optional[float]
    oos_rate: Optional[float]
    cluster_ratio: Optional[float]
    step_stencil_oos_rate: Optional[float]
    top_oos_refdes: List[Dict[str, Any]]
    top_oos_pad: List[Dict[str, Any]]
    total_oos_count: int
    abnormal_cluster_location: Optional[str]


class ProcessDiagnosisResult(TypedDict):
    issue_type: IssueType
    issue_type_display_zh: str
    root_cause_zh: str
    recommended_action_zh: str
    priority: Priority
    process_diagnosis_flags: Dict[str, bool]
    defect_pattern: DefectPattern
    defect_pattern_zh: str
    thresholds_version: str


def _priority_from_oos_rate(oos_rate: Optional[float]) -> Priority:
    if oos_rate is None:
        return "low"
    if oos_rate > OOS_RATE_HIGH:
        return "high"
    if oos_rate > OOS_RATE_MEDIUM:
        return "medium"
    return "low"


def _bool_center_shift(mean_shift_pct: Optional[float]) -> bool:
    if mean_shift_pct is None:
        return False
    return abs(float(mean_shift_pct)) > THRESH_MEAN_SHIFT_ABS_PCT


def _bool_variation_too_large(std_spec_ratio: Optional[float]) -> bool:
    if std_spec_ratio is None:
        return False
    return float(std_spec_ratio) > THRESH_STD_SPEC_RATIO


def _bool_local_cluster(cluster_ratio: Optional[float]) -> bool:
    if cluster_ratio is None:
        return False
    return float(cluster_ratio) > THRESH_CLUSTER_RATIO


def _bool_step_stencil(
    step_rate: Optional[float],
    overall_oos: Optional[float],
) -> bool:
    if step_rate is None or overall_oos is None:
        return False
    thr = max(float(overall_oos) * STEP_STENCIL_OOS_VS_OVERALL_MULT, STEP_STENCIL_OOS_MIN_ABSOLUTE)
    return float(step_rate) > thr


def _bool_process_offset(cp: Optional[float], cpk: Optional[float]) -> bool:
    if cp is None or cpk is None:
        return False
    return float(cp) >= CP_HIGH_FOR_OFFSET and float(cpk) < CPK_LOW_FOR_OFFSET


def _bool_variation_problem(cp: Optional[float]) -> bool:
    if cp is None:
        return False
    return float(cp) < CP_LOW_VARIATION


def _bool_spec_too_tight(oos_rate: Optional[float], cpk: Optional[float]) -> bool:
    if oos_rate is None or cpk is None:
        return False
    return float(oos_rate) > OOS_RATE_HIGH and float(cpk) >= CPK_ACCEPTABLE_FOR_SPEC_TIGHT


def _compute_defect_pattern(
    *,
    step_stencil_diagnosis: bool,
    top_oos_refdes: List[Dict[str, Any]],
    top_oos_pad: List[Dict[str, Any]],
    total_oos: int,
    abnormal_cluster_location: Optional[str],
    cluster_ratio: Optional[float],
) -> tuple[DefectPattern, str]:
    tags: List[str] = []
    primary: DefectPattern = "unknown"

    if step_stencil_diagnosis:
        tags.append("階梯鋼網區")
        primary = "step_stencil_area"

    ref_share = first_group_share(top_oos_refdes, total_oos)
    if ref_share is not None and ref_share >= TOP_GROUP_CONCENTRATION:
        tags.append("同元件集中")
        if primary == "unknown":
            primary = "same_component"

    pad_share = first_group_share(top_oos_pad, total_oos)
    if pad_share is not None and pad_share >= TOP_GROUP_CONCENTRATION:
        tags.append("同焊墊／位置集中")
        if primary in ("unknown", "same_component"):
            primary = "same_location" if primary == "unknown" else primary

    if abnormal_cluster_location:
        tags.append("同面板區域")
        if primary == "unknown":
            primary = "same_panel_area"

    if not tags:
        if total_oos <= 0:
            return "unknown", "—"
        if cluster_ratio is not None and float(cluster_ratio) <= THRESH_CLUSTER_RATIO:
            primary = "random"
            tags.append("隨機／分散")
        else:
            primary = "random"
            tags.append("隨機／分散")

    if len(tags) >= 2:
        primary = "mixed"

    zh = "；".join(tags) if tags else "—"
    return primary, zh


_ISSUE_MESSAGES: Dict[IssueType, tuple[str, str]] = {
    "unknown": ("資料不足，無法判斷主因。", "請確認量測、規格與樣本數後重新分析。"),
    "mixed": ("多項訊號同時異常（中心、變異、群集或階梯鋼網等）。", "依優先順序排查：群集與階梯區 → 對位與印刷參數 → 規格與來料。"),
    "process_center_shift": ("製程中心相對目標明顯偏移。", "調整印刷參數使均值回到目標；確認刮刀壓力、脫模與鋼網張力。"),
    "variation_too_large": ("製程變異相對規格寬度偏大。", "降低製程變異：清潔鋼網、檢查錫膏與環境；必要時檢視 SPI 閾值與來料。"),
    "local_cluster": ("異常有空間／時間群集傾向。", "檢查特定 RefDes／焊墊與軌跡；排查刮刀、鋼網局部堵塞或治具。"),
    "step_stencil": ("階梯鋼網區 OOS 相對整體偏高。", "優先檢查階梯區印刷條件、錫膏量與鋼網階梯設計。"),
    "process_offset": ("Cp 足夠但 Cpk 偏低，顯示中心偏移為主。", "以對位與均值調整為主，變異次要。"),
    "variation_problem": ("Cp 偏低，整體變異能力不足。", "著重降低變異與來料／製程穩定性。"),
    "spec_too_tight": ("OOS 偏高但 Cpk 尚可，規格可能過緊或量測邊界。", "與客戶／工程檢討規格與 SPI 判讀；確認是否需放寬或分區規格。"),
}

_DISPLAY_ZH: Dict[IssueType, str] = {
    "unknown": "—",
    "mixed": "混合",
    "process_center_shift": "偏移",
    "variation_too_large": "變異",
    "local_cluster": "局部",
    "step_stencil": "階梯鋼網",
    "process_offset": "偏移",
    "variation_problem": "變異",
    "spec_too_tight": "變異",
}


def run_process_diagnosis(inputs: ProcessDiagnosisInputs) -> ProcessDiagnosisResult:
    msp = inputs.get("mean_shift_pct")
    ssr = inputs.get("std_spec_ratio")
    cp = inputs.get("cp")
    cpk = inputs.get("cpk")
    oos = inputs.get("oos_rate")
    cr = inputs.get("cluster_ratio")
    step_r = inputs.get("step_stencil_oos_rate")
    top_r = list(inputs.get("top_oos_refdes") or [])
    top_p = list(inputs.get("top_oos_pad") or [])
    total_oos = int(inputs.get("total_oos_count") or 0)
    ab_loc = inputs.get("abnormal_cluster_location")

    flags: Dict[str, bool] = {
        "center_shift": _bool_center_shift(msp),
        "variation_too_large": _bool_variation_too_large(ssr),
        "local_cluster": _bool_local_cluster(cr),
        "step_stencil_issue": _bool_step_stencil(step_r, oos),
        "process_offset": _bool_process_offset(cp, cpk),
        "variation_problem": _bool_variation_problem(cp),
        "spec_too_tight": _bool_spec_too_tight(oos, cpk),
    }

    # Layer 5 display: four headline buckets (user spec)
    process_diagnosis_flags = {
        "center_shift": flags["center_shift"],
        "variation_too_large": flags["variation_too_large"] or flags["variation_problem"],
        "spec_too_tight": flags["spec_too_tight"],
        "step_stencil_issue": flags["step_stencil_issue"],
    }

    active: List[IssueType] = []
    if flags["step_stencil_issue"]:
        active.append("step_stencil")
    if flags["local_cluster"]:
        active.append("local_cluster")
    if flags["center_shift"]:
        active.append("process_center_shift")
    if flags["process_offset"]:
        active.append("process_offset")
    if flags["variation_too_large"]:
        active.append("variation_too_large")
    if flags["variation_problem"]:
        active.append("variation_problem")
    if flags["spec_too_tight"]:
        active.append("spec_too_tight")

    # Deduplicate preserving order
    seen: set[str] = set()
    unique_active: List[IssueType] = []
    for a in active:
        if a not in seen:
            seen.add(a)
            unique_active.append(a)

    if len(unique_active) > 1:
        issue: IssueType = "mixed"
    elif len(unique_active) == 1:
        issue = unique_active[0]
    else:
        issue = "unknown"

    root, action = _ISSUE_MESSAGES[issue]
    pr = _priority_from_oos_rate(oos)

    dpat, dpat_zh = _compute_defect_pattern(
        step_stencil_diagnosis=flags["step_stencil_issue"],
        top_oos_refdes=top_r,
        top_oos_pad=top_p,
        total_oos=total_oos,
        abnormal_cluster_location=ab_loc,
        cluster_ratio=cr,
    )

    return ProcessDiagnosisResult(
        issue_type=issue,
        issue_type_display_zh=_DISPLAY_ZH[issue],
        root_cause_zh=root,
        recommended_action_zh=action,
        priority=pr,
        process_diagnosis_flags=process_diagnosis_flags,
        defect_pattern=dpat,
        defect_pattern_zh=dpat_zh,
        thresholds_version=THRESHOLDS_VERSION,
    )
