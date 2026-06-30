def validate_coordinate_minimum(mapped_result) -> tuple[bool, str]:
    mapped = getattr(mapped_result, "mapped_columns", {})
    required = ["RefDes", "X", "Y"]
    missing = [r for r in required if r not in mapped]
    if missing:
        return False, f"缺少欄位: {', '.join(missing)}"
    return True, "OK"
