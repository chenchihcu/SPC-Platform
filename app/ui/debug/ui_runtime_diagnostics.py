from __future__ import annotations

import os
import sys
from typing import Any

from PySide6.QtCore import QRect
from PySide6.QtWidgets import QFrame, QMainWindow, QWidget

from app.bootstrap.app_config import APP_VERSION
from app.ui.pages.data_setup_page import DataSetupPage
from app.utils.logger import get_logger

logger = get_logger(__name__)
_DIAGNOSTIC_ENV = "SPC_UI_DIAGNOSTICS"
_TRUTHY = {"1", "true", "yes", "on"}


def ui_diagnostics_enabled() -> bool:
    return os.environ.get(_DIAGNOSTIC_ENV, "").strip().lower() in _TRUTHY


def _rect_dict(rect: QRect) -> dict[str, int]:
    return {"x": rect.x(), "y": rect.y(), "width": rect.width(), "height": rect.height()}


def build_ui_diagnostics_snapshot(window: QMainWindow) -> dict[str, Any]:
    screen = window.screen()
    central = window.centralWidget()
    workspace = getattr(window, "workspace", None)
    data_page = getattr(getattr(window, "pages", {}), "get", lambda *_: None)("資料")
    data_setup = data_page if isinstance(data_page, DataSetupPage) else None

    snapshot: dict[str, Any] = {
        "app_version": APP_VERSION,
        "argv0": sys.argv[0] if sys.argv else "",
        "cwd": os.getcwd(),
        "python_executable": sys.executable,
        "dpi_env": {
            "QT_ENABLE_HIGHDPI_SCALING": os.environ.get("QT_ENABLE_HIGHDPI_SCALING", ""),
            "QT_AUTO_SCREEN_SCALE_FACTOR": os.environ.get("QT_AUTO_SCREEN_SCALE_FACTOR", ""),
            "QT_SCALE_FACTOR": os.environ.get("QT_SCALE_FACTOR", ""),
            "QT_SCALE_FACTOR_ROUNDING_POLICY": os.environ.get("QT_SCALE_FACTOR_ROUNDING_POLICY", ""),
        },
        "main_window": _rect_dict(window.geometry()),
        "central_widget": _rect_dict(central.geometry()) if central is not None else None,
        "workspace": _rect_dict(workspace.geometry()) if isinstance(workspace, QWidget) else None,
        "screen": None,
        "data_setup": None,
    }
    if screen is not None:
        snapshot["screen"] = {
            "name": screen.name(),
            "device_pixel_ratio": screen.devicePixelRatio(),
            "logical_dpi_x": screen.logicalDotsPerInchX(),
            "logical_dpi_y": screen.logicalDotsPerInchY(),
            "available_geometry": _rect_dict(screen.availableGeometry()),
        }
    if data_setup is not None:
        page_inner_width = getattr(data_setup, "_diagnostic_page_inner_width", data_setup.width())
        content_host_width = getattr(data_setup, "_diagnostic_content_host_width", data_setup._content_host.width())
        available_w = getattr(data_setup, "_diagnostic_available_width", max(page_inner_width, content_host_width))
        cards = []
        for card in data_setup.findChildren(QFrame):
            if card.objectName() in {"stepCard", "controlCard"}:
                cards.append(
                    {
                        "object_name": card.objectName(),
                        "parent": type(card.parentWidget()).__name__ if card.parentWidget() is not None else "",
                        "geometry": _rect_dict(card.geometry()),
                    }
                )
        snapshot["data_setup"] = {
            "geometry": _rect_dict(data_setup.geometry()),
            "tier": getattr(data_setup, "_current_tier", None),
            "layout_budget": data_setup.latest_layout_budget().to_dict(),
            "page_inner_width": page_inner_width,
            "content_host_width": content_host_width,
            "available_w": available_w,
            "coord_geometry": _rect_dict(data_setup._coord_page.geometry()),
            "stencil_geometry": _rect_dict(data_setup._stencil_editor.geometry()),
            "upload_geometry": _rect_dict(data_setup._upload_page.geometry()),
            "coord_size_hint": {
                "width": data_setup._coord_page.sizeHint().width(),
                "height": data_setup._coord_page.sizeHint().height(),
            },
            "stencil_size_hint": {
                "width": data_setup._stencil_editor.sizeHint().width(),
                "height": data_setup._stencil_editor.sizeHint().height(),
            },
            "upload_size_hint": {
                "width": data_setup._upload_page.sizeHint().width(),
                "height": data_setup._upload_page.sizeHint().height(),
            },
            "cards": cards,
        }
    return snapshot


def log_ui_diagnostics(window: QMainWindow, reason: str = "startup") -> None:
    snapshot = build_ui_diagnostics_snapshot(window)
    logger.info("ui_diagnostics[%s]=%s", reason, snapshot)
