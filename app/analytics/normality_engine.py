import numpy as np
import pandas as pd
from typing import Dict, Any
import scipy.stats as stats  # type: ignore[import-untyped]

class NormalityEngine:
    """
    Engine to assess Normal Distribution characteristics of a given data series.
    Calculates Probability Plot coordinates and performs formal Anderson-Darling/Shapiro tests.
    """
    
    @staticmethod
    def compute_normality(data: pd.Series) -> Dict[str, Any]:
        """
        Calculates theoretical vs actual quantiles (Q-Q plot) and formal normality tests.
        """
        valid_data = data.dropna()
        n = len(valid_data)
        
        if n < 3:
            return {
                "chart_type": "Normality",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": "需要至少3筆以上的資料進行常態檢定。(N < 3)"}
            }
            
        try:
            # Use full-data normality testing; switch method by dataset size.
            tested_n = n
            sampled_for_test = False
            sampling_method = "full_data"
            sampling_seed = None
            normality_test_skipped = False
            shapiro_skip_reason = ""
            values = valid_data.to_numpy(dtype=float, copy=False)

            # SciPy probplot/shapiro emit zero-range warnings and NaN fit
            # statistics. Handle deterministic data before calling them.
            if np.isclose(np.ptp(values), 0.0):
                plotting_positions = (np.arange(1, n + 1) - 0.5) / n
                theoretical_q = stats.norm.ppf(plotting_positions)
                actual_q = np.sort(values)
                line_x = np.array([theoretical_q.min(), theoretical_q.max()])
                line_y = np.array([float(actual_q[0]), float(actual_q[0])])
                p_value = 1.0
                test_name = "Shapiro-Wilk (skipped: zero variance)"
                normality_test_skipped = True
                shapiro_skip_reason = "zero_variance"
                r_squared_val = 1.0
            else:
                # Generate Probability Plot (Q-Q coordinates)
                # res[0][0] = theoretical quantiles, res[0][1] = ordered values
                res = stats.probplot(values, dist="norm")
                theoretical_q = res[0][0]
                actual_q = res[0][1]
                slope, intercept, r = res[1]

                # Theoretical fit line endpoints
                line_x = np.array([theoretical_q.min(), theoretical_q.max()])
                line_y = slope * line_x + intercept

                if n <= 5000:
                    _stat, p_value = stats.shapiro(values)
                    test_name = "Shapiro-Wilk"
                else:
                    # Avoid partial-sample testing on large datasets:
                    # use full-data D'Agostino K^2 test for N > 5000.
                    _stat, p_value = stats.normaltest(values)
                    test_name = "D'Agostino K² (full data / N>5000)"

                r_squared_val = float(r**2)

            is_normal = False if normality_test_skipped else bool(p_value >= 0.05)

            if not (np.isfinite(r_squared_val) and np.isfinite(p_value)):
                return {
                    "chart_type": "Normality",
                    "data": {},
                    "statistics": {},
                    "metadata": {"is_valid": False, "error": "輸入資料變異不足，統計量為 NaN。"}
                }

            return {
                "chart_type": "Normality",
                "data": {
                    "theoretical_q": theoretical_q.tolist(),
                    "actual_q": actual_q.tolist(),
                    "line_x": line_x.tolist(),
                    "line_y": line_y.tolist()
                },
                "statistics": {
                    "p_value": float(p_value),
                    "r_squared": r_squared_val,
                    "is_normal": is_normal,
                    "test_name": test_name,
                    "total_n": n,
                    "tested_n": tested_n,
                    "sampled_for_test": sampled_for_test,
                    "sampling_method": sampling_method,
                    "sampling_seed": sampling_seed,
                    "normality_test_skipped": normality_test_skipped,
                    "shapiro_skip_reason": shapiro_skip_reason,
                },
                "metadata": {
                    "is_valid": True,
                    "error": "",
                    "sampled_for_test": sampled_for_test,
                    "normality_test_skipped": normality_test_skipped,
                }
            }
        except (TypeError, ValueError, FloatingPointError, RuntimeError, OSError) as e:
            return {
                "chart_type": "Normality",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": f"常態測算引擎崩潰: {str(e)}"}
            }
