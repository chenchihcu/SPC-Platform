"""
Left-side navigation as a vertical list with phase group headers.
Emits ``step_clicked(nav_index)`` with **nav_index 0..N** (sidebar buttons; map to
workspace stack via ``MainWindow.NAV_TO_STACK``). Selection uses the same index domain.

Layout: single vertical column — each phase has a muted header label followed by
its step buttons. This is the standard sidebar pattern for professional desktop apps.

Supports paired (side-by-side) buttons: when a step_names entry is a ``list[str]``
instead of a plain ``str``, the buttons are arranged horizontally on the same row.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PySide6.QtCore import Qt, Signal
from app.ui.theme.tokens import (
    SPACING_4,
    SIDEBAR_DIVIDER_HEIGHT,
)

# Type: list of (phase_label, list of step names or paired groups)
# Each item in step_names can be:
#   - str: a single nav button occupying one full row
#   - list[str]: multiple buttons placed side-by-side on the same row
NavPhasesType = list[tuple[str, list[str | list[str]]]]

# Tooltips for each step (order matches NAV_PHASES flat index)
NAV_STEP_TOOLTIPS: list[str] = [
    "選擇產品、座標、規格與量測檔，完成分析前置設定",
    "管理量測紀錄、座標、供應商與規格資料",
    "依特徵檢視 SPC 管制圖、能力與空間分析",
    "瀏覽失控、偏移、漂移與離群等文字統計摘要",
    "製程統計報告：狀態摘要、能力指標、工程結論與工單背景",
    "診斷證據矩陣：組合分析、證據判讀、圖表連動與對策建議",
    "匯出工程報告與診斷 Excel",
    "查看圖表說明、SPC 關聯與規範對照",
]


class NavigationPanel(QWidget):
    """
    Left-side navigation: vertical list with phase group headers.
    Each phase (前置 / 分析 / 設置) gets a muted section label, followed by its
    step buttons stacked vertically. This gives each button full sidebar width
    for legibility and a natural top-to-bottom reading flow.

    Supports paired buttons: when step_names contains a ``list[str]``, those
    buttons are arranged horizontally on the same row with ``paired="true"``
    QSS property for compact styling.

    Emits ``step_clicked(nav_index)`` (0..N). Method ``set_current_stack_index`` is named for
    MainWindow compatibility but takes the **same nav_index** (not raw workspace stack index).
    Styled by QSS: #navigationPanel, #navPhaseHeader, #navStepBtn.
    """

    step_clicked = Signal(int)  # nav step index 0..N（導覽鍵；非 workspace stack index）

    def __init__(
        self,
        items: list[str] | None = None,
        phases: NavPhasesType | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("navigationPanel")
        self.setMinimumWidth(0)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._step_buttons: list[QPushButton] = []
        self._current_stack_index = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(SPACING_4)

        if phases is None:
            phases = []

        stack_idx = 0
        for phase_i, (phase_label, step_names) in enumerate(phases):
            # Phase group separator: add divider line + spacing between groups (not before the first)
            # Only add spacing and header if label is NOT empty
            if phase_label:
                if phase_i > 0:
                    root.addSpacing(SPACING_4)
                    _div = QFrame()
                    _div.setObjectName("navPhaseDivider")
                    _div.setFixedHeight(SIDEBAR_DIVIDER_HEIGHT)
                    root.addWidget(_div)
                    root.addSpacing(SPACING_4)

                # Phase header — muted uppercase-style label with color-coded stage
                phase_lbl = QLabel(phase_label.upper())
                phase_lbl.setObjectName("navPhaseHeader")
                phase_lbl.setProperty("class", "navPhase")
                phase_lbl.setProperty("phase", str(phase_i))
                phase_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                root.addWidget(phase_lbl)

            for name_or_group in step_names:
                if isinstance(name_or_group, list):
                    # Paired buttons: arrange side-by-side on the same row
                    row_layout = QHBoxLayout()
                    row_layout.setContentsMargins(0, 0, 0, 0)
                    row_layout.setSpacing(SPACING_4)
                    for name in name_or_group:
                        btn = self._create_step_btn(name, stack_idx)
                        btn.setProperty("paired", "true")
                        row_layout.addWidget(btn)
                        stack_idx += 1
                    root.addLayout(row_layout)
                else:
                    # Single button: full-width row
                    btn = self._create_step_btn(name_or_group, stack_idx)
                    root.addWidget(btn)
                    stack_idx += 1

        root.addStretch(1)  # push nav items to top, remaining space below

        if self._step_buttons:
            self._step_buttons[0].setProperty("isCurrent", "true")
            self._step_buttons[0].setProperty("state", "selected")
            for b in self._step_buttons[1:]:
                b.setProperty("state", "")
            self._current_stack_index = 0
            self._refresh_step_style()

    def _create_step_btn(self, name: str, stack_idx: int) -> QPushButton:
        """Create a single navigation step button and register it."""
        btn = QPushButton(name)
        btn.setObjectName("navStepBtn")
        btn.setProperty("dataStackIndex", stack_idx)
        btn.setProperty("isCurrent", "false")
        if stack_idx < len(NAV_STEP_TOOLTIPS):
            btn.setToolTip(NAV_STEP_TOOLTIPS[stack_idx])
        btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        btn.clicked.connect(self._make_step_handler(stack_idx))
        self._step_buttons.append(btn)
        return btn

    def _make_step_handler(self, stack_index: int):
        def _on_click():
            self.step_clicked.emit(stack_index)
        return _on_click

    def _refresh_step_style(self) -> None:
        for btn in self._step_buttons:
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def set_current_stack_index(self, stack_index: int) -> None:
        """Set the current selection by **nav sidebar index** (0..N), not ``QStackedWidget`` index."""
        if stack_index == self._current_stack_index:
            return
        self._current_stack_index = stack_index
        for btn in self._step_buttons:
            idx = btn.property("dataStackIndex")
            is_current = idx == stack_index
            btn.setProperty("isCurrent", "true" if is_current else "false")
            # 維持 locked 狀態不被 selected 覆蓋
            if btn.property("state") != "locked":
                btn.setProperty("state", "selected" if is_current else "")
        self._refresh_step_style()

    def set_step_locked(self, nav_index: int, locked: bool, reason: str = "") -> None:
        """鎖定或解鎖指定導覽步驟（稽核修正 A-02：防止用戶跳過前置條件未完成的步驟）。

        Args:
            nav_index: 導覽索引 0..N。
            locked: True = 鎖定（disabled + locked 樣式），False = 解鎖。
            reason: 鎖定原因，顯示於 tooltip（如「請先完成資料設定與工單規格」）。
        """
        if nav_index < 0 or nav_index >= len(self._step_buttons):
            return
        btn = self._step_buttons[nav_index]
        btn.setEnabled(not locked)
        if locked:
            btn.setProperty("state", "locked")
            tip = reason or "請先完成前置步驟"
            btn.setToolTip(f"已鎖定：{tip}")
        else:
            # 解鎖後回到一般狀態（is_current 決定是否 selected）
            is_current = btn.property("dataStackIndex") == self._current_stack_index
            btn.setProperty("state", "selected" if is_current else "")
            # 恢復原始 tooltip
            idx = btn.property("dataStackIndex")
            if idx < len(NAV_STEP_TOOLTIPS):
                btn.setToolTip(NAV_STEP_TOOLTIPS[idx])
            else:
                btn.setToolTip("")
        self._refresh_step_style()
