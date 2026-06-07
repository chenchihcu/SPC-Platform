> [DEPRECATED] Historical snapshot only. Do not use as current specification.
> Reason: Contains phase-based pending items (P1/P2) that may not reflect current codebase state.

# UI 盤點報告（現有專案 UI 盤點與改進）

依據 [ui_design_spec.md](../../../docs/specs/ui_design_spec.md) 與 [app/ui/theme/tokens.py](../../../app/ui/theme/tokens.py) 進行盤點，產出對照表、內聯樣式清單與改進優先順序。

---

## 1. 畫面與元件對照表

| 區塊 | 規範章節 | 實作檔 | 符合度 | 備註 |
|------|----------|--------|--------|------|
| 主視窗 | §3 | [main_window.py](../../../app/ui/main_window.py) | 完全符合 | 兩欄 + StatusBar、Splitter |
| 左欄收合 | §3 | [collapsible_sidebar.py](../../../app/ui/widgets/collapsible_sidebar.py) | 完全符合 | 含導航 + 控制 + rail |
| 導航 | §4 | [navigation_panel.py](../../../app/ui/widgets/navigation_panel.py) | 完全符合 | 階段分組、active 樣式 |
| 控制面板 | §5 | [control_panel.py](../../../app/ui/widgets/control_panel.py) | 部分符合 | 狀態顏色為內聯 setStyleSheet |
| 資料設定 | §4 資料準備 | [data_setup_page.py](../../../app/ui/pages/data_setup_page.py) | 完全符合 | 含上傳 + 座標管理 |
| 工單 | §4 | [workorder_page.py](../../../app/ui/pages/workorder_page.py) | 部分符合 | 儲存按鈕回饋為內聯 setStyleSheet |
| 元件/量測選定 | §4 | [component_select_page.py](../../../app/ui/pages/component_select_page.py) | 完全符合 | |
| 製程診斷儀表板 | §4 | [diagnostic_page.py](../../../app/ui/pages/diagnostic_page.py)（舊名 `statistics_page.py`） | 完全符合 | |
| 圖表分析 | §4 + §6.1 | [chart_analysis_page.py](../../../app/ui/pages/chart_analysis_page.py) + 各 tab | 部分符合 | 圖表 placeholder 為內聯樣式、文案未統一 tokens |
| 報告輸出 | §4 | [report_export_page.py](../../../app/ui/pages/report_export_page.py) | 完全符合 | |
| 資料管理 | §4 | [data_management_page.py](../../../app/ui/pages/data_management_page.py) | 完全符合 | |
| 空狀態 | §14 | [placeholder_view.py](../../../app/ui/widgets/placeholder_view.py) + tokens.EMPTY_* | 待補 | PlaceholderView 未被使用；圖表使用 BaseChart 內建 placeholder，文案未用 EMPTY_SELECT_BATCH/ERROR_* |
| 錯誤提示 | §19 | tokens.ERROR_* | 待補 | 四類錯誤文案已定義，各頁/圖表未一致引用 |

---

## 2. Token 與樣式一致性

### 2.1 QSS 與 tokens

- [dark_stylesheet.py](../../../app/ui/theme/dark_stylesheet.py) 多數已引用 tokens；以下為**硬編碼**：
  - 按鈕/列表/捲軸 hover：`#3d3d3d`, `#505050`, `#353535`, `#2196F3`, `#388E3C`, `#b71c1c`, `#2a2a2a`, `#606060`
  - 導航區：`#FDF5E0`, `#2F4F4F`, `#F5F5DC`, `#3d5f5f`, `#404040`
- 建議：hover/active 色可擇要加入 tokens；導航區可新增 NAV_* tokens 以集中管理。

### 2.2 內聯樣式清單與建議

| 檔案 | 行號 | 現狀 | 建議 |
|------|------|------|------|
| [workorder_page.py](../../../app/ui/pages/workorder_page.py) | 101, 106, 110 | btn_save 依成功/失敗/預設 setStyleSheet | 改為動態 property（如 saveState），QSS 內用 #workorderSaveBtn[saveState="success"] 等 |
| [control_panel.py](../../../app/ui/widgets/control_panel.py) | 75, 117–126 | 狀態 QLabel 以 setStyleSheet 設顏色 | 改為 setProperty("class", "status-ok") / "status-error"，沿用 QSS 既有 QLabel[class="status-ok"] |
| [placeholder_view.py](../../../app/ui/widgets/placeholder_view.py) | 20 | lbl_msg 內聯 font-size + color | 新增 QSS 類別（如 placeholderMessage），用 tokens |
| [status_bar.py](../../../app/ui/widgets/status_bar.py) | 14 | _label 內聯 color + font-size | 新增 QSS 類別（如 statusBarLabel）或 objectName，用 tokens |
| [base_chart.py](../../../app/charts/base_chart.py) | 58 | placeholder QLabel 內聯 color + font-size | 新增 QSS 類別（如 chartPlaceholder），文案改用 tokens.ERROR_NO_DATA |
| [theme/__init__.py](../../../app/ui/theme/__init__.py) | 32, 45–46 | app.setStyleSheet / msgbox | 保留（全域與 QMessageBox 樣式注入，非元件內聯） |

### 2.3 Typography / 間距

- 各頁標題已普遍使用 `pageTitle`，說明使用 `description`，路徑/輔助文字使用 `caption`。
- 僅少數元件仍寫死字級（如 placeholder 14px），改為 token 或 QSS 類別即可統一。

---

## 3. 行為與規範對照

- **§18 風格**：工程軟體、高資訊密度、清晰圖表；目前符合，無過度裝飾。
- **§17 DPI**：main.py 已呼叫 `setup_high_dpi()`，[dpi.py](../../../app/bootstrap/dpi.py) 使用 `PassThrough`。**驗證建議**：於 Windows 顯示設定 100%、125%、150% 縮放下，分別檢查「資料設定」頁與左欄（導航、分析條件、資料狀態）是否有 label 裁切、元件重疊或文字模糊；若有問題再調整 QSS 字級或 layout 最小尺寸。未做實機截圖驗證前列為 P2。
- **§19 錯誤提示**：ERROR_NO_DATA / ERROR_NO_FIELDS / ERROR_NO_RELATION / ERROR_INSUFFICIENT_DATA 與 EMPTY_SELECT_BATCH 已定義，圖表與空狀態文案尚未統一引用，列為 P1。

---

## 4. 改進優先順序（Phase 2）

| 優先級 | 項目 | 說明 |
|--------|------|------|
| **P0** | （無） | 無影響正確性/可用性之缺口 |
| **P1** | 控制面板狀態顏色 | 改為 QSS class（status-ok/status-error），移除內聯 setStyleSheet |
| **P1** | 工單儲存按鈕回饋 | 改為動態 property + QSS，移除內聯 setStyleSheet |
| **P1** | PlaceholderView / 圖表 placeholder | 改用 QSS 類別 + tokens，圖表預設文案改用 ERROR_NO_DATA |
| **P1** | 狀態列標籤 | 改用 QSS 類別或 objectName，移除內聯 setStyleSheet |
| **P2** | QSS 硬編碼色碼 | 導航區與 hover 色納入 tokens（可選、分批） |
| **P2** | DPI 驗證 | 125%/150% 實機檢查 label clipping / overlap |
| **P2** | 錯誤/空狀態文案統一 | 各 chart 與空狀態改用 tokens.ERROR_* / EMPTY_SELECT_BATCH |

---

## 5. 產出與後續

- 本報告為 Phase 1 產出；Phase 2 優先順序已列入上表。
- **Phase 3（P1）已實作**：
  - 控制面板：狀態標籤改為 `setProperty("class", "status-ok"|"status-error")`，移除內聯 setStyleSheet。
  - 工單儲存按鈕：改為動態 property `saveState`（success/failure/default）+ QSS `#workorderSaveBtn[saveState="..."]`，並以 unpolish/polish 觸發樣式更新。
  - PlaceholderView：訊息標籤改為 class `placeholderMessage`，由 QSS 與 `FONT_SIZE_PLACEHOLDER` token 控制。
  - 狀態列：標籤改為 `objectName="statusBarLabel"`，樣式由 QSS 統一。
  - 圖表 BaseChart：placeholder 文案改為 `ERROR_NO_DATA`，樣式改為 class `chartPlaceholder`。
  - tokens 新增 `FONT_SIZE_PLACEHOLDER`；dark_stylesheet 新增上述選擇器。
- P2（QSS 硬編碼色、錯誤文案全面統一）可於後續迭代進行。
- **導航區**：導航區色碼已納入 tokens（NAV_PHASE_*、NAV_STEP_*），見 [tokens.py](../../../app/ui/theme/tokens.py) 與 [dark_stylesheet.py](../../../app/ui/theme/dark_stylesheet.py)。
- **資料設定頁**：文案「徑層」已改為「路徑」；空狀態使用 tokens（EMPTY_MEAS_FILE、EMPTY_COORD_SET）；版面間距使用 SPACING_MD / SPACING_LG。
