# 文件總覽（Current）

本檔提供 `docs/` 目錄的快速導覽（**2026-05-25** 對齊版）。

## 主要入口

- 專案首頁與快速啟動：`README.md`（repo root）
- 高層總覽（精簡）：`docs/reference/platform_overview.md`
- 系統架構規格：`docs/specs/project_architecture.md`
- 規格維護治理：`docs/specs/spec_maintenance_and_alignment.md`
- 全域計畫框架（永久單人版）：`docs/governance/GLOBAL_PLAN_FRAMEWORK_V2_2.md`
- 計畫模板（可直接複製）：`docs/templates/PLAN.md`
- 決策紀錄：`docs/decision-log.md`
- 開放問題（active risk single source）：`docs/open-questions.md`

## 架構與導覽文件一覽表

| 路徑 | 主要讀者 | 內容重點 | 何時必須更新 |
|------|----------|----------|--------------|
| `README.md`（repo root） | 新進開發者、維運 | 快速啟動、runtime 流程精簡圖、目錄快照、驗證指令、文件地圖 | 入口流程、CI 指令、主線功能摘要變更時 |
| `docs/specs/project_architecture.md` | 開發者、架構檢閱 | 分層架構、UI 頁面、分析管線、圖表／報告契約、主資料 DB、驗證基線 | 模組邊界、頁面堆疊、registry／報告契約、持久化變更時（並同步 `docs/specs/data_contract.md`／`docs/decision-log.md` 等） |
| `docs/reference/platform_overview.md` | 需快速掃描者 | 系統定位、關鍵檔案路徑、啟動與品質基線、重要文件連結 | 與 root README／架構規格脫節時；以該兩份為權威校正本檔 |
| `docs/specs/data_contract.md` | 資料／分析開發者 | 欄位、映射、payload、工程報告匯出契約（PPTX only） | 匯入結構、圖表 payload、報告輸出契約變更時 |
| `docs/specs/ui_design_spec.md` | UI／產品 | 版面、流程、報告頁行為、設計原則 | 使用者可見版面、互動、報告 UI 契約變更時 |
| `docs/specs/process_dashboard_figma_alignment.md` | UI／設計 | 製程統計分析欄位網格、token、Figma 元件與 `use_figma` 檢查清單 | `DiagnosticPage`／製程統計分析 QSS 或欄位配置變更時 |
| `docs/governance/SPC_RULES.md` | 統計／品質工程 | 公式、常數、解讀門檻（統計權威） | **規格先於程式**：變更 Cp/Cpk、管制圖常數等時 |
| `docs/governance/GLOBAL_PLAN_FRAMEWORK_V2_2.md` | 跨專案治理／代理 | 全域計畫框架 v2.2（永久單人模型、Gate A~F pass/fail criteria、合規核對） | 計畫治理或交付標準變更時 |
| `docs/templates/PLAN.md` | 開發者、代理 | 可直接複製之實作計畫模板（含 Code Matrix、UX Pack、Migration Runbook、AGENTS Gate） | 計畫模板欄位或強制章節變更時 |
| `docs/governance/ai_hallucination_rework_prevention_matrix.md` | rules／skills 維護者 | AI 幻覺導致重工之事件矩陣、低 token 預防流程、可貼入模板 | 發生重複修補、文件/契約來回修改、或要優化 agent 規則時 |
| `docs/decision-log.md` | 全員 | 已採納決策、範圍、風險、回溯方式 | 每次架構或契約層級決策定案時 |
| `AGENTS.md`（repo root） | 代理／貢獻者 | 網域優先序、統計契約、UI／報告邊界、驗證基線 | 治理規則或強制驗證流程變更時 |
| `docs/specs/spec_maintenance_and_alignment.md` | 規格維護者 | 跨文件對齊觸發條件、計畫檔生命週期 | 治理流程或「何時更新哪份 spec」規則變更時 |
| `docs/specs/final_audit_suite.md` | 關帳／稽核 | 最終稽核套件階段與產出 | 稽核閘門或工件路徑變更時 |
| `docs/specs/release_validation_coverage.md` | 關帳／品質 | Golden、`tests/release_validation`、發行檢查指令對照 | 新增 golden 情境、parity 測試或發行閘門變更時 |
| `docs/reports/document_sync_full_audit_2026-05-25.md` | 維護／代理 | 2026-05-25 全文件盤點、漂移修正與保留/排除判定 | 下次 full docs sync 或文件刪移判定變更時 |

**最終稽核執行（補充）**：`python scripts/run_final_audit_suite.py --repo-root . --profile full`；產出目錄：`Outputs/final_audit/<timestamp>/`。計劃說明：`docs/plans/final_audit_execution_plan.md`。

**發行驗證（補充）**：`python scripts/release_check.py`（可選 **`--with-release-ext`**）→ `Outputs/release/release_report.json`；測試與 golden 對照表見 `docs/specs/release_validation_coverage.md`；剩餘範圍與可選項收斂見 **`docs/open-questions.md` Watchlist #7**。

## 圖表與統計計算：相關檔案／文件總覽表

| 類別 | 路徑 | 角色 |
|------|------|------|
| 圖表契約／ID／payload 解析 | `app/analytics/chart_registry.py` | 單一來源：`CHART_CATALOG`、`resolve_chart_payload`、工程決策五分類（製程監控/製程能力/異常根源/變數關係/比較分析）、特徵數相容 |
| 分析 payload 組裝 | `app/viewmodels/chart_analysis_viewmodel.py` | `compute_analysis_payload`：呼叫各引擎並組出完整 `payload`；`ChartAnalysisViewModel.analyze` 委派至此 |
| 摘要／儀表板資料 | `app/analytics/summary_engine.py` | `compute_summary` → `payload["summary"]`（含 `dashboard_layers`；UI 為 `DiagnosticPage`） |
| 異常四卡計算 | `app/analytics/analysis_cards_engine.py` | OOC／Shift／Drift／Outlier 對應四圖表 ID |
| 常態檢定 | `app/analytics/normality_engine.py` | `normality` 圖表資料 |
| 多數圖表統計核心 | `app/analytics/*_engine.py` | 各管制圖、分佈、關聯、ANOVA、pattern 等（見架構 §6 示例） |
| 共用演算輔助 | `app/analytics/statistical_utils.py`、`ooc_utils.py` 等 | 多引擎共用；變更時檢查呼叫端 |
| 繪圖實作 | `app/charts/*_chart.py`、`app/charts/base_chart.py` | Matplotlib 繪製；輸入多為 payload 切片 |
| 圖表頁 UI 綁定 | `app/ui/pages/chart_analysis_page.py` | `chart_id` → 圖表類別與 payload 鍵對照 |
| 架構說明（圖表／管線） | `docs/specs/project_architecture.md` §5–§6 | 主流程圖表 ID、模組分工、與 registry 一致 |
| 資料／payload 契約 | `docs/specs/data_contract.md` | `resolve_chart_payload`、摘要與報告相關欄位 |
| 統計公式與門檻 | `docs/governance/SPC_RULES.md` | 統計權威；變更須規格先於程式 |
| 圖表契約稽核紀錄 | `docs/reports/chart_contract_audit.md` | 語意與實作落差、風險項與處置 |
| 規格對齊觸發 | `docs/specs/spec_maintenance_and_alignment.md` | 圖表／payload 變更時應同步更新之文件 |

## 文件分類

- `docs/governance/`：治理規範與統計規則（例如 `AGENTS.md`, `SPC_RULES.md`）
- `docs/specs/`：產品、資料、流程、UI 與契約規格
- `docs/plans/`：實作計畫與治理計畫
- `docs/reports/`：驗證、稽核、修復與對齊報告（多數為時間快照）
- `docs/reference/`：參考資料與主題型說明（如 UI design system）

最新收斂封板報告：
- `docs/reports/convergence_closeout_2026-04-02.md`

最新文件同步稽核：
- `docs/reports/document_sync_full_audit_2026-05-25.md`

## 簡報資產

- 輸出簡報：`presentations/SPI_SPC_Platform_Overview.pptx`
- 簡報工程：`presentations/smt-spi-platform-overview/`
  - 範例輸出：`presentations/smt-spi-platform-overview/SMT_SPI_SPC_平台簡介.pptx`
  - 重建（在 repo root 執行）：
    - `npm --prefix presentations/smt-spi-platform-overview run build:all`
    - 若需刷新 UI 截圖：`npm --prefix presentations/smt-spi-platform-overview run build:full`

## 歷史文件

- `archive/unused/`：目前未引用但保留可回復的歷史文件
- `archive/outputs/final_audit_index.md`：`Outputs/final_audit/*/report.md` 封存索引（原路徑已清空）
- `docs/reports/` 歷史快照說明：`docs/reports/README.md`
- 搬移紀錄：`docs/reports/document_relocation_log.csv`
- 搬移摘要：`docs/reports/document_relocation_summary.md`

## 維護建議

1. 治理規則更新優先落在 `docs/governance/`。
2. 架構、資料契約、UI 契約變更同步更新 `docs/specs/`。
3. 驗證結果與稽核證據落在 `docs/reports/`。
4. 文件若失效但需保留，移至 `archive/unused/` 並補註原因。
