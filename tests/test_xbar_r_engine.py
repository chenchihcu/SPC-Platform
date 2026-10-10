import numpy as np
import pandas as pd

from app.analytics.xbar_r_engine import XbarREngine


def test_xbar_r_engine_computes_limits_with_board_groups() -> None:
    df = pd.DataFrame(
        {
            "BoardNo": ["B1", "B1", "B1", "B2", "B2", "B2", "B3", "B3", "B3"],
            "Volume": [100.0, 101.0, 99.8, 100.2, 100.1, 100.3, 99.7, 99.9, 100.0],
        }
    )

    result = XbarREngine.compute_xbar_r(df, "Volume")

    assert result["metadata"]["is_valid"] is True
    assert result["statistics"]["n_subgroups"] == 3
    assert result["statistics"]["n_effective"] >= 2
    assert "ucl_xbar" in result["statistics"]
    assert "ucl_r" in result["statistics"]


def test_xbar_r_engine_returns_invalid_when_column_missing() -> None:
    df = pd.DataFrame({"BoardNo": ["B1", "B2"]})
    result = XbarREngine.compute_xbar_r(df, "Volume")
    assert result["metadata"]["is_valid"] is False


def test_exact_d2_d3_reproduce_aiag_table() -> None:
    """Numerical d2/d3 must match published AIAG values (incl. n > 10)."""
    from app.analytics.xbar_r_engine import _integrate_d2_d3

    reference = {2: (1.128, 0.853), 5: (2.326, 0.864), 10: (3.078, 0.797),
                 15: (3.472, 0.756), 20: (3.735, 0.729), 25: (3.931, 0.708)}
    for n, (d2_ref, d3_ref) in reference.items():
        d2, d3 = _integrate_d2_d3(n)
        assert abs(d2 - d2_ref) < 1e-3, n
        assert abs(d3 - d3_ref) < 1e-3, n


def test_large_board_subgroups_detect_one_sigma_board_shift() -> None:
    """Regression: SPI boards hold hundreds of pads; n must not be clamped to 10.

    With n clamped to 10 the Xbar half-width was ~1.84 sigma (true: 3/sqrt(500)
    = 0.134 sigma) and a whole-board +1 sigma shift went undetected.
    """
    rng = np.random.default_rng(0)
    frames = []
    for b in range(25):
        shift = 1.0 if b == 20 else 0.0
        frames.append(pd.DataFrame({"BoardNo": f"B{b:02d}", "Volume": rng.normal(100 + shift, 1, 500)}))
    df = pd.concat(frames, ignore_index=True)

    result = XbarREngine.compute_xbar_r(df, "Volume")
    stats = result["statistics"]

    assert stats["n_effective"] == 500
    assert abs((stats["ucl_xbar"] - stats["xbarbar"]) - 3 / np.sqrt(500)) < 0.02
    assert 20 in result["data"]["ooc_xbar_indices"]


def test_equal_small_subgroups_match_a2_table_limits() -> None:
    df = pd.DataFrame(
        {
            "BoardNo": [f"B{i // 5}" for i in range(50)],
            "Volume": np.random.default_rng(2).normal(100, 1, 50),
        }
    )
    stats = XbarREngine.compute_xbar_r(df, "Volume")["statistics"]
    assert abs(stats["ucl_xbar"] - (stats["xbarbar"] + 0.577 * stats["rbar"])) < 1e-3 * stats["rbar"] + 1e-9
    assert abs(stats["ucl_r"] - 2.114 * stats["rbar"]) < 1e-3 * stats["rbar"] + 1e-9
