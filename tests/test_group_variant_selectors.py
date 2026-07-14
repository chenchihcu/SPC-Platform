from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.tabs.comparison_tab import ComparisonTab
from app.ui.tabs.pareto_tab import ParetoTab


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _payload() -> dict:
    valid = {
        "metadata": {"is_valid": True},
        "data": {"labels": ["A"], "arrays": [[1.0]]},
        "analysis_context": {"target_col": "Volume"},
    }
    return {
        **valid,
        "_group_variants": {
            "pad": {**valid, "_grouping_mode": "pad", "_group_col": "Pad"},
            "image": {**valid, "_grouping_mode": "image", "_group_col": "ImageID"},
        },
    }


@pytest.mark.parametrize("tab_class", [ComparisonTab, ParetoTab])
def test_group_selector_uses_stable_keys_and_switches_precomputed_payload(
    qapp: QApplication, tab_class, monkeypatch: pytest.MonkeyPatch
) -> None:
    tab = tab_class()
    drawn: list[dict] = []
    monkeypatch.setattr(tab.chart_view, "draw_chart", lambda payload: drawn.append(payload) or True)

    tab.update_data(_payload())
    qapp.processEvents()

    assert [tab.group_combo.itemData(i) for i in range(tab.group_combo.count())] == [
        "default", "pad", "image"
    ]
    assert not tab._group_row.isHidden()
    tab.group_combo.setCurrentIndex(tab.group_combo.findData("image"))
    qapp.processEvents()
    assert drawn[-1]["_group_col"] == "ImageID"
