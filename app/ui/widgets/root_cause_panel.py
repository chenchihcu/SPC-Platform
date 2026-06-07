"""
RootCausePanel: 根本原因推斷提示面板
顯示基於 SMT 工藝模式的診斷建議，整合 RunChart、Spatial、Boxplot 分析。
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QApplication, QMenu
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from app.analytics.root_cause_engine import infer_root_cause_hints
from app.ui.theme.tokens import SPACING_SM, SEVERITY_LABEL_MIN_W


class RootCauseHintCard(QFrame):
    """單個根本原因提示卡片，右鍵可複製診斷內容。"""

    hint_clicked = Signal(str)

    def __init__(self, hint_dict: dict, parent=None):
        super().__init__(parent)
        self.rule_id = hint_dict.get("rule_id", "unknown")
        self.severity = hint_dict.get("severity", "info")
        self._hint_text = hint_dict.get("hint", "")

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setLineWidth(1)
        self.setProperty("class", f"hint-card hint-{self.severity}")
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)
        layout.setSpacing(SPACING_SM)

        severity_label = QLabel()
        if self.severity == "error":
            severity_label.setText("🔴 致命")
            severity_label.setProperty("class", "hintSeverityError")
        elif self.severity == "warning":
            severity_label.setText("🟡 警告")
            severity_label.setProperty("class", "hintSeverityWarning")
        else:
            severity_label.setText("ℹ️ 提示")
            severity_label.setProperty("class", "hintSeverityInfo")

        severity_label.setMinimumWidth(SEVERITY_LABEL_MIN_W)
        layout.addWidget(severity_label)

        hint_label = QLabel(self._hint_text)
        hint_label.setWordWrap(True)
        hint_label.setProperty("class", "hintMainText")
        layout.addWidget(hint_label, 1)

        evidence = hint_dict.get("evidence", {}) if isinstance(hint_dict.get("evidence"), dict) else {}
        ipc_refs = hint_dict.get("ipc_refs", []) if isinstance(hint_dict.get("ipc_refs"), list) else []
        confidence = hint_dict.get("confidence")
        priority = hint_dict.get("priority")
        details: list[str] = []
        if evidence:
            threshold = evidence.get("threshold")
            if threshold:
                details.append(f"證據門檻: {threshold}")
        if confidence is not None:
            try:
                details.append(f"可信度: {float(confidence):.0%}")
            except (TypeError, ValueError):
                details.append(f"可信度: {confidence}")
        if priority:
            details.append(f"優先級: {priority}")
        if ipc_refs:
            first_ref = ipc_refs[0] if isinstance(ipc_refs[0], dict) else {}
            std = first_ref.get("std", "")
            edition = first_ref.get("edition", "")
            clause = first_ref.get("clause", "")
            summary_zh = first_ref.get("summary_zh", "")
            details.append(f"IPC 依據: [{std}-{edition}] {clause} {summary_zh}".strip())

        if details:
            detail_label = QLabel(" | ".join(details))
            detail_label.setWordWrap(True)
            detail_label.setProperty("class", "hintDetailText")
            layout.addWidget(detail_label, 1)

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        copy_action = QAction("複製診斷", self)
        copy_action.triggered.connect(self._copy_hint)
        menu.addAction(copy_action)
        menu.exec(self.mapToGlobal(pos))

    def _copy_hint(self):
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self._hint_text)


class RootCausePanel(QWidget):
    """
    根本原因推斷面板
    顯示基於分析結果的診斷建議列表
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "root-cause-panel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)
        layout.setSpacing(SPACING_SM)

        title = QLabel("🔍 製程診斷建議")
        title.setProperty("class", "rootCauseTitle")
        layout.addWidget(title)

        self._hints_layout = QVBoxLayout()
        self._hints_layout.setSpacing(SPACING_SM)
        self._hints_layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(self._hints_layout, 1)

        self._last_payload = {}

    def update_hints(self, payload: dict) -> None:
        """
        根據分析 payload 更新提示

        Args:
            payload: 完整的分析結果 payload（包含 run_chart、spatial、box 等）
        """
        self._last_payload = payload or {}

        while self._hints_layout.count() > 0:
            item = self._hints_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        hints = infer_root_cause_hints(payload)

        if not hints:
            no_hint = QLabel("✓ 製程正常，無異常偵測")
            no_hint.setProperty("class", "rootCauseEmpty")
            no_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._hints_layout.addWidget(no_hint)
        else:
            severity_order = {"error": 0, "warning": 1, "info": 2}
            hints.sort(key=lambda h: severity_order.get(h.get("severity", "info"), 2))

            for hint in hints:
                card = RootCauseHintCard(hint, self)
                self._hints_layout.addWidget(card)

        self._hints_layout.addStretch()
