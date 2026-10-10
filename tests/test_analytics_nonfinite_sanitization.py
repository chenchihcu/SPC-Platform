from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from app.analytics.anomaly_3f_engine import Anomaly3FEngine
from app.analytics.comparison_engine import ComparisonEngine
from app.analytics.consistency_3f_engine import Consistency3FEngine
from app.analytics.parallel_coord_engine import ParallelCoordEngine
from app.analytics.pareto_engine import ParetoEngine
from app.analytics.pass_fail_engine import PassFailEngine
from app.analytics.radar_payload_helper import build_radar_from_dataframe_groups
from app.analytics.repeated_offender_engine import RepeatedOffenderEngine
from app.analytics.spatial_engine import SpatialEngine
from app.analytics.subgroup_engine import SubgroupEngine


FEATURES = ["Volume", "Area", "Height"]
SPECS = {
    feature: {"usl": 130.0, "lsl": 70.0}
    for feature in FEATURES
}


def _assert_all_finite(value: Any) -> None:
    if isinstance(value, dict):
        for child in value.values():
            _assert_all_finite(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _assert_all_finite(child)
    elif isinstance(value, (float, np.floating)):
        assert math.isfinite(float(value))


def _multifeature_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "RefDes": ["R1", "R1", "R2", "R2"],
            "PartType": ["A", "A", "B", "B"],
            "X": [0.0, 1.0, 2.0, 3.0],
            "Y": [0.0, 1.0, 2.0, 3.0],
            "Volume": [100.0, 101.0, np.inf, 99.0],
            "Area": [100.0, 102.0, 100.0, 98.0],
            "Height": [100.0, 103.0, 100.0, 97.0],
        }
    )


def test_multifeature_engines_exclude_nonfinite_rows() -> None:
    df = _multifeature_df()

    anomaly = Anomaly3FEngine.compute_anomaly_3f(df, FEATURES)
    consistency = Consistency3FEngine.compute_consistency_3f(df, FEATURES)
    parallel = ParallelCoordEngine.compute_parallel_coord(df, FEATURES)
    pass_fail = PassFailEngine.compute_pass_fail(df, FEATURES, SPECS)
    radar = build_radar_from_dataframe_groups(df, FEATURES)

    assert anomaly["data"]["indices"] == [0, 1, 3]
    assert consistency["data"]["indices"] == [0, 1, 3]
    assert parallel["statistics"]["n"] == 3
    assert pass_fail["statistics"]["n_total"] == 3
    for payload in (anomaly, consistency, parallel, pass_fail, radar):
        assert payload["metadata"]["is_valid"] is True
        _assert_all_finite(payload)


def test_grouped_engines_do_not_emit_or_count_infinite_measurements() -> None:
    df = _multifeature_df()

    boxplot = ComparisonEngine.compute_boxplot(df, "Volume", "PartType")
    subgroup = SubgroupEngine.compute_subgroup(
        df, "Volume", group_col="PartType", usl=130.0, lsl=70.0
    )
    repeated = RepeatedOffenderEngine.compute_repeated_offender(
        df, "Volume", usl=130.0, lsl=70.0
    )
    component_pareto = ParetoEngine.compute_component_pareto(
        df, "Volume", group_col="PartType", usl=130.0, lsl=70.0
    )

    assert boxplot["data"]["arrays"] == [[100.0, 101.0], [99.0]]
    assert subgroup["data"]["counts"] == [2, 1]
    assert repeated["data"]["labels"] == []
    assert component_pareto["statistics"]["total_abnormal"] == 0
    for payload in (boxplot, subgroup, repeated, component_pareto):
        assert payload["metadata"]["is_valid"] is True
        _assert_all_finite(payload)


def test_footprint_comparison_is_invalid_when_all_measurements_are_nonfinite() -> None:
    df = pd.DataFrame(
        {
            "PartType": ["A", "B"],
            "RefDes": ["R1", "R2"],
            "Volume": [np.inf, -np.inf],
        }
    )

    result = ComparisonEngine.compute_footprint_comparison(df, "Volume")

    assert result["metadata"]["is_valid"] is False
    assert result["metadata"]["error"]
    assert result["data"] == {}
    assert result["statistics"] == {}


def test_spatial_engine_excludes_nonfinite_coordinates_and_measurements() -> None:
    df = _multifeature_df()
    df.loc[1, "X"] = -np.inf

    result = SpatialEngine.compute_heatmap(df, "Volume", usl=130.0, lsl=70.0)

    assert result["metadata"]["is_valid"] is True
    assert result["statistics"]["n"] == 2
    _assert_all_finite(result)


def test_pareto_treats_nonfinite_values_as_excluded_not_defects() -> None:
    df = pd.DataFrame({"Volume": [100.0, np.inf, -np.inf, np.nan, 150.0]})

    result = ParetoEngine.compute_pareto(
        df, "Volume", usl=130.0, lsl=70.0
    )

    assert result["metadata"]["is_valid"] is True
    assert result["data"]["categories"] == ["Excess"]
    assert result["statistics"]["total_defects"] == 1
    assert result["statistics"]["excluded_invalid_n"] == 3


def test_pareto_is_invalid_when_all_measurements_are_nonfinite() -> None:
    df = pd.DataFrame({"Volume": [np.inf, -np.inf, np.nan]})

    result = ParetoEngine.compute_pareto(
        df, "Volume", usl=130.0, lsl=70.0
    )

    assert result["metadata"]["is_valid"] is False
    assert result["metadata"]["error"]
    assert result["data"] == {}
    assert result["statistics"] == {}


def test_radar_is_canonical_invalid_when_all_measurements_are_nonfinite() -> None:
    df = pd.DataFrame(
        {
            "RefDes": ["R1", "R2"],
            "Volume": [np.inf, -np.inf],
            "Area": [1.0, 2.0],
            "Height": [1.0, 2.0],
        }
    )

    result = build_radar_from_dataframe_groups(df, FEATURES)

    assert result["metadata"]["is_valid"] is False
    assert result["metadata"]["error"]
    assert result["data"] == {}
    assert result["statistics"] == {}
