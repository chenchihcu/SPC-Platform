def validate_measurement_minimum(mapped_result) -> tuple[bool, str]:
    mapped = getattr(mapped_result, "mapped_columns", {})
    has_measure = any(key in mapped for key in ["Volume", "Area", "Height"])
    has_identity = any(key in mapped for key in ["BoardNo", "Time"])
    if "RefDes" not in mapped:
        return False, "缺少 RefDes"
    if not has_measure:
        return False, "缺少量測欄位"
    if not has_identity:
        return False, "缺少樣本識別欄位"
    return True, "OK"
