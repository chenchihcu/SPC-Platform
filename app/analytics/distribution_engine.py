import numpy as np
import pandas as pd
from typing import Dict, Any

class DistributionEngine:
    """
    Engine for calculating Frequency Histograms and Normal Distribution curves.
    """
    
    @staticmethod
    def compute_histogram(data: pd.Series, bins: int = 30) -> Dict[str, Any]:
        """
        Computes bins, frequencies and an overlaid ideal Normal Curve scaling.
        Note: Independent of Capability Engine. Doesn't require specifications.
        """
        valid_data = data.replace([np.inf, -np.inf], np.nan).dropna()
        if len(valid_data) < 2:
            return {
                "chart_type": "Distribution",
                "data": {},
                "statistics": {},
                "metadata": {"is_valid": False, "error": "Insufficient data to compute distribution geometry (N<2)."}
            }
            
        # Compute histogram frequencies and bins
        counts, bin_edges = np.histogram(valid_data, bins=bins)
        
        mean_val = valid_data.mean()
        std_val = np.std(valid_data, ddof=1)
        
        # Generate generic normal curve points 
        x_norm = np.linspace(valid_data.min(), valid_data.max(), 100)
        y_norm = np.zeros_like(x_norm)
        
        if std_val > 0:
            # Probability Density Function of Normal Distribution
            pdf = (1 / (std_val * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x_norm - mean_val) / std_val) ** 2)
            
            # Scale PDF to Match Histogram count envelope
            bin_width = bin_edges[1] - bin_edges[0]
            y_norm = pdf * len(valid_data) * bin_width
        
        return {
            "chart_type": "Distribution",
            "data": {
                "bin_edges": bin_edges.tolist(),
                "counts": counts.tolist(),
                "normal_curve_x": x_norm.tolist(),
                "normal_curve_y": y_norm.tolist()
            },
            "statistics": {
                "mean": float(mean_val),
                "std": float(std_val),
                "min": float(valid_data.min()),
                "max": float(valid_data.max())
            },
            "metadata": {
                "is_valid": True,
                "error": ""
            }
        }
