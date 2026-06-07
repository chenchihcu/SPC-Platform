import pytest
from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QSizePolicy, QWidget

from app.ui.theme import layout_policy
from app.ui.theme.layout_policy import normalize_text_input_policies


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_normalize_text_input_policies_applies_expected_size_policy():
    _app()
    root = QWidget()
    label = QLabel("Title", root)
    line_edit = QLineEdit(root)

    normalize_text_input_policies(root)

    assert label.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Preferred
    assert label.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Preferred
    assert line_edit.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.MinimumExpanding
    assert line_edit.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Preferred


def test_ensure_window_visible_clamps_offscreen_geometry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    window = QWidget()
    window.setMinimumSize(200, 100)
    window.resize(400, 300)
    window.move(-120, 40)
    monkeypatch.setattr(
        layout_policy,
        "available_geometry_for",
        lambda _widget: QRect(0, 0, 800, 600),
    )

    assert layout_policy.ensure_window_visible(window)
    assert window.frameGeometry().left() >= 16


def test_ensure_window_visible_rejects_oversized_geometry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    window = QWidget()
    window.setMinimumSize(200, 100)
    window.resize(900, 700)
    monkeypatch.setattr(
        layout_policy,
        "available_geometry_for",
        lambda _widget: QRect(0, 0, 800, 600),
    )

    assert not layout_policy.ensure_window_visible(window)


def test_fit_top_level_to_available_caps_and_centers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    window = QWidget()
    window.setMinimumSize(200, 100)
    monkeypatch.setattr(
        layout_policy,
        "available_geometry_for",
        lambda _widget: QRect(0, 0, 1280, 752),
    )

    assert layout_policy.fit_top_level_to_available(
        window,
        preferred_size=(1400, 900),
    )

    assert window.width() <= 1248
    assert window.height() <= 720
    assert window.frameGeometry().left() >= 16
    assert window.frameGeometry().top() >= 16


def test_fit_top_level_to_available_uses_screen_ratio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _app()
    window = QWidget()
    window.setMinimumSize(200, 100)
    monkeypatch.setattr(
        layout_policy,
        "available_geometry_for",
        lambda _widget: QRect(0, 0, 1000, 800),
    )

    assert layout_policy.fit_top_level_to_available(
        window,
        screen_ratio=0.5,
    )

    assert window.size().width() == 484
    assert window.size().height() == 384
