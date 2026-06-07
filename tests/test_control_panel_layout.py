import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QComboBox, QLineEdit

from app.ui.widgets.control_panel import ControlPanel


def _ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_refdes_filter_row_uses_combo_only() -> None:
    _ensure_app()
    panel = ControlPanel()

    item = panel._condition_grid.itemAtPosition(2, 1)
    assert item is not None
    assert item.widget() is panel.refdes_combo
    assert isinstance(item.widget(), QComboBox)
    assert panel.refdes_combo.lineEdit() is None

    visible_line_edits = [line_edit for line_edit in panel.findChildren(QLineEdit) if line_edit.isVisible()]
    assert visible_line_edits == []


def test_feature_toggle_segments_are_equal_width_without_overlap() -> None:
    app = _ensure_app()

    for width in (220, 300, 418):
        panel = ControlPanel()
        panel.resize(width, 720)
        panel.set_feature_section_visible(True)
        panel.sync_feature_states(["Volume"])
        panel.show()
        app.processEvents()

        buttons = [panel._btn_height, panel._btn_area, panel._btn_volume]
        rects = [button.geometry() for button in buttons]
        widths = [rect.width() for rect in rects]

        assert max(widths) - min(widths) <= 1
        assert rects[1].x() == rects[0].x() + rects[0].width()
        assert rects[2].x() == rects[1].x() + rects[1].width()
        segment_layout = buttons[0].parentWidget().layout()
        assert [segment_layout.stretch(i) for i in range(3)] == [1, 1, 1]


def test_condition_section_collapse_has_visible_affordance() -> None:
    app = _ensure_app()

    panel = ControlPanel()
    panel.range_combo.setCurrentIndex(1)
    selected_range = panel.range_combo.currentText()

    panel.set_condition_section_collapsed(True)
    app.processEvents()

    assert panel._condition_title.text() == "分析條件（已收合）"
    assert not panel._condition_container.isVisible()
    assert panel._condition_summary.isVisibleTo(panel)
    assert panel.range_combo.currentText() == selected_range

    panel.set_condition_section_collapsed(False)
    app.processEvents()

    assert panel._condition_title.text() == "分析條件"
    assert panel._condition_container.isVisibleTo(panel)
    assert not panel._condition_summary.isVisible()
