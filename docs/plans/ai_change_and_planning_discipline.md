# AI 變更與計畫擬定紀律（通用）

本文件與 `docs/governance/AGENTS.md` §11、§12、§13 搭配，用於預防：

1. **假設性結論**：依推測修改 A，卻改壞或漏改關聯的 B、C。  
2. **未找根因即下對策**：只在症狀處加 guard，不追溯資料／呼叫鏈。  
3. **計畫前置不足**：未盤點現況就寫「已採用某架構」或「版面已如此」。  
4. **計畫與程式長期脫節**：見 `docs/reports/document_alignment_report.md`。

**說明**：本倉庫若無 `.cursor/plans/*.md` 實體檔，仍以 `docs/reports/document_alignment_report.md` 中已稽核之計畫為 **案例來源**；之後新增計畫必須遵守本文件與 `.cursor/plans/README.md` 範本。

**整合入口**：**`docs/specs/issue_resolution_workflow.md`** 將 Preflight（§2 下）、根因（§3）、爆炸半徑（§4）與驗收／再發防止 **排成同一條可執行鏈**（步驟 1–7、閘門、L1/L2）。本文件提供 **細則與失敗模式**；執行順序以工作流為準。

---

## 1. 已稽核「過期／不一致」計畫 → 失敗模式 → 可建立之規則

以下對應 `docs/reports/document_alignment_report.md` 之結論（程式為權威來源）。

| 計畫（檔名） | 失敗模式（問題本質） | 預防規則（適用任何專案） |
|--------------|----------------------|---------------------------|
| `adaptive-toasting-ladybug.md`（`needs-archive`） | 計畫宣稱 **SQLite、透明取代 JSON registry、全寬三步驟、移除座標預覽**，與實際 **JSON registry、兩欄骨架、預覽表仍存在** 不符。 | **架構／持久化計畫前必做**：(1) `grep`／讀檔確認實際讀寫路徑與檔名；(2) 列出將被取代之模組與公開 API；(3) 計畫內 **禁止** 寫「已落地」除非能給出 **分支＋檔案＋行為證據**。 |
| `data_setup_流程版面重排_*.plan.md`（`needs-update`） | 宣稱 **同一 scroll 內** coord → upload 順序，實際為 **左欄 scroll（coord＋鋼板）＋右欄 upload**。 | **UI 流程計畫必附**：目標頁之 **widget 樹／layout 文字圖** 或 **檔案路徑＋關鍵變數名**（例如哪個 `QScrollArea` 包住誰）。順序宣稱必須可被對照到程式。 |
| `data-setup-single-page-2k-layout_*.plan.md`（`needs-update`） | 宣稱 **2K 無整頁捲軸／一頁式**，實際仍 **兩欄 template＋局部 QScrollArea**。 | **效能／版面 KPI** 必須 **可量測**（解析度、OS 縮放、何謂「整頁捲軸」、哪個容器可捲）；否則只能寫成 **階段目標** 並註明 **尚未驗收**。 |

**歸納成三條總規則**：

1. **證據優先**：計畫與修補都以 **可驗證事實**（讀碼、測試、log）為準，不以「理應如此」為準。  
2. **邊界定義**：凡涉及「順序、捲動範圍、持久化格式」者，必須 **指到實作邊界**（模組、容器、檔案）。  
3. **驗收可測**：宣稱使用者可見結果時，必須 **寫出如何判定通過**。

---

## 2. 計畫擬定前：強制前置措施（Preflight）

在寫入或執行任何 **多檔／跨層** 實作計畫前，Agent 必須完成下列 **最低限度**（可寫進計畫首節「現況盤點」）：

| 步驟 | 內容 | 產出 |
|------|------|------|
| P1 範圍 | 明確 **in-scope 檔案／模組** 與 **explicit non-goals** | 避免順手改到不相干 B |
| P2 現況證據 | 對持久化、路由、主要 UI：用 **grep／讀檔** 確認實際行為，**不得**僅依記憶或舊對話 | 路徑清單、關鍵呼叫點 |
| P3 依賴圖 | 列出 **上游（資料）／下游（UI、報表、測試）** | 改 A 時必查之 B、C |
| P4 規格對齊 | 對照 `docs/specs/spec_maintenance_and_alignment.md` 與相關契約 | 是否需先改規格 |
| P5 風險 | 若計畫前提與 P2 衝突，**先** 標註「與現況不符」或 **先** 更新計畫再實作 | 避免幽靈需求 |

**禁止**：在未完成 P2 的情況下，於計畫中撰寫「已採用 X 技術」「已移除 Y」。

---

## 3. 根因分析（RCA）再對策

與 `docs/governance/AGENTS.md` §11 一致，並補強 **「何時必須寫 RCA」**：

| 情境 | 最低要求 |
|------|----------|
| Bug 修復（非顯 typo） | 說明 **失敗行**、**錯誤資料形狀** 或 **錯誤狀態**，再寫對策；禁止只加 `try/except` 或 `if x is None` 而無上游追蹤。 |
| 跨模組症狀 | 畫出 **資料流** 或 **呼叫鏈** 再改；禁止只改第一個被看到的檔案。 |
| 重複出現的類似 bug | 執行 **橫向搜尋**（同 anti-pattern 全 repo），見 §4。 |

**可選格式**（簡短即可）：  
`觀察 → 直接原因 → 根因（例如：單一來源未更新）→ 對策 → 如何驗證`。

---

## 4. 關聯性與爆炸半徑（Blast radius）

預防「改了 A，假設 B 跟著對」：

1. **呼叫者與被呼叫者**：改公開函式／payload 鍵時，**必須** `grep` 符號與字串鍵。  
2. **雙軌路徑**：UI 與報表若共用語意，**必須** 確認是否共用 **單一** helper（見 `docs/governance/AGENTS.md` §7 single-source merge）。  
3. **並行同模式**：同一類錯誤（例如缺 `QScrollArea`）修一處後，**全 repo** 搜尋同模式。  
4. **契約變更**：變更欄位、狀態、單位時，同步更新 **文件＋測試＋** 依 `docs/specs/spec_maintenance_and_alignment.md` 列管之規格。

---

## 5. 計畫與實作檔案之最低欄位（範本）

完整 Markdown 範本見 **`.cursor/plans/README.md`**。計畫檔頂部建議包含：

- `Status`: `draft` | `ok` | `needs-update` | 與 `document_alignment` 一致之標記  
- `Evidence date`: 最近一次對照程式之日期  
- **現況盤點**（Preflight 表）  
- **根因**（若為修 bug 計畫）  
- **影響範圍**（模組、測試、規格）  
- **驗收**（可觀測條件）

---

## 6. 與既有文件的關係

| 文件 | 用途 |
|------|------|
| **`docs/specs/issue_resolution_workflow.md`** | **整合入口**：步驟順序、閘門、PR 檢查清單 |
| `docs/governance/AGENTS.md` §11–§13 | 強制工作流程與計畫紀律 |
| `docs/specs/spec_maintenance_and_alignment.md` | 規格與計畫生命週期 |
| `docs/reports/document_alignment_report.md` | 本 repo 計畫 vs 程式案例 |
| `.cursor/rules/ai-planning-and-root-cause.mdc` | Cursor 自動套用之簡要規則 |

---

## 7. 修訂紀錄

| 日期 | 摘要 |
|------|------|
| 2026-03-26 | 初版：由 document_alignment 過期計畫萃取失敗模式，並定義 Preflight／RCA／爆炸半徑規則。 |
| 2026-03-26 | 對應 **`docs/specs/issue_resolution_workflow.md`** 整合入口；§6 表格增列。 |
