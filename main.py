from __future__ import annotations

import importlib.util
import os
import sys
from typing import Callable, Any

from app.bootstrap.runtime_env import ensure_home_env

_REQUIRED_MODULES: tuple[str, ...] = (
    "app.ui.pages.diagnostic_page",
)


def _runtime_context_lines() -> list[str]:
    return [
        f"python_executable={sys.executable}",
        f"python_version={sys.version.split()[0]}",
        f"cwd={os.getcwd()}",
        f"script_dir={os.path.dirname(os.path.abspath(__file__))}",
    ]


def _missing_required_modules() -> list[str]:
    missing: list[str] = []
    for module_name in _REQUIRED_MODULES:
        if importlib.util.find_spec(module_name) is None:
            missing.append(module_name)
    return missing


def _load_run_app() -> Callable[[Any], None]:
    from app.ui.main_window import run_app

    return run_app


def _print_startup_error(title: str, details: list[str]) -> None:
    print(title, file=sys.stderr)
    for line in details:
        print(f" - {line}", file=sys.stderr)


# Define styled splash screen to replace the black window delay
# Inheriting QSplashScreen needs PySide6.QtWidgets
# We import inside or wrap in try/except to prevent import failures from blocking standard exit
try:
    from PySide6.QtWidgets import QSplashScreen
    
    class ElectricSplash(QSplashScreen):
        def __init__(self) -> None:
            from PySide6.QtGui import QPixmap
            # 建立一個成員變數保存 pixmap，確保 painter 繪圖後能手動觸發顯示快取重繪
            self.splash_pixmap = QPixmap(600, 380)
            super().__init__(self.splash_pixmap)
            self.progress = 0
            self.status_msg = "正在初始化系統..."
            self._update_splash_pixmap()
            
        def set_progress(self, val: int, msg: str) -> None:
            self.progress = val
            self.status_msg = msg
            self._update_splash_pixmap()
            
        def _update_splash_pixmap(self) -> None:
            from PySide6.QtGui import QPainter, QLinearGradient, QColor, QFont, QPen
            from PySide6.QtCore import Qt, QRect
            from app.bootstrap.font_runtime import preferred_qt_font_family
            
            # 清除舊內容以防殘留
            self.splash_pixmap.fill(Qt.transparent)
            
            painter = QPainter(self.splash_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 1. 繪製 Electric Blue 科技感漸層背景
            gradient = QLinearGradient(0, 0, 600, 380)
            gradient.setColorAt(0, QColor("#101B35"))  # 深邃科技藍底
            gradient.setColorAt(1, QColor("#1D4ED8"))  # 電光藍
            painter.setBrush(gradient)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(0, 0, 600, 380, 12, 12)
            
            # 2. 繪製精緻邊框
            border_pen = QPen(QColor("#2563EB"), 1.5)
            painter.setPen(border_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(1, 1, 598, 378, 12, 12)
            
            # 3. 取得 UI 字型
            try:
                font_family = preferred_qt_font_family()
            except Exception:
                font_family = "Noto Sans TC"
                
            # 4. 繪製標題與副標題
            title_font = QFont(font_family, 24)
            title_font.setBold(True)
            painter.setFont(title_font)
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(QRect(40, 60, 520, 50), Qt.AlignLeft | Qt.AlignVCenter, "SPC 統計分析平台")
            
            sub_font = QFont(font_family, 10)
            painter.setFont(sub_font)
            painter.setPen(QColor("#93C5FD"))  # 亮天藍
            painter.drawText(QRect(40, 110, 520, 24), Qt.AlignLeft | Qt.AlignVCenter, "Statistical Process Control Platform")
            
            # 5. 裝飾線條
            deco_pen = QPen(QColor("rgba(147, 197, 253, 0.15)"), 1)
            painter.setPen(deco_pen)
            for i in range(4):
                painter.drawLine(40, 152 + i*6, 560, 152 + i*6)
                
            # 6. 進度與狀態字串
            status_font = QFont(font_family, 10)
            painter.setFont(status_font)
            painter.setPen(QColor("#DBEAFE"))  # 淡天藍
            painter.drawText(QRect(40, 260, 520, 24), Qt.AlignLeft | Qt.AlignVCenter, self.status_msg)
            
            # 7. 進度條繪製
            bar_x, bar_y, bar_w, bar_h = 40, 290, 520, 5
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("rgba(255, 255, 255, 0.1)"))
            painter.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 2.5, 2.5)
            
            if self.progress > 0:
                progress_w = int(bar_w * (self.progress / 100))
                prog_grad = QLinearGradient(bar_x, bar_y, bar_x + progress_w, bar_y)
                prog_grad.setColorAt(0, QColor("#60A5FA"))  # 亮藍
                prog_grad.setColorAt(1, QColor("#34D399"))  # 漸層到綠
                painter.setBrush(prog_grad)
                painter.drawRoundedRect(bar_x, bar_y, progress_w, bar_h, 2.5, 2.5)
                
            # 8. 版本與版權資訊
            version_font = QFont(font_family, 8)
            painter.setFont(version_font)
            painter.setPen(QColor("rgba(219, 234, 254, 0.5)"))
            painter.drawText(QRect(40, 320, 260, 20), Qt.AlignLeft | Qt.AlignVCenter, "v2.0.0")
            painter.drawText(QRect(300, 320, 260, 20), Qt.AlignRight | Qt.AlignVCenter, "© 2026 SPC Platform Group")
            
            painter.end()
            
            # CRITICAL: 必須調用 setPixmap 重新覆蓋顯示緩衝, 否則視窗內容將無法重新繪製 (呈現全黑一片)
            self.setPixmap(self.splash_pixmap)

except ImportError:
    ElectricSplash = None  # type: ignore


def main() -> int:
    ensure_home_env()

    missing_modules = _missing_required_modules()
    if missing_modules:
        _print_startup_error(
            "Startup preflight failed: required modules are missing.",
            [f"missing_module={name}" for name in missing_modules]
            + _runtime_context_lines()
            + ["hint=Run from repository root and verify file copy integrity."],
        )
        return 1

    # Check for offscreen execution
    is_offscreen = os.environ.get("QT_QPA_PLATFORM") == "offscreen"
    
    splash = None
    app = None
    
    # 1. Early QApplication & QSplashScreen initialization
    if not is_offscreen and ElectricSplash is not None:
        try:
            from PySide6.QtWidgets import QApplication
            from app.bootstrap.dpi import setup_high_dpi
            setup_high_dpi()
            app = QApplication.instance()
            if not app:
                app = QApplication(sys.argv)
            
            splash = ElectricSplash()
            splash.show()
            splash.set_progress(15, "正在載入數據科學模組 (Pandas, Numpy)...")
            app.processEvents()
        except Exception as e:
            print(f"Warning: Failed to initialize splash screen: {e}", file=sys.stderr)

    # 2. Module loading phase (with splash updates)
    if splash and app:
        splash.set_progress(45, "正在載入統計分析核心 (Matplotlib, Scipy)...")
        app.processEvents()

    try:
        run_app = _load_run_app()
    except ModuleNotFoundError as exc:
        if splash:
            splash.close()
        _print_startup_error(
            "Startup import failed (ModuleNotFoundError).",
            [f"exception={exc}"]
            + _runtime_context_lines()
            + ["hint=Check interpreter/environment and repository path consistency."],
        )
        return 1

    # 3. Handover splash to main application execution
    import inspect
    try:
        sig = inspect.signature(run_app)
        if len(sig.parameters) > 0 or any(p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD) for p in sig.parameters.values()):
            run_app(splash)
        else:
            run_app()
    except Exception:
        try:
            run_app(splash)
        except TypeError:
            run_app()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

