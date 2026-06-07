"""D (depth): numeric literals and tables align with docs/governance/SPC_RULES.md + engine cross-checks."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from app.analytics import capability_engine as cap_mod
from app.analytics.spc_engine import SPCEngine
from app.analytics.statistical_utils import StatisticalUtils
from app.analytics.summary_engine import CPK_CI_ALPHA
from app.analytics.xbar_r_engine import _XBAR_R_CONSTANTS

_SPC_DOC_Z975 = 1.959963984540054

# AIAG / ISO 7870-2 style Xbar-R factors (n = subgroup size). Keep in sync with
# `app.analytics.xbar_r_engine._XBAR_R_CONSTANTS` when the spec appendix or engine table changes.
_EXPECTED_XBAR_R: dict[int, tuple[float, float, float]] = {
    2: (1.880, 0.000, 3.267),
    3: (1.023, 0.000, 2.574),
    4: (0.729, 0.000, 2.282),
    5: (0.577, 0.000, 2.114),
    6: (0.483, 0.000, 2.004),
    7: (0.419, 0.076, 1.924),
    8: (0.373, 0.136, 1.864),
    9: (0.337, 0.184, 1.816),
    10: (0.308, 0.223, 1.777),
}


def _spc_rules_body() -> str:
    root = Path(__file__).resolve().parents[2]
    p = root / "docs" / "governance" / "SPC_RULES.md"
    return p.read_text(encoding="utf-8")


def test_spc_rules_documents_imr_d2_literal() -> None:
    body = _spc_rules_body()
    assert "d2 = 1.128" in body


def test_spc_rules_documents_cpk_ci_z_literal() -> None:
    body = _spc_rules_body()
    assert str(_SPC_DOC_Z975) in body


def test_imr_d2_matches_between_spc_and_capability_modules() -> None:
    assert SPCEngine.I_MR_D2 == cap_mod._D2_N2 == 1.128


def test_cpk_ci_normal_quantile_matches_spc_rules_z975() -> None:
    pytest.importorskip("scipy.stats")
    import scipy.stats as stats  # type: ignore[import-untyped]

    z = float(stats.norm.ppf(1.0 - CPK_CI_ALPHA / 2.0))
    assert abs(z - _SPC_DOC_Z975) < 1e-9
    assert CPK_CI_ALPHA == 0.05


def test_capability_spread_constants_match_cp_pp_formulas_in_spec() -> None:
    body = _spc_rules_body()
    assert cap_mod._CP_SIGMA_SPAN == 6
    assert cap_mod._ONE_SIDED_SIGMA == 3
    assert "Cp = (USL - LSL) / (6 \\* sigma)" in body or "Cp = (USL - LSL) / (6 * sigma)" in body


def test_xbar_r_constant_table_matches_engine_and_reference_tuple() -> None:
    assert _XBAR_R_CONSTANTS == _EXPECTED_XBAR_R


def test_minimum_spc_sample_matches_spec_language() -> None:
    body = _spc_rules_body()
    ok, msg = StatisticalUtils.is_valid_for_spc(pd.Series([1.0] * 9))
    assert ok is False
    assert "10" in msg
    assert "sample size < 10" in body or "Sample size" in body
