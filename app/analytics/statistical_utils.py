import numpy as np
import pandas as pd
from typing import Tuple

class StatisticalUtils:
    """
    Core statistical utilities for the analytics engine.
    Implements fundamental rules and validations from docs/governance/SPC_RULES.md.
    """
    
    @staticmethod
    def is_valid_for_spc(data: pd.Series) -> Tuple[bool, str]:
        """
        Validates if a dataset is statistically fit for SPC control limits 
        and capability computation.
        Rule: min 10 samples (20+ recommended), sigma must not be 0.
        """
        if data is None or data.empty:
            return False, "No data available."
            
        # MANDATORY: Sanitize Infinite values to prevent analytic contagion (Pass 123).
        # np.inf could crash Matplotlib plotting or lead to invalid sigma results.
        valid_data = data.replace([np.inf, -np.inf], np.nan).dropna()
        n = len(valid_data)
        
        if n < 10:
            return False, f"Sample size too small (N={n}). Minimum required for SPC is 10."
            
        if np.std(valid_data, ddof=1) == 0:
            return False, "Standard deviation is 0 (all values identical). Process variation cannot be measured."
            
        return True, ""

    @staticmethod
    def calculate_moving_range(data: pd.Series) -> pd.Series:
        """
        Calculates the Moving Range (MR_i = |X_i - X_(i-1)|).
        """
        return data.diff().abs()


def get_dot_nested_value(data, path, default=None):
    """
    Retrieves a value from a nested dictionary using dot notation.
    Example: get_dot_nested_value(data, "a.b.c") -> data['a']['b']['c']
    """
    if not isinstance(data, dict) or not path:
        return default
    keys = path.split('.')
    val = data
    for key in keys:
        if isinstance(val, dict) and key in val:
            val = val[key]
        else:
            return default
    return val
