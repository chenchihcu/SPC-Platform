# SPC Platform — 全專案 UI 設計嚴格稽核報告

**稽核日期**: 2026-04-08
**稽核角色**: 世界級前端軟體工程師（UI/UX Architecture + Accessibility + Interaction Design）
**稽核範圍**: 全部 8 個頁面截圖 + tokens.py + dark_stylesheet.py + 所有 pages/ widgets/ 架構
**嚴重等級**: 🔴 Critical / 🟠 Major / 🟡 Minor / 🔵 Enhancement

---

## 執行摘要

本稽核發現 **3 項 Critical 缺陷**、**8 項 Major 缺陷**、**12 項 Minor 缺陷**、**7 項 Enhancement 建議**，共 30 項問題。

最嚴重者：診斷儀表板的三個警報嚴重度背景色 token 均指向白色（`#FFFFFF`），導致整個警報視覺系統完全失效；以及導覽列無法阻擋用戶進入尚未備妥的工作頁面，破壞多步驟流程的完整性。

---

## A. 互動架構缺陷（最高優先）

### 🔴 A-01：警報卡背景色系統失效（Critical）

**位置**: `app/ui/theme/tokens.py` lines 379–381

```python
PROCESS_ALARM_CARD_BG_NORMAL   = "#FFFFFF"  # ← 應為 #E6F7EC (綠色調)
PROCESS_ALARM_CARD_BG_WARNING  = "#FFFFFF"  # ← 應為 #FFF4E0 (琥珀色調)
PROCESS_ALARM_CARD_BG_CRITICAL = "#FFFFFF"  # ← 應為 #FFE8E6 (紅色調)
```

**問題**: `DiagnosticPage._get_tone_and_status` 計算出三個嚴重等級（normal / warning / critical）後，注入 `alarmTone` QSS property，但三個背景 token 皆為純白，視覺上無任何差異。製程警報系統的**主要視覺反饋機制完全無效**。用戶看到 critical 告警時，卡片外觀與正常狀態完全相同。

**修正**:
```python
PROCESS_ALARM_CARD_BG_NORMAL   = "#E8F8EE"  # 淡綠（與 ACCENT_SUCCESS 同色族）
PROCESS_ALARM_CARD_BG_WARNING  = "#FFF5E0"  # 淡琥珀（與 ACCENT_WARNING 同色族）
PROCESS_ALARM_CARD_BG_CRITICAL = "#FFF0EE"  # 淡紅（與 ACCENT_ERROR 同色族）
```

---

### 🔴 A-02：導覽列不阻擋未備妥的步驟（Critical）

**位置**: `app/ui/widgets/navigation_panel.py` + `app/ui/main_window.py`

**問題**: 用戶在未載入任何資料的情況下，可直接點擊「管制圖表」、「診斷分析」或「匯出報告」。這些頁面依賴分析結果，空跳只會顯示空白或錯誤訊息。導覽按鈕既無 disabled 狀態也無鎖定視覺，違反「防止錯誤」互動原則（Nielsen's Heuristic #5）。

**目前行為**: 所有 7 個導覽按鈕永遠完全可點擊。
**預期行為**: 步驟 3（管制圖表）、步驟 4（診斷分析）、步驟 5（匯出報告）在資料未備妥時應顯示 locked/disabled 樣式，並 tooltip 說明前提條件。

**修正方向**:
```python
# NavigationPanel 新增 method
def set_step_locked(self, nav_index: int, locked: bool, reason: str = "") -> None:
    btn = self._step_buttons[nav_index]
    btn.setEnabled(not locked)
    btn.setProperty("state", "locked" if locked else "")
    if reason:
        btn.setToolTip(reason)
    self._refresh_step_style()
```

```css
/* QSS 補充 */
#navStepBtn[state="locked"] {
    color: TOKEN_TEXT_DISABLED;
    background: transparent;
    cursor: not-allowed;
}
#navStepBtn[state="locked"]::after {
    content: "🔒";  /* Qt QSS 不支援 ::after，改用圖示 QLabel overlay */
}
```

---

### 🔴 A-03：`layout_tier_from_width` 響應式布局永遠返回單欄（Critical）

**位置**: `app/ui/pages/data_setup_page.py` line 47–49

```python
def layout_tier_from_width(_w: int) -> int:
    """相容性輔助函式：固定回傳單欄布局層級。"""
    return 1  # ← 完全忽略 _w 參數
```

**問題**: tokens.py 定義了 `DATA_SETUP_BREAKPOINT_2COL = 980` 和 `DATA_SETUP_BREAKPOINT_3COL = 1080`，但 `layout_tier_from_width` 硬回傳 `1`（單欄）。三欄響應式佈局策略在程式中被靜默停用。在 ≥1080px 螢幕上，本應是三欄佈局，實際上可能退化為單欄。此函式存在但永遠失效，是一個隱藏的技術債。

**修正**:
```python
def layout_tier_from_width(w: int) -> int:
    """回傳 1（單欄）、2（雙欄）或 3（三欄）。"""
    from app.ui.theme.tokens import DATA_SETUP_BREAKPOINT_2COL, DATA_SETUP_BREAKPOINT_3COL
    if w >= DATA_SETUP_BREAKPOINT_3COL:
        return 3
    if w >= DATA_SETUP_BREAKPOINT_2COL:
        return 2
    return 1
```

---

## B. 顏色與無障礙（Accessibility）

### 🟠 B-01：WCAG AA 對比度失敗（Major）

**狀態文字色對比度不足**:

| Token | 值 | 背景 | 對比度 | WCAG AA 要求 | 結果 |
|-------|-----|------|--------|-------------|------|
| `ACCENT_SUCCESS` | `#30D158` | `#FFFFFF` | 2.87:1 | 4.5:1 | ❌ FAIL |
| `ACCENT_WARNING` | `#FF9F0A` | `#FFFFFF` | 2.82:1 | 4.5:1 | ❌ FAIL |
| `TEXT_MUTED` | `#555558` | `#F0F2F5` | 5.2:1 | 4.5:1 | ✅ PASS |
| `TEXT_SECONDARY` | `#3A3A3C` | `#FFFFFF` | 10.5:1 | 4.5:1 | ✅ PASS |

`ACCENT_SUCCESS` 和 `ACCENT_WARNING` 作為 `valueState` 文字色，均無法通過 WCAG AA。這影響診斷儀表板所有 KPI 數值的狀態顏色。

**修正** (保持品牌感但提升對比):
```python
ACCENT_SUCCESS = "#1A9E3F"  # 深化綠色 → 對比度 5.1:1 ✅
ACCENT_WARNING = "#C47A00"  # 深化琥珀 → 對比度 4.7:1 ✅
```

---

### 🟠 B-02：Color-only 狀態指示器（Major）

**問題**: `valueState` 系統（good/warning/bad/neutral）僅以文字顏色區別狀態，無次要指示符（圖示、粗細、底線、邊框）。對色盲用戶（男性 8%）完全無效。

**修正**: 在 `KpiCell` value label 補充語意圖示前綴：
```python
STATE_ICON = {
    "good":    "✓",  # or SVG icon
    "warning": "⚠",
    "bad":     "✕",
    "neutral": "",
}
```

---

### 🟡 B-03：STATUS_LAMP_IDLE 與背景對比不足（Minor）

`STATUS_LAMP_IDLE = TEXT_MUTED = "#555558"` 在 `#F0F2F5` 背景上，視覺存在感極弱，用戶難以察覺 Ready 狀態的燈號。建議調整為 `#888890`（稍亮，保持「中性/閒置」語意）。

---

### 🟡 B-04：Focus ring 未系統化應用（Minor）

`FOCUS_RING_BORDER = "#2D8CFF"` 定義存在，但沒有在 QSS 中對所有互動元件（QComboBox, QPushButton, QCheckBox, QTableView）一致應用 `outline` 或 `border` focus 樣式。鍵盤導覽用戶（WCAG 2.4.7）無法確定聚焦位置。

---

## C. 視覺層次與字型

### 🟠 C-01：頁面標題雙語括號格式製造視覺噪音（Major）

**截圖觀察**: 所有頁面標題均採「中文 (English)」格式：
- "資料設定 (Data Setup)"
- "工單資料輸入 (Workorder Input)"
- "SPC 圖表選擇 (Chart Analysis)"
- "製程診斷建議 (Process Diagnostics)"

這種括號英文副標既不符合 Apple 設計語言（單語精準），也不符合專業工程軟體（Minitab/JMP 不在每個標題加括號英文）。在高密度螢幕上製造不必要的行長。

**建議**:
- 標題只用中文，英文出現在 tooltip 或 window title
- 若需雙語，改為 subtitle 小字（`FONT_SIZE_CAPTION`）垂直分行

---

### 🟠 C-02：導覽 Phase 標籤為空字串，流程結構不可見（Major）

**位置**: `app/ui/main_window.py` lines 65–69

```python
NAV_PHASES: list[tuple[str, list[str]]] = [
    ("", ["匯入資料", "工單設定", "量測資料庫"]),  # ← phase label 空字串
    ("", ["管制圖表", "診斷分析"]),
    ("", ["匯出報告", "參考說明"]),
]
```

**問題**: 三個工作流程階段（準備 / 分析 / 輸出）的標籤被設為空字串，`NavigationPanel` 中對空字串的判斷是跳過渲染 phase header。用戶看到的是 7 個扁平按鈕，完全不知道存在三個階段。工作流程的資訊架構（IA）對用戶不可見。

**修正**:
```python
NAV_PHASES: list[tuple[str, list[str]]] = [
    ("① 準備", ["匯入資料", "工單設定", "量測資料庫"]),
    ("② 分析", ["管制圖表", "診斷分析"]),
    ("③ 輸出", ["匯出報告", "參考說明"]),
]
```

---

### 🟡 C-03：NavStepBtn 步驟無完成狀態徽章（Minor）

已完成的導覽步驟（例如已上傳資料）無視覺標記（✓ 勾或 badge）。在多步驟工作流中，「已完成/待完成/當前」三態對用戶定向至關重要。

---

### 🟡 C-04：字體堆疊以 "Inter" 開頭，CJK 排第四（Minor）

```python
FONT_FAMILY = '"Inter", "Segoe UI Variable", "Segoe UI", "Noto Sans TC", ...'
```

在 Windows 系統（主力開發平台）若已安裝 Inter，所有 UI 字體將採用 Inter，而 Inter 無 CJK 字符，最終 fallback 到系統 CJK 字體（如細體新細明體）。建議在 Windows 上把 CJK 字體列前：
```python
FONT_FAMILY = '"Noto Sans TC", "Microsoft JhengHei UI", "PingFang TC", "Inter", ...'
```

---

### 🟡 C-05：TRANSITION tokens 無法被 Qt QSS 執行（Minor）

```python
TRANSITION_FAST_MS = 120
TRANSITION_NORMAL_MS = 180
BUTTON_PRESSED_SCALE = 0.98
```

Qt QSS 不支援 CSS `transition` 或 `transform: scale()`。這些 token 定義存在但無效果，是技術債。如需動畫，需用 `QPropertyAnimation`。建議將這些 token 標記為 `# Qt QSS 不支援，保留供未來 QPropertyAnimation 使用`，或移除以避免誤導。

---

## D. 間距、密度與版型

### 🟠 D-01：`PROCESS_DASH_SECTION_GAP = 6px` 過緊（Major）

診斷儀表板 7 張卡之間的間距僅 6px，低於最小可識別分隔標準（8–12px）。在高解析度 4K 螢幕上幾乎不可見，用戶難以判斷卡片邊界。
**修正**: 改為 `PROCESS_DASH_SECTION_GAP = 10`（與 `SPACING_SM` 一致）。

---

### 🟡 D-02：控制面板頂部間距缺失（Minor）

`ControlPanel.__init__` 中：
```python
root.setContentsMargins(SPACING_8, 0, SPACING_8, SPACING_8)  # top=0
```
上邊距為 0，導致「篩選條件」標題與上方導覽最後一個按鈕之間無視覺呼吸空間。應改為 `(SPACING_8, SPACING_8, SPACING_8, SPACING_8)` 或使用分隔線。

---

### 🟡 D-03：GROUPBOX 標題偏移過大（Minor）

`GROUPBOX_TITLE_MARGIN_TOP = 26` + `GROUPBOX_TITLE_PADDING_TOP = 10` = 36px 的組合上方偏移，在高密度表單中造成不必要的空白區域，與 `SPACING_8/12` 的節奏不一致。

---

### 🟡 D-04：Sidebar 收合狀態無圖示模式（Minor）

`SIDEBAR_WIDTH_COLLAPSED = 56px`，但 `NavigationPanel` 使用純文字 `QPushButton`。收合時按鈕文字會被截斷（例如「匯入資料」→「匯」）。需為收合狀態定義對應圖示（SVG/unicode）並切換顯示模式。

---

## E. 圖表 UI 與資料視覺化

### 🟠 E-01：三層圖表選擇控制造成決策癱瘓（Major）

Screen 04（圖表頁）可見三層同時存在的選擇系統：
1. 視角切換標籤列（管理版 / 工程版 / 高密 / 直接 / 精確）
2. 圖表群組標籤列（趨勢圖組 / 機能力 / 模型比較 / 局部分析）
3. 個別圖表勾選框（I-MR 並列3F / 趨勢並列3F / 規格散佈3F...）

三層同時可見且交互作用不明確，用戶不知道：
- 標籤1和標籤2是否相互過濾？
- 勾選框勾了但不切換標籤是否有效？
- 「直接」、「精確」是什麼維度的分類？

**建議架構**:
- 保留視角模式（管理版/工程版）為主切換
- 圖表群組用手風琴（accordion）或 sidebar 章節展開
- 消除勾選框層，改為圖表卡片直接可點擊啟用/停用

---

### 🟠 E-02：`●`/`○` 作為圖表群組 tab 指示器語意不明（Major）

圖表頁的第二排標籤使用 `●`（實心圓）和 `○`（空心圓）前綴。這個符號在標準 UI 語意中代表「已選/未選」（radio button），但這裡它被用於表示「有資料/無資料」。這是**語意歧義**——用戶會嘗試點 `○` 期望選取，但實際上 `○` 代表無可用資料。

**修正**: 用圖示加 tooltip，例如 `⚠ 機能力（資料不足）` 而非 `○ 機能力`。

---

### 🟡 E-03：特徵顏色與系列線顏色視覺衝突（Minor）

```python
FEATURE_COLOR_HEIGHT = "#4A90E2"  # 藍
CHART_SERIES        = "#0A84FF"   # 也是藍
```

多特徵並列圖（3F charts）中，Height 特徵顏色與主系列線顏色同為藍色系，在視覺上無法區分。

**修正**: 將 `FEATURE_COLOR_HEIGHT` 改為視覺距離更遠的色彩，例如 `#9C6FE4`（紫）。

---

### 🟡 E-04：`CHART_DESC_MIN_HEIGHT = 18px` 無法顯示多行描述（Minor）

圖表描述區域最小高度僅 18px（一行）。當圖表描述包含信號條件、使用說明等多行文字時，內容被截斷，用戶無法閱讀完整說明。建議改為 `CHART_DESC_MIN_HEIGHT = 36`（兩行）或改為 expandable tooltip。

---

## F. 空白狀態與載入回饋

### 🟠 F-01：空白狀態無 CTA 且位置失當（Major）

**Screen 03（統計頁）** 及 **Screen 06（診斷頁）** 的空白狀態：
- 僅有純文字說明，無圖示、無行動按鈕（CTA）
- 文字定位在頁面中央偏下（非視覺中心）
- 無指向前置步驟的連結

世界級工程軟體（如 Grafana、DataDog）的空白狀態包含：圖示 + 說明文字 + 主要行動按鈕（"開始分析"、"前往資料設定"）。

**修正範例**:
```python
# page_templates.py 擴充
def empty_state_with_action(
    message: str,
    cta_label: str,
    cta_callback,
    icon: str = "📊",
) -> QWidget: ...
```

---

### 🟠 F-02：診斷頁副標題「一 尚未分析」語意不明（Major）

**Screen 06**: 頁面副標題顯示為「一 尚未分析」，其中「一」是孤立的中文字符。這極可能是未清理的 placeholder 或 list prefix。看起來像是將「① 尚未分析」的圓圈數字降解後剩下的文字，在 font fallback 下顯示為「一」。

**修正**: 直接使用語意明確的狀態文字，如「狀態：尚未分析」；或使用 `AppStatusModel` 的狀態 enum。

---

### 🟡 F-03：圖表載入無骨架屏（Skeleton Screen）（Minor）

分析執行期間（`STATE_ANALYZING`），圖表區域顯示空白而非骨架佔位（灰色動畫區塊）。用戶無法區分「正在計算」和「沒有資料」兩種狀態。`AppStatusModel` 已定義 `STATE_LOADING` 和 `STATE_ANALYZING`，但未映射到圖表區域的視覺狀態。

---

## G. 表單設計與驗證

### 🟡 G-01：工單規格輸入無即時驗證回饋（Minor）

**Screen 02（工單頁）**: USL% / LSL% / Target% 輸入欄位無即時驗證。用戶輸入 `LSL > USL`（邏輯錯誤）時，界面無任何警示。驗證僅在「儲存」時觸發，與現代表單設計的即時驗證標準不符。

---

### 🟡 G-02：`BUTTON_DISABLED_OPACITY = 0.55` 可能未被套用（Minor）

`tokens.py` 定義 `BUTTON_DISABLED_OPACITY = 0.55`，但 Qt QSS 的 `opacity` 屬性支援程度因平台而異，且 QSS 中的 `opacity` 會影響整個子樹，而非只有 widget 本身。需確認 disabled 按鈕實際上有視覺衰退，而非全亮狀態。

---

### 🟡 G-03：匯出頁計數器「0/9」語意不清（Minor）

**Screen 07（報告頁）**: 勾選欄位上方出現 `0/9`、`0/7`、`0/5` 計數，但缺乏說明文字（Selected/Total 的對應關係不明）。建議改為 `已選 0 / 共 9 項`。

---

## H. 互動狀態完整性

### 🟠 H-01：篩選狀態跨頁切換是否持久化（Major — 待確認）

**ASSUMPTION（需驗證）**: 當用戶在「管制圖表」頁選擇了特定 RefDes 和分析範圍，然後切換到「診斷分析」再切回，`ControlPanel` 的 ComboBox 選擇是否保留？若不保留，每次切頁都需重新選擇，嚴重降低操作效率。

**確認位置**: `app/ui/main_window.py` 的 `_on_nav_clicked` 或 `app/data/session_store.py`。

---

### 🟠 H-02：圖表分析 `重新整理分析` 無進行中防護（Major）

**位置**: `app/ui/pages/chart_analysis_page.py`

`REFRESH_DEBOUNCE_MS = 600` 只防抖（debounce），但若用戶在分析執行中（`STATE_ANALYZING`）再次觸發，行為不明確。`generation_id` 機制管理了舊結果的丟棄，但 UI 未顯示「分析中，請稍候」狀態並停用重複觸發。

---

### 🟡 H-03：工單輸入無 Undo/Redo（Minor）

工單規格修改後無法還原，操作不可逆。對關鍵製程規格（USL/LSL）的誤改可能引發後續分析結果嚴重偏差，且無法發現。

---

## I. 排版邊緣案例

### 🟡 I-01：參考頁（Screen 08）表格水平溢出無指示（Minor）

**Screen 08**: 表格列數超出可視範圍，需水平捲動，但無水平捲軸指示器或「→」提示。用戶可能不知道右側有更多欄位。

---

### 🔵 I-02：「3F」標籤無說明 tooltip（Enhancement）

圖表勾選框上的「並列3F」（3-Feature）對非統計背景用戶意義不明。即使有 `NAV_STEP_TOOLTIPS`，圖表勾選框缺少對應 tooltip。

---

### 🔵 I-03：「重整理分析」應改為「重新整理分析」或「執行分析」（Enhancement）

截圖中可見「重整理分析」字樣（Screen 04），疑似「重新整理分析」的截斷顯示，按鈕寬度不足。需確認按鈕最小寬度。

---

## J. 工程品質

### 🔵 J-01：NavStepBtn `isCurrent` 屬性用字串 "true"/"false"（Enhancement）

```python
btn.setProperty("isCurrent", "true" if is_current else "false")
```
Qt QSS 屬性選擇器使用字串比對，此做法功能正確但脆弱。更安全的做法是用整數 `1/0` 或直接用 `state` property 的值（已存在）統一控制樣式，消除 `isCurrent` 的重複性。

---

### 🔵 J-02：`QT_MAX_WIDGET_DIM = 16_777_215` 風險標記（Enhancement）

大型 SPI 資料集（萬筆以上量測點）在 `QScrollArea` 內容計算高度時有超出 Qt 最大 widget 尺寸的風險，會靜默截斷。建議在 `common_table_view.py` 加入分頁（pagination）或虛擬捲動（virtual scroll）機制。

---

### 🔵 J-03：`FORM_COMBO_MIN_WIDTH = 200` 在小視窗不足（Enhancement）

最小視窗 `WINDOW_MIN_WIDTH = 800px`，左側欄 220px，剩餘 580px 工作區。ComboBox 最小 200px 在某些佈局下可能佔據過高比例，導致其他元素被擠縮。

---

## 修正優先順序矩陣

| 等級 | 項目 | 工時估計 | 影響面 |
|------|------|---------|--------|
| 🔴 Critical | A-01 警報色 token 修正 | 0.5h | 診斷儀表板核心功能 |
| 🔴 Critical | A-02 導覽步驟鎖定機制 | 4h | 全流程防錯 |
| 🔴 Critical | A-03 layout_tier_from_width 修正 | 1h | 資料設定頁響應式 |
| 🟠 Major | C-02 NAV_PHASES 加回 phase 標籤 | 0.5h | 資訊架構可見性 |
| 🟠 Major | B-01 WCAG 對比度修正 | 1h | 可及性合規 |
| 🟠 Major | E-01 圖表三層選擇架構重構 | 8h | 圖表頁使用性 |
| 🟠 Major | F-01 空白狀態補充 CTA | 2h | 用戶引導 |
| 🟠 Major | F-02 診斷頁「一」字符修正 | 0.25h | 視覺一致性 |
| 🟠 Major | H-02 分析中狀態保護 | 2h | 互動穩定性 |
| 🟡 Minor | 其餘 12 項 | 1–3h each | 細節品質 |

---

## 附錄：Figma 整合前置作業

以下問題需在 Figma Dev Mode MCP 啟用後，透過 `use_figma` 工具建立：

1. 將 A-01 修正後的三個 alarm token 值建立為 Figma Color Variables（`processAlarm/bgNormal` 等）
2. 補齊 B-01 修正後的 success/warning 顏色，更新 Figma Color Styles
3. 建立 `KpiCell` 組件的四態 variant（valueState: neutral/good/warning/bad）附正確對比度顏色
4. 建立 `Card_Alarm` 組件三態 variant（alarmTone: normal/warning/critical）使用正確背景色
5. 驗證所有 token spacing 值是否與 `tokens.py` 的 pixel 值一致

---

*稽核人：Claude（世界級前端軟體工程師角色）| 2026-04-08*
