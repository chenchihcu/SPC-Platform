import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional

class ParetoEngine:
    """
    Classifies SPI defects and produces Pareto category aggregations.
    Relies on SPI_DEFECT_CLASSIFICATION.md standards.
    """
    
    @staticmethod
    def classify_defects(
        meas_df: pd.DataFrame,
        target_col: str,
        usl: Optional[float] = None,
        lsl: Optional[float] = None,
    ) -> pd.DataFrame:
        """Classify defects strictly relative to provided spec limits."""
        if meas_df.empty or target_col not in meas_df.columns:
            return meas_df

        df_copy = meas_df.copy()
        values = pd.to_numeric(df_copy[target_col], errors="coerce")
        defect = pd.Series("Normal", index=df_copy.index, dtype="object")
        defect[values.isna()] = "Unknown"
        if lsl is not None:
            defect[values.notna() & (values < lsl)] = "Insufficient"
        if usl is not None:
            defect[values.notna() & (values > usl)] = "Excess"
        df_copy["DefectType"] = defect
        return df_copy

    @staticmethod
    def compute_pareto(
        meas_df: pd.DataFrame,
        target_col: str = "Volume",
        usl: Optional[float] = None,
        lsl: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Compute defect frequencies and cumulative percentages from spec limits."""
        if usl is None and lsl is None:
            return {
                "chart_type": "Pareto",
                "data": {},
                "statistics": {},
                "metadata": {
                    "is_valid": False,
                    "error": "缺少 USL/LSL，無法進行標準 Pareto 缺陷分類。",
                    "mode": "non_computable",
                },
            }
        classified = ParetoEngine.classify_defects(meas_df, target_col, usl=usl, lsl=lsl)
        
        if classified.empty or "DefectType" not in classified.columns:
             return {
                "chart_type": "Pareto",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": "Cannot compute pareto over empty/unmapped data", "mode": "spec"}
             }

        # Filter out normal
        defects = classified[classified["DefectType"] != "Normal"]
        if defects.empty:
            return {
                "chart_type": "Pareto",
                "data": {"categories": ["None"], "counts": [0], "cumulative_pct": [0.0]},
                "statistics": {"total_defects": 0},
                "metadata": {"is_valid": True, "error": "No defects found. Process is clean.", "mode": "spec"}
            }

        counts = defects["DefectType"].value_counts()
        categories = counts.index.tolist()
        freq = counts.values.tolist()
        
        total = sum(freq)
        # O(n) running cumulative percentage (avoids per-element O(n^2) prefix sum).
        # Operation order is preserved (int prefix sum / total * 100.0) so float values
        # are byte-identical to the previous comprehension, keeping the determinism contract.
        running = 0
        cum_pct = []
        for f in freq:
            running += f
            cum_pct.append(running / total * 100.0)
        
        return {
            "chart_type": "Pareto",
            "data": {
                "categories": categories,
                "counts": freq,
                "cumulative_pct": cum_pct
            },
            "statistics": {
                "total_defects": int(total)
            },
            "metadata": {
                "is_valid": True,
                "error": "",
                "mode": "spec",
            }
        }

    @staticmethod
    def compute_component_pareto(
        meas_df: pd.DataFrame,
        target_col: str,
        group_col: str = "PartType",
        ucl: Optional[float] = None,
        lcl: Optional[float] = None,
        usl: Optional[float] = None,
        lsl: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Component-based Pareto: rank by abnormal_rate = (OOS + UCL + LCL violations) / total.
        Returns data for chart and component list for click-to-filter.
        """
        if meas_df.empty or target_col not in meas_df.columns or group_col not in meas_df.columns:
            return {
                "chart_type": "Pareto",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": "Missing data or required columns", "mode": "component"},
            }
        if usl is None and lsl is None and ucl is None and lcl is None:
            return {
                "chart_type": "Pareto",
                "data": {},
                "statistics": {},
                "metadata": {
                    "is_valid": False,
                    "error": "缺少規格與管制界線，無法進行元件 Pareto 異常分類。",
                    "mode": "component_non_computable",
                },
            }
        df = meas_df[[group_col, target_col]].dropna()
        if df.empty:
            return {
                "chart_type": "Pareto",
                "data": {"categories": [], "counts": [], "cumulative_pct": [], "component_ids": []},
                "statistics": {},
                "metadata": {"is_valid": True, "mode": "component"},
            }
        vals = df[target_col].astype(float).to_numpy()
        oos = np.zeros(len(df), dtype=int)
        ucl_v = np.zeros(len(df), dtype=int)
        lcl_v = np.zeros(len(df), dtype=int)
        if usl is not None and lsl is not None:
            oos = ((vals < lsl) | (vals > usl)).astype(int)
        if ucl is not None:
            ucl_v = (vals > ucl).astype(int)
        if lcl is not None:
            lcl_v = (vals < lcl).astype(int)
        abnormal = oos + ucl_v + lcl_v
        df = df.copy()
        df["_abnormal"] = abnormal
        agg = df.groupby(group_col, dropna=False).agg(
            total=(target_col, "count"),
            abnormal=("_abnormal", "sum"),
        ).reset_index()
        # abnormal_rate = abnormal_count / total_count
        # Keep it explicit because callers (UI/report) and unit tests rely on the field.
        agg["abnormal_rate"] = agg["abnormal"].astype(float) / agg["total"].replace(0, np.nan)
        # Rank by count (descending) first to satisfy Pareto's frequency-first rule
        agg = agg.sort_values(["abnormal", "abnormal_rate"], ascending=[False, False], na_position="last")
        agg = agg.dropna(subset=["abnormal_rate"])
        components: List[Dict[str, Any]] = []
        categories = []
        counts = []
        for row in agg.itertuples(index=False):
            comp_id = str(getattr(row, group_col))
            abnormal_count = int(getattr(row, "abnormal"))
            components.append({
                "component_id": comp_id,
                "abnormal_rate": float(getattr(row, "abnormal_rate")),
                "total": int(getattr(row, "total")),
                "abnormal_count": abnormal_count,
            })
            categories.append(comp_id)
            counts.append(abnormal_count)
        total_ab = sum(counts)
        cumulative_pct = (100.0 * np.cumsum(counts) / total_ab).tolist() if total_ab else [0.0] * len(counts)
        return {
            "chart_type": "Pareto",
            "data": {
                "categories": categories,
                "counts": counts,
                "cumulative_pct": cumulative_pct,
                "component_ids": categories,
                "mode": "component",
            },
            "statistics": {"total_components": len(categories), "total_abnormal": total_ab},
            "metadata": {"is_valid": True, "error": "", "mode": "component"},
            "components": components,
        }
