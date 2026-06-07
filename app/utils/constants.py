APP_AUTHOR = "Mitcorp SQE 陳智富"
INSTRUCTION_VERSION = "v2"

# SPI measure columns; used for multi-feature selection and chart compatibility
FEATURE_COLUMNS = ["Volume", "Area", "Height"]

# Order-column priority: first match in a DataFrame determines sort order for SPC charts.
# Keep time-like columns first so trend charts (CUSUM/EWMA/Run) are computed in chronological order.
ORDER_COL_PRIORITY = ("Time", "Timestamp", "timestamp", "DateTime", "BoardNo", "PanelId")

# Filter dropdown "all" option; used for batch/refdes/part_type comparison and UI labels
FILTER_ALL = "全部 (All)"

# Analysis range options for the 範圍 ComboBox
RANGE_ALL_BOARDS = "全批"
RANGE_FIRST      = "首件"
RANGE_LAST       = "末件"
RANGE_SPECIFY    = "指定板號"

# Display names for feature selection UI
FEATURE_DISPLAY_NAMES = {
    "Volume": "Volume (體積)",
    "Area": "Area (面積)",
    "Height": "Height (高度)",
}

# Phase 3: unified empty / incompatible chart messages (used by chart_registry and BaseChart)
MSG_NO_DATA = "無資料或無法繪圖。"
MSG_INCOMPATIBLE_SINGLE = "此圖表僅支援單一特徵，請在元件/量測選定頁選擇一個特徵。"
# 分布／箱型／常態：至少一個特徵即可；多選時以分頁或並列方式呈現各特徵。
MSG_INCOMPATIBLE_AT_LEAST_ONE = "此圖表需至少選擇一個量測特徵；可於元件/量測選定頁單選或多選並列顯示。"
MSG_INCOMPATIBLE_DUAL = "此圖表需選擇 2 個特徵（雙特徵分析）。"
MSG_INCOMPATIBLE_TRIPLE = "此圖表需選擇 3 個特徵（Volume、Area、Height）。"
MSG_INCOMPATIBLE_SINGLE_OR_DUAL = "此圖表需單一或雙特徵。"
MSG_UNKNOWN_CHART = "未知圖表。"
# Phase 4: suffix when chart is incompatible (not a system error)
MSG_NOT_SYSTEM_ERROR = "（此為依目前量測選取之正常提示，並非系統錯誤。）"
