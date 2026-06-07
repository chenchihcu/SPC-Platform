"""Shared visible workflow labels for the desktop shell."""

WORKFLOW_LABEL_DATA_SETUP = "資料設定"
WORKFLOW_LABEL_LIBRARY = "資料庫"
WORKFLOW_LABEL_CHARTS = "統計圖表"
WORKFLOW_LABEL_DIAGNOSTIC_1 = "診斷一"
WORKFLOW_LABEL_DIAGNOSTIC_2 = "診斷二"
WORKFLOW_LABEL_DIAGNOSTIC = WORKFLOW_LABEL_DIAGNOSTIC_1  # backward compat alias
WORKFLOW_LABEL_REPORT = "報告匯出"
WORKFLOW_LABEL_REFERENCE = "說明"

VISIBLE_WORKFLOW_TABS: list[tuple[str, int]] = [
    (WORKFLOW_LABEL_DATA_SETUP, 0),
    (WORKFLOW_LABEL_LIBRARY, 6),
    (WORKFLOW_LABEL_CHARTS, 2),
    (WORKFLOW_LABEL_DIAGNOSTIC_1, 5),
    (WORKFLOW_LABEL_DIAGNOSTIC_2, 7),
    (WORKFLOW_LABEL_REPORT, 3),
    (WORKFLOW_LABEL_REFERENCE, 4),
]
WORKFLOW_LABEL_BY_STACK = {stack_index: label for label, stack_index in VISIBLE_WORKFLOW_TABS}


def workflow_label_for_stack(stack_index: int) -> str:
    """Return the visible workflow label for a stack index."""
    return WORKFLOW_LABEL_BY_STACK.get(stack_index, "")
