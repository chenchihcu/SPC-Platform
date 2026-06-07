> [DEPRECATED] Historical snapshot only. Do not use as current specification.
> Reason: Stage integration summary; keep for traceability only.

# 主畫面 UI 整合修改摘要（字體可讀性 + 版面平衡 + 色彩系統統一）

本文檔彙整三類已完成的修改：字體可讀性與元件高度、版面空白與 layout 平衡、主畫面色彩系統統一。供釋出說明、回歸測試與後續頁面沿用 theme/token 參考。

---

## 1. 完整修改檔案清單

| 序 | 檔案路徑 | 涉及修改類型 |
|----|----------|----------------|
| 1 | `app/ui/theme/tokens.py` | 字體可讀性、版面、色彩 |
| 2 | `app/ui/theme/dark_stylesheet.py` | 字體可讀性、色彩 |
| 3 | `app/ui/widgets/control_panel.py` | 字體可讀性、版面 |
| 4 | `app/ui/widgets/collapsible_sidebar.py` | 版面 |
| 5 | `app/ui/widgets/navigation_panel.py` | 版面 |
| 6 | `app/ui/pages/workorder_page.py` | 版面 |
| 7 | `app/ui/pages/component_select_page.py` | 版面 |
| 8 | `app/ui/pages/data_upload_page.py` | 字體/空狀態 token（沿用） |
| 9 | `app/ui/pages/coordinate_manager_page.py` | 空狀態 token（沿用） |
| 10 | `app/ui/tabs/normality_tab.py` | 色彩 |

**未新增** theme.py / styles.py；色彩與版面皆集中於既有 `tokens.py` + `dark_stylesheet.py`。

---

## 2. 每個檔案修改摘要

### 2.1 app/ui/theme/tokens.py

- **字體可讀性**：新增 `SIDEBAR_CONTENT_FONT_SIZE=11`、`SIDEBAR_SECTION_TITLE_FONT_SIZE=14`、`CONTROL_CONDITION_GROUP_MIN_HEIGHT=200`、`CONTROL_STATUS_GROUP_MIN_HEIGHT=150`、`CONTROL_STATUS_LINE_MIN_HEIGHT=22`、`CONTROL_FORM_ROW_SPACING=10`、`GROUPBOX_TITLE_MARGIN_TOP=14`；空狀態文案 `EMPTY_MEAS_FILE`、`EMPTY_COORD_SET`。
- **版面**：`SIDEBAR_NAV_MIN_HEIGHT` 由 300 改為 0（導航依內容高度）。
- **色彩**：頂部註解補充 color roles 與狀態規則；新增 `BG_BLOCK_ALT`、`SURFACE_HOVER`、`SURFACE_ACTIVE`、`TEXT_ON_ACCENT`、`BORDER_HOVER`、`SCROLLBAR_HANDLE`、`SCROLLBAR_HANDLE_HOVER`、`ACCENT_PRIMARY_HOVER`、`ACCENT_SUCCESS_HOVER`、`ACCENT_ERROR_HOVER`；`ACCENT_PRIMARY` 改為低飽和藍綠 `#256b6b`。

### 2.2 app/ui/theme/dark_stylesheet.py

- **字體可讀性**：QGroupBox 使用 `GROUPBOX_TITLE_MARGIN_TOP`、::title padding；QFormLayout QLabel 與 status-ok/status-error 使用 `SIDEBAR_CONTENT_FONT_SIZE`、`CONTROL_STATUS_LINE_MIN_HEIGHT`；QComboBox min-height 26px。
- **色彩**：import 所有新 token；QPushButton hover/pressed 改為 `SURFACE_HOVER`/`BORDER_HOVER`、`SURFACE_ACTIVE`；primary/success/error 按鈕與 hover 改為對應 ACCENT_* 與 `TEXT_ON_ACCENT`；QTableView alternate/selected、QTabBar、QListWidget、navStepBtn、ScrollBar、Splitter、workorderSaveBtn 之硬編碼 hex 全改為 token。

### 2.3 app/ui/widgets/control_panel.py

- **字體可讀性**：base_font 使用 `SIDEBAR_CONTENT_FONT_SIZE`；`form.setVerticalSpacing(CONTROL_FORM_ROW_SPACING)`；cond_box/status_box `setMinimumHeight(CONTROL_*_MIN_HEIGHT)`；status 行距 `SPACING_SM`；每個 status QLabel `setMinimumHeight(CONTROL_STATUS_LINE_MIN_HEIGHT)`；狀態列以 class `status-ok`/`status-error` 交由 QSS 著色。
- **版面**：移除 `root_layout.addStretch(1)`。

### 2.4 app/ui/widgets/collapsible_sidebar.py

- **版面**：`content_layout.addWidget(self._control_panel, 1)`（stretch factor 1），移除 `content_layout.addStretch(1)`；導航區仍 `setMinimumHeight(SIDEBAR_NAV_MIN_HEIGHT)`（現為 0）。

### 2.5 app/ui/widgets/navigation_panel.py

- **版面**：移除每個 phase 欄內 `col_layout.addStretch(1)`，導航高度改為依內容。

### 2.6 app/ui/pages/workorder_page.py

- **版面**：import `SPACING_MD`；`layout.addStretch()` 改為 `layout.addSpacing(SPACING_MD)`。

### 2.7 app/ui/pages/component_select_page.py

- **版面**：import `SPACING_MD`；`layout.addStretch()` 改為 `layout.addSpacing(SPACING_MD)`。

### 2.8 app/ui/pages/data_upload_page.py

- 使用 `EMPTY_MEAS_FILE` 顯示「目前檔案路徑」空狀態；依賴 tokens 的 SPACING_*（與本次整合一致）。

### 2.9 app/ui/pages/coordinate_manager_page.py

- 使用 `EMPTY_COORD_SET` 顯示「目前載入座標集合」空狀態。

### 2.10 app/ui/tabs/normality_tab.py

- **色彩**：import `ACCENT_SUCCESS`；結論文字顏色由硬編碼 `#2e7d32`/`#c62828` 改為 `ACCENT_SUCCESS`/`ACCENT_ERROR`。

---

## 3. 最終 diff-style patch（依檔案彙總）

以下為相對於「三類修改前」的整體變更摘要，便於 code review 與還原對照。

### tokens.py

```diff
+ Color roles / states 註解
  # Backgrounds
  BG_PRIMARY = "#1e1e1e"
  BG_SECONDARY = "#2d2d2d"
  BG_BLOCK = "#252525"
+ BG_BLOCK_ALT = "#2a2a2a"
+ SURFACE_HOVER = "#3d3d3d"
+ SURFACE_ACTIVE = "#353535"
  # Text
  TEXT_PRIMARY = "#e8e8e8"
  TEXT_SECONDARY = "#b0b0b0"
  TEXT_MUTED = "#808080"
+ TEXT_ON_ACCENT = "#ffffff"
  # Accent
- ACCENT_PRIMARY = "#1e88e5"
+ ACCENT_PRIMARY = "#256b6b"
+ ACCENT_PRIMARY_HOVER = "#2f7a7a"
  ACCENT_SUCCESS = "#2e7d32"
+ ACCENT_SUCCESS_HOVER = "#388E3C"
  ACCENT_ERROR = "#c62828"
+ ACCENT_ERROR_HOVER = "#b71c1c"
  # Border
  BORDER = "#404040"
+ BORDER_HOVER = "#505050"
+ SCROLLBAR_HANDLE = "#505050"
+ SCROLLBAR_HANDLE_HOVER = "#606060"
  # Navigation (unchanged NAV_PHASE_* / NAV_STEP_*)
- SIDEBAR_NAV_MIN_HEIGHT = 300
+ SIDEBAR_NAV_MIN_HEIGHT = 0
+ CONTROL_CONDITION_GROUP_MIN_HEIGHT = 200
+ CONTROL_STATUS_GROUP_MIN_HEIGHT = 150
+ CONTROL_STATUS_LINE_MIN_HEIGHT = 22
+ CONTROL_FORM_ROW_SPACING = 10
+ GROUPBOX_TITLE_MARGIN_TOP = 14
  # Typography
+ SIDEBAR_CONTENT_FONT_SIZE = 11
  SIDEBAR_SECTION_TITLE_FONT_SIZE = 14  (was 12)
+ EMPTY_MEAS_FILE = "尚未載入檔案"
+ EMPTY_COORD_SET = "(無)"
```

### dark_stylesheet.py

```diff
  from app.ui.theme.tokens import (
      BG_PRIMARY, BG_SECONDARY, BG_BLOCK,
+     BG_BLOCK_ALT, SURFACE_HOVER, SURFACE_ACTIVE,
+     TEXT_ON_ACCENT, ACCENT_PRIMARY_HOVER, ACCENT_SUCCESS_HOVER, ACCENT_ERROR_HOVER,
+     BORDER_HOVER, SCROLLBAR_HANDLE, SCROLLBAR_HANDLE_HOVER,
      ...
  )
  QPushButton:hover { background-color: {SURFACE_HOVER}; border-color: {BORDER_HOVER}; }
  QPushButton:pressed { background-color: {SURFACE_ACTIVE}; }
  QPushButton#refreshBtn, [class="primary"] { color: {TEXT_ON_ACCENT}; }
  QPushButton#refreshBtn:hover { background-color: {ACCENT_PRIMARY_HOVER}; ... }
  QPushButton#nextStepBtn:hover { background-color: {ACCENT_SUCCESS_HOVER}; ... }
  QPushButton#dangerBtn:hover { background-color: {ACCENT_ERROR_HOVER}; ... }
  QComboBox:hover { border-color: {BORDER_HOVER}; }
  QGroupBox { margin-top: {GROUPBOX_TITLE_MARGIN_TOP}px; ... }
  QFormLayout QLabel { font-size: {SIDEBAR_CONTENT_FONT_SIZE}px; min-height: {CONTROL_STATUS_LINE_MIN_HEIGHT}px; }
  QLabel[class="status-ok"], [class="status-error"] { font-size, min-height, padding }
  QTableView::item:alternate { background-color: {BG_BLOCK_ALT}; }
  QTableView::item:selected { color: {TEXT_ON_ACCENT}; }
  QTabBar::tab:hover:!selected { background-color: {SURFACE_ACTIVE}; }
  QListWidget::item:hover { background-color: {SURFACE_ACTIVE}; }
  QListWidget::item:selected { background-color: {SURFACE_HOVER}; }
  QPushButton#navStepBtn:hover, [isCurrent="true"] { color: {TEXT_ON_ACCENT}; }
  QScrollBar::handle { background-color: {SCROLLBAR_HANDLE}; }
  QScrollBar::handle:hover { background-color: {SCROLLBAR_HANDLE_HOVER}; }
  QSplitter::handle:hover { background-color: {BORDER_HOVER}; }
  QPushButton#workorderSaveBtn[saveState="success|failure"] { color: {TEXT_ON_ACCENT}; }
```

### control_panel.py

```diff
  from app.ui.theme.tokens import (
+     SIDEBAR_CONTENT_FONT_SIZE, CONTROL_CONDITION_GROUP_MIN_HEIGHT,
+     CONTROL_STATUS_GROUP_MIN_HEIGHT, CONTROL_STATUS_LINE_MIN_HEIGHT, CONTROL_FORM_ROW_SPACING,
      ...
  )
  base_font = QFont(..., SIDEBAR_CONTENT_FONT_SIZE)
  form.setVerticalSpacing(CONTROL_FORM_ROW_SPACING)
  cond_box.setMinimumHeight(CONTROL_CONDITION_GROUP_MIN_HEIGHT)
  status_layout.setSpacing(SPACING_SM)
  for lbl in status_labels: lbl.setMinimumHeight(CONTROL_STATUS_LINE_MIN_HEIGHT)
  status_box.setMinimumHeight(CONTROL_STATUS_GROUP_MIN_HEIGHT)
  root_layout.addLayout(button_layout)
  root_layout.addSpacing(SPACING_MD)
- root_layout.addStretch(1)
```

### collapsible_sidebar.py

```diff
  content_layout.addWidget(self._nav)
  self._control_panel = ControlPanel()
  self._control_panel.setMinimumWidth(0)
- content_layout.addWidget(self._control_panel)
- content_layout.addStretch(1)
+ content_layout.addWidget(self._control_panel, 1)
```

### navigation_panel.py

```diff
              col_layout.addWidget(btn)
              stack_idx += 1
-             col_layout.addStretch(1)
              root.addWidget(column, 1)
```

### workorder_page.py

```diff
- from app.ui.theme.tokens import SIDEBAR_BUTTON_MIN_HEIGHT
+ from app.ui.theme.tokens import SIDEBAR_BUTTON_MIN_HEIGHT, SPACING_MD
  layout.addWidget(self.btn_save)
- layout.addStretch()
+ layout.addSpacing(SPACING_MD)
```

### component_select_page.py

```diff
+ from app.ui.theme.tokens import SPACING_MD
  layout.addWidget(group)
- layout.addStretch()
+ layout.addSpacing(SPACING_MD)
```

### normality_tab.py

```diff
- from app.ui.theme.tokens import ACCENT_PRIMARY, ACCENT_ERROR, TEXT_PRIMARY
+ from app.ui.theme.tokens import ACCENT_PRIMARY, ACCENT_SUCCESS, ACCENT_ERROR, TEXT_PRIMARY
  ...
- result_color = "#2e7d32" if is_normal else "#c62828"
+ result_color = ACCENT_SUCCESS if is_normal else ACCENT_ERROR
```

---

## 4. 風險清單（可能影響其他頁面之處）

| 風險項 | 說明 | 影響範圍 | 建議 |
|--------|------|----------|------|
| 全域 QSS | `get_dark_stylesheet()` 套用於整個 QApplication，所有 QPushButton、QComboBox、QGroupBox、QTableView 等皆受新 token 影響 | 所有使用同一 stylesheet 的視窗與頁面 | 若某頁有特殊樣式，可透過 objectName 或 class property 覆寫 |
| ACCENT_PRIMARY 改色 | 主色由藍 #1e88e5 改為藍綠 #256b6b，所有依賴主色的焦點框、主按鈕、選取色一併改變 | 主畫面、圖表（如 normality_tab 的 scatter）、任何使用 ACCENT_PRIMARY 的元件 | 已一併改 normality_tab；其他引用 ACCENT_PRIMARY 的圖表/自繪需目視確認 |
| 導航區無固定最小高度 | SIDEBAR_NAV_MIN_HEIGHT=0，極端高 DPI 或字體放大時導航區可能被壓得很扁 | 僅左側導航 | 若實機過扁可改回 160～180 |
| 控制區 stretch 1 | 左欄多餘高度全部分配給控制區，控制區變高時空白落在按鈕下方 | 僅左欄控制區 | 可接受；若需「按鈕貼底」可再調整 |
| workorder / component_select 底部 | 由 addStretch 改為 addSpacing(SPACING_MD)，頁面拉高時底部留白行為改變 | 工單頁、元件選定頁 | 屬預期，減少無意義空白 |
| 字級與 min-height | SIDEBAR_CONTENT_FONT_SIZE、CONTROL_*_MIN_HEIGHT 僅用於 control_panel 與 QSS 對應選擇器；其他頁面若自設字級不受影響 | 分析條件／資料狀態區與使用相同 QSS 選擇器的元件 | 無需改動其他頁面 |
| EMPTY_MEAS_FILE / EMPTY_COORD_SET | 僅為字串常數，用於 data_upload_page、coordinate_manager_page 顯示 | 資料上傳、座標管理頁 | 其他頁面若需相同文案可從 tokens 引入 |

---

## 5. 回歸測試清單

- [ ] **主畫面啟動**：應用程式啟動後主視窗正常顯示，左欄導航 + 控制區、右欄 stacked 頁面無報錯。
- [ ] **左欄：字體可讀性**：分析條件、資料狀態兩區塊內文字完整可讀，無裁切、重疊或上下貼邊；section 標題（14px）明顯大於內容（11px）；125% / 150% DPI 下再驗一次。
- [ ] **左欄：版面**：上方功能卡區與下方資訊區之間無大塊空白；導航區高度隨內容變化；控制區下方「重新整理」「下一步驟」與兩區塊相對位置合理；視窗拉高時多餘空間在控制區底部，不造成重疊或異常捲動。
- [ ] **左欄：色彩**：一般按鈕 hover/pressed 有明顯變化；重新整理（主操作）為藍綠色、下一步為綠色；選中導航步驟有邊條與背景區分。
- [ ] **右欄：工單頁**：表單與「儲存設定」按鈕之間為固定間距，無底部大塊 stretch；儲存成功/失敗時按鈕顏色正確（綠/紅）。
- [ ] **右欄：元件選定頁**：內容與底部間距合理，無大塊空白。
- [ ] **右欄：資料設定**：資料上傳、座標管理子頁空狀態顯示「尚未載入檔案」「(無)」等 token 文案。
- [ ] **圖表分析：常態檢定**：常態機率圖與結論文字顏色使用主題色（成功綠、錯誤紅）；結論文字無硬編碼色碼。
- [ ] **收合側欄**：收合/展開後 splitter 與 rail 按鈕正常，無版面錯位。
- [ ] **鍵盤與訊號**：Ctrl+R、Ctrl+Right、導航點擊、重新整理/下一步/儲存工單等 signal/slot 行為與修改前一致。

---

## 6. Theme / Token 沿用說明（其他頁面如何沿用）

未新增獨立 theme.py / styles.py；**所有視覺 token 與 QSS 入口** 均在既有結構中：

- **色彩、間距、字級、版面常數**：`app/ui/theme/tokens.py`
- **全域 QSS**：`app/ui/theme/dark_stylesheet.py` 的 `get_dark_stylesheet()`，由應用程式啟動時套用。

### 6.1 新頁面或新元件如何沿用

1. **使用 token 常數**  
   在頁面或 widget 中：  
   `from app.ui.theme.tokens import SPACING_MD, TEXT_PRIMARY, ACCENT_PRIMARY, ...`  
   用於：
   - 程式內設定（如 `setMinimumHeight(CONTROL_STATUS_LINE_MIN_HEIGHT)`、`addSpacing(SPACING_MD)`）
   - 或組裝 inline style / 傳入 QSS 字串時使用 f-string 代入 token。

2. **依賴全域 QSS**  
   若元件使用標準 Qt 類別且設好 `objectName` 或 `setProperty("class", "xxx")`，且該選擇器已在 `dark_stylesheet.py` 中定義，則無需再寫樣式即可與主畫面一致（例如 `QLabel[class="status-ok"]`、`QPushButton#refreshBtn`）。

3. **需要額外樣式時**  
   - 在 `dark_stylesheet.py` 中為該 `objectName` 或 `class` 增加規則，並使用 token（如 `{ACCENT_PRIMARY}`），不要寫死 hex。  
   - 或於該頁面 `setStyleSheet(...)` 時從 tokens 引入顏色/間距，保持與主畫面同一套語意（background、surface、primary、success、border 等）。

4. **空狀態或錯誤文案**  
   使用 tokens 中的 `EMPTY_MEAS_FILE`、`EMPTY_COORD_SET`、`ERROR_NO_DATA` 等，以便日後統一修改文案。

5. **圖表或自繪顏色**  
   從 tokens 引入 `ACCENT_PRIMARY`、`ACCENT_SUCCESS`、`ACCENT_ERROR`、`TEXT_PRIMARY` 等，避免硬編碼，以配合日後主題或主色調整。

### 6.2 約定摘要

- 新 UI 盡量用 **tokens 常數**，不寫死數值或 hex。
- 新 QSS 規則放在 **dark_stylesheet.py**，並用 token 變數代入。
- 主色線維持：灰階（背景/surface/block）+ 藍綠 primary + 綠 success + 紅 error；米白僅用於上層分類卡（如 NAV_PHASE_BG）。
- 狀態規則：normal → hover (SURFACE_HOVER) → active/pressed (SURFACE_ACTIVE) → disabled (TEXT_MUTED + BG_BLOCK)。

依照上述方式，後續新增或修改的頁面即可與主畫面保持同一套顏色與版面語言，並在單一檔案（tokens.py + dark_stylesheet.py）中維護。
