"""
Radar chart payload helper — slices existing engine outputs into radar format.
"""
from typing import Any, Dict, List


def build_radar_payload(
    statistics_map: Dict[str, Dict[str, float]],
    category_label: str = "features",
) -> Dict[str, Any]:
    """
    Build a radar chart payload from a statistics map.

    Args:
        statistics_map: {series_name: {category: value, ...}, ...}
            Example:
            {
                "Center": {"Volume": 85.0, "Area": 78.0, "Height": 92.0},
                "Left":   {"Volume": 72.0, "Area": 80.0, "Height": 88.0},
                "Right":  {"Volume": 78.0, "Area": 82.0, "Height": 90.0},
            }
        category_label: Label for what the categories represent (default: "features")

    Returns:
        Radar chart payload:
        {
            "chart_type": "radar",
            "payload_key": "radar",
            "data": {
                "categories": ["Volume", "Area", "Height"],
                "series": [
                    {"name": "Center", "values": [85.0, 78.0, 92.0]},
                    {"name": "Left", "values": [72.0, 80.0, 88.0]},
                    {"name": "Right", "values": [78.0, 82.0, 90.0]},
                ],
            },
            "metadata": {
                "is_valid": True,
                "n_series": 3,
                "n_categories": 3,
                "category_label": "features",
            },
        }
    """
    if not statistics_map:
        return {
            "chart_type": "radar",
            "payload_key": "radar",
            "data": {"categories": [], "series": []},
            "metadata": {
                "is_valid": False,
                "n_series": 0,
                "n_categories": 0,
                "category_label": category_label,
                "error": "No statistics data provided",
            },
        }

    # Collect all unique categories from all series
    all_categories: set[str] = set()
    for series_values in statistics_map.values():
        all_categories.update(series_values.keys())

    categories = sorted(all_categories)
    series: List[Dict[str, Any]] = []

    for series_name, category_values in statistics_map.items():
        values = [category_values.get(cat, 0.0) for cat in categories]
        series.append({"name": str(series_name), "values": values})

    return {
        "chart_type": "radar",
        "payload_key": "radar",
        "data": {
            "categories": categories,
            "series": series,
        },
        "metadata": {
            "is_valid": True,
            "n_series": len(series),
            "n_categories": len(categories),
            "category_label": category_label,
        },
    }


def extract_statistics_from_engine_outputs(
    engine_outputs: Dict[str, Dict[str, Any]],
    stat_key: str = "mean",
) -> Dict[str, Dict[str, float]]:
    """
    Extract a specific statistic from multiple engine outputs (one per position/Image location).

    Args:
        engine_outputs: {position_name: engine_payload, ...}
            Each engine_payload has statistics.mean_t2, data.indices, etc.
        stat_key: The statistic key to extract from each engine output's statistics dict.
            Common values: "mean", "std", "median", "p95", "range"

    Returns:
        statistics_map suitable for build_radar_payload:
        {position_name: {feature_name: value, ...}}
    """
    result: Dict[str, Dict[str, float]] = {}
    for position_name, payload in engine_outputs.items():
        stats = payload.get("statistics", {})
        metadata = payload.get("metadata", {})
        if not metadata.get("is_valid", False):
            continue
        features: Dict[str, float] = {}
        # Extract stat value per feature if available
        if stat_key in stats:
            features[stat_key] = float(stats[stat_key])
        result[str(position_name)] = features
    return result


def build_radar_from_measurement_stats(
    means_by_position: Dict[str, Dict[str, float]],
) -> Dict[str, Any]:
    """
    Convenience wrapper — build radar payload directly from per-position, per-feature means.

    Args:
        means_by_position: {position_name: {feature_name: mean_value, ...}, ...}

    Returns:
        Complete radar chart payload
    """
    return build_radar_payload(means_by_position, category_label="features")
