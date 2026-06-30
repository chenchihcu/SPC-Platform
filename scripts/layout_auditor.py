# -*- coding: utf-8 -*-
"""
Layout Auditor Core
模擬單一解析度與 DPI 縮放比例，自動執行 E2E 流程，並進行 Widget 幾何與文字截斷稽核。
"""
from __future__ import annotations

import sys
import os
import json
import argparse
from pathlib import Path

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("--out-dir", type=str, required=True)
    args = parser.parse_args()

    # 設定模擬環境變數 (必須在建立 QApplication 前)
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
    os.environ["QT_SCALE_FACTOR"] = str(args.scale)
    os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "RoundPreferFloor"
    os.environ["QT_QPA_PLATFORM"] = "offscreen"  # 無頭執行以避免干擾

    # 將專案根目錄加入路徑
    SCRIPT_DIR = Path(__file__).resolve().parent
    REPO_ROOT = SCRIPT_DIR.parent
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QComboBox, QLineEdit, QTabWidget, QWidget, QCheckBox
    from PySide6.QtCore import Qt, QRect, QTimer
    from PySide6.QtTest import QTest

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    from app.ui.main_window import MainWindow
    from app.bootstrap.font_runtime import register_qt_bundled_fonts, preferred_qt_font_family
    from app.ui.theme import apply_app_theme
    from app.ui.state.app_status_model import STATE_SUCCESS

    # 初始化字型與樣式主題
    register_qt_bundled_fonts()
    apply_app_theme(app)
    app.setFont(preferred_qt_font_family())

    w = MainWindow()
    w.resize(args.width, args.height)
    w.show()
    app.processEvents()
    QTest.qWait(500)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    audit_records = []

    def audit_current_page(page_name: str, state: str):
        """遍歷當前所有 visible widget，進行 Truncation、Overlap 與 Overflow 稽核。"""
        all_widgets = [w] + w.findChildren(QWidget)
        
        for widget in all_widgets:
            if not widget.isVisible():
                continue
            
            # 1. 檢查文字截斷 (Truncation)
            if isinstance(widget, QLabel):
                text = widget.text()
                if text and not text.isspace() and not ("<" in text and ">" in text):
                    fm = widget.fontMetrics()
                    # 取得文字寬度與高度
                    size_hint = fm.size(Qt.TextSingleLine, text)
                    # 如果 widget 寬度小於文字所需寬度 (容許 2px 誤差)
                    if not widget.wordWrap() and widget.width() < size_hint.width() - 2:
                        # 排除寬度極小 (如小於 10px) 的佔位符或折合狀態下的 minimal text
                        if widget.width() > 10:
                            audit_records.append({
                                "resolution": f"{args.width}x{args.height}",
                                "scale": args.scale,
                                "page": page_name,
                                "state": state,
                                "widget_name": widget.objectName() or widget.__class__.__name__,
                                "type": "TRUNCATION",
                                "text": text,
                                "width": widget.width(),
                                "needed": size_hint.width(),
                                "details": f"Label text '{text}' (width: {widget.width()}px) is smaller than single-line text sizeHint ({size_hint.width()}px)."
                            })
                            
            # 2. 檢查視窗底邊或右邊溢出 (Overflow)
            if any(isinstance(widget, cls) for cls in (QPushButton, QComboBox, QLineEdit, QTabWidget, QCheckBox)):
                try:
                    local_rect = widget.rect()
                    global_pos = widget.mapTo(w, local_rect.topLeft())
                    widget_in_main = QRect(global_pos.x(), global_pos.y(), widget.width(), widget.height())
                    
                    status_bar_h = 30
                    limit_y = w.height() - status_bar_h
                    if widget_in_main.bottom() > limit_y + 2:
                        audit_records.append({
                            "resolution": f"{args.width}x{args.height}",
                            "scale": args.scale,
                            "page": page_name,
                            "state": state,
                            "widget_name": widget.objectName() or widget.__class__.__name__,
                            "type": "OVERFLOW",
                            "details": f"Widget clipped at bottom of window. y={widget_in_main.bottom()} > limit={limit_y}."
                        })
                    if widget_in_main.right() > w.width() + 2:
                        audit_records.append({
                            "resolution": f"{args.width}x{args.height}",
                            "scale": args.scale,
                            "page": page_name,
                            "state": state,
                            "widget_name": widget.objectName() or widget.__class__.__name__,
                            "type": "OVERFLOW",
                            "details": f"Widget clipped at right of window. x={widget_in_main.right()} > limit={w.width()}."
                        })
                except Exception:
                    pass

        # 3. 檢查同層重疊 (Overlap)
        siblings = {}
        for widget in all_widgets:
            if not widget.isVisible() or widget.parent() is None:
                continue
            siblings.setdefault(widget.parent(), []).append(widget)
            
        for parent, widgets in siblings.items():
            n = len(widgets)
            for i in range(n):
                for j in range(i + 1, n):
                    w1 = widgets[i]
                    w2 = widgets[j]
                    w1_class = w1.__class__.__name__
                    w2_class = w2.__class__.__name__
                    
                    if any(cls in (w1_class, w2_class) for cls in ("MainWindow", "QSplitter", "QStackedWidget", "QTabWidget", "QScrollArea", "QSplitterHandle", "StatusBarWidget", "CollapsibleSidebar", "QFrame")):
                        continue
                    
                    rect1 = w1.geometry()
                    rect2 = w2.geometry()
                    if rect1.isEmpty() or rect2.isEmpty():
                        continue
                    
                    intersect = rect1.intersected(rect2)
                    if not intersect.isEmpty():
                        area = intersect.width() * intersect.height()
                        # 重疊面積顯著且非完全包含
                        if area > 100 and not (rect1.contains(rect2) or rect2.contains(rect1)):
                            audit_records.append({
                                "resolution": f"{args.width}x{args.height}",
                                "scale": args.scale,
                                "page": page_name,
                                "state": state,
                                "widget_name": f"{w1.objectName() or w1_class} vs {w2.objectName() or w2_class}",
                                "type": "OVERLAP",
                                "details": f"Widgets overlap. Intersect area: {area}px. w1: {rect1.x()},{rect1.y()},{rect1.width()}x{rect1.height()} | w2: {rect2.x()},{rect2.y()},{rect2.width()}x{rect2.height()}."
                            })

    # 定義所有要巡迴的分頁資訊 (stack_index, save_name, label_name)
    PAGES = [
        (0, "01_data_setup", "資料設定"),
        (6, "02_library", "資料庫"),
        (2, "03_charts", "統計圖表"),
        (8, "04_statistics_data", "統計資料"),
        (5, "05_diagnostic", "製程診斷"),
        (3, "06_report", "報告匯出"),
        (4, "07_reference", "說明")
    ]

    print(f"[{args.width}x{args.height} @{args.scale}x] Phase 1 & 2: 執行空狀態頁面巡迴與稽核...")
    for stack_idx, save_name, page_name in PAGES:
        w._go_to_page(stack_idx)
        app.processEvents()
        QTest.qWait(350)
        
        # 若是圖表頁，嘗試勾選可見的圖表
        if stack_idx == 2:
            try:
                chart_page = w.pages["圖表"]
                for chart_id, cb in getattr(chart_page, "_chart_id_to_checkbox", {}).items():
                    if cb and cb.isEnabled():
                        cb.setChecked(True)
            except Exception as e:
                print(f"  [圖表勾選輔助失敗]: {e}")
            app.processEvents()
            QTest.qWait(200)

        # 稽核佈局並保存截圖
        audit_current_page(page_name, "empty")
        w.grab().save(str(out_dir / f"{save_name}_empty.png"), "PNG")

    print(f"[{args.width}x{args.height} @{args.scale}x] Phase 3: 執行資料匯入與統計分析流程...")
    
    # 3-1 匯入座標資料
    coord_path = str(REPO_ROOT / "sample_data" / "coordinate" / "test_coords.csv")
    w._on_coord_uploaded(coord_path)
    # 等待座標載入完成
    for _ in range(30):
        app.processEvents()
        QTest.qWait(100)
        if getattr(w, "current_coord_path", None) == coord_path:
            break
            
    # 3-2 匯入量測資料
    meas_path = str(REPO_ROOT / "sample_data" / "measurement" / "test_meas.csv")
    w._auto_save_meas_session(meas_path)
    w.start_loading_worker(meas_path=meas_path)
    # 等待量測資料載入完成 (status_model 變為 idle 或是 load_finished)
    for _ in range(50):
        app.processEvents()
        QTest.qWait(100)
        if w.status_model.state != "loading":
            break

    # 3-3 儲存規格與工單 (藉由重新整理分析觸發)
    w.refresh_analysis()
    # 等待分析完成 (status_model.state 變為 SUCCESS)
    for _ in range(100):
        app.processEvents()
        QTest.qWait(100)
        if w.status_model.state == STATE_SUCCESS:
            break

    print(f"[{args.width}x{args.height} @{args.scale}x] Phase 3.5: 執行有資料狀態頁面巡迴與稽核...")
    for stack_idx, save_name, page_name in PAGES:
        w._go_to_page(stack_idx)
        app.processEvents()
        QTest.qWait(350)
        
        # 若是圖表頁，多特徵或單特徵切換時，確保圖表已勾選
        if stack_idx == 2:
            try:
                chart_page = w.pages["圖表"]
                for chart_id, cb in getattr(chart_page, "_chart_id_to_checkbox", {}).items():
                    if cb and cb.isEnabled():
                        cb.setChecked(True)
                app.processEvents()
                QTest.qWait(300)
            except Exception as e:
                pass
        
        # 稽核佈局並保存截圖
        audit_current_page(page_name, "with_data")
        w.grab().save(str(out_dir / f"{save_name}_with_data.png"), "PNG")

    # 保存稽核紀錄為 JSON 檔
    log_path = out_dir / "audit_log.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(audit_records, f, ensure_ascii=False, indent=2)
        
    print(f"[{args.width}x{args.height} @{args.scale}x] 完成！稽核記錄寫入至: {log_path}")
    w.close()
    app.processEvents()
    return 0

if __name__ == "__main__":
    sys.exit(main())
