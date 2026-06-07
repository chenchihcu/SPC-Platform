"""
Minimal page layout helpers (spec L-01). Use tokens for spacing and max width.
Does not change business logic; provides consistent structure for form / data / preview pages.

雙欄工程表單頁 (Two-column form page) pattern
-----------------------------------------
適用於「左欄 + 右欄 + 底部主操作」的工程表單頁，可滿版利用主內容區，避免置中窄條空白。

結構：
  1. Page header 區：頁標題 (pageTitle)，與主內容區以 PAGE_HEADER_BOTTOM_SPACING 分隔。
  2. 2-column content layout：左右兩欄等寬 (stretch 1:1)，可設 TWO_COLUMN_MIN_COLUMN_WIDTH 避免過窄。
  3. Group box 統一樣式：使用全域 QGroupBox 樣式；標題與框線不重疊依賴 tokens 的 GROUPBOX_TITLE_MARGIN_TOP。
  4. Page primary action 區：雙欄下方一列，用於「儲存設定」等主操作按鈕，與雙欄以 PRIMARY_ACTION_TOP_SPACING 分隔。
  5. Section title 避免與框線重疊：GROUPBOX_TITLE_MARGIN_TOP >= 18，QGroupBox::title 的 subcontrol-origin: margin 才有足夠空間。

使用方式：先 page_margins_and_spacing(layout)，再 setup_two_column_form_page(layout, "頁標題")，
然後將左欄內容加入 .left_column、右欄加入 .right_column、主按鈕加入 .primary_action_layout。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QSizePolicy,
    QFrame,
    QPushButton,
    QTableWidget,
    QAbstractItemView,
    QAbstractScrollArea,
    QApplication,
    QHeaderView,
    QStyle,
)
from PySide6.QtCore import Qt

from app.ui.theme.tokens import (
    SPACING_4,
    SPACING_8,
    SPACING_12,
    SPACING_16,
    SPACING_20,
    PAGE_CONTENT_MARGIN,
    PAGE_CONTENT_SPACING,
    PAGE_HEADER_BOTTOM_SPACING,
    TWO_COLUMN_CONTENT_SPACING,
    TWO_COLUMN_STRETCH_LEFT,
    TWO_COLUMN_STRETCH_RIGHT,
    TWO_COLUMN_MIN_COLUMN_WIDTH,
    PRIMARY_ACTION_TOP_SPACING,
    LEFT_ALIGN_BUTTON_ROW_GAP,
    STATUS_LAMP_SIZE,
    LABEL_ROW_MIN_HEIGHT,
    INPUT_MIN_HEIGHT,
    BUTTON_MIN_HEIGHT,
    TABLE_ROW_MIN_HEIGHT,
)

TableRole = Literal["default", "reference", "library", "diagnostic"]

BUTTON_ICON_KEYS: dict[str, QStyle.StandardPixmap] = {
    "save": QStyle.StandardPixmap.SP_DialogSaveButton,
    "clear": QStyle.StandardPixmap.SP_DialogResetButton,
    "reset": QStyle.StandardPixmap.SP_BrowserReload,
    "search": QStyle.StandardPixmap.SP_FileDialogStart,
    "export": QStyle.StandardPixmap.SP_DialogOpenButton,
    "delete": QStyle.StandardPixmap.SP_TrashIcon,
    "cancel": QStyle.StandardPixmap.SP_DialogCancelButton,
    "apply": QStyle.StandardPixmap.SP_DialogApplyButton,
    "info": QStyle.StandardPixmap.SP_MessageBoxInformation,
    "open": QStyle.StandardPixmap.SP_DirOpenIcon,
}


@dataclass
class TwoColumnFormPageLayout:
    """雙欄工程表單頁的 layout 區塊，由 setup_two_column_form_page 回傳，供呼叫端填入左/右欄與主操作。"""
    header_label: QLabel
    content_area: QWidget
    left_column: QWidget
    right_column: QWidget
    primary_action_layout: QHBoxLayout


def setup_two_column_form_page(layout: QVBoxLayout, page_title: str) -> TwoColumnFormPageLayout:
    """
    建立雙欄工程表單頁結構：page header + 滿版左右雙欄 + 主操作區。
    呼叫前需已對 layout 套用 page_margins_and_spacing(layout)。
    """
    header = QLabel(page_title)
    header.setProperty("class", "pageTitle")
    header.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    layout.addWidget(header)
    layout.addSpacing(PAGE_HEADER_BOTTOM_SPACING)

    content_area = QWidget()
    content_area.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
    content_v = QVBoxLayout(content_area)
    content_v.setContentsMargins(0, 0, 0, 0)
    content_v.setSpacing(PRIMARY_ACTION_TOP_SPACING)

    row = QHBoxLayout()
    row.setSpacing(TWO_COLUMN_CONTENT_SPACING)
    left_col = QWidget()
    left_col.setMinimumWidth(TWO_COLUMN_MIN_COLUMN_WIDTH)
    left_col.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    left_layout = QVBoxLayout(left_col)
    left_layout.setContentsMargins(0, 0, 0, 0)
    right_col = QWidget()
    right_col.setMinimumWidth(TWO_COLUMN_MIN_COLUMN_WIDTH)
    right_col.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    right_layout = QVBoxLayout(right_col)
    right_layout.setContentsMargins(0, 0, 0, 0)
    row.addWidget(left_col, TWO_COLUMN_STRETCH_LEFT)
    row.addWidget(right_col, TWO_COLUMN_STRETCH_RIGHT)
    content_v.addLayout(row)

    primary_action_row = QWidget()
    primary_action_layout = QHBoxLayout(primary_action_row)
    primary_action_layout.setContentsMargins(0, 0, 0, 0)
    primary_action_layout.setSpacing(LEFT_ALIGN_BUTTON_ROW_GAP)
    content_v.addWidget(primary_action_row)

    layout.addWidget(content_area, 1)
    return TwoColumnFormPageLayout(
        header_label=header,
        content_area=content_area,
        left_column=left_col,
        right_column=right_col,
        primary_action_layout=primary_action_layout,
    )


def create_page_shell(page_title: str = "") -> tuple[QWidget, QVBoxLayout]:
    """Create a reference-style page shell with standard margins and optional title."""
    shell = QWidget()
    layout = QVBoxLayout(shell)
    page_margins_and_spacing(layout)
    if page_title:
        title = QLabel(page_title)
        title.setProperty("class", "pageTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(title)
        layout.addSpacing(SPACING_8)
    return shell, layout


def create_section_card(title: str = "", subtitle: str = "") -> tuple[QFrame, QVBoxLayout]:
    """Create a card-framed work area with optional title and subtitle labels."""
    card = QFrame()
    card.setObjectName("stepCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(SPACING_16, SPACING_12, SPACING_16, SPACING_12)
    layout.setSpacing(SPACING_12)
    if title:
        title_label = QLabel(title)
        title_label.setProperty("class", "stepTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(title_label)
    if subtitle:
        subtitle_label = QLabel(subtitle)
        subtitle_label.setProperty("class", "caption")
        subtitle_label.setWordWrap(True)
        layout.addWidget(subtitle_label)
    return card, layout


def create_form_grid(
    *,
    horizontal_spacing: int = SPACING_20,
    vertical_spacing: int = SPACING_12,
) -> QGridLayout:
    """Create the dense form grid used by factory data-entry pages."""
    grid = QGridLayout()
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setHorizontalSpacing(horizontal_spacing)
    grid.setVerticalSpacing(vertical_spacing)
    return grid


def add_labeled_field(
    grid: QGridLayout,
    row: int,
    col: int,
    label_text: str,
    widget: QWidget,
    *,
    label_min_width: int | None = None,
    field_minimum_width: int | None = None,
    col_span: int = 1,
) -> QLabel:
    """Add a right-aligned label and field pair to a form grid."""
    label = _form_label(label_text)
    label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    bind_label_to_widget(label, widget, label_text)
    if label_min_width is not None:
        label.setMinimumWidth(label_min_width)
    if field_minimum_width is not None and hasattr(widget, "setMinimumWidth"):
        widget.setMinimumWidth(field_minimum_width)
    if hasattr(widget, "setMinimumHeight"):
        widget.setMinimumHeight(INPUT_MIN_HEIGHT)
    grid.addWidget(label, row, col * 2)
    grid.addWidget(widget, row, col * 2 + 1, 1, col_span)
    return label


def _normalize_accessible_text(text: str) -> str:
    """Strip presentation-only punctuation before exposing label text to AT."""
    return text.replace("&", "").rstrip(":：").strip()


def bind_label_to_widget(label: QLabel, widget: QWidget, label_text: str) -> None:
    """Bind a visible form label to its field and seed basic accessibility metadata."""
    accessible_text = _normalize_accessible_text(label_text)
    label.setBuddy(widget)
    if accessible_text and not label.accessibleName():
        label.setAccessibleName(accessible_text)
    if accessible_text and not widget.accessibleName():
        widget.setAccessibleName(accessible_text)


_STATUS_ACCESSIBLE_STATE_TEXT: dict[str, str] = {
    "idle": "未載入",
    "pending": "待完成",
    "loading": "處理中",
    "success": "已就緒",
    "ok": "已就緒",
    "warning": "需要注意",
    "error": "錯誤",
    "info": "資訊",
    "ready": "已就緒",
    "incompatible": "目前不適用",
    "nodata": "無資料",
}


def apply_status_accessibility(
    lamp: QFrame,
    label: QLabel,
    *,
    state: str | None = None,
    text: str | None = None,
) -> None:
    """Keep decorative lamps out of the way and expose state through adjacent text."""
    current_state = (state or str(lamp.property("state") or "idle")).strip() or "idle"
    current_text = (text if text is not None else label.text()).strip()
    state_text = _STATUS_ACCESSIBLE_STATE_TEXT.get(current_state, current_state)
    lamp.setAccessibleName("")
    lamp.setAccessibleDescription("裝飾性狀態指示，請以相鄰狀態文字為準。")
    label.setProperty("state", current_state)
    if current_text:
        label.setAccessibleName(current_text)
        label.setAccessibleDescription(f"狀態：{state_text}。顯示：{current_text}")
    else:
        label.setAccessibleDescription(f"狀態：{state_text}")


def set_button_role(button: QPushButton, role: str) -> None:
    """Set the semantic button role consumed by the global QSS."""
    button.setProperty("class", role)
    button.setMinimumHeight(BUTTON_MIN_HEIGHT)
    button.style().unpolish(button)
    button.style().polish(button)


def set_drop_zone_active(frame: QFrame, active: bool) -> None:
    """Apply the shared drag-over state consumed by the global drop-zone QSS."""
    frame.setProperty("state", "active" if active else "")
    frame.style().unpolish(frame)
    frame.style().polish(frame)


def apply_button_icon(button: QPushButton, icon_key: str) -> None:
    """Apply a platform-native Qt standard icon to a button."""
    pixmap_name = BUTTON_ICON_KEYS.get(icon_key)
    if pixmap_name is None:
        return
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        return
    button.setIcon(app.style().standardIcon(pixmap_name))


def style_table(table: QTableWidget, role: TableRole = "default") -> None:
    """Apply shared dense table behavior for data, reference, and diagnostic views."""
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.verticalHeader().hide()
    table.setWordWrap(role in {"reference", "diagnostic"})
    table.setShowGrid(True)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setDefaultSectionSize(TABLE_ROW_MIN_HEIGHT)
    table.verticalHeader().setMinimumSectionSize(TABLE_ROW_MIN_HEIGHT)
    header = table.horizontalHeader()
    if role in {"reference", "diagnostic"}:
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
    else:
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    if role == "diagnostic":
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored)
        table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        table.setMinimumWidth(0)
        header.setStretchLastSection(False)
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        table.setMinimumHeight(0)


def create_summary_card(label: str, value: str, icon_key: str | None = None) -> QFrame:
    """Create a compact KPI summary card."""
    card = QFrame()
    card.setProperty("class", "kpiCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(SPACING_12, SPACING_8, SPACING_12, SPACING_8)
    layout.setSpacing(SPACING_4)
    value_label = QLabel(value)
    value_label.setProperty("class", "kpiValue")
    value_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    label_label = QLabel(label)
    label_label.setProperty("class", "caption")
    label_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    layout.addWidget(value_label)
    layout.addWidget(label_label)
    if icon_key:
        card.setToolTip(icon_key)
    return card


def create_status_badge(text: str, state: str = "info") -> QLabel:
    """Create a small status badge label with semantic state styling."""
    badge = QLabel(text)
    badge.setProperty("class", "statusIndicator")
    badge.setProperty("state", state)
    badge.setMinimumHeight(LABEL_ROW_MIN_HEIGHT)
    badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return badge


def create_status_lamp() -> QFrame:
    """建立統一的狀態指示燈：class=statusBarLamp (Pass 12)."""
    lamp = QFrame()
    lamp.setObjectName("statusBarLamp")
    lamp.setMinimumSize(STATUS_LAMP_SIZE, STATUS_LAMP_SIZE)
    lamp.setMaximumSize(STATUS_LAMP_SIZE, STATUS_LAMP_SIZE)
    lamp.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    lamp.setProperty("state", "idle")
    lamp.setAccessibleName("")
    lamp.setAccessibleDescription("裝飾性狀態指示，請以相鄰狀態文字為準。")
    return lamp


def setup_page_header_with_status(layout: QVBoxLayout, page_title: str) -> tuple[QLabel, QFrame, QLabel]:
    """
    建立帶有狀態指示燈的頁面標題：[Title] .... [Lamp] [StatusText]
    """
    header_frame = QFrame()
    header_frame.setProperty("class", "headerToolbar")
    header_frame.setProperty("headerRole", "utilityHeader")
    header_row = QHBoxLayout(header_frame)
    header_row.setContentsMargins(SPACING_16, SPACING_8, SPACING_16, SPACING_8)
    header_row.setSpacing(SPACING_8)

    header = QLabel(page_title)
    header.setProperty("class", "pageTitle")
    header.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    header_row.addWidget(header)

    header_row.addStretch(1) # Pushes lamp to the right

    lamp = create_status_lamp()
    header_row.addWidget(lamp)

    status_lbl = QLabel("未載入")
    status_lbl.setProperty("class", "statusIndicator")
    status_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    apply_status_accessibility(lamp, status_lbl, state="idle", text=status_lbl.text())
    header_row.addWidget(status_lbl)

    layout.addWidget(header_frame)
    if page_title:
        layout.addSpacing(PAGE_HEADER_BOTTOM_SPACING)
    else:
        # If no title, use smaller spacing or none to save space
        header.hide()
    return header, lamp, status_lbl


def setup_compact_title_header(layout: QVBoxLayout, page_title: str) -> QLabel:
    """建立只顯示頁名的緊湊頁首，頁面狀態放到就近工具列或底部狀態列。"""
    header_frame = QFrame()
    header_frame.setProperty("class", "headerToolbar")
    header_frame.setProperty("headerRole", "utilityHeader")
    header_frame.setProperty("headerDensity", "compact")
    header_row = QHBoxLayout(header_frame)
    header_row.setContentsMargins(SPACING_8, SPACING_4, SPACING_8, SPACING_4)
    header_row.setSpacing(SPACING_8)

    header = QLabel(page_title)
    header.setProperty("class", "pageTitle")
    header.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    header_row.addWidget(header)
    header_row.addStretch(1)

    layout.addWidget(header_frame)
    if page_title:
        layout.addSpacing(PAGE_HEADER_BOTTOM_SPACING)
    return header


def setup_multi_status_header(layout: QVBoxLayout, page_title: str, status_items: list[tuple[str, str]]) -> tuple[QLabel, dict[str, tuple[QFrame, QLabel]]]:
    """
    建立帶有多個狀態指示燈的頁面標題：[Title] .... [Lamp1][Text1] [Lamp2][Text2] ...
    status_items: list of (key, label_text)
    Returns: (header_label, {key: (lamp, status_lbl)})
    """
    header_row = QHBoxLayout()
    header_row.setContentsMargins(0, 0, 0, 0)
    header_row.setSpacing(SPACING_12)

    header = QLabel(page_title)
    header.setProperty("class", "pageTitle")
    header.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    header_row.addWidget(header)

    header_row.addStretch(1)

    res = {}
    for key, txt in status_items:
        item_lay = QHBoxLayout()
        item_lay.setSpacing(SPACING_4)
        lamp = create_status_lamp()
        lbl = QLabel(txt)
        lbl.setProperty("class", "statusIndicator")
        apply_status_accessibility(lamp, lbl, state="idle", text=txt)
        item_lay.addWidget(lamp)
        item_lay.addWidget(lbl)
        header_row.addLayout(item_lay)
        header_row.addSpacing(SPACING_8)
        res[key] = (lamp, lbl)

    layout.addLayout(header_row)
    if page_title:
        layout.addSpacing(PAGE_HEADER_BOTTOM_SPACING)
    else:
        header.hide()
    return header, res


def _form_label(text: str) -> QLabel:
    """建立統一的表單標籤：class=formLabel，左對齊，不壓縮 (Used in multiple pages)."""
    lbl = QLabel(text)
    lbl.setProperty("class", "formLabel")
    lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    lbl.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
    return lbl


def form_field_row(
    label_text: str,
    widget: QWidget,
    action_btn: QWidget | None = None,
    label_min_width: int | None = None,
    row_min_height: int | None = None,
    action_min_width: int | None = None,
) -> QVBoxLayout:
    """
    建立「標籤在上、控件在下」的垂直表單行，減少各頁面重複代碼 (Pass 1).
    適用於窄欄排版，避免 Grid 水平擠壓。
    """
    row = QVBoxLayout()
    row.setSpacing(SPACING_4)
    row.setContentsMargins(0, 0, 0, 0)
    lbl = _form_label(label_text)
    if label_min_width is not None:
        lbl.setMinimumWidth(label_min_width)
        lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
    row.addWidget(lbl)
    if row_min_height is not None and hasattr(widget, "setMinimumHeight"):
        widget.setMinimumHeight(row_min_height)
    if action_btn is not None:
        if row_min_height is not None and hasattr(action_btn, "setMinimumHeight"):
            action_btn.setMinimumHeight(row_min_height)
        if action_min_width is not None and hasattr(action_btn, "setMinimumWidth"):
            action_btn.setMinimumWidth(action_min_width)
        h = QHBoxLayout()
        h.setSpacing(SPACING_8)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(widget, 1)
        h.addWidget(action_btn, 0)
        row.addLayout(h)
    else:
        row.addWidget(widget)
    return row


def page_margins_and_spacing(layout: QVBoxLayout) -> None:
    """Apply consistent page margins and spacing from tokens (spec L-05).

    Note: 不設 AlignTop — 各頁面自行決定對齊方式。
    AlignTop 會阻止 stretch>0 的子 widget 垂直擴展（BUG-5 橫向展開 FINDING-1）。
    """
    # Global page layout baseline: all pages use the same margin/spacing tokens.
    layout.setContentsMargins(
        PAGE_CONTENT_MARGIN, PAGE_CONTENT_MARGIN,
        PAGE_CONTENT_MARGIN, PAGE_CONTENT_MARGIN,
    )
    layout.setSpacing(PAGE_CONTENT_SPACING)


_PRESENTATION_ONLY_EMPTY_STATE_ICONS = {"📊", "📋"}


def empty_state_label(text: str, icon: str = "") -> QLabel:
    """Label for empty state; use class placeholderMessage for styling.
    Optional text icon keys may be prepended, but emoji icons are suppressed.
    """
    display = text if icon in _PRESENTATION_ONLY_EMPTY_STATE_ICONS else f"{icon}\n{text}" if icon else text
    lbl = QLabel(display)
    lbl.setProperty("class", "placeholderMessage")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setWordWrap(True)
    return lbl
