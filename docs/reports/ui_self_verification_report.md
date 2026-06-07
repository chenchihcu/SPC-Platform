# Apple 簡約風格改版自我驗證（2026-03）

> **Note (2026-04-06)**：本驗收快照中的 `statistics_page.py` 已併入 `diagnostic_page.py`（`DiagnosticPage`）；對齊檢查請改對 **`diagnostic_page.py`**。

## 驗證摘要

- UI 風格：完成 Apple-like 簡約語彙更新（色彩、圓角、層次、字重）。
- 排版一致性：頁面模板與關鍵頁面已統一左對齊第一閱讀軸。
- 圖表可讀性：`base_chart` 已統一 figure/axes 分層、grid 層次與軸文字對比。
- 安全性：未更動統計公式、分析流程與 public interface。

## 驗證清單

- Token 單一來源
  - [x] 顏色、間距、字體、狀態語意集中在 `app/ui/theme/tokens.py`
- 全域樣式一致
  - [x] `app/ui/theme/dark_stylesheet.py` 採 token 參照
  - [x] 主要元件（按鈕、輸入、表格、卡片、導覽）視覺語言一致
- 排版對齊
  - [x] `page_templates.py` 套用左對齊與內容寬度節奏
  - [x] `diagnostic_page.py`（當時驗收寫為 `statistics_page.py`）、`report_export_page.py` 標題列左對齊
- 圖表視覺語意
  - [x] `app/charts/base_chart.py` 統一背景、網格與軸色
  - [x] 保留統計語意，不改動運算結果

## 風險與備註

- 本次為視覺與排版重構，未引入新依賴。
- 個別頁面仍可能存在歷史 objectName 樣式差異，後續可再做逐頁微調。

## 二輪精修驗證（Apple 細節）

- 品牌化 token
  - [x] 新增 focus ring / 玻璃層 / micro-detail token
  - [x] 主色與狀態色對比再強化
- 全域元件細節
  - [x] 按鈕、輸入、卡片、表格、導覽狀態一致化
  - [x] 側欄內容容器加入一致 objectName 與樣式掛鉤
- 頁面一致性
  - [x] 診斷（製程診斷儀表板）、圖表、報告頁標題與提示列左對齊
- 圖表讀感
  - [x] `base_chart` 強化軸/網格層級
  - [x] 新增 `chart_line_style()` 統一線條語彙

## 三輪微互動驗證（Apple 超細節）

- [x] 按鈕按壓狀態與 disabled 對比提升
- [x] 輸入 focus ring / selection 色彩語法一致
- [x] 導覽選中態加入更清楚的品牌化層次
- [x] status bar / control panel 狀態列對齊與字重節奏微調

# UI 稽核規格 — 自我驗收報告

> **維護提示**：本報告為某次驗收快照；持續治理準則（DPI／響應式驗收如何寫入規格、token 單一來源）見 **`docs/specs/spec_maintenance_and_alignment.md`** §3、§4。

依 checklist 逐項檢視程式碼與設定後的結果。

---

## [Typography]

### App Title / Page Title / Section Title / Body / Button / Caption 是否形成固定字型層級

**結果：部分符合**

| 層級 | 現況 |
|------|------|
| **App Title** | 未在 UI 內單獨呈現（僅 `setWindowTitle(APP_NAME)` 用於視窗標題列）；tokens 已定義 `TYPO_APP_TITLE_PT = 17`，未在 QSS 使用。 |
| **Page Title** | 已形成：`QLabel[class="pageTitle"]` 使用 `FONT_SIZE_TITLE`（17px）、bold，與 tokens 之 `TYPO_PAGE_TITLE_PT` 對齊。 |
| **Section Title** | 側欄區塊使用 `SIDEBAR_SECTION_TITLE_FONT_SIZE`（14px）、QGroupBox 標題同；右側內容區若另有「區段標題」未統一使用 `section_title` class。 |
| **Body** | 已形成：QPushButton、QLineEdit、QComboBox 等使用 `FONT_SIZE_BODY`（11px），與 `TYPO_BODY_PT` 對齊。 |
| **Button** | 與 Body 同字級（11px），由全域 QSS 控制；primary/success 為 bold。 |
| **Caption** | 已形成：`QLabel[class="caption"]` 使用 `FONT_SIZE_CAPTION`（10px）、`TEXT_SECONDARY`。 |

**結論**：字型層級在 tokens 有完整 scale（含 TYPO_*），QSS 以 FONT_SIZE_TITLE/BODY/CAPTION 與 SIDEBAR_* 套用；Page / Body / Button / Caption 已固定，App Title 僅在視窗標題、Section 在側欄有對應，右側頁面區段標題可再統一用 `section_title` class。

---

### 中文與英文混排是否一致

**結果：符合**

- 全系統字型由單一 `FONT_FAMILY` 控制：`"Noto Sans TC, Microsoft JhengHei UI, Segoe UI, sans-serif"`（tokens.py）。
- 未在個別 widget 再設 `setFont()`，導航、控制面板、按鈕、標籤皆由 QSS 繼承，中英混排為同一字族與字級。
- 標題如「資料設定 (Data Setup)」「工單資料輸入 (Workorder Input)」為同一 label，不會出現中英不同字重或字級。

---

### placeholder / helper text 是否清楚

**結果：符合**

- **Caption / 說明文字**：`QLabel[class="caption"]` 使用 `TEXT_SECONDARY`（#b0b0b0），已移除過淡的 italic，可讀性提升。
- **Placeholder / 空狀態**：`QLabel[class="placeholderMessage"]`、`chartPlaceholder` 使用 `FONT_SIZE_PLACEHOLDER`（14px）、`TEXT_SECONDARY`。
- **報告預覽**：`QTextEdit.setPlaceholderText(PREVIEW_EMPTY_HINT)`，未產生預覽時有明確提示。
- **Tooltip**：QToolTip 使用 `FONT_SIZE_CAPTION`、`TEXT_PRIMARY`、背景與邊框，納入統一規格。

---

## [Window]

### 預設開窗尺寸是否依可用螢幕區域計算

**結果：符合**

- `main_window._apply_initial_geometry_and_splitter()` 在無儲存 geometry 時：
  - 使用 `QApplication.primaryScreen().availableGeometry()`；
  - 寬高為 `available.width/height * INITIAL_WINDOW_SCREEN_RATIO`（0.85，落在規格 82%–88%）；
  - 以 `resize(w, h)` 設定，並 `move(available.center().x() - w/2, ...)` 置中。
- `app_config.INITIAL_WINDOW_SCREEN_RATIO = 0.85`；無 screen 時 fallback 為 `DEFAULT_WINDOW_SIZE`。

---

### 是否支援恢復上次 geometry / window state

**結果：符合**

- `closeEvent` 呼叫 `saveGeometry()`、`saveState()` 寫入 `QSettings("SPC", "PlatformV2")`，group `MainWindow`，key `main_window/geometry`、`main_window/state`。
- 啟動時先讀取；若 `restoreGeometry(geom)` 成功則再 `restoreState(state)`；只有首次或無效資料才用 QScreen 計算與置中。

---

### 最大化後是否仍存在大量無意義空白

**結果：部分符合（依頁型）**

- **Form 頁（工單、元件選定）**：內容區限寬 `FORM_PAGE_CONTENT_MAX_WIDTH`（720px）並置中，最大化時兩側為 stretch，空白為刻意留白，非 layout 失敗。
- **Data / List 頁（資料設定、資料管理）**：workspace 為 `QStackedWidget`，`setMinimumWidth(DATA_LIST_PAGE_MIN_WIDTH)`（600），splitter 右側為 stretch，內容區會隨視窗擴展；資料管理頁表格有 `stretch=1`。
- **Preview 頁（報告匯出）**：預覽區 `layout.addWidget(self.text_preview, 1)`，會佔滿剩餘高度。
- **未改動頁（診斷儀表板、圖表）**：未套用 template，最大化時右側可能仍有較多空白，屬已知範圍，可後續套用同一 spacing/模板規則。

---

## [Layout]

### Form Page / Data Page / Preview Page 是否已形成模板規則

**結果：部分符合**

| 頁型 | 現況 |
|------|------|
| **Form Page** | 已建立：`page_templates.page_margins_and_spacing()`、`add_form_page_centered_content()`；工單、元件選定已套用（限寬 720、置中、SPACING_24/16）。 |
| **Data Page** | 規則為：`page_margins_and_spacing` + 標題/說明 + 內容區（必要時 empty state）；資料設定、資料管理已套用邊距/間距與空狀態，惟未抽出獨立「DataListPageTemplate」類別。 |
| **Preview Page** | 規則為：`page_margins_and_spacing` + 標題 + 動作列 + 預覽區（stretch + placeholder）；報告匯出已套用，未另建「PreviewExportPageTemplate」類別。 |

**結論**：三種頁型皆有對應的版面規則（邊距、間距、限寬/置中、空狀態、stretch），並在指定五頁套用；模板以 helpers（functions）實作，未使用繼承式 template class。

---

### 左側導航與右側內容區比例是否協調

**結果：符合**

- 左側：`CollapsibleSidebar` 展開寬 `NAV_WIDTH_EXPANDED`（380px）、收合 56px，固定寬度。
- 右側：`QStackedWidget` 最小寬 600px，於 splitter 中設為 stretch，取得剩餘寬度。
- Splitter 初始與收合/展開時皆以 `[NAV_WIDTH_*, max(DATA_LIST_PAGE_MIN_WIDTH, total - NAV)]` 計算，比例穩定。

---

### 是否移除多餘框線與不必要空白

**結果：部分符合**

- **間距**：已統一使用 tokens（SPACING_24、SPACING_16 等），表單頁與資料/報告頁邊距與區塊間距一致。
- **框線**：導航區改為與主內容同深色系，視覺一致；QGroupBox / QFrame 仍用於表單與區塊，未大量移除，僅避免新增多餘 nested frame。
- **空白**：Form 頁以限寬置中取代過寬表單；資料管理無資料時以明確 empty state 取代大塊空洞；未以空白 widget 撐版。

---

## [Color]

### selected / hover / primary / success / danger 是否一致

**結果：符合**

| 狀態/類型 | 實作 |
|-----------|------|
| **Selected（導航）** | `QPushButton#navStepBtn[isCurrent="true"]`：背景 `NAV_STEP_ACTIVE_BG`、左邊框 4px `ACCENT_PRIMARY`、字重 bold。 |
| **Hover** | 一般按鈕 `SURFACE_HOVER`/`BORDER_HOVER`；navStepBtn `NAV_STEP_HOVER_BG`；Tab `:hover:!selected` → `SURFACE_ACTIVE`。 |
| **Primary** | `#refreshBtn`、`[class="primary"]`：`ACCENT_PRIMARY`，hover 為 `ACCENT_PRIMARY_HOVER`。 |
| **Success** | `#nextStepBtn`、`[class="success"]`、workorderSaveBtn[saveState="success"]：`ACCENT_SUCCESS`，hover 為 `ACCENT_SUCCESS_HOVER`。 |
| **Danger** | `[class="danger"]`、`#dangerBtn`：`ACCENT_ERROR`（已降飽和 #a84343），hover 為 `ACCENT_ERROR_HOVER`。 |

上述皆由 `dark_stylesheet.py` 與 `tokens.py` 集中定義，無分散硬編碼。

---

### Data Status 是否不再全部紅字

**結果：符合**

- `control_panel.update_connection_status` 依語意設定 class：
  - 未載入/未計算：`status-pending`（灰 `TEXT_MUTED`）；
  - 已載入/已完成：`status-ok`（綠 `ACCENT_SUCCESS`）；
  - 關聯成功率 &lt; 90% 且 &gt; 0：`status-warning`（黃 `ACCENT_WARNING`）；
  - 不再將「未完成」設為 `status-error`。
- QSS 已定義 `status-ok`、`status-error`、`status-info`、`status-pending`、`status-warning` 五種，顏色與字級一致。

---

### title bar 與主內容區是否風格一致

**結果：符合**

- 未自繪應用程式 title bar；作業系統標題列為系統樣式。
- 左側「標題」視覺為導航階段標題（`#navPhaseHeader`）：已改為深色系（`NAV_PHASE_BG = "#2a2a2a"`、`NAV_PHASE_TEXT = TEXT_SECONDARY`、`NAV_PHASE_BORDER = BORDER`），與主內容區 dark industrial 一致，不再使用米黃/深綠。

---

## [DPI]

### 125% / 150% / 200% scaling 下是否可讀、可用、對齊正常

**結果：需實機/實環境驗證**

- **程式面**：
  - `app/bootstrap/dpi.py` 已設 `QApplication.setHighDpiScaleFactorRoundingPolicy(PassThrough)`，由 Qt 依系統 DPI 縮放。
  - 尺寸以 layout、stretch、minWidth/minHeight 與 token 常數為主，未在關鍵處硬寫固定 px 幾何；按鈕/輸入 min-height、狀態列高度等由 token 控制。
  - 字級與間距為 px，會隨系統縮放一併放大，理論上可讀性會隨之提高。
- **未做**：未使用 font metrics 動態計算欄高、未在 125/150/200% 下跑過完整 UI 測試。
- **建議**：在 Windows 顯示設定 125%、150%、200% 下實際開啟應用，檢查：標題/內文/按鈕可讀、表單與列表不裁切、導航與狀態列對齊、tooltip 可讀；若有錯位或過擠再針對該元件改用 layout 或 font metrics 取代固定 px。

---

## 總結表

| 大項 | 子項 | 結果 |
|------|------|------|
| **Typography** | 固定字型層級 | 部分符合（scale 有，App/Section 在 UI 未完全對齊） |
| | 中英混排一致 | 符合 |
| | placeholder/helper 清楚 | 符合 |
| **Window** | 預設開窗依螢幕計算 | 符合 |
| | 恢復 geometry/state | 符合 |
| | 最大化無大量空白 | 部分符合（已改五頁符合；統計/圖表未改） |
| **Layout** | 三種頁型模板規則 | 部分符合（規則已建立並套用，無 template class） |
| | 左右比例協調 | 符合 |
| | 移除多餘框線/空白 | 部分符合（間距統一、未大量減框） |
| **Color** | selected/hover/primary/success/danger 一致 | 符合 |
| | Data Status 不全紅 | 符合 |
| | title bar 與主內容一致 | 符合（導航區已改深色） |
| **DPI** | 125/150/200% 可讀可用對齊 | 需實機驗證 |

---

**建議後續**（可選）：

1. 在 QSS 中為右側頁面區段標題新增並使用 `section_title` class，對應 `TYPO_SECTION_TITLE_PT`。
2. 統計分析、圖表分析頁套用 `page_margins_and_spacing`，必要時套用 Data/Preview 規則，以改善最大化時空白。
3. 在 125%、150%、200% 下執行手動 DPI 驗收並記錄結果。
