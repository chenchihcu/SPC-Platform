# Apple 簡約風格改版補充（2026-03）

> Historical Snapshot Note (2026-04-02): 本文件是 2026-03 UI refactor 驗收快照，內容中的舊流程文案（例如早期匯出描述）僅代表當時狀態；最新輸出契約以 `README.md` 與 `docs/decision-log.md` 為準。
>
> **Path note (2026-04-06)**：內文若見 `statistics_page.py`，現已併入 **`app/ui/pages/diagnostic_page.py`**（`DiagnosticPage`）。
>
> **Report export note (2026-04-06)**：報告匯出已收斂為 **PPTX-only、engineering-only**（無管理／工程模板切換）；見 `docs/decision-log.md`「Report export: engineering-only PPTX template」。

本次補充針對 UI 表現層進行 Apple 簡約風格重構，保持分析邏輯、資料契約與 signal/slot 行為不變。

後續若版面／token／狀態語意與本摘要或主線程式漂移，請依 **`docs/specs/spec_maintenance_and_alignment.md`** 更新對應規格（`docs/specs/ui_design_spec.md`、`docs/specs/ui_state_semantics.md`）。

## 變更範圍

- `app/ui/theme/tokens.py`
  - 更新中性色與語意色（primary/success/warning/error）為 Apple-like 語彙。
  - 新增左對齊節奏 token（`LEFT_ALIGN_*`）與更一致的圓角/間距/字體策略。
  - 強化圖表語意色差（主線、次線、控制界限、規格線、背景層）。
- `app/ui/theme/dark_stylesheet.py`
  - 全域元件樣式改為更低噪音、柔和圓角、細邊框層次。
  - 強化 page title / section title 的左對齊與一致字重。
  - 表格與卡片改為更清晰的層級分隔，保留高密度閱讀。
- `app/ui/widgets/page_templates.py`
  - 統一頁面容器左對齊，限制內容最大寬，避免中心漂移。
  - 雙欄表單主動作區改為一致間距節奏。
- `app/ui/pages/diagnostic_page.py`（本補丁撰寫時檔名為 `statistics_page.py`）、`app/ui/pages/report_export_page.py`
  - 標題列與控制列對齊第一閱讀軸（左對齊）。
  - 移除零散硬編 spacing，改用 token。
- `app/charts/base_chart.py`
  - 統一圖表背景分層、major/minor grid 可讀性與座標軸視覺一致性。

## 設計原則落實

- Token 單一來源：顏色、間距、字體與狀態語意均由 `tokens.py` 管理。
- 左對齊優先：頁標題、卡片內容與操作列保持同一閱讀起點。
- 視覺差異不只靠顏色：圖表保留網格層次與不同語意線條配置能力。
- 風格節制：僅在容器層塑造 Apple-like 乾淨層次，不對資料內容區做過度玻璃化。

## Apple 二輪精修（細節版）

- 強化品牌語彙：主色、狀態色、focus ring 與 micro-interaction token 補齊。
- 側欄細節：`sidebarContent` 與導航群組標題對齊一致，閱讀起點更穩定。
- 元件細節：按鈕/輸入/卡片/表格圓角與邊框階層統一，視覺噪訊降低。
- 圖表讀感：`base_chart` 新增統一線條樣式橋接，調整網格濃淡與軸線對比。
- 一致性：診斷／儀表板頁、圖表頁、報告頁標題與提示列左對齊語法統一。

## Apple 三輪微互動精修（第三輪）

- 互動回饋：按鈕 `pressed` 狀態增加更細緻的邊框與視覺位移感，提升操作可感知性。
- 焦點語法：輸入元件 focus ring 與選取色語法一致化，鍵盤操作辨識更清楚。
- 導覽選中態：側欄選中項加入微光暈層次（不改統計語意、僅視覺強化）。
- 文字節奏：caption/狀態列與側欄狀態資訊的對齊與字重再平衡。

# UI 稽核規格 v1.0 — 實作摘要與驗收清單

## 一、修改檔案清單

| 檔案 | 類型 |
|------|------|
| `app/ui/theme/tokens.py` | 修改 |
| `app/bootstrap/app_config.py` | 修改 |
| `app/ui/main_window.py` | 修改 |
| `app/ui/theme/dark_stylesheet.py` | 修改 |
| `app/ui/widgets/page_templates.py` | **新增** |
| `app/ui/pages/workorder_page.py` | 修改 |
| `app/ui/pages/component_select_page.py` | 修改 |
| `app/ui/pages/data_setup_page.py` | 修改 |
| `app/ui/pages/data_management_page.py` | 修改 |
| `app/ui/pages/report_export_page.py` | 修改 |
| `app/ui/widgets/control_panel.py` | 修改 |
| `app/ui/widgets/navigation_panel.py` | 修改 |
| `app/ui/widgets/status_bar.py` | 修改 |

---

## 二、每個檔案修改摘要

### `app/ui/theme/tokens.py`
- 新增語意顏色別名：`bg_app`, `bg_surface`, `bg_panel`, `bg_card`, `bg_card_active`, `text_primary`, `text_secondary`, `text_muted`, `border_default`, `accent_primary`, `accent_success`, `accent_warning`, `accent_danger`。
- 調低 `ACCENT_ERROR` 飽和度（`#c62828` → `#a84343`），符合規格 C-04。
- 新增 spacing scale：`SPACING_4`, `SPACING_8`, `SPACING_12`, `SPACING_16`, `SPACING_24`, `SPACING_32`。
- 新增 typography scale：`TYPO_APP_TITLE_PT` … `TYPO_CAPTION_PT`；`FONT_FAMILY` 改為 `"Noto Sans TC, Microsoft JhengHei UI, Segoe UI, sans-serif"`。
- 導航色改為與 dark industrial 一致：`NAV_PHASE_BG` / `NAV_STEP_*` 改為深灰系。
- 新增 `FORM_PAGE_CONTENT_MAX_WIDTH`、`DATA_LIST_PAGE_MIN_WIDTH`。

### `app/bootstrap/app_config.py`
- `DEFAULT_WINDOW_SIZE` 改為 `(1280, 720)` 作為 fallback。
- 新增 `INITIAL_WINDOW_SCREEN_RATIO = 0.85`（82%~88% 內）。

### `app/ui/main_window.py`
- 新增 `QSettings` / `QByteArray` / `QRect` / `QSize` 與 `INITIAL_WINDOW_SCREEN_RATIO`、`DATA_LIST_PAGE_MIN_WIDTH` 引用。
- 首次啟動改為以 `QScreen.availableGeometry()` 計算 85% 並置中；無 screen 時使用 `DEFAULT_WINDOW_SIZE`。
- 關閉時儲存、啟動時還原 geometry 與 window state（`SETTINGS_GEOMETRY_KEY`, `SETTINGS_STATE_KEY`）。
- `setMinimumSize(800, 500)`；workspace 與 splitter 使用 `DATA_LIST_PAGE_MIN_WIDTH` 取代硬編碼 600。
- 新增 `_settings()`、`_apply_initial_geometry_and_splitter()`、`closeEvent()`。

### `app/ui/theme/dark_stylesheet.py`
- 新增 `QLabel[class="status-info"]`、`status-pending`、`status-warning`（C-06）。
- caption 改為 `TEXT_SECONDARY`（移除 italic），提升可讀性（T-04）。
- 新增 `QToolTip` 樣式：背景、邊框、padding、字型（T-07）。

### `app/ui/widgets/page_templates.py`（新檔）
- `page_margins_and_spacing(layout)`：統一頁邊距與間距（SPACING_24 / SPACING_16）。
- `add_form_page_centered_content(parent, layout)`：回傳內層 VBoxLayout，表單頁內容限寬 `FORM_PAGE_CONTENT_MAX_WIDTH` 並置中。
- `empty_state_label(text)`：回傳套用 `placeholderMessage` 的空狀態 QLabel。

### `app/ui/pages/workorder_page.py`
- 使用 `page_margins_and_spacing`、`add_form_page_centered_content`；表單區（工單主檔、規格、儲存鈕）改為加入 `form_layout`，內容最大寬度 720px 置中。
- 移除多餘 `layout.addSpacing(SPACING_MD)`。

### `app/ui/pages/component_select_page.py`
- 使用 `page_margins_and_spacing`、`add_form_page_centered_content`；單一 GroupBox 改為加入 `form_layout`。

### `app/ui/pages/data_setup_page.py`
- 邊距改為 `SPACING_24`，區塊間距改為 `SPACING_16`（由 `SPACING_MD`/`SPACING_LG` 改為 scale 常數）。
- 主內容依可用寬度切換單欄／雙欄／三欄（`DATA_SETUP_BREAKPOINT_2COL` / `DATA_SETUP_BREAKPOINT_3COL` 與 `layout_tier_from_width`）。

### `app/ui/pages/data_management_page.py`
- 使用 `page_margins_and_spacing`、`empty_state_label`。
- 新增 `_empty_state` 標籤：「尚無資料。請先至資料設定…」；`_sync_data` 有資料時隱藏、無資料時顯示。
- 表格區 `layout.addWidget(self.table_view, 1)` 以利伸展。
- 無資料時 `lbl_meta` 文案改為「無法從快取擷取…」（非「錯誤：」）。

### `app/ui/pages/report_export_page.py`
- 使用 `page_margins_and_spacing`。
- 預覽區標題改為 `QLabel` + class `caption`；`QTextEdit` 設 `setPlaceholderText(PREVIEW_EMPTY_HINT)`，預覽區 stretch=1。

### `app/ui/widgets/control_panel.py`
- 移除所有 `QFont` / `setFont`，字型完全由全域 QSS 控制（T-01）。
- 邊距改為 `SPACING_16`。
- 資料狀態初始與更新改為語意 class：`status-pending`（未載入/未計算）、`status-ok`（成功）、`status-warning`（成功率 &lt; 90%）；不再一律使用 `status-error`（C-06）。
- `update_connection_status` 結尾對四個狀態 label 呼叫 `unpolish`/`polish` 以更新樣式。

### `app/ui/widgets/navigation_panel.py`
- 移除 `QFont` 與 `setFont`（phase header、step 按鈕），改由 QSS 控制字型。
- 移除對 `FONT_FAMILY`、`SIDEBAR_FONT_SIZE`、`SIDEBAR_PHASE_TITLE_FONT_SIZE` 的引用。

### `app/ui/widgets/status_bar.py`
- 使用 `SPACING_8`、`CONTROL_STATUS_LINE_MIN_HEIGHT` 設定 layout 邊距與 label 最小高度（T-06）。

---

## 三、Diff 風格重點摘要（關鍵片段）

```diff
# tokens.py
- ACCENT_ERROR = "#c62828"
+ ACCENT_ERROR = "#a84343"
+ SPACING_4, SPACING_8, SPACING_12, SPACING_16, SPACING_24, SPACING_32
+ FONT_FAMILY = "Noto Sans TC, Microsoft JhengHei UI, Segoe UI, sans-serif"
- NAV_PHASE_BG = "#FDF5E0"
+ NAV_PHASE_BG = "#2a2a2a"
+ FORM_PAGE_CONTENT_MAX_WIDTH = 720
+ DATA_LIST_PAGE_MIN_WIDTH = 600

# main_window.py
- self.resize(*DEFAULT_WINDOW_SIZE)
+ self.setMinimumSize(800, 500)
+ self._apply_initial_geometry_and_splitter()  # QScreen 85% + 置中 或 還原 QSettings
+ def closeEvent: saveGeometry(); saveState()
- right_w = max(600, total - left_w)
+ right_w = max(DATA_LIST_PAGE_MIN_WIDTH, total - left_w)

# dark_stylesheet.py
+ QLabel[class="status-info"] { ... }
+ QLabel[class="status-pending"] { ... }
+ QLabel[class="status-warning"] { ... }
+ QToolTip { background-color; color; border; padding; font-family; font-size; }
  QLabel[class="caption"] { color: TEXT_SECONDARY; }  /* 移除 italic */

# control_panel.py
- base_font = QFont(...); cond_box.setFont(...); lbl.setFont(base_font)
+ (移除所有 setFont)
- lbl.setProperty("class", "status-error")
+ lbl.setProperty("class", "status-pending")
  update_connection_status: rate>=90 -> status-ok; 0<rate<90 -> status-warning; else -> status-pending
```

---

## 四、可能影響其他頁面的風險

| 風險 | 說明 | 緩解 |
|------|------|------|
| **統計分析、圖表分析頁** | 未套用 `page_margins_and_spacing`，與已改頁面邊距可能不一致 | 後續可對兩頁呼叫 `page_margins_and_spacing(layout)`，或沿用既有邊距不變 |
| **FONT_FAMILY 改為 Noto Sans TC** | 若系統未安裝 Noto Sans TC，會 fallback 到 JhengHei UI / Segoe UI | 屬預期；必要時在安裝說明註明字型 |
| **NAV 顏色改為深色** | 左側導航由米黃/深綠改為深灰，視覺對比略降 | 選中態仍依 QSS `[isCurrent="true"]` 左邊框與背景區分 |
| **ACCENT_ERROR 變淡** | 刪除/危險按鈕紅色較不刺眼 | 仍具警示性，符合規格 C-04 |
| **QSettings 鍵名** | 使用 `SPC/PlatformV2` 與 `MainWindow` group | 若未來多視窗需區分，可改 key 或 group |
| **資料管理頁 empty_state** | 初次進入為「尚無資料」提示，同步後隱藏 | 邏輯僅依 `_sync_data` 顯示/隱藏，不影響既有同步與表格行為 |

---

## 五、回歸驗收 Checklist

### 視窗與版面
- [ ] 首次啟動：視窗約為可用螢幕 85%，且置中。
- [ ] 第二次啟動：視窗尺寸與最大化狀態與上次關閉一致。
- [ ] 視窗縮到最小（800×500）時，內容不重疊、不嚴重裁切。
- [ ] 左側導航收合/展開時，右側內容區寬度正確（≥600）。

### 導航與左側欄
- [ ] 三欄階段標題與步驟按鈕為深色主題，選中步驟有左邊框與背景區分。
- [ ] 分析條件、資料狀態、重新整理/下一步驟按鈕可操作；資料狀態顯示為 pending（灰）/ ok（綠）/ warning（黃），不再全部紅字。

### 資料設定頁
- [ ] 上傳量測、座標管理區塊正常；間距與邊距一致。
- [ ] 視窗寬度變更時，單欄／雙欄／三欄切換正常（門檻見 tokens）。
- [ ] 匯入與轉發 signal 行為不變。

### 工單資料輸入頁
- [ ] 表單區最大寬度約 720px、置中；儲存後成功/失敗仍為綠/紅樣式。
- [ ] 工單與規格儲存、分析觸發流程不變。

### 元件/量測選定頁
- [ ] 單一 GroupBox 與 List 置中、限寬；選擇 Volume/Height/Area 仍可被主視窗分析使用。

### 資料管理頁
- [ ] 無資料時顯示「尚無資料…」提示；按「從快取核心同步」有資料後提示隱藏、表格顯示。
- [ ] 同步邏輯與 2000 筆 cap 不變。

### 匯出分析報告頁
- [ ] 未產生預覽時，預覽區顯示 placeholder 提示；生成預覽、另存 TXT 流程不變。

### 字型與樣式
- [ ] 各頁標題、按鈕、說明與狀態列字型一致（由 QSS 驅動）。
- [ ] Tooltip 有邊框與背景、可讀。

### 未改動頁面（快速確認）
- [ ] 統計分析頁：表格與資料來源正常。
- [ ] 圖表分析頁：Tab 與圖表更新正常。

---

## 六、後續可選項目（未在此次 patch）

- 統計分析、圖表分析頁套用 `page_margins_and_spacing` 或專用 template。
- 左側「重新整理 / 下一步」按鈕視覺退階（例如改為 secondary 樣式）。
- 表單欄位 `min-height` 改為依 font metrics 計算。
- 125% / 150% / 200% DPI 正式驗證清單與自動化檢查。
