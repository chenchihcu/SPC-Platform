"""
Global light theme QSS. Uses tokens as the single source of visual truth.
"""
import re
from app.ui.theme.tokens import (
    BG_PRIMARY,
    BG_SECONDARY,
    BG_BLOCK,
    BG_PANEL,
    BG_CARD,
    BORDER_SUBTLE,
    SURFACE_HOVER,
    SURFACE_HOVER_SUBTLE,
    SURFACE_ACTIVE,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
    TEXT_DISABLED,
    TEXT_ON_ACCENT,
    TEXT_STATE_INCOMPATIBLE,
    BORDER_INCOMPATIBLE,
    BG_STATE_INCOMPATIBLE,
    PRIMARY_100,
    PRIMARY_300,
    PRIMARY_700,
    ACCENT_PRIMARY,
    ACCENT_PRIMARY_HOVER,
    ACCENT_SUCCESS,
    ACCENT_SUCCESS_HOVER,
    ACCENT_WARNING,
    ACCENT_ERROR,
    ACCENT_ERROR_HOVER,
    BORDER,
    BORDER_HOVER,
    SCROLLBAR_HANDLE,
    SCROLLBAR_HANDLE_HOVER,
    TABLE_HEADER_BG,
    SIDEBAR_BRAND_FONT_SIZE,
    SIDEBAR_BRAND_VERSION_FONT_SIZE,
    SIDEBAR_DB_BODY_FONT_SIZE,
    SIDEBAR_DB_BUTTON_HEIGHT,
    SIDEBAR_DB_COUNT_FONT_SIZE,
    SIDEBAR_DB_TITLE_FONT_SIZE,
    NAV_STEP_BTN_HEIGHT,
    SPACING_XXS,
    SPACING_4,
    SPACING_8,
    SPACING_12,
    SPACING_16,
    SPACING_20,
    SPACING_XS,
    SPACING_SM,
    FONT_FAMILY,
    FONT_FAMILY_MONO,
    FONT_SIZE_BODY,
    FONT_SIZE_CAPTION,
    FONT_SIZE_SECTION,
    FONT_SIZE_SMALL,
    FONT_SIZE_TITLE,
    FONT_SIZE_MONO,
    FONT_SIZE_PLACEHOLDER,
    FONT_SIZE_DISABLED,
    SIDEBAR_SECTION_TITLE_FONT_SIZE,
    SIDEBAR_NAV_FONT_SIZE,
    SIDEBAR_LABEL_FONT_SIZE,
    SIDEBAR_PHASE_FONT_SIZE,
    SIDEBAR_COMPACT_ACTION_HEIGHT,
    SIDEBAR_COMPACT_FEATURE_HEIGHT,
    SIDEBAR_COMPACT_INPUT_HEIGHT,
    RADIUS_SM,
    RADIUS_MD,
    RADIUS_BUTTON,
    CARD_RADIUS,
    BUTTON_MIN_HEIGHT,
    CONTROL_STATUS_LINE_MIN_HEIGHT,
    GROUPBOX_TITLE_MARGIN_TOP,
    GROUPBOX_TITLE_PADDING_TOP,
    STATUS_LAMP_IDLE,
    STATUS_LAMP_LOADING,
    STATUS_LAMP_WARNING,
    STATUS_LAMP_SUCCESS,
    STATUS_LAMP_ERROR,
    STATUS_LAMP_SIZE,
    LABEL_ROW_MIN_HEIGHT,
    INPUT_MIN_HEIGHT,
    SECTION_TITLE_MIN_HEIGHT,
    CHART_DESC_MIN_HEIGHT,
    SIDEBAR_MINIMAL_BTN_MIN_HEIGHT,
    HEADER_TOOLBAR_MIN_HEIGHT,
    COMPACT_HEADER_TOOLBAR_MIN_HEIGHT,
    COMPACT_HEADER_MARGIN_H,
    COMPACT_HEADER_MARGIN_V,
    TABLE_TOOLBAR_MARGIN_H,
    TABLE_TOOLBAR_MARGIN_V,
    TABLE_TOOLBAR_MIN_HEIGHT,
    DETAIL_CARD_MIN_HEIGHT,
    FOCUS_RING_BORDER,
    APPLE_GLASS_TINT,
    APPLE_GLASS_BORDER,
    FONT_WEIGHT_BOLD,
    FONT_WEIGHT_NORMAL,
    DATA_SETUP_DENSE_STEP_TITLE_MIN_HEIGHT,
    DATA_SETUP_DENSE_CAPTION_MIN_HEIGHT,
    DATA_SETUP_DENSE_FORM_LABEL_MIN_HEIGHT,
    DATA_SETUP_DENSE_LIST_PADDING,
    TABLE_ROW_MIN_HEIGHT,
    BTN_GRAD_LIGHT,
    CONFIDENCE_BAR_HEIGHT,
    DIAG_CONFIDENCE_LABEL_MIN_W,
    FEATURE_BADGE_MIN_W,
    KPI_CARD_MIN_W,
    DATA_COL_SEPARATOR_W,
    SIDEBAR_TOGGLE_BTN_MIN_W,
    SIDEBAR_MINIMAL_BTN_MIN_W,
    SCROLLBAR_WIDTH,
    SCROLLBAR_RADIUS,
    SCROLLBAR_MIN_LENGTH,
    ACCENT_STRIPE_W,
    CHECKBOX_INDICATOR_SIZE,
    COMBO_DROPDOWN_W,
    UI_DIVIDER_THICKNESS,
    BTN_SECONDARY_BG,
    BTN_SECONDARY_BORDER,
    BTN_SECONDARY_TEXT,
    BTN_SECONDARY_HOVER_BG,
    BTN_SECONDARY_HOVER_BORDER,
    BTN_SECONDARY_HOVER_TEXT,
    WORKFLOW_TAB_MIN_WIDTH,
    SIDEBAR_BRAND_HEIGHT,
    CONN_LAMP_SIZE,
    FONT_SIZE_PROCESS_DASH_KPI,
    FONT_SIZE_PROCESS_DASH_KPI_MEDIUM,
    FONT_SIZE_PROCESS_DASH_STAT,
    FONT_SIZE_DASH_LABEL,
    SIDEBAR_DARK_BG,
    SIDEBAR_DARK_HOVER,
    SIDEBAR_TEXT_PRIMARY,
    SIDEBAR_TEXT_SECONDARY,
    SIDEBAR_ACCENT,
    SIDEBAR_DIVIDER,
    ACCENT_STRIPE_BLUE,
    ACCENT_STRIPE_RED,
    ACCENT_STRIPE_SUCCESS,
    CARD_SHADOW_BOTTOM,
    CARD_SHADOW_BOTTOM_MD,
    CHART_SERIES_SECONDARY,
    CHART_SPEC_LIMITS,
    CHART_GROUP_MONITOR_COLOR,
    CHART_GROUP_MONITOR_BG,
    CHART_GROUP_MONITOR_BORDER,
    CHART_GROUP_CAPABILITY_COLOR,
    CHART_GROUP_CAPABILITY_BG,
    CHART_GROUP_CAPABILITY_BORDER,
    CHART_GROUP_ROOT_CAUSE_COLOR,
    CHART_GROUP_ROOT_CAUSE_BG,
    CHART_GROUP_ROOT_CAUSE_BORDER,
    CHART_GROUP_RELATION_COLOR,
    CHART_GROUP_RELATION_BG,
    CHART_GROUP_RELATION_BORDER,
    CHART_GROUP_COMPARISON_COLOR,
    CHART_GROUP_COMPARISON_BG,
    CHART_GROUP_COMPARISON_BORDER,
    CHART_GROUP_STAT_DATA_COLOR,
    CHART_GROUP_STAT_DATA_BG,
    CHART_GROUP_STAT_DATA_BORDER,
    CHART_SELECTOR_CONTENT_MARGIN,
    CHART_SELECTOR_CHECKBOX_MIN_HEIGHT,
    CHART_CARD_HEADER_BUTTON_HEIGHT,
    CHART_CARD_STATUS_MIN_HEIGHT,
    FEATURE_COLOR_HEIGHT,
    FEATURE_COLOR_AREA,
    FEATURE_COLOR_VOLUME,
    FEATURE_TINT_HEIGHT,
    FEATURE_TINT_AREA,
    FEATURE_TINT_VOLUME,
    FEATURE_BORDER_HEIGHT,
    FEATURE_BORDER_AREA,
    FEATURE_BORDER_VOLUME,
    FEATURE_TOGGLE_MIN_HEIGHT,
    FEATURE_TOGGLE_MIN_WIDTH,
    INFO_SURFACE,
    INFO_SURFACE_SUBTLE,
    SUCCESS_SURFACE_SUBTLE,
    WARNING_SURFACE_SUBTLE,
    ERROR_SURFACE_SUBTLE,
    NEUTRAL_SURFACE,
    PROCESS_ALARM_CARD_BG_NORMAL,
    PROCESS_ALARM_CARD_BG_WARNING,
    PROCESS_ALARM_CARD_BG_CRITICAL,
    ACCENT_ERROR_VIVID,
    ACCENT_WARNING_VIVID,
    SECONDARY_TAB_COMPACT_MIN_WIDTH,
    SECONDARY_TAB_COMPACT_PADDING_H,
    SECONDARY_TAB_COMPACT_PADDING_V,
)


def get_app_stylesheet() -> str:
    """Return the app-wide Slate/Electric Blue stylesheet."""
    stylesheet = f"""
    QMainWindow, QWidget {{
        background-color: {BG_PRIMARY};
        color: {TEXT_PRIMARY};
        font-family: {FONT_FAMILY};
        font-size: {FONT_SIZE_BODY}pt;
        text-align: left;
    }}
    QWidget#centralWidget {{
        background-color: {BG_PRIMARY};
    }}

    /* Buttons — 現代簡約風格：扁平底色 + 細邊框，hover 用 tint 而非漸層 */
    QPushButton {{
        background-color: {BG_BLOCK};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
        border-bottom: 1px solid {BORDER_HOVER};  /* 微立體感底部邊 */
        border-radius: {RADIUS_BUTTON}px;
        padding: {SPACING_XXS}px {SPACING_16}px;
        min-height: {BUTTON_MIN_HEIGHT}px;
        font-family: {FONT_FAMILY};
        font-size: {FONT_SIZE_BODY}pt;
    }}
    QPushButton:hover {{
        background-color: {SURFACE_HOVER_SUBTLE};
        border-color: {BORDER_HOVER};
    }}
    QPushButton:pressed {{
        background-color: {SURFACE_ACTIVE};
        border-color: {BORDER_HOVER};
        padding-top: {SPACING_XXS + 1}px;
        padding-bottom: {max(1, SPACING_XXS - 1)}px;
    }}
    QPushButton:checked {{
        background-color: {ACCENT_PRIMARY};
        border-color: {ACCENT_PRIMARY};
        color: {TEXT_ON_ACCENT};
        font-weight: {FONT_WEIGHT_BOLD};
    }}
    QPushButton:checked:hover {{
        background-color: {ACCENT_PRIMARY_HOVER};
        border-color: {ACCENT_PRIMARY_HOVER};
    }}
    QPushButton:disabled {{
        color: {TEXT_DISABLED};
        background-color: {BG_BLOCK};
        border-color: {BORDER_SUBTLE};
    }}
    QPushButton[class="primary"] {{
        background-color: {ACCENT_PRIMARY};
        border: 1px solid {ACCENT_PRIMARY};
        border-bottom: 1px solid {ACCENT_PRIMARY_HOVER};
        color: {TEXT_ON_ACCENT};
        font-weight: {FONT_WEIGHT_BOLD};
    }}
    QPushButton[class="primary"]:hover {{
        background-color: {ACCENT_PRIMARY_HOVER};
        border-color: {ACCENT_PRIMARY_HOVER};
    }}
    QPushButton[class="primary"]:pressed {{
        background-color: {PRIMARY_700};
        border-color: {PRIMARY_700};
    }}
    /* Refresh: secondary outline — visually subordinate to nextStepBtn (spec I-1 full states) */
    QPushButton#refreshBtn {{
        background-color: {BTN_SECONDARY_BG};
        border: 1px solid {BTN_SECONDARY_BORDER};
        color: {BTN_SECONDARY_TEXT};
        font-weight: {FONT_WEIGHT_BOLD};
    }}
    QPushButton#refreshBtn:hover {{
        background-color: {BTN_SECONDARY_HOVER_BG};
        border-color: {BTN_SECONDARY_HOVER_BORDER};
        color: {BTN_SECONDARY_HOVER_TEXT};
    }}
    QPushButton#refreshBtn:focus {{
        border: 2px solid {FOCUS_RING_BORDER};
    }}
    QPushButton#refreshBtn:pressed {{
        background-color: {SURFACE_ACTIVE};
        border-color: {ACCENT_PRIMARY_HOVER};
    }}
    QPushButton#refreshBtn:disabled {{
        color: {TEXT_DISABLED};
        background-color: {BG_BLOCK};
        border-color: {BORDER_SUBTLE};
    }}
    QPushButton#refreshBtn[state="loading"] {{
        color: {TEXT_MUTED};
        background-color: {BG_BLOCK};
        border-color: {BORDER};
    }}
    QPushButton#nextStepBtn {{
        background-color: {ACCENT_SUCCESS};
        border: 1px solid {ACCENT_SUCCESS};
        border-bottom: 1px solid {ACCENT_SUCCESS_HOVER};
        color: {TEXT_ON_ACCENT};
        font-weight: {FONT_WEIGHT_BOLD};
    }}
    QPushButton#nextStepBtn:hover {{
        background-color: {ACCENT_SUCCESS_HOVER};
        border-color: {ACCENT_SUCCESS_HOVER};
    }}
    QPushButton#nextStepBtn:pressed {{
        background-color: {ACCENT_SUCCESS_HOVER};
        border-color: {ACCENT_SUCCESS_HOVER};
    }}
    QPushButton[class="danger"] {{
        background-color: {ACCENT_ERROR};
        border: 1px solid {ACCENT_ERROR};
        border-bottom: 1px solid {ACCENT_ERROR_HOVER};
        color: {TEXT_ON_ACCENT};
    }}
    QPushButton[class="danger"]:hover {{
        background-color: {ACCENT_ERROR_HOVER};
        border-color: {ACCENT_ERROR_HOVER};
    }}
    QPushButton[class="danger"]:pressed {{
        background-color: {ACCENT_ERROR_HOVER};
        border-color: {ACCENT_ERROR_HOVER};
    }}
    QPushButton[class="secondary"] {{
        background-color: {BG_SECONDARY};
        border: 1px solid {BORDER};
        border-bottom: 1px solid {BORDER_HOVER};
        color: {TEXT_PRIMARY};
    }}
    QPushButton[class="secondary"]:hover {{
        background-color: {SURFACE_HOVER_SUBTLE};
        border-color: {BORDER_HOVER};
    }}
    QPushButton[class="secondary"]:pressed {{
        background-color: {SURFACE_ACTIVE};
    }}
    QPushButton[variant="featureTab"] {{
        font-size: {FONT_SIZE_SECTION}pt;
        font-weight: {FONT_WEIGHT_BOLD};
    }}
    QPushButton[class="tertiary"] {{
        background-color: transparent;
        border-color: {BORDER};
        color: {TEXT_SECONDARY};
    }}
    QPushButton[class="tertiary"]:hover {{
        background-color: {SURFACE_HOVER};
        border-color: {BORDER_HOVER};
        color: {TEXT_PRIMARY};
    }}
    QPushButton[class="tertiary"]:focus {{
        border: 2px solid {FOCUS_RING_BORDER};
    }}
    QPushButton[class="tertiary"]:pressed {{
        background-color: {SURFACE_ACTIVE};
        border-color: {BORDER_HOVER};
    }}
    QPushButton[class="tertiary"]:disabled {{
        background-color: transparent;
        border-color: {BORDER_SUBTLE};
        color: {TEXT_DISABLED};
    }}

    /* ComboBox */
    QComboBox {{
        background-color: {BG_SECONDARY};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
        border-radius: {RADIUS_BUTTON}px;
        /* 高密度：下修垂直 padding，維持可讀字級 */
        padding: {SPACING_XXS}px {SPACING_SM}px;
        min-height: {INPUT_MIN_HEIGHT}px;
        font-family: {FONT_FAMILY};
        font-size: {FONT_SIZE_BODY}pt;
    }}
    QComboBox:hover {{
        border-color: {BORDER_HOVER};
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: center right;
        width: {COMBO_DROPDOWN_W}px;
        border: none;
        background: transparent;
    }}
    /* ::down-arrow — let Qt draw the platform-native chevron.
       CSS border-trick triangles do not render in Qt QSS. */
    QComboBox::down-arrow {{
        width: {COMBO_DROPDOWN_W}px;
        height: {INPUT_MIN_HEIGHT}px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {BG_BLOCK};
        color: {TEXT_PRIMARY};
        selection-background-color: {ACCENT_PRIMARY};
        selection-color: {TEXT_ON_ACCENT};
        border: 1px solid {BORDER};
        border-radius: {RADIUS_SM}px;
        padding: {SPACING_XXS}px;
    }}
    QComboBox QAbstractItemView::item {{
        padding: {SPACING_XXS}px {SPACING_SM}px;
        min-height: {INPUT_MIN_HEIGHT}px;
    }}
    QComboBox QAbstractItemView::item:hover {{
        background-color: {SURFACE_HOVER};
        color: {TEXT_PRIMARY};
    }}

    /* DateEdit + popup calendar */
    QDateEdit {{
        background-color: {BG_BLOCK};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
        border-radius: {RADIUS_BUTTON}px;
        padding: {SPACING_XXS}px {SPACING_SM}px;
        min-height: {INPUT_MIN_HEIGHT}px;
        font-family: {FONT_FAMILY};
        font-size: {FONT_SIZE_BODY}pt;
    }}
    QDateEdit:hover {{
        border-color: {BORDER_HOVER};
    }}
    QDateEdit:disabled {{
        color: {TEXT_DISABLED};
        background-color: {BG_SECONDARY};
        border-color: {BORDER_SUBTLE};
        font-size: {FONT_SIZE_DISABLED}pt;
    }}
    QDateEdit:focus {{
        border: 2px solid {FOCUS_RING_BORDER};
    }}
    QDateEdit::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: center right;
        width: {COMBO_DROPDOWN_W}px;
        border: none;
        background: transparent;
    }}
    QDateEdit::down-arrow {{
        width: {COMBO_DROPDOWN_W}px;
        height: {INPUT_MIN_HEIGHT}px;
    }}
    QCalendarWidget QWidget {{
        alternate-background-color: {BG_SECONDARY};
    }}
    QCalendarWidget QToolButton {{
        color: {TEXT_PRIMARY};
        background: transparent;
        border: 1px solid transparent;
        border-radius: {RADIUS_SM}px;
        min-height: {INPUT_MIN_HEIGHT}px;
        padding: {SPACING_XXS}px {SPACING_XS}px;
    }}
    QCalendarWidget QToolButton:hover {{
        background: {SURFACE_HOVER};
        border-color: {BORDER_HOVER};
    }}
    QCalendarWidget QToolButton:disabled {{
        color: {TEXT_DISABLED};
        background: transparent;
    }}
    QCalendarWidget QAbstractItemView {{
        background-color: {BG_BLOCK};
        color: {TEXT_PRIMARY};
        selection-background-color: {ACCENT_PRIMARY};
        selection-color: {TEXT_ON_ACCENT};
    }}
    QCalendarWidget QAbstractItemView:enabled {{
        color: {TEXT_PRIMARY};
    }}
    QCalendarWidget QAbstractItemView::item {{
        min-height: {INPUT_MIN_HEIGHT}px;
    }}

    /* LineEdit */
    QLineEdit {{
        background-color: {BG_BLOCK};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
        border-radius: {RADIUS_BUTTON}px;
        padding: {SPACING_XXS}px {SPACING_SM}px;
        min-height: {INPUT_MIN_HEIGHT}px;
        font-family: {FONT_FAMILY};
        font-size: {FONT_SIZE_BODY}pt;
    }}
    QLineEdit:hover {{
        border-color: {BORDER_HOVER};
    }}
    QLineEdit:focus {{
        border: 2px solid {FOCUS_RING_BORDER};
        background-color: {BG_BLOCK};
        selection-background-color: {ACCENT_PRIMARY};
        selection-color: {TEXT_ON_ACCENT};
    }}
    QLineEdit:read-only {{
        background-color: {BG_SECONDARY};
        color: {TEXT_MUTED};
        border-color: {BORDER_SUBTLE};
        font-size: {FONT_SIZE_DISABLED}pt;
    }}
    /* Placeholder text: explicit contrast-safe color — Qt6 supports ::placeholder pseudo-element */
    QLineEdit::placeholder {{
        color: {TEXT_MUTED};
        font-size: {FONT_SIZE_PLACEHOLDER}pt;
    }}

    QLineEdit[class="largeInput"] {{
        padding: {SPACING_XXS}px {SPACING_SM}px;
        min-height: {INPUT_MIN_HEIGHT}px;
        font-size: {FONT_SIZE_BODY}pt;
        background-color: {BG_BLOCK};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: {RADIUS_MD}px;
    }}
    QLineEdit[class="largeInput"]:focus {{
        border-color: {ACCENT_PRIMARY};
    }}
    QPushButton:focus {{
        border: 2px solid {FOCUS_RING_BORDER};
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 {BTN_GRAD_LIGHT}, stop:1 {SURFACE_HOVER});
    }}
    QComboBox:focus {{
        border: 2px solid {FOCUS_RING_BORDER};
    }}
    QComboBox:disabled {{
        color: {TEXT_DISABLED};
        background-color: {BG_SECONDARY};
        border-color: {BORDER_SUBTLE};
        font-size: {FONT_SIZE_DISABLED}pt;
    }}
    QLineEdit:disabled {{
        color: {TEXT_DISABLED};
        background-color: {BG_SECONDARY};
        border-color: {BORDER_SUBTLE};
        font-size: {FONT_SIZE_DISABLED}pt;
    }}

    /* TextEdit */
    QTextEdit {{
        background-color: {BG_BLOCK};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
        border-radius: {RADIUS_BUTTON}px;
        padding: {SPACING_SM}px;
        font-family: {FONT_FAMILY_MONO};
        font-size: {FONT_SIZE_MONO}pt;
    }}
    QTextEdit:hover {{
        border-color: {BORDER_HOVER};
    }}
    QTextEdit:focus {{
        border: 2px solid {FOCUS_RING_BORDER};
    }}
    QTextEdit:disabled {{
        color: {TEXT_DISABLED};
        background-color: {BG_SECONDARY};
        border-color: {BORDER_SUBTLE};
    }}

    /* GroupBox — 純白背景，邊框收斂 */
    QGroupBox {{
        background-color: {BG_BLOCK};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: {CARD_RADIUS}px;
        margin-top: {GROUPBOX_TITLE_MARGIN_TOP}px;
        padding: {SPACING_12}px {SPACING_SM}px {SPACING_SM}px;
        font-family: {FONT_FAMILY};
        font-size: {FONT_SIZE_SECTION}pt;
        font-weight: {FONT_WEIGHT_BOLD};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: {SPACING_SM}px;
        padding: {GROUPBOX_TITLE_PADDING_TOP}px {SPACING_XS}px {SPACING_XXS}px;
        color: {TEXT_SECONDARY};
        font-weight: {FONT_WEIGHT_BOLD};
        text-align: left;
    }}

    /* Frame: 預設透明無邊，避免佈局容器（如 vol_frame、area_frame 等）
       意外繼承背景與邊框。視覺樣式由具名/具 class 的 QFrame 規則單獨定義。 */
    QFrame {{
        background-color: transparent;
        color: {TEXT_PRIMARY};
        border: none;
        border-radius: 0;
    }}
    /* VLine (frameShape=5) / HLine (frameShape=4) 分隔線保留 Qt 原生繪製 */
    QFrame[frameShape="4"], QFrame[frameShape="5"] {{
        color: {BORDER_SUBTLE};
    }}
    QFrame[class="divider"] {{
        color: {BORDER_SUBTLE};
        background-color: {BORDER_SUBTLE};
        max-height: {UI_DIVIDER_THICKNESS}px;
    }}
    QFrame#controlCard, QFrame#stepCard {{
        background-color: {BG_BLOCK};
        border: 1px solid {BORDER_SUBTLE};
        border-bottom: 3px solid {CARD_SHADOW_BOTTOM_MD};
        border-radius: {CARD_RADIUS}px;
    }}
    QFrame[class="accentBlue"] {{
        border-left: {ACCENT_STRIPE_W}px solid {ACCENT_STRIPE_BLUE};
        background-color: {BG_BLOCK};
    }}
    QFrame[class="accentRed"] {{
        border-left: {ACCENT_STRIPE_W}px solid {ACCENT_STRIPE_RED};
        background-color: {BG_BLOCK};
    }}
    QFrame[class="accentSuccess"] {{
        border-left: {ACCENT_STRIPE_W}px solid {ACCENT_STRIPE_SUCCESS};
        background-color: {BG_BLOCK};
    }}
    QFrame[class="dropZone"] {{
        background-color: {NEUTRAL_SURFACE};
        border: 1px dashed {BORDER_HOVER};
        border-radius: {RADIUS_MD}px;
    }}
    QFrame[class="dropZone"][state="active"] {{
        background-color: {INFO_SURFACE_SUBTLE};
        border: 1px dashed {ACCENT_PRIMARY};
    }}
    QFrame[class="headerToolbar"] {{
        background-color: {BG_BLOCK};
        border: 1px solid {BORDER_SUBTLE};
        border-bottom: 2px solid {BORDER};
        border-radius: {RADIUS_BUTTON}px;
        min-height: {HEADER_TOOLBAR_MIN_HEIGHT}px;
        padding: {SPACING_SM}px;
    }}
    QFrame[class="headerToolbar"][headerDensity="compact"] {{
        min-height: {COMPACT_HEADER_TOOLBAR_MIN_HEIGHT}px;
        padding: {COMPACT_HEADER_MARGIN_V}px {COMPACT_HEADER_MARGIN_H}px;
        border-bottom: 1px solid {BORDER};
    }}
    QFrame[class="tableToolbar"] {{
        background-color: {BG_BLOCK};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: {RADIUS_BUTTON}px;
        min-height: {TABLE_TOOLBAR_MIN_HEIGHT}px;
        padding: {TABLE_TOOLBAR_MARGIN_V}px {TABLE_TOOLBAR_MARGIN_H}px;
    }}
    QLabel#dataMgmtDetailCard {{
        background-color: {BG_BLOCK};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: {RADIUS_BUTTON}px;
        min-height: {DETAIL_CARD_MIN_HEIGHT}px;
        padding: {SPACING_8}px {SPACING_SM}px;
    }}
    QLabel[class="sectionTitle"] {{
        font-size: {FONT_SIZE_SECTION}pt;
        font-weight: {FONT_WEIGHT_BOLD};
        color: {TEXT_PRIMARY};
        min-height: {SECTION_TITLE_MIN_HEIGHT}px;
        border-left: {ACCENT_STRIPE_W}px solid {ACCENT_PRIMARY};
        padding-left: {SPACING_8}px;
        qproperty-alignment: 'AlignLeft | AlignVCenter';
    }}
    QLabel[class="stepTitle"] {{
        font-size: {FONT_SIZE_SECTION}pt;
        font-weight: {FONT_WEIGHT_BOLD};
        color: {TEXT_PRIMARY};
        min-height: {SECTION_TITLE_MIN_HEIGHT}px;
        padding-bottom: {SPACING_XXS}px;
        border-left: {ACCENT_STRIPE_W}px solid {ACCENT_PRIMARY};
        padding-left: {SPACING_8}px;
    }}
    /* 工單規格卡內的分組子標頭（體積/面積/高度），視覺層次介於 stepTitle 與 caption 之間 */
    QLabel[class="specGroupLabel"] {{
        font-size: {FONT_SIZE_CAPTION}pt;
        font-weight: {FONT_WEIGHT_BOLD};
        color: {TEXT_MUTED};
        padding-top: {SPACING_4}px;
        padding-bottom: 1px;
    }}
    /* KPI summary bar cards */
    QFrame#kpiCard, QFrame[class="kpiCard"] {{
        background-color: {BG_CARD};
        border: 1px solid {BORDER_SUBTLE};
        border-bottom: 2px solid {CARD_SHADOW_BOTTOM_MD};
        border-left: 4px solid {ACCENT_PRIMARY};
        border-radius: {RADIUS_MD}px;
        min-width: {KPI_CARD_MIN_W}px;
    }}
    QLabel[class="kpiValue"] {{
        font-size: {FONT_SIZE_BODY}pt;
        font-weight: {FONT_WEIGHT_BOLD};
        color: {TEXT_PRIMARY};
    }}

    /* --- Process Diagnosis Dashboard Specifics --- */
    QFrame#processDashCard, QFrame#processAlarmCard {{
        background-color: {BG_BLOCK};
        border: 1px solid {BORDER_SUBTLE};
        border-bottom: 3px solid {CARD_SHADOW_BOTTOM_MD};
        border-radius: {CARD_RADIUS}px;
    }}
    QLabel[class="processDashCardTitle"] {{
        font-size: {FONT_SIZE_SECTION}pt;
        font-weight: {FONT_WEIGHT_BOLD};
        color: {TEXT_SECONDARY};
        padding-bottom: {SPACING_4}px;
        border-bottom: 1px solid {BORDER_SUBTLE};
    }}
    QLabel[class="processDashFieldLabel"] {{
        font-size: {FONT_SIZE_CAPTION}pt;
        color: {TEXT_MUTED};
        font-weight: {FONT_WEIGHT_BOLD};
    }}
    QLabel[class="processDashKpiValueLarge"] {{
        font-size: {FONT_SIZE_PROCESS_DASH_KPI}pt;
        font-weight: {FONT_WEIGHT_BOLD};
    }}
    QLabel[class="processDashKpiValueMedium"] {{
        font-size: {FONT_SIZE_PROCESS_DASH_KPI_MEDIUM}pt;
        font-weight: {FONT_WEIGHT_BOLD};
    }}
    QLabel[class="processDashStatSmall"] {{
        font-size: {FONT_SIZE_PROCESS_DASH_STAT}pt;
        font-weight: {FONT_WEIGHT_BOLD};
    }}
    
    /* Value State Coloring */
    QLabel[valueState="good"] {{ color: {ACCENT_SUCCESS}; }}
    QLabel[valueState="warning"] {{ color: {ACCENT_WARNING}; }}
    QLabel[valueState="bad"] {{ color: {ACCENT_ERROR}; }}
    QLabel[valueState="neutral"] {{ color: {TEXT_PRIMARY}; }}

    /* Special Highlight Card for Diagnostic Insight */
    QFrame#processDiagnosisHighlightCard {{
        background-color: {BG_BLOCK};
        border-left: {ACCENT_STRIPE_W}px solid {ACCENT_STRIPE_BLUE};
        border-top: 1px solid {BORDER_SUBTLE};
        border-right: 1px solid {BORDER_SUBTLE};
        border-bottom: 3px solid rgba(0, 0, 0, 0.08); /* Stronger shadow */
    }}

    /* 特徵切換按鈕（高度/面積/體積）：checked 狀態用柔和的 tinted 風格，
       與主要動作按鈕（solid accent）視覺區隔。 */
    QPushButton[class="featureToggle"]:checked {{
        background-color: {PRIMARY_100};
        border: 1px solid {ACCENT_PRIMARY};
        color: {PRIMARY_700};
        font-weight: {FONT_WEIGHT_BOLD};
    }}
    QPushButton[class="featureToggle"]:checked:hover {{
        background-color: {PRIMARY_300};
        border-color: {ACCENT_PRIMARY_HOVER};
        color: {PRIMARY_700};
    }}
    QPushButton[class="featureToggle"][feature="height"]:checked {{
        background-color: {FEATURE_TINT_HEIGHT};
        border-color: {FEATURE_BORDER_HEIGHT};
        color: {FEATURE_BORDER_HEIGHT};
    }}
    QPushButton[class="featureToggle"][feature="area"]:checked {{
        background-color: {FEATURE_TINT_AREA};
        border-color: {FEATURE_BORDER_AREA};
        color: {FEATURE_BORDER_AREA};
    }}
    QPushButton[class="featureToggle"][feature="volume"]:checked {{
        background-color: {FEATURE_TINT_VOLUME};
        border-color: {FEATURE_BORDER_VOLUME};
        color: {FEATURE_BORDER_VOLUME};
    }}
    QPushButton[class="featureToggle"] {{
        background-color: {BG_SECONDARY};
        border: 1px solid {BORDER};
        color: {TEXT_SECONDARY};
    }}
    QPushButton[class="featureToggle"]:hover {{
        background-color: {SURFACE_HOVER};
        border-color: {BORDER_HOVER};
        color: {TEXT_PRIMARY};
    }}
    QPushButton[class="featureToggle"]:focus {{
        border: 2px solid {FOCUS_RING_BORDER};
    }}
    QPushButton[class="featureToggle"]:disabled {{
        color: {TEXT_DISABLED};
        background-color: {BG_SECONDARY};
        border-color: {BORDER_SUBTLE};
    }}

    /* Segmented control wrapper for feature toggle buttons */
    QFrame[class="segmentedControl"] {{
        background-color: {BG_SECONDARY};
        border: 1px solid {BORDER};
        border-radius: {RADIUS_BUTTON}px;
    }}
    QFrame[class="segmentedControl"] QPushButton[class="featureToggle"] {{
        background-color: transparent;
        border: none;
        border-right: 1px solid {BORDER};
        border-radius: 0;
        min-height: {FEATURE_TOGGLE_MIN_HEIGHT}px;
        min-width: {FEATURE_TOGGLE_MIN_WIDTH}px;
        color: {TEXT_SECONDARY};
        font-size: {FONT_SIZE_BODY}pt;
    }}
    QFrame[class="segmentedControl"] QPushButton[class="featureToggle"]:hover {{
        background-color: {SURFACE_HOVER};
        color: {TEXT_PRIMARY};
    }}
    QFrame[class="segmentedControl"] QPushButton[class="featureToggle"]:checked {{
        background-color: {ACCENT_PRIMARY};
        border-right: 1px solid {BORDER};
        color: {TEXT_ON_ACCENT};
        font-weight: {FONT_WEIGHT_BOLD};
    }}
    QFrame[class="segmentedControl"] QPushButton[class="featureToggle"][feature="height"]:checked {{
        background-color: {FEATURE_COLOR_HEIGHT};
        border-right: 1px solid {BORDER};
        color: {TEXT_ON_ACCENT};
    }}
    QFrame[class="segmentedControl"] QPushButton[class="featureToggle"][feature="area"]:checked {{
        background-color: {FEATURE_COLOR_AREA};
        border-right: 1px solid {BORDER};
        color: {TEXT_ON_ACCENT};
    }}
    QFrame[class="segmentedControl"] QPushButton[class="featureToggle"][feature="volume"]:checked {{
        background-color: {FEATURE_COLOR_VOLUME};
        border-right: 1px solid {BORDER};
        color: {TEXT_ON_ACCENT};
    }}
    QFrame[class="segmentedControl"] QPushButton[class="featureToggle"]:checked:hover {{
        background-color: {ACCENT_PRIMARY_HOVER};
    }}
    QFrame[class="segmentedControl"] QPushButton[class="featureToggle"][feature="height"]:checked:hover {{
        background-color: {FEATURE_BORDER_HEIGHT};
    }}
    QFrame[class="segmentedControl"] QPushButton[class="featureToggle"][feature="area"]:checked:hover {{
        background-color: {FEATURE_BORDER_AREA};
    }}
    QFrame[class="segmentedControl"] QPushButton[class="featureToggle"][feature="volume"]:checked:hover {{
        background-color: {FEATURE_BORDER_VOLUME};
    }}
    QFrame[class="segmentedControl"] QPushButton[class="featureToggle"]:disabled {{
        color: {TEXT_DISABLED};
        background-color: transparent;
    }}
    QFrame[class="segmentedControl"] QPushButton[class="featureToggle"][position="first"] {{
        border-top-left-radius: 5px;
        border-bottom-left-radius: 5px;
    }}
    QFrame[class="segmentedControl"] QPushButton[class="featureToggle"][position="last"] {{
        border-top-right-radius: 5px;
        border-bottom-right-radius: 5px;
        border-right: none;
    }}
    QFrame[class="segmentedControl"] QPushButton[class="featureToggle"][position="last"]:checked {{
        border-right: none;
    }}

    /* navPhase: 舊水平三欄佈局已移除，class="navPhase" 與 #navPhaseHeader 均由同一 widget 使用。
       以 #navPhaseHeader（id 選擇器，更高特異性）作為唯一樣式來源；class 規則維持 reset，確保不殘留舊框格。 */
    QLabel[class="navPhase"] {{
        background: transparent;
        border: none;
        padding: 0;
    }}

    /* Accordion group selector */
    QFrame#accordionArea {{
        background-color: {BG_PANEL};
        border: 1px solid {APPLE_GLASS_BORDER};
        border-radius: {RADIUS_BUTTON}px;
    }}
    QFrame#accordionArea[layoutDensity="compact"] {{
        background-color: {BG_BLOCK};
    }}

    QFrame#accordionGroup {{
        background-color: transparent;
        border: none;
        border-right: 1px solid {BORDER_SUBTLE};
        padding-right: {SPACING_4}px;
    }}
    QFrame#accordionGroup[chartGroup="monitor"] {{
        border-right: 2px solid {CHART_GROUP_MONITOR_BORDER};
    }}
    QFrame#accordionGroup[chartGroup="capability"] {{
        border-right: 2px solid {CHART_GROUP_CAPABILITY_BORDER};
    }}
    QFrame#accordionGroup[chartGroup="root-cause"] {{
        border-right: 2px solid {CHART_GROUP_ROOT_CAUSE_BORDER};
    }}
    QFrame#accordionGroup[chartGroup="relation"] {{
        border-right: 2px solid {CHART_GROUP_RELATION_BORDER};
    }}
    QFrame#accordionGroup[chartGroup="comparison"] {{
        border-right: 2px solid {CHART_GROUP_COMPARISON_BORDER};
    }}
    QFrame#accordionGroup[chartGroup="stat-data"] {{
        border-right: 2px solid {CHART_GROUP_STAT_DATA_BORDER};
    }}

    /* ── DataSetupPage 欄位分隔線 ───────────────────────────────── */
    QFrame[class="dataColSeparator"] {{
        color: {BORDER_SUBTLE};
        max-width: {DATA_COL_SEPARATOR_W}px;
        min-width: {DATA_COL_SEPARATOR_W}px;
    }}

    QFrame[class="specSummaryRow"] {{
        background-color: {BG_SECONDARY};
        border: 1px dashed {BORDER_SUBTLE};
        border-radius: {RADIUS_MD}px;
    }}
    QLabel[class="specSummaryText"] {{
        font-size: {FONT_SIZE_BODY}pt;
        color: {TEXT_PRIMARY};
        qproperty-alignment: 'AlignLeft | AlignVCenter';
    }}

    QPushButton[class="accordionHeader"] {{
        background: {BG_SECONDARY};
        color: {TEXT_SECONDARY};
        font-size: {FONT_SIZE_CAPTION}pt;
        font-weight: {FONT_WEIGHT_BOLD};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: {RADIUS_SM}px;
        padding: {SPACING_4}px {SPACING_SM}px;
        text-align: left;
    }}
    QFrame#accordionArea[layoutDensity="compact"] QPushButton[class="accordionHeader"] {{
        padding: {CHART_SELECTOR_CONTENT_MARGIN}px {SPACING_8}px;
    }}
    QFrame#accordionArea[layoutDensity="compact"] QCheckBox {{
        min-height: {CHART_SELECTOR_CHECKBOX_MIN_HEIGHT}px;
    }}

    QPushButton[class="accordionHeader"]:hover {{
        background: {SURFACE_HOVER};
        color: {TEXT_PRIMARY};
        border-color: {BORDER_HOVER};
    }}

    QPushButton[class="accordionHeader"]:checked {{
        background: {PRIMARY_100};
        color: {PRIMARY_700};
        border: 1px solid {ACCENT_PRIMARY};
        border-left: 3px solid {ACCENT_PRIMARY};
    }}
    QPushButton[class="accordionHeader"][chartGroup="monitor"]:checked {{
        background: {CHART_GROUP_MONITOR_BG};
        color: {CHART_GROUP_MONITOR_COLOR};
        border-color: {CHART_GROUP_MONITOR_BORDER};
        border-left: 3px solid {CHART_GROUP_MONITOR_COLOR};
    }}
    QPushButton[class="accordionHeader"][chartGroup="capability"]:checked {{
        background: {CHART_GROUP_CAPABILITY_BG};
        color: {CHART_GROUP_CAPABILITY_COLOR};
        border-color: {CHART_GROUP_CAPABILITY_BORDER};
        border-left: 3px solid {CHART_GROUP_CAPABILITY_COLOR};
    }}
    QPushButton[class="accordionHeader"][chartGroup="root-cause"]:checked {{
        background: {CHART_GROUP_ROOT_CAUSE_BG};
        color: {CHART_GROUP_ROOT_CAUSE_COLOR};
        border-color: {CHART_GROUP_ROOT_CAUSE_BORDER};
        border-left: 3px solid {CHART_GROUP_ROOT_CAUSE_COLOR};
    }}
    QPushButton[class="accordionHeader"][chartGroup="relation"]:checked {{
        background: {CHART_GROUP_RELATION_BG};
        color: {CHART_GROUP_RELATION_COLOR};
        border-color: {CHART_GROUP_RELATION_BORDER};
        border-left: 3px solid {CHART_GROUP_RELATION_COLOR};
    }}
    QPushButton[class="accordionHeader"][chartGroup="comparison"]:checked {{
        background: {CHART_GROUP_COMPARISON_BG};
        color: {CHART_GROUP_COMPARISON_COLOR};
        border-color: {CHART_GROUP_COMPARISON_BORDER};
        border-left: 3px solid {CHART_GROUP_COMPARISON_COLOR};
    }}
    QPushButton[class="accordionHeader"][chartGroup="stat-data"]:checked {{
        background: {CHART_GROUP_STAT_DATA_BG};
        color: {CHART_GROUP_STAT_DATA_COLOR};
        border-color: {CHART_GROUP_STAT_DATA_BORDER};
        border-left: 3px solid {CHART_GROUP_STAT_DATA_COLOR};
    }}
    QPushButton[class="accordionHeader"]:focus {{
        border: 2px solid {FOCUS_RING_BORDER};
    }}
    QPushButton[class="accordionHeader"]:disabled {{
        color: {TEXT_DISABLED};
        background-color: {BG_SECONDARY};
        border-color: {BORDER_SUBTLE};
    }}

    /* Action Buttons (Generic classes used in DiagnosticPage) */
    QPushButton[class="secondary"] {{
        background-color: {BG_BLOCK};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
        border-radius: {RADIUS_MD}px;
        padding: {SPACING_XXS}px {SPACING_SM}px;
        min-height: {INPUT_MIN_HEIGHT}px;
        font-family: {FONT_FAMILY};
        font-size: {FONT_SIZE_SMALL}pt;
        font-weight: {FONT_WEIGHT_BOLD};
    }}
    QPushButton[class="secondary"]:hover {{
        background-color: {SURFACE_HOVER};
        border-color: {BORDER_HOVER};
    }}
    QPushButton[class="secondary"]:pressed {{
        background-color: {SURFACE_ACTIVE};
    }}

    QPushButton[class="tertiary"] {{
        background-color: transparent;
        color: {ACCENT_PRIMARY};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: {RADIUS_SM}px;
        padding: 2px {SPACING_8}px;
        font-family: {FONT_FAMILY};
        font-size: {FONT_SIZE_SMALL}pt;
        font-weight: {FONT_WEIGHT_BOLD};
    }}
    QPushButton[class="tertiary"]:hover {{
        background-color: {SURFACE_HOVER_SUBTLE};
        border-color: {ACCENT_PRIMARY};
    }}
    QPushButton[class="tertiary"]:pressed {{
        background-color: {SURFACE_ACTIVE};
    }}

    /* Dashboard chart cards (one per chart in the scroll area) */
    QFrame#chartDashboardCard {{
        background-color: {BG_PANEL};
        border: 1px solid {BORDER_SUBTLE};
        border-bottom: 3px solid {CARD_SHADOW_BOTTOM_MD};
        border-radius: {CARD_RADIUS}px;
        margin-bottom: {SPACING_4}px;
    }}
    QPushButton[variant="chartCardAction"] {{
        min-height: {CHART_CARD_HEADER_BUTTON_HEIGHT}px;
        padding: {SPACING_XXS}px {SPACING_8}px;
        font-size: {FONT_SIZE_CAPTION}pt;
    }}
    QLabel[class="chartCardStatus"] {{
        min-height: {CHART_CARD_STATUS_MIN_HEIGHT}px;
        padding: 0px {SPACING_XS}px;
        font-size: {FONT_SIZE_SMALL}pt;
        font-weight: {FONT_WEIGHT_BOLD};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: {RADIUS_SM}px;
        color: {TEXT_SECONDARY};
        background-color: {BG_SECONDARY};
    }}
    QLabel[class="chartCardStatus"][state="ready"] {{
        color: {ACCENT_SUCCESS};
        border-color: {ACCENT_SUCCESS};
        background-color: {SUCCESS_SURFACE_SUBTLE};
    }}
    QLabel[class="chartCardStatus"][state="incompatible"] {{
        color: {TEXT_STATE_INCOMPATIBLE};
        border-color: {BORDER_INCOMPATIBLE};
        background-color: {BG_STATE_INCOMPATIBLE};
    }}
    QLabel[class="chartCardStatus"][state="nodata"] {{
        color: {TEXT_MUTED};
        border-color: {BORDER_SUBTLE};
        background-color: {BG_SECONDARY};
    }}
    QLabel[class="chartCardStatus"][state="error"] {{
        color: {ACCENT_ERROR};
        border-color: {ACCENT_ERROR};
        background-color: {ERROR_SURFACE_SUBTLE};
    }}
    QFrame#chartDashboardCard[chartGroup="monitor"],
    QFrame#controlCard[chartGroup="monitor"] {{
        border-left: {ACCENT_STRIPE_W}px solid {CHART_GROUP_MONITOR_COLOR};
    }}
    QFrame#chartDashboardCard[chartGroup="capability"],
    QFrame#controlCard[chartGroup="capability"] {{
        border-left: {ACCENT_STRIPE_W}px solid {CHART_GROUP_CAPABILITY_COLOR};
    }}
    QFrame#chartDashboardCard[chartGroup="root-cause"],
    QFrame#controlCard[chartGroup="root-cause"] {{
        border-left: {ACCENT_STRIPE_W}px solid {CHART_GROUP_ROOT_CAUSE_COLOR};
    }}
    QFrame#chartDashboardCard[chartGroup="relation"],
    QFrame#controlCard[chartGroup="relation"] {{
        border-left: {ACCENT_STRIPE_W}px solid {CHART_GROUP_RELATION_COLOR};
    }}
    QFrame#chartDashboardCard[chartGroup="comparison"],
    QFrame#controlCard[chartGroup="comparison"] {{
        border-left: {ACCENT_STRIPE_W}px solid {CHART_GROUP_COMPARISON_COLOR};
    }}
    QFrame#chartDashboardCard[chartGroup="stat-data"],
    QFrame#controlCard[chartGroup="stat-data"] {{
        border-left: {ACCENT_STRIPE_W}px solid {CHART_GROUP_STAT_DATA_COLOR};
    }}

    /* Progress Bar */
    QProgressBar#statusBarProgress {{
        background-color: {BG_SECONDARY};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 3px;
        text-align: center;
    }}
    QProgressBar#statusBarProgress::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {PRIMARY_300}, stop:1 {ACCENT_PRIMARY});
        border-radius: 2px;
    }}

    /* Form layout labels (QLabel inside QFormLayout) */
    QFormLayout QLabel {{
        color: {TEXT_SECONDARY};
        font-size: {FONT_SIZE_BODY}pt;
        font-family: {FONT_FAMILY};
        font-weight: {FONT_WEIGHT_NORMAL};
        min-height: {CONTROL_STATUS_LINE_MIN_HEIGHT}px;
    }}

    /* Tables — single canonical block (duplicates removed) */
    QLabel#featureBadge {{
        border-radius: {RADIUS_SM}px;
        font-size: {FONT_SIZE_CAPTION}pt;
        font-weight: {FONT_WEIGHT_BOLD};
        padding: 1px {SPACING_XS}px;
        min-width: {FEATURE_BADGE_MIN_W}px;
    }}
    QLabel#featureBadge[level="single"] {{
        background: {ACCENT_PRIMARY};
        color: {TEXT_ON_ACCENT};
    }}
    QLabel#featureBadge[level="dual"] {{
        background: {ACCENT_SUCCESS};
        color: {TEXT_ON_ACCENT};
    }}
    QLabel#featureBadge[level="triple"] {{
        background: {ACCENT_WARNING};
        color: {TEXT_ON_ACCENT};
    }}
    QLabel#featureBadge[level="unknown"] {{
        background: {TEXT_MUTED};
        color: {TEXT_ON_ACCENT};
    }}

    /* TabWidget — 底線指示器風格（Linear/Notion style） */
    QTabWidget::pane {{
        background-color: {BG_PRIMARY};
        border: none;
        border-top: 1px solid {BORDER_SUBTLE};
    }}
    QTabBar::tab {{
        background: transparent;
        color: {TEXT_MUTED};
        padding: {SPACING_XS}px {SPACING_16}px;
        margin-right: {SPACING_4}px;
        border: none;
        border-bottom: 2px solid transparent;
        font-family: {FONT_FAMILY};
        font-size: {FONT_SIZE_CAPTION}pt;
    }}
    QTabBar::tab:selected {{
        background: transparent;
        color: {ACCENT_PRIMARY};
        font-weight: {FONT_WEIGHT_BOLD};
        border-bottom: 2px solid {ACCENT_PRIMARY};
    }}
    QTabBar::tab:hover:!selected {{
        background: {SURFACE_HOVER_SUBTLE};
        color: {TEXT_SECONDARY};
        border-radius: {RADIUS_SM}px;
    }}
    QTabBar::tab:disabled {{
        color: {TEXT_DISABLED};
        border-bottom: 2px solid transparent;
    }}
    QTabWidget[class~="secondaryTabs"] QTabBar::tab {{
        background: transparent;
        color: {TEXT_MUTED};
        border: none;
        border-bottom: 2px solid transparent;
        padding: {SECONDARY_TAB_COMPACT_PADDING_V}px {SECONDARY_TAB_COMPACT_PADDING_H}px;
        font-size: {FONT_SIZE_BODY}pt;
        min-width: {SECONDARY_TAB_COMPACT_MIN_WIDTH}px;
    }}
    QTabWidget[class~="secondaryTabs"] QTabBar::tab:selected {{
        background: transparent;
        color: {ACCENT_PRIMARY};
        font-weight: {FONT_WEIGHT_BOLD};
        border-bottom: 2px solid {ACCENT_PRIMARY};
    }}
    QTabWidget[class~="secondaryTabs"] QTabBar::tab:hover:!selected {{
        background: {SURFACE_HOVER_SUBTLE};
        color: {TEXT_SECONDARY};
        border-radius: {RADIUS_SM}px;
    }}
    QTabWidget[class~="secondaryTabs"] QTabBar::tab:disabled {{
        color: {TEXT_DISABLED};
        border-bottom: 2px solid transparent;
    }}
    QTabWidget#workflowTabs::pane {{
        border: 1px solid {BORDER};
        background-color: {BG_BLOCK};
        top: -1px;
        border-radius: {CARD_RADIUS}px;
    }}
    QTabWidget#workflowTabs QTabBar::tab {{
        background: {BG_PRIMARY};
        color: {TEXT_SECONDARY};
        border: 1px solid {BORDER};
        border-bottom: 1px solid {BORDER};
        border-top-left-radius: {RADIUS_BUTTON}px;
        border-top-right-radius: {RADIUS_BUTTON}px;
        padding: {SPACING_8}px {SPACING_20}px;
        min-width: {WORKFLOW_TAB_MIN_WIDTH}px;
        font-size: {FONT_SIZE_BODY}pt;
        font-weight: {FONT_WEIGHT_BOLD};
    }}
    QTabWidget#workflowTabs QTabBar::tab:selected {{
        background: {BG_BLOCK};
        color: {ACCENT_PRIMARY};
        border-bottom-color: {BG_BLOCK};
        border-top: 2px solid {ACCENT_PRIMARY};
    }}
    QTabWidget#workflowTabs QTabBar::tab:hover:!selected {{
        background: {BG_SECONDARY};
        color: {TEXT_PRIMARY};
        border-color: {BORDER_HOVER};
    }}
    QTabWidget#workflowTabs QTabBar::tab:disabled {{
        color: {TEXT_DISABLED};
        background: {BG_PRIMARY};
    }}

    /* ListWidget */
    QListWidget {{
        background-color: {BG_BLOCK};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
        border-radius: {RADIUS_SM}px;
        padding: {SPACING_XS}px;
    }}
    QListWidget::item {{
        /* 高密度：縮小垂直 padding，保留左右縮排 */
        padding: {SPACING_XXS}px {SPACING_16}px;
        border-left: {SPACING_4}px solid transparent;
    }}
    QListWidget::item:hover {{
        background-color: {SURFACE_HOVER_SUBTLE};
    }}
    QListWidget::item:selected {{
        background-color: {SURFACE_ACTIVE};
        border-left: {SPACING_4}px solid {ACCENT_PRIMARY};
        font-weight: {FONT_WEIGHT_BOLD};
    }}
    QListWidget::item:selected:hover {{
        background-color: {SURFACE_HOVER};
    }}
    QListWidget::item:disabled {{
        background-color: {BG_STATE_INCOMPATIBLE};
        color: {TEXT_STATE_INCOMPATIBLE};
        border-left: {SPACING_4}px solid {BORDER_INCOMPATIBLE};
    }}
    QListWidget:focus {{
        border-color: {FOCUS_RING_BORDER};
    }}
    QLabel[class="sidebarDbTitle"] {{
        font-size: {SIDEBAR_DB_TITLE_FONT_SIZE}pt;
        font-weight: {FONT_WEIGHT_BOLD};
        color: {TEXT_PRIMARY};
        background-color: transparent;
    }}
    QLabel[class="sidebarDbCount"] {{
        font-size: {SIDEBAR_DB_COUNT_FONT_SIZE}pt;
        font-weight: {FONT_WEIGHT_NORMAL};
        color: {TEXT_MUTED};
        background-color: transparent;
    }}
    QListWidget[density="sidebarDb"] {{
        font-size: {SIDEBAR_DB_BODY_FONT_SIZE}pt;
        padding: {SPACING_XXS}px;
    }}
    QPushButton[density="sidebarDb"] {{
        font-size: {SIDEBAR_DB_BODY_FONT_SIZE}pt;
        min-height: {SIDEBAR_DB_BUTTON_HEIGHT}px;
        padding: 0px {SPACING_4}px;
    }}

    /* Sidebar brand header (professional anchor at top) */
    QWidget#sidebarBrand {{
        min-height: {SIDEBAR_BRAND_HEIGHT}px;
        padding: {SPACING_4}px {SPACING_SM}px;
        border-bottom: 1px solid {BORDER_SUBTLE};
        background: transparent;
    }}
    QLabel#sidebarBrandTitle {{
        font-size: {SIDEBAR_BRAND_FONT_SIZE}pt;
        font-weight: {FONT_WEIGHT_BOLD};
        color: {TEXT_SECONDARY};
        background-color: transparent;
    }}
    QLabel#sidebarBrandVersion {{
        font-size: {SIDEBAR_BRAND_VERSION_FONT_SIZE}pt;
        font-weight: {FONT_WEIGHT_NORMAL};
        color: {TEXT_MUTED};
        background-color: transparent;
    }}
    /* Sidebar divider between nav and control panel */
    QFrame#sidebarDivider {{
        color: {BORDER_SUBTLE};
        background-color: {BORDER_SUBTLE};
        border: none;
        max-height: 1px;
    }}

    /* Navigation panel (left sidebar): Industrial Dark Theme */
    QWidget#navigationPanel, QWidget#sidebarContent {{
        background-color: {SIDEBAR_DARK_BG};
        border-right: 1px solid {SIDEBAR_DIVIDER};
    }}
    
    QWidget#sidebarBrand {{
        padding: {SPACING_4}px {SPACING_8}px;
        border-bottom: 1px solid {SIDEBAR_DIVIDER};
        background-color: transparent;
    }}
    QLabel#sidebarBrandTitle {{
        font-size: {SIDEBAR_BRAND_FONT_SIZE}pt;
        color: {SIDEBAR_TEXT_PRIMARY};
        font-weight: {FONT_WEIGHT_BOLD};
    }}
    QLabel#sidebarBrandVersion {{
        font-size: {SIDEBAR_BRAND_VERSION_FONT_SIZE}pt;
        color: {SIDEBAR_TEXT_SECONDARY};
        font-weight: {FONT_WEIGHT_NORMAL};
    }}
    QWidget#sidebarContent QLabel[class="sectionTitle"] {{
        font-size: {SIDEBAR_SECTION_TITLE_FONT_SIZE}pt;
        color: {SIDEBAR_TEXT_PRIMARY};
        font-weight: {FONT_WEIGHT_BOLD};
    }}

    QLabel#navPhaseHeader {{
        font-size: {SIDEBAR_PHASE_FONT_SIZE}pt;
        font-weight: {FONT_WEIGHT_BOLD};
        color: {SIDEBAR_TEXT_PRIMARY};
        padding: {SPACING_8}px {SPACING_12}px {SPACING_4}px;
        margin-top: {SPACING_8}px;
    }}

    QPushButton#navStepBtn {{
        background-color: transparent;
        color: {SIDEBAR_TEXT_SECONDARY};
        border: none;
        border-left: 3px solid transparent;
        border-radius: 0px;
        padding: {SPACING_XXS}px {SPACING_12}px;
        text-align: left;
        font-size: {SIDEBAR_NAV_FONT_SIZE}pt;
        font-weight: {FONT_WEIGHT_NORMAL};
        min-height: {NAV_STEP_BTN_HEIGHT}px;
    }}

    QPushButton#navStepBtn:hover {{
        background-color: {SIDEBAR_DARK_HOVER};
        color: {SIDEBAR_TEXT_PRIMARY};
        border-left: 3px solid transparent;
    }}

    QPushButton#navStepBtn[state="selected"] {{
        background-color: rgba(10, 132, 255, 0.12);
        color: {SIDEBAR_ACCENT};
        font-weight: {FONT_WEIGHT_BOLD};
        border-left: 3px solid {SIDEBAR_ACCENT};
    }}

    /* 稽核修正 A-02：鎖定步驟樣式（前置條件未完成時） */
    QPushButton#navStepBtn[state="locked"] {{
        color: {TEXT_DISABLED};
        background-color: transparent;
        border-left: {ACCENT_STRIPE_W}px solid transparent;
    }}
    QPushButton#navStepBtn[state="locked"]:hover {{
        background-color: transparent;
        color: {TEXT_DISABLED};
        cursor: default;
    }}

    QFrame#sidebarDivider {{
        background-color: {SIDEBAR_DIVIDER};
        border: none;
        margin: {SPACING_4}px {SPACING_12}px;
    }}

    QFrame#navPhaseDivider {{
        background-color: {SIDEBAR_DIVIDER};
        border: none;
        max-height: 1px;
        min-height: 1px;
        margin: 0 {SPACING_12}px;
    }}

    QWidget#sidebarRail {{
        background-color: {SIDEBAR_DARK_BG};
        border-right: 1px solid {SIDEBAR_DIVIDER};
    }}

    QPushButton#sidebarToggleBtn, QPushButton#sidebarMinimalNextBtn, QPushButton#sidebarMinimalRefreshBtn {{
        background-color: transparent;
        color: {SIDEBAR_TEXT_SECONDARY};
        border: 1px solid {SIDEBAR_DIVIDER};
        border-radius: {RADIUS_SM}px;
    }}

    QPushButton#sidebarToggleBtn:hover, QPushButton#sidebarMinimalNextBtn:hover, QPushButton#sidebarMinimalRefreshBtn:hover {{
        background-color: {SIDEBAR_DARK_HOVER};
        color: {SIDEBAR_TEXT_PRIMARY};
    }}


    /* Collapsible sidebar rail and toggle */
    QWidget#sidebarRail {{
        background-color: {APPLE_GLASS_TINT};
        border-left: 1px solid {BORDER};
    }}
    QPushButton#sidebarToggleBtn {{
        padding: {SPACING_XS}px;
        min-width: {SIDEBAR_TOGGLE_BTN_MIN_W}px;
        font-size: {SIDEBAR_LABEL_FONT_SIZE}pt;
    }}
    QPushButton#sidebarToggleBtn:hover {{
        background-color: {SURFACE_HOVER};
        color: {ACCENT_PRIMARY};
    }}
    QPushButton#sidebarToggleBtn:pressed {{
        background-color: {SURFACE_ACTIVE};
    }}
    QPushButton#sidebarMinimalNextBtn,
    QPushButton#sidebarMinimalRefreshBtn {{
        padding: {SPACING_XS}px;
        min-width: {SIDEBAR_MINIMAL_BTN_MIN_W}px;
        min-height: {SIDEBAR_MINIMAL_BTN_MIN_HEIGHT}px;
        font-size: {SIDEBAR_LABEL_FONT_SIZE}pt;
    }}
    QPushButton#sidebarMinimalNextBtn:hover,
    QPushButton#sidebarMinimalRefreshBtn:hover {{
        background-color: {SURFACE_HOVER};
        color: {ACCENT_PRIMARY};
    }}
    QPushButton#sidebarMinimalNextBtn:pressed,
    QPushButton#sidebarMinimalRefreshBtn:pressed {{
        background-color: {SURFACE_ACTIVE};
    }}

    /* ScrollArea */
    QScrollArea {{
        background-color: {BG_PRIMARY};
        border: none;
    }}
    QScrollBar:vertical {{
        background-color: {BG_SECONDARY};
        width: {SCROLLBAR_WIDTH}px;
        border-radius: {SCROLLBAR_RADIUS}px;
        margin: 2px 1px 2px 1px;
    }}
    QScrollBar::handle:vertical {{
        background-color: {SCROLLBAR_HANDLE};
        border-radius: {SCROLLBAR_RADIUS}px;
        min-height: {SCROLLBAR_MIN_LENGTH}px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {SCROLLBAR_HANDLE_HOVER};
    }}
    QScrollBar::handle:horizontal:hover {{
        background-color: {SCROLLBAR_HANDLE_HOVER};
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        height: 0px;
        width: 0px;
    }}
    QScrollBar::add-page, QScrollBar::sub-page {{
        background: transparent;
    }}

    /* TableView / TableWidget (Audit 114, 120, 109) */
    QTableView, QTableWidget {{
        background-color: {BG_BLOCK};
        gridline-color: {BORDER_SUBTLE};
        border: 1px solid {BORDER};
        border-radius: {RADIUS_SM}px;
        selection-background-color: {SURFACE_HOVER};
        selection-color: {TEXT_PRIMARY};
    }}
    QTableView::item {{
        padding: {SPACING_4}px {SPACING_8}px;
        border-left: {ACCENT_STRIPE_W}px solid transparent; /* Prevent jitter (Audit 109) */
        min-height: {TABLE_ROW_MIN_HEIGHT}px;
    }}
    QTableView::item:hover {{
        background-color: {SURFACE_HOVER_SUBTLE}; /* Subtle hover feedback (Audit 114) */
    }}
    QTableView::item:selected {{
        background-color: {SURFACE_ACTIVE};
        color: {TEXT_PRIMARY};
        border-left: {ACCENT_STRIPE_W}px solid {ACCENT_PRIMARY};
    }}
    
    QHeaderView::section {{
        background-color: {TABLE_HEADER_BG};
        color: {TEXT_SECONDARY};
        padding: {SPACING_XXS}px {SPACING_SM}px;
        border: none;
        border-right: 1px solid {BORDER_SUBTLE};
        border-bottom: 2px solid {BORDER};
        font-weight: {FONT_WEIGHT_BOLD};
        font-family: {FONT_FAMILY};
    }}
    /* Header sorting arrows (Audit 120) */
    QHeaderView::up-arrow {{
        image: none;
        border-left: {SPACING_4}px solid transparent;
        border-right: {SPACING_4}px solid transparent;
        border-bottom: {SPACING_4}px solid {TEXT_SECONDARY};
        margin-right: {SPACING_4}px;
    }}
    QHeaderView::down-arrow {{
        image: none;
        border-left: {SPACING_4}px solid transparent;
        border-right: {SPACING_4}px solid transparent;
        border-top: {SPACING_4}px solid {TEXT_SECONDARY};
        margin-right: {SPACING_4}px;
    }}

    /* CheckBox (Audit 121) */
    QCheckBox {{
        spacing: {SPACING_XS}px;
        color: {TEXT_PRIMARY};
    }}
    QCheckBox::indicator {{
        width: {CHECKBOX_INDICATOR_SIZE}px;
        height: {CHECKBOX_INDICATOR_SIZE}px;
        border: 1px solid {BORDER};
        border-radius: {RADIUS_SM}px;
        background-color: {BG_PRIMARY};
    }}
    QCheckBox::indicator:hover {{
        border-color: {ACCENT_PRIMARY};
    }}
    QCheckBox::indicator:checked {{
        background-color: {ACCENT_PRIMARY};
        border-color: {ACCENT_PRIMARY};
        image: url(app/ui/assets/check_white.png); /* Assume exists or fallback to CSS drawing if needed */
    }}
    QCheckBox[chartGroup="monitor"]::indicator:checked {{
        background-color: {CHART_GROUP_MONITOR_COLOR};
        border-color: {CHART_GROUP_MONITOR_COLOR};
    }}
    QCheckBox[chartGroup="capability"]::indicator:checked {{
        background-color: {CHART_GROUP_CAPABILITY_COLOR};
        border-color: {CHART_GROUP_CAPABILITY_COLOR};
    }}
    QCheckBox[chartGroup="root-cause"]::indicator:checked {{
        background-color: {CHART_GROUP_ROOT_CAUSE_COLOR};
        border-color: {CHART_GROUP_ROOT_CAUSE_COLOR};
    }}
    QCheckBox[chartGroup="relation"]::indicator:checked {{
        background-color: {CHART_GROUP_RELATION_COLOR};
        border-color: {CHART_GROUP_RELATION_COLOR};
    }}
    QCheckBox[chartGroup="comparison"]::indicator:checked {{
        background-color: {CHART_GROUP_COMPARISON_COLOR};
        border-color: {CHART_GROUP_COMPARISON_COLOR};
    }}
    QCheckBox[chartGroup="stat-data"]::indicator:checked {{
        background-color: {CHART_GROUP_STAT_DATA_COLOR};
        border-color: {CHART_GROUP_STAT_DATA_COLOR};
    }}
    QCheckBox::indicator:focus {{
        border: 2px solid {FOCUS_RING_BORDER};
    }}
    /* Indeterminate state (Audit 121) */
    QCheckBox::indicator:indeterminate {{
        background-color: {BG_PRIMARY};
        border-color: {ACCENT_PRIMARY};
        image: none;
        background-image: none;
        background-clip: padding;
        background-origin: content;
        padding: {SPACING_4}px;
        background-color: {ACCENT_PRIMARY};
    }}
    QScrollBar:horizontal {{
        background-color: {BG_SECONDARY};
        height: {SCROLLBAR_WIDTH}px;
        border-radius: {SCROLLBAR_RADIUS}px;
        margin: 1px 2px 1px 2px;
    }}
    QScrollBar::handle:horizontal {{
        background-color: {SCROLLBAR_HANDLE};
        border-radius: {SCROLLBAR_RADIUS}px;
        min-width: {SCROLLBAR_MIN_LENGTH}px;
    }}

    /* Splitter — 3px handle for easier grab, accent on hover */
    QSplitter::handle {{
        background-color: {BORDER_SUBTLE};
        width: {SPACING_4}px;
        height: {SPACING_4}px;
    }}
    QSplitter::handle:hover {{
        background-color: {ACCENT_PRIMARY};
    }}
    QSplitter::handle:pressed {{
        background-color: {ACCENT_PRIMARY_HOVER};
    }}

    /* Status bar */
    QStatusBar {{
        background-color: {BG_SECONDARY};
        color: {TEXT_SECONDARY};
        border-top: 1px solid {BORDER};
    }}

    /* Labels - page title */
    QLabel[class="pageTitle"] {{
        font-size: {FONT_SIZE_TITLE}pt;
        font-weight: {FONT_WEIGHT_BOLD};
        font-family: {FONT_FAMILY};
        color: {TEXT_PRIMARY};
        min-height: {SECTION_TITLE_MIN_HEIGHT}px;
    }}
    /* Form labels (global) — 表單標籤，黑色文字確保可見 */
    QLabel[class="formLabel"] {{
        font-size: {FONT_SIZE_BODY}pt;
        font-weight: {FONT_WEIGHT_NORMAL};
        font-family: {FONT_FAMILY};
        color: {TEXT_PRIMARY};
        min-height: {LABEL_ROW_MIN_HEIGHT}px;
        padding: {SPACING_XXS}px 0;
    }}
    QLabel[class="caption"] {{
        font-size: {FONT_SIZE_CAPTION}pt;
        color: {TEXT_PRIMARY};
        min-height: {LABEL_ROW_MIN_HEIGHT}px;
        font-family: {FONT_FAMILY};
        font-weight: {FONT_WEIGHT_NORMAL};
    }}
    QLabel[class="reportPreview"] {{
        color: {TEXT_SECONDARY};
        background-color: transparent;
        font-size: {FONT_SIZE_BODY}pt;
        padding-bottom: {SPACING_12}px;
    }}
    QLabel[class="interpretationIllustration"] {{
        background-color: {BG_SECONDARY};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: {RADIUS_MD}px;
        margin: {SPACING_8}px 0;
    }}
    /* 頁面 toolbar 內的狀態文字（lamp 右側），比 caption 稍粗以配合狀態燈視覺重量 */
    QLabel[class="statusIndicator"] {{
        font-size: {FONT_SIZE_CAPTION}pt;
        color: {TEXT_SECONDARY};
        font-weight: {FONT_WEIGHT_BOLD};
        font-family: {FONT_FAMILY};
        min-height: {LABEL_ROW_MIN_HEIGHT}px;
    }}
    QLabel[class="statusIndicator"][interactionState="changed"] {{
        color: {PRIMARY_700};
        background-color: {INFO_SURFACE};
    }}
    QLabel[class="statusIndicator"][state="ready"],
    QLabel[class="statusIndicator"][state="success"],
    QLabel[class="statusIndicator"][state="ok"] {{
        color: {ACCENT_SUCCESS};
        background-color: {SUCCESS_SURFACE_SUBTLE};
        border: 1px solid {ACCENT_SUCCESS};
        border-radius: {RADIUS_SM}px;
        padding: {SPACING_XXS}px {SPACING_XS}px;
    }}
    QLabel[class="statusIndicator"][state="info"],
    QLabel[class="statusIndicator"][state="loading"] {{
        color: {ACCENT_PRIMARY};
        background-color: {INFO_SURFACE_SUBTLE};
        border: 1px solid {ACCENT_PRIMARY};
        border-radius: {RADIUS_SM}px;
        padding: {SPACING_XXS}px {SPACING_XS}px;
    }}
    QLabel[class="statusIndicator"][state="warning"] {{
        color: {ACCENT_WARNING};
        background-color: {WARNING_SURFACE_SUBTLE};
        border: 1px solid {ACCENT_WARNING};
        border-radius: {RADIUS_SM}px;
        padding: {SPACING_XXS}px {SPACING_XS}px;
    }}
    QLabel[class="statusIndicator"][state="incompatible"] {{
        color: {TEXT_STATE_INCOMPATIBLE};
        background-color: {BG_STATE_INCOMPATIBLE};
        border: 1px solid {BORDER_INCOMPATIBLE};
        border-radius: {RADIUS_SM}px;
        padding: {SPACING_XXS}px {SPACING_XS}px;
    }}
    QLabel[class="statusIndicator"][state="nodata"] {{
        color: {TEXT_MUTED};
        background-color: {NEUTRAL_SURFACE};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: {RADIUS_SM}px;
        padding: {SPACING_XXS}px {SPACING_XS}px;
    }}
    QLabel[class="statusIndicator"][state="error"] {{
        color: {ACCENT_ERROR};
        background-color: {ERROR_SURFACE_SUBTLE};
        border: 1px solid {ACCENT_ERROR};
        border-radius: {RADIUS_SM}px;
        padding: {SPACING_XXS}px {SPACING_XS}px;
    }}
    QLabel[class="statusIndicator"][state="disabled"] {{
        color: {TEXT_MUTED};
        background-color: {NEUTRAL_SURFACE};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: {RADIUS_SM}px;
        padding: {SPACING_XXS}px {SPACING_XS}px;
    }}
    QLabel[class="status-ok"] {{
        color: {ACCENT_SUCCESS};
        font-size: {FONT_SIZE_SMALL}pt;
        font-family: {FONT_FAMILY};
        font-weight: {FONT_WEIGHT_NORMAL};
        min-height: {CONTROL_STATUS_LINE_MIN_HEIGHT}px;
        padding: {SPACING_XXS}px 0;
    }}
    QLabel[class="status-error"] {{
        color: {ACCENT_ERROR};
        font-size: {FONT_SIZE_SMALL}pt;
        font-family: {FONT_FAMILY};
        font-weight: {FONT_WEIGHT_NORMAL};
        min-height: {CONTROL_STATUS_LINE_MIN_HEIGHT}px;
        padding: {SPACING_XXS}px 0;
    }}
    QLabel[class="status-pending"] {{
        color: {TEXT_MUTED};
        font-size: {FONT_SIZE_SMALL}pt;
        font-family: {FONT_FAMILY};
        font-weight: {FONT_WEIGHT_NORMAL};
        min-height: {CONTROL_STATUS_LINE_MIN_HEIGHT}px;
        padding: {SPACING_XXS}px 0;
    }}
    QLabel[class="status-warning"] {{
        color: {ACCENT_WARNING};
        font-size: {FONT_SIZE_SMALL}pt;
        font-family: {FONT_FAMILY};
        font-weight: {FONT_WEIGHT_NORMAL};
        min-height: {CONTROL_STATUS_LINE_MIN_HEIGHT}px;
        padding: {SPACING_XXS}px 0;
    }}
    QLabel[class="placeholderMessage"],
    QLabel[class="chartPlaceholder"] {{
        font-size: {FONT_SIZE_BODY}pt;
        color: {TEXT_SECONDARY};
    }}
    QLabel[class="chartPlaceholder-incompatible"] {{
        font-size: {FONT_SIZE_BODY}pt;
        color: {TEXT_STATE_INCOMPATIBLE};
        background-color: {BG_STATE_INCOMPATIBLE};
        border: 1px solid {BORDER_INCOMPATIBLE};
        border-radius: {RADIUS_SM}px;
        padding: {SPACING_SM}px;
    }}
    QLabel[class="chartPlaceholder-empty"] {{
        font-size: {FONT_SIZE_BODY}pt;
        color: {TEXT_MUTED};
        padding: {SPACING_SM}px;
    }}
    QLabel[class="chartPlaceholder-error"] {{
        font-size: {FONT_SIZE_BODY}pt;
        color: {ACCENT_ERROR};
        border: 1px solid {ACCENT_ERROR};
        border-radius: {RADIUS_SM}px;
        padding: {SPACING_SM}px;
    }}

    /* CheckBox disabled (report chart list, etc.) */
    QCheckBox:disabled {{
        color: {TEXT_DISABLED};
    }}
    QCheckBox[state="incompatible"]:disabled {{
        color: {TEXT_STATE_INCOMPATIBLE};
        font-weight: {FONT_WEIGHT_BOLD};
    }}
    QCheckBox[state="recommended"] {{
        color: {ACCENT_PRIMARY};
        font-weight: {FONT_WEIGHT_BOLD};
    }}
    QCheckBox[state="insufficient_data"] {{
        color: {TEXT_MUTED};
    }}

    /* Recommendation chip buttons (chart guidance strip) */
    QPushButton[class="recoChip"] {{
        padding: {SPACING_XS}px {SPACING_SM}px;
        border-radius: {RADIUS_SM}px;
        border: 1px solid {BORDER};
        background: {BG_BLOCK};
        font-size: {FONT_SIZE_CAPTION}pt;
        font-family: {FONT_FAMILY};
    }}
    QPushButton[class="recoChip"][severity="error"] {{
        border-color: {ACCENT_ERROR_VIVID};
        color: {ACCENT_ERROR_VIVID};
    }}
    QPushButton[class="recoChip"][severity="warning"] {{
        border-color: {ACCENT_WARNING_VIVID};
        color: {ACCENT_WARNING_VIVID};
    }}
    QPushButton[class="recoChip"][severity="info"] {{
        border-color: {ACCENT_PRIMARY};
        color: {ACCENT_PRIMARY};
    }}
    QPushButton[class="recoChip"]:hover {{
        background: {SURFACE_HOVER};
    }}

    /* Tooltip (spec T-07) */
    QToolTip {{
        background-color: {BG_BLOCK};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
        border-radius: {RADIUS_SM}px;
        padding: {SPACING_XS}px {SPACING_SM}px;
        font-family: {FONT_FAMILY};
        font-size: {FONT_SIZE_CAPTION}pt;
    }}
    QLabel#statusBarLabel {{
        color: {TEXT_SECONDARY};
        font-size: {FONT_SIZE_CAPTION}pt;
        font-family: {FONT_FAMILY};
        font-weight: {FONT_WEIGHT_NORMAL};
        min-height: {LABEL_ROW_MIN_HEIGHT}px;
    }}
    QFrame#statusBarLamp {{
        border-radius: {STATUS_LAMP_SIZE // 2}px;
        background-color: {STATUS_LAMP_IDLE};
    }}
    QFrame#statusBarLamp[state="idle"], QFrame#statusBarLamp[state="ready"] {{
        background-color: {STATUS_LAMP_IDLE};
    }}
    QFrame#statusBarLamp[state="loading"], QFrame#statusBarLamp[state="analyzing"] {{
        background-color: {STATUS_LAMP_LOADING};
    }}
    QFrame#statusBarLamp[state="dirty"], QFrame#statusBarLamp[state="pending_refresh"], QFrame#statusBarLamp[state="warning"] {{
        background-color: {STATUS_LAMP_WARNING};
    }}
    QFrame#statusBarLamp[state="success"], QFrame#statusBarLamp[state="updated"] {{
        background-color: {STATUS_LAMP_SUCCESS};
    }}
    QFrame#statusBarLamp[state="error"] {{
        background-color: {STATUS_LAMP_ERROR};
    }}
    /* Connection signal lamps (座標 / 量測 / 關聯) in status bar */
    QFrame[class="connLamp"] {{
        border-radius: {CONN_LAMP_SIZE // 2}px;
        background-color: {STATUS_LAMP_IDLE};
    }}
    QFrame[class="connLamp"][state="pending"] {{
        background-color: {STATUS_LAMP_IDLE};
    }}
    QFrame[class="connLamp"][state="ok"] {{
        background-color: {STATUS_LAMP_SUCCESS};
    }}
    QFrame[class="connLamp"][state="warning"] {{
        background-color: {STATUS_LAMP_WARNING};
    }}
    QLabel[class="connLabel"] {{
        color: {TEXT_MUTED};
        font-size: {FONT_SIZE_CAPTION}pt;
        font-family: {FONT_FAMILY};
        font-weight: {FONT_WEIGHT_NORMAL};
        padding: 0;
    }}
    QFrame#statusBarSep {{
        color: {BORDER_SUBTLE};
    }}
    QPushButton#workorderSaveBtn[saveState="success"] {{
        background-color: {ACCENT_SUCCESS};
        border-color: {ACCENT_SUCCESS};
        color: {TEXT_ON_ACCENT};
        font-weight: {FONT_WEIGHT_BOLD};
    }}
    QPushButton#workorderSaveBtn[saveState="failure"] {{
        background-color: {ACCENT_ERROR};
        border-color: {ACCENT_ERROR};
        color: {TEXT_ON_ACCENT};
        font-weight: {FONT_WEIGHT_BOLD};
    }}
    /* workorderSaveBtn default state — renders as a standard primary action button */
    QPushButton#workorderSaveBtn {{
        font-weight: {FONT_WEIGHT_BOLD};
    }}

    /* Data Management: SPC mindmap tree readability tuning */
    QTreeWidget#spcMindmapTree {{
        font-size: {FONT_SIZE_BODY}pt;
    }}
    QTreeWidget#spcMindmapTree::item {{
        min-height: {TABLE_ROW_MIN_HEIGHT + SPACING_8}px;
        padding: {SPACING_4}px {SPACING_SM}px;
    }}
    QTreeWidget#spcMindmapTree QHeaderView::section {{
        padding: {SPACING_4}px {SPACING_SM}px;
    }}

    QFrame#stepCard QLabel[class="stepTitle"] {{
        min-height: {SECTION_TITLE_MIN_HEIGHT}px;
        padding-bottom: {SPACING_4}px;
        border-left: {ACCENT_STRIPE_W}px solid {ACCENT_PRIMARY};
        padding-left: {SPACING_8}px;
    }}
    QLabel[class="statsResultNormal"] {{
        color: {ACCENT_SUCCESS};
        font-weight: {FONT_WEIGHT_BOLD};
        font-size: {FONT_SIZE_BODY}pt;
    }}
    QLabel[class="statsResultAbnormal"] {{
        color: {ACCENT_ERROR};
        font-weight: {FONT_WEIGHT_BOLD};
        font-size: {FONT_SIZE_BODY}pt;
    }}

    /* Root Cause Hints (Audit Item 4) - Consolidate and use double braces for f-string escaping */
    QFrame[class~="hint-card"] {{
        background-color: {BG_CARD};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: {RADIUS_MD}px;
        margin-bottom: {SPACING_XXS}px;
    }}
    QFrame[class~="hint-error"] {{
        border-left: {SPACING_4}px solid {ACCENT_ERROR};
        background-color: {BG_STATE_INCOMPATIBLE}; /* Subtle red tint */
    }}
    QFrame[class~="hint-warning"] {{
        border-left: {SPACING_4}px solid {ACCENT_WARNING};
    }}
    QFrame[class~="hint-info"] {{
        border-left: {SPACING_4}px solid {ACCENT_PRIMARY};
    }}
    QLabel[class="hintSeverityError"] {{ color: {ACCENT_ERROR}; font-weight: {FONT_WEIGHT_BOLD}; }}
    QLabel[class="hintSeverityWarning"] {{ color: {ACCENT_WARNING}; font-weight: {FONT_WEIGHT_BOLD}; }}
    QLabel[class="hintSeverityInfo"] {{ color: {ACCENT_PRIMARY}; font-weight: {FONT_WEIGHT_BOLD}; }}
    QLabel[class="hintMainText"] {{ color: {TEXT_PRIMARY}; font-size: {FONT_SIZE_BODY}pt; font-weight: {FONT_WEIGHT_BOLD}; }}
    QLabel[class="hintDetailText"] {{ color: {TEXT_SECONDARY}; font-size: {FONT_SIZE_SMALL}pt; }}

    /* DataSetup page dense mode (local only) */
    QWidget[dataPage="dataSetup"] QLabel[class="stepTitle"] {{
        font-size: {FONT_SIZE_SECTION}pt;
        font-weight: {FONT_WEIGHT_BOLD};
        min-height: {DATA_SETUP_DENSE_STEP_TITLE_MIN_HEIGHT}px;
        padding-bottom: {SPACING_XXS}px;
        color: {TEXT_PRIMARY};
    }}
    QWidget[dataPage="dataSetup"] QLabel[class="caption"] {{
        font-size: {FONT_SIZE_CAPTION}pt;
        min-height: {DATA_SETUP_DENSE_CAPTION_MIN_HEIGHT}px;
        color: {TEXT_PRIMARY};
    }}
    QWidget[dataPage="dataSetup"] QLabel[class="formLabel"] {{
        font-size: {FONT_SIZE_BODY}pt;
        font-weight: {FONT_WEIGHT_NORMAL};
        min-height: {DATA_SETUP_DENSE_FORM_LABEL_MIN_HEIGHT}px;
        color: {TEXT_PRIMARY};
    }}
    QWidget[dataPage="dataSetup"] QLabel[class="sectionTitle"] {{
        font-size: {FONT_SIZE_SECTION}pt;
        font-weight: {FONT_WEIGHT_BOLD};
        color: {TEXT_PRIMARY};
        padding-top: {SPACING_8}px;
    }}
    QWidget[dataPage="dataSetup"] QListWidget {{
        padding: {DATA_SETUP_DENSE_LIST_PADDING}px;
    }}
    QFrame#dataSetupTable {{
        background-color: {BG_BLOCK};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: {CARD_RADIUS}px;
    }}
    QFrame[class="dataSetupTableRegion"] {{
        background-color: {BG_SECONDARY};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: {RADIUS_MD}px;
    }}
    QFrame[class="dataSetupTableRegion"] QLabel[class="sectionTitle"] {{
        font-size: {FONT_SIZE_BODY}pt;
        font-weight: {FONT_WEIGHT_BOLD};
        color: {TEXT_PRIMARY};
        padding-top: 0;
    }}
    /* ControlPanel (sidebar): explicit dark background + override all text to sidebar-safe colors */
    QWidget[sidebarPanel="controlDense"] {{
        background-color: {SIDEBAR_DARK_BG};
    }}
    QWidget[sidebarPanel="controlDense"] QLabel[class="sectionTitle"] {{
        font-size: {SIDEBAR_SECTION_TITLE_FONT_SIZE}pt;
        color: {SIDEBAR_TEXT_PRIMARY};
    }}
    QWidget[sidebarPanel="controlDense"] QLabel[class="formLabel"] {{
        font-size: {SIDEBAR_LABEL_FONT_SIZE}pt;
        color: {SIDEBAR_TEXT_PRIMARY};
    }}
    QWidget[sidebarPanel="controlDense"] QLabel[class="status-ok"],
    QWidget[sidebarPanel="controlDense"] QLabel[class="status-error"],
    QWidget[sidebarPanel="controlDense"] QLabel[class="status-pending"],
    QWidget[sidebarPanel="controlDense"] QLabel[class="status-warning"] {{
        font-size: {SIDEBAR_LABEL_FONT_SIZE}pt;
        padding: 1px 0;
    }}
    /* ControlPanel combo boxes: keep light bg for input contrast on dark sidebar */
    QWidget[sidebarPanel="controlDense"] QComboBox {{
        background-color: {BG_BLOCK};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
        padding: 0px {SPACING_XS}px;
        min-height: {SIDEBAR_COMPACT_INPUT_HEIGHT}px;
        font-size: {SIDEBAR_LABEL_FONT_SIZE}pt;
    }}
    QWidget[sidebarPanel="controlDense"] QLineEdit {{
        background-color: {BG_BLOCK};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER};
        padding: 0px {SPACING_XS}px;
        min-height: {SIDEBAR_COMPACT_INPUT_HEIGHT}px;
        font-size: {SIDEBAR_LABEL_FONT_SIZE}pt;
    }}
    QWidget[sidebarPanel="controlDense"] QFrame[class="segmentedControl"] QPushButton[class="featureToggle"] {{
        min-height: {SIDEBAR_COMPACT_FEATURE_HEIGHT}px;
        font-size: {SIDEBAR_LABEL_FONT_SIZE}pt;
    }}
    QWidget[sidebarPanel="controlDense"] QPushButton#nextStepBtn,
    QWidget[sidebarPanel="controlDense"] QPushButton#refreshBtn {{
        min-height: {SIDEBAR_COMPACT_ACTION_HEIGHT}px;
        font-size: {SIDEBAR_LABEL_FONT_SIZE}pt;
    }}

    /* Statistical test result label (e.g. normality test result) */
    QLabel[class="statsResult"] {{
        font-size: {FONT_SIZE_SECTION}pt;
        font-weight: {FONT_WEIGHT_BOLD};
        color: {TEXT_PRIMARY};
        min-height: {LABEL_ROW_MIN_HEIGHT}px;
        padding: {SPACING_XXS}px {SPACING_XS}px;
    }}

    /* Chart page: compact description above chart (1-2 lines) */
    QLabel[class="chartDescCompact"] {{
        font-size: {FONT_SIZE_CAPTION}pt;
        color: {TEXT_SECONDARY};
        padding: {SPACING_XXS}px {SPACING_XS}px;
        min-height: {CHART_DESC_MIN_HEIGHT}px;
    }}
    /* Chart page: left sidebar compact hint text */
    QLabel[class="chartHintCompact"] {{
        font-size: {FONT_SIZE_SMALL}pt;
        color: {TEXT_MUTED};
        padding: {SPACING_XXS}px 0;
    }}
    /* Chart page: bottom details strip (1-2 lines, integrated) */
    QLabel[class="chartDetailsStrip"] {{
        font-size: {FONT_SIZE_SMALL}pt;
        color: {TEXT_SECONDARY};
        background-color: {BG_SECONDARY};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: {RADIUS_SM}px;
        padding: {SPACING_XS}px {SPACING_SM}px;
        min-height: {CONTROL_STATUS_LINE_MIN_HEIGHT}px;
    }}
    QLabel[class="chartDetailsStrip"][interactionState="changed"] {{
        color: {TEXT_PRIMARY};
        background-color: {PRIMARY_100};
        border-color: {ACCENT_PRIMARY};
    }}
    /* Hint labels — canonical block (duplicates removed, see root-cause section above) */
    QWidget[class="root-cause-panel"] {{
        background-color: {BG_BLOCK};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: {CARD_RADIUS}px;
    }}
    QLabel[class="rootCauseTitle"] {{
        color: {TEXT_PRIMARY};
        font-size: {FONT_SIZE_BODY}pt;
        font-weight: {FONT_WEIGHT_BOLD};
    }}
    QLabel[class="rootCauseEmpty"] {{
        color: {ACCENT_SUCCESS};
        font-style: italic;
    }}

    /* ── DiagnosticPage ───────────────────────────────────────────── */
    QFrame[class~="diagHeaderBar"] {{
        background-color: {BG_BLOCK};
        border: 1px solid {BORDER_SUBTLE};
        border-bottom: 2px solid {CARD_SHADOW_BOTTOM};
        border-radius: {RADIUS_BUTTON}px;
    }}
    QLabel[class="diagPageTitle"],
    QLabel[class~="diagStatusBadge"],
    QLabel[class="diagUpdatedLabel"],
    QLabel[class="diagDescription"],
    QLabel[class="diagEmptyState"],
    QLabel[class="diagAllClear"],
    QLabel[class~="diagSectionTitle"],
    QLabel[class="diagSectionEmpty"],
    QLabel[class~="diagSeverityError"],
    QLabel[class~="diagSeverityWarning"],
    QLabel[class~="diagSeverityInfo"],
    QLabel[class="diagPriorityLabel"],
    QLabel[class="diagMainText"],
    QLabel[class="diagSectionHeader"],
    QLabel[class="diagEvidenceItem"],
    QLabel[class="diagThresholdText"],
    QLabel[class="diagConfidenceLabel"],
    QLabel[class="diagIpcText"],
    QLabel[class="diagActionText"],
    QLabel[class="diagChartChip"] {{
        font-family: {FONT_FAMILY};
    }}
    QLabel[class="diagPageTitle"] {{
        color: {TEXT_PRIMARY};
        font-size: {FONT_SIZE_SECTION}pt;
        font-weight: {FONT_WEIGHT_BOLD};
    }}
    QLabel[class~="diagStatusBadge"] {{
        font-size: {FONT_SIZE_CAPTION}pt;
        font-weight: {FONT_WEIGHT_BOLD};
        padding: {SPACING_XXS}px {SPACING_SM}px;
        border-radius: {RADIUS_SM}px;
    }}
    QLabel[class~="diagStatusBadge-idle"]    {{ background-color: {SURFACE_HOVER}; color: {TEXT_MUTED}; }}
    QLabel[class~="diagStatusBadge-ok"]      {{ background-color: {BG_BLOCK}; color: {ACCENT_SUCCESS}; }}
    QLabel[class~="diagStatusBadge-warning"] {{ background-color: {BG_BLOCK}; color: {ACCENT_WARNING}; }}
    QLabel[class~="diagStatusBadge-error"]   {{ background-color: {BG_BLOCK}; color: {ACCENT_ERROR}; }}
    QLabel[class~="diagStatusBadge-info"]    {{ background-color: {BG_BLOCK}; color: {ACCENT_PRIMARY}; }}
    QLabel[class="diagUpdatedLabel"] {{ color: {TEXT_SECONDARY}; font-size: {FONT_SIZE_CAPTION}pt; }}
    QLabel[class="diagDescription"]  {{ color: {TEXT_SECONDARY}; font-size: {FONT_SIZE_CAPTION}pt; }}
    QLabel[class="diagEmptyState"]   {{ color: {TEXT_MUTED}; font-size: {FONT_SIZE_BODY}pt; font-style: italic; }}
    QLabel[class="diagAllClear"]     {{ color: {ACCENT_SUCCESS}; font-size: {FONT_SIZE_BODY}pt; font-weight: {FONT_WEIGHT_BOLD}; }}
    QLabel[class~="diagSectionTitle"] {{
        font-size: {FONT_SIZE_BODY}pt;
        font-weight: {FONT_WEIGHT_BOLD};
        color: {TEXT_PRIMARY};
        padding-bottom: {SPACING_XXS}px;
        border-bottom: 1px solid {BORDER_SUBTLE};
    }}
    QLabel[class~="diagSectionTitle-error"]   {{ color: {ACCENT_ERROR}; }}
    QLabel[class~="diagSectionTitle-warning"] {{ color: {ACCENT_WARNING}; }}
    QLabel[class~="diagSectionTitle-info"]    {{ color: {ACCENT_PRIMARY}; }}
    QLabel[class="diagSectionEmpty"]  {{ color: {TEXT_MUTED}; font-size: {FONT_SIZE_CAPTION}pt; padding-left: {SPACING_SM}px; }}
    QFrame[class~="diagHintCard"] {{
        background-color: {BG_BLOCK};
        border: 1px solid {BORDER_SUBTLE};
        border-bottom: 2px solid {BORDER};
        border-radius: {RADIUS_SM}px;
    }}
    QLabel[class~="diagSeverityError"]   {{ color: {ACCENT_ERROR};   font-weight: {FONT_WEIGHT_BOLD}; font-size: {FONT_SIZE_CAPTION}pt; }}
    QLabel[class~="diagSeverityWarning"] {{ color: {ACCENT_WARNING}; font-weight: {FONT_WEIGHT_BOLD}; font-size: {FONT_SIZE_CAPTION}pt; }}
    QLabel[class~="diagSeverityInfo"]    {{ color: {ACCENT_PRIMARY}; font-weight: {FONT_WEIGHT_BOLD}; font-size: {FONT_SIZE_CAPTION}pt; }}
    QLabel[class="diagPriorityLabel"] {{ color: {TEXT_SECONDARY}; font-size: {FONT_SIZE_CAPTION}pt; }}
    QLabel[class="diagMainText"] {{
        color: {TEXT_PRIMARY};
        font-size: {FONT_SIZE_BODY}pt;
        font-weight: {FONT_WEIGHT_BOLD};
    }}
    QFrame[class="diagSeparator"] {{ color: {BORDER_SUBTLE}; }}
    QLabel[class="diagSectionHeader"] {{
        color: {TEXT_SECONDARY};
        font-size: {FONT_SIZE_CAPTION}pt;
        font-weight: {FONT_WEIGHT_BOLD};
    }}
    QLabel[class="diagEvidenceItem"] {{
        color: {TEXT_PRIMARY};
        font-size: {FONT_SIZE_CAPTION}pt;
        background-color: {SURFACE_HOVER};
        border-radius: {RADIUS_SM}px;
        padding: {SPACING_4}px {SPACING_SM}px;
    }}
    QLabel[class="diagThresholdText"] {{ color: {TEXT_MUTED}; font-size: {FONT_SIZE_CAPTION}pt; font-style: italic; }}
    QLabel[class="diagConfidenceLabel"] {{ color: {TEXT_SECONDARY}; font-size: {FONT_SIZE_CAPTION}pt; min-width: {DIAG_CONFIDENCE_LABEL_MIN_W}px; }}
    QFrame[class="diagConfidenceBar"] {{
        background-color: {SURFACE_HOVER};
        border-radius: {CONFIDENCE_BAR_HEIGHT // 2}px;
        max-height: {CONFIDENCE_BAR_HEIGHT}px;
    }}
    QFrame[class="diagConfidenceFill"] {{
        background-color: {ACCENT_PRIMARY};
        border-radius: {CONFIDENCE_BAR_HEIGHT // 2}px;
        max-height: {CONFIDENCE_BAR_HEIGHT}px;
    }}
    QLabel[class="diagIpcText"] {{ color: {TEXT_SECONDARY}; font-size: {FONT_SIZE_CAPTION}pt; }}
    QLabel[class="diagActionText"] {{
        color: {TEXT_PRIMARY};
        font-size: {FONT_SIZE_CAPTION}pt;
        padding-left: {SPACING_SM}px;
    }}
    QLabel[class="diagChartChip"] {{
        color: {ACCENT_PRIMARY};
        background-color: {BG_PANEL};
        border: 1px solid {ACCENT_PRIMARY};
        border-radius: {RADIUS_SM}px;
        font-size: {FONT_SIZE_CAPTION}pt;
        padding: 1px {SPACING_4}px;
    }}

    /* ── Process diagnosis dashboard (DiagnosticPage) ─────────────── */
    /* Dashboard section card: grouped metric card in the grid */
    QFrame#dashboardSectionCard {{
        background-color: {BG_CARD};
        border: 1px solid {BORDER_SUBTLE};
        border-bottom: 2px solid {CARD_SHADOW_BOTTOM};
        border-radius: {CARD_RADIUS}px;
    }}
    /* Section accent stripe (left border) — color set via property */
    QFrame#dashboardSectionCard[section="capability"] {{
        border-left: {ACCENT_STRIPE_W}px solid {ACCENT_PRIMARY};
    }}
    QFrame#dashboardSectionCard[section="descriptive"] {{
        border-left: {ACCENT_STRIPE_W}px solid {PRIMARY_300};
    }}
    QFrame#dashboardSectionCard[section="spec"] {{
        border-left: {ACCENT_STRIPE_W}px solid {ACCENT_WARNING};
    }}
    QFrame#dashboardSectionCard[section="yield"] {{
        border-left: {ACCENT_STRIPE_W}px solid {ACCENT_SUCCESS};
    }}
    QFrame#dashboardSectionCard[section="normality"] {{
        border-left: {ACCENT_STRIPE_W}px solid {CHART_SPEC_LIMITS};
    }}
    QFrame#dashboardSectionCard[section="relation"] {{
        border-left: {ACCENT_STRIPE_W}px solid {CHART_SERIES_SECONDARY};
    }}
    QFrame#dashboardSectionCard[section="process"] {{
        border-left: {ACCENT_STRIPE_W}px solid {ACCENT_ERROR};
    }}
    /* Section card header label */
    QLabel[class="dashSectionTitle"] {{
        font-size: {FONT_SIZE_SECTION}pt;
        font-weight: {FONT_WEIGHT_BOLD};
        color: {TEXT_PRIMARY};
        padding: {SPACING_4}px 0;
    }}
    /* Conditional value coloring */
    QLabel[class="dashValueGood"] {{
        color: {ACCENT_SUCCESS};
        font-weight: {FONT_WEIGHT_BOLD};
        font-size: {FONT_SIZE_BODY}pt;
        font-family: {FONT_FAMILY_MONO};
    }}
    QLabel[class="dashValueWarning"] {{
        color: {ACCENT_WARNING};
        font-weight: {FONT_WEIGHT_BOLD};
        font-size: {FONT_SIZE_BODY}pt;
        font-family: {FONT_FAMILY_MONO};
    }}
    QLabel[class="dashValueBad"] {{
        color: {ACCENT_ERROR};
        font-weight: {FONT_WEIGHT_BOLD};
        font-size: {FONT_SIZE_BODY}pt;
        font-family: {FONT_FAMILY_MONO};
    }}
    QLabel[class="dashValueNeutral"] {{
        color: {TEXT_PRIMARY};
        font-size: {FONT_SIZE_BODY}pt;
        font-family: {FONT_FAMILY_MONO};
    }}
    QLabel[class="dashMetricLabel"] {{
        color: {TEXT_SECONDARY};
        font-size: {FONT_SIZE_CAPTION}pt;
        font-family: {FONT_FAMILY};
        min-height: {LABEL_ROW_MIN_HEIGHT}px;
    }}
    QLabel[class="dashColHeader"] {{
        color: {TEXT_MUTED};
        font-size: {FONT_SIZE_SMALL}pt;
        font-weight: {FONT_WEIGHT_BOLD};
        font-family: {FONT_FAMILY};
        padding: {SPACING_XXS}px 0;
    }}
    /* Hero KPI card (top-row big numbers) */
    QFrame#dashboardHeroCard {{
        background-color: {BG_CARD};
        border: 1px solid {BORDER_SUBTLE};
        border-bottom: 2px solid {CARD_SHADOW_BOTTOM_MD};
        border-left: 4px solid {ACCENT_PRIMARY};
        border-radius: {CARD_RADIUS}px;
        min-width: {KPI_CARD_MIN_W}px;
    }}
    QLabel[class="dashHeroValue"] {{
        font-size: {FONT_SIZE_TITLE}pt;
        font-weight: {FONT_WEIGHT_BOLD};
        font-family: {FONT_FAMILY_MONO};
        color: {TEXT_PRIMARY};
    }}
    QLabel[class="dashHeroLabel"] {{
        font-size: {FONT_SIZE_SMALL}pt;
        color: {TEXT_MUTED};
        font-family: {FONT_FAMILY};
    }}
    /* Dashboard verdict badge */
    QLabel[class="dashVerdictGood"] {{
        background-color: {ACCENT_SUCCESS};
        color: {TEXT_ON_ACCENT};
        font-weight: {FONT_WEIGHT_BOLD};
        font-size: {FONT_SIZE_CAPTION}pt;
        border-radius: {RADIUS_SM}px;
        padding: {SPACING_XXS}px {SPACING_SM}px;
    }}
    QLabel[class="dashVerdictBad"] {{
        background-color: {ACCENT_ERROR};
        color: {TEXT_ON_ACCENT};
        font-weight: {FONT_WEIGHT_BOLD};
        font-size: {FONT_SIZE_CAPTION}pt;
        border-radius: {RADIUS_SM}px;
        padding: {SPACING_XXS}px {SPACING_SM}px;
    }}

    /* --- 製程統計分析報告 (Process Statistics Report) --- */
    QFrame#processStatReport {{
        background-color: {BG_CARD};
        border: 1px solid {BORDER_SUBTLE};
        border-left: 4px solid {ACCENT_SUCCESS};
        border-radius: {RADIUS_MD}px;
    }}
    QFrame#processStatReport[alarmTone="critical"] {{
        border-left: 4px solid {ACCENT_ERROR};
        background-color: {ERROR_SURFACE_SUBTLE};
    }}
    QFrame#processStatReport[alarmTone="warning"] {{
        border-left: 4px solid {ACCENT_WARNING};
        background-color: {WARNING_SURFACE_SUBTLE};
    }}
    QFrame#processStatReport[alarmTone="normal"] {{
        border-left: 4px solid {ACCENT_SUCCESS};
        background-color: {SUCCESS_SURFACE_SUBTLE};
    }}
    QLabel[class="processReportTitle"] {{
        font-size: {FONT_SIZE_PROCESS_DASH_STAT}pt;
        font-weight: {FONT_WEIGHT_BOLD};
        color: {TEXT_PRIMARY};
        padding-bottom: {SPACING_4}px;
        border-bottom: 1px solid {BORDER_SUBTLE};
    }}
    QLabel[class="processReportSectionLabel"] {{
        font-size: {FONT_SIZE_PROCESS_DASH_STAT}pt;
        font-weight: {FONT_WEIGHT_BOLD};
        color: {TEXT_SECONDARY};
        padding-top: {SPACING_8}px;
        padding-bottom: {SPACING_XXS}px;
        border-bottom: 1px solid {BORDER_SUBTLE};
    }}
    QFrame[class="processReportMetric"] {{
        background-color: {BG_BLOCK};
        border: none;
        border-bottom: 1px solid {BORDER_SUBTLE};
        padding: {SPACING_4}px {SPACING_4}px;
    }}
    QLabel[class="processReportSource"] {{
        font-size: {FONT_SIZE_PROCESS_DASH_STAT}pt;
        color: {TEXT_MUTED};
    }}

    /* --- 製程診斷儀表板 (legacy card selectors retained) --- */
    QFrame#processDashCard, QFrame#processAlarmCard {{
        background-color: {BG_CARD};
        border: 1px solid {BORDER_SUBTLE};
        border-bottom: 2px solid {CARD_SHADOW_BOTTOM};
        border-radius: {CARD_RADIUS}px;
    }}
    QFrame#processDiagnosisHighlightCard {{
        background-color: {BG_CARD};
        border: 1px solid {BORDER_SUBTLE};
        border-bottom: 2px solid {CARD_SHADOW_BOTTOM_MD};
        border-radius: {CARD_RADIUS}px;
        border-left: 4px solid {ACCENT_PRIMARY};
    }}
    
    /* 警報側欄設計 (Alarm Level Accents) - 提升視覺銳利度 */
    QFrame#processAlarmCard[alarmTone="critical"] {{
        border-left: 5px solid {ACCENT_ERROR};
        background-color: {PROCESS_ALARM_CARD_BG_CRITICAL};
    }}
    QFrame#processAlarmCard[alarmTone="warning"] {{
        border-left: 5px solid {ACCENT_WARNING};
        background-color: {PROCESS_ALARM_CARD_BG_WARNING};
    }}
    QFrame#processAlarmCard[alarmTone="normal"] {{
        border-left: 5px solid {ACCENT_SUCCESS};
        background-color: {PROCESS_ALARM_CARD_BG_NORMAL};
    }}

    QLabel[class="processDashCardTitle"] {{
        font-size: {FONT_SIZE_SECTION}pt;
        font-weight: {FONT_WEIGHT_BOLD};
        color: {TEXT_PRIMARY};
    }}
    
    QLabel[class="processDashFieldLabel"] {{
        font-size: {FONT_SIZE_DASH_LABEL}pt;
        font-weight: {FONT_WEIGHT_NORMAL};
        color: {TEXT_MUTED};
    }}

    /* KPI Typography - 高解析對齊 (Alignment & Sharpness) */
    QLabel[class="processDashKpiValueLarge"] {{
        font-size: {FONT_SIZE_PROCESS_DASH_KPI}pt;
        font-weight: {FONT_WEIGHT_BOLD};
        color: {TEXT_PRIMARY};
        /* 推薦在具備表格數字 (Tabular Figures) 的字體環境使用 */
    }}
    QLabel[class="processDashKpiValueLarge"][valueState="good"] {{ color: {ACCENT_SUCCESS}; }}
    QLabel[class="processDashKpiValueLarge"][valueState="warning"] {{ color: {ACCENT_WARNING}; }}
    QLabel[class="processDashKpiValueLarge"][valueState="bad"] {{ color: {ACCENT_ERROR}; }}
    QLabel[class="processDashKpiValueLarge"][valueState="neutral"] {{ color: {TEXT_PRIMARY}; }}

    QLabel[class="processDashKpiValueMedium"] {{
        font-size: {FONT_SIZE_PROCESS_DASH_KPI_MEDIUM}pt;
        font-weight: {FONT_WEIGHT_BOLD};
        color: {TEXT_PRIMARY};
    }}
    QLabel[class="processDashKpiValueMedium"][valueState="good"]    {{ color: {ACCENT_SUCCESS}; }}
    QLabel[class="processDashKpiValueMedium"][valueState="warning"]  {{ color: {ACCENT_WARNING}; }}
    QLabel[class="processDashKpiValueMedium"][valueState="bad"]      {{ color: {ACCENT_ERROR};   }}
    QLabel[class="processDashKpiValueMedium"][valueState="neutral"]  {{ color: {TEXT_SECONDARY}; }}

    QLabel[class="processDashStatSmall"] {{
        font-size: {FONT_SIZE_PROCESS_DASH_STAT}pt;
        color: {TEXT_SECONDARY};
    }}
    QLabel[class="processDashStatSmall"][valueState="good"]    {{ color: {ACCENT_SUCCESS}; }}
    QLabel[class="processDashStatSmall"][valueState="warning"]  {{ color: {ACCENT_WARNING}; }}
    QLabel[class="processDashStatSmall"][valueState="bad"]      {{ color: {ACCENT_ERROR};   }}
    QLabel[class="processDashStatSmall"][valueState="neutral"]  {{ color: {TEXT_SECONDARY}; }}

    QTabWidget[class~="processMatrixTabs"]::pane {{
        background-color: {BG_CARD};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: {CARD_RADIUS}px;
        top: -1px;
    }}
    QTabWidget[class~="processMatrixTabs"] QTabBar::tab {{
        min-height: {BUTTON_MIN_HEIGHT}px;
        padding: {SPACING_8}px {SPACING_16}px;
    }}
    QTabWidget[class~="processMatrixTabs"] QTabBar::tab:selected {{
        border-bottom: 3px solid {ACCENT_PRIMARY};
    }}

    QFrame#diagnosticBanner, QFrame#diagnosticSection {{
        background-color: {BG_CARD};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: {CARD_RADIUS}px;
    }}
    QFrame#diagnosticBanner {{
        border-left: 4px solid {ACCENT_PRIMARY};
    }}
    QFrame#diagnosticEvidenceRow, QFrame#diagnosticMetricTile {{
        background-color: {BG_SECONDARY};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: {RADIUS_MD}px;
    }}
    QFrame#diagnosticInfoGrid, QFrame#diagnosticMetricGrid {{
        background-color: transparent;
        border: none;
    }}
    QLabel[class="diagnosticSectionTitle"] {{
        font-size: {FONT_SIZE_SECTION}pt;
        font-weight: {FONT_WEIGHT_BOLD};
        color: {TEXT_PRIMARY};
    }}
    QLabel[class="diagnosticBodyText"] {{
        font-size: {FONT_SIZE_PROCESS_DASH_STAT}pt;
        color: {TEXT_SECONDARY};
    }}
    QLabel[class="diagnosticMutedText"] {{
        font-size: {FONT_SIZE_PROCESS_DASH_STAT}pt;
        color: {TEXT_MUTED};
    }}
    QFrame#diagnosticBulletList {{
        background-color: transparent;
        border: none;
    }}
    QLabel[class="diagnosticBulletIndex"] {{
        font-size: {FONT_SIZE_PROCESS_DASH_STAT}pt;
        font-weight: {FONT_WEIGHT_BOLD};
        color: {TEXT_MUTED};
    }}
    QLabel[class="diagnosticBulletText"] {{
        font-size: {FONT_SIZE_PROCESS_DASH_STAT}pt;
        color: {TEXT_SECONDARY};
    }}
    QLabel[class="diagnosticMetricLabel"] {{
        font-size: {FONT_SIZE_CAPTION}pt;
        color: {TEXT_MUTED};
    }}
    QLabel[class="diagnosticMetricValue"] {{
        font-size: {FONT_SIZE_SECTION}pt;
        color: {TEXT_PRIMARY};
        font-weight: {FONT_WEIGHT_BOLD};
    }}
    QLabel[class="diagnosticBadge"] {{
        min-height: {LABEL_ROW_MIN_HEIGHT}px;
        padding: {SPACING_XXS}px {SPACING_SM}px;
        border-radius: {RADIUS_SM}px;
        border: 1px solid {BORDER_SUBTLE};
        background-color: {BG_SECONDARY};
        color: {TEXT_SECONDARY};
        font-size: {FONT_SIZE_BODY}pt;
        font-weight: {FONT_WEIGHT_BOLD};
    }}
    QLabel[class="diagnosticBadge"][state="support"],
    QLabel[class="diagnosticBadge"][state="analyzed"] {{
        color: {ACCENT_SUCCESS};
        border-color: {ACCENT_SUCCESS};
        background-color: {SUCCESS_SURFACE_SUBTLE};
    }}
    QLabel[class="diagnosticBadge"][state="refute"],
    QLabel[class="diagnosticBadge"][state="error"] {{
        color: {ACCENT_ERROR};
        border-color: {ACCENT_ERROR};
        background-color: {ERROR_SURFACE_SUBTLE};
    }}
    QLabel[class="diagnosticBadge"][state="warning"],
    QLabel[class="diagnosticBadge"][state="available-not-selected"] {{
        color: {ACCENT_WARNING};
        border-color: {ACCENT_WARNING};
        background-color: {WARNING_SURFACE_SUBTLE};
    }}
    QLabel[class="diagnosticBadge"][state="neutral"] {{
        color: {TEXT_SECONDARY};
        border-color: {BORDER};
        background-color: {BG_SECONDARY};
    }}
    QLabel[class="diagnosticBadge"][state="unavailable"],
    QLabel[class="diagnosticBadge"][state="not-applicable"],
    QLabel[class="diagnosticBadge"][state="missing-data"],
    QLabel[class="diagnosticBadge"][state="no-data"] {{
        color: {TEXT_MUTED};
        border-color: {BORDER_SUBTLE};
        background-color: {BG_SECONDARY};
    }}
    QLabel[class="diagnosticBadge"][tone="subtle"] {{
        color: {TEXT_MUTED};
        border-color: {BORDER_SUBTLE};
        background-color: {BG_SECONDARY};
        font-weight: {FONT_WEIGHT_NORMAL};
    }}
    QTableWidget#diagnosticMatrixTable {{
        background-color: {BG_CARD};
        alternate-background-color: {BG_SECONDARY};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: {RADIUS_MD}px;
        gridline-color: {BORDER_SUBTLE};
        color: {TEXT_SECONDARY};
        font-size: {FONT_SIZE_BODY}pt;
        selection-background-color: {SURFACE_ACTIVE};
        selection-color: {TEXT_PRIMARY};
    }}
    QTableWidget#diagnosticMatrixTable::item {{
        padding: {SPACING_4}px {SPACING_8}px;
    }}
    QTableWidget#diagnosticMatrixTable QHeaderView::section {{
        background-color: {TABLE_HEADER_BG};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_SUBTLE};
        padding: {SPACING_8}px;
        font-weight: {FONT_WEIGHT_BOLD};
    }}

    /* Message box (attempt to style - may not apply on all platforms) */
    QMessageBox {{
        background-color: {BG_PRIMARY};
        color: {TEXT_PRIMARY};
    }}
    """
    # Some Qt builds are sensitive to QSS comments and may report
    # "Could not parse application stylesheet". Strip comments at runtime
    # while keeping source comments for maintainability.
    return re.sub(r"/\*.*?\*/", "", stylesheet, flags=re.S)


def get_dark_stylesheet() -> str:
    """Backward-compatible alias for the historical theme function name."""
    return get_app_stylesheet()
