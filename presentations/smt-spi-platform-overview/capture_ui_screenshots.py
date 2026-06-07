"""
於本機 GUI 環境截取主視窗各流程頁面，供簡報「產品介面」投影片使用。
需在專案根目錄已可正常啟動 PySide6 主程式（需顯示器；不支援純 SSH 無頭）。

執行（於 repo 根目錄）:
  python presentations/smt-spi-platform-overview/capture_ui_screenshots.py

或於本目錄:
  cd presentations/smt-spi-platform-overview && python capture_ui_screenshots.py

輸出: assets/ui_screens/*.png
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

OUT = SCRIPT_DIR / "assets" / "ui_screens"

# (stack_index, filename, 簡報標籤)
CAPTURE_PAGES: list[tuple[int, str, str]] = [
    (0, "01_data_setup.png", "匯入資料"),
    (1, "02_workorder.png", "工單設定"),
    (3, "03_statistics.png", "統計摘要"),
    (4, "04_charts.png", "統計圖表"),
    (2, "05_measure_select.png", "元件／量測選定"),
    (7, "06_diagnostic.png", "診斷建議"),
    (5, "07_report.png", "匯出報告"),
    (6, "08_reference.png", "參考說明"),
]


def main() -> int:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest

    OUT.mkdir(parents=True, exist_ok=True)

    app = QApplication(sys.argv)
    from app.ui.main_window import MainWindow

    w = MainWindow()
    w.resize(1360, 820)
    w.show()
    app.processEvents()
    QTest.qWait(400)

    for stack_idx, fname, _label in CAPTURE_PAGES:
        w._go_to_page(stack_idx)
        app.processEvents()
        QTest.qWait(350)
        path = OUT / fname
        ok = w.grab().save(str(path), "PNG")
        if not ok:
            print("WARN: save failed", path, file=sys.stderr)

    w.close()
    app.processEvents()
    print("Wrote UI screenshots to", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
