"""
IPC references for SMT diagnostics.

This module keeps lightweight, auditable references:
- standard code / edition
- clause code
- Chinese engineering summary
- optional action checklist
"""
from typing import Any, Dict, List


IPC_REFERENCES_BY_RULE_ID: Dict[str, List[Dict[str, Any]]] = {
    "volume_decline_along_board": [
        {
            "std": "J-STD-005",
            "edition": "current",
            "clause": "ShelfLife/OpenTime",
            "summary_zh": "錫膏需在受控開封與暴露時間內使用；超時易導致轉印量下降與連續趨勢下滑。",
            "actions": ["確認開罐時間紀錄", "檢查環境溫濕度與停線暴露時長"],
        },
        {
            "std": "IPC-7525",
            "edition": "current",
            "clause": "ProcessControl",
            "summary_zh": "模板印刷需建立清潔頻率與製程控制窗口，避免連續印刷後轉印效率惡化。",
            "actions": ["縮短清潔週期", "檢討刮刀速度/壓力設定"],
        },
    ],
    "edge_spatial_cluster": [
        {
            "std": "IPC-7525",
            "edition": "current",
            "clause": "StencilAlignmentSupport",
            "summary_zh": "邊緣區域異常聚集常與模板張力、支撐或對位穩定性相關，需檢查治具與印刷校正。",
            "actions": ["檢查PCB支撐與夾持", "重新執行模板/視覺對位校正"],
        },
        {
            "std": "IPC-7527",
            "edition": "current",
            "clause": "SPIUsage",
            "summary_zh": "SPI 空間分佈應用於辨識系統性位置偏差，並回饋至印刷設備校正流程。",
            "actions": ["比對SPI熱區與設備校正紀錄", "檢查相機/基準點設定"],
        },
    ],
    "footprint_variance_imbalance": [
        {
            "std": "IPC-7525",
            "edition": "current",
            "clause": "ApertureDesign",
            "summary_zh": "同足印位置若呈現顯著變異落差，應回查開孔設計與製程能力匹配。",
            "actions": ["審查開孔幾何一致性", "比對同足印位置之模板區域磨耗"],
        },
        {
            "std": "IPC-7351",
            "edition": "current",
            "clause": "LandPatternConsistency",
            "summary_zh": "焊墊設計一致性會影響錫膏沉積穩定性，建議與模板開孔協同檢核。",
            "actions": ["核對Land Pattern與模板資料源一致性"],
        },
    ],
    "consistent_volume_high": [
        {
            "std": "IPC-A-610",
            "edition": "current",
            "clause": "SolderConditions",
            "summary_zh": "整體過量沉積可能提高橋接與外觀不良風險，應以可接受性準則回看缺陷型態。",
            "actions": ["抽查橋接/錫珠缺陷比例", "回調模板開孔或印刷偏移補償"],
        },
        {
            "std": "J-STD-001",
            "edition": "current",
            "clause": "SolderingProcessControl",
            "summary_zh": "焊接製程需維持受控參數，持續偏高屬於製程中心漂移訊號，需進行矯正。",
            "actions": ["檢討目標值與設備補償係數", "建立偏移告警門檻"],
        },
    ],
    "consistent_volume_low": [
        {
            "std": "IPC-A-610",
            "edition": "current",
            "clause": "SolderConditions",
            "summary_zh": "整體少錫沉積會提高開路與潤濕不足風險，應依可接受性標準回查缺陷分佈。",
            "actions": ["抽查少錫/開路缺陷", "檢查刮刀壓力與模板釋放性"],
        },
        {
            "std": "J-STD-001",
            "edition": "current",
            "clause": "ProcessVerification",
            "summary_zh": "若沉積中心持續偏低，需驗證製程參數與材料狀態是否偏離控制計畫。",
            "actions": ["檢查錫膏黏度與回溫流程", "校正設備參數與列印速度"],
        },
    ],
    "cusum_trend_drift": [
        {
            "std": "IPC-9191",
            "edition": "current",
            "clause": "ManufacturingDataQuality",
            "summary_zh": "持續漂移需結合製程資料與設備事件追溯，建立閉環矯正機制。",
            "actions": ["對齊漂移區段與設備維護事件", "建立漂移超門檻自動通報"],
        },
        {
            "std": "J-STD-001",
            "edition": "current",
            "clause": "ProcessControl",
            "summary_zh": "製程超出受控狀態時，應執行原因調查、矯正與再驗證。",
            "actions": ["啟動異常調查流程", "完成矯正後執行再驗證批次"],
        },
    ],
    "cusum_local_shift": [
        {
            "std": "IPC-7527",
            "edition": "current",
            "clause": "SPITrendUse",
            "summary_zh": "局部偏移可透過 SPI 趨勢圖追蹤特定時段或板次，辨識短期干擾源。",
            "actions": ["標記異常板次並回查生產條件", "針對區段做局部設備點檢"],
        }
    ],
    "localized_deviation_bias": [
        {
            "std": "IPC-7525",
            "edition": "current",
            "clause": "StencilWearMaintenance",
            "summary_zh": "局部單側偏差常見於模板局部磨耗或印刷壓力不均，需執行區域性檢修。",
            "actions": ["檢查模板局部磨耗", "驗證刮刀平行度與壓力均勻性"],
        },
        {
            "std": "IPC-7095",
            "edition": "current",
            "clause": "BTCAssemblyControl",
            "summary_zh": "對細間距與底部端子元件，沉積均勻度偏差會放大組裝缺陷風險，須優先管控。",
            "actions": ["針對高風險元件加嚴檢查頻率"],
        },
    ],
    "normality_test_fail": [
        {
            "std": "J-STD-001",
            "edition": "current",
            "clause": "ProcessControl",
            "summary_zh": "若分布偏離常態，需回到製程條件與資料來源一致性進行調查與再驗證。",
            "actions": ["分群檢查班別/機台/批次資料一致性", "完成調整後重新執行能力與常態檢驗"],
        },
        {
            "std": "IPC-9191",
            "edition": "current",
            "clause": "ManufacturingDataQuality",
            "summary_zh": "製程決策需基於可追溯資料品質，異常分布需先排除資料混流與量測偏差。",
            "actions": ["檢查資料分群與映射完整性", "確認量測系統與資料管道一致性"],
        },
    ],
}


IPC_REFERENCES_BY_FAILURE_MODE_ID: Dict[str, List[Dict[str, Any]]] = {
    "stencil_clogging": [
        {
            "std": "IPC-7525",
            "edition": "current",
            "clause": "StencilCleaning",
            "summary_zh": "模板清潔與保養週期需依產品特性與印刷負荷建立標準作業。",
            "actions": ["提高清潔頻率", "確認清潔方式與耗材相容性"],
        }
    ],
    "paste_drying": IPC_REFERENCES_BY_RULE_ID["volume_decline_along_board"],
    "aperture_mismatch": IPC_REFERENCES_BY_RULE_ID["footprint_variance_imbalance"],
    "printer_alignment_shift": IPC_REFERENCES_BY_RULE_ID["edge_spatial_cluster"],
    "squeegee_pressure": [
        {
            "std": "IPC-7525",
            "edition": "current",
            "clause": "PrintParameterControl",
            "summary_zh": "刮刀壓力、角度與速度需維持在可重現窗口，以確保沉積一致性。",
            "actions": ["檢查刮刀磨耗", "重新校正印刷參數窗口"],
        }
    ],
    "localized_stencil_wear": IPC_REFERENCES_BY_RULE_ID["localized_deviation_bias"],
    "instability": [
        {
            "std": "J-STD-001",
            "edition": "current",
            "clause": "ProcessControl",
            "summary_zh": "當製程偏離受控狀態時，需執行矯正措施並保留驗證紀錄。",
            "actions": ["啟動製程管制異常處置", "完成矯正後再驗證"],
        }
    ],
    "spatial_oos": IPC_REFERENCES_BY_RULE_ID["edge_spatial_cluster"],
}


def get_ipc_references_by_rule(rule_id: str) -> List[Dict[str, Any]]:
    """Return IPC references for a given root-cause rule_id."""
    return list(IPC_REFERENCES_BY_RULE_ID.get(rule_id, []))


def get_ipc_references_by_failure_mode(failure_mode_id: str) -> List[Dict[str, Any]]:
    """Return IPC references for a given failure_mode_id."""
    return list(IPC_REFERENCES_BY_FAILURE_MODE_ID.get(failure_mode_id, []))
