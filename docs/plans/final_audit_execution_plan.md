# Final Audit Execution Plan（最終稽核改善計劃）

## 1. Done Definition

本計劃完成條件（全部同時成立）：
1. `python scripts/run_final_audit_suite.py --repo-root . --profile full` 返回 `pass`
2. `Outputs/final_audit/<timestamp>/report.md` 與 `summary.json` 已產生
3. 若有 fail/blocked finding，已完成修復或在 `docs/open-questions.md` 留下可追蹤風險與 rollback

## 2. Output Format（固定）

- 主要輸出：`Outputs/final_audit/<timestamp>/report.md`
- 結構化輸出：`Outputs/final_audit/<timestamp>/summary.json`
- 程式證據：同目錄 gate log 檔案

## 3. Backward Plan（由結案往回）

### Phase 5: Closeout
- 目標：確認 `overall=pass`，且沒有未分流阻斷 finding。
- 動作：
  - 審核 `report.md` 的 gate table 與 exception scan。
  - 若涉及契約/流程變更，更新 `docs/decision-log.md`。
- 驗收：關帳結論可追溯到具體 log 與測試檔。

### Phase 4: Remediation Loop
- 目標：對 fail/blocked 階段執行對應 skill 修復。
- 動作：
  - `baseline` / `qt_policy` -> `code-audit`
  - `statistical_correctness` -> `spc-code-audit`
  - `chart_feature_cross` / `performance_baseline` -> `spc-chart-ui` + `smt-spi-self-heal`
  - `ui_runtime` -> `playwright-interactive` / `playwright`
- 驗收：重跑 full suite 後該階段轉為 `pass`。

### Phase 3: Performance + Runtime Validation
- 目標：確認圖表效能基線與 UI runtime 契約。
- 動作：
  - 執行 performance pack + UI runtime pack。
  - 必要時以 Playwright 重播多特徵交叉路徑。
- 驗收：效能與 UI runtime gate 全部通過。

### Phase 2: Statistical + Chart Contract Validation
- 目標：確保 SPC/SPI 統計語意與圖表契約一致。
- 動作：
  - 執行統計 pack、圖表/互動 pack。
  - 對 fail case 建立 root-cause 與最小修復方案。
- 驗收：兩個階段 gate 全部通過。

### Phase 1: Baseline Gate
- 目標：建立可交付最低品質門檻。
- 動作：
  - `ruff check .`
  - `mypy app`
  - `pytest -q`
- 驗收：baseline 皆為 `pass`，否則禁止進入 closeout。

## 4. MCP Usage Plan（稽核工具分工）

1. `shell_command`: 執行 gate、測試、基線驗證。
2. `filesystem`: 檔案掃描、稽核報告落地、修補追蹤。
3. `playwright` / `playwright-interactive`: 多特徵即時交叉 UI 路徑重播。
4. `web` + `openai_docs`: 外部依賴/官方契約查核（必要時）。
5. `database` + `chart`: 以結構化方式整理 trend/findings（必要時）。
6. `figma`: UI 實作與設計契約比對（需要設計一致性稽核時啟用）。

## 5. Execution Command

```bash
python scripts/run_final_audit_suite.py --repo-root . --profile full
```
