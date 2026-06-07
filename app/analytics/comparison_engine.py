import pandas as pd
import numpy as np
from typing import Dict, Any, List

class ComparisonEngine:
    """
    Computes Subgroup Variance and Medians, generating Boxplot statistics
    to expose variation between batches, components, or part types.
    Supports same-footprint comparison (PartType → RefDes per location).
    """
    
    @staticmethod
    def compute_boxplot(df: pd.DataFrame, target_col: str, group_col: str = "RefDes") -> Dict[str, Any]:
        """
        Splits data by `group_col` and packages it into arrays for Boxplot charting.
        Adds variance_by_label for variance comparison when needed.
        """
        if df is None or df.empty or target_col not in df.columns or group_col not in df.columns:
            return {
                "chart_type": "Boxplot",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": f"缺少 {group_col} 分組特徵或測量值 (Missing grouping or target column)."}
            }
            
        valid_df = df[[group_col, target_col]].dropna()
        if len(valid_df) == 0:
             return {
                 "chart_type": "Boxplot",
                 "data": {},
                 "statistics": {},
                 "metadata": {"is_valid": False, "error": "無有效測量數值與分組 (No valid grouped data)."}
             }
             
        group_obj = valid_df.groupby(group_col)
        
        labels = []
        data_arrays = []
        variance_by_label: Dict[str, float] = {}
        
        for name, chunk in group_obj:
            lbl = str(name)
            labels.append(lbl)
            arr = chunk[target_col].tolist()
            data_arrays.append(arr)
            if len(arr) > 1:
                variance_by_label[lbl] = float(np.var(arr))
            else:
                variance_by_label[lbl] = 0.0
            
        return {
            "chart_type": "Boxplot",
            "data": {
                "labels": labels,
                "arrays": data_arrays
            },
            "statistics": {
                "num_groups": len(labels),
                "variance_by_label": variance_by_label,
            },
            "metadata": {
                "is_valid": True,
                "error": ""
            }
        }

    @staticmethod
    def compute_footprint_comparison(
        df: pd.DataFrame,
        target_col: str,
        part_type_col: str = "PartType",
        refdes_col: str = "RefDes",
    ) -> Dict[str, Any]:
        """
        Same-footprint comparison: for each PartType, compare RefDes (same design, different PCB locations).
        Returns first PartType's boxplot data plus list of footprints for selector.
        """
        if df is None or df.empty or target_col not in df.columns:
            return {
                "chart_type": "Boxplot",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": "Missing data or columns", "mode": "footprint"},
            }
        if part_type_col not in df.columns or refdes_col not in df.columns:
            return ComparisonEngine.compute_boxplot(df, target_col, group_col=refdes_col)
        valid = df[[part_type_col, refdes_col, target_col]].dropna()
        if valid.empty:
            return {
                "chart_type": "Boxplot",
                "data": {"labels": [], "arrays": []},
                "statistics": {},
                "metadata": {"is_valid": True, "mode": "footprint"},
                "footprints": [],
            }
        footprints: List[Dict[str, Any]] = []
        part_types = valid[part_type_col].astype(str).unique().tolist()
        for pt in part_types:
            sub = valid[valid[part_type_col].astype(str) == pt]
            box = ComparisonEngine.compute_boxplot(sub, target_col, group_col=refdes_col)
            if box.get("metadata", {}).get("is_valid") and box.get("data", {}).get("labels"):
                footprints.append({
                    "part_type": pt,
                    "labels": box["data"]["labels"],
                    "arrays": box["data"]["arrays"],
                    "variance_by_label": box.get("statistics", {}).get("variance_by_label", {}),
                })
        if not footprints:
            return {
                "chart_type": "Boxplot",
                "data": {"labels": [], "arrays": []},
                "statistics": {},
                "metadata": {"is_valid": True, "mode": "footprint"},
                "footprints": [],
            }
        first = footprints[0]
        return {
            "chart_type": "Boxplot",
            "data": {
                "labels": first["labels"],
                "arrays": first["arrays"],
                "mode": "footprint",
            },
            "statistics": {
                "num_groups": len(first["labels"]),
                "variance_by_label": first.get("variance_by_label", {}),
                "footprint_count": len(footprints),
            },
            "metadata": {"is_valid": True, "error": "", "mode": "footprint"},
            "footprints": footprints,
        }
