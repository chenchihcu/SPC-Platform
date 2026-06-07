"""Reusable interpretation dialog for chart and diagnostic guidance."""

from __future__ import annotations

import os
from typing import Any, Sequence

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.ui.theme.tokens import (
    DIALOG_INTERPRETATION_INIT_HEIGHT,
    DIALOG_INTERPRETATION_INIT_WIDTH,
    DIALOG_MIN_HEIGHT_STANDARD,
    DIALOG_MIN_WIDTH_WIDE,
    SPACING_8,
    SPACING_12,
)
from app.ui.theme.layout_policy import ensure_window_visible, fit_top_level_to_available

SectionList = Sequence[dict[str, Any]]


class InterpretationDialog(QDialog):
    """Shared dialog showing full interpretation sections for charts and diagnostics."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setModal(True)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setMinimumWidth(DIALOG_MIN_WIDTH_WIDE)
        self.setMinimumHeight(DIALOG_MIN_HEIGHT_STANDARD)
        self._post_show_geometry_clamped = False

        fit_top_level_to_available(
            self,
            preferred_size=(DIALOG_INTERPRETATION_INIT_WIDTH, DIALOG_INTERPRETATION_INIT_HEIGHT),
            fallback_size=(DIALOG_INTERPRETATION_INIT_WIDTH, DIALOG_INTERPRETATION_INIT_HEIGHT),
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_12, SPACING_12, SPACING_12, SPACING_12)
        layout.setSpacing(SPACING_8)

        self._heading_label = QLabel("")
        self._heading_label.setProperty("class", "stepTitle")
        self._heading_label.setWordWrap(True)
        layout.addWidget(self._heading_label)

        self._context_label = QLabel("")
        self._context_label.setProperty("class", "caption")
        self._context_label.setWordWrap(True)
        self._context_label.setVisible(False)
        layout.addWidget(self._context_label)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(SPACING_12)
        self._scroll.setWidget(self._content_widget)
        layout.addWidget(self._scroll, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_btn = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close_btn is not None:
            close_btn.setText("關閉")
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def showEvent(self, event) -> None:
        """Clamp native frame geometry after the dialog is shown."""
        super().showEvent(event)
        if self._post_show_geometry_clamped:
            return
        self._post_show_geometry_clamped = True
        QTimer.singleShot(0, self._fit_native_frame_visible)

    def _fit_native_frame_visible(self) -> None:
        if ensure_window_visible(self):
            return
        fit_top_level_to_available(
            self,
            preferred_size=(DIALOG_INTERPRETATION_INIT_WIDTH, DIALOG_INTERPRETATION_INIT_HEIGHT),
            fallback_size=(DIALOG_INTERPRETATION_INIT_WIDTH, DIALOG_INTERPRETATION_INIT_HEIGHT),
        )

    def _clear_sections(self) -> None:
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.setParent(None)

    def set_sections(
        self,
        *,
        window_title: str,
        heading: str,
        sections: SectionList,
        context_lines: Sequence[str] | None = None,
    ) -> None:
        """Apply title/context and render full interpretation sections."""
        self.setWindowTitle(window_title)
        self._heading_label.setText(heading)

        ctx_lines = [str(x).strip() for x in (context_lines or []) if str(x).strip()]
        self._context_label.setText("\n".join(ctx_lines))
        self._context_label.setVisible(bool(ctx_lines))

        self._clear_sections()
        
        # Base path for illustrations (app/assets/illustrations)
        # Resolved relative to this file: ./../../assets/illustrations
        base_assets = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "assets", "illustrations")
        )

        for section in sections:
            title_text = str(section.get("title") or "").strip()
            icon = str(section.get("icon") or "").strip()
            body_text = str(section.get("body") or "—").strip() or "—"
            illustration = str(section.get("illustration") or "").strip()

            # Section Title with Icon
            title_final = f"{icon} {title_text}" if icon else title_text
            section_title = QLabel(title_final)
            section_title.setProperty("class", "sectionTitle")
            section_title.setWordWrap(True)
            self._content_layout.addWidget(section_title)

            # Horizontal divider
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setFrameShadow(QFrame.Shadow.Plain)
            line.setProperty("class", "divider")
            self._content_layout.addWidget(line)

            # Per-section Illustration — prefer live QPixmap, fall back to file path
            raw_pixmap = section.get("illustration_pixmap")
            pixmap = raw_pixmap if isinstance(raw_pixmap, QPixmap) else None
            if pixmap is None and illustration:
                img_path = os.path.join(base_assets, illustration)
                pixmap = QPixmap(img_path)
                if pixmap.isNull():
                    pixmap = None
            if pixmap is not None and not pixmap.isNull():
                ill_label = QLabel()
                ill_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                ill_label.setProperty("class", "interpretationIllustration")
                # Scale to fit width while maintaining aspect ratio
                scaled = pixmap.scaledToWidth(self.width() - 80, Qt.TransformationMode.SmoothTransformation)
                ill_label.setPixmap(scaled)
                self._content_layout.addWidget(ill_label)

            # Body with Rich Text support
            if "\n" in body_text and "<" not in body_text:
                body_html = body_text.replace("\n", "<br>")
            else:
                body_html = body_text

            section_body = QLabel(body_html)
            section_body.setProperty("class", "reportPreview")
            section_body.setWordWrap(True)
            section_body.setTextFormat(Qt.TextFormat.RichText)
            section_body.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
                | Qt.TextInteractionFlag.TextSelectableByKeyboard
            )
            self._content_layout.addWidget(section_body)

        self._content_layout.addStretch(1)

    def open_for_chart(
        self,
        *,
        chart_name: str,
        sections: SectionList,
        context_lines: Sequence[str] | None = None,
    ) -> int:
        """Open the dialog for one chart interpretation."""
        self.set_sections(
            window_title=f"{chart_name}｜圖表解讀",
            heading=f"{chart_name} - 完整解讀",
            sections=sections,
            context_lines=context_lines,
        )
        return self.exec()

    def open_for_diagnostic(
        self,
        *,
        sections: SectionList,
        context_lines: Sequence[str] | None = None,
    ) -> int:
        """Open the dialog for diagnostic dashboard interpretation."""
        self.set_sections(
            window_title="製程診斷｜指標解讀",
            heading="製程診斷儀表板 - 指標解讀",
            sections=sections,
            context_lines=context_lines,
        )
        return self.exec()
