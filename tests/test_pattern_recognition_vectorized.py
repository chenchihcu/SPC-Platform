import numpy as np
import pandas as pd

from app.analytics.pattern_recognition_engine import PatternRecognitionEngine


def _slow_rule_hits(values: list[float]) -> dict[str, list[int]]:
    series = pd.Series(values)
    mean = float(np.mean(values))
    sigma = float(np.std(values, ddof=1))
    indices = list(series.index)

    rule1 = [indices[i] for i, value in enumerate(values) if abs(value - mean) > 3 * sigma]

    rule2: list[int] = []
    run_start = 0
    for i in range(1, len(values) + 1):
        if i == len(values) or (values[i] >= mean) != (values[run_start] >= mean):
            if i - run_start >= 9:
                rule2.extend(indices[run_start:i])
            run_start = i

    rule3: list[int] = []
    arr = np.asarray(values, dtype=float)
    for i in range(len(arr) - 5):
        window = arr[i : i + 6]
        if np.all(np.diff(window) > 0) or np.all(np.diff(window) < 0):
            rule3.extend(indices[i : i + 6])

    rule4: list[int] = []
    for i in range(len(arr) - 13):
        diffs = np.diff(arr[i : i + 14])
        if np.all(diffs[:-1] * diffs[1:] < 0):
            rule4.extend(indices[i : i + 14])

    return {
        "R1": sorted(set(rule1)),
        "R2": sorted(set(rule2)),
        "R3": sorted(set(rule3)),
        "R4": sorted(set(rule4)),
    }


def _vectorized_rule_hits(values: list[float]) -> dict[str, list[int]]:
    result = PatternRecognitionEngine.compute_nelson(pd.Series(values), "Volume")
    hits = {entry["rule"]: entry["indices"] for entry in result["data"]["rule_hits"]}
    return {rule: hits.get(rule, []) for rule in ("R1", "R2", "R3", "R4")}


def test_vectorized_nelson_rules_match_legacy_window_logic() -> None:
    values = [
        100, 101, 102, 103, 104, 105, 106, 107,
        94, 106, 95, 107, 96, 108, 97, 109, 98, 110, 99, 111,
        90, 89, 88, 87, 86, 85, 84, 83, 82,
        100, 100, 100, 100, 100, 100,
    ]

    assert _vectorized_rule_hits(values) == _slow_rule_hits(values)
