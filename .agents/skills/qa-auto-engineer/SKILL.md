---
name: qa-auto-engineer
version: 1.1.0
description: "自動操作 SPC/SPI Platform UI、擷取頁面截圖並輸出結構化缺失報告。Use when 要從頭到尾走本專案 UI 並產出 QA 缺失報告。Do NOT use for 通用 Playwright E2E（改用 automate-playwright-browser）、OS 桌面截圖（改用 capture-desktop-screenshot）或僅啟動 app（改用 run-spc）。"
---

# QA 自動工程師 — 端對端 UI 測試技能

自動操作 SPC/SPI Platform，發現視覺缺失、功能異常與效能瓶頸，產出結構化 QA 缺失報告。

---

## 1. 核心稽核守則

1. **資料庫隔離**：設定 `SPC_MASTER_DB_PATH` 指向本次 `Outputs/qa_report_*/test.db`，嚴禁寫入正式 `data/` 資料庫。
2. **動態 Tab 索引**：從 `app.ui.workflow_labels.VISIBLE_WORKFLOW_TABS` 取得頁籤名稱與 stack index，嚴禁寫死整數索引。
3. **證據分級**：幾何檢查僅列為 `CANDIDATE`；唯有截圖確認或可重現互動者方可列為 `CONFIRMED` 缺失。
4. **真實事件驅動**：核心互動（上傳、開始分析、重新分析、下一步、匯出）必須使用 `QTest.mouseClick` 觸發並驗證 `QSignalSpy`。
5. **程式內 Qt 截圖**：直接在 Python 內以 `MainWindow.grab().save(path, "PNG")` 存圖。

---

## 2. 標準執行流程 (Phases)

```
Phase 0: 建立 Outputs/qa_report_YYYYMMDD_HHMM/ 並初始化測試資料庫
Phase 1: 啟動 MainWindow (1360x820)，等待視窗穩定 (QTest.qWait(400))，擷取 00_startup.png
Phase 2: 頁籤巡迴 (依序切換各 Workflow Tab，擷取截圖並進行幾何/對齊/文字截斷分析)
Phase 3: 完整業務流程測試 (上傳測量 CSV -> 座標匹配 -> 執行分析 -> 產出報表)
Phase 4: 彙整缺失與證據 (分級 CRITICAL / MAJOR / MINOR / COSMETIC)
Phase 5: 產出結構化 QA_REPORT.md
```

---

## 3. Qt 程式內截圖範本

```python
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

app = QApplication.instance() or QApplication(sys.argv)
from app.ui.main_window import MainWindow
w = MainWindow()
w.resize(1360, 820)
w.show()
app.processEvents()
QTest.qWait(400)
w.grab().save("Outputs/qa_report_TIMESTAMP/00_startup.png", "PNG")
```

---

## 4. 缺失回報等級定義
- **CRITICAL**: 程式崩潰 (Crash)、無法啟動、資料庫寫入毀損、核心分析死鎖。
- **MAJOR**: 計算數據錯誤、按鈕點擊無反應、重大功能流程中斷。
- **MINOR**: 佈局溢出、滾動條遮擋、焦點跳轉錯誤、元件未自適應縮放。
- **COSMETIC**: 顏色代碼不一致、邊距微小不對齊、文案微調。