from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QRect
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QSizePolicy, QWidget

from app.ui.theme.tokens import WINDOW_GEOMETRY_VISIBLE_MARGIN


def _apply_label_policy(label: QLabel) -> None:
    policy = label.sizePolicy()
    if (
        policy.horizontalPolicy() != QSizePolicy.Policy.Preferred
        or policy.verticalPolicy() != QSizePolicy.Policy.Preferred
    ):
        policy.setHorizontalPolicy(QSizePolicy.Policy.Preferred)
        policy.setVerticalPolicy(QSizePolicy.Policy.Preferred)
        label.setSizePolicy(policy)


def _apply_line_edit_policy(line_edit: QLineEdit) -> None:
    policy = line_edit.sizePolicy()
    if (
        policy.horizontalPolicy() != QSizePolicy.Policy.MinimumExpanding
        or policy.verticalPolicy() != QSizePolicy.Policy.Preferred
    ):
        policy.setHorizontalPolicy(QSizePolicy.Policy.MinimumExpanding)
        policy.setVerticalPolicy(QSizePolicy.Policy.Preferred)
        line_edit.setSizePolicy(policy)


def normalize_text_input_policies(root: QWidget) -> None:
    widgets = [root, *root.findChildren(QWidget)]
    for widget in widgets:
        if isinstance(widget, QLabel):
            _apply_label_policy(widget)
        elif isinstance(widget, QLineEdit):
            _apply_line_edit_policy(widget)


def stabilize_minimum_height(widget: QWidget, floor: int = 0) -> int:
    min_height = max(floor, widget.minimumHeight())
    widget.setMinimumHeight(min_height)
    return min_height


def available_geometry_for(widget: QWidget) -> QRect | None:
    """Return the current screen's available geometry for a widget."""
    current_rect = widget.frameGeometry()
    screen = None
    if not current_rect.isNull():
        screen = QApplication.screenAt(current_rect.center())
    if screen is None:
        window_handle = widget.windowHandle()
        if window_handle is not None:
            screen = window_handle.screen()
    if screen is None:
        screen = QApplication.primaryScreen()
    return screen.availableGeometry() if screen is not None else None


def usable_geometry_for(
    widget: QWidget,
    *,
    margin: int = WINDOW_GEOMETRY_VISIBLE_MARGIN,
) -> QRect | None:
    """Return the visible work area available to a top-level widget."""
    available = available_geometry_for(widget)
    if available is None:
        return None
    usable = available.adjusted(margin, margin, -margin, -margin)
    if usable.width() <= 0 or usable.height() <= 0:
        return available
    return usable


def resize_and_center_in_available(
    widget: QWidget,
    *,
    screen_ratio: float,
    fallback_size: tuple[int, int],
    margin: int = WINDOW_GEOMETRY_VISIBLE_MARGIN,
) -> None:
    """Size and center a top-level window inside the active screen work area."""
    usable = usable_geometry_for(widget, margin=margin)
    if usable is None:
        widget.resize(*fallback_size)
        return

    width = int(usable.width() * screen_ratio)
    height = int(usable.height() * screen_ratio)
    width = max(widget.minimumWidth(), min(width, usable.width()))
    height = max(widget.minimumHeight(), min(height, usable.height()))

    widget.resize(width, height)
    widget.move(usable.center().x() - width // 2, usable.center().y() - height // 2)


def fit_top_level_to_available(
    widget: QWidget,
    *,
    preferred_size: tuple[int, int] | None = None,
    screen_ratio: float | None = None,
    fallback_size: tuple[int, int] | None = None,
    margin: int = WINDOW_GEOMETRY_VISIBLE_MARGIN,
) -> bool:
    """Resize and center a top-level window/dialog within the active work area.

    Returns ``True`` when screen geometry was available. Dialogs can call this
    after creating their content so command buttons remain visible on smaller
    screens without changing their internal layout contracts.
    """
    usable = usable_geometry_for(widget, margin=margin)
    if usable is None:
        if fallback_size is not None:
            widget.resize(*fallback_size)
        return False

    if screen_ratio is not None:
        base_width = int(usable.width() * screen_ratio)
        base_height = int(usable.height() * screen_ratio)
    elif preferred_size is not None:
        base_width, base_height = preferred_size
    else:
        hint = widget.sizeHint()
        base_width = hint.width() if hint.isValid() else widget.width()
        base_height = hint.height() if hint.isValid() else widget.height()

    if base_width <= 0 or base_height <= 0:
        base_width, base_height = fallback_size or (usable.width(), usable.height())

    width = max(widget.minimumWidth(), min(base_width, usable.width()))
    height = max(widget.minimumHeight(), min(base_height, usable.height()))

    for _attempt in range(2):
        widget.resize(width, height)
        widget.move(usable.center().x() - width // 2, usable.center().y() - height // 2)

        frame = widget.frameGeometry()
        if frame.isNull():
            break
        frame_extra_width = max(0, frame.width() - widget.width())
        frame_extra_height = max(0, frame.height() - widget.height())
        max_content_width = max(widget.minimumWidth(), usable.width() - frame_extra_width)
        max_content_height = max(widget.minimumHeight(), usable.height() - frame_extra_height)
        next_width = min(width, max_content_width)
        next_height = min(height, max_content_height)
        if next_width == width and next_height == height:
            break
        width = next_width
        height = next_height

    return ensure_window_visible(widget, margin=margin)


def ensure_window_visible(
    widget: QWidget,
    *,
    margin: int = WINDOW_GEOMETRY_VISIBLE_MARGIN,
) -> bool:
    """Clamp a restored top-level window to the active screen, or reject stale geometry."""
    available = available_geometry_for(widget)
    if available is None:
        return False

    usable = available.adjusted(margin, margin, -margin, -margin)
    if usable.width() < widget.minimumWidth() or usable.height() < widget.minimumHeight():
        usable = available

    current = widget.frameGeometry()
    if (
        current.isNull()
        or current.width() > usable.width()
        or current.height() > usable.height()
        or not available.intersects(current)
    ):
        return False

    left = max(usable.left(), min(current.left(), usable.right() - current.width() + 1))
    top = max(usable.top(), min(current.top(), usable.bottom() - current.height() + 1))
    if left != current.left() or top != current.top():
        widget.move(left, top)
    return True


class TextInputPolicyFilter(QObject):
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Filter Qt events to enforce layout constraints."""
        if event.type() == QEvent.Type.Show and isinstance(watched, QWidget):
            normalize_text_input_policies(watched)
        return False


def install_text_input_policy_filter(app: QApplication) -> None:
    if getattr(app, "_text_input_policy_filter", None) is not None:
        return
    policy_filter = TextInputPolicyFilter(app)
    app.installEventFilter(policy_filter)
    setattr(app, "_text_input_policy_filter", policy_filter)
