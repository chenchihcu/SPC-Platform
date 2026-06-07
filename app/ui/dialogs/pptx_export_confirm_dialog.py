"""PPTX export confirmation: read-only chart list before writing the file."""

from __future__ import annotations

from typing import List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.analytics.chart_registry import get_chart_display_name
from app.ui.theme.layout_policy import fit_top_level_to_available
from app.ui.theme.tokens import (
    DIALOG_MIN_HEIGHT_STANDARD,
    DIALOG_MIN_WIDTH_WIDE,
    DIALOG_PPTX_CONFIRM_INIT_HEIGHT,
    DIALOG_PPTX_CONFIRM_INIT_WIDTH,
)


def estimate_gallery_pages(chart_count: int) -> int:
    """Match pptx_report_builder: (len(items) + 3) // 4 when items > 0."""
    if chart_count <= 0:
        return 0
    return (chart_count + 3) // 4


def build_pptx_export_confirmation_body_lines(
    chart_ids: List[str],
    *,
    using_fallback: bool,
) -> List[str]:
    """Build human-readable lines for the confirmation dialog (testable, no Qt)."""
    lines: List[str] = []
    if using_fallback:
        lines.append("範圍：未勾選任何圖表，將使用建議預設圖表。")
    else:
        lines.append("範圍：依目前勾選。")
    n = len(chart_ids)
    lines.append(f"證據圖：共 {n} 張（下列為將嘗試納入的圖表）。")
    gp = estimate_gallery_pages(n)
    lines.append(f"預估畫廊頁數：{gp} 頁（每頁最多 4 張證據圖）。")
    lines.append("")
    lines.append("圖表清單：")
    for cid in chart_ids:
        lines.append(f"  • {get_chart_display_name(cid, lang='zh_only')}")
    lines.append("")
    lines.append("敘事頁「分布分析」：是（工程報告固定包含一頁；與上方勾選無關）。")
    lines.append(
        "註：若特徵不足或單張證據圖渲染失敗，實際插入張數可能少於上述。"
    )
    return lines


class PptxExportConfirmDialog(QDialog):
    """唯讀確認：即將寫入 PPTX 的圖表清單與敘事頁說明。"""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        chart_ids: List[str],
        using_fallback: bool,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("匯出確認")
        self.setModal(True)
        layout = QVBoxLayout(self)
        intro = QLabel("即將匯出至 PowerPoint，請確認下列內容：")
        intro.setProperty("class", "stepTitle")
        layout.addWidget(intro)

        body = "\n".join(
            build_pptx_export_confirmation_body_lines(chart_ids, using_fallback=using_fallback)
        )
        detail = QTextEdit()
        detail.setReadOnly(True)
        detail.setPlainText(body)
        detail.setMinimumHeight(DIALOG_MIN_HEIGHT_STANDARD)
        detail.setProperty("class", "reportPreview")
        layout.addWidget(detail)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn is not None:
            ok_btn.setText("確認匯出")
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn is not None:
            cancel_btn.setText("取消")
        layout.addWidget(buttons)

        self.setMinimumWidth(DIALOG_MIN_WIDTH_WIDE)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        fit_top_level_to_available(
            self,
            preferred_size=(DIALOG_PPTX_CONFIRM_INIT_WIDTH, DIALOG_PPTX_CONFIRM_INIT_HEIGHT),
            fallback_size=(DIALOG_PPTX_CONFIRM_INIT_WIDTH, DIALOG_PPTX_CONFIRM_INIT_HEIGHT),
        )
