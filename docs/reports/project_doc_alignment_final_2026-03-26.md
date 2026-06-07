# 專案/文件對齊最終總表（2026-03-26）

## 1) 對齊基準

- 基準原則：以程式碼可驗證行為為準（Code as Source of Truth）。
- 程式碼事實來源：`docs/reports/code_fact_snapshot_2026-03-26.md`
- 差異矩陣來源：`docs/reports/doc_code_alignment_matrix_2026-03-26.md`
- 歷史文件處置來源：`docs/reports/reports_and_archive_triage_2026-03-26.md`

## 2) 本次完成的對齊動作

| 類別 | 文件 | 動作 |
|---|---|---|
| governance | `docs/governance/AGENTS.md` | 修正不存在的 `.cursor/*/platform_overview.md` 連結 |
| specs | `docs/specs/spec_maintenance_and_alignment.md` | 修正 `.cursor/rules/README.md`、`.cursor/plans/README.md` 對應路徑與修訂紀錄 |
| specs | `docs/specs/issue_resolution_workflow.md` | 修正計畫模板引用路徑為 `.cursor/plans/README.md` |
| specs | `docs/specs/workflow_governance_monthly_checklist.md` | 修正 Cursor Rules README 路徑 |
| specs | `docs/specs/ui_design_spec.md` | 控制按鈕文案對齊程式（`重新整理分析`）並補 2026-03-26 實作快照 |
| specs | `docs/specs/data_contract.md` | 新增 2026-03-26 實作對齊快照（規格解析/拒絕分析/預設值） |
| reports | `docs/reports/reports_and_archive_triage_2026-03-26.md` | 新增 reports 與 archive 狀態分級與刪除候選 |

## 3) 狀態結論

- `docs/governance`：關鍵路徑已與實際檔案存在性對齊。
- `docs/specs`：核心規格已補齊程式碼快照，並移除失效路徑引用。
- `docs/reports`：現行有效報告與歷史快照已分級。
- `archive/unused`：已有 `safe_to_delete / deprecated / historical` 處置建議，可進入人工確認後清理。

## 4) 驗證結果

- Markdown 本地連結完整性：`BROKEN 0`
- 本次新增對齊產出：
  - `docs/reports/code_fact_snapshot_2026-03-26.md`
  - `docs/reports/doc_code_alignment_matrix_2026-03-26.md`
  - `docs/reports/reports_and_archive_triage_2026-03-26.md`
  - `docs/reports/project_doc_alignment_final_2026-03-26.md`

## 5) 後續建議（可選）

1. 依 triage 清單先刪除 `safe_to_delete` 文件（9 份），再重跑 inventory。
2. 對 `deprecated` 文件加上檔頭註記（Historical/Do not use as current spec）。
3. 每月依 `docs/specs/workflow_governance_monthly_checklist.md` 做一次路徑與規格一致性稽核。
