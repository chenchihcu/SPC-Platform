"""
Bottom status bar: app-state lamp + message (left) and connection-status signal lamps (right).

Connection lamps show data load state (座標/量測/關聯) as small colored dots with short labels,
replacing the former sidebar status card. Styled by QSS via objectName and [state] property.
"""
from typing import TYPE_CHECKING, Optional

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt

from app.ui.theme.tokens import (
    SPACING_4,
    SPACING_8,
    SPACING_12,
    CONTROL_STATUS_LINE_MIN_HEIGHT,
    STATUS_LAMP_SIZE,
    CONN_LAMP_SIZE,
    STATUS_PROGRESS_BAR_HEIGHT,
    STATUS_PROGRESS_MIN_WIDTH,
    STATUS_PROGRESS_MAX_WIDTH,
)
from app.ui.widgets.page_templates import apply_status_accessibility

if TYPE_CHECKING:
    from app.ui.state.app_status_model import AppStatusModel


class StatusBarWidget(QWidget):
    """
    Status bar content: app-state lamp + text (left), connection signal lamps (right).

    Left section driven by AppStatusModel (state_changed) or set_message().
    Right section updated by update_connection_status(coord_meta, meas_meta, relation_meta).
    Styled by QSS: #statusBarLamp, #statusBarLabel, .connLamp, .connLabel.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACING_8, SPACING_4, SPACING_8, SPACING_4)
        layout.setSpacing(SPACING_12)

        # ── Left: app-state lamp + message ──
        self._lamp = QFrame()
        self._lamp.setObjectName("statusBarLamp")
        self._lamp.setMinimumSize(STATUS_LAMP_SIZE, STATUS_LAMP_SIZE)
        self._lamp.setMaximumSize(STATUS_LAMP_SIZE, STATUS_LAMP_SIZE)
        self._lamp.setProperty("state", "idle")
        layout.addWidget(self._lamp)

        self._label = QLabel("就緒 (Ready)")
        self._label.setObjectName("statusBarLabel")
        self._label.setMinimumHeight(CONTROL_STATUS_LINE_MIN_HEIGHT)
        self._label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        apply_status_accessibility(self._lamp, self._label, state="idle", text=self._label.text())
        layout.addWidget(self._label)

        # ── Progress Bar ──
        from PySide6.QtWidgets import QProgressBar
        self._progress_bar = QProgressBar()
        self._progress_bar.setObjectName("statusBarProgress")
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(STATUS_PROGRESS_BAR_HEIGHT)
        self._progress_bar.setMinimumWidth(STATUS_PROGRESS_MIN_WIDTH)
        self._progress_bar.setMaximumWidth(STATUS_PROGRESS_MAX_WIDTH)
        self._progress_bar.setVisible(False)
        self._progress_bar.setAccessibleName("分析進度")
        self._progress_bar.setAccessibleDescription("目前沒有進度資訊。")
        layout.addWidget(self._progress_bar)

        layout.addStretch(1) # Stretch between label/progress and right icons

        # ── Right: connection signal lamps ──
        # Separator
        sep = QFrame()
        sep.setObjectName("statusBarSep")
        sep.setFrameShape(QFrame.Shape.VLine)
        layout.addWidget(sep)

        # Coord lamp
        self._coord_lamp = self._make_conn_lamp("connLampCoord")
        self._coord_label = self._make_conn_label("座標")
        apply_status_accessibility(self._coord_lamp, self._coord_label, state="pending", text=self._coord_label.text())
        layout.addSpacing(SPACING_4)
        layout.addWidget(self._coord_lamp)
        layout.addWidget(self._coord_label)

        # Meas lamp
        layout.addSpacing(SPACING_12)
        self._meas_lamp = self._make_conn_lamp("connLampMeas")
        self._meas_label = self._make_conn_label("量測")
        apply_status_accessibility(self._meas_lamp, self._meas_label, state="pending", text=self._meas_label.text())
        layout.addWidget(self._meas_lamp)
        layout.addWidget(self._meas_label)

        # Match rate lamp
        layout.addSpacing(SPACING_12)
        self._rate_lamp = self._make_conn_lamp("connLampRate")
        self._rate_label = self._make_conn_label("關聯 --")
        apply_status_accessibility(self._rate_lamp, self._rate_label, state="pending", text=self._rate_label.text())
        layout.addWidget(self._rate_lamp)
        layout.addWidget(self._rate_label)
        layout.addSpacing(SPACING_4)

        self._model: Optional["AppStatusModel"] = None

    # ── Factory helpers ──

    def _make_conn_lamp(self, object_name: str) -> QFrame:
        """Create a small circular lamp indicator for connection status."""
        lamp = QFrame()
        lamp.setObjectName(object_name)
        lamp.setProperty("class", "connLamp")
        lamp.setProperty("state", "pending")
        lamp.setMinimumSize(CONN_LAMP_SIZE, CONN_LAMP_SIZE)
        lamp.setMaximumSize(CONN_LAMP_SIZE, CONN_LAMP_SIZE)
        return lamp

    def _make_conn_label(self, text: str) -> QLabel:
        """Create a compact label next to a connection lamp."""
        lbl = QLabel(text)
        lbl.setProperty("class", "connLabel")
        lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        return lbl

    # ── App-state binding ──

    def set_status_model(self, model: "AppStatusModel") -> None:
        """Bind the status bar to an AppStatusModel instance."""
        if self._model is not None:
            self._model.state_changed.disconnect(self._on_state_changed)
        self._model = model
        self._model.state_changed.connect(self._on_state_changed)
        self._model.progress_changed.connect(self._on_progress_changed)
        self._on_state_changed(model.state, model.message)
        self._on_progress_changed(model.progress)

    def _on_state_changed(self, state: str, message: str) -> None:
        self._lamp.setProperty("state", state)
        self._label.setText(message)
        apply_status_accessibility(self._lamp, self._label, state=state, text=message)
        self._lamp.style().unpolish(self._lamp)
        self._lamp.style().polish(self._lamp)

    def _on_progress_changed(self, value: int) -> None:
        """Handle progress signal: -1 (indeterminate), -2 (hidden), or 0-100."""
        if value <= -2:
            self._progress_bar.setVisible(False)
            self._progress_bar.setAccessibleDescription("目前未顯示進度。")
        else:
            self._progress_bar.setVisible(True)
            if value == -1:
                self._progress_bar.setRange(0, 0)
                self._progress_bar.setAccessibleDescription("分析進行中，進度尚未確定。")
            else:
                self._progress_bar.setRange(0, 100)
                self._progress_bar.setValue(value)
                self._progress_bar.setAccessibleDescription(f"分析進度 {value}%。")

    def set_message(self, text: str) -> None:
        """Backward compatibility: update label only. Lamp state unchanged unless driven by model."""
        self._label.setText(text)

    # ── Connection status (moved from ControlPanel) ──

    def update_connection_status(self, coord_meta: dict, meas_meta: dict, relation_meta: dict) -> None:
        """Update the three connection signal lamps (座標 / 量測 / 關聯) in the status bar."""
        c_ok = coord_meta.get("is_valid", False)
        m_ok = meas_meta.get("is_valid", False)
        rate = relation_meta.get("match_rate", -1.0)

        # Coord
        coord_state = "ok" if c_ok else "pending"
        coord_text = "座標 ✓" if c_ok else "座標"
        self._coord_lamp.setProperty("state", coord_state)
        self._coord_label.setText(coord_text)
        apply_status_accessibility(self._coord_lamp, self._coord_label, state=coord_state, text=coord_text)

        # Meas
        meas_state = "ok" if m_ok else "pending"
        meas_text = "量測 ✓" if m_ok else "量測"
        self._meas_lamp.setProperty("state", meas_state)
        self._meas_label.setText(meas_text)
        apply_status_accessibility(self._meas_lamp, self._meas_label, state=meas_state, text=meas_text)

        # Match rate
        if rate < 0:
            rate_state = "pending"
            rate_text = "關聯 --"
        elif rate >= 90:
            rate_state = "ok"
            rate_text = f"關聯 {rate:.0f}%"
        elif rate > 0:
            rate_state = "warning"
            rate_text = f"關聯 {rate:.0f}%"
        else:
            rate_state = "pending"
            rate_text = "關聯 0%"
        self._rate_lamp.setProperty("state", rate_state)
        self._rate_label.setText(rate_text)
        apply_status_accessibility(self._rate_lamp, self._rate_label, state=rate_state, text=rate_text)

        # Refresh QSS state for all lamps
        for w in (self._coord_lamp, self._meas_lamp, self._rate_lamp):
            w.style().unpolish(w)
            w.style().polish(w)
