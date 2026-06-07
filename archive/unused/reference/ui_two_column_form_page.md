> [DEPRECATED] Historical guidance only. Do not use as current specification.
> Reason: This page-layout guidance may diverge from current governance and latest implementation.

# 雙欄工程表單頁 (Two-column form page) 版面規範

本文件整理「雙欄工程表單頁」的 layout pattern，供工單資料輸入等頁面及後續同類頁面沿用。

## 實作位置

- **Layout 輔助**：`app/ui/widgets/page_templates.py`  
  - `setup_two_column_form_page(layout, page_title)` → 回傳 `TwoColumnFormPageLayout`
  - 使用前需先對頁面根 layout 套用 `page_margins_and_spacing(layout)`
- **Tokens**：`app/ui/theme/tokens.py`（間距、欄寬、GroupBox 標題留白）
- **範例頁**：`app/ui/pages/workorder_page.py`（工單資料輸入）

---

## 1. Page header 區

- 頁面標題使用 `QLabel` + `class="pageTitle"`，由 `setup_two_column_form_page` 建立並加入 layout。
- 標題與主內容區之間間距由 token **PAGE_HEADER_BOTTOM_SPACING**（預設 12px）控制，避免與內容貼太緊或過鬆。

---

## 2. 2-column content layout

- 主內容區為滿版（無 max-width 置中），左右兩欄以 **TWO_COLUMN_STRETCH_LEFT / TWO_COLUMN_STRETCH_RIGHT**（預設 1:1）分配寬度，必要時可改為 9:11 微調 45:55。
- 左右欄之間間距：**TWO_COLUMN_CONTENT_SPACING**（16px）。
- 單欄最小寬度：**TWO_COLUMN_MIN_COLUMN_WIDTH**（280px），避免過度壓縮。
- 左欄放主要表單區塊（如工單主檔），右欄放次要或並列區塊（如管制規格）；兩欄頂部對齊。

---

## 3. Group box 統一樣式

- 表單區塊使用全域 `QGroupBox` 樣式（`app/ui/theme/dark_stylesheet.py`），不在此 pattern 內覆寫。
- 內距與 tokens 對齊時可參考 **GROUPBOX_CONTENT_PADDING_H / GROUPBOX_CONTENT_PADDING_V**（與 QSS 一致即可）。

---

## 4. Page primary action 區

- 雙欄下方單一橫列，用於本頁主操作（例如「儲存設定」）。
- 與雙欄內容之間間距：**PRIMARY_ACTION_TOP_SPACING**（16px）。
- 按鈕加入 `TwoColumnFormPageLayout.primary_action_layout`（QHBoxLayout），可依需求在左側加入 stretch 置中或靠左。

---

## 5. Section title 避免與框線重疊的統一規則

- **QGroupBox 標題**：樣式使用 `QGroupBox::title` 的 `subcontrol-origin: margin`，標題繪製在 margin 區。
- Token **GROUPBOX_TITLE_MARGIN_TOP** 須足夠容納標題字級行高（建議 ≥ 18px），否則標題會與框線或上方區塊重疊。
- 左側 Control Panel 等有多個 GroupBox 連續排列時，區塊之間可多加 **addSpacing**，與 GROUPBOX_TITLE_MARGIN_TOP 搭配，避免「資料狀態」等標題與「分析條件」內容視覺重疊。

---

## 使用範例

```python
layout = QVBoxLayout(self)
page_margins_and_spacing(layout)
page_layout = setup_two_column_form_page(layout, "工單資料輸入 (Workorder Input)")

page_layout.left_column.layout().addWidget(wo_group)
page_layout.right_column.layout().addWidget(spec_group)
page_layout.primary_action_layout.addWidget(btn_save)
```

其他同類頁面（例如未來若有「參數設定」雙欄表單）可依此 pattern 與 tokens 沿用，保持版面一致。
