# AI 幻覺重工預防矩陣（單一權威）

## 1. 範圍與目的

本文件用於盤查「AI 幻覺或假設錯誤導致重複修改」事件，並提供低 token 的預防機制，供 rules/skills 直接採用。

- 盤查範圍（全歷史）：`docs/decision-log.md`、`docs/reports/*.md`、`docs/governance/*.md`
- 目標：降低「文件漂移 -> 反覆修補 -> 再次漂移」循環
- 非目標：重寫歷史快照內容、改動統計公式或執行程式邏輯

## 2. 高頻重工主題（2026-04 歷史）

1. Validation gates 漂移（CI 與 repo 實際閘門不一致）
2. Docs alignment 漂移（路徑、命名、堆疊與導覽描述不同步）
3. Report contract 漂移（PPTX-only 收斂前後的舊 HTML/template 殘留）
4. Chart/Data contract 漂移（分類、payload、sample-integrity 語意不一致）
5. UI 頁面命名漂移（`StatisticsPage` / `DiagnosticPage` 交錯）

## 3. 規則矩陣（事件族群）

| 事件/日期區間 | 幻覺型錯誤假設 | 重複修改症狀 | 正確根因 | 已採修正 | 預防規則 | 必跑驗證閘 | 來源證據路徑 |
|---|---|---|---|---|---|---|---|
| Validation gate 收斂（2026-04-05~2026-04-08） | 「CI 已等同 repo gate，不需再補」 | 同一條件在本地與 CI 反覆失敗 | gate 定義分散於 workflow、README、AGENTS 且不同步 | workflow 納入 `qt_audit` + `check_launch`，文件同步 | 任何 gate 變更必須同改 workflow + README + architecture + decision-log | `ruff`、`mypy app`、`pytest -q`、`check_launch` | `docs/decision-log.md`（2026-04-08 條目） |
| 文件路徑與敘述漂移（2026-04-02~2026-04-19） | 「文件已是最新，不需對照程式」 | 多輪僅修文案但仍持續失配 | 權威來源未明確綁定程式路徑，歷史快照與現行規格混讀 | 多份 docs 改為完整路徑與 superseded 註記 | 文檔更新前先核對權威程式（`main_window.py`/`chart_registry.py`/`report_service.py`） | 文件連結可開啟 + 核心閘門全跑 | `docs/decision-log.md`（2026-04-06 多條 docs convergence） |
| 報告輸出契約震盪（2026-04-01~2026-04-06） | 「仍支援雙模板或 HTML UI 匯出」 | 匯出流程相關文案反覆改寫 | UI/Service 已收斂到 engineering-only PPTX，但舊字串殘留 | 收斂為 `template_type=engineering`、移除 UI template 切換 | 涉及 report contract 的變更，先查 `report_service.generate_pptx_report` 與 `ReportExportPage` | `pytest -q` + `check_launch` | `docs/decision-log.md`（Report export 系列條目） |
| 圖表分類與根因流程不一致（2026-04-02~2026-04-08） | 「分類名稱只改 UI 文字即可」 | 同一 chart 在 registry/UI/report 分類不一致 | chart taxonomy、root-cause flow 與套餐映射未同時更新 | 收斂為五大分類與五段 root-cause flow | `chart_registry` 變更必同步 UI/測試/文件 | `pytest -q`（含 registry 合約測試） | `docs/decision-log.md`（2026-04-08 taxonomy 條目） |
| 頁面命名漂移（2026-04-02~2026-04-08） | 「Statistics/Diagnostic 混用不影響」 | 文件與測試名稱反覆修正、cache 殘留 | 歷史條目保留舊名，但現行頁面已改為 `DiagnosticPage` | 主線文件改以 `DiagnosticPage` 為現行；歷史快照加註 superseded | 文件提到頁名時，先對照 `app/ui/main_window.py` 與真實檔案存在性 | 文件一致性檢查 + `pytest --cache-clear -q`（必要時） | `docs/decision-log.md`（2026-04-06 命名收斂條目） |
| 資料契約與持久化語意混用（2026-04-03~2026-04-06） | 「JSON/SQLite 或 golden 路徑可以共存且不需註明權威」 | 針對資料來源路徑反覆修文與補測 | 持久化遷移後，權威資料路徑未統一標示 | 明示 `data/spc_master.db`、`golden_dataset/`、`GOLDEN_DATASET_ROOT` 契約 | 任何資料契約路徑變更都要同步 data_contract + architecture + release docs | `mypy app` + `pytest -q` + `check_launch` | `docs/decision-log.md`（2026-04-03/05 條目） |

## 4. 低 Token 預防流程（5 步驟）

1. **Preflight 最小查證**：先讀 3 個權威點（程式入口、契約入口、最新 decision-log）再動手。
2. **停止條件**：若同一概念存在兩種說法（例如頁名/匯出契約）且程式證據不足，先停在查證，不直接改檔。
3. **文件單改條件**：僅在「程式已正確、文件失配」時才做 docs-only 變更。
4. **全閘門條件**：只要碰到契約詞（gate、payload、template、stack/nav、DB path），一律跑完整四閘（ruff/mypy/pytest/check_launch）。
5. **收斂輸出**：每次修正都追加 `decision-log` 一條，避免下次重複判斷上下文。

## 5. 可直接貼入 Rules/Skills 的短模板

### Prompt Guard

```text
先驗證再修改：至少比對 main_window.py、chart_registry.py、report_service.py 三個權威點。
若與文件衝突，以可驗證程式行為為準；歷史快照只能標註 superseded，不覆寫歷史內容。
```

### RCA Guard

```text
先回答四句：現象是什麼、直接原因是什麼、根因是什麼、哪個單一修正可以阻止重複發生。
禁止只改文案或只加保護條件而不修正根因契約。
```

### Blast-Radius Guard

```text
任何契約字詞變更（頁名、導航、template、payload、gate）必查四處：
1) 程式權威 2) 測試 3) 核心規格 4) decision-log。
若四處未同改，變更視為未完成。
```

## 6. 維護規則

- 本文件為 rules/skills 優化的單一入口，新增事件族群時只在此處擴充。
- 新增條目必須附可開啟的 repo 路徑證據，不接受純敘述。
- 若流程或 gate 更新，需同步 `docs/decision-log.md` 與 `docs/README.md` 文件地圖。
