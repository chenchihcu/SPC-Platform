import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

# When point count exceeds this, aggregate to grid for faster heatmap rendering (Phase 12)
# Lowered from 50000 to 30000 to prevent memory pressure in resource-constrained environments.
SPATIAL_GRID_THRESHOLD = 30000
SPATIAL_GRID_BINS = 80


def _aggregate_to_grid(
    x_vals: np.ndarray,
    y_vals: np.ndarray,
    v_vals: np.ndarray,
    r_vals: list,
    n_bins: int = SPATIAL_GRID_BINS,
) -> tuple:
    """Bin (x,y,value) into n_bins x n_bins grid; return cell centers and mean value per cell."""
    x_min, x_max = float(np.nanmin(x_vals)), float(np.nanmax(x_vals))
    y_min, y_max = float(np.nanmin(y_vals)), float(np.nanmax(y_vals))
    if x_max <= x_min:
        x_max = x_min + 1.0
    if y_max <= y_min:
        y_max = y_min + 1.0
    x_edges = np.linspace(x_min, x_max, n_bins + 1)
    y_edges = np.linspace(y_min, y_max, n_bins + 1)
    x_idx = np.clip(np.searchsorted(x_edges[1:], x_vals, side="right"), 0, n_bins - 1)
    y_idx = np.clip(np.searchsorted(y_edges[1:], y_vals, side="right"), 0, n_bins - 1)
    # Accumulate with zeros; using NaN here would poison np.add.at sums.
    grid_val = np.zeros((n_bins, n_bins), dtype=float)
    grid_cnt = np.zeros((n_bins, n_bins))
    np.add.at(grid_cnt, (y_idx, x_idx), 1)
    np.add.at(grid_val, (y_idx, x_idx), v_vals)
    mask = grid_cnt > 0
    grid_val[mask] /= grid_cnt[mask]
    yi, xi = np.where(mask)
    x_centers = (x_edges[xi] + x_edges[xi + 1]) / 2
    y_centers = (y_edges[yi] + y_edges[yi + 1]) / 2
    labels = [f"grid_{i}" for i in range(len(x_centers))]
    return x_centers.tolist(), y_centers.tolist(), grid_val[mask].tolist(), labels


class SpatialEngine:
    """
    Computes spatial relationships projecting measurements onto PCB coordinates.
    Generates Heatmap grids and supports multiple modes: value, UCL/LCL/OOS density, volume deviation.
    For large point counts, optionally aggregates to grid for faster rendering (Phase 12).
    """

    MODE_VALUE = "value"
    MODE_UCL_DENSITY = "ucl_density"
    MODE_LCL_DENSITY = "lcl_density"
    MODE_OOS_DENSITY = "oos_density"
    MODE_VOLUME_DEVIATION = "volume_deviation"
    HEATMAP_MODES = (MODE_VALUE, MODE_UCL_DENSITY, MODE_LCL_DENSITY, MODE_OOS_DENSITY, MODE_VOLUME_DEVIATION)

    @staticmethod
    def compute_heatmap(
        joined_df: pd.DataFrame,
        target_col: str,
        mode: str = "value",
        ucl: Optional[float] = None,
        lcl: Optional[float] = None,
        usl: Optional[float] = None,
        lsl: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Extracts X, Y and value/density for scatter map. Mode: value (raw), ucl_density, lcl_density, oos_density, volume_deviation.
        """
        if joined_df is None or joined_df.empty or "X" not in joined_df.columns or "Y" not in joined_df.columns or target_col not in joined_df.columns:
            return {
                "chart_type": "Spatial",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": "缺乏有效的映射座標資料 (Missing Joined Coordinates). 請確認座標檔已匯入且關聯成功率大於零。"},
                "modes": {},
            }
        valid_df = joined_df[["X", "Y", "RefDes", target_col]].dropna()
        if len(valid_df) == 0:
            return {
                "chart_type": "Spatial",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": "無有效測量數值與座標組合 (No valid Value-Coordinate pairs)."},
                "modes": {},
            }
        # Normalize pandas arrays to NumPy ndarrays so downstream math/comparisons
        # have a stable type (avoids ExtensionArray vs ndarray ambiguity).
        x_vals = np.asarray(valid_df["X"], dtype=float)
        y_vals = np.asarray(valid_df["Y"], dtype=float)
        v_vals_raw = np.asarray(valid_df[target_col], dtype=float)
        mean_val = float(np.mean(v_vals_raw))
        r_vals = valid_df["RefDes"].tolist()
        n_pts = len(x_vals)
        use_grid = n_pts > SPATIAL_GRID_THRESHOLD

        def to_mode_data(x: list, y: list, v, labels: list) -> dict:
            return {"x": x, "y": y, "values": v.tolist() if hasattr(v, "tolist") else list(v), "labels": labels}

        if use_grid:
            # Use a separate variable for grid labels to avoid overwriting the original r_vals (RefDes list)
            x_list, y_list, v_list, grid_labels = _aggregate_to_grid(x_vals, y_vals, v_vals_raw, r_vals)
            data_by_mode = {}
            data_by_mode[SpatialEngine.MODE_VALUE] = to_mode_data(x_list, y_list, np.array(v_list), grid_labels)
            data_by_mode[SpatialEngine.MODE_VOLUME_DEVIATION] = to_mode_data(
                x_list, y_list, np.array(v_list) - mean_val, grid_labels
            )
            if ucl is not None:
                _, _, ucl_list, _ = _aggregate_to_grid(x_vals, y_vals, (v_vals_raw > ucl).astype(float), r_vals)
                data_by_mode[SpatialEngine.MODE_UCL_DENSITY] = to_mode_data(x_list, y_list, np.array(ucl_list), grid_labels)
            if lcl is not None:
                _, _, lcl_list, _ = _aggregate_to_grid(x_vals, y_vals, (v_vals_raw < lcl).astype(float), r_vals)
                data_by_mode[SpatialEngine.MODE_LCL_DENSITY] = to_mode_data(x_list, y_list, np.array(lcl_list), grid_labels)
            if usl is not None and lsl is not None:
                oos = (v_vals_raw < lsl) | (v_vals_raw > usl)
                _, _, oos_list, _ = _aggregate_to_grid(x_vals, y_vals, oos.astype(float), r_vals)
                data_by_mode[SpatialEngine.MODE_OOS_DENSITY] = to_mode_data(x_list, y_list, np.array(oos_list), grid_labels)
        else:
            x_list = x_vals.tolist()
            y_list = y_vals.tolist()
            v_list = v_vals_raw.tolist()
            data_by_mode = {}
            data_by_mode[SpatialEngine.MODE_VALUE] = to_mode_data(x_list, y_list, v_vals_raw, r_vals)
            data_by_mode[SpatialEngine.MODE_VOLUME_DEVIATION] = to_mode_data(
                x_list, y_list, v_vals_raw - mean_val, r_vals
            )
            if ucl is not None:
                data_by_mode[SpatialEngine.MODE_UCL_DENSITY] = to_mode_data(
                    x_list, y_list, (v_vals_raw > ucl).astype(float), r_vals
                )
            if lcl is not None:
                data_by_mode[SpatialEngine.MODE_LCL_DENSITY] = to_mode_data(
                    x_list, y_list, (v_vals_raw < lcl).astype(float), r_vals
                )
            if usl is not None and lsl is not None:
                data_by_mode[SpatialEngine.MODE_OOS_DENSITY] = to_mode_data(
                    x_list, y_list, ((v_vals_raw < lsl) | (v_vals_raw > usl)).astype(float), r_vals
                )
        
        current = data_by_mode.get(mode, data_by_mode[SpatialEngine.MODE_VALUE])
        vals = current["values"]
        displayed_n = len(current["x"])
        sampled_for_display = bool(use_grid and displayed_n < n_pts)
        sampling_method = "grid_aggregation" if use_grid else "full_data"
        downsample_step = None
        return {
            "chart_type": "Spatial",
            "data": current,
            "statistics": {
                "max": float(np.nanmax(vals)),
                "min": float(np.nanmin(vals)),
                "points": displayed_n,  # displayed points (legacy field)
                "n": n_pts,
                "displayed_n": displayed_n,
                "sampled_for_display": sampled_for_display,
                "sampling_method": sampling_method,
                "downsample_step": downsample_step,
                "aggregation_bins": SPATIAL_GRID_BINS if use_grid else None,
            },
            "metadata": {
                "is_valid": True,
                "error": "",
                "mode": mode,
                "sampled_for_display": sampled_for_display,
            },
            "modes": data_by_mode,
        }
