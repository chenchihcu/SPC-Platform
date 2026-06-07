# Reports 與 Archive 狀態分級（2026-03-26）

分級規則：

- `active`：可作現行規格/治理/驗證依據
- `historical`：歷史脈絡或稽核證據，保留但不作現行規格
- `deprecated`：內容已過時或被新文件覆蓋，建議標註
- `safe_to_delete`：重複、占位、或對當前維護無實質價值

## A. `docs/reports` 分級

| path | status | reason |
|---|---|---|
| `docs/reports/chart_contract_audit.md` | active | 仍被規格文件引用，屬圖表契約稽核基準 |
| `docs/reports/cjk_typography_remediation_report.md` | active | 對應 CJK 字重與驗收流程 |
| `docs/reports/document_alignment_report.md` | active | 文件/程式對齊歷史與案例來源 |
| `docs/reports/ui_refactor_patch_summary.md` | historical | 階段性改版摘要，非現行規格本體 |
| `docs/reports/ui_self_verification_report.md` | historical | 階段驗證紀錄，具追溯價值 |
| `docs/reports/IMPLEMENTATION_SUMMARY.md` | historical | 里程碑完成報告 |
| `docs/reports/TECHNICAL_VALIDATION_REPORT.md` | historical | 技術驗證快照 |
| `docs/reports/document_inventory_master.md` | active | 文件治理主清單 |
| `docs/reports/document_relocation_summary.md` | active | 搬移結果摘要 |
| `docs/reports/code_fact_snapshot_2026-03-26.md` | active | 本次對齊的程式碼事實來源 |
| `docs/reports/doc_code_alignment_matrix_2026-03-26.md` | active | 本次對齊差異矩陣 |

## B. `archive/unused` 分級與處置建議

### B1. `safe_to_delete`（建議刪除）

| path | reason |
|---|---|
| `archive/unused/samples/README.txt` | 樣本占位文字，無實質內容 |
| `archive/unused/samples/README__sample_data_measurement.txt` | 樣本占位文字，無實質內容 |
| `archive/unused/samples/README__sample_data_workorder.txt` | 樣本占位文字，無實質內容 |
| `archive/unused/reports/EXECUTION_SUMMARY.md` | 同批次完工敘事，與其他 final 類報告高度重複 |
| `archive/unused/reports/FINAL_VERIFICATION.md` | 同批次完工敘事，與其他 final 類報告高度重複 |
| `archive/unused/reports/IMPLEMENTATION_COMPLETE_REPORT.md` | 同批次完工敘事，與其他 final 類報告高度重複 |
| `archive/unused/reports/FINAL_COMPLETION_REPORT.md` | 同批次完工敘事，且已指向現行報告 |
| `archive/unused/governance/AI_RULES.md` | 治理來源已統一至 `docs/governance/AGENTS.md` |
| `archive/unused/governance/DOCUMENT_CONTROL_POLICY.md` | 治理來源已統一至 `docs/governance/AGENTS.md` |

### B2. `deprecated`（保留但需加註）

| path | reason |
|---|---|
| `archive/unused/reports/ui_audit_report.md` | 含多個待補/P2，與現況易產生偏差 |
| `archive/unused/reports/ui_refactor_integration_summary.md` | 階段整合摘要，非現行規格 |
| `archive/unused/reference/ui_two_column_form_page.md` | 歷史 layout 指南，與現行治理可能不一致 |

### B3. `historical`（建議保留）

其餘 `archive/unused` 文件保留為歷史決策、稽核與規格推導證據，不做現行規格依據。
