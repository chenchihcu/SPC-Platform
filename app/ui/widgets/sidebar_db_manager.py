"""
SidebarDbManager — 側欄並列資料庫管理面板

在展開側欄內並排顯示：
  左欄：座標檔資料庫（coordinate_registry）
  右欄：量測檔資料庫（measurement_library）

設計限制：
- 可用寬度 ≈ 180px（SIDEBAR_WIDTH_EXPANDED=220 - rail=24 - padding×2=16）
- 每欄 ≈ 88px；字體縮小至 7.5pt 以適應空間
- 不依賴 ScrollArea，列表高度使用 theme token，超出內容自動 scrollbar
"""
from __future__ import annotations

import logging
import os
from typing import List, Dict, Any, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QFileDialog, QSizePolicy,
)

from app.data.coordinate_registry import (
    list_registered,
    register as coord_register,
    remove_by_product_name,
)
from app.data.measurement_library import (
    list_measurement_sessions,
)
from app.ui.theme import show_dark_warning, show_dark_information
from app.ui.theme.tokens import (
    SIDEBAR_DB_BUTTON_HEIGHT,
    SIDEBAR_DB_LIST_MAX_HEIGHT,
    SIDEBAR_DB_PANEL_MARGIN,
    SIDEBAR_DB_PANEL_SPACING,
    SPACING_4,
    SPACING_XXS,
    UI_DIVIDER_THICKNESS,
)

_log = logging.getLogger(__name__)


def _compact_btn(label: str, tooltip: str = "") -> QPushButton:
    btn = QPushButton(label)
    btn.setProperty("density", "sidebarDb")
    btn.setFixedHeight(SIDEBAR_DB_BUTTON_HEIGHT)
    btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    if tooltip:
        btn.setToolTip(tooltip)
    return btn


# ─────────────────────────────────────────────────────────────────────────────
# 座標檔資料庫欄
# ─────────────────────────────────────────────────────────────────────────────

class _CoordDbPanel(QFrame):
    """
    左欄：已註冊座標檔清單 + 新增 / 移除 操作。
    Signals:
      coord_selected(path)  — 使用者雙擊或選取後按「載入」時發出
      registry_changed()    — 登錄表更新後通知外層刷新
    """
    coord_selected   = Signal(str)
    registry_changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)

        root = QVBoxLayout(self)
        root.setContentsMargins(
            SIDEBAR_DB_PANEL_MARGIN,
            SIDEBAR_DB_PANEL_MARGIN,
            SIDEBAR_DB_PANEL_MARGIN,
            SIDEBAR_DB_PANEL_MARGIN,
        )
        root.setSpacing(SIDEBAR_DB_PANEL_SPACING)

        # 標題
        title = QLabel("座標檔 DB")
        title.setProperty("class", "sidebarDbTitle")
        root.addWidget(title)

        # 筆數
        self._count_lbl = QLabel("0 筆")
        self._count_lbl.setProperty("class", "sidebarDbCount")
        root.addWidget(self._count_lbl)

        # 列表
        self._list = QListWidget()
        self._list.setProperty("density", "sidebarDb")
        self._list.setFixedHeight(SIDEBAR_DB_LIST_MAX_HEIGHT)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setToolTip("已登錄座標檔（產品 → 路徑）")
        self._list.itemDoubleClicked.connect(self._on_load)
        root.addWidget(self._list)

        # 按鈕列
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(SPACING_XXS)

        self._add_btn = _compact_btn("+", "選取並登錄座標 CSV")
        self._add_btn.setProperty("class", "secondary")
        self._add_btn.clicked.connect(self._on_add)
        btn_row.addWidget(self._add_btn)

        self._remove_btn = _compact_btn("✕", "移除選取的登錄項目")
        self._remove_btn.setProperty("class", "danger")
        self._remove_btn.clicked.connect(self._on_remove)
        btn_row.addWidget(self._remove_btn)

        self._load_btn = _compact_btn("↑", "載入選取的座標檔")
        self._load_btn.setProperty("class", "secondary")
        self._load_btn.clicked.connect(self._on_load)
        btn_row.addWidget(self._load_btn)

        root.addLayout(btn_row)
        self.refresh()

    # ── public ───────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """重新從登錄表載入清單。"""
        entries: List[Dict[str, Any]] = list_registered()
        self._list.clear()
        for e in entries:
            name  = (e.get("product_name") or "").strip()
            fname = os.path.basename(e.get("file_path") or "")
            text  = f"{name}" + (f"\n{fname}" if fname else "")
            item  = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, e)
            item.setToolTip(e.get("file_path") or "")
            self._list.addItem(item)
        self._count_lbl.setText(f"{len(entries)} 筆")

    # ── private slots ─────────────────────────────────────────────────────────

    def _on_add(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "選取座標 CSV", "", "CSV Files (*.csv);;All Files (*)"
        )
        if not path:
            return
        # 以檔名（去副檔名）作為預設產品名稱；使用者可在 CoordinateManagerPage 細編
        name = os.path.splitext(os.path.basename(path))[0]
        if coord_register(name, path, ""):
            self.refresh()
            self.registry_changed.emit()
            show_dark_information(self, "已登錄", f"已登錄座標：{name}")
        else:
            show_dark_warning(self, "登錄失敗", "寫入失敗，請確認權限。")

    def _on_remove(self) -> None:
        item = self._list.currentItem()
        if item is None:
            show_dark_warning(self, "請先選取", "請在清單中選取要移除的項目。")
            return
        data: Dict[str, Any] = item.data(Qt.ItemDataRole.UserRole) or {}
        name = (data.get("product_name") or "").strip()
        if not name:
            return
        if remove_by_product_name(name):
            self.refresh()
            self.registry_changed.emit()
        else:
            show_dark_warning(self, "移除失敗", "無法移除，請重試。")

    def _on_load(self) -> None:
        item = self._list.currentItem()
        if item is None:
            show_dark_warning(self, "請先選取", "請在清單中選取一個座標登錄項目。")
            return
        data: Dict[str, Any] = item.data(Qt.ItemDataRole.UserRole) or {}
        path = (data.get("file_path") or "").strip()
        if not path:
            show_dark_warning(self, "路徑為空", "此登錄項目沒有有效的路徑。")
            return
        self.coord_selected.emit(path)


# ─────────────────────────────────────────────────────────────────────────────
# 量測檔資料庫欄
# ─────────────────────────────────────────────────────────────────────────────

class _MeasDbPanel(QFrame):
    """
    右欄：量測記錄清單（最近 20 筆）+ 載入 / 刷新 操作。
    Signals:
      measurement_selected(path)  — 使用者雙擊或選取後按「載入」時發出
    """
    measurement_selected = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._sessions: List[Dict[str, Any]] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(
            SIDEBAR_DB_PANEL_MARGIN,
            SIDEBAR_DB_PANEL_MARGIN,
            SIDEBAR_DB_PANEL_MARGIN,
            SIDEBAR_DB_PANEL_MARGIN,
        )
        root.setSpacing(SIDEBAR_DB_PANEL_SPACING)

        # 標題
        title = QLabel("量測檔 DB")
        title.setProperty("class", "sidebarDbTitle")
        root.addWidget(title)

        # 筆數
        self._count_lbl = QLabel("0 筆")
        self._count_lbl.setProperty("class", "sidebarDbCount")
        root.addWidget(self._count_lbl)

        # 列表
        self._list = QListWidget()
        self._list.setProperty("density", "sidebarDb")
        self._list.setFixedHeight(SIDEBAR_DB_LIST_MAX_HEIGHT)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setToolTip("最近上傳的量測記錄（雙擊載入）")
        self._list.itemDoubleClicked.connect(self._on_load)
        root.addWidget(self._list)

        # 按鈕列
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(SPACING_XXS)

        self._refresh_btn = _compact_btn("↻", "刷新量測清單")
        self._refresh_btn.setProperty("class", "secondary")
        self._refresh_btn.clicked.connect(self.refresh)
        btn_row.addWidget(self._refresh_btn)

        self._load_btn = _compact_btn("↑", "載入選取的量測檔")
        self._load_btn.setProperty("class", "secondary")
        self._load_btn.clicked.connect(self._on_load)
        btn_row.addWidget(self._load_btn)

        root.addLayout(btn_row)
        self.refresh()

    # ── public ───────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """重新從 DB 載入最近 20 筆量測記錄。"""
        import sqlite3
        try:
            sessions = list_measurement_sessions()
        except sqlite3.Error:
            sessions = []
        # 只顯示最近 20 筆
        self._sessions = sessions[:20]
        self._list.clear()
        for s in self._sessions:
            fname = os.path.basename(str(s.get("file_path") or "—"))
            prod  = (s.get("product_name") or "").strip()
            dt    = str(s.get("upload_datetime") or "")[:10]
            text  = f"{prod}\n{fname}\n{dt}" if prod else f"{fname}\n{dt}"
            item  = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, s)
            item.setToolTip(str(s.get("file_path") or ""))
            self._list.addItem(item)
        self._count_lbl.setText(f"{len(sessions)} 筆")

    # ── private slots ─────────────────────────────────────────────────────────

    def _on_load(self) -> None:
        item = self._list.currentItem()
        if item is None:
            show_dark_warning(self, "請先選取", "請在清單中選取一筆量測記錄。")
            return
        data: Dict[str, Any] = item.data(Qt.ItemDataRole.UserRole) or {}
        path = str(data.get("file_path") or "").strip()
        if not path:
            show_dark_warning(self, "路徑為空", "此記錄沒有有效的量測檔路徑。")
            return
        if not os.path.isfile(path):
            show_dark_warning(
                self, "找不到檔案",
                f"量測檔不存在：\n{path}\n（可能已被移動或刪除）"
            )
            return
        self.measurement_selected.emit(path)


# ─────────────────────────────────────────────────────────────────────────────
# 公開複合 Widget（供 CollapsibleSidebar 使用）
# ─────────────────────────────────────────────────────────────────────────────

class SidebarDbManager(QWidget):
    """
    側欄並列資料庫管理器：
      左欄 _CoordDbPanel  │  右欄 _MeasDbPanel

    信號（供 MainWindow 連接）：
      coord_selected(path)         — 座標檔選取
      measurement_selected(path)   — 量測檔選取
      coord_registry_changed()     — 座標登錄表變更
    """

    coord_selected        = Signal(str)
    measurement_selected  = Signal(str)
    coord_registry_changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 分隔線（視覺區分上方 nav 區）
        divider = QFrame()
        divider.setObjectName("sidebarDivider")
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFixedHeight(UI_DIVIDER_THICKNESS)
        outer.addWidget(divider)

        # 並列容器
        row = QHBoxLayout()
        row.setContentsMargins(0, SPACING_4, 0, SPACING_4)
        row.setSpacing(SPACING_4)

        self._coord_panel = _CoordDbPanel()
        self._meas_panel  = _MeasDbPanel()

        # 中間垂直分割線
        vsep = QFrame()
        vsep.setFrameShape(QFrame.Shape.VLine)
        vsep.setObjectName("sidebarDivider")
        vsep.setFixedWidth(UI_DIVIDER_THICKNESS)

        row.addWidget(self._coord_panel, 1)
        row.addWidget(vsep)
        row.addWidget(self._meas_panel, 1)

        outer.addLayout(row)

        # 信號轉發
        self._coord_panel.coord_selected.connect(self.coord_selected)
        self._coord_panel.registry_changed.connect(self.coord_registry_changed)
        self._meas_panel.measurement_selected.connect(self.measurement_selected)

    # ── public API ────────────────────────────────────────────────────────────

    def refresh_coord(self) -> None:
        """刷新座標登錄清單（外部呼叫：e.g. 上傳完成後）。"""
        self._coord_panel.refresh()

    def refresh_meas(self) -> None:
        """刷新量測記錄清單（外部呼叫：e.g. 量測上傳完成後）。"""
        self._meas_panel.refresh()

    def refresh_all(self) -> None:
        """一次刷新兩欄。"""
        self._coord_panel.refresh()
        self._meas_panel.refresh()
