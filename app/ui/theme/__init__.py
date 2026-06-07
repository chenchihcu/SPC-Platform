"""
Central design tokens and theme utilities for the app UI.
"""
from PySide6.QtWidgets import QMessageBox
from PySide6.QtGui import QPalette, QColor
from app.ui.theme.tokens import (
    BG_PRIMARY,
    BG_SECONDARY,
    BG_BLOCK,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
    TEXT_DISABLED,
    SURFACE_ACTIVE,
    ACCENT_PRIMARY,
    ACCENT_SUCCESS,
    ACCENT_WARNING,
    ACCENT_ERROR,
    BORDER,
    SPACING_XS,
    SPACING_SM,
    SPACING_16,
    FONT_FAMILY,
    FONT_FAMILY_MONO,
    FONT_SIZE_BODY,
    FONT_SIZE_CAPTION,
    FONT_SIZE_SECTION,
    FONT_SIZE_SMALL,
    FONT_SIZE_TITLE,
)
from app.ui.theme.dark_stylesheet import get_app_stylesheet, get_dark_stylesheet
from app.ui.theme.layout_policy import install_text_input_policy_filter, stabilize_minimum_height


def _build_app_palette() -> QPalette:
    """Build a QApplication-level palette so Qt internals (selection highlight,
    placeholder text, alternate rows, disabled state) match the theme even where
    QSS selectors cannot reach (e.g. native rendering paths, accessibility APIs)."""
    p = QPalette()
    # Active / normal group
    p.setColor(QPalette.ColorRole.Window,          QColor(BG_PRIMARY))
    p.setColor(QPalette.ColorRole.WindowText,      QColor(TEXT_PRIMARY))
    p.setColor(QPalette.ColorRole.Base,            QColor(BG_BLOCK))
    p.setColor(QPalette.ColorRole.AlternateBase,   QColor(BG_SECONDARY))
    p.setColor(QPalette.ColorRole.Text,            QColor(TEXT_PRIMARY))
    p.setColor(QPalette.ColorRole.Button,          QColor(BG_SECONDARY))
    p.setColor(QPalette.ColorRole.ButtonText,      QColor(TEXT_PRIMARY))
    p.setColor(QPalette.ColorRole.Highlight,       QColor(SURFACE_ACTIVE))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(TEXT_PRIMARY))
    p.setColor(QPalette.ColorRole.ToolTipBase,     QColor(BG_BLOCK))
    p.setColor(QPalette.ColorRole.ToolTipText,     QColor(TEXT_PRIMARY))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(TEXT_MUTED))
    # Disabled group — ensures Qt's own disabled rendering uses theme colors
    for role, color in [
        (QPalette.ColorRole.WindowText, TEXT_DISABLED),
        (QPalette.ColorRole.Text,       TEXT_DISABLED),
        (QPalette.ColorRole.ButtonText, TEXT_DISABLED),
        (QPalette.ColorRole.Button,     BG_SECONDARY),
        (QPalette.ColorRole.Base,       BG_SECONDARY),
    ]:
        p.setColor(QPalette.ColorGroup.Disabled, role, QColor(color))
    return p


def apply_app_theme(app) -> None:
    """Apply the global stylesheet and palette to the QApplication."""
    install_text_input_policy_filter(app)
    app.setPalette(_build_app_palette())
    app.setStyleSheet(get_app_stylesheet())


def apply_dark_theme(app) -> None:
    """Backward-compatible alias for the historical theme function name."""
    apply_app_theme(app)


def apply_dark_palette_to_message_box(msgbox: QMessageBox) -> None:
    """Apply theme palette and stylesheet to a QMessageBox (call before exec)."""
    msgbox.setPalette(_build_app_palette())
    msgbox.setStyleSheet(get_app_stylesheet())


def _show_dark_message(parent, title: str, text: str, icon: QMessageBox.Icon) -> None:
    mb = QMessageBox(icon, title, text, QMessageBox.StandardButton.Ok, parent)
    apply_dark_palette_to_message_box(mb)
    mb.exec()


def show_dark_warning(parent, title: str, text: str) -> None:
    """Show a dark-themed warning message box."""
    _show_dark_message(parent, title, text, QMessageBox.Icon.Warning)


def show_dark_information(parent, title: str, text: str) -> None:
    """Show a dark-themed information message box."""
    _show_dark_message(parent, title, text, QMessageBox.Icon.Information)


# Re-export for convenience
__all__ = [
    "apply_dark_theme",
    "apply_app_theme",
    "get_dark_stylesheet",
    "get_app_stylesheet",
    "BG_PRIMARY",
    "BG_SECONDARY",
    "BG_BLOCK",
    "TEXT_PRIMARY",
    "TEXT_SECONDARY",
    "TEXT_MUTED",
    "ACCENT_PRIMARY",
    "ACCENT_SUCCESS",
    "ACCENT_WARNING",
    "ACCENT_ERROR",
    "BORDER",
    "SPACING_XS",
    "SPACING_SM",
    "SPACING_16",
    "FONT_FAMILY",
    "FONT_FAMILY_MONO",
    "FONT_SIZE_BODY",
    "FONT_SIZE_CAPTION",
    "FONT_SIZE_SECTION",
    "FONT_SIZE_SMALL",
    "FONT_SIZE_TITLE",
    "install_text_input_policy_filter",
    "stabilize_minimum_height",
]
