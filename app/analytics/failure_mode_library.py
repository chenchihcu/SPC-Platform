"""
Failure mode knowledge base for SPI process diagnostics.
Static structure: symptom_pattern, statistical_indicators, typical_root_cause, recommended_actions.
Used by anomaly classifier and root cause engine; read-only data.
"""
from typing import Dict, Any, List

FAILURE_MODES: List[Dict[str, Any]] = [
    {
        "id": "stencil_clogging",
        "name": "鋼板堵塞",
        "symptom_pattern": "局部少錫、點狀缺印",
        "statistical_indicators": ["spatial OOS cluster", "LCL violation density"],
        "typical_root_cause": "鋼板開孔殘膏或清潔不足",
        "recommended_actions": ["增加鋼板清潔頻率", "檢查刮刀壓力與速度"],
        "standard_ref": "IPC-7525 (stencil aperture maintenance)",
    },
    {
        "id": "paste_drying",
        "name": "錫膏乾涸",
        "symptom_pattern": "隨板序或時間 volume 下降",
        "statistical_indicators": ["run chart decline", "EWMA drift"],
        "typical_root_cause": "環境濕度或錫膏曝露時間過長",
        "recommended_actions": ["縮短開罐後使用時間", "確認環境溫濕度"],
        "standard_ref": "J-STD-005 (solder paste stencil life / open time)",
        "paste_type_sensitivity": {"Type 5": "HIGH", "Type 6": "HIGH", "Type 4": "MEDIUM", "Type 3": "LOW"},
    },
    {
        "id": "aperture_mismatch",
        "name": "開孔設計不匹配",
        "symptom_pattern": "同 footprint 多位置變異大",
        "statistical_indicators": ["footprint variance imbalance", "boxplot spread"],
        "typical_root_cause": "鋼板開孔與 pad 設計不一致",
        "recommended_actions": ["檢討鋼板開孔設計", "比對 CAD 與鋼板", "確認 Area Ratio >= 0.66"],
        "standard_ref": "IPC-7525 Sec 4.2 (area ratio >= 0.66)",
    },
    {
        "id": "printer_alignment_shift",
        "name": "印刷機對位偏移",
        "symptom_pattern": "空間系統性偏移或邊緣聚集",
        "statistical_indicators": ["spatial OOS at edge", "UCL/LCL density pattern"],
        "typical_root_cause": "夾具或相機對位偏移",
        "recommended_actions": ["執行對位校正", "檢查夾具與支撐"],
        "standard_ref": "IPC-7527 (SPI measurement & alignment)",
    },
    {
        "id": "squeegee_pressure",
        "name": "刮刀壓力異常",
        "symptom_pattern": "整體偏高/偏低或不均",
        "statistical_indicators": ["global mean shift", "capability Cpk"],
        "typical_root_cause": "刮刀壓力或角度設定不當",
        "recommended_actions": ["調整刮刀壓力與角度", "確認刮刀磨耗"],
        "standard_ref": None,
    },
    {
        "id": "localized_stencil_wear",
        "name": "鋼板局部磨損",
        "symptom_pattern": "特定區域持續異常",
        "statistical_indicators": ["repeated offender", "spatial heatmap cluster"],
        "typical_root_cause": "鋼板局部磨損或損傷",
        "recommended_actions": ["檢查鋼板表面", "規劃鋼板更換"],
        "standard_ref": "IPC-7525 (stencil life cycle management)",
    },
    {
        "id": "instability",
        "name": "製程不穩",
        "symptom_pattern": "管制界線違反率偏高",
        "statistical_indicators": ["I-MR OOC rate"],
        "typical_root_cause": "製程或設備變異過大",
        "recommended_actions": ["確認設備參數穩定性", "檢視原料與環境變因"],
        "standard_ref": None,
    },
    {
        "id": "spatial_oos",
        "name": "空間 OOS 聚集",
        "symptom_pattern": "OOS 在 PCB 上呈聚集",
        "statistical_indicators": ["spatial OOS density"],
        "typical_root_cause": "鋼板、對位或局部印刷問題",
        "recommended_actions": ["檢視空間熱圖 OOS 密度模式", "檢查鋼板與對位"],
        "standard_ref": "IPC-7525 / IPC-7527",
    },
]


def get_failure_mode(failure_mode_id: str) -> Dict[str, Any] | None:
    """Return failure mode dict by id or None."""
    for fm in FAILURE_MODES:
        if fm.get("id") == failure_mode_id:
            return fm
    return None


