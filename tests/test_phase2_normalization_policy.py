import numpy as np

from app.charts.cusum_3f_chart import _zscore_pair
from app.charts.ewma_3f_chart import _zscore_with_limits


def test_ewma_zscore_normalization_transforms_values_and_limits():
    values = [10.0, 12.0, 14.0, 16.0]
    cl, ucl, lcl = 13.0, 18.0, 8.0
    vals, clp, uclp, lclp = _zscore_with_limits(values, cl, ucl, lcl)

    assert len(vals) == len(values)
    assert abs(float(np.mean(vals))) < 1e-9
    assert abs(float(np.std(vals, ddof=1)) - 1.0) < 1e-9
    assert uclp > clp > lclp


def test_cusum_zscore_pair_normalization_preserves_ordering():
    cp = np.array([2.0, 4.0, 8.0], dtype=float)
    cm_neg = np.array([-1.0, -2.0, -3.0], dtype=float)
    cpz, cmz, _mean, _std, zero = _zscore_pair(cp, cm_neg)

    assert cpz.shape == cp.shape
    assert cmz.shape == cm_neg.shape
    assert cpz[2] > cpz[1] > cpz[0]
    assert cmz[0] > cmz[1] > cmz[2]
    assert isinstance(zero, float)
