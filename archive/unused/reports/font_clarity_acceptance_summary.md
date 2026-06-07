# 字體清晰度驗收摘要（100% / 125% / 150%）

## 目標

- 僅提升文字渲染清晰度與可讀性。
- 不改動版面結構、互動語言與整體 Apple-like 視覺方向。

## 本次調整

- DPI 初始化：在 `run_app()` 建立 `QApplication` 前呼叫 `setup_high_dpi()`。
- DPI rounding policy：由 `PassThrough` 調整為 `RoundPreferFloor`，降低 125% 縮放常見子像素模糊。
- 字型 fallback：將 Windows 常見字型放在前位，降低 fallback 跳字造成的清晰度不一致。
- 文字 token 微調：
  - `FONT_SIZE_BODY`: 13 -> 14
  - `TEXT_SECONDARY`: 加深
  - `TEXT_MUTED`: 加深
  - `CHART_AXIS_TEXT`: 加深
  - `CAPTION_FONT_WEIGHT`: 500 -> 400
- QSS 定向優化（文字限定）：
  - `QLabel[class="caption"]`
  - `QLabel#statusBarLabel`
  - `QFormLayout QLabel`
  - `QHeaderView::section`
  - `QLabel[class="status-*"]`

## 自動化驗證

- `pytest -q`：`245 passed`（無行為回歸）
- Lint（本次修改檔案）：無新增問題

## 100% / 125% / 150% 清晰度檢查點

- 側欄 `ControlPanel` 小字：字邊緣與對比提升，狀態行辨識更穩定。
- `DiagnosticPage`（製程診斷儀表板）表頭/表格文字：表頭字重與字級更清楚，低對比環境可讀性提升。
- `StatusBarWidget` 狀態文字：字重與高度提高穩定性，縮放切換時更不易糊。
- 圖表軸標與註解：軸文字對比提升，不改圖表統計語意。

## 結論

- 已達成「僅清晰度優化」範圍，且未觸及風格重設、版面重排、分析邏輯修改。
