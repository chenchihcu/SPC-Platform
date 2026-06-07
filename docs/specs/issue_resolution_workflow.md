# 問題解決與變更工作流（整合入口）

本文件是 **單一導航入口**：把「現象 → 證據 → 根因 → 橫向影響 → 對策 → 驗證 → 再發防止 → 結案」串成 **可重複執行的步驟**，避免規則散落在多份文件卻無法依序執行。  
細則不重複全文，只 **指向** 既有權威章節；與 **8D／CAPA** 精神對齊，但不取代產品規格（`ui_design_spec`、`data_contract` 等）。

**權威順序**仍依 `docs/specs/spec_maintenance_and_alignment.md` 開頭所列（程式可驗證行為 > `docs/governance/SPC_RULES.md` > 明示規格 > 計畫）。

---

## 0. 何時走完整流程（層級）

| 層級 | 典型情形 | 最低要求 |
|------|----------|----------|
| **L1 輕量** | 單檔 typo、註解、無行為變更之明顯修正 | 若觸及測試覆蓋區，仍執行相關 `pytest`。 |
| **L2 標準** | 非顯而易見的 bug、**跨模組**、使用者可見行為、資料形狀／API／圖表／全域 QSS | **自步驟 1 依序做到步驟 7**，並保留證據（PR 描述、計畫節、或 issue 附註）。 |

**判斷不確定時，採 L2**，避免「以為是小改」卻漏掉橫向關聯。

### AI 初判入口（fail-safe）

建議以 AI 做第一層分流，但最終裁決採 fail-safe 規則（見 `docs/governance/GLOBAL_PLAN_FRAMEWORK_V2_2.md`）：

- 先判斷硬觸發（`ui/data/contract`、簽章/API/payload 變更、migration SQL、跨 >=2 子系統、RCA 不清楚）。
- 任一硬觸發 = true -> 直接走完整路徑（`Full` / 對應本文件 `L2`）。
- 無硬觸發時再看信心：`confidence < 0.85` -> 走完整路徑。
- 僅在「無硬觸發且 `confidence >= 0.85`」才可走 `L1`。
- 僅允許人工升級 `L1 -> Full`；禁止降級 `Full -> L1`。

---

## 1. 整合步驟與閘門（對應 8D 精簡）

「閘門」＝進入下一步前 **必須** 產出的最小產物；缺少則視為流程未完成。

| 步驟 | 名稱（8D 對照） | 閘門（必備產物） | 權威文件／工具 |
|------|-----------------|------------------|----------------|
| **1** | **問題與範圍**（D2） | 可重現步驟或資料條件；**in-scope / non-goals** 一句話 | `.cursor/plans/README.md`（計畫章節與證據欄位）；計畫檔頭 `status` / `evidence_date` |
| **2** | **現況證據**（Preflight） | 至少一項 **程式證據**：失敗點（檔案／函式）、或 log／診斷輸出；**禁止**僅憑推測改碼 | `docs/plans/ai_change_and_planning_discipline.md` §2 Preflight |
| **3** | **根因分析**（D4） | **觀察 → 直接原因 → 根因 → 擬定對策** 鏈；對策必須對應根因（非僅症狀 guard） | `docs/governance/AGENTS.md` §11；`docs/plans/ai_change_and_planning_discipline.md` §3 |
| **4** | **橫向與爆炸半徑**（修 A 不漏 B） | **上游／下游清單**；對公開符號、payload 鍵、`grep` 同 pattern；圖表語意是否 **單一來源** | `docs/plans/ai_change_and_planning_discipline.md` §4；`docs/governance/AGENTS.md` §7（圖表 merge）、§11（橫向搜尋） |
| **5** | **永久對策**（D5） | 變更符合 **小步、單一問題類型**；不擅自改動禁止之公開介面（見 `docs/governance/AGENTS.md` §5） | `docs/governance/AGENTS.md` §5 |
| **6** | **實施與驗證**（D6） | **`pytest -q` 通過**（行為有變時必測）；領域特有驗證依下表 | `docs/governance/AGENTS.md` §5（測試）；本節 §6 附表 |
| **7** | **再發防止與結案**（D7／D8） | 規格／計畫狀態更新；**至少一項**可審計：新測試、文件觸發列、或凍結規則；計畫標 `ok` / `needs-update` | `docs/specs/spec_maintenance_and_alignment.md` §1、§2；`.cursor/plans/README.md` |

**暫時防堵（D3）**：僅在需要 **先止血**（例如產線阻斷）時採用；須註明「暫時」與 **後續仍須完成步驟 3–7**，避免暫時變成永久。

---

## 2. 驗證附表（領域對照）

| 變更類型 | 除 `pytest` 外須對照 |
|----------|----------------------|
| 全域 QSS／字型／`FONT_FAMILY` | `docs/specs/spec_maintenance_and_alignment.md` **§4.1**（三層有效性驗證）；`tests/test_ui_font_caps.py` 字重凍結 |
| UI 版面／響應式／DPI 宣稱 | 同文件 **§3**；須寫清解析度／縮放／容器 |
| 統計門檻、公式、樣本 | **`docs/governance/SPC_RULES.md` 先於程式** |
| 資料欄位、payload、圖表 slice | `docs/specs/data_contract.md`、`docs/reports/chart_contract_audit.md`（依觸發更新 §1） |

---

## 3. 與其他文件的關係（整合而非取代）

| 文件 | 在本工作流中的角色 |
|------|---------------------|
| **本文件** | **從哪一步開始、閘門是什麼** |
| `docs/specs/ui_design_spec.md` §22 | UI 規格維護與驗收要點；與本工作流 **互補**（架構／原則 vs 操作順序） |
| `docs/governance/AGENTS.md` §11–§13 | 強制行為：證據、橫向、規格對齊 |
| `docs/plans/ai_change_and_planning_discipline.md` | Preflight、RCA 格式、爆炸半徑 |
| `docs/specs/spec_maintenance_and_alignment.md` | 何時更新規格、計畫生命週期、§4.1 驗證 |
| `docs/specs/workflow_governance_monthly_checklist.md` | 每月流程治理稽核（規則對齊、L2 品質、Blast、回歸守門） |
| `docs/governance/GLOBAL_PLAN_FRAMEWORK_V2_2.md` | 跨專案可複用之計畫框架（永久單人模型、Gate A~F pass/fail criteria、AGENTS 深度核對） |
| `docs/templates/PLAN.md` | 任務計畫實作模板（可直接複製） |
| `.cursor/plans/README.md` | 計畫檔章節與證據日期 |
| `docs/reports/document_alignment_report.md` | 計畫 vs 程式案例（避免重複過期敘述） |

---

## 4. 一頁式檢查清單（可複製到 PR 或 issue）

**PR 開啟時**：若使用 GitHub，預設會載入 **`.github/pull_request_template.md`**（精簡勾選）。  
**結構化全文**：複製 **`docs/specs/ai_agent_response_template.md`**。

```markdown
- [ ] L2？若否，註明為 L1 及理由
- [ ] 步驟 1：可重現／範圍與 non-goals
- [ ] 步驟 2：程式或 log 證據（路徑或片段）
- [ ] 步驟 3：根因鏈；對策對應根因（非僅症狀）
- [ ] 步驟 4：上游／下游；grep 同 pattern；圖表單一來源已查
- [ ] 步驟 5：符合 AGENTS §5（小步、介面未違規）
- [ ] 步驟 6：pytest；§2 附表領域驗證（若適用）
- [ ] 步驟 7：規格／計畫／測試或凍結規則至少一項已更新或註明「無需」
```

---

## 5. 修訂紀錄

| 日期 | 摘要 |
|------|------|
| 2026-03-26 | 初版：整合入口，對齊 8D 精簡步驟與既有 Preflight／RCA／§4.1。 |
| 2026-03-26 | §3 表格增列 `docs/specs/ui_design_spec.md` §22；與 README、`ui_design_spec` 雙向對照。 |
| 2026-03-26 | §4 對照 **PR 模板**（`.github/pull_request_template.md`）與 **`docs/specs/ai_agent_response_template.md`**；常駐規則見 `.cursor/rules/agent-residence-minimal.mdc`。 |
| 2026-03-26 | §3 表格增列 `docs/specs/workflow_governance_monthly_checklist.md`，落地月度治理稽核。 |
