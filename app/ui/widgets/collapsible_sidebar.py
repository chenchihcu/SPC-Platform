"""
Collapsible left sidebar: NavigationPanel + ControlPanel (when expanded),
with a rail and expand/collapse toggle. When collapsed, shows a minimal strip
with Next Step and Refresh buttons. Emits collapse_changed(collapsed: bool)
for main window to update splitter sizes.
"""
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QFrame,
    QStyle,
)
from PySide6.QtCore import Qt, Signal, QSize
from app.ui.widgets.navigation_panel import NavigationPanel, NavPhasesType
from app.ui.widgets.control_panel import ControlPanel
from app.bootstrap.app_config import APP_VERSION
from app.ui.theme.tokens import (
    SIDEBAR_GAP,
    SIDEBAR_NAV_MIN_HEIGHT,
    SIDEBAR_PADDING_COMPACT,
    SIDEBAR_BRAND_HEIGHT,
    RAIL_MARGIN_VERTICAL,
    RAIL_SPACING,
    RAIL_BTN_HEIGHT,
    RAIL_BTN_HEIGHT_COLLAPSED,
    RAIL_BTN_SIZE_OFFSET,
    SIDEBAR_WIDTH_EXPANDED,
    SIDEBAR_WIDTH_COLLAPSED,
    SIDEBAR_WIDTH_MAX,
    RAIL_WIDTH_EXPANDED,
    RAIL_WIDTH_COLLAPSED,
    RAIL_COLLAPSED_BTN_MARGIN,
    SIDEBAR_CONDITIONS_COLLAPSE_HEIGHT,
)


class CollapsibleSidebar(QWidget):
    """
    Left sidebar: NavigationPanel + ControlPanel in a single content area (no scroll), plus rail.
    Expanded: full width (~260px) with nav + control. Collapsed: narrow rail (56px)
    with toggle + Next Step + Refresh buttons. Exposes navigation, control_panel,
    and minimal strip buttons for MainWindow to wire signals.
    """

    collapse_changed = Signal(bool)  # True = collapsed, False = expanded

    def __init__(self, phases: NavPhasesType | None = None) -> None:
        super().__init__()
        self._collapsed = False
        self.setMinimumWidth(SIDEBAR_WIDTH_EXPANDED)
        self.setMaximumWidth(SIDEBAR_WIDTH_MAX)  # H-03: cap expanded width so sidebar can't crowd workspace

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Content: brand + workflow nav + analysis controls in one bounded sidebar.
        self._content = QWidget()
        self._content.setObjectName("sidebarContent")
        self._content.setMinimumWidth(0)
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(
            SIDEBAR_PADDING_COMPACT,
            SIDEBAR_PADDING_COMPACT,
            SIDEBAR_PADDING_COMPACT,
            SIDEBAR_PADDING_COMPACT,
        )
        content_layout.setSpacing(SIDEBAR_GAP)

        # Brand header: app name + version sub-line (professional anchor)
        self._brand = QWidget()
        self._brand.setObjectName("sidebarBrand")
        self._brand.setMinimumHeight(SIDEBAR_BRAND_HEIGHT)
        brand_layout = QVBoxLayout(self._brand)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(0)
        brand_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        brand_title = QLabel("SPI 製程統計分析")
        brand_title.setObjectName("sidebarBrandTitle")
        brand_title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        brand_layout.addWidget(brand_title)

        brand_version = QLabel(f"v{APP_VERSION}")
        brand_version.setObjectName("sidebarBrandVersion")
        brand_version.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        brand_layout.addWidget(brand_version)
        content_layout.addWidget(self._brand)

        self._nav_title = QLabel("流程")
        self._nav_title.setProperty("class", "sectionTitle")
        self._nav_title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        content_layout.addWidget(self._nav_title)

        self._nav = NavigationPanel(phases=phases)
        self._nav.setMinimumWidth(0)
        self._nav.setMinimumHeight(SIDEBAR_NAV_MIN_HEIGHT)
        self._nav.setVisible(True)
        content_layout.addWidget(self._nav, 0)
        content_layout.addWidget(self._make_divider())

        self._control_panel = ControlPanel()
        self._control_panel.setMinimumWidth(0)
        content_layout.addWidget(self._control_panel, 1)

        main_layout.addWidget(self._content, 1)

        # Rail: toggle + (when collapsed) minimal Next Step and Refresh
        self._rail = QWidget()
        self._set_exact_width(self._rail, RAIL_WIDTH_EXPANDED)
        self._rail.setObjectName("sidebarRail")
        rail_layout = QVBoxLayout(self._rail)
        rail_layout.setContentsMargins(0, RAIL_MARGIN_VERTICAL, 0, RAIL_MARGIN_VERTICAL)
        rail_layout.setSpacing(RAIL_SPACING)
        rail_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._toggle_btn = QPushButton("\u25c0")
        self._toggle_btn.setObjectName("sidebarToggleBtn")
        self._set_exact_size(self._toggle_btn, RAIL_WIDTH_EXPANDED - RAIL_BTN_SIZE_OFFSET, RAIL_BTN_HEIGHT)
        self._toggle_btn.setToolTip("收合導航 (Collapse)")
        self._toggle_btn.setAccessibleName("收合導航")
        self._toggle_btn.clicked.connect(self._on_toggle)
        rail_layout.addWidget(self._toggle_btn, 0, Qt.AlignmentFlag.AlignHCenter)

        self._minimal_next_btn = QPushButton()
        self._minimal_next_btn.setObjectName("sidebarMinimalNextBtn")
        self._minimal_next_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipForward))
        self._minimal_next_btn.setIconSize(QSize(16, 16))
        self._minimal_next_btn.setToolTip("下一步驟 (Next Step)")
        self._minimal_next_btn.setAccessibleName("精簡條下一步驟")
        self._minimal_next_btn.setVisible(False)

        self._minimal_refresh_btn = QPushButton()
        self._minimal_refresh_btn.setObjectName("sidebarMinimalRefreshBtn")
        self._minimal_refresh_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self._minimal_refresh_btn.setIconSize(QSize(16, 16))
        self._minimal_refresh_btn.setToolTip("重新分析 (Refresh)")
        self._minimal_refresh_btn.setAccessibleName("精簡條重新整理")
        self._minimal_refresh_btn.setVisible(False)

        rail_layout.addWidget(self._minimal_next_btn, 0, Qt.AlignmentFlag.AlignHCenter)
        rail_layout.addWidget(self._minimal_refresh_btn, 0, Qt.AlignmentFlag.AlignHCenter)
        rail_layout.addStretch(1)
        main_layout.addWidget(self._rail)
        self._set_exact_width(self._rail, RAIL_WIDTH_EXPANDED)
        self._sync_control_density()

    @property
    def navigation(self) -> NavigationPanel:
        """Expose inner NavigationPanel for main_window signal/slot wiring."""
        return self._nav

    @property
    def control_panel(self) -> ControlPanel:
        """Expose ControlPanel for main_window to wire actions and update status."""
        return self._control_panel

    @property
    def minimal_next_btn(self) -> QPushButton:
        """Button in collapsed rail: forward to same slot as control_panel.target_btn."""
        return self._minimal_next_btn

    @property
    def minimal_refresh_btn(self) -> QPushButton:
        """Button in collapsed rail: forward to same slot as control_panel.refresh_btn."""
        return self._minimal_refresh_btn

    def _on_toggle(self) -> None:
        self._collapsed = not self._collapsed
        if self._collapsed:
            self._content.hide()
            self._set_exact_width(self._rail, RAIL_WIDTH_COLLAPSED)
            self._toggle_btn.setText("\u25b6")
            self._toggle_btn.setToolTip("展開導航 (Expand)")
            self._toggle_btn.setAccessibleName("展開導航")
            self._set_exact_size(
                self._toggle_btn,
                RAIL_WIDTH_COLLAPSED - RAIL_COLLAPSED_BTN_MARGIN,
                RAIL_BTN_HEIGHT_COLLAPSED,
            )
            self._set_exact_size(
                self._minimal_next_btn,
                RAIL_WIDTH_COLLAPSED - RAIL_COLLAPSED_BTN_MARGIN,
                RAIL_BTN_HEIGHT_COLLAPSED,
            )
            self._set_exact_size(
                self._minimal_refresh_btn,
                RAIL_WIDTH_COLLAPSED - RAIL_COLLAPSED_BTN_MARGIN,
                RAIL_BTN_HEIGHT_COLLAPSED,
            )
            self._minimal_next_btn.setVisible(True)
            self._minimal_refresh_btn.setVisible(True)
            self.setMinimumWidth(SIDEBAR_WIDTH_COLLAPSED)
            self.setMaximumWidth(SIDEBAR_WIDTH_COLLAPSED)
            self.collapse_changed.emit(True)
        else:
            self._content.show()
            self._set_exact_width(self._rail, RAIL_WIDTH_EXPANDED)
            self._toggle_btn.setText("\u25c0")
            self._toggle_btn.setToolTip("收合導航 (Collapse)")
            self._toggle_btn.setAccessibleName("收合導航")
            self._set_exact_size(self._toggle_btn, RAIL_WIDTH_EXPANDED - RAIL_BTN_SIZE_OFFSET, RAIL_BTN_HEIGHT)
            self._minimal_next_btn.setVisible(False)
            self._minimal_refresh_btn.setVisible(False)
            self.setMinimumWidth(SIDEBAR_WIDTH_EXPANDED)
            self.setMaximumWidth(SIDEBAR_WIDTH_MAX)  # H-03: restore cap on expand
            self.collapse_changed.emit(False)
            self._sync_control_density()

    def is_collapsed(self) -> bool:
        return self._collapsed

    def set_collapsed(self, collapsed: bool) -> None:
        if self._collapsed == collapsed:
            return
        self._on_toggle()

    def resizeEvent(self, event) -> None:
        """Re-evaluate sidebar density whenever the available height changes."""
        super().resizeEvent(event)
        self._sync_control_density()

    def _sync_control_density(self) -> None:
        # If the user has manually toggled the condition section, do not auto-collapse on resize
        if getattr(self._control_panel, "_user_toggled", False):
            return
        collapse_conditions = (
            not self._collapsed
            and self.height() < SIDEBAR_CONDITIONS_COLLAPSE_HEIGHT
        )
        self._control_panel.set_condition_section_collapsed(collapse_conditions)

    @staticmethod
    def _set_exact_width(widget: QWidget, width: int) -> None:
        widget.setMinimumWidth(width)
        widget.setMaximumWidth(width)

    @staticmethod
    def _set_exact_size(widget: QWidget, width: int, height: int) -> None:
        widget.setMinimumSize(width, height)
        widget.setMaximumSize(width, height)

    @staticmethod
    def _make_divider() -> QFrame:
        divider = QFrame()
        divider.setObjectName("sidebarDivider")
        divider.setFrameShape(QFrame.Shape.HLine)
        return divider
