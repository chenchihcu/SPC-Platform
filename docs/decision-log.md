# Decision Log

## 2026-06-30 規格管理新增手動新增產品規格

- Decision: 在資料庫的「規格管理」合併表新增「新增規格」入口，讓使用者可直接建立既有或全新產品的錫膏印刷規格與鋼板厚度規格，新增表單一律從系統預設值開始。
- Scope: `MeasurementLibraryPage` 規格管理 action row/dialog/refresh logic、錫膏與鋼板 registry 的 `product_part_no` 保留、focused UI/SQLite tests、README 與架構規格。
- Reason: 每個產品可能對應不同鋼板、Height 基準與 Volume/Area/Height 管制上下限；只允許編輯既有列會阻塞 X3000=A、VS80=B 這種大量產品規格建檔流程。
- Impact: 新產品可由規格管理頁直接建立 active 規格版本，spec-only 產品也會出現在規格頁產品篩選；新增後不自動切換目前分析，仍需使用者明確選用規格。SPC 公式、規格解析契約與資料庫 schema 不變。
- Risk: 本次仍是產品層 active 規格；若未來需同產品依鋼板序號或供應商鋼板批次覆蓋規格，應新增覆蓋層，不回寫本次產品層契約。
- Rollback: 回退 UI/registry/tests/docs 變更即可移除新增入口；已新增的 SQLite 產品與規格版本可用 UI 刪除或由資料庫備份還原。

## 2026-06-30 振順豐 TOP.csv supplier-specific import profile

- Decision: 新增 `振順豐` 供應商限定量測匯入 profile，將 TOP 寬表 `Component ID/PAD ID/Volume(mm)<n>/Height(mm)<n>/Area(mm)<n>` 轉為標準 `RefDes/Pad/Volume/Height/Area/BoardNo` 長表；供應商匹配優先，未選供應商時僅允許路徑含 `振順豐` 且欄位簽名完整時自動啟用。
- Scope: `MeasurementLoader`、`DataLoaderWorker` 供應商上下文傳遞、Data Setup 自動儲存供應商同步、`measurement_sessions.supplier` 可重入 migration、量測庫保存/回載 supplier、focused loader/library tests、README 與資料/架構契約。
- Reason: 振順豐 TOP.csv 的量測欄位是 `(mm)` 寬表，現有全域別名只支援一般/百分比格式，導致寬表轉長後仍缺 `Volume/Area/Height` 標準欄位；此格式只適用振順豐，不應放大全域映射。
- Impact: 振順豐 TOP.csv 可匯入為 valid，保留 `raw_rows/raw_columns/board_count/measurement_units/vendor_profile` metadata；其他供應商不會因 `(mm)` 欄位自動匹配。量測庫會保存 supplier 並於回載時寫回 `SessionStore`，避免路徑更名後失去供應商 profile。SPC 公式與規格比對語意不變，絕對量測值不隱性轉百分比。
- Risk: 若振順豐未來改欄位命名或少輸出某個量測族，profile 會回報 signature error；需依新樣本更新 profile 與測試，不應放寬為全域 alias。
- Rollback: 回退 loader/profile、供應商上下文傳遞、量測庫 supplier 欄位讀寫、tests/docs 即可恢復舊匯入行為；既有 SQLite 若已新增 `measurement_sessions.supplier` 可保留空值相容，必要時以備份還原資料庫。

## 2026-05-26 Qt desktop layout and theme remediation

- Decision: 將主視窗與代表性對話框收斂到 `availableGeometry()` fitting policy，並將 Data Setup 從垂直堆疊/整頁 scroll 假設改為一頁式量化表格布局。
- Scope: `app/bootstrap/app_config.py`, `app/ui/theme/layout_policy.py`, `app/ui/main_window.py`, Data Setup page/theme/diagnostics, sidebar density behavior, interpretation/export/library edit dialogs, focused UI tests, README and active UI/architecture specs.
- Reason: 主要 workflow shell 與資料設定入口需先滿足目前 `1280x752` 可用區，並在 `1200x700`, `1366x768`, `1920x1080` 仍保持核心行動可見；舊 Data Setup 文件與測試仍假設垂直堆疊與整頁 scroll，已不符合表格化布局目標。
- Impact: 初次開啟主視窗使用 `0.93` 可用區比例；`fit_top_level_to_available(...)` 套用於主視窗、解讀、PPTX 匯出確認與資料庫編輯對話框；Data Setup 主區固定為工單列跨欄、座標左欄跨兩列、規格/量測右欄上下排列，並透過 `DataSetupLayoutBudget` 輸出診斷。側欄高度不足時收合分析條件但顯示已收合提示並保留目前篩選值。SPC 公式、chart registry、payload shape、report contract 與資料庫 schema 不變。
- Risk: 本次自動化涵蓋 offscreen 幾何與 launch；多螢幕或 125%/150% 真機 CJK 字型邊界仍需依現場設備抽查，結果應更新到 active risk ledger 而非改統計或資料契約。
- Rollback: 回退上述 UI/theme/dialog/tests/docs 檔案即可恢復舊 sizing 與 Data Setup layout；不需要 migration、資料回填或 payload consumer rollback。

## 2026-05-24 Process statistics report-style diagnostic output

- Decision: 將 `DiagnosticPage` 可見輸出從多卡片「製程診斷」重整為少容器「製程統計分析」報告版，並以 `dashboard_layers_display.build_process_stat_report_sections` 作為 UI、Excel、PPTX 的欄位順序與嚴重性單一來源。
- Scope: `app/analytics/dashboard_layers_display.py`, `app/ui/pages/diagnostic_page.py`, `app/ui/widgets/process_dashboard_cards.py`, `app/ui/theme/tokens.py`, `app/ui/theme/dark_stylesheet.py`, `app/services/diagnostic_excel_exporter.py`, `app/services/pptx_report_builder.py`, focused tests and active UI/docs specs.
- Reason: 原本 1-7 區塊卡片感過重、KPI 字級偏大，且 UI/Excel/PPTX 欄位與顏色判讀分散，容易讓正式報告與畫面不同步。
- Impact: 閱讀順序固定為狀態、規格/能力、穩定性/資料範圍、診斷與對策、背景；每個欄位標示來源 layer；報告面板欄位字級一致，不以大/小字做層級；`good/warning/bad/neutral` 嚴重性共用，紅色限用於超規、Cpk 不足、OOC/OOS 嚴重與需處置項。`dashboard_layers` payload、`diagnostic_evidence_matrix` schema、chart ID 與統計公式不變。
- Risk: 本次是 presentation/report-output 變更；若現場仍覺得欄位過密，後續應先調整 token 與分組密度，不應改動統計 payload 或診斷 schema。
- Rollback: 回退上述 UI/theme/export/report/tests/docs 檔案即可恢復原多卡片診斷輸出；不需要資料庫、schema 或 payload consumer migration。

## 2026-05-24 Analysis and PPTX export performance optimization

- Decision: 將 100k 分析與 PPTX 匯出瓶頸收斂到向量化計算、payload reuse、report cache reuse、chart render cache 與背景匯出 worker；既有 SPC 公式、chart ID、payload top-level shape 與 PPTX 內容契約不變。
- Scope: `app/analytics/pattern_recognition_engine.py`, `app/analytics/summary_engine.py`, `app/viewmodels/chart_analysis_viewmodel.py`, `app/data/session_store.py`, `app/services/report_service.py`, `app/services/report_diagnostics.py`, `app/services/pptx_report_builder.py`, `app/ui/pages/report_export_page.py`, `app/ui/pages/chart_analysis_page.py`, performance harness and focused regression tests.
- Reason: synthetic_large_100k 顯示 `chart_payload_sec=9.9138`、`report_export_sec=12.3223`，且匯出在 UI thread 重算/渲染會造成互動卡頓；主要成本來自 Nelson window loop、summary row loop、重複 feature payload 組裝、report 匯出前整包重算與同圖重複 render。
- Impact: Nelson rule 3/4 與 summary defect count 改為 pandas/numpy 聚合；單特徵 selected-feature 結果在 `parameters` 內重用；`ReportService` 優先採用符合 filters/spec/selected_features 的 `last_analysis_payload` 或 `_analysis_cache`；PPTX diagnostic/gallery 共用單次匯出 chart image cache；`ReportExportPage` 使用背景 worker 並移除 export path 的 `QApplication.processEvents()` reentry；圖表頁保留 checkbox/selection UX 但 first-use lazy-create chart cards。
- Risk: 自動化已覆蓋 payload parity、worker 行為、cache reuse 與 launch，但大型真實客戶資料的 UI 體感仍需實機抽查；performance gate 仍以 synthetic_large_100k 作為第一層可重現基準。
- Rollback: 回退上述 production/test/doc 檔案即可恢復舊同步匯出與 eager chart/card 建立；不需要資料庫 migration、payload consumer migration 或金標資料格式回滾。

## 2026-05-23 Left sidebar workflow navigation and button findability

- Decision: 將可見 workflow 切換移回左側 `NavigationPanel`，右側 `QTabWidget#workflowTabs` 保留為內部頁面容器並隱藏 tab bar；左側欄固定分為流程、分析條件、特徵、動作四區。
- Scope: `app/ui/main_window.py`, `app/ui/widgets/collapsible_sidebar.py`, `app/ui/widgets/navigation_panel.py`, `app/ui/widgets/control_panel.py`, focused navigation tests, README and UI/architecture specs.
- Reason: workflow tabs 在頂部、全域動作在左下、頁面動作分散於內容區時，使用者需要在多個方向找按鈕；左側導覽讓流程切換與全域分析控制回到同一掃描線，但避免把表單/資料表列操作也塞進側欄。
- Impact: `NAV_TO_STACK` 與 `TAB_TO_STACK` 映射維持 `[0, 6, 2, 5, 3, 4]`；`Ctrl+1..6`、下一步、診斷跳圖表、資料設定跳資料庫仍走既有切頁路徑。側欄在高度不足時優先收合分析條件，保留流程導覽與底部動作。SPC 公式、payload shape、資料庫 schema、report contract 均不變。
- Risk: 側欄同時承載流程與篩選後，低高度視窗可能較擁擠；本次以分區標題、固定底部動作、側欄密度 token 與測試檢查限制按鈕數量，後續若實機顯示不足，優先調整側欄密度或收合分析條件，而非新增側欄操作。
- Rollback: 回退上述 UI/docs/tests 檔案即可恢復 2026-05-05 的頂部 workflow tabs；不需要資料或 schema rollback。

## 2026-05-23 Qt window-fit and QSS compatibility hardening

- Decision: 將主視窗幾何還原改為 screen-aware：已儲存幾何必須仍位於目前螢幕可用工作區且尺寸可容納，否則回到安全置中尺寸；同時把 Qt QSS 不支援的 CSS 屬性從全域 stylesheet 移除並納入 `qt_audit` gate。
- Scope: `app/ui/main_window.py`, `app/ui/theme/layout_policy.py`, `app/ui/theme/dark_stylesheet.py`, compact sidebar theme tokens/widgets, `scripts/qt_audit.py`, focused audit test, README and UI/architecture specs.
- Reason: 測試 gate 先前可通過，但仍允許 stale/off-screen window geometry 與 `outline` / `text-transform` / `opacity` 等 Qt QSS 會忽略的樣式存在，造成實機視窗可見性與主題一致性風險。
- Impact: 主視窗在多螢幕/解析度變更後更可恢復；QSS 規則與 `AI_RULES.md` 的相容性清單一致。SPC 公式、payload shape、資料庫 schema、workflow tab order、report contract 均不變。
- Risk: 既有使用者若保存了超出目前螢幕的舊視窗大小，下一次啟動會被重設；這是有意的可見性修正。
- Rollback: 回退上述 UI/theme/audit/docs/test 檔案即可恢復舊幾何還原與 stylesheet audit 行為；不需要資料或 schema rollback。

## 2026-05-05 Slate/Electric Blue mixed navigation UI redesign

- Decision: 將桌面 UI 從舊 dark/left-nav presentation 收斂為淺色 Slate + Electric Blue；右側 workspace 改為 6 個頂部 workflow tabs，左側僅保留全域篩選、資料狀態、下一步與重新分析。
- Scope: `app/ui/theme/*`, `app/ui/main_window.py`, shared page templates, selected inline-style cleanup, `app/charts/base_chart.py`, `app/services/pptx_report_builder.py`, navigation/theme tests, README and UI/architecture specs.
- Reason: reference UI 風格要求更接近密集製造桌面工具：淺色背景、清楚表格/表單層級、語意化按鈕，以及避免左側 workflow nav 與全域篩選在同一欄競爭注意力。
- Impact: `apply_app_theme()` / `get_app_stylesheet()` 成為新公開名稱，`apply_dark_theme()` / `get_dark_stylesheet()` 保留相容；`VISIBLE_WORKFLOW_TABS` / `TAB_TO_STACK` 是可見流程映射。Matplotlib chart 與 PPTX 報告色彩改為 token-derived，統計公式、chart IDs、payload shape、report chapter order、診斷資料來源與資料 schema 均不變。
- Risk: 本次是大範圍 presentation 變更；驗證以 ruff/mypy/pytest/qt_audit/check_launch 與 focused navigation/theme/report tests 控制回歸，仍建議在實機 DPI 100%/125%/150% 做人工視覺掃描。
- Rollback: 回退上述 UI/theme/chart/report/docs/tests 檔案即可恢復舊 presentation；不需資料庫 migration 或 payload rollback。

## 2026-05-02 Diagnostic readable tabs and export parity

- Decision: keep `diagnostic_evidence_matrix` as the statistical/data contract, and add `build_readable_diagnostic_tabs(matrix)` as the shared presenter for DiagnosticPage, diagnostic Excel, and PPTX process diagnosis text.
- Scope: `app/services/diagnostic_evidence_matrix.py`, `app/ui/pages/diagnostic_page.py`, `app/services/diagnostic_excel_exporter.py`, `app/services/report_process_narrative.py`, `app/services/pptx_report_builder.py`, focused tests, README, architecture/UI/data-contract docs, this entry.
- Reason: the seven diagnosis sub-tabs were technically populated but too abstract for engineering use; labels such as isolated `refute`/`反證` and badge-only next-chart names did not explain the judgment, evidence source, or next action.
- Impact: UI, Excel, and PPTX now use the same readable rows (`title`, `result_zh`, `reason_zh`, `evidence_zh`, `next_action_zh`, `source_zh`). The `support/refute/neutral/unavailable` internal states, SPC formulas, chart IDs, thresholds, and existing matrix payload shape remain unchanged.
- Risk: readable wording is a presentation layer over existing payload evidence; if a chart payload is absent, the presenter exposes data insufficiency instead of inferring a statistical result.
- Rollback: revert the presenter wiring in the listed UI/export/report modules and tests to return to raw matrix/tab rendering while leaving the original `diagnostic_evidence_matrix` payload generation intact.

## 2026-04-30 Process diagnosis combination evidence matrix

- Decision: 將製程診斷從單一卡片/KPI 判讀擴充為 `diagnostic_evidence_matrix`：先最大化展開 `特徵 × 圖表 × 篩選 × 顯示` 候選組合，再依可用性、證據維度與多圖表關聯收斂診斷結論。
- Scope: `app/services/diagnostic_evidence_matrix.py`, `analysis_payload_finalize`, `DiagnosticPage`, diagnostic Excel exporter, PPTX report context/builder, tests, README, architecture/UI/data-contract docs, this entry.
- Reason: SMT SPI 製程異常證據不應由單一 KPI 或單一圖表決定；三特徵情境需保留「1F charts × features + 2F charts × feature pairs + 3F charts × triple set」的組合思維，並明確區分已分析、未選、缺資料、不適用與不可用。
- Impact: 診斷頁新增組合/證據/關聯分頁；Excel 匯出新增 `組合矩陣` 與 `證據矩陣` sheet；PPTX 製程診斷與多訊號頁同步顯示矩陣覆蓋與證據鏈。統計公式、圖表計算 payload 與 SPC 門檻不變。
- Risk: 矩陣依既有 payload 判讀，不強制補算所有缺失圖表；缺資料或不適用會明確標示，後續若要提高覆蓋率應新增對應圖表 payload，而非在診斷層推估。
- Rollback: 移除 `diagnostic_evidence_matrix` finalize 注入與 UI/Excel/PPTX 讀取邏輯，回復 DiagnosticPage 僅呈現 `dashboard_layers` Layer 1-8。

## 2026-04-24 Chart analysis page selection-friction remediation

- Decision: 將 `ChartAnalysisPage` 的圖表選擇流程收斂為明確的兩步驟工具列：`步驟 1 特徵`、`步驟 2 顯示模式`；保留單列 toolbar 與 persistent hint，但把 live selection 狀態集中到全域脈絡列，並將 autoswitch 提示改為更直白的 `原圖 -> 新圖` 說明。
- Scope: `app/ui/pages/chart_analysis_page.py`, `tests/test_chart_analysis_header_layout.py`, `tests/test_feature_interaction_logic.py`, `docs/specs/ui_design_spec.md`, this entry.
- Reason: 既有圖表頁雖已具備 `單特徵/雙特徵/三特徵`、autoswitch 與 context strip，但 toolbar 內缺少明確步驟語意，`標準化顯示` 也容易被看成獨立動作；同時 selection 相關事件流分散在 feature shortcut、tab 切換、selector rebuild、checkbox toggle，增加維護與回歸風險。
- Impact: toolbar 仍保持單列，但使用者能直接理解「先選特徵、再選顯示模式、最後勾圖表分類」；context strip 會即時顯示 active features、顯示模式、已選圖表數、多特徵標準化狀態與 active filters；manual chart selection 會清掉過期 autoswitch hint，避免殘留錯誤引導。
- Risk: 本次不改 `chart_registry` 或圖表計算契約，因此改善集中在文案與互動語意；若後續仍有理解落差，下一步應以 screenshot/runtime review 驗證真實掃讀順序，而不是再堆更多提示文字。
- Rollback: 回退上述檔案至本次變更前版本，恢復原 toolbar 文案、原 context strip copy 與原 selection event flow。

## 2026-04-23 Gate A~F release-gated governance alignment

- Decision: 將 Gate A~F 從可填寫的計畫輸出升級為 release-gated governance contract；現行入口統一指向 `docs/governance/GLOBAL_PLAN_FRAMEWORK_V2_2.md`，並以自動檢查阻擋缺少 pass/fail criteria、evidence 欄位或 fail action 的回歸。
- Scope: `README.md`, `docs/README.md`, `.cursor/plans/README.md`, `docs/specs/issue_resolution_workflow.md`, `docs/specs/project_architecture.md`, `docs/governance/GLOBAL_AGENTS_8CLASS_TEMPLATE.md`, `docs/governance/AGENTS.md`, historical superseded notice in `docs/governance/GLOBAL_PLAN_FRAMEWORK_V2_1.md`, `docs/templates/PLAN.md`, `scripts/check_governance_alignment.py`, `tests/release_validation/test_governance_alignment.py`, this entry.
- Reason: V2_2 已補 Gate A~F pass/fail criteria，但多個入口仍指向 V2_1，且 `PLAN.md` 的 Delivery Output 只要求填 `Pass/Fail`，無法防止 AI 看似照計畫輸出但未用證據閉環。
- Impact: `tests/release_validation` 會涵蓋 governance alignment；`scripts/run_release_gate.py` 與 `scripts/release_check.py` 的預設 release validation pack 會在治理入口或 Gate 判準退化時失敗。
- Risk: 文字檢查只覆蓋 canonical entrypoints 與模板欄位，不能驗證每一次人工/AI 回覆內容的語意品質；仍需由任務執行者提供實際證據。
- Rollback: 移除 `scripts/check_governance_alignment.py` 與對應 release-validation test，還原上述文件入口至 V2_1、移除 V2_1 superseded notice，並恢復 `docs/templates/PLAN.md` 原 Delivery Output 區塊。

## 2026-04-23 All-chart SPC visual semantics convergence

- Decision: Add a shared `BaseChart` presentation layer for chart visual semantics and wire chart dashboard state styling/context disclosure into the UI without changing analytics formulas or payload schemas.
- Scope: `app/charts/base_chart.py`, selected monitoring/capability chart renderers, `app/ui/pages/chart_analysis_page.py`, `app/ui/theme/dark_stylesheet.py`, chart readability tests, README/spec docs.
- Reason: Chart calculations and payload routing were already centralized, but line semantics, sample disclosure, latest-point labeling, and card status styling were spread across individual chart classes; this made UI and PPTX evidence harder to verify consistently.
- Impact: Report and screen renders now share legend/sample-disclosure finishing through `BaseChart`; control limits and spec limits have distinct helper semantics; chart cards expose active feature/mode/filter context and visible `Ready/Incompatible/NoData/Error` state styles.
- Risk: Very dense charts may need follow-up visual tuning after manual DPI review, but the patch keeps existing data/sample visibility and does not introduce hidden truncation.
- Rollback: Revert the modified chart/UI/QSS files and docs to restore per-chart styling behavior while leaving analytics engines unchanged.

## 2026-04-22 Risk ledger convergence (active-only, #7 noise-first diagnosis)

- Decision: 將 `docs/open-questions.md` 收斂為 active-only 風險帳本，統一欄位為 `Scope/Risk/Guardrail/Next action/Revalidation gate/Rollback/Status`，並採三狀態 `stabilizing/fixing/monitoring`；同時新增 blocker 升級準則（僅直接影響交付 gate 才升級 blocker）。
- Scope: `docs/open-questions.md`, this entry.
- Reason: 先前 active 風險項目過多且粒度不一，容易造成追蹤成本高、重複項與歷史殘留混在同一層。
- Impact: active 項目由 7 項收斂為 5 項；`Watchlist #7` 以「先降噪再判因」執行後，依 5-run 證據判定偏向 true regression（非純主機噪音），狀態改為 `fixing`；#11/#12 轉入 dormant（不佔 active 配額，保留再激活條件）。
- Risk: active 項目縮減後，若再激活條件定義不清，可能延後問題浮現時點。
- Rollback: 回退 `docs/open-questions.md` 至收斂前版本，恢復原 active 列表與條目格式。

## 2026-04-22 Performance gate hard-signal set: exclude `spc_sec` from release blocking

- Decision: 調整 performance regression gate 的 hard-signal 指標集合：`spc_sec` 為毫秒級 micro-segment，對主機抖動高度敏感（即使重複平均仍可能造成假陽性），因此保留量測與紀錄但不再作為 release gate 阻擋指標；hard gate 僅保留 `analysis_total_sec`、`chart_payload_sec`、`report_export_sec`。
- Scope: `tests/release_validation/helpers/performance_gate.py`, this entry.
- Reason: `spc_sec` 的時間尺度太小，易受背景排程、CPU power state、熱節流影響，導致 gate 以低信號指標阻擋 release，與「防止真回歸」的目標不成比例。
- Impact: `tests/release_validation/test_performance_regression.py::test_performance_regression_synthetic_large_100k` 仍產出 `spc_sec` 觀測值，但 gate PASS/FAIL 不再受其影響；全庫 `pytest -q` 恢復通過。
- Risk: 若未來 `spc_sec` 出現長期飆升，仍需以端到端指標（或獨立 microbenchmark gate）捕捉真回歸。
- Rollback: 將 `spc_sec` 加回 gating 集合並重新評估其穩定化策略（例如更大 repeats 或獨立基準測試）。

## 2026-04-22 AI triage fail-safe policy adoption for planning depth (L1 vs Full)

- Decision: 在全域計畫框架導入 AI 初判分流政策，固定演算法為「先判斷硬觸發，再判斷信心」：任一硬觸發為 true 或 `confidence < 0.85` 一律走 `Full`；僅在無硬觸發且信心足夠時可走 `L1`。同時採單向覆寫規則：僅允許 `L1 -> Full`，禁止 `Full -> L1`。
- Scope: `docs/governance/GLOBAL_PLAN_FRAMEWORK_V2_1.md`, `docs/templates/PLAN.md`, `docs/specs/issue_resolution_workflow.md`, `.cursor/plans/README.md`, this entry.
- Reason: 單靠人工判斷 L1/L2 容易在 UI/資料/契約變更或低信心情境下誤走輕流程，增加漏測與回歸風險。
- Impact: 每份計畫在 Metadata 必填 `triage_route`、`triage_confidence`、`triage_triggers`、`triage_evidence`、`triage_decision_note`；分流結果成為章節深度的唯一依據，`triage_evidence` 缺失視同無效並需 `blocked`。
- Risk: 初期文件填寫成本上升；若硬觸發識別描述不夠具體，仍可能出現分流爭議。
- Rollback: 回退上述檔案至本次變更前版本，恢復純人工 L1/L2 判斷與舊模板欄位。

## 2026-04-22 Global planning framework v2.1 adoption (permanent self-only model)

- Decision: 新增跨專案可複用的計畫治理框架 **`docs/governance/GLOBAL_PLAN_FRAMEWORK_V2_1.md`** 與可直接複製模板 **`docs/templates/PLAN.md`**；流程固定為永久單人模型（`executor=self`），並將 `Code Change Matrix`、`UX Acceptance Pack`、`Data Migration Runbook`、`AGENTS Compliance Gate` 列為強制章節。
- Scope: `docs/governance/GLOBAL_PLAN_FRAMEWORK_V2_1.md`, `docs/templates/PLAN.md`, `.cursor/plans/README.md`, `docs/specs/issue_resolution_workflow.md`, `docs/specs/project_architecture.md`, `docs/README.md`, `README.md`, this entry.
- Reason: 既有計畫習慣偏向敘事型，對「檔案/類別/函數簽章級別精準度」與「AGENTS 條款級合規證據」要求不一致，且缺乏跨專案統一模板。
- Impact: 任務計畫改為可執行格式並可跨專案重用；UI 任務需提供 Premium Design 驗收與視覺證據；資料或契約任務需提供完整 SQL 鏈與回滾步驟；A~F 任一 Gate 失敗時任務必須標記 `blocked`。
- Risk: 模板初期會提高計畫撰寫成本；若未維護 Rule ID 映射，`AGENTS Compliance Gate` 可能變成形式化勾選。
- Rollback: 回退上述檔案至本次變更前版本，恢復舊計畫章節建議與既有文件入口。

## 2026-04-22 SPC spec split: paste-printing spec vs stencil-thickness spec (product-level dual library)

- Decision: 將混合式 `spec_versions` 拆分為兩個產品層版本庫：`paste_printing_spec_versions`（Volume/Area + Height LSL/USL）與 `stencil_thickness_versions`（stencil type/thickness + `unit_mode` + `height_denominator_mm`），並由 `spec_resolver` 在執行期組裝結果；`Height target` 一律由鋼板基準（100% 邏輯）推導，`Height LSL/USL` 維持由錫膏庫提供固定百分比規格。
- Scope: `app/data/master_data_db.py`, `app/data/paste_printing_spec_registry.py`, `app/data/stencil_thickness_registry.py`, `app/data/paste_printing_spec_library.py`, `app/data/stencil_thickness_library.py`, `app/data/product_spec_registry.py`, `app/data/product_spec_library.py`, `app/services/spec_resolver.py`, `app/ui/pages/measurement_library_page.py`, `tests/test_spec_split_migration_master_db_e2e.py`, `tests/test_spec_resolver_unit_mode_absolute.py`, `tests/test_measurement_library_spec_tabs.py`, `tests/release_validation/test_spec_stencil_stepped_resolver.py`, `tests/test_product_spec_library_master_db_e2e.py`, `README.md`, `docs/specs/project_architecture.md`, `docs/open-questions.md`, this entry.
- Reason: 產品規格需要同時滿足兩種管理節奏：錫膏印刷規格跟產品設計走（以百分比管制），鋼板厚度規格需保留供應商差異與單位彈性（percent/absolute），單表混存會讓契約與未來擴充（例如鋼板序號覆蓋）耦合過高。
- Impact: 規格管理 UI 改為兩個獨立主分頁（錫膏/鋼板）各自查詢、編輯、設為現用與刪除；分析前 gate 變更為「任一產品層 active 規格缺失即阻擋」並給出明確原因；啟動 migration 會將舊 `spec_versions` 自動拆遷到新雙表，舊表保留唯讀作回滾保險。
- Risk: 目前 `unit_mode` 與 `height_denominator_mm` 為產品層單值；若同產品需依鋼板序號差異換算，需新增覆蓋層（converter/擴充表）而非回寫本次契約。
- Rollback: 回退上述檔案並停用 `spec_versions_split_v1` migration 路徑，恢復舊 `spec_versions` 單表讀寫流程與單一規格管理分頁。

## 2026-04-22 Supplier code auto-generation + read-only contract (with one-time legacy renumber)

- Decision: 將供應商管理改為「系統自動維護 `supplier_code`」：新增時依 `SUP-0001` 流水規則自動給號（同名供應商沿用同一編號），編輯時 `supplier_code` 唯讀且不可更新；同時加入一次性 legacy 重編 migration（寫入 `schema_meta` 標記），若偵測到「同名映射後同編號 + 同鋼板編號」衝突則中止並提示。
- Scope: `app/data/supplier_library.py`, `app/ui/pages/measurement_library_page.py`, `tests/test_supplier_library_master_db_e2e.py`, `README.md`, `docs/specs/project_architecture.md`, this entry.
- Reason: 現行流程允許人工輸入/修改供應商編號，容易造成編號規則不一致與維護成本；需收斂為系統生成且不可手改的單一契約。
- Impact: 供應商新增/編輯 UI 不再提交 `supplier_code`；資料層改由名稱映射與流水規則統一生成；既有資料首次使用供應商管理時會執行一次性重編，衝突時保留原資料並回報錯誤，不做部分落地。
- Risk: 若歷史資料存在同名同鋼板重複紀錄，migration 會被阻擋直到資料清理完成；衝突摘要最多顯示前 5 筆。
- Rollback: 回退上述檔案，恢復 `supplier_code` 手動輸入/更新契約，並移除 auto-renumber migration 路徑。

## 2026-04-22 Performance gate near-boundary retry median stabilization

- Decision: 在不調整 `time_factor=1.2`／`mem_factor=1.3` 前提下，為 release validation **P gate** 新增「首次失敗才補跑」策略：若首次失敗僅屬 time metrics 且 ratio 落在 `(1.2, 1.3]`，補跑 2 次並以 3 次中位數作最終判定；`ratio > 1.3`、`memory_peak_bytes` 失敗、`scenario_id` 不符皆維持直接 fail。
- Scope: `tests/release_validation/helpers/performance_gate.py`, `tests/release_validation/test_performance_regression.py`, `tests/release_validation/test_performance_retry_policy.py`, `README.md`, `docs/specs/release_validation_coverage.md`, `docs/specs/project_architecture.md`, `docs/open-questions.md`, this entry.
- Reason: 在高負載 host 下，P gate 單次量測可能接近 1.2 邊界造成偶發誤判；需降低抖動敏感度，同時保持對明顯回歸（`ratio > 1.3`）的即時阻擋。
- Impact: `performance_gate_result.json` 新增 `attempt_count`、`retry_applied`、`retry_policy`、`attempts`、`final_current_source` 等追溯欄位；release pipeline 既有 `performance_status` 消費路徑不變。
- Rollback: 回退上述檔案至本次變更前版本，恢復單次量測判定與舊版 performance artifact 欄位集合。

## 2026-04-21 Remaining risks convergence (logger side-effect + performance baseline median sampling)

- Decision: 以最小補丁收斂兩項殘餘風險：  
  1) 移除 `app/utils/logger.py::get_logger()` 內 `logging.basicConfig(level=logging.INFO)`，避免 library import 改寫 root logger；  
  2) `scripts/record_performance_baseline.py` 新增 `--samples`（預設 3）且每個 sample 以獨立子行程量測，再以中位數寫入 `golden_dataset/performance_baselines.json`；並將 `tests/release_validation/helpers/performance_gate.py` 的 `spc_sec` 改為 5 次平均，降低短時段計時抖動造成的 P gate 偽回歸。
- Scope: `app/utils/logger.py`, `tests/test_logger_import_side_effects.py`, `scripts/record_performance_baseline.py`, `tests/release_validation/helpers/performance_gate.py`, `golden_dataset/performance_baselines.json`, `docs/open-questions.md`, this entry.
- Reason: `ui_runtime_diagnostics` import chain 會經由 logger helper 將 root logger 拉到 INFO；且效能回歸測試對單次機器負載波動敏感，存在偶發 fail。
- Impact: 匯入診斷模組不再隱式改寫 root logger；performance baseline 改為 3-run median（子行程採樣）且 `spc_sec` 以重複平均計時後，P gate 判定更可重複且維持既有門檻係數（time=1.2、memory=1.3）。
- Rollback: 回退上述檔案至本次變更前版本，恢復 helper 內 `basicConfig` 與單次量測 baseline 產生方式。

## 2026-04-21 Cross-chart CJK tofu remediation (bundled font + glyph-safe labels)

- Decision: 將圖表字型供應改為 repo 內建（`app/assets/fonts/NotoSansTC-VF.ttf` + `OFL-1.1`），新增共用註冊模組 `app/bootstrap/font_runtime.py`，並重構 `setup_mpl_cjk_font()` 使 CJK 字型優先於 `DejaVu Sans`；同時將高風險缺字文案改為等價穩定字元（`μ₀ -> mu0`、`MR̄ -> MR平均`、`平均値 -> 平均值`、`✓/✗ -> (OK)/(NG)`）。
- Scope: `app/assets/fonts/*`, `app/bootstrap/font_runtime.py`, `app/charts/mpl_font_config.py`, `app/ui/main_window.py`, `app/charts/cusum_chart.py`, `app/charts/cusum_3f_chart.py`, `app/charts/control_chart.py`, `app/charts/subgroup_chart.py`, `app/ui/tabs/normality_tab.py`, `.gitattributes`, `tests/test_mpl_font_config.py`, `tests/test_chart_glyph_rendering.py`, `tests/test_chart_label_glyph_safety.py`, `README.md`, `docs/specs/project_architecture.md`, `docs/specs/spec_maintenance_and_alignment.md`, `docs/open-questions.md`, this entry.
- Reason: 既有 `mpl_font_config` 將 CJK 字型 append 於 `font.sans-serif` 尾端，導致 Matplotlib 實際優先選用 `DejaVu Sans`，造成跨圖表中文/符號方塊字（tofu）。
- Impact: 所有走 Matplotlib 共用路徑的圖表改為 bundled CJK 優先渲染；新增三個回歸測試防止字型優先序或高風險 glyph token 回流。
- Rollback: 回退上述檔案，恢復系統字型 fallback-only 與既有圖表文案。

## 2026-04-21 Chart + Diagnostic interpretation entrypoint convergence (hidden-by-default dialog)

- Decision: 在不改統計契約與計算引擎的前提下，新增共用 `InterpretationDialog`，將圖表頁每張圖卡與診斷頁頁首都接入「預設隱藏、按鈕開啟」的完整解讀視窗；圖表解讀內容由 `chart_registry` 單一來源組裝，診斷解讀內容由 `diagnostic_interpretation_registry` 單一來源維護。
- Scope: `app/ui/dialogs/interpretation_dialog.py`, `app/analytics/chart_registry.py`, `app/analytics/diagnostic_interpretation_registry.py`, `app/ui/pages/chart_analysis_page.py`, `app/ui/pages/diagnostic_page.py`, `tests/test_chart_registry_acceptance.py`, `tests/test_diagnostic_interpretation_registry.py`, `tests/test_interpretation_dialog_entrypoints.py`, `docs/specs/ui_design_spec.md`, this entry.
- Reason: 完整說明雖已存在於 tooltip/參考頁，但主判讀流程缺少可見且可主動呼叫的解讀入口，導致使用期間不易理解圖表用途與解讀方式。
- Impact: 使用者可在圖表卡片與診斷頁一鍵開啟完整解讀，內容固定覆蓋用途、公式/函數、資料來源與工程判讀，且無資料時仍顯示 NoData 判讀框架。
- Rollback: 回退上述檔案到本次變更前版本，恢復 tooltip/參考頁為主要說明入口的既有行為。

## 2026-04-20 Remaining risks convergence (`_overlapped` / parity path / backfill)

- Decision: 以最小補丁收斂三項殘餘風險：  
  1) 新增 runtime environment guard（`HOME/USERPROFILE`）並將 pytest 預設停用 `_pytest.debugging`；  
  2) legacy `coordinate_registry.json` 新增與 DB active path 對齊的最新 `x3000` entry，parity mismatch 清零；  
  3) 以固定輸入路徑 `Outputs/master_data/workorder_backfill_real.csv` 完成 non-dry-run backfill，`measurement_sessions.id=3` 雙工單欄位與 `work_order_no` 對齊 `301-000100124`。
- Scope: `app/bootstrap/runtime_env.py`, `main.py`, `scripts/check_launch.py`, `app/charts/base_chart.py`, `tests/conftest.py`, `tests/release_validation/helpers/performance_gate.py`, `pyproject.toml`, `data/coordinate_registry.json`, `docs/reference/windows_runtime_recovery.md`, `docs/open-questions.md`, this entry.
- Reason: shell 缺 `HOME/USERPROFILE` 與 Windows provider 異常會造成非業務邏輯的啟動/測試失敗；同時 parity 與 backfill 需要落地為可驗證、可追蹤狀態。
- Impact: `check_launch` 可在未手動設定 `HOME/USERPROFILE` 下通過；`parity_report.json` 由 1 筆路徑差異降至 0；backfill non-dry-run 工件顯示 `updated_rows=1`、`missing_target_rows=0`，DB 實際欄位已更新。
- Risk: 直接 `import _overlapped` 仍為 `WinError 10106`（host 層待修復）；雖然全庫 `pytest -q` 已可通過，但 host provider 狀態仍需 runbook 修復與留證。
- Rollback: 回退上述檔案至本次變更前版本，恢復會話級 workaround 與原 parity/backfill 追蹤方式。

## 2026-04-20 Watchlist #1/#5/#6/#7/#8 收斂落地（驗證自動化 + dual-field migration）

- Decision: 在不改統計契約前提下，完成五項 active risk 的可重複驗證落地：  
  #1 補 `MainWindow` loader lifecycle（cancel/wait + stale-finish）測試；  
  #5 新增 `scripts/final_audit_runtime_report.py` 生成 quick/full 中位數報表；  
  #6 新增 `scripts/master_data_parity_audit.py` 生成 JSON vs SQLite parity 工件；  
  #7 新增 release pipeline 合約測試並鎖定 `release_check --with-release-ext` 邊界；  
  #8 對 `measurement_sessions` 導入雙工單欄位可重入 migration、CRUD/UI context 回填與 CSV 補值工具。
- Scope: `app/data/master_data_db.py`, `app/data/measurement_library.py`, `app/ui/pages/measurement_library_page.py`, `app/ui/main_window.py`, `scripts/final_audit_runtime_report.py`, `scripts/master_data_parity_audit.py`, `scripts/backfill_workorder_dual_fields.py`, `tests/test_main_window_data_loader_lifecycle.py`, `tests/test_release_check_plan_modules.py`, `tests/test_release_pipeline_contract.py`, `tests/test_final_audit_runtime_report.py`, `tests/test_measurement_library_dual_workorder_db_e2e.py`, `tests/test_backfill_workorder_dual_fields.py`, `tests/test_master_data_parity_audit.py`, `docs/open-questions.md`, this entry.
- Reason: 既有風險雖可追蹤，但缺乏「可持續關帳」的固定工件與邊界測試，且 #8 仍停留於資料層與 UI context 未完全打通。
- Impact: `docs/open-questions.md` 可直接附掛最新證據路徑（`Outputs/final_audit/runtime_report.json`、`Outputs/master_data/parity_report.json`、`Outputs/release/release_report.json`、`Outputs/master_data/workorder_backfill_report.json`）；`Watchlist #7` 編號與引用維持不變；四閘驗證持續可執行。
- Rollback: 回退上述檔案至本次提交前版本，恢復單工單欄位/舊測試集合與舊風險驗證方式。

## 2026-04-20 Active Risk Ledger Convergence (single source, keep Watchlist #7 compatibility)

- Decision: 將 **active risk** 追蹤收斂到 `docs/open-questions.md` 單一來源；僅保留可行動項（需具 `Next action` + `Revalidation gate`），並保留既有 **Watchlist #7** 編號與引用相容。
- Scope: `docs/open-questions.md`, `AGENTS.md`, `README.md`, `docs/README.md`, `C:\Users\user\.codex\AGENTS.md`, this entry.
- Reason: 風險敘述分散於多份文件時，容易造成「同一風險多版本」與追蹤失焦；需要單一 active ledger 才能維持可執行與可驗證的一致性。
- Impact: `open-questions` 成為唯一 active 風險清單；`decision-log` 保留歷史脈絡；治理規則同步要求殘餘風險必須附下一步與重驗證閘門。
- Risk: 若未同步更新 single source 入口（尤其 #7 邊界描述），跨文件敘述可能再次漂移。
- Rollback: revert 本次文件修改，恢復原 `open-questions` 結構與相關入口敘述。

## 2026-04-20 Final Documentation Convergence + AI Hallucination Rework Prevention Matrix

- Decision: 新增 `docs/governance/ai_hallucination_rework_prevention_matrix.md` 作為 rules/skills 優化的單一權威入口，整合歷史重工事件、高頻漂移主題、低 token 預防流程與可直接貼用模板（Prompt Guard / RCA Guard / Blast-Radius Guard）。
- Scope: `docs/governance/ai_hallucination_rework_prevention_matrix.md`, `README.md`, `docs/README.md`, `docs/specs/project_architecture.md`, `docs/specs/ui_design_spec.md`, `docs/reference/platform_overview.md`, `docs/reports/document_relocation_log.csv`, `docs/reports/document_relocation_summary.md`, `archive/cleanup_log.md`, this entry.
- Reason: 決策與規格在 2026-04 全期多次收斂後，仍出現「文件漂移 -> AI 重複修補 -> 再次對齊」循環，造成 token 與審查成本增加；需將「可驗證現況、常見幻覺假設、必跑閘門」收斂為單一可操作文件。
- Impact: 核心架構文件統一對齊 `main_window.py` 現況（無獨立 `WorkorderPage`、導覽 6 項、`量測`頁不進導覽）；歷史稽核快照與過期規劃文檔移至 `archive/unused/`，主線文件地圖改為以現行權威路徑為準。
- Rollback: 從 `archive/unused/` 將本次封存文件搬回原路徑並還原上述文檔更新；移轉紀錄可依 `docs/reports/document_relocation_log.csv` 反向回放。

## 2026-04-19 Documentation and Codebase Synchronization (Final Alignment)

- Decision: 全面進行系統文件與程式碼之對齊審計；更新 `README.md`、`project_architecture.md`、`ui_design_spec.md`、`data_contract.md` 與 `ui_state_semantics.md`，使其 100% 反映目前系統狀態（包含整合資料載入頁、Noto Sans TC 字型標準、與五大圖表分類）。
- Scope: `README.md`, `docs/specs/*.md`, this entry.
- Reason: 過去數次對話累積了 UI 結構調整（移除 `WorkorderPage`、整合 `DataSetupPage`）與視覺標準變更（Noto Sans TC），需確保文件與發行版本完全同步。
- Impact: 規格文件與現行主線程式碼達成一致，導覽索引、頁面堆疊、以及圖表分類定義均符合 `main_window.py` 與 `chart_registry.py` 之權威落實。
- Rollback: 無（純文件對齊回退通常指還原舊版 Markdown，不影響程式功能）。

## 2026-04-08 SPC chart taxonomy convergence step 2: root-cause flow aligned to same 5 categories

- Decision: `ROOT_CAUSE_FLOW_ORDER` 由 6 段（偵測偏移/確認偏移/驗證失控/時序對照/定位原因/機制驗證）收斂為與 UI 同步的 5 段：`process_monitoring / process_capability / anomaly_root_cause / variable_relationship / comparison_analysis`；同步調整 `CHART_ROOT_CAUSE_STAGE_BY_ID` 對應與 `CHART_NEXT_STEP_BY_ID` 跨類別建議路徑。
- Scope: `app/analytics/chart_registry.py`, `tests/test_chart_registry_acceptance.py`, `docs/specs/project_architecture.md`, this entry.
- Reason: 第一階段僅完成分類與套餐收斂，根因流程元資料仍沿用舊六段命名，造成 UI 分類與 drill-down metadata 不一致。
- Impact: `get_charts_by_root_cause_flow(...)` 與 `root_cause_stage` 欄位完全對齊五分類，導引路徑一致且可直接映射工程決策節點。
- Rollback: revert `ROOT_CAUSE_FLOW_ORDER` / `CHART_NEXT_STEP_BY_ID` to previous six-stage model and restore related tests/docs.

## 2026-04-08 SPC chart taxonomy refactor: consolidate to 5 decision categories

- Decision: `chart_registry` 與 UI 套餐（`report_intent_presets`）由多分類收斂為 **5 大工程決策分類**：製程監控、製程能力、異常根源、變數關係、比較分析；移除 UI 層「進階分析」分類，所有既有圖表重新歸位至上述五類且保留 SPI `Volume/Area/Height` 多維路徑（含 3F 監控/能力/根因圖）。
- Scope: `app/analytics/chart_registry.py`, `app/services/report_intent_presets.py`, `app/ui/pages/report_export_page.py`, `tests/test_chart_registry_acceptance.py`, `README.md`, `docs/README.md`, `docs/specs/project_architecture.md`, this entry.
- Reason: 原分類由「主流程 + Advanced」與多個套餐並存，分析目的混雜；需改為單一分析目的分類並直接對齊工程決策流程。
- Impact: 圖表頁與報告頁分類固定為 5 類，套餐按同一分類語意運作；圖表渲染與 payload 契約不變。
- Rollback: revert `chart_registry` 的 `CHART_UI_GROUPS_ORDER`/`CHART_UI_GROUP_BY_ID`/`CHART_ORDER`、`report_intent_presets` 內容與對應文件/測試更新。

## 2026-04-08 CI harness gate convergence: add `qt_audit` + `check_launch`

- Decision: 將 GitHub Actions workflow（`.github/workflows/pytest.yml`）的品質閘收斂為 `ruff -> mypy app -> pytest -q -> scripts/qt_audit.py app/ -> scripts/check_launch.py -> release_check --with-release-ext`，使 CI 直接對齊 repository harness gate（含 UI token/QSS 規則與啟動渲染檢查）。
- Scope: `.github/workflows/pytest.yml`, `README.md`, `docs/specs/project_architecture.md`, this entry.
- Reason: 先前 CI 只覆蓋 lint/type/test + release script，未直接強制 `qt_audit` 與 `check_launch`，與新 AGENTS/AI_RULES 的 harness gate 不完全一致。
- Impact: PR 與 main 分支在 merge 前即會攔截 UI 規範違規與啟動失敗；CI 失敗訊號更接近實際交付條件。
- Risk: CI 執行時間增加，且 `check_launch` 對 headless/Qt 環境較敏感（已透過 `QT_QPA_PLATFORM=offscreen` 降低風險）。
- Rollback: revert `.github/workflows/pytest.yml` 新增步驟，並回退 `README.md`/`project_architecture.md` 對應敘述。

## 2026-04-08 Platform Renaming: Changed to "SPI 製程統計分析"

- Decision: 將系統正式名稱由「SMT SPI / SPC 統計分析平台 v2」更改為「**SPI 製程統計分析**」，以更精簡地反映系統核心價值。
- Scope: `app/bootstrap/app_config.py` (`APP_NAME`), `app/ui/widgets/collapsible_sidebar.py` (brand label), `README.md`, `docs/specs/project_architecture.md`, `docs/specs/ui_design_spec.md`, `docs/reference/platform_overview.md`, this entry.
- Rollback: revert `APP_NAME` and brand labels across listed files.

## 2026-04-08 Sidebar navigation: '量測資料庫' renamed to '資料庫管理'

- Decision: 將側邊導覽列的 **「量測資料庫」** (Nav 2) 重新命名為 **「資料庫管理」**，以與對應頁面標題（`MeasurementLibraryPage`）保持用語一致。同步更新 `main_window.py` 導覽清單、無障礙描述、`README.md`、`project_architecture.md` 以及 `navigation_panel.py` 的工具提示。
- Scope: `app/ui/main_window.py`, `app/ui/widgets/navigation_panel.py`, `README.md`, `docs/specs/project_architecture.md`, `app/ui/pages/measurement_library_page.py` (header tooltip), this entry.
- Rollback: restore label to '量測資料庫' across listed files.

## 2026-04-06 Report export: UX copy alignment (證據圖／匯出範圍摘要)

- Decision: 匯出確認對話框與 **`ReportExportPage`** 預覽區 **[F]** 統一用語：**證據圖**、**預估畫廊頁數**、**敘事頁「分布分析」**；預覽區標題由「圖表覆蓋摘要」改為 **匯出範圍摘要**；**另存 PPTX** Tooltip 補述選檔後確認清單再寫檔。
- Scope: `app/ui/dialogs/pptx_export_confirm_dialog.py`, `app/ui/pages/report_export_page.py`, `tests/test_pptx_export_confirm_dialog.py`, `tests/test_report_preview_summary.py`, `README.md`, `docs/specs/project_architecture.md`, `docs/specs/data_contract.md`, `docs/specs/ui_design_spec.md`, `docs/specs/ui_state_semantics.md`, this entry.
- Rollback: restore prior strings in listed files; remove this entry.

## 2026-04-06 Report export: pre-export confirmation checklist

- Decision: `ReportExportPage` 在「另存 PPTX」選擇路徑後，新增唯讀確認對話框；內容包含實際匯出圖表名稱、圖表張數、預估畫廊頁數（每頁 4 張）、以及工程報告固定包含「分布分析」敘事頁的明示說明。使用者按下確認後才呼叫 `ReportService.generate_pptx_report(...)` 寫檔。
- Scope: `app/ui/pages/report_export_page.py`, `app/ui/dialogs/pptx_export_confirm_dialog.py`, `tests/test_report_preview_summary.py`, `tests/test_pptx_export_confirm_dialog.py`, `README.md`, `docs/specs/project_architecture.md`, `docs/open-questions.md`, this entry.
- Rollback: remove confirmation dialog flow and related tests/docs; restore direct export after file selection.

## 2026-04-06 Report export: engineering-only PPTX template

- Decision: **`ReportExportPage`** 移除「管理／工程報告」模板切換與「保留／重設模板」等 UI；固定 **`engineering`** 工程報告預設圖表集與 **PPTX-only** 匯出；**`ReportService.TEMPLATE_DEFAULT_CHARTS`** 刪除 `management`；**`pptx_report_builder`** 封面標籤固定為工程報告。
- Scope: `app/ui/pages/report_export_page.py`, `app/services/report_service.py`, `app/services/pptx_report_builder.py`, `tests/test_report_preview_summary.py`, `README.md`, `docs/specs/project_architecture.md`, `docs/specs/data_contract.md`, `docs/specs/ui_design_spec.md`, `docs/specs/ui_target_layout.md`, `docs/specs/ui_state_semantics.md`, this entry.
- Rollback: restore prior template combos and `management` chart list; revert docs/tests.

## 2026-04-06 Report export: copy convergence + explicit `engineering` resolution

- Decision: **`generate_pptx_report`** 一律以 **`resolved_template = engineering`**（舊參數非 `engineering` 時 `debug` 記錄）；診斷篩選與 PPTX 使用者可見字串將「模板」改為「匯出勾選」語意；**`navigation_panel`**／**`platform_overview`**／**`open-questions`** 對齊現行行為。
- Scope: `app/services/report_service.py`, `app/services/pptx_report_builder.py`, `app/ui/pages/report_export_page.py`, `app/ui/widgets/navigation_panel.py`, `docs/open-questions.md`, `docs/reference/platform_overview.md`, `tests/test_report_preview_summary.py`, `tests/test_report_template_filtering.py`, this entry.
- Rollback: revert listed files; remove this entry.

## 2026-04-06 Report export: spec wording sweep (PPTX-only)

- Decision: 將仍寫「模板導向」之 **`docs/specs/ui_design_spec.md`**（§1、§19、§20）、**`docs/specs/project_architecture.md`**（開頭摘要、頁面表、§7、`template_type` 敘述、修訂列註）、**`docs/specs/data_contract.md`** §15 標題與 `template_type` 說明、**`docs/README.md`** 架構表列，統一改為 **工程／PPTX-only** 語意，避免與已移除之雙模板 UI 混淆。
- **補遺（同日主線 README）**：根目錄 **`README.md`**「Runtime Flow」仍含 `template-driven` 英文殘留，改為 **PPTX-only engineering** 與 `template_type=engineering` 敘述一致。
- Scope: listed `docs/**` paths, repo root `README.md`, this entry.
- Rollback: revert listed docs; remove this entry.

## 2026-04-06 Report export: historical decision-log supersession notes

- Decision: 在 **2026-04-05**「Watchlist／follow-up」**#3**、**2026-04-03**「Multi-feature UX Convergence Phase A」「Report Export Contract Convergence」「SPC Engineering UI One-shot Refactor」等條目內，補上 **2026-04-06 engineering-only** 已取代舊「preserve/reset」與雙模板敘述之註記；**`docs/open-questions.md`** 用語改為全中文（避免 `preserve/reset` 殘留）。
- Scope: `docs/decision-log.md`, `docs/open-questions.md`, this entry.
- Rollback: revert those paragraphs; remove this entry.

## 2026-04-06 `docs/reports` snapshots: PPTX-only wording

- Decision: 歷史快照 **`docs/reports/convergence_closeout_2026-04-02.md`** 後續補遺中「PPTX/HTML」改為 **PPTX-only** 並註明 UI 不匯出 HTML；**`docs/reports/ui_refactor_patch_summary.md`** 區塊引言補 **engineering-only** 匯出註記；**`docs/reports/README.md`** 範例行舉與現行契約對齊。
- Scope: `docs/reports/convergence_closeout_2026-04-02.md`, `docs/reports/ui_refactor_patch_summary.md`, `docs/reports/README.md`, this entry.
- Rollback: revert three files; remove this entry.

## 2026-04-06 `main_window`: shortcuts + a11y string vs nav labels

- Decision: 修正 **`MainWindow`** 註解：**Ctrl+快捷鍵** 為 **1..7** 對應左欄 **7** 鍵（先前誤寫 6）；**`_go_to_page`** docstring 同步；**無障礙描述**「診斷建議」→ **「診斷分析」**（與 **`NAV_PHASES`** 一致）；**`_on_nav_step_clicked`** docstring 改為「經 **`NAV_TO_STACK`** 對應堆疊索引」避免讀成「`NAV_TO_STACK` 等於堆疊索引」。
- Scope: `app/ui/main_window.py`, this entry.
- Rollback: revert `main_window.py`; remove this entry.

## 2026-04-06 `navigation_panel` docstrings + `project_architecture` §11 paths

- Decision: Clarify **`NavigationPanel`** 模組／類別／**`set_current_stack_index`** 說明：信號與選取狀態使用 **導覽索引 0..6**（與 **`MainWindow.NAV_TO_STACK`** 對應），**不是** workspace **`QStackedWidget`** 的 raw index；方法名保留以相容 **`MainWindow`**。**`docs/specs/project_architecture.md`** §11 修訂列（2026-04-06）將裸檔名改為 **`docs/specs/…`** 完整路徑。
- Scope: `app/ui/widgets/navigation_panel.py`, `docs/specs/project_architecture.md`, this entry.
- Rollback: revert two files; remove this entry.

## 2026-04-06 UI tokens + PPTX: nav wording + P10 comment disambiguation

- Decision: **`tokens.py`** 導覽階段色註解由「統計分析階段」改為與左欄一致之 **管制圖／診斷分析**；**`pptx_report_builder.py`** P10 區塊註解標明為 **簡報章節標題**（appendix），避免讀成已移除之桌面「統計」分頁。
- Scope: `app/ui/theme/tokens.py`, `app/services/pptx_report_builder.py`, this entry.
- Rollback: revert two files; remove this entry.

## 2026-04-06 Code + release-validation docs: `SPC_RULES` path convergence

- Decision: 將 **`app/analytics`**（`capability_engine`、`spc_engine`、`statistical_utils`、`process_diagnosis_engine`）與相關 **測試 docstring／assert 訊息** 中裸寫之 **`SPC_RULES.md`** 改為 **`docs/governance/SPC_RULES.md`**；同步 **`docs/specs/release_validation_*.md`**、**`docs/open-questions.md` Watchlist #7**、**`.cursor/plans/README.md`** 之表格與敘述。
- Scope: listed `app/`、`tests/`、`.cursor/plans/README.md`、`docs/specs/release_validation_coverage.md`、`docs/specs/release_validation_gap_matrix.md`、`docs/specs/release_validation_data_flow_and_tolerance.md`、`docs/open-questions.md`, `docs/decision-log.md` (this entry).
- Rollback: revert listed files; remove this entry.

## 2026-04-06 Docs: full paths for cross-spec links (`docs/specs/*`, `docs/reports/*`)

- Decision: 將多處 **僅寫檔名** 之互相引用改為 **repo 相對完整路徑**，避免與根目錄或其他資料夾同名檔混淆；涵蓋 **`docs/specs/spec_maintenance_and_alignment.md`**（§1 觸發表、§4、修訂列）、**`ui_design_spec.md`**、**`ui_target_layout.md`**、**`project_architecture.md`**（§9 長句與修訂表）、**`release_validation_coverage.md`**、**`issue_resolution_workflow.md`**、**`docs/reference/platform_overview.md`**、**`golden_dataset/README.md`**、**`docs/reports/ui_refactor_patch_summary.md`**、**`docs/README.md`** 架構表一列。
- Scope: listed paths, this entry.
- Rollback: revert touched files; remove this entry.

## 2026-04-06 Spec maintenance + ui_state_semantics: alignment doc paths

- Decision: **`docs/specs/spec_maintenance_and_alignment.md`** §1 觸發表「計畫檔過期」列與 **§2** 標題改為明確指向 **`docs/plans/document_alignment_patch_plan.md`**／**`docs/reports/document_alignment_report.md`**（移除不存在的 `docs/document_alignment_*.md` 萬用字元）；**`docs/specs/ui_state_semantics.md`** §4 標題與 **`agent-residence-minimal.mdc`** Verify 行補上 **`docs/specs/spec_maintenance_and_alignment.md`** 完整路徑。
- Scope: `docs/specs/spec_maintenance_and_alignment.md`, `docs/specs/ui_state_semantics.md`, `.cursor/rules/agent-residence-minimal.mdc`, this entry.
- Rollback: revert three files; remove this entry.

## 2026-04-06 Cursor + PR template: docs path convergence (specs/plans/reports)

- Decision: 將 **`.cursor/plans/README.md`**、**`.cursor/skills/smt-spi-ui-conventions/SKILL.md`**、**`.cursor/rules/ui-theme-and-layout.mdc`**、**`.cursor/rules/ai-planning-and-root-cause.mdc`**（globs 與內文）、**`.cursor/rules/agent-residence-minimal.mdc`** 中仍指向 `docs/` 根目錄的連結，改為實際位置：**`docs/specs/*`**、**`docs/plans/*`**、**`docs/reports/*`**；同步修正 **`.github/pull_request_template.md`** 之 `spec_maintenance`／工作流／範本路徑。
- Scope: listed `.cursor/**` files, `.github/pull_request_template.md`, this entry.
- Rollback: revert listed files; remove this entry.

## 2026-04-06 Spec + QSS: verification path + dashboard wording

- Decision: **`docs/specs/spec_maintenance_and_alignment.md`** 驗收觸發列改指向 **`docs/reports/ui_self_verification_report.md`**（完整路徑）；**`diagnostic_page.py`** 模組說明改為 **payload summary + 診斷建議**（避免「Statistics Summary」讀成已移除分頁）；**`dark_stylesheet.py`** 區塊註解 **Statistics Dashboard → Process diagnosis dashboard (DiagnosticPage)**，**statsResult** 旁註改為 *Statistical test result*（與常態性檢定語意一致）。
- Scope: `docs/specs/spec_maintenance_and_alignment.md`, `app/ui/pages/diagnostic_page.py`, `app/ui/theme/dark_stylesheet.py`, this entry.
- Rollback: revert three code/spec files; remove this entry.

## 2026-04-06 Skills + presentations: report paths + deck wording (DiagnosticPage)

- Decision: Fix **`.cursor/skills/smt-spi-ui-conventions/SKILL.md`**「實作摘要／驗收報告」連結至搬移後路徑 **`docs/reports/ui_refactor_patch_summary.md`**、**`docs/reports/ui_self_verification_report.md`**；**`presentations/smt-spi-platform-overview/build_deck.js`** 之 `UI_SHOTS`、工程導入流程、功能對照表與案例 1 文案改與左欄「**診斷分析**」及 **製程診斷儀表板**一致，避免讀成獨立「統計」分頁。（截圖檔名 `03_statistics.png` 保留以免破圖。）
- Scope: `.cursor/skills/smt-spi-ui-conventions/SKILL.md`, `presentations/smt-spi-platform-overview/build_deck.js`, this entry.
- Rollback: revert two files; remove this entry.

## 2026-04-06 Documentation: main window + diagnostic dashboard alignment

- Decision: Align **README**、**project_architecture**、**docs/README**、**platform_overview**、**process_dashboard_figma_alignment** with current UI: `STACK_ORDER` includes **量測庫**; **量測** stack page is omitted from left nav; standalone **Statistics** page is removed — **製程診斷儀表板** lives in **`DiagnosticPage`** (`app/ui/pages/diagnostic_page.py`). Replace stale references to non-existent `statistics_page.py` in the Figma alignment spec; **§5** grids now match `_init_dashboard_sections`.
- Decision: Update **`navigation_panel.NAV_STEP_TOOLTIPS`** to match **`NAV_PHASES`** (量測資料庫 / 診斷分析 wording).
- Scope: listed Markdown files, `docs/specs/ui_design_spec.md`（頁面堆疊／導覽）、`app/ui/widgets/navigation_panel.py`, this entry.
- Rollback: revert the listed files.

## 2026-04-06 Documentation: specs convergence (Statistics → DiagnosticPage)

- Decision: Align **`ui_design_spec.md`** §8–§9、`data_contract.md` §14 引言、`ui_state_semantics.md` §3、`project_architecture.md` §6 用語、**`process_dashboard_figma_alignment.md`** 修訂列、驗收快照 **`docs/reports/ui_*.md`** 與 **`diagnostic_page.update_table` docstring**，使「統計頁／Statistics page」敘述與 **`DiagnosticPage`** 一致。
- Scope: listed specs/reports, `archive/unused/reports/ui_audit_report.md`／`font_clarity_acceptance_summary.md`, `app/analytics/summary_engine.py`, `app/ui/widgets/process_dashboard_cards.py`, `app/ui/pages/diagnostic_page.py`, this entry.
- Rollback: revert touched files.

### Historical terminology（決策條目追溯用）

2026-04-05 及更早之 **`StatisticsPage`**、**`app/ui/pages/statistics_page.py`** 於 **2026-04-06** 起已歸併為 **`DiagnosticPage`**（`app/ui/pages/diagnostic_page.py`）。**更下方舊條目原文不修改**；若 Scope 仍列舊檔名，以本註與現行程式為準。

## 2026-04-06 Docs + tooling: `ui_target_layout`, Claude py_compile, mypy cache

- Decision: Update **`docs/specs/ui_target_layout.md`** 右欄頁面列表（移除獨立「統計」、補 **量測庫**／量測不在導覽）；**`.claude/settings.local.json`** 將 `py_compile` 目標由已刪除之 `statistics_page.py` 改為 **`diagnostic_page.py`**；精簡 **`tests/test_summary_mode_switch.py`** 與 **`DiagnosticPage.update_table`** 註解；刪除 **`.mypy_cache/**/statistics_page.*`** 殘留快取。
- Scope: listed paths, this entry.
- Rollback: restore prior strings; mypy 會於下次執行重建快取。

## 2026-04-06 QA skill + verification snapshot wording + pytest cache

- Decision: Align **`.claude/skills/qa-auto-engineer/SKILL.md`**（Phase 2 **§2-3**、Phase 3 **§3-6**）與現行左側「**診斷分析**」／**`DiagnosticPage`**；更新 **`docs/reports/ui_self_verification_report.md`** 中仍寫「統計頁」之驗收句；執行 **`python -m pytest --cache-clear -q`** 清除 **`.pytest_cache`** 內過期 nodeids（舊 `test_statistics_page_*` 名稱）。
- Scope: listed files, this entry.
- Rollback: revert SKILL／驗收報告文案；pytest 快取可刪 `.pytest_cache` 後由本機重跑重建。

## 2026-04-06 Sync `.agents` QA skill + tokens/README wording

- Decision: Mirror **`.claude/skills/qa-auto-engineer/SKILL.md`** 之 §2-3／§3-6 更新至 **`.agents/skills/qa-auto-engineer/SKILL.md`**；**`tokens.py`** 儀表板註解由「統計頁」改為 **`DiagnosticPage`**；**`README.md`** runtime 流程列精簡（移除冗餘「舊統計頁」字樣）。
- Scope: listed files, this entry.
- Rollback: revert three files.

## 2026-04-06 Code/docs: main_window next-step comment + data_contract §12 disambiguation

- Decision: Correct **`MainWindow._on_next_step_clicked`** comment（「跳至統計」→ 實際為略過量測、進入**圖表** index 3）；在 **`data_contract.md` §12** 標明「統計摘要」指 **`payload["summary"]`**，避免與已移除之獨立統計分頁混淆；**`ui_design_spec.md` §8** 一句話收斂合併敘述；修正 **`_on_nav_step_clicked`**／**`navigation_panel.step_clicked`** 註解（導覽鍵為 **0..6** 共七項，非 0..5）。
- Scope: `app/ui/main_window.py`, `app/ui/widgets/navigation_panel.py`, `docs/specs/data_contract.md`, `docs/specs/ui_design_spec.md`, this entry.
- Rollback: revert listed files.

## 2026-04-06 SPI process knowledge base (JSON bundle + xlsx import)

- Decision: **Reference workbook** for v1 content: **`SPI_製程對應知識庫_v1.0.xlsx`** (constant **`CANONICAL_SPI_KB_WORKBOOK_BASENAME`** in `spi_process_kb_loader.py`); `manifest.json` may record `source_xlsx_basename`, `canonical_workbook_basename`, and `source_xlsx_sha256` after import; **`data_contract.md` §12.4** documents Excel → JSON.
- Decision: Ship **`data/spi_process_kb/v1/`** with four JSON files (`multi_signal_rules.json`, `dimension_abnormality_matrix.json`, `inspection_checklist.json`, `chart_signal_lookup.json`) + **`manifest.json`** (`schema_version` **1.0.0**, optional `source_xlsx_sha256`).
- Decision: Add **`app/services/spi_process_kb_loader.py`** (validate + load), **`app/services/spi_process_kb_matcher.py`** (heuristic R-rule matching + matrix / chart-lookup / checklist merge), extend **`run_multi_signal_diagnosis`** with `kb_*` fields; PPTX P5 shows KB status and top matches.
- Decision: Add **`scripts/import_spi_process_kb_xlsx.py`** and runtime dep **`openpyxl`** in **`docs/reference/requirements.txt`** for xlsx→JSON maintenance.
- Scope: `data/spi_process_kb/v1/**`, `app/services/multi_signal_diagnosis.py`, `app/services/pptx_report_builder.py`, `tests/test_spi_process_kb.py`, `README.md`, this entry.
- Rollback: remove KB files and matcher wiring; revert `multi_signal_diagnosis` return shape and PPTX block.

## 2026-04-06 Process dashboard Figma alignment spec

- Decision: Add **`docs/specs/process_dashboard_figma_alignment.md`** as the design handoff for the Statistics「製程診斷儀表板」: eight section grids aligned to `statistics_page.py`, `KpiCell` tier / `valueState` / `alarmTone`, and token mapping from `tokens.py` + process-dashboard QSS in `dark_stylesheet.py`.
- Scope: `docs/specs/process_dashboard_figma_alignment.md`, `docs/specs/project_architecture.md` (Statistics bullet), `docs/README.md` (specs table), `README.md` (one-line pointer), this entry.
- Rollback: remove the new spec and revert the four cross-reference edits.

## 2026-04-05 Process diagnosis engine + dashboard layer_8

- Decision: Add **`app/analytics/process_diagnosis_engine.py`** — heuristic-only rules (thresholds in-module, **`THRESHOLDS_VERSION`**); **not** statistical authority vs `docs/governance/SPC_RULES.md`. Outputs **`issue_type`**, Chinese **`root_cause_zh`** / **`recommended_action_zh`**, **`priority`**, **`process_diagnosis_flags`**, **`defect_pattern`** for dashboard use.
- Decision: Extend **`compute_summary`** `dashboard_layers` with **`layer_1_alarm.issue_type`**, **`layer_1_alarm.issue_type_display_zh`**, **`layer_4_defect_structure.defect_pattern`** / **`defect_pattern_zh`**, **`layer_5_spec_analysis.process_diagnosis`**, and **`layer_8_diagnosis`** (mirrors engine output + flags).
- Decision: Refactor **`StatisticsPage`** card order to align **layer_3 資料 → layer_4 缺陷 → layer_5 規格**; add **第 8 卡診斷與建議**; KPI row promotes **主特徵 Cpk** and large tiers for Yield / DPMO / Sigma / mean shift / Std÷Spec.
- Scope: `app/analytics/process_diagnosis_engine.py`, `app/analytics/summary_engine.py`, `app/ui/pages/statistics_page.py`, `tests/test_process_diagnosis_engine.py`, `tests/test_summary_mode_switch.py`, `tests/release_validation/test_phase1_infrastructure.py`, this entry.
- Rollback: remove engine and `layer_8_*` wiring; restore prior `statistics_page` layout and layer keys.

## 2026-04-05 Validation report schema v2 + release gate script

- Decision: Bump **`validation/report_schema.py`** `REPORT_SCHEMA_VERSION` to **`2`**. Replace top-level **`modules`** with nine fixed section keys (`dataset_validation`, `statistical_validation`, `spec_validation`, `kpi_validation`, `chart_validation`, `report_validation`, `feature_switch_validation`, `non_computable_validation`, `deterministic_validation`) plus **`final_result`** (`status`, **`release_allowed`**); keep **`tests`**, **`failed_tests`**, **`junit_summary`**, **`pytest_exit_code`** for debugging. Ordered substring rules map JUnit cases to sections (first match wins); unmatched → **`statistical_validation`** with **`unmapped_tests_count`**.
- Decision: Add **`scripts/run_release_gate.py`** (default **`Outputs/release_validation_report.json`**); process exit **0** iff **`release_allowed`** is true (requires pytest exit 0 and all nine section statuses PASS).
- Scope: `validation/report_builder.py`, `validation/report_schema.py`, `scripts/run_validation.py`, `scripts/run_release_gate.py`, `tests/test_validation_report_builder.py`, `README.md`, `AGENTS.md`, `docs/specs/project_architecture.md`, this entry.
- Rollback: restore schema v1 and `modules` summary in `report_builder`; remove `run_release_gate.py` and new tests.

## 2026-04-05 Golden dataset root + validation runner + dashboard Layers 4–7

- Decision: Move release-validation CSV/JSON fixtures to repo root **`golden_dataset/`** (single source of truth); `tests/fixtures/golden/` reduced to a pointer README. Pytest resolves via `tests/release_validation/conftest.py` and optional **`GOLDEN_DATASET_ROOT`**.
- Decision: Add **`validation/`** package (domain stubs + `report_builder` JUnit → JSON) and **`scripts/run_validation.py`**, default output **`Outputs/validation_report.json`**.
- Decision: Fix **`StatisticsPage`** Yield display (`yield_pct` is 0–100, not a 0–1 ratio); align PPTX golden snippet; add tests for yield range and SPC OOC vs `per_feature_alarm`.
- Decision: Extend **`compute_summary`** with optional `primary_feature` / `workorder_master` and additive **`layer_4_defect_structure`** … **`layer_7_engineering_info`**; wire through **`compute_analysis_payload`**, **`ReportService`**, **`AnalysisWorker`**, and **`StatisticsPage`** UI.
- Scope: `golden_dataset/**`, `validation/**`, `scripts/run_validation.py`, `scripts/release_check.py`, `scripts/record_performance_baseline.py`, `app/analytics/summary_engine.py`, `app/viewmodels/chart_analysis_viewmodel.py`, `app/services/report_service.py`, `app/ui/main_window.py`, `app/ui/pages/statistics_page.py`, `docs/specs/data_contract.md` §14.4–14.7, `docs/specs/release_validation_coverage.md`, `docs/specs/release_validation_data_flow_and_tolerance.md`, affected tests, `README.md`, `AGENTS.md`, this entry.
- Rollback: restore `tests/fixtures/golden` tree, revert path rewires, remove new dashboard keys (breaking UI/tests).

## 2026-04-05 Watchlist／follow-up 收斂（#1–#4、#7 B／A、baseline PNG）

- **#4 autoswitch hint**：`ChartAnalysisPage._refresh_chart_selector` 開頭清空 `_autoswitch_reason`；測試 `tests/test_feature_interaction_logic.py`。
- **#3 報告模板**（2026-04-05 當時敘述；**2026-04-06 起**已由單一工程 PPTX、無 preserve/reset／雙模板 UI 取代，見本檔「Report export: engineering-only PPTX template」）：曾描述匯出頁 `reset` 預設與 `QSettings`、`preserve`／`reset` 說明；相關測試／`ui_state_semantics` 後續已對齊新行為。
- **#2 零變異常態**：`SPC_RULES.md` §2.1 文件化；`tests/test_normality_engine_zero_variance.py`；`open-questions` 移至 Recently resolved。
- **#1 執行緒**：`tests/test_data_loader_worker_thread.py`（`DataLoaderWorker.start` + `QEventLoop`）；Watchlist #1 收窄為殘餘整合風險。
- **#7 B**：`tests/test_golden_csv_master_db_analysis_e2e.py`（子程序 `SPC_MASTER_DB_PATH` + `normal_baseline` CSV + `compute_analysis_payload`）。
- **#7 A**：`tests/test_measurement_loader_column_contract.py`。
- **視覺 baseline**：`tests/baseline_images/density_chart_default.png` + `tests/test_chart_baseline_png.py` + `tests/baseline_images/README.md`。
- **測試輔助**：`tests/helpers` 套件與頂層 `tests/helpers.py` 名稱衝突排除 — `assert_engine_contract` 移至 [`tests/helpers/engine_contract.py`](../tests/helpers/engine_contract.py)，刪除重複之 `tests/helpers.py`。
- Scope: 上述檔案、`docs/open-questions.md`、`docs/specs/release_validation_gap_matrix.md`（A／B 列）、本條目。
- Rollback: revert touched files and restore prior watchlist text.

## 2026-04-05 CI：`release_check --with-release-ext`

- Decision: [.github/workflows/pytest.yml](../.github/workflows/pytest.yml) 在完整 `pytest -q` 之後新增一步 **`python scripts/release_check.py --skip-ruff --skip-mypy --with-release-ext`**，以在 CI 演練 `release_check` 編排、`tests/release_validation`、三個 traceability 測試與 **`release_report.json`** 欄位；`--skip-ruff`／`--skip-mypy` 避免與前兩步重複。
- Scope: workflow、README「Validation Baseline」、`docs/open-questions.md` Watchlist #5 Note（與 #7 對齊）、`docs/specs/project_architecture.md` §9、[review/exception_pass_audit_2026-04-05.md](review/exception_pass_audit_2026-04-05.md)（限定範圍 `pass`／except 審計清單）、本條目。
- Rollback: 刪除該 job 步驟並還原上述文件敘述。

## 2026-04-05 `release_check.py --with-release-ext`

- Decision: add optional flag **`--with-release-ext`** to [scripts/release_check.py](../scripts/release_check.py): after `tests/release_validation`, run `pytest -q` on `tests/test_data_contract_code_alignment.py`, `tests/test_spec_resolver_master_db_e2e.py`, `tests/test_release_check_plan_modules.py` (step key `pytest_release_traceability_ext`, timeout 900s). [Outputs/release/release_report.json](../Outputs/release/release_report.json) gains **`release_ext_enabled`** and **`release_ext_paths`** (schema_version remains **3**). Default behavior unchanged when flag omitted.
- Scope: script + README, `docs/README.md`, `final_audit_suite.md`, `release_validation_coverage.md`, `release_validation_data_flow_and_tolerance.md`, `project_architecture.md`, `platform_overview.md`, `open-questions.md` Watchlist #7, `docs/decision-log.md` (this entry).
- Rollback: remove flag, second pytest step, report keys, and doc mentions.

## 2026-04-05 Docs: single pointer to release-validation watchlist (#7)

- Decision: deduplicate narrative — `release_validation_gap_matrix.md` §後續擴充、`release_validation_coverage.md` §3、`release_validation_data_flow_and_tolerance.md` §4、README、`docs/README.md`、`final_audit_suite.md`、`project_architecture.md`、`platform_overview.md` now **link to** `docs/open-questions.md` Watchlist **#7**; expand #7 title to state it is the **single watchlist source** for optional follow-ups and `release_check` boundaries.
- Rollback: restore prior paragraphs in touched docs and shorten Watchlist #7 title.

## 2026-04-05 `open-questions.md` — release validation watchlist (#7)

- Decision: add Watchlist item **7** (release validation residual scope, `release_check` vs full pytest, optional B/A/RNG, Xbar-R table authority note); bump **Last updated** to 2026-04-05.
- Scope: `docs/open-questions.md`, `docs/decision-log.md` (this entry).
- Rollback: remove item 7 and restore prior date if obsolete.

## 2026-04-05 SPC_RULES numeric contract tests (D depth)

- Decision: add `tests/release_validation/test_spc_rules_numeric_contract.py` — assert `SPC_RULES.md` contains **d2 = 1.128** and documented **z₀.₉₇₅**; `SPCEngine.I_MR_D2` == `capability_engine._D2_N2`; `scipy.stats.norm.ppf(1 - CPK_CI_ALPHA/2)` matches spec literal; Cp **6σ** / one-sided **3σ** constants vs spec text; **Xbar-R** `(A2, D3, D4)` table equals frozen AIAG-style reference (must stay in sync with `xbar_r_engine`); SPC min-sample language vs `StatisticalUtils` for N=9. Extend `release_check` **D** plan_modules and gap/coverage/data_flow notes.
- Rollback: remove test file and revert doc/script enumerations.

## 2026-04-05 Data contract code alignment tests (A ext)

- Decision: add `tests/test_data_contract_code_alignment.py` — assert `docs/specs/data_contract.md` exists；`SchemaMapper` 別名涵蓋契約表範例（Ref／Component／Panel／Vol／A／H／Center-X／Center-Y）；`ORDER_COL_PRIORITY` 時間欄序與 Board／Panel 位置；`FEATURE_COLUMNS` 與量測別名字典一致；`validate_*_schema` 最小欄位煙霧。
- Scope: 新測試檔、`release_validation_gap_matrix.md`、`release_validation_coverage.md`、`docs/decision-log.md`。
- Rollback: delete test file and revert three docs.

## 2026-04-05 Master DB override + stepped stencil SQLite E2E

- Decision: `app/data/master_data_db.db_path()` honors env **`SPC_MASTER_DB_PATH`** (absolute SQLite path) for tests/automation; add `tests/test_spec_resolver_master_db_e2e.py` (subprocess + tempfile DB: stepped spec without precision assignments blocks, with `save_assignments` succeeds); add `tests/test_release_check_plan_modules.py` (plan module index values are `str` or `list[str]`).
- Scope: `master_data_db.py`, 兩測試檔、`release_validation_gap_matrix.md`、`release_validation_coverage.md`、`tests/fixtures/golden/README.md`、`docs/decision-log.md`。
- Rollback: remove env branch in `db_path`, delete tests, revert docs.

## 2026-04-05 Release validation：收斂 D／RNG + plan_modules

- Decision: add `test_spc_rules_release_authority.py`（`SPC_RULES.md` 存在、最小篇幅、Cp／I-MR 等錨點；`spec_maintenance_and_alignment.md` 須提及 SPC_RULES）；add `test_determinism_surface_release.py`（`app/` 不得含 `np.random.`／`numpy.random.`）；`test_manifest_release_contract.py` 強制各情境 `determinism.notes` 非空；`release_check.py` 之 `release_validation_plan_modules`：**B**、**D** 改為路徑清單（含階梯 resolver、SPC 權威測試）。gap 矩陣 **D**、**RNG** 標 **Y**；後續擴充段落改為可選 DB／逐欄契約／未來引入隨機時之注意事項。
- Scope: 上述測試與腳本、`release_validation_gap_matrix.md`、`release_validation_coverage.md`、`docs/decision-log.md`。
- Rollback: 刪除兩新測試檔、還原 manifest 契約與 `release_check` 對應鍵、還原 gap／coverage／本條目。

## 2026-04-05 Release validation：階梯鋼板 spec resolver（B）

- Decision: add `tests/release_validation/test_spec_stencil_stepped_resolver.py` — mock `get_product_spec`／`has_any_precision_assignment`／`get_profile_by_refdes`／`build_height_spec` 以驗證階梯鋼板無精密指派時阻擋、有指派時產出 workorder_spec、以及 `resolve_height_spec_by_refdes` 區分 precision vs main；普通鋼板全 RefDes 同 main 高度。
- Scope: 新測試檔、`release_validation_gap_matrix.md`（B→Y）、`release_validation_coverage.md`、`tests/fixtures/golden/README.md`、`docs/decision-log.md`。
- Reason: 補齊計畫 **B（spec_stencil）** 之階梯語意，無需 SQLite golden。
- Rollback: 刪除測試檔並還原四份文件列舉。

## 2026-04-05 Golden `timestamp_lowercase_measurements` + `refdes_suffix_strip_join`

- Decision: add `timestamp_lowercase_measurements`（小寫 `timestamp` 欄）與 `refdes_suffix_strip_join`（`R1_1`/`R2_1` vs 座標 `R1`/`R2`，JoinEngine **&lt;10% 嚴格匹配** 觸發尾碼 strip）；擴充 `_JOIN_COORD_SCENARIOS`、`_TIME_ORDER_SCENARIOS`、phase1 time-like 參數化；`test_refdes_suffix_strip_join_xy_matches_coord_table`、`test_refdes_suffix_strip_join_volume_stats_vs_manifest`；`release_validation_data_flow_and_tolerance.md` 補 Join 列。
- Scope: 兩新目錄、`test_join_conservation_golden.py`、`test_phase1_infrastructure.py`、`golden/README.md`、`release_validation_coverage.md`、`release_validation_gap_matrix.md`、`release_validation_data_flow_and_tolerance.md`、`docs/decision-log.md`。
- Reason: 覆蓋 `ORDER_COL_PRIORITY` 之 `timestamp` 與 join **Pass 122／fallback** 行為。
- Rollback: 刪除兩目錄與相關測試／文件列舉。

## 2026-04-05 Golden `datetime_alias_measurements` + `partial_coord_match`

- Decision: add `datetime_alias_measurements`（`DateTime` 欄、與 time-only 同網格）與 `partial_coord_match`（12 筆量測、**R99 無座標**、join 10/2）；擴充 `_JOIN_COORD_SCENARIOS`、`_TIME_ORDER_SCENARIOS`；`test_partial_coord_match_unmatched_rows_have_no_xy`；phase1 之 time-like volume 測試含 `DateTime`、新增 `test_partial_coord_match_volume_stats_vs_manifest`。
- Scope: `tests/fixtures/golden/datetime_alias_measurements/`、`partial_coord_match/`、`test_join_conservation_golden.py`、`test_phase1_infrastructure.py`、`golden/README.md`、`release_validation_coverage.md`、`release_validation_gap_matrix.md`、`docs/decision-log.md`。
- Reason: 時間欄別名覆蓋 `DateTime`；資料契約 **匹配／未匹配** 與左連接行為之 golden。
- Rollback: 刪除兩目錄與相關測試／文件列舉。

## 2026-04-05 Golden `timestamp_alias_measurements` + `duplicate_refdes_coords`

- Decision: add `timestamp_alias_measurements`（`Timestamp` 欄、其餘同 time-only 網格）與 `duplicate_refdes_coords`（normal 量測 + coords 內 **R1 雙列**）；`time_only_measurements` manifest 補 `order_col_expected`；join 測試擴充五情境參數化、時間類情境參數化（`Time`／`Timestamp`）、`test_duplicate_refdes_coords_keeps_first_row_xy`；phase1 對 time/ts 雙情境與 duplicate 之 volume 摘要測試。
- Scope: `tests/fixtures/golden/timestamp_alias_measurements/`、`duplicate_refdes_coords/`、`time_only_measurements/expected/manifest.json`、`tests/release_validation/test_join_conservation_golden.py`、`test_phase1_infrastructure.py`、`tests/fixtures/golden/README.md`、`docs/specs/release_validation_coverage.md`、`release_validation_gap_matrix.md`、`docs/decision-log.md`。
- Reason: 資料契約時間欄別名與 JoinEngine 座標去重契約（Pass 122）之 golden 覆蓋。
- Rollback: 刪除兩目錄與相關測試／manifest 鍵還原。

## 2026-04-05 Golden `time_only_measurements`（Time 主鍵）

- Decision: add `tests/fixtures/golden/time_only_measurements/`（無 BoardNo/PanelId，僅 `Time` + 與 normal 相同量測數值）；manifest `time_filter_probe`；擴充 `test_join_conservation_golden.py`（三情境參數化、`detect_order_col`==`Time`、時間區間篩選）；`test_phase1_infrastructure.py` 對 join 後 volume 摘要對齊 manifest。
- Scope: 上述與 `tests/fixtures/golden/README.md`、`docs/specs/release_validation_coverage.md`、`docs/specs/release_validation_gap_matrix.md`、`docs/decision-log.md`。
- Reason: 資料契約「BoardNo **或** Time」第二條路徑；SPC 排序以 `Time` 為準之釋義與測試。
- Risk: 無產品邏輯變更。
- Rollback: 刪除目錄與相關測試／文件列舉。

## 2026-04-05 Golden `panel_id_instead_of_board` + data contract tests（A）

- Decision: add `tests/fixtures/golden/panel_id_instead_of_board/`（`PanelId` 欄位、其餘同 normal 網格）；`tests/release_validation/test_data_contract_golden.py` 驗證 `data_contract.md` 最低欄位與「有 coords manifest 時 join 後具 X/Y」；`test_join_conservation_golden.py` 對 `normal_baseline`／`panel_id_instead_of_board` 參數化並新增 `filter_analysis_df` 之 PanelId 路徑；`normal_baseline` manifest 的 `engine_seed_params.parallel_coord` 註記；文件與 gap 矩陣更新（golden 6 目錄、A→Y）。
- Scope: 上述路徑與 `docs/specs/release_validation_coverage.md`、`docs/specs/release_validation_gap_matrix.md`、`tests/fixtures/golden/README.md`、`scripts/release_check.py`（plan_modules A）、`docs/decision-log.md`。
- Reason: 接續 roadmap：補 **A** 與 **12 類**中「Panel 別名」情境。
- Impact: `tests/release_validation` 測試數量略增；`release_check` 之 `golden_scenarios` 自動多一筆目錄名。
- Risk: 無行為變更；僅測試與 fixture。
- Rollback: 刪除 `panel_id_instead_of_board` 目錄與 `test_data_contract_golden.py`，還原 join 測試參數化與 manifest 片段。

## 2026-04-05 Release validation plan Steps 1–7 + 9–10（文件、L/G/H/I、report schema v3）

- Decision: add `docs/specs/release_validation_data_flow_and_tolerance.md`（Step 1）、`docs/specs/release_validation_gap_matrix.md`（Step 2）；golden manifests 補 `determinism`／`tolerance_overrides`／`performance_baseline_id`（normal_baseline）；`conftest` 的 `--golden-profile` 與 `dataset_version` fixture；測試 `test_dashboard_layers_alignment_golden.py`、`test_chart_transparency_golden.py`、`test_cache_state_release_golden.py`、`test_manifest_release_contract.py`、`test_step4_tolerance_policy_coverage.py`；`tests/helpers/perf_timing.py` 供 chart perf 與 P gate 共用；`release_check` 報告 schema **v3**（`git_commit`、`dataset_version`、`golden_scenarios`、`release_validation_plan_modules` 等）；微調 `performance_baselines.json` 以吸收分析／SPC 微秒級抖動。
- Scope: 上述新路徑與 `tests/release_validation/*`、`tests/test_chart_performance_baseline.py`、`scripts/release_check.py`、`tests/fixtures/golden/**/manifest.json`、`performance_baselines.json`、`docs/specs/release_validation_coverage.md`、`tests/fixtures/golden/README.md`、`README.md`／`project_architecture.md`／`final_audit_suite.md`／`decision-log.md`（若已同步）。
- Reason: 依發行驗證計畫 G 節順序補齊尚未落地項（含 H+I、L、G、Step 4/6 契約、Step 10 報告欄位）。
- Impact: `tests/release_validation` 測試數量增加；`release_report.json` 消費端若依 schema 解析需辨識 v3。
- Risk: P baseline 仍依主機漂移；極慢機器可能需再跑 `record_performance_baseline.py`。
- Rollback: 刪除新增測試／文件並還原 `release_check`、manifest、baseline。

## 2026-04-05 Performance regression gate (P) + `release_report` schema v2

- Decision: add `tests/fixtures/golden/performance_baselines.json`, `tests/release_validation/helpers/performance_gate.py`, `tests/release_validation/test_performance_regression.py`, and `scripts/record_performance_baseline.py`; extend `scripts/release_check.py` to schema v2 with `performance_baseline`, `performance_current`, `performance_status`, optional `final_audit_summary_path`, and env-driven `performance_gate_result.json`; raise `pytest_release_validation_pack` timeout to 2400s (PPTX on 100k is slow).
- Scope: `tests/fixtures/golden/performance_baselines.json`, `tests/fixtures/golden/README.md`, `tests/release_validation/helpers/performance_gate.py`, `tests/release_validation/test_performance_regression.py`, `scripts/record_performance_baseline.py`, `scripts/release_check.py`, `scripts/run_final_audit_suite.py`, `docs/specs/release_validation_coverage.md`, `docs/decision-log.md` (this entry).
- Reason: close the remaining release-validation plan items for end-to-end timing vs baseline (×1.2 wall, ×1.3 memory when RSS is available via optional psutil) and surface results in `release_report.json`.
- Impact: slower `tests/release_validation` (~30s+ on typical hardware); CI on slower hosts may need `python scripts/record_performance_baseline.py` or temporary `RELEASE_PERF_GATE=0` / `performance_gate.skip` (not for formal release).
- Risk: baseline is host-dependent; memory gate is skipped if `memory_peak_bytes` is absent from the current measurement (no psutil).
- Rollback: remove the listed new files and revert edits to `release_check.py`, `run_final_audit_suite.py`, and docs.

## 2026-04-05 Release validation coverage matrix + 2F `resolve_chart_payload` parity tests

- Decision: add `docs/specs/release_validation_coverage.md` (golden × tests × gate entrypoints) and `tests/release_validation/test_resolve_chart_payload_two_feature_golden.py` (Volume+Area computed payload: UI vs report resolver parity).
- Scope: `docs/specs/release_validation_coverage.md`, `docs/README.md`, `docs/specs/final_audit_suite.md`, `docs/specs/project_architecture.md`, `tests/fixtures/golden/README.md`, `tests/release_validation/test_resolve_chart_payload_two_feature_golden.py`, `docs/decision-log.md` (this entry).
- Reason: the prior release-validation plan left no single mapping doc; 2F parity was not explicitly covered while 1F and 3F were.
- Impact: contributors can see which fixture answers which risk; resolver regressions for dual-feature analysis are caught in the release pack.
- Risk: parity lists must be updated when new chart IDs require 2F-specific assertions.
- Rollback: delete the new test module and coverage spec; revert the listed doc edits.

## 2026-04-05 Release check script (`release_check.py` + `release_report.json`)

- Decision: add `scripts/release_check.py` to run `ruff check .`, `mypy app`, and `pytest -q tests/release_validation`, writing **`Outputs/release/release_report.json`** (machine-readable step results + output tails).
- Scope: `scripts/release_check.py`, `README.md`, `docs/specs/final_audit_suite.md`, `docs/specs/project_architecture.md`, `docs/decision-log.md` (this entry).
- Reason: release validation golden pack exists under `tests/release_validation` and is wired into `run_final_audit_suite.py`; teams need a lighter, JSON-friendly entry than the full final-audit timestamp folder.
- Impact: CI or local scripts can gate on `overall_ok` and per-step `return_code`; optional flags `--skip-ruff` / `--skip-mypy` / `--skip-pytest` for partial runs.
- Risk: duplicate overlap with final audit baseline gates; mitigated by documenting both roles (full audit vs release JSON snapshot).
- Rollback: remove the script and revert the listed doc edits.

## 2026-04-05 Chart/statistics documentation accuracy (architecture §6, chart audit, docs index)

- Decision: document the real split between `compute_analysis_payload`, `summary_engine`, `analysis_cards_engine`, `normality_engine`, shared analytics utils, `*_engine.py` modules, and `app/charts/*`; widen `chart_contract_audit.md` scope statement; add a chart/statistics file map table to `docs/README.md`.
- Scope: `docs/specs/project_architecture.md` (§5.3, §6, §11 revision row), `docs/reports/chart_contract_audit.md`, `docs/README.md`, `docs/decision-log.md` (this entry).
- Reason: prior wording implied all chart statistics lived only under `app/analytics/*_engine.py`, which omitted OOC/shift/drift/outlier card computations and summary/normality paths.
- Impact: readers can locate computation entrypoints without spelunking; audit doc explicitly lists ViewModel + non-suffix engines.
- Risk: none functional.
- Rollback: revert the listed Markdown edits.

## 2026-04-05 Documentation snapshot alignment (README, docs index, architecture, overview)

- Decision: refresh documentation snapshot dates and narrative so root `README.md`, `docs/README.md`, `docs/reference/platform_overview.md`, and `docs/specs/project_architecture.md` match the current mainline code and prior decisions (2026-04-03 through 2026-04-04); add a structured documentation map table under `docs/README.md`; correct the architecture revision-history row that still implied an active HTML export contract.
- Scope: `README.md`, `docs/README.md`, `docs/reference/platform_overview.md`, `docs/specs/project_architecture.md`, `docs/decision-log.md` (this entry).
- Reason: readers were pointed at multiple “current” dates (2026-04-02 vs 2026-04-03) and the §11 history line contradicted the PPTX-only convergence already recorded on 2026-04-03; tooling baseline from 2026-04-04 was not reflected in the architecture spec body.
- Impact: clearer navigation (including `platform_overview` in the docs index), explicit note that `CHART_UI_GROUPS_ORDER` is the primary chart UI grouping while `WORKFLOW_SECTION_*` remains a secondary registry dimension, and architecture §9 documents centralized `pyproject.toml` quality settings.
- Risk: none functional; future edits must bump snapshot dates when behavior changes.
- Rollback: revert the listed Markdown files to the prior revision.

## 2026-04-04 Tooling & Rules Baseline (pyproject, EditorConfig, Cursor rules)

- Decision: centralize Python lint/type/test configuration in root **`pyproject.toml`**; remove standalone **`ruff.toml`**; add **`.editorconfig`** and **`.gitattributes`** for cross-platform editor/Git consistency; extend **`.cursor/rules`** with always-on cross-platform baseline plus backend/frontend-scoped rules; align CI to install quality tools only via **`requirements.txt`** (ruff/mypy already listed in `docs/reference/requirements.txt`).
- Scope: `pyproject.toml`, `.editorconfig`, `.gitattributes`, `.cursor/rules/*.mdc`, `.cursor/rules/README.md`, `.github/workflows/pytest.yml`, `README.md`, `docs/specs/project_architecture.md`, `Outputs/industrial-data-setup-ui/`（`tsconfig` strict、`api.ts` FormData append、`api.contract.test.ts` Vitest environment、`App.tsx` ref typing）.
- Reason: official-style single source for Ruff/Mypy/pytest, fewer duplicate CI installs, and clearer Agent rules for Python vs React subproject workflows.
- Impact: `ruff` excludes generated/vendor trees via `extend-exclude`; mypy gains `explicit_package_bases` / `namespace_packages` and targeted `ignore_missing_imports` for Qt/chart third-party modules; frontend prototype runs TypeScript `strict` and MSW contract tests under **Node** environment to match native `fetch`/`FormData`.
- Risk: stricter TS may surface new errors in future edits; contract tests must keep `@vitest-environment node` when using MSW + multipart.
- Rollback: restore `ruff.toml`, delete `pyproject.toml` tool tables if needed, revert frontend strict/Vitest env changes.

## 2026-04-03 Master Data Persistence Migration (JSON Registry → SQLite)

- Decision: migrate product-level master-data persistence from file-based JSON registries to SQLite (`data/spc_master.db`) with versioned records and active-version semantics.
- Scope: `app/data/master_data_db.py`, `app/data/coordinate_registry.py`, `app/data/product_spec_registry.py`, `app/data/stencil_assignment_registry.py`, `README.md`, `docs/specs/project_architecture.md`.
- Reason: JSON files lacked transaction safety, version management, and durable query behavior for product coordinate/spec/stencil assignments under repeated edits.
- Impact:
  - Startup now performs one-time import of legacy registries (`coordinate_registry.json`, `product_spec_registry.json`, `stencil_assignments.json`) when DB tables are empty.
  - Coordinate/spec registries now store append-only versions and enforce one active version per product.
  - Existing registry public APIs remain compatible, so UI/service call-sites do not need interface changes.
- Risk: first-run migration may carry forward malformed legacy JSON values unless guarded by follow-up data review.
- Rollback: restore the three registry modules to file-backed JSON implementation and stop DB bootstrap/import in `master_data_db.py`.

## 2026-04-03 PPTX Chart Evidence Expansion (Engineering Template + Gallery Pages)

- Decision: expand engineering report template default chart set and add auto-generated `5A. Chart Evidence Gallery` slides (2x2 per page) to strengthen data-quality evidence in exported PPTX reports.
- Scope: `app/ui/pages/report_export_page.py`, `app/services/report_service.py`, `app/services/pptx_report_builder.py`, report builder tests, and report/architecture docs.
- Reason: existing PPTX export mostly presented narrative bullets with too few chart visuals, reducing confidence when explaining whether SPI measurement quality is good or bad.
- Impact:
  - Engineering template defaults now cover stability, distribution, anomaly, and localization evidence charts.
  - PPTX keeps core 12-section structure and appends evidence gallery pages only when selected charts are actually renderable.
  - Exported deck page count is now dynamic (`core + diagnostics + gallery`), while section numbering remains stable.
- Risk: deck length may increase when many charts are selected and renderable.
- Rollback: revert engineering template default chart list and remove chart-gallery rendering path from `pptx_report_builder.py`.

## 2026-04-03 Final Audit Suite Composition (Skills + MCP + Execution Plan)

- Decision: introduce a single final-audit orchestration entrypoint that composes baseline verification, SPC/statistical packs, chart/feature-cross packs, UI runtime checks, performance guard checks, Qt policy audit, and exception-policy scan into one reportable run.
- Scope: `scripts/run_final_audit_suite.py`, `docs/specs/final_audit_suite.md`, `docs/plans/final_audit_execution_plan.md`, `README.md`, `docs/specs/project_architecture.md`.
- Reason: project closeout quality needed a reproducible, skills-mapped and MCP-mapped audit pipeline instead of ad-hoc manual sequencing.
- Impact:
  - New executable command: `python scripts/run_final_audit_suite.py --repo-root . --profile full`.
  - Audit artifacts are now consolidated under `Outputs/final_audit/<timestamp>/` (`report.md`, `summary.json`, per-gate logs).
  - Statistical correctness, chart contract integrity, multi-feature interaction stability, UI runtime, and performance checks now share one closeout report.
  - Skill-to-phase and MCP-to-phase mapping is documented for remediation routing.
- Risk: full profile re-runs selected targeted packs after baseline `pytest -q`, so runtime is longer than baseline-only validation.
- Rollback: remove `run_final_audit_suite.py`, remove the new spec/plan docs, and revert README/architecture links if the team returns to baseline-only manual closeout.

## 2026-04-03 Multi-feature UX Convergence Phase A (Chart/Report Interaction Stability)

- Decision: implement explicit UI-local interaction contracts for Chart Analysis and Report Export without changing external analytics/report APIs.
- Scope: `app/ui/pages/chart_analysis_page.py`, `app/ui/pages/report_export_page.py`, feature/report interaction tests, and architecture/UI/data-contract docs.
- Reason: multi-feature switching still had hidden fallback behavior and report template re-apply ambiguity, reducing operator confidence in chart/report completeness.
- Impact:
  - Chart Analysis now has explicit state model (`active_features`, `selected_chart_ids`, `autoswitch_reason`, `render_status`) plus `1F/2F/3F` tab split and auto-switch trace message.
  - Chart cards now expose render status (`Ready/Incompatible/NoData/Error`) with reason text.
  - Report export：**2026-04-03** 曾加入 template apply mode／一鍵重設／覆蓋摘要；**2026-04-06** 起已收斂為 **engineering-only**（無上述 UI）；見本檔「Report export: engineering-only PPTX template」。
- Risk: autoswitch hint currently reflects the most recent auto-switch event and may persist until manual selector action.
- Rollback: revert the two page modules to prior selector/default-apply behavior and remove the added interaction-state tests.

## 2026-04-03 Report Export Contract Convergence (PPTX-only UI/service path)

- Decision: remove residual HTML export handlers from `ReportExportPage`, remove legacy HTML public export methods from `ReportService`, and align active UI/overview docs + sidebar tooltip to PPTX-only export path（歷史用語曾寫 template-driven；**2026-04-06** 起契約語意收斂為 **engineering-only**，見同日條目）。
- Scope: `app/ui/pages/report_export_page.py`, `app/services/report_service.py`, `app/ui/widgets/navigation_panel.py`, `docs/specs/ui_target_layout.md`, `docs/reference/platform_overview.md`.
- Reason: UI contract had already moved to PPTX-only template flow, but dead HTML export code paths and wording remained, creating implementation/documentation drift.
- Impact:
  - Report export page now contains only active PPTX export behavior.
  - `ReportService` public interface converges to PPTX export (`generate_pptx_report`) only（參數語意：**engineering-only**，見 2026-04-06 條目）。
  - Added contract regression coverage to lock PPTX-only service API surface.
  - Sidebar export tooltip and active layout/overview docs match runtime behavior.
  - Validation baseline remains green (`ruff`, `mypy app`, `pytest -q`).
- Risk: teams that relied on hidden/legacy HTML entrypoints from this page can no longer trigger them via UI code path.
- Rollback: restore `_export_to_html` / `_export_comprehensive` handlers in `ReportExportPage`, reintroduce `ReportService` HTML public methods, and revert the aligned tooltip/docs if HTML entry is reintroduced intentionally.

## 2026-04-03 SPC Engineering UI One-shot Refactor (Dashboard/Charts/Diagnosis/Report + Template Contracts)

- Decision: complete the engineering-oriented SPC UI refactor in one release pass, including `StatisticsPage` 3-layer dashboard (`Alarm > KPI > Info`), chart main-flow regrouping (`製程監控/分佈分析/關聯分析/異常分析` + `Advanced` retention), fixed six-section diagnosis layout, and PPTX export contract（歷史決策曾含 `management` / `engineering` 雙模板；**2026-04-06** 起僅 **engineering**，見同日條目）。
- Scope:
  - Analytics/contracts: `summary_engine`, `chart_registry`, `chart_analysis_viewmodel`, new engines (`xbar_r`, `anova_parttype`, `pattern_recognition`, analysis cards).
  - UI pages: `statistics_page`, `chart_analysis_page`, `diagnostic_page`, `report_export_page`.
  - Report pipeline: `report_service`, `pptx_report_builder`, `report_chart_lookup`, `report_diagnostics`.
  - Tests/docs: engine/contract/template tests + architecture/UI/data-contract docs.
- Reason: prior UI flow mixed legacy chart groups and non-engineering report paths, reducing decision speed for SPC troubleshooting; requirements demanded a dense engineering workflow with explicit status semantics and report-template consistency.
- Impact:
  - Dashboard metrics now come from `summary.process.dashboard_layers` (shared by UI/report).
  - Main-flow charts include `xbar_r`, `correlation_matrix`, `correlation_heatmap`, `anova_parttype`, `ooc/shift/drift/outlier`, `pattern_recognition`; legacy charts remain in `Advanced` (not removed).
  - Diagnosis cards enforce fixed six-section output and `UNKNOWN/VERIFY` for insufficient fields.
  - Report export UI once used a template selector + chart micro-adjust and only exposed PPTX（**2026-04-06** 起無模板選擇器，僅工程結構 + 勾選微調）。
  - Full validation baseline passed: `ruff`, `mypy app`, `pytest -q` (424 passed).
- Risk:
  - Template filtering can hide chart images for non-selected chart IDs; diagnostic narrative remains but reviewers must understand template scope.
  - New dashboard layer fields tighten payload expectations for downstream consumers that previously read legacy statistics layout directly.
- Rollback:
  - Restore previous statistics/diagnostic/report pages from pre-refactor versions.
  - Revert `chart_registry` ordering/grouping and disable new chart IDs in `CHART_ORDER`.
  - Revert `ReportService.generate_pptx_report()` template arguments to legacy export signature.

## 2026-04-03 Report HTML Numeric Coercion Hardening (match_rate / abnormal_rate)

- Decision: harden `_build_report_html()` numeric rendering by coercing `relation_meta.match_rate` and Pareto `abnormal_rate` through safe float conversion with deterministic fallback (`0.0`) instead of direct numeric formatting.
- Scope: `app/services/report_service.py`, `tests/test_report_service_pptx.py`.
- Reason: report rendering used direct format specifiers (`:.1f`, `:.2%`), which could raise runtime exceptions on malformed/legacy payload values and fail the whole export path.
- Impact:
  - HTML report generation no longer fails when these fields contain non-numeric values.
  - Output remains stable and explicit (`0.0%` / `0.00%`) for invalid numeric inputs.
  - Added regression test to lock this behavior.
- Risk: invalid upstream values are now normalized to `0.0`, which may hide data-quality issues if callers rely solely on the rendered text.
- Rollback: remove `_coerce_float` usage in `_build_report_html()` and restore direct numeric formatting for `match_rate` / `abnormal_rate`.

## 2026-04-03 Report Robustness Hardening (component focus counts + executive summary KPI coercion)

- Decision: extend report rendering numeric coercion to executive-summary KPI fields (`min_cpk`, `overall_yield_pct`) and component-focus matrix counts.
- Scope: `app/services/report_exec_summary.py`, `app/services/report_service.py`, `tests/test_report_exec_summary.py`, `tests/test_report_component_focus.py`.
- Reason: malformed or legacy payload values could trigger formatting/type conversion errors and break report generation in non-critical display sections.
- Impact:
  - Executive summary now renders non-numeric KPI fields as `—` instead of raising formatting errors.
  - Component-focus matrix now coerces non-numeric violation counts to `0`, preventing render-time crashes.
  - Added regression tests for both paths.
- Risk: coercing invalid counts to `0` may understate data-quality issues in the rendered matrix.
- Rollback: remove `_try_float` / `_coerce_int` paths and revert to strict formatting/conversion behavior in both modules.

## 2026-04-02 Data Setup High-DPI Layout Resilience (Content-First + Scroll Host)

- Decision: replace embedded `DataSetupPage` fixed `40/30/30` step-height stretch with a content-first vertical stack inside a dedicated step `QScrollArea`.
- Scope: `app/ui/pages/data_setup_page.py`, `tests/test_ui_geometry_stability.py`, UI architecture/spec docs.
- Reason: fixed-ratio compression caused text overlap and clipping under high-DPI / enlarged-font environments, violating UI readability requirements.
- Impact:
  - Step 1/2/3 cards now follow natural content height first, with vertical scrolling only when viewport height is insufficient.
  - Header/Footer chrome rows now enforce a size-hint-derived minimum height to avoid text overlap under high-DPI scaling.
  - Data Setup remains single-column and keeps existing readiness gate + step state semantics.
  - Geometry tests now enforce vertical order and no clipping (size-hint safe), instead of enforcing a hard 40/30/30 ratio.
- Risk: users may observe a vertical scrollbar in the step region on smaller windows or higher scaling factors.
- Rollback: restore ratio-based `_place_host(..., stretch)` placement and remove step-host `QScrollArea` in `DataSetupPage`, then revert updated geometry tests/docs.

## 2026-04-02 Data Setup Integration: Global Product Source + Readiness Gate

- Decision: integrate Data Setup page into a single product-driven configuration center by introducing one global product selector, step-level status dashboard, and footer readiness gate (`Start Analysis`) in the existing PySide6 workflow.
- Scope: `app/ui/pages/data_setup_page.py`, `app/ui/pages/coordinate_manager_page.py`, `app/ui/pages/data_upload_page.py`, `app/ui/widgets/stencil_spec_editor.py`, `app/ui/main_window.py`, UI specs.
- Reason: duplicated product selectors across step cards and distant status feedback caused state drift and extra clicks in engineer workflows; the refactor requirement explicitly demanded one product source and readiness gating.
- Impact:
  - Product selection is now centralized in Data Setup header and propagated to Step 1/2 embedded editors.
  - Step 1/3 now support drag-and-drop CSV input and show metadata (`filename/rows/timestamp`).
  - Step 2 thickness validation enforces `0.05~0.50 mm`; spec readiness is reflected in header status.
  - Footer `Start Analysis` becomes enabled only when `(product selected) && (coord exists) && (measure exists) && (thickness valid)`.
  - Main window now accepts `start_analysis_requested` from Data Setup footer and triggers immediate refresh analysis.
- Risk: centralized product-change reset may feel stricter for users who previously relied on carrying old step states across product switches.
- Rollback: restore embedded per-step product selectors and remove footer readiness/start-analysis integration, reverting DataSetupPage and child-page external-product APIs.

## 2026-04-02 Diagnostic Output Reasonability Convergence

- Decision: close remaining diagnostic-output reasonability gaps by refining severity policy, numeric formatting, and IPC mapping.
- Scope: `app/analytics/root_cause_engine.py`, `app/analytics/ipc_reference_library.py`, `app/ui/pages/diagnostic_page.py`, diagnostic/root-cause tests.
- Reason: owner review flagged four issues: extreme CUSUM drift still shown as warning, very small p-value displayed as zero, normality IPC shown as unknown, and overview label ambiguity for `正常`.
- Impact:
  - `cusum_trend_drift` now escalates to `error` when `ooc_ratio >= 50%` (otherwise remains warning).
  - `normality_test_fail` now preserves raw `p_value` precision in evidence payload.
  - Diagnostic formatter now renders tiny p-values with scientific notation (or `< 1e-6`) instead of `0`.
  - Overview text now uses `未觸發規則` to represent rule-level normal count semantics.
  - `normality_test_fail` now includes IPC references (`J-STD-001`, `IPC-9191`) instead of fallback unknown.
- Risk: CUSUM severity escalation can increase perceived risk level in downstream exports that consume root-cause severity directly.
- Rollback: revert the severity threshold logic in `root_cause_engine.py`, restore prior p-value rounding/display rules, and remove the added IPC mapping for `normality_test_fail`.

## 2026-04-02 Closeout Report Baseline Correction (Executable Reality Sync)

- Decision: correct `docs/reports/convergence_closeout_2026-04-02.md` validation snapshot to match current executable baseline (`python -m ruff check .`, `python -m mypy app`, `python -m pytest -q`) and remove stale `mypy not available` wording.
- Scope: `docs/reports/convergence_closeout_2026-04-02.md`.
- Reason: historical carry-over text in the report conflicted with the current repository validation contract and could mislead closure review.
- Impact: closeout report now reflects the same validation gates used in CI/local execution and the latest passing test count.
- Risk: low; documentation-only correction.
- Rollback: restore previous snapshot wording if a future governance policy intentionally tracks multiple validation tracks in the same section.

## 2026-04-02 Repository Baseline Completion (AGENTS/Env/Fixtures)

- Decision: complete repository bootstrap/governance baseline by adding repo-level domain guardrails (`AGENTS.md`), optional runtime env template (`.env.example`), and reproducible test anchor directories (`tests/fixtures`, `tests/golden`).
- Scope: `AGENTS.md`, `.env.example`, `tests/fixtures/README.md`, `tests/golden/README.md`, `README.md`, `docs/reports/convergence_closeout_2026-04-02.md`.
- Reason: convergence closeout still had missing baseline artifacts expected by repository governance standards.
- Impact: baseline onboarding and verification scaffolding are now explicit and discoverable from repository root and closeout report.
- Risk: template files may drift from runtime reality if environment knobs or test conventions evolve without updates.
- Rollback: remove the added baseline template files/directories if project policy later centralizes these artifacts outside the repository.

## 2026-04-02 Chart Render Blank-Image Detection Typing Fix

- Decision: replace Pillow `PixelAccess` per-pixel indexing in `_png_has_visual_content()` with NumPy array-based non-white pixel counting.
- Scope: `app/services/chart_render.py`.
- Reason: full-app mypy surfaced a typed-access incompatibility in `PixelAccess` indexing (`PixelAccess | None` and ambiguous tuple typing), which blocked convergence gate closure.
- Impact: blank-image detection logic remains equivalent while becoming type-stable and faster on large images.
- Risk: very unusual image mode conversions could affect threshold behavior; conversion is explicitly normalized to RGB before counting.
- Rollback: restore the previous nested loop over `rgb.load()` if NumPy-based counting causes unexpected edge-case regressions.

## 2026-04-02 Full Convergence Closeout Addendum (Active vs Historical Docs)

- Decision: finalize documentation convergence by separating active-contract specs from historical report snapshots, and verify repository markdown local-link health as a closure gate.
- Scope: `README.md`, `docs/specs/project_architecture.md`, `docs/specs/ui_target_layout.md`, `docs/reports/README.md`, `docs/reports/convergence_closeout_2026-04-02.md`, and selected report snapshot headers.
- Reason: convergence closure required preventing outdated report wording from being interpreted as current runtime contract while preserving historical audit evidence.
- Impact: active behavior guidance now consistently points to current specs/decision log, historical reports remain traceable with explicit snapshot context, and markdown local links are verified (`BROKEN_LINKS=0`).
- Risk: low; document-only governance refinement, no code-path behavior change.
- Rollback: remove snapshot notes and addendum docs if a future governance model chooses to rewrite historical reports in place.

## 2026-04-02 Documentation Convergence: Current Specs + Historical Snapshot Labels

- Decision: complete doc convergence by (1) updating active layout spec (`docs/specs/ui_target_layout.md`) to current architecture semantics, and (2) adding explicit historical-snapshot labels to legacy report documents instead of rewriting their original findings.
- Scope: `docs/specs/ui_target_layout.md`, `docs/README.md`, `docs/reports/README.md`, `docs/reports/IMPLEMENTATION_SUMMARY.md`, `docs/reports/TECHNICAL_VALIDATION_REPORT.md`, `docs/reports/ui_refactor_patch_summary.md`.
- Reason: several older documents still reflected superseded contracts and could be misread as current behavior; direct rewriting of old reports would weaken audit traceability.
- Impact: current-contract guidance is centralized in active specs/readme, while historical reports remain intact but clearly marked as time-scoped evidence.
- Risk: low; this is documentation-structure alignment and does not change runtime behavior.
- Rollback: remove snapshot labels and restore previous `ui_target_layout.md` wording if a different documentation governance model is adopted.

## 2026-04-02 Convergence Closeout: Governance Minimum Set Completion

- Decision: complete convergence-cycle documentation closure by adding missing governance artifacts (`code_review.md`, `docs/open-questions.md`) and publishing a 01~10 closeout report with validation snapshot.
- Scope: `code_review.md`, `docs/open-questions.md`, `docs/reports/convergence_closeout_2026-04-02.md`, `README.md`, `docs/README.md`.
- Reason: repository-level closeout still lacked explicit review rubric and open-question ledger expected by project governance minimum.
- Impact: review expectations, residual-risk tracking, and convergence completion evidence are now discoverable from root/docs entry points.
- Risk: if governance expectations evolve, these baseline templates may drift without periodic updates.
- Rollback: remove the added governance files and map links if project policy intentionally centralizes these artifacts elsewhere.

## 2026-04-02 Cpk CI Method Visibility: Dashboard + PPTX

- Decision: surface `defect.cpk_ci_method` in engineer-facing outputs with compact display text (`Bissell 95%`) to make CI convention visible without overflowing layouts.
- Scope: `app/ui/pages/statistics_page.py`, `app/services/pptx_report_builder.py`, and PPTX formatting tests.
- Reason: CI formula version was already locked in payload/spec, but output surfaces still showed only CI bounds and hid the method, reducing audit transparency.
- Impact:
  - Statistics dashboard now includes a `Cpk CI Method` row.
  - PPTX section-3 metric table now includes `Cpk CI Method`.
  - Long method strings are compacted to `Bissell 95%` for readability.
- Risk: report/table row density increases by one line; extreme slide crowding scenarios may require future layout tuning.
- Rollback: remove `defect.cpk_ci_method` row from dashboard/PPTX metric definitions and revert method-compaction formatting.

## 2026-04-02 Diagnostic Typography Consistency Tuning

- Decision: unify Diagnostic page typography to a stable three-tier hierarchy (title/body/caption), and raise diagnostic metadata text from `small` to `caption` for readability.
- Scope: `app/ui/theme/dark_stylesheet.py` (`diag*` style block only).
- Reason: owner requested better font consistency and font-size optimization in Process Diagnostics.
- Impact:
  - Diagnostic labels now explicitly use one shared font family declaration (`FONT_FAMILY`) across `diag*` selectors.
  - Status badge, update time, description, severity labels, key evidence, IPC/action metadata now align to caption scale.
  - Main issue line remains body scale + bold to preserve visual hierarchy.
- Risk: slightly larger metadata text increases vertical density and may show fewer lines in the same viewport.
- Rollback: restore the prior `diag*` font-size assignments (`FONT_SIZE_SMALL` / `FONT_SIZE_BODY` mix) in `dark_stylesheet.py`.

## 2026-04-02 Diagnostic Page Structured Format Alignment (Process Diagnostics Template)

- Decision: diagnostic page output is standardized to a fixed section format aligned with Process Diagnostics template, and clipboard summary now emits the same ASCII block structure.
- Scope: `app/ui/pages/diagnostic_page.py`, `tests/test_diagnostic_page_format.py`.
- Reason: owner requested a stable engineering-readable diagnostic format with explicit overview, key metrics, causes, grouped actions, chart links, and IPC references.
- Impact:
  - Diagnostic content now renders only `error` / `warning` hints; `info` hints are excluded from page cards and copied summary.
  - A single in-file rule formatting contract (`rule_id -> title/impact/key-data/cause/action-groups`) is used as the source for UI and clipboard text.
  - Process overview now uses `normal = total_rule_count - error_count - warning_count` (bounded at zero).
  - Unmapped or incomplete diagnostic fields now output `UNKNOWN (VERIFY)` instead of inferred text.
- Risk: users may perceive reduced detail because informational hints are hidden in this view.
- Rollback: restore the prior severity-section rendering and old `_copy_summary` formatter in `diagnostic_page.py`, and remove the new format regression tests.

## 2026-04-02 Cpk 95% CI Method Lock: Bissell (NIST/AIAG Convention)

- Decision: lock `Cpk 95% CI` computation to the Bissell approximation (two-sided 95%) and expose the applied method in summary payload (`defect.cpk_ci_method`).
- Scope: `app/analytics/summary_engine.py`, `docs/governance/SPC_RULES.md`, `docs/specs/data_contract.md`, and summary defect-metric tests.
- Reason: owner requested a strict, auditable formula version instead of an unlabeled approximation.
- Impact:
  - `defect.cpk_ci` remains `[lower, upper]` text (or `N/A`).
  - `defect.cpk_ci_method` now identifies the exact CI convention used.
  - SPC rules document now explicitly records the CI formula and boundary condition (`N < 2` -> `N/A`).
- Risk: historical outputs without `cpk_ci_method` metadata cannot be retroactively attributed to a named formula version.
- Rollback: remove `cpk_ci_method`, revert CI wording in specs/rules, and restore the previous unlabeled CI implementation.

## 2026-04-02 Statistics Dashboard Defect-Metric Consistency & CI Completion

- Decision: align summary-metric denominators so `N / Yield / PPM / DPMO` use the same inf-safe valid-sample base, implement `Cpk 95% CI` output, and correct Zbench wording to one-tail semantics.
- Scope: `app/analytics/summary_engine.py`, `tests/test_summary_engine_defect_metrics.py`, `docs/specs/data_contract.md`.
- Reason: dashboard values could become internally inconsistent under `±inf` input, DPMO opportunity definition caused board-count dominated inflation at feature level, and `Cpk 95% CI` remained permanently `N/A`.
- Impact:
  - Per-feature `n` and `yield_pct` now exclude `±inf` consistently with defect counters.
  - `DPMO(Feature)` now uses per-feature valid opportunities (`n_valid`), `DPMO(Combined-Event)` uses `n_complete_rows * feature_count`, and `DPMO(Combined-Board)` uses `board_n`.
  - `defect.cpk_ci` now emits a computed `[lower, upper]` interval when Cpk is available.
  - Summary relation calculations now sanitize `±inf` before correlation/ratio math.
- Risk: historical report baselines and threshold interpretations for DPMO may shift because denominator semantics are now opportunity-based instead of fixed `board_n * 3`.
- Rollback: restore the previous DPMO denominator rules and `cpk_ci=\"N/A\"` behavior in `summary_engine.py`, then revert the matching contract/tests.

## 2026-04-02 Full-Sample Integrity Remediation (No Partial Display/Test Sampling)

- Decision: remove automatic partial-sample behavior from core chart/statistical paths that were causing sample-count distortion in large uploaded datasets.
- Scope: `app/analytics/run_chart_engine.py`, `app/analytics/parallel_coord_engine.py`, `app/analytics/normality_engine.py`, and related regression/performance/sample-integrity tests.
- Reason: owner reported severe distortion where charts/statistical outputs reflected only a subset of samples, which is unacceptable for SPC engineering judgment.
- Impact:
  - `RunChartEngine` now always returns/displays full valid samples (`displayed_n == n`, `sampled_for_display=False`).
  - `ParallelCoordEngine` now uses full valid rows for rendering and normalization (no fixed 500-row display sampling).
  - `NormalityEngine` no longer samples 5000 rows for large datasets; for `N>5000` it runs full-data `D'Agostino K²` and reports full tested count.
  - `SpatialEngine` grid aggregation now discloses `n/displayed_n/sampled_for_display/sampling_method` metadata, and `HeatmapChart` adds an explicit on-chart aggregation cue.
  - `SpatialEngine` grid accumulator now uses zero-initialized sum buffers (instead of NaN) to prevent all-NaN aggregated values.
  - `RepeatedOffenderEngine` default output is now full offender ranking (no implicit `top_n=20` truncation); if caller passes `top_n`, truncation is explicitly disclosed via metadata and on-chart annotation.
  - Contract documents (`data_contract`, `chart_contract_audit`) are updated to encode "default full sample, explicit disclosure for any display compression/truncation" as a persistent rule.
- Risk: rendering and compute latency may increase on very large datasets; performance guardrail tests remain to detect pathological regressions.
- Rollback: restore prior downsampling/sampling branches in the three engines and revert corresponding tests if product direction later re-approves sampled display/testing with explicit owner approval.

## 2026-04-02 SPC Rules Terminology Alignment (Canonical vs UI Labels)

- Decision: add a terminology-mapping note to `docs/governance/SPC_RULES.md` clarifying that I-MR/Xbar-R/Xbar-S remain canonical statistical names, while current UI labels may differ (`imr`, `run_chart`, `subgroup`).
- Scope: `docs/governance/SPC_RULES.md` and this decision log entry.
- Reason: documentation and UI naming evolved over time, creating potential confusion between statistical taxonomy and product-facing labels.
- Impact: naming ambiguity is reduced without changing formulas, constants, thresholds, or chart computation behavior.
- Risk: low; this is a documentation clarification only.
- Rollback: remove the mapping subsection if a future unified naming policy makes the clarification redundant.

## 2026-04-02 Navigation Export Tooltip Contract Alignment (PPTX/HTML)

- Decision: update navigation step tooltip wording from `PDF / HTML` to `PPTX / HTML` to align UI copy with the current report export contract.
- Scope: `app/ui/widgets/navigation_panel.py` and this decision log entry.
- Reason: report export flow has already switched to PPTX as the default engineering artifact, while old tooltip wording still implied a PDF-first contract.
- Impact: sidebar guidance now matches the actual export actions provided by `ReportExportPage` (`另存為 PPTX`, `另存為 HTML`), reducing user-facing terminology drift.
- Risk: low; this is copy-only and does not alter navigation behavior or export implementation.
- Rollback: revert the tooltip string to the previous wording if product direction restores PDF as a primary export format.

## 2026-04-01 ReportService Split Phase H: Executive Summary Builder Extraction

- Decision: extract executive-summary HTML assembly from `report_service.py` into `app/services/report_exec_summary.py`, and keep `_build_executive_summary_html` in `report_service` as a compatibility wrapper.
- Scope: `app/services/report_exec_summary.py`, `app/services/report_service.py`, and new executive-summary regression tests.
- Reason: executive-summary generation is a cohesive presentation sub-domain and did not need to stay embedded in the central report coordinator.
- Impact: report-service orchestration surface is reduced while preserving existing output semantics and call sites.
- Risk: changes to risk badge wording or anchor conventions can drift if summary module updates are not reflected in consumer tests.
- Rollback: inline summary builder logic back into `report_service.py` and remove `report_exec_summary.py` if split causes regressions.

## 2026-04-01 CI Type Gate Expansion: Include ReportService Coordinator

- Decision: include `app/services/report_service.py` in staged CI `mypy` targets after contract-extraction phases reached a stable typed state.
- Scope: `.github/workflows/pytest.yml`.
- Reason: `report_service` remains a central orchestration file and should be continuously type-checked to prevent integration drift across extracted service components.
- Impact: CI now covers the coordinator plus extracted modules as one typed boundary.
- Risk: future edits in low-typed dependencies imported by `report_service` may increase gate noise.
- Rollback: temporarily remove `report_service.py` from staged mypy targets if CI throughput is impacted.

## 2026-04-01 ReportService Split Phase G: No-Chart Reason Resolver Extraction

- Decision: extract no-chart reason resolution (payload metadata probing + fallback policy) from `report_service.py` into `app/services/report_chart_reason.py`, keeping `_get_no_chart_reason` wrapper for compatibility.
- Scope: `app/services/report_chart_reason.py`, `app/services/report_service.py`, and new resolver regression tests.
- Reason: no-chart reason policy is a focused domain rule set that should be testable and maintainable independently from report assembly flow.
- Impact: chart-missing reason behavior remains equivalent while reducing logic concentration inside `report_service`.
- Risk: if chart registry `payload_key` semantics change, resolver behavior can drift without synchronized tests.
- Rollback: inline resolver logic back into `report_service.py` and remove `report_chart_reason.py` if modular split causes runtime regressions.

## 2026-04-01 Chart Draw Contract Alignment + CI Type Gate Expansion (Phase 2)

- Decision: enforce `BaseChart.draw_chart()` boolean contract across chart subclasses, add explicit return-contract regression test, and expand staged CI `mypy` gate to include chart modules and `report_diagnostics`.
- Scope: `app/charts/*_chart.py` (draw-chart return contract alignment), `tests/test_chart_draw_contract.py`, and `.github/workflows/pytest.yml`.
- Reason: type-gate expansion previously surfaced widespread return-type drift (`-> None` overrides) that could hide control-flow intent in chart rendering paths.
- Impact: chart draw entrypoints now have a consistent bool contract (`True` = canvas-ready draw path, `False` = placeholder/error/no-data path), and CI can continuously guard this boundary.
- Risk: some callers may still ignore the bool return value; contract consistency is enforced at type/test level but runtime adoption remains incremental.
- Rollback: revert chart `draw_chart` signatures/returns and narrow CI `mypy` scope if integration regressions appear.

## 2026-04-01 CI Type Gate Expansion For Extracted Service Modules (Task 10)

- Decision: expand the staged `mypy` CI gate to include newly extracted service modules (`analysis_context`, `analysis_orchestrator`, `report_context`, `report_risk`, `report_chart_lookup`, `report_actions`, `report_formatters`) in addition to the previous baseline core modules.
- Scope: `.github/workflows/pytest.yml`.
- Reason: architecture decomposition without matching type-gate coverage allows silent contract drift between wrappers, service boundaries, and callers.
- Impact: CI now validates a broader, still-manageable typed boundary focused on newly established service contracts without yet enabling full-repo mypy.
- Risk: gate can become noisy if downstream imports pull unstable modules into this staged boundary.
- Rollback: narrow the `mypy` target list back to the previous 3-module baseline if CI throughput is blocked.

## 2026-04-01 ReportService Split Phase F: Formatting Utilities Extraction (Task 09)

- Decision: extract report formatting helpers (PPTX evidence/IPC lines and HTML evidence/IPC snippets) from `report_service.py` into `app/services/report_formatters.py`, with `report_service` wrappers retained for compatibility.
- Scope: `app/services/report_formatters.py`, `app/services/report_service.py`, and new formatter regression tests.
- Reason: formatting concerns are stable utility logic and should be separated from orchestration code to reduce maintenance overhead and improve focused testability.
- Impact: formatting behavior is preserved while report assembly code is slimmer and easier to reason about.
- Risk: if output formatting contracts evolve in PPTX/HTML builder independently, wrappers can hide drift unless formatter tests are updated with those contracts.
- Rollback: move formatter implementations back into `report_service.py` and remove `report_formatters.py` if module split causes regressions.

## 2026-04-01 ReportService Split Phase E: Recommendation Policy Extraction (Task 08)

- Decision: extract PPTX recommendation policy (`rule_id` to failure-mode mapping and deduplicated action collection) from `report_service.py` into `app/services/report_actions.py`, preserving `report_service` wrapper compatibility.
- Scope: `app/services/report_actions.py`, `app/services/report_service.py`, and new action-policy regression tests.
- Reason: recommendation policy is domain logic and should not be embedded in report assembly flow, which increased file complexity and reduced focused test coverage.
- Impact: report action recommendation behavior remains the same, while policy maintenance and tests are isolated in a dedicated module.
- Risk: if failure-mode taxonomy IDs change, recommendation mapping can silently degrade unless mapping tests are kept in sync.
- Rollback: move mapping/collection logic back into `report_service.py` and remove `report_actions.py` if module layering causes regressions.

## 2026-04-01 ReportService Split Phase D: Chart Lookup Componentization (Task 07)

- Decision: extract chart-name normalization, alias mapping, chart-id resolution, and PPTX observable-chart title normalization from `report_service.py` into `app/services/report_chart_lookup.py`, while keeping backward-compatible wrapper functions in `report_service.py`.
- Scope: `app/services/report_chart_lookup.py`, `app/services/report_service.py`, and new lookup regression tests.
- Reason: this logic block was static-policy heavy and mixed with report assembly flow, increasing edit blast radius and making targeted unit testing harder.
- Impact: chart lookup policy now has a dedicated module with focused tests, and existing callers/tests that use `report_service` private helper names remain compatible through wrappers.
- Risk: if future chart registry metadata fields change, lookup behavior may diverge unless both `report_chart_lookup` tests and registry updates are maintained together.
- Rollback: inline lookup functions back into `report_service.py` and remove `report_chart_lookup.py` if cross-module import layering introduces regressions.

## 2026-04-01 ReportService Split Phase C: PPTX Context Builder Extraction

- Decision: extract PPTX `report_context` assembly from `report_service.py` into dedicated component `app/services/report_context.py`, and keep `ReportService.generate_pptx_report()` as orchestration-only path.
- Scope: `app/services/report_context.py`, `app/services/report_service.py`, and new context-focused regression tests.
- Reason: report-context assembly mixed filter snapshot, inferred metadata, and risk packaging inside one large method, increasing change risk and reducing testability.
- Impact: context construction is now isolated behind `build_pptx_report_context()`, enabling targeted tests while preserving the existing PPTX output contract.
- Risk: cross-module callback/contract drift can occur if context keys are changed in one module without syncing PPTX builder consumers.
- Rollback: inline `build_pptx_report_context()` logic back into `generate_pptx_report()` and remove `report_context.py` if integration regressions appear.

## 2026-04-01 Analysis Context Modeling (Task 05)

- Decision: introduce immutable analysis execution context (`AnalysisFilterContext`, `AnalysisRunContext`) as the canonical contract between preparation, background compute, and cache write-back paths; keep legacy `batch/refdes/part_type` fields in `AnalysisPreparation` for backward compatibility.
- Scope: `app/services/analysis_context.py`, `app/services/analysis_orchestrator.py`, `app/ui/main_window.py`, and orchestration regression tests.
- Reason: filter/spec state previously relied on mutable `SessionStore` fields during async completion, which can drift when users change filters while a worker is still running.
- Impact: UI now carries the exact run context produced at preflight time into payload stamping and cache persistence, reducing cache/context mismatch risk in concurrent refresh interactions.
- Risk: dual-path compatibility (context objects + legacy scalar fields) can drift if future edits update only one side.
- Rollback: revert `MainWindow` to store-based context lookup, remove `run_context` usage from orchestrator cache path, and keep only scalar context fields if runtime regressions appear.

## 2026-04-01 ReportService Split Phase B: Diagnostics Builder Componentization

- Decision: move PPTX diagnostics assembly flow into dedicated component `app/services/report_diagnostics.py`, with `report_service.py` keeping only a thin wrapper that injects existing helper callbacks.
- Scope: `app/services/report_diagnostics.py` and `_build_pptx_diagnostics` wrapper path in `app/services/report_service.py`.
- Reason: diagnostics assembly is a coherent sub-domain and was previously embedded as a large in-file routine in `report_service`, increasing coupling and edit risk.
- Impact: report diagnostics composition is now isolated in a reusable service-level component while preserving existing output behavior and compatibility with current tests.
- Risk: callback-contract drift between wrapper and component can break diagnostics assembly if function signatures change independently.
- Rollback: inline diagnostics builder back into `report_service.py` and remove `report_diagnostics.py` if integration issues surface.

## 2026-04-01 ReportService Split Phase A: Risk Domain Extraction

- Decision: extract report risk-classification logic into a dedicated domain module `app/services/report_risk.py` and keep `report_service.py` as orchestration/assembly entrypoint via thin adapter functions.
- Scope: `app/services/report_risk.py`, `app/services/report_service.py`, and new regression tests (`tests/test_report_risk.py`).
- Reason: `report_service.py` remains oversized and mixes domain policy with rendering/export flow; risk-policy logic is stable and independent enough to split first with low blast radius.
- Impact: severity normalization, risk-signal summarization, process-verdict normalization, and risk-level derivation now have a reusable single source outside report rendering paths.
- Risk: adapter and domain implementation can diverge if only one side is edited in future refactors.
- Rollback: inline `report_risk` functions back into `report_service.py` and remove module/test additions if import layering causes runtime issues.

## 2026-04-01 Analysis Orchestrator Extraction (Task 03)

- Decision: introduce `AnalysisOrchestrator` as the application-layer coordinator for analysis preflight (spec resolution, filter application, dataframe slicing, cache hit/miss decision, payload context binding, and cache persistence), and reduce `MainWindow` to UI-state + worker lifecycle orchestration.
- Scope: `app/services/analysis_orchestrator.py`, `app/ui/main_window.py`, and new orchestration regression tests (`tests/test_analysis_orchestrator.py`).
- Reason: analysis flow logic was previously embedded in UI code (`MainWindow._run_refresh_analysis` / `_on_analysis_result_ready`), creating high coupling and making architecture-level changes risky.
- Impact: analysis decision logic now has a single non-UI entry point, with behavior-equivalent statuses (`missing_feature`, `idle_no_data`, `error`, `cached`, `ready`) consumed by UI; cache key construction and payload context stamping are unified in orchestrator service.
- Risk: orchestrator/status mapping drift could cause UI message or state mismatches if future changes modify one side without updating the other.
- Rollback: revert `MainWindow` to inline preflight/cache logic and remove orchestrator service/test file if runtime regressions appear.

## 2026-04-01 CI Baseline: Enable Lint + Staged Type Gate + Tests

- Decision: GitHub Actions workflow now runs `ruff` lint, a staged `mypy` gate on core contract modules (`chart_registry`, `session_store`, `spec_resolver`), and then `pytest`.
- Scope: `.github/workflows/pytest.yml` and repository root dependency entrypoint (`requirements.txt`).
- Reason: CI previously referenced a missing root `requirements.txt`, and validation gate coverage only executed tests without lint/type checks.
- Impact: CI is now executable against the current repository layout and enforces a baseline quality gate sequence (`lint -> type -> test`).
- Assumption: full-repository mypy is provisional and deferred; current type gate intentionally scopes to stable core modules while existing legacy type debt is retired incrementally.
- Risk: type defects outside scoped modules can still bypass CI until the mypy scope expands.
- Rollback: revert workflow steps to test-only mode and remove staged mypy command if gate noise blocks delivery.

## 2026-04-01 Chart Base Return Contract + Data Setup No-Scroll Regression Fix

- Decision: `BaseChart.draw_chart()` now returns an explicit boolean (`True` when chart rendering can continue, `False` when invalid metadata triggers placeholder), and `DataSetupPage` embedded layout is restored to non-scroll full-page composition with fixed `40/30/30` section stretch.
- Scope: `app/charts/base_chart.py`, `app/ui/pages/data_setup_page.py`, and chart/layout regression tests.
- Reason: chart subclasses used `if not super().draw_chart(...)` but base method had no return value, causing silent early returns and blank charts; Data Setup embedded page still used full-page scroll and ratio drift, conflicting with UI layout contract and tests.
- Impact: chart rendering path is deterministic across all chart classes, and Data Setup embedded mode no longer introduces full-page scroll area while preserving target vertical ratio behavior.
- Risk: any downstream subclass that relied on implicit `None` truthiness from base draw path could behave differently (expected low risk because all subclasses follow the same guard pattern).
- Rollback: revert `BaseChart.draw_chart()` boolean contract and Data Setup layout host changes to prior implementation if unexpected UI behavior appears.

## 2026-04-01 Unified Report Risk Decision Logic (HTML + PPTX)

- Decision: risk-level scoring for report outputs now uses one shared rule in `report_service` that normalizes severity aliases, applies process-verdict floors, and then feeds PPTX section 10 through `report_context.risk_assessment`.
- Scope: `app/services/report_service.py`, `app/services/pptx_report_builder.py`, and report/PPTX regression tests.
- Reason: previous implementation could diverge between HTML and PPTX and could understate risk when `verdict=不可接受` but anomaly severity counts were low.
- Impact: both outputs now align on the same risk semantics (`HIGH/MEDIUM/LOW`), severity aliases (for example `HIGH`/`WARN`) are interpreted consistently, and PPTX section 10 text no longer claims SOD-style dimensions that were not actually used.
- Follow-up: comprehensive HTML executive summary now computes risk from the same diagnostics-oriented signal source as PPTX (with chart rendering disabled in risk-only mode), reducing multi-feature risk divergence between output formats.
- Follow-up: diagnostics entries now retain `priority`, diagnostics-based risk summarization now counts `high_priority_count`, and PPTX section-10 fallback (when `risk_assessment` is absent) now uses shared `report_risk` policy instead of local severity-only counting.
- Follow-up: PPTX section-10 risk block now explicitly shows `高優先級訊號` count so high-risk outcomes driven by priority escalation remain auditable to reviewers.
- Follow-up: simplified HTML export (`generate_report_with_charts`) now adds a shared-decision risk snapshot (`Risk Level / Process Verdict / Risk Signals`) generated from the same diagnostics-based scoring path used by other report outputs.
- Follow-up: introduced single-source `report_risk.build_risk_assessment()` and migrated PPTX context, simplified HTML snapshot, comprehensive HTML executive summary input, and PPTX fallback scoring to this shared risk snapshot contract.
- Risk: report consumers may observe risk-level changes on historical datasets where prior logic under-classified risk.
- Rollback: restore the old local risk counters in `pptx_report_builder` and revert `_compute_risk_level` to hint-only severity checks.

## 2026-04-01 Report Export Switches From TXT To PPTX

- Decision: the default engineering report export on the report page is now `PPTX` instead of plain `TXT`; deck layout is fixed to A4 landscape with slide 1 product/workorder/spec, slide 2 statistics summary, and slide 3+ anomaly-focused diagnostic recommendations plus related charts.
- Scope: `app/ui/pages/report_export_page.py`, `app/services/report_service.py`, `app/services/pptx_report_builder.py`, and report export regression tests.
- Reason: owner requested a presentation-grade engineering report that can be reviewed directly in PowerPoint, while keeping HTML available for full chart-matrix output.
- Impact: the report preview remains text-based inside the UI, but the primary downloadable report artifact becomes `.pptx`; selected diagnostic slides now emphasize concise Traditional Chinese engineering findings with retained English technical terms, PPTX diagnostic pages recompute from the current filtered dataset so slide 2 statistics and slide 3+ anomalies stay aligned, multi-feature exports still expand diagnostics per single feature instead of collapsing to an empty anomaly section, chart headers in PPTX use concise slide-oriented short names instead of verbose UI labels, the observable-chart references in PPTX are deduplicated to the same short-name vocabulary, diagnostic slides are ordered by severity so the highest-risk findings appear first, chart placeholders now state the concrete no-chart reason when one is known, and evidence ratio units are displayed by semantics (`%` for rate/share, `x` for variance ratio) to avoid misleading engineering interpretation.
- Risk: PowerPoint layout quality depends on `python-pptx` rendering and the length of diagnostic text; long hint text still needs regression coverage to avoid overflow.
- Rollback: reconnect the export button to the previous text-file save path and revert the PPTX-specific report assembly if a plain-text artifact is later reinstated as the primary export contract.

## 2026-04-01 PPTX Report Adopts 12-Section Framework (No Page Cap)

- Decision: PPTX report output now follows a fixed 12-section content framework, while allowing section 9 (Anomaly Diagnosis & Recommendation) to auto-expand to multiple pages based on anomaly count.
- Scope: `app/services/pptx_report_builder.py`, `app/services/report_service.py`, and PPTX export regression tests.
- Reason: owner required a stable report narrative structure for presentation while explicitly removing hard page-count limits.
- Impact: baseline deck now always includes sections 1~8 and 10~12; section 9 can generate one or more diagnostic pages so total page count is dynamic (`11 + anomaly_pages`).
- Risk: decks with many anomaly hints can become long; downstream consumers should rely on section titles instead of fixed slide index.
- Rollback: restore fixed-page assembly logic in `build_pptx_report()` and revert tests to fixed-index assumptions if a strict page cap is later reintroduced.

## 2026-04-01 PPTX Completeness Enrichment (Context + Data Quality + Defect Metrics)

- Decision: enrich PPTX sections with additional system-derived context so report completeness no longer depends solely on manually filled workorder fields.
- Scope: `app/services/report_service.py`, `app/services/pptx_report_builder.py`, and builder regression tests.
- Reason: owner requested complete report content; previous export omitted available data such as relation quality, filter scope, product spec profile, and defect-quality indicators.
- Impact: section 1 now includes missing-field completeness and coordinate-registry part-number fallback notes; section 2 includes product-spec profile (stencil type/thickness/update timestamp); section 3 includes `DPMO/Zbench/Cpk CI`; section 7 includes spatial join quality and spatial stats; section 8 includes relation coefficients and top abnormal components; section 10 includes combined DPMO risk evidence; section 12 includes filter scope and join-quality appendix lines.
- Follow-up: missing critical workorder fields are now rendered as `UNKNOWN (VERIFY)` (instead of ambiguous dash placeholders), and report context auto-infers single-value line/time scope from filtered data when explicit filters are absent.
- Risk: denser text can increase slide crowding for long values; existing line-truncation remains active and may hide tail text.
- Rollback: remove `report_context`/`analysis_payload` inputs from PPTX builder call path and revert section-level enrichment lines to the previous compact baseline.

## 2026-04-01 Data Setup Page Single-Page Vertical Layout

- Decision: `DataSetupPage` uses a fixed top-to-bottom single-page layout in embedded mode, with section height targets of `40% / 30% / 30%`.
- Scope: `app/ui/pages/data_setup_page.py`, embedded `CoordinateManagerPage`, `StencilSpecEditor`, `DataUploadPage`, and related UI tests.
- Reason: owner requested a simpler one-page flow with no step-title clutter and no full-page vertical scroll design.
- Impact: embedded data-setup UI no longer switches between 1/2/3-column tiers; visible step titles/descriptions are removed in embedded mode.
- Risk: if future data-setup content grows materially, the fixed-ratio layout may need a documented redesign instead of ad-hoc scroll restoration.
- Rollback: restore the previous tier-based layout logic in `DataSetupPage` and re-enable embedded step titles/descriptions in the three child widgets.

## 2026-04-01 PPTX Diagnostic Evidence Keyword Coloring

- Decision: diagnostic-slide evidence lines in PPTX are color-scored by key metrics/keywords (`Cpk/Cp`, `Yield`, `PPM`, `OOC Ratio`, `Variance Ratio`, `p-value`) while keeping default body text black.
- Scope: `app/services/pptx_report_builder.py` and new builder-focused regression tests.
- Reason: owner requested white-background black-text deck style with explicit color emphasis on key parameters and keywords.
- Impact: Slide 3+ evidence bullets now visually flag high-risk numeric signals (red/amber/green) without changing wording or data values.
- Risk: threshold-based color mapping is heuristic and may require domain tuning for future product lines.
- Rollback: remove evidence color resolver usage and fall back to uniform black evidence bullet text.

## 2026-04-01 PPTX Diagnostics Limited To Anomalies

- Decision: PPTX diagnostic slides now include only anomaly hints with `severity` in `error` or `warning`; `info`-only hints are excluded from slide generation.
- Scope: `app/services/report_service.py` diagnostic assembly and PPTX diagnostics regression tests.
- Reason: export contract defines slide 3+ as anomaly-oriented diagnosis, so informational hints should not inflate deck pages.
- Impact: if a batch only has informational hints, diagnostics list becomes empty and the deck falls back to the existing minimum-slide status page.
- Risk: users may lose low-priority context previously shown in PPTX; full context remains available in HTML.
- Rollback: remove severity filtering in `_build_pptx_diagnostics` to restore previous inclusion of `info` hints.
- Follow-up: diagnostic entries also normalize severity to lowercase and drop empty hint text, preventing badge mislabeling and low-signal blank-summary slides.
- Follow-up: no-anomaly fallback evidence lines are phrased as Traditional Chinese first, with concise English terms retained for engineering context.
- Follow-up: PPTX severity normalization now accepts alias labels (`HIGH`, `critical`, `medium`, `warn`) and priority fallback; non-list/non-dict hint payloads are skipped safely to avoid export-time breakage.
- Follow-up: when filtered data has no analyzable feature columns (`Volume/Area/Height` absent), PPTX export no longer reuses stale cached payload for diagnostics and falls back to the no-anomaly status slide.
- Follow-up: diagnostic evidence line `Is Normal: False/True` is now color-coded (`False` red, `True` green) so normality status is visually emphasized with other key parameters.
- Follow-up: Slide 2 metric table now renders `Yield (良率 %)` values with explicit `%` suffix and accepts numeric-like string inputs for metric formatting without crashing.
- Follow-up: `Yield` formatting now also normalizes ratio-style inputs (`0.9934`) into percent display (`99.34%`) for both KPI and metric table rendering.
- Follow-up: yield color thresholds now normalize ratio-style values (`0~1`) before grading so KPI text and KPI color remain consistent.
- Follow-up: sample count (`N`) formatting in PPTX now safely accepts numeric-like string inputs (for KPI and metric table) to avoid type-related render failures.
- Follow-up: chart export rendering now treats hidden-canvas/placeholder states as `no chart` (return `None`) instead of emitting blank PNGs, so PPTX diagnostics show explicit missing-chart reasons rather than empty chart content.
- Follow-up: chart export rendering now also validates PNG pixel content and rejects near-blank all-white images, preventing "image exists but chart has no visible content" artifacts in PPTX.

## 2026-04-01 Full Chart Sample-Integrity Audit

- Decision: when a chart is reported for sample-count distortion, the validation scope expands to every chart under `app/charts` plus chart-specific tabs that surface sampling/test counts.
- Scope: `app/charts/*`, `app/ui/tabs/normality_tab.py`, and regression tests covering silent truncation or undisclosed sampling.
- Reason: owner explicitly required a full-chart audit after boxplot evidence showed severe sample distortion.
- Impact: chart rendering may no longer truncate categories/groups for readability shortcuts; charts that still sample for performance must disclose displayed/tested counts.
- Risk: very dense charts can become visually crowded, so readability must rely on sparse labels/annotations instead of dropping data.
- Rollback: revert the affected chart rendering changes and remove the full-chart integrity regression tests if product direction later approves explicit sampling/truncation with a documented contract.

## 2026-04-01 Type Debt Burn-Down: Full `mypy app` Pass

- Decision: resolve remaining application-wide mypy errors by tightening Qt nullability guards (`layout()/takeAt()/item()`), removing side-effect list-comprehension patterns, and enforcing numeric typing in transfer-efficiency calculations.
- Scope: `app/ui/pages/statistics_page.py`, `app/ui/pages/data_management_page.py`, `app/ui/pages/workorder_page.py`, `app/ui/pages/diagnostic_page.py`, `app/ui/pages/component_select_page.py`, `app/ui/pages/data_setup_page.py`, `app/ui/pages/chart_analysis_page.py`, `app/services/import_service.py`, `app/analytics/transfer_efficiency_engine.py`.
- Reason: staged type gates were already green, but full-repo type debt still masked potential runtime null/typing defects in UI composition and analytics computation paths.
- Impact: `python -m mypy app` now passes for all application modules; data-loader empty-path behavior uses empty `DataFrame` placeholders instead of `None`; transfer-efficiency uses explicit numeric array conversion and typed IPC pitch/thickness table entries.
- Risk: empty `DataFrame` fallback can alter branches that previously depended on explicit `None` checks (expected low risk because existing branches already treat empty data as no-analysis path).
- Rollback: revert the above file set and restore prior `None` fallback/implicit typing behavior if downstream integrations require legacy contracts.

## 2026-04-01 CI Type Gate Upgrade: Scoped List → `mypy app`

- Decision: simplify CI type-check step from a manually maintained scoped file list to a single full-app command: `python -m mypy app`.
- Scope: `.github/workflows/pytest.yml`.
- Reason: the app now passes full mypy locally, so maintaining a long allowlist increases drift risk and can hide newly added untyped modules from CI.
- Impact: CI now enforces type safety across all `app/` modules by default, reducing regression escape paths.
- Risk: future untyped additions under `app/` will fail CI immediately and may require faster type-hygiene discipline in feature branches.
- Rollback: restore the previous scoped file list in workflow if emergency delivery requires temporary narrowing of gate scope.

## 2026-04-02 Import Pipeline Contract Tests + Doc Baseline Sync

- Decision: add focused regression tests for `DataLoaderWorker` empty-path and `batch_qty` behavior, and synchronize architecture/reference docs to the now-active full-app type gate (`python -m mypy app`).
- Scope: `tests/test_import_service.py`, `README.md`, `docs/specs/project_architecture.md`, `docs/reference/platform_overview.md`, `docs/reports/chart_contract_audit.md`.
- Reason: recent typing hardening changed import fallback semantics to empty `DataFrame`; contract-level tests were missing for this branch, and docs still contained outdated staged-mypy command examples.
- Impact: import pipeline behavior (empty input, unique-board count, row-count fallback) is now regression-protected; onboarding/architecture docs now match CI and local validation baseline.
- Risk: tests currently exercise `run()` synchronously (without thread scheduling), so race/timing behavior still relies on existing integration tests.
- Rollback: remove `tests/test_import_service.py` and revert the listed docs if the project intentionally returns to `None`-based loader fallback or staged type gate guidance.

## 2026-04-02 Normality Engine: Zero-Variance Shapiro Skip

- Decision: when input series has zero variance, `NormalityEngine.compute_normality()` skips Shapiro-Wilk execution and returns deterministic normality stats (`p_value=1.0`, `is_normal=True`) with explicit skip metadata.
- Scope: `app/analytics/normality_engine.py`, `tests/test_normality_engine.py`.
- Reason: SciPy emits repeat warnings for zero-range input (`shapiro: Input data has range zero`), creating noisy test output and non-actionable runtime warnings.
- Impact: zero-variance datasets no longer emit SciPy warnings during analysis/report generation; response contract now exposes `normality_test_skipped` and `shapiro_skip_reason` for traceability.
- Risk: downstream consumers that previously interpreted warning side-effects (instead of payload fields) will no longer observe those warnings.
- Rollback: remove the zero-variance pre-check and revert to direct Shapiro calls if strict parity with SciPy warning behavior is required.

## 2026-04-07 SMT SPI Data Setup Workflow Optimization & Control Limit Integration

- Decision: transform the data setup workflow into a product-centric automated system by integrating stencil specs and control limits (USL/LSL/Target for Volume, Area, Height) into the master database and enabling auto-sync between setup steps and the workorder sidebar.
- Scope: `app/data/master_data_db.py`, `app/data/product_spec_registry.py`, `app/ui/pages/data_setup_page.py`, `app/ui/widgets/stencil_spec_editor.py`, `app/ui/main_window.py`.
- Reason: direct product creation was missing from the setup flow, and control limits were managed ad-hoc in the workorder sidebar, leading to manual data entry errors and lack of persistence.
- Impact: selecting a product now auto-loads registered coordinates and full specifications; "New Product" button streamlines onboarding; sidebar specifications are automatically populated and set to read-only when a product is selected; database schema updated to store 3D control limits.
- Risk: existing databases require migration (handled via idempotent schema updates); tight coupling between product and spec may require more flexible "spec versioning" in the future.
- Rollback: revert database schema changes (manual column removal) and restore previous independent setup/workorder pages if ad-hoc limit management is still preferred.

## 2026-04-09 Measurement Library Adds Supplier Management Tab

- Decision: extend `MeasurementLibraryPage` with a fourth tab, `供應商管理`, backed by a new SQLite table `supplier_records` and dedicated data access module `app/data/supplier_library.py`.
- Scope: `app/ui/pages/measurement_library_page.py`, `app/data/master_data_db.py`, `app/data/supplier_library.py`, `app/ui/main_window.py`, README and regression tests.
- Reason: operator needs a managed supplier database in the same UI style/interaction pattern as existing measurement/coordinate/spec tabs, with fields `供應商編號/供應商名稱/鋼板編號/鋼板生產日期`.
- Impact: users can search/add/edit/delete supplier records from the library page; existing DBs auto-migrate idempotently to include `supplier_records`.
- Risk: `supplier_code + steel_plate_no` uniqueness may reject duplicate historical entries if operations expect non-unique combinations.
- Rollback: remove supplier tab UI wiring and revert `supplier_records` table/schema hook plus `supplier_library` usage.

## 2026-04-09 Data Setup Workorder Contract: Dual Workorder Fields

- Decision: replace the single workorder input with two explicit fields in `DataSetupPage`: `supplier_work_order_no` (供應商製令工單) and `outsource_work_order_no` (醫電製令工單), and remove direct batch-number input.
- Scope: `app/ui/pages/data_setup_page.py`, `app/ui/main_window.py`, `app/analytics/summary_engine.py`, `app/ui/pages/diagnostic_page.py`, `app/analytics/dashboard_layers_display.py`, report/export services, README/spec docs, and related regression tests.
- Reason: domain rule changed to treat batch number as equivalent to workorder identity; operators need two separate identifiers for supplier and outsourcing traceability.
- Impact: UI/diagnostic/report exports now display dual-workorder metadata; legacy consumers remain compatible because `work_order_no` and `batch_no` are auto-derived from the new workorder fields.
- Risk: legacy records containing only `work_order_no` may show an empty supplier workorder field until data is backfilled.
- Rollback: restore `batch_no` input in `DataSetupPage` and revert dual-workorder display/required-field checks in diagnostic/report modules.

## 2026-04-22 Workorder Legacy Sunset: 醫電命名與 `work_order_no` 清空

- Decision: rename all user-facing `outsource_work_order_no` labels from `委外製令工單` to `醫電製令工單` (compact UI label: `醫電工單`), remove manual `work_order_no` editing from measurement-library edit dialog, and enforce `work_order_no` as empty string on all write paths.
- Scope: `app/ui/pages/measurement_library_page.py`, `app/ui/pages/data_setup_page.py`, `app/ui/main_window.py`, `app/data/measurement_library.py`, `app/data/master_data_db.py`, diagnostics/report/export text surfaces, `scripts/backfill_workorder_dual_fields.py`, docs, and regression tests.
- Reason: domain contract now treats dual workorder fields as the only writable identifiers; `work_order_no` remains compatibility-only and must not carry runtime/business value.
- Impact: UI/diagnostic/report/export wording is unified to `醫電製令工單`; new/updated sessions persist `work_order_no=''`; startup runs a one-shot idempotent migration to clear historical `measurement_sessions.work_order_no`.
- Risk: legacy datasets that only depended on `work_order_no` lose that value after migration (by policy); downstream tooling must read `supplier_work_order_no` / `outsource_work_order_no`.
- Rollback: revert `WORK_ORDER_CLEAR_MIGRATION_KEY` hook and write-path forced-clear logic, then restore prior UI labels and edit fields.

## 2026-05-09 PPTX Report Evidence Scope and Coverage Contract

- Decision: strengthen engineering PPTX output from fixed narrative plus chart rendering into a traceable report contract with `data_scope`, `excluded_evidence`, `evidence_coverage`, `metric_definitions`, and per-diagnostic `evidence_type`.
- Scope: `app/services/report_context.py`, `app/services/report_service.py`, `app/services/report_diagnostics.py`, `app/services/pptx_report_builder.py`, `app/ui/pages/report_export_page.py`, README/spec docs, and report regression tests.
- Reason: owner required report credibility disclosure and specifically excluded coordinate/spatial evidence when current measurement data has no coordinate fields.
- Impact: PPTX now states used data sources, sample/features/filters, excluded spatial evidence, section trust status, evidence types, and a chart coverage table. Without valid `X/Y`, `spatial_heatmap` is marked `未納入：缺座標資料`; spatial slides do not output coordinate match rate, spatial point count, or heatmap as effective evidence.
- Risk: deck length increases by coverage-table pages, and downstream consumers should rely on section/title text rather than fixed slide indexes.
- Rollback: revert the report-context coverage additions, remove coverage slides and no-coordinate spatial gating from `pptx_report_builder.py`, and restore `ReportExportPage` chart availability to registry-only behavior.

## 2026-05-16 Full Documentation Sync Pass

- Decision: run a source-of-truth documentation sync over active root docs, `docs/**`, `.github` text, and test README contracts; update stale active claims and record the inventory in `docs/reports/document_sync_full_audit_2026-05-16.md`.
- Scope: documentation only: README/reference maps, report-module lists, workorder/report contract wording, active risk ledger status, broken relative links, and documentation inventory. No runtime code, SPC formulas, payloads, chart IDs, UI labels, or release-gate logic changed.
- Reason: active docs had drift from current evidence: `Watchlist #7` still described a release-blocking performance failure despite later PASS reports; governance text still referenced PDF report generation; some relative links resolved incorrectly from `docs/`; report service split lists were incomplete.
- Impact: active documentation now points to current code/config evidence and the active risk ledger reflects the latest available release-validation evidence while keeping `Watchlist #7` monitored.
- Risk: historical snapshot docs under `docs/reports/`, `archive/**`, and generated `Outputs/**` may still contain superseded wording by design; use current README/specs/decision-log for live contracts.
- Rollback: revert this documentation-only change set and remove `docs/reports/document_sync_full_audit_2026-05-16.md` if a later audit finds the source evidence was misread.

## 2026-05-25 Active Documentation Sync After Shell / Font Contract Updates

- Decision: run a documentation-only sync over active README/reference/spec/governance docs and refresh the inventory in `docs/reports/document_sync_full_audit_2026-05-25.md`.
- Scope: active documentation and inventory pointers only: current architecture date, left-sidebar workflow wording, hidden `QTabWidget#workflowTabs` wording, bundled Noto Sans TC runtime guidance, and `DiagnosticPage` 製程統計分析輸出 terminology. No runtime code, SPC formulas, payloads, chart IDs, UI labels, data schema, or release-gate logic changed.
- Reason: active docs still carried post-2026-05-16 drift: the overview/layout target described older right-side top workflow tabs, governance said the repo did not ship font files despite `app/assets/fonts/NotoSansTC-VF.ttf`, and the latest sync pointers did not include the 2026-05-24 architecture/performance snapshot.
- Impact: onboarding and agent-facing docs now point to the same shell, font, and DiagnosticPage contracts as `app/ui/main_window.py`, `app/ui/workflow_labels.py`, `app/bootstrap/font_runtime.py`, and `docs/specs/project_architecture.md`.
- Risk: historical reports and archived materials may still contain superseded terminology by design; use root README, active specs, and this decision log for live contracts.
- Rollback: revert the documentation-only files changed in this pass and remove `docs/reports/document_sync_full_audit_2026-05-25.md` if a later audit finds the source evidence was misread.
