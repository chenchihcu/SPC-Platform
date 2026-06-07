import os
from importlib import import_module
from typing import Any


def _load_qt_bindings() -> tuple[Any, Any, Any]:
    try:
        qt_core = import_module("PySide6.QtCore")
        qt_widgets = import_module("PySide6.QtWidgets")
    except ImportError:
        qt_core = import_module("PySide2.QtCore")
        qt_widgets = import_module("PySide2.QtWidgets")
    return qt_core.QCoreApplication, qt_core.Qt, qt_widgets.QApplication


def setup_high_dpi() -> None:
    """
    Configure Windows-friendly high DPI behavior before QApplication is created.

    The environment variables are only set when absent so external launchers can
    still override them deliberately.
    """
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
    os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "RoundPreferFloor")

    try:
        qcore_application, qt, qapplication = _load_qt_bindings()
    except ImportError:
        return  # env vars already set; Qt attributes only needed at runtime

    # Qt5/PySide2 still relies on application attributes for DPI-aware widgets.
    # PySide6 may still expose these names but marks them deprecated; only apply
    # attributes for legacy Qt generations to avoid deprecation warnings.
    qt_major = 6
    try:
        qt_version = getattr(qt, "qVersion", lambda: "")()
        qt_major = int(str(qt_version).split(".", 1)[0]) if qt_version else 6
    except (TypeError, ValueError):
        qt_major = 6
    if qt_major < 6:
        if hasattr(qt, "AA_EnableHighDpiScaling"):
            qcore_application.setAttribute(qt.AA_EnableHighDpiScaling, True)
        if hasattr(qt, "AA_UseHighDpiPixmaps"):
            qcore_application.setAttribute(qt.AA_UseHighDpiPixmaps, True)

    if (
        hasattr(qapplication, "setHighDpiScaleFactorRoundingPolicy")
        and hasattr(qt, "HighDpiScaleFactorRoundingPolicy")
    ):
        qapplication.setHighDpiScaleFactorRoundingPolicy(
            qt.HighDpiScaleFactorRoundingPolicy.RoundPreferFloor
        )
