# 工程規格維護與對齊（Spec Maintenance & Alignment）

本文件為 **跨計畫、跨迭代** 的規格治理準則，補充 `docs/governance/AGENTS.md`、`docs/governance/SPC_RULES.md`、UI／資料契約與圖表契約。目標是避免「計畫／設計書與程式長期脫節」以及「基礎標準化（token、合併規則、語意）各自發明」。  
**問題解決與變更的操作順序**（根因、橫向影響、驗證、再發防止）見 **`docs/specs/issue_resolution_workflow.md`**（整合入口，與本文件互補）。

**權威順序（衝突時）**  
1. 已合併之主分支 **可驗證行為**（程式路徑、測試、執行結果）  
2. **`docs/governance/SPC_RULES.md`**（統計公式、常數、解讀門檻）  
3. **本 repo 之明示規格**（`docs/specs/ui_design_spec.md`、`docs/specs/data_contract.md`、`docs/specs/ui_state_semantics.md`、`docs/reports/chart_contract_audit.md` 等）  
4. **迭代計畫**（例如 `.cursor/plans/*.md`）— 計畫 **不得** 凌駕於 1–3；若計畫宣稱已落地而程式無證據，必須 **更新計畫或標示歸檔**，而非假設程式錯。

---

## 1. 何時必須更新規格（觸發條件）

| 觸發 | 應更新的文件（至少） |
|------|----------------------|
| 非顯而易見之 bug、跨模組／使用者可見行為變更 | 依 **`docs/specs/issue_resolution_workflow.md`** 走完整閘門；PR／計畫附 **§4 檢查清單**；規格觸發列於下表 |
| 持久化／架構變更（例如 JSON ↔ DB） | 架構說明、`docs/specs/data_contract.md` 或專用持久化規格、相關計畫歸檔 |
| 版面／流程與文件描述不一致（scroll 區塊、欄位順序、步驟標題） | `docs/specs/ui_design_spec.md`、`docs/specs/ui_target_layout.md`（若有）、對應計畫 `needs-update` |
| 新增或修改 **驗收條件**（「無整頁捲軸」、斷點、DPI%） | `docs/specs/ui_design_spec.md` §3、`docs/reports/ui_self_verification_report.md` 類驗收附錄（並對照 **本文件 §3**） |
| 顏色／字級／間距／狀態語意變更 | `tokens.py` / `dark_stylesheet` 為實作單一來源；**規格**須在 `docs/specs/ui_design_spec.md` 或 `docs/specs/ui_state_semantics.md` 註明原則與禁止事項 |
| 全域 QSS 之 `font-weight`（尤其 500/600）、`FONT_FAMILY`、內嵌字型（含 Matplotlib CJK 字型優先序） | 須符合 `docs/governance/AGENTS.md` §4 與本文件 **§4.1 有效性驗證**；更新 `tests/test_ui_font_caps.py` 基線（若凍結數下降），並維持 `tests/test_mpl_font_config.py` / `tests/test_chart_glyph_rendering.py` / `tests/test_chart_label_glyph_safety.py` 通過 |
| 欄位映射、payload、圖表 slice/merge 規則變更 | `docs/specs/data_contract.md`、`chart_registry`／helper 註解、`docs/reports/chart_contract_audit.md` |
| 統計門檻、最小樣本、分類規則、fallback 可見性 | **`docs/governance/SPC_RULES.md` 先於程式**（見 `docs/governance/AGENTS.md`） |
| 同一 UI 開關在不同圖表有不同數學定義 | 拆開關或拆命名；規格表列「開關 × 圖表 × 公式 × 圖例文案」 |
| 更動 `objectName`、`state`、`class`（QSS／測試依賴） | `docs/specs/ui_state_semantics.md`、對照表、`dark_stylesheet.py` |
| 計畫檔明顯過期 | `docs/plans/document_alignment_patch_plan.md` 歸檔策略、`[ARCHIVED]`／`needs-update` 標註 |

---

## 2. 計畫檔生命週期（與 `docs/plans/document_alignment_patch_plan.md`／`docs/reports/document_alignment_report.md` 一致）

- **ok**：敘述與目前程式可對照，或有關鍵字掃描證據。  
- **needs-update**：目標仍有效，但敘述與實作不符；應補「目前狀態（程式證據）」「與原計畫差異」「擇一更新方案」。  
- **ARCHIVED**：計畫前提（架構／大改版）已廢棄；保留原文並加「目前狀態」「對應程式路徑」「新建議方向（若仍要做）」。

**禁止**：計畫中宣稱「已採用某技術／已移除某 UI」而主分支無對應實作，卻不更新計畫或標記狀態。

---

## 3. UI／響應式驗收（可觀測條件）

下列類型需求 **不可** 僅以口語寫在計畫內；須在 UI 規格或驗收文件中寫清 **量測方式**：

- 「某解析度下不需整頁捲軸」「一頁式」：須定義 **視窗大小、OS 縮放百分比、何謂整頁捲軸**（哪個容器可捲、哪個不可）。  
- 「響應式／卡片化」：須定義 **斷點、欄數、最小內容寬**（與 `tokens` 中 breakpoint 對齊）。  
- **DPI**：主要頁面在 100%／125%／150%（與 `projectplan`／自我驗收一致）下的可讀性與裁切檢查。

目標可階段性調整（例如先「降低整頁捲動」再追求「特定環境無整頁捲軸」），但 **調整後須回寫規格**，避免新舊承諾並存。

---

## 4. 設計系統（Design tokens）與程式標準化

- **單一來源**：`app/ui/theme/tokens.py` + `app/ui/theme/dark_stylesheet.py`（細則見 `docs/governance/AGENTS.md` §4）。  
- **規格文件職責**：說明 **原則**（不可頁面硬編色碼、字級由 QSS 驅動），不必重複每個 token 數值；數值以 repo 為準。  
- **新增語意狀態**：必須同步 `docs/specs/ui_state_semantics.md` 與 QSS；若影響無障礙或測試選擇器，須註明。

### 4.1 CJK／字型政策之有效性驗證（三層）

預防「合成半粗體導致中文顯示碎裂」等問題，**僅寫規則不夠**；須在下列三層至少可追溯到證據（與 `docs/governance/AGENTS.md` §4 對齊）。

| 層級 | 驗什麼 | 本 repo 做法 |
|------|--------|----------------|
| **1. 規則守門（Rule compliance）** | 未經審批新增高風險字型規則（QSS 字重 / 圖表 glyph） | `pytest`：`tests/test_ui_font_caps.py` 對 `get_dark_stylesheet()` 產出內 **`font-weight: 500` / `600`** 維持 **零基線**；`tests/test_mpl_font_config.py` 確認 CJK 字型優先於 `DejaVu Sans`；`tests/test_chart_label_glyph_safety.py` 防止高風險 glyph token（`μ₀`/`MR̄`/`✓✗` 等）回流。 |
| **2. 渲染結果（Outcome）** | 變更後畫面可讀性優於或等於變更前 | **Windows** 上，針對該變更所涉頁面，在 **至少兩種** OS 顯示縮放（建議自 {100%, 125%, 150%} 中取）**目視**標題與內文；含至少一句 **CJK** 頁面標題與一塊內文。另以 `tests/test_chart_glyph_rendering.py` 驗證常見中英混排圖表文字不出現 `Glyph ... missing` 警告。重大調整建議附 **前後對照**（截圖或簡短錄影）寫入 PR／計畫附註。 |
| **3. 環境代表性（Environment coverage）** | 問題不是單一機器特例 | PR 或交付說明記錄：**OS 版本**、是否 **多螢幕**、是否 **遠端桌面**；若能與 `SPC_UI_DIAGNOSTICS=1` 啟動診斷（DPR、DPI）併記更好。 |

**觸發**（須跑通 1+2+3 的最低組合）：合併前 **任何** 針對 `dark_stylesheet.py` 的 `font-weight`／`FONT_FAMILY` 變更、或內嵌／載入字型之變更。  

**例外**：純英文／報表 HTML 等非 Qt 全域 QSS 路徑，可不套用第 1 層凍結，但仍建議在該模組自有測試或人工驗收中註明。

---

## 5. 資料與圖表契約（避免雙軌邏輯）

- **Payload 切片／合併**：同一語意只允許 **一處** 權威實作（registry／helper）；UI 與報表 **禁止** 平行複製 merge 規則（見 `docs/governance/AGENTS.md` §7）。  
- **解析入口治理**：圖表 payload 解析應收斂到單一函式入口（例如 `resolve_chart_payload`）；新增圖表或 3F 路徑時，需同步驗證 UI/報表 parity。  
- **診斷組合矩陣治理**：製程診斷的跨圖表候選、可用性與關聯判讀收斂於 `app/services/diagnostic_evidence_matrix.py`；UI、Excel、PPTX 僅讀取其輸出，不得各自重建 feature/chart/filter/display 組合邏輯。  
- **資料契約**（必填欄位、別名、關聯鍵）以 `docs/specs/data_contract.md` 為準；Loader／Store 行為變更須更新該文件。  
- **圖表契約與稽核**：`docs/reports/chart_contract_audit.md` 記載引擎／敘述／風險；高風險修正須 **先** 釐清規格與使用者可見訊息，再改程式。  
- **單位與 fallback**：規格線、控制限、資料欄位單位不一致時，圖例／註解須可解釋；統計 fallback 須 **可見**（metadata／圖上註記），見 `docs/governance/AGENTS.md` §7。
- **抽樣與正規化透明度**：對 display downsampling 或 sampled test（如 normality），需以結構化 metadata 輸出（`n/displayed_n/...`、`tested_n/total_n/...`），不得只靠字串文案。

---

## 6. 領域規則（SPC／能力指標）

- 公式與常數：**僅** `docs/governance/SPC_RULES.md`（不可在程式中重定義）。  
- 任何 **門檻、最小樣本、解讀分類** 變更：**先** 更新 `docs/governance/SPC_RULES.md` 或專用附錄，**再** 改程式與測試。

---

## 7. 與其他文件對照

| 文件 | 角色 |
|------|------|
| `docs/governance/AGENTS.md` | Agent／審查強制規則（含圖表完整性、PySide 安全）；§4 含 CJK 字重與有效性驗證要點 |
| **`docs/specs/issue_resolution_workflow.md`** | **問題解決與變更之整合入口**（步驟與閘門、L1/L2、8D 對照、PR 檢查清單） |
| **`docs/specs/ai_agent_response_template.md`** | AI／人類共用之 **結構化回覆範本**（與工作流 §4 對齊） |
| **`.cursor/rules/README.md`** | **與官方文件對照索引**（規則四類、`Team→Project→User` 優先順序、FAQ：Tab／Inline／Agent、`docs/governance/AGENTS.md` 與 `.cursorrules` 遺留）— [cursor.com/docs/context/rules](https://cursor.com/docs/context/rules) |
| **`.cursor/rules/agent-residence-minimal.mdc`** | Cursor **極簡閘門**；預設 **Apply Intelligently**（`alwaysApply: false` + `description`）；細則見上列 README 與 [Cursor Rules](https://cursor.com/docs/context/rules) |
| **`.github/pull_request_template.md`** | GitHub PR **預設勾選表**（L1/L2 與驗證） |
| **`.github/workflows/pytest.yml`** | **機器驗證**：CI 跑 `pytest -q` |
| `docs/reports/cjk_typography_remediation_report.md` | CJK 字重修復批次報告（修復內容、測試證據、視覺驗證矩陣） |
| `docs/specs/workflow_governance_monthly_checklist.md` | 流程治理月度稽核（規則對齊、L2 品質、Blast、回歸守門） |
| **本文件 §4.1** | CJK／全域 QSS 字型政策之 **有效性驗證（三層）**：規則守門、渲染結果、環境代表性 |
| `docs/specs/ui_design_spec.md` | UI 架構與互動；§22 規格維護要點 |
| `docs/specs/data_contract.md` | 輸入資料與關聯；§11 契約對齊 |
| `docs/specs/ui_state_semantics.md` | 狀態與 token 語意；變更對照 |
| `docs/reports/chart_contract_audit.md` | 圖表／引擎／敘述風險清單 |
| `docs/reports/document_alignment_report.md` | 計畫 vs 程式對齊稽核紀錄 |
| `docs/plans/document_alignment_patch_plan.md` | 計畫檔 patch／歸檔指南 |
| `docs/plans/ai_change_and_planning_discipline.md` | 計畫 Preflight、根因分析、爆炸半徑；預防假設性跨改 |
| `.cursor/plans/README.md` | 計畫檔範本與必填章節 |
| `docs/governance/SPC_RULES.md` | 統計單一來源 |

---

## 8. AI 變更紀律（與計畫擬定）

避免「依假設改 A 卻漏改 B」「未找根因即下對策」「計畫前置不足」等問題，完整規則見 **`docs/plans/ai_change_and_planning_discipline.md`**；`docs/governance/AGENTS.md` §13 為執行摘要。

---

## 9. 修訂紀錄

| 日期 | 摘要 |
|------|------|
| 2026-04-21 | 新增 Matplotlib CJK 字型守門要求：內嵌字型變更需同步通過 `test_mpl_font_config` / `test_chart_glyph_rendering` / `test_chart_label_glyph_safety`，並維持 CJK 優先於 `DejaVu Sans`。 |
| 2026-03-26 | 初版：彙整計畫對齊報告與跨文件治理事項，作為規格必更新之單一索引。 |
| 2026-03-26 | 新增 §8 與 `docs/plans/ai_change_and_planning_discipline.md`、`.cursor/plans/README.md` 對照。 |
| 2026-03-26 | 新增 §4.1（CJK／字型政策三層有效性驗證）與 §1 觸發列；對應 `docs/governance/AGENTS.md` §4 與 `test_ui_font_caps.py` 字重凍結。 |
| 2026-03-26 | 新增 **`docs/specs/issue_resolution_workflow.md`** 為問題解決整合入口；**§1**、**§7** 與 `docs/governance/AGENTS.md` §11、§12 對應更新。 |
| 2026-03-26 | 增列 **`docs/specs/ai_agent_response_template.md`**、**`.cursor/rules/agent-residence-minimal.mdc`**、**`.github/pull_request_template.md`**、**`.github/workflows/pytest.yml`**（§7 對照）。 |
| 2026-03-26 | **`.cursor/rules/README.md`**：依 [Cursor Rules](https://cursor.com/docs/context/rules) 說明四種套用方式；`agent-residence-minimal.mdc` 改為 **`alwaysApply: false`** + 強化 `description`（Intelligent）；§7 對照更新。 |
| 2026-03-26 | **深度對齊官方**：§7 增列 **`.cursor/rules/README.md`** 為對照索引；README 補 **優先順序**、**FAQ（Tab／Agent）**、**`docs/governance/AGENTS.md`／`.cursorrules`** 與 **Intelligent 須有 description**（見 Context7／cursor.com 文件）。 |
| 2026-03-26 | 文件對齊修正：不存在的 `.cursor/*/platform_overview.md` 路徑已統一更正為 `.cursor/rules/README.md` 與 `.cursor/plans/README.md`。 |
| 2026-03-26 | 完成 CJK 第一批字重修復：`dark_stylesheet.py` 移除 `500/600`，`test_ui_font_caps.py` 基線更新為 0/0，新增 `docs/reports/cjk_typography_remediation_report.md`。 |
| 2026-03-26 | 新增 `docs/specs/workflow_governance_monthly_checklist.md`，制度化月度流程治理與橫向檢查。 |
