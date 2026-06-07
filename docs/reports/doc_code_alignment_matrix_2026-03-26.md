# 文件/程式對齊差異矩陣（2026-03-26）

對齊基準：`docs/reports/code_fact_snapshot_2026-03-26.md`

| 文件 | 差異類型 | 現況 | 對齊動作 |
|---|---|---|---|
| `docs/governance/AGENTS.md` | 文件過時（路徑） | 引用 `.cursor/rules/docs/reference/platform_overview.md`、`.cursor/plans/docs/reference/platform_overview.md` 不存在 | 改為 `.cursor/rules/README.md`、`.cursor/plans/README.md` |
| `docs/specs/spec_maintenance_and_alignment.md` | 文件過時（路徑） | 多處引用不存在的 `.cursor/*/platform_overview.md` | 改為 `.cursor/rules/README.md`、`.cursor/plans/README.md` |
| `docs/specs/issue_resolution_workflow.md` | 文件過時（路徑） | 使用不存在的 `.cursor/plans/docs/reference/platform_overview.md` | 改為 `.cursor/plans/README.md` |
| `docs/specs/workflow_governance_monthly_checklist.md` | 文件過時（路徑） | checklist 指向 `.cursor/rules/docs/reference/platform_overview.md` | 改為 `.cursor/rules/README.md` |
| `docs/specs/ui_design_spec.md` | 文件過時（文案） | 控制按鈕文案仍寫「重新整理批次」 | 改為「重新整理分析」（與程式一致） |
| `docs/specs/data_contract.md` | 文件需補強（現況快照） | 契約原則完整，但缺少「本次對齊快照」 | 新增「2026-03-26 實作對齊快照」段落 |
| `docs/reports/*` | 歷史記錄 | 多份為階段/完成報告，非現行規格 | 保留為報告，不作為規格來源 |
| `archive/unused/*` | 歷史記錄/待刪候選 | 已不被引用；部分為重複完工報告 | 以 triage 清單標記 `historical/deprecated/safe_to_delete` |

## 分類定義

- `一致`：文件可直接對應目前程式行為
- `文件過時（需改文）`：內容或路徑與現況不符
- `歷史記錄（保留）`：可作稽核追溯，不作現行規格
- `誤導/重複（建議移除）`：對當前維護無幫助且可能混淆
