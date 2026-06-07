"""
App-wide background status model for load/analyze/report/export.
Drives the status bar widget (lamp + text). Reusable across the project.
"""
from __future__ import annotations

from typing import Optional
from PySide6.QtCore import QObject, Signal

# State constants for lamp + semantics
STATE_IDLE = "idle"
STATE_LOADING = "loading"
STATE_ANALYZING = "analyzing"
STATE_SUCCESS = "success"
STATE_ERROR = "error"


class AppStatusModel(QObject):
    """
    Central status for background operations. Emits state_changed(state, message)
    for the status bar to show lamp + text.
    """

    state_changed = Signal(str, str)  # state, message
    progress_changed = Signal(int)    # 0-100, -1 for indeterminate, -2 to hide

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._state = STATE_IDLE
        self._message = "就緒 (Ready)"
        self._detail: Optional[str] = None
        self._progress = -2  # -2 means hidden

    @property
    def state(self) -> str:
        """Return the current application status state."""
        return self._state

    @property
    def message(self) -> str:
        """Return the primary status message string."""
        return self._message

    @property
    def detail(self) -> Optional[str]:
        """Return the secondary detail string."""
        return self._detail

    @property
    def progress(self) -> int:
        """Return current progress (-1 indeterminate, -2 hidden)."""
        return self._progress

    def set_state(self, state: str, message: str, detail: Optional[str] = None) -> None:
        """Set status state, message, and optional detail directly."""
        self._state = state
        self._message = message
        self._detail = detail
        if state not in (STATE_LOADING, STATE_ANALYZING):
            self._progress = -2
            self.progress_changed.emit(-2)
        self.state_changed.emit(state, message)

    def set_progress(self, value: int) -> None:
        """Update progress value and emit signal."""
        self._progress = value
        self.progress_changed.emit(value)

    def set_busy(self, reason: str) -> None:
        """Transition to busy state with the given message."""
        self.set_state(STATE_LOADING, reason)

    def set_analyzing(self, message: str = "正在分析…") -> None:
        """Transition to analyzing state."""
        self.set_state(STATE_ANALYZING, message)

    def set_done(self, success: bool, message: str, detail: Optional[str] = None) -> None:
        """Transition to done/idle state with optional summary message."""
        self.set_state(STATE_SUCCESS if success else STATE_ERROR, message, detail)

    def clear_error(self) -> None:
        """Clear any current error state and return to idle."""
        if self._state == STATE_ERROR:
            self.set_state(STATE_IDLE, "就緒 (Ready)")
