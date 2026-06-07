from typing import Any, Optional
import numpy as np

def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    """
    Safely convert a value to float. 
    Handles "N/A", "—", and other non-numeric strings by returning the default.
    Handles numpy infinity/nan by returning the default if specified as a number.
    """
    if value is None:
        return default
    
    if isinstance(value, (int, float)):
        f_val = float(value)
    else:
        # Handle common missing value strings
        text = str(value).strip()
        if not text or text in {"—", "N/A", "Unknown", "UNKNOWN", "VERIFY", "None", "nan", "NoneType"}:
            return default
        try:
            f_val = float(text)
        except (ValueError, TypeError):
            return default
            
    if not np.isfinite(f_val):
        return default
        
    return f_val

def safe_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    """Safely convert a value to int (coerces via float if necessary)."""
    f_val = safe_float(value)
    if f_val is None:
        return default
    try:
        return int(round(f_val))
    except (ValueError, TypeError, OverflowError):
        return default

def coerce_float(value: Any, default: float = 0.0) -> float:
    """Version of safe_float that always returns a float."""
    res = safe_float(value, default=default)
    return res if res is not None else default

def coerce_int(value: Any, default: int = 0) -> int:
    """Version of safe_int that always returns an int."""
    res = safe_int(value, default=default)
    return res if res is not None else default
