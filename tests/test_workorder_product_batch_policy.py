"""Policy: switching product name clears workorder identifiers to avoid cross-product carryover."""


def _apply_product_name_change(master: dict[str, str], name: str) -> None:
    """Mirror MainWindow._on_product_name_selected store updates (no Qt)."""
    prev = (master.get("product_name") or "").strip()
    new = (name or "").strip()
    master["product_name"] = name or ""
    if prev and new and prev != new:
        master["batch_no"] = ""
        master["work_order_no"] = ""
        master["supplier_work_order_no"] = ""
        master["outsource_work_order_no"] = ""


def test_first_product_selection_does_not_clear_existing_batch_no() -> None:
    master: dict[str, str] = {"batch_no": "LOT-KEEP"}
    _apply_product_name_change(master, "ProdA")
    assert master["product_name"] == "ProdA"
    assert master["batch_no"] == "LOT-KEEP"


def test_switching_product_clears_batch_no() -> None:
    master = {
        "product_name": "ProdA",
        "batch_no": "LOT-1",
        "work_order_no": "WO-1",
        "supplier_work_order_no": "SUP-1",
        "outsource_work_order_no": "OUT-1",
    }
    _apply_product_name_change(master, "ProdB")
    assert master["product_name"] == "ProdB"
    assert master["batch_no"] == ""
    assert master["work_order_no"] == ""
    assert master["supplier_work_order_no"] == ""
    assert master["outsource_work_order_no"] == ""


def test_reselect_same_product_keeps_batch_no() -> None:
    master = {"product_name": "ProdA", "batch_no": "LOT-1"}
    _apply_product_name_change(master, "ProdA")
    assert master["batch_no"] == "LOT-1"
