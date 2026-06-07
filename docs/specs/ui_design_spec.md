# SPI 製程統計分析
## UI Design Specification (Current)

# 1. UI 設計目標

本系統 UI 需符合工程分析軟體特性：
- 清晰資料呈現
- 高密度資訊顯示
- 穩定操作流程
- 可處理大數據量
- DPI-aware 支援

主要用途：
- SPI 製程數據分析
- SPC 統計監控
- PCB 空間異常分析
- 工程報告產生（PPTX-only，`engineering`）

# 2. UI 整體架構

系統採左側流程導覽兩欄式工作界面：左欄為流程切換、全域篩選、特徵快捷與固定動作，右欄為內容工作區（`QTabWidget#workflowTabs` 仍作內部容器，但隱藏 tab bar）。

```text
+------------------------------------------+
| Left: Workflow / Filters / Actions | Workspace Content |
+------------------------------------------+
```

左欄（`CollapsibleSidebar`）內含：
- `NavigationPanel` 可見流程導覽（6 個 workflow buttons）
- 分析條件（Control Panel）
- 特徵快捷（高度 / 面積 / 體積）
- 全域動作按鈕（下一步 / 重新分析）

可尋性限制：左欄不是萬用工具箱。表單內按鈕（如選檔、儲存、管理規格）與資料表列操作（如編輯、刪除、設為現用版次）必須留在內容區的作用範圍旁，避免使用者在側欄失去操作脈絡。

# 3. 主視窗 (Main Window)

### 類型
```text
QMainWindow
```

### 入口
```text
main.py -> app.ui.main_window.run_app()
```

### 結構
```text
MainWindow
 ├─ CollapsibleSidebar (NavigationPanel + ControlPanel + actions，可收合)
 └─ Workspace (QTabWidget#workflowTabs，tab bar 隱藏)
```

### 視窗尺寸與幾何還原
- 初次開啟使用目前螢幕 `availableGeometry()` 的 90-95% 安全比例置中；現行主視窗預設為 `0.93`，優先對齊 `1280x752` 可用區域並避免被工作列或多螢幕邊界遮住。
- 儲存的 `QSettings` 幾何只在目前螢幕可見、尺寸未超出可用工作區時保留；離屏或過大的舊幾何會重設為安全尺寸。
- `app/ui/theme/layout_policy.py` 是主視窗文字輸入 policy、`resize_and_center_in_available(...)`、`fit_top_level_to_available(...)` 與視窗可見範圍 clamp 的共用位置；主視窗、解讀視窗、匯出確認與資料庫編輯對話框需走相同可見區 fitting 規則。

### 可見流程分頁（現行）
- 資料設定（DataSetup）：整合座標、工單、量測匯入
- 資料庫（MeasurementLibrary）：SQLite 歷史庫
- 統計圖表（ChartAnalysis）：管制圖分析
- 診斷（Diagnostic）：製程統計分析報告輸出
- 報告匯出（ReportExport）：PPTX 報告
- 說明（DataManagement）：說明與參考

### 內部頁面
- 量測（ComponentSelect）：元件與特徵選定；不進入可見流程導覽，仍由圖表頁快捷與相容 `_go_to_page(1)` 流程進入。

詳見 `docs/specs/project_architecture.md` §4 與 `app/ui/main_window.py` 之 `STACK_ORDER`／`VISIBLE_WORKFLOW_TABS`。

# 4. Navigation Panel

可見流程導航由左側 `NavigationPanel` 承載：
- `資料設定`
- `資料庫`
- `統計圖表`
- `診斷`
- `報告匯出`
- `說明`

行為：
- 單選模式
- active item highlight
- 導覽切換透過 `NAV_TO_STACK = [0, 6, 2, 5, 3, 4]` 對應 legacy stack index
- 右側 `QTabWidget#workflowTabs` 保留 6 個內部頁面與 `TAB_TO_STACK = [0, 6, 2, 5, 3, 4]`，但 tab bar 隱藏，只作內容容器與相容層。

# 5. Control Panel

位於左欄流程導覽下方，提供分析條件。其下方保留特徵快捷與固定動作區，避免頁面主動作散落到側欄。

## 5.1 分析範圍
`QComboBox` 選項：
- 全批
- 首件
- 末件
- 指定板號

若選「指定板號」，顯示板號下拉選單。

## 5.2 主要篩選
- 元件指標（RefDes）
- 元件類型（PartType）

## 5.3 可選篩選（資料欄位存在時顯示）
- 產品（Product）
- 時間起訖（Time start/end）
- 產線（Line）

## 5.4 控制按鈕
- 下一步驟
- 重新分析

收合狀態下由 minimal controls 提供相同行為入口。

## 5.5 側欄密度與可尋性門檻
- 左欄同時可見的主要按鈕限制為 6 個流程按鈕 + 2 個全域動作按鈕。
- 篩選與特徵為控制項，不加入頁面型 action。
- 若導覽、分析條件、特徵與動作在預設視窗高度下出現重疊、裁切或底部動作不可見，優先壓縮 token spacing / 字級；仍不足時收合分析條件，不收合流程導覽或底部主動作。
- 視窗最小高度以側欄可讀性為準；在最小高度附近，`分析條件` 預設收合並顯示「已收合、已保留篩選值」的可見 affordance，`特徵`、`下一步`、`重新分析` 仍須完整顯示。
- 快速載入 DB 面板延後；不得在此版本加入側欄，以免流程、篩選、資料庫操作競爭注意力。

# 6. Chart Analysis Workspace

圖表頁為「Dashboard + 圖表選擇器」模式，不是傳統單一 `QTabWidget`。

組成：
- 頂部工具列（特徵快捷切換、標準化切換）
- 多特徵頁籤分流（`1F / 2F / 3F`，依檢視特徵數切換 selector 相容性）
- 五大分類圖表選擇器（緊湊分類區，可展開/收合；不得以空白欄位撐高第一屏）
- 圖表卡片區（依選取顯示/隱藏）
- 圖表脈絡列需常駐顯示目前特徵、1F/2F/3F 模式、勾選圖表數、標準化狀態與批次／PartType／RefDes 等 active filter；操作提示併入同一列，不能再固定佔兩行。
- 特徵數變更造成不相容時，系統自動改選相容圖，並顯示 transition 訊息（來源圖/目標圖/原因）。
- 圖卡標題列需保持緊湊，顯示圖名、`解讀` 按鈕與渲染狀態 badge：`Ready` / `Incompatible` / `NoData` / `Error`，並以 QSS state 呈現不同視覺語意。
- 每張圖卡標題列提供 `解讀` 按鈕；預設隱藏說明內容，點擊後開啟完整解讀視窗（用途／函數與公式／資料來源／SMT 判讀與下一步）。

# 7. 圖表分類與支援範圍（chart_registry）

五大分類（UI 頂端選單）：
- **製程監控**：I-MR, Xbar-R, Run Chart, OOC, Shift/Drift
- **製程能力**：Cp/Cpk, Normality, Boxplot, Pass/Fail Matrix
- **異常根源**：Pareto, Spatial Heatmap, Repeated Offender
- **變數關係**：Scatter, Correlation matrix/heatmap, Density, Quadrant
- **比較分析**：Subgroup, ANOVA

代表圖表（依現行 `CHART_ORDER`）：
- 製程監控：`imr`, `xbar_r`, `run_chart`, `ooc_analysis`, `shift_detection`, `drift_detection`, `pattern_recognition`, `ewma`, `cusum`
- 製程能力：`histogram_spec`, `normality`, `boxplot`, `pass_fail_matrix`
- 異常根源：`pareto`, `spatial_heatmap`, `repeated_offender`, `outlier_analysis`, `anomaly_3f`, `consistency_3f`
- 變數關係：`scatter_spec`, `correlation_matrix`, `correlation_heatmap`, `density`, `quadrant`, `bivariate_outlier`, `parallel_coord`
- 比較分析：`subgroup`, `anova_parttype`

相容性規則由 `chart_registry` 管理：
- 單特徵
- 雙特徵
- 三特徵
- 至少一個特徵（可 1~3）

# 8. 製程統計分析輸出（`DiagnosticPage`）

**實作**：`app/ui/pages/diagnostic_page.py`（左側流程分頁「診斷」）。頁首可見名稱為「製程統計分析」，主區以少容器報告式版面呈現；主要 KPI 契約為 `payload.summary.process.dashboard_layers`（多層 Alarm／KPI／規格／缺陷／第 8 層診斷等），組合判讀契約為 `payload.diagnostic_evidence_matrix`。

主區閱讀順序固定為「狀態 -> 規格/能力 -> 穩定性/資料範圍 -> 診斷與對策 -> 背景」，欄位順序與嚴重性由 `app/analytics/dashboard_layers_display.py::build_process_stat_report_sections` 供 UI、Excel、PPTX 共用。

工程儀表板層級（摘要；完整鍵見 `docs/specs/data_contract.md` §14）：
- Layer 1（Alarm）：`ooc_rate`, `cpk_below_133_count`, `max_drift_ratio`, `anomaly_cluster_count` 等
- Layer 2（KPI）：`yield_pct`, `dpmo`, `sigma_level` 等（含主特徵 Cpk 語意）
- Layer 3+：資訊／規格／缺陷／產品情境／工程資訊／`layer_8_diagnosis` 等

色彩僅用於狀態語意：`good / warning / bad / neutral`。紅色僅用於超規、Cpk 不足、OOC/OOS 嚴重或需處置項；一般資料與背景資訊使用中性色。

**根因敘事**：高階工程語意（異常類型、影響、可能原因、建議行動、待確認資料、實驗建議）由 `layer_8_diagnosis` 與相關摘要欄位承載；資料不足必須顯示 `UNKNOWN/VERIFY`（與 `root_cause_engine` 契約一致）。

**組合證據分頁**：診斷頁在第 8 卡後提供 `QTabWidget` 分頁，固定包含 `總覽`、`組合矩陣`、`證據矩陣`、`關聯判讀`、`圖表連動`、`對策建議`、`資料背景`。分頁資料以 `diagnostic_evidence_matrix` 為來源，UI/Excel/PPTX 主要透過 `build_readable_diagnostic_tabs(matrix)` 呈現白話判讀列；`diagnostic_evidence_matrix.tabs` 保留為 legacy/fallback，不可在 UI 重新推論圖表證據。

診斷頁頁首提供 `指標解讀` 按鈕；預設不常駐說明，點擊後以視窗顯示 layer_1 至 layer_7 的「用途／如何解讀／門檻含意／建議動作」，並附目前狀態（含 NoData）。

# 9. （保留節號）與 §8 合併說明

本節保留編號以避免外部錨點斷裂。舊版「診斷建議頁」獨立分頁敘述已不適用；現行以 **§8 `DiagnosticPage`** 為準。

# 10. 資料與參考頁面

- 資料頁（DataSetup）：一頁式量化表格布局（embedded mode）
  - 全域 Header 採單列緊湊工具列，提供單一「產品選擇」來源，步驟子區塊不再重複產品選擇控件
  - Header 同列顯示 mini-status（Coord / Spec / Measure），不得另佔第二列
  - 主內容不可再以整頁 scroll host 作為主要布局；`dataSetupTable` 以 `QGridLayout` 固定為工單列跨欄、座標區在左欄跨兩列、鋼板規格與量測區在右欄上下排列
  - `DataSetupLayoutBudget` 需計算 `content_width/content_height`、左右欄寬、工單列高度、主內容高度、右側上下區高度、label/input/action/row budget；實際 layout 只套基準最小值與 stretch，不得用診斷預算把視窗撐出可用區
  - 核心列、Header、Footer Readiness Bar 與 Start Analysis 必須在 `1280x752`、`1200x700`、`1366x768`、`1920x1080` 檢查尺寸內可見且無 sibling overlap
  - Step 1（座標）與 Step 3（量測）支援 Drag & Drop CSV，並顯示檔案 metadata（檔名 / 列數 / 時間）
  - Step 2（鋼板規格）主厚度需符合 `0.05 ~ 0.50 mm`，違規時顯示 inline validation
  - Footer Readiness Bar：僅在 `(產品已選) && (座標存在) && (量測存在) && (厚度有效)` 時啟用 `Start Analysis`
- 參考頁（DataManagement）：參考說明與資料檢視
- 量測庫頁（MeasurementLibrary）：SQLite 歷史量測記錄查詢與載入

# 11. 報告輸出頁（Report Export）

主要操作：
- 產生報告預覽
- 微調要匯出的圖表勾選（工程建議預設）
- 另存 PPTX

輸出契約：
- 僅輸出 PPTX（工程報告結構）
- 預覽需附帶匯出範圍摘要（已選/可用/不相容 + 建議未選示例）；選檔後另有唯讀確認清單（證據圖、預估畫廊頁、分布分析敘事頁）再寫檔。

# 12. 資料相依與啟用條件

- 僅量測資料可用時：可執行一般統計/圖表分析
- 座標 + 量測且關聯成功時：可啟用空間分析
- 缺必要欄位時：顯示相依缺失與不可用理由，不可假裝成功輸出

# 13. 空狀態與錯誤狀態

應明確區分：
- empty（尚未載入/尚無資料）
- incompatible（特徵條件不符）
- warning（可執行但有風險）
- error（計算或資料失敗）

詳細狀態語意見：`docs/specs/ui_state_semantics.md`

# 14. 表格與模型

表格基礎：
```text
QTableView + QAbstractTableModel
```

要求：
- 欄位命名一致
- 空值/錯誤值可辨識
- 不因單一異常資料造成整頁崩潰

# 15. Chart Engine 與責任分工

- 統計運算：`app/analytics/*_engine.py`
- 繪圖渲染：`app/charts/*_chart.py`
- 契約與相容性：`app/analytics/chart_registry.py`
- 圖表視覺語意：`app/charts/base_chart.py` 統一提供量測線、中心線、管制限、規格限、target/mean、OOC/OOS marker、最新點標記、樣本/聚合揭露與 legend 樣式；各 chart class 不得用相同 dash/color 同時表示 control limit 與 spec limit。

建議技術：
| Library | 用途 |
|-------|------|
| Matplotlib | 主圖表渲染 |
| PyQtGraph | 高效能情境（保留） |

# 16. UI Style 與 Token

UI 風格：
- 工程軟體、高資訊密度
- 淺色 Slate + Electric Blue，卡片/表格白底，主要動作使用 Electric Blue
- 全系統統一採用 **Noto Sans TC (思源黑體)**
- 清晰圖表與狀態語意

實作單一來源：
- `app/ui/theme/tokens.py`
- `app/ui/theme/dark_stylesheet.py::get_app_stylesheet()`（`get_dark_stylesheet()` 保留相容）

# 17. DPI 支援

系統需支援：
- 100%
- 125%
- 150%

避免：
- label clipping
- widget overlap
- 重要操作按鈕不可見
- 離屏或過大的歷史視窗幾何阻擋啟動後操作

UI diagnostics snapshot 必須包含主視窗/螢幕可用區與 `Data Setup` 最新 layout budget，方便實機驗證 100% / 125% / 150% 與 CJK 文字裁切風險。

# 18. 效能目標（UI 體感）

- 大資料量下保持可操作
- 分析過程需有 loading 狀態
- 背景執行不可阻塞主 UI

# 19. UI Interaction Flow（現行）

```text
Data Setup
   │
   ▼
Select Filters + Features
   │
   ▼
Refresh Analysis (orchestrator + worker)
   │
   ▼
View Dashboard (Diagnostic) / Charts / Report
   │
  ├─ Charts: 步驟 1 特徵 -> 步驟 2 顯示模式 -> selector 重建 -> autoswitch 提示 -> 脈絡列/狀態確認
   │
   └─ Report: 工程建議預設勾選 -> 微調勾選 -> 匯出範圍摘要 -> 選檔確認 -> PPTX
   │
   ▼
Export Report (Engineering PPTX)
```

# 20. 未來擴展

預留：
- AI 異常判讀強化
- 多產線/多產品線治理視圖
- 報告分眾版本／額外匯出格式（若產品需要）
- 近即時分析流程

# 21. 參考關聯

- 架構規格：`docs/specs/project_architecture.md`
- 資料契約：`docs/specs/data_contract.md`
- 統計規則：`docs/governance/SPC_RULES.md`

# 22. 規格維護與驗收要點（與程式對齊）

本節連結 `docs/specs/spec_maintenance_and_alignment.md`，避免 UI 規格與迭代計畫、實作三者漂移。

- 權威：當本文件、計畫檔與主分支程式行為不一致時，以可驗證的程式行為為準。
- 設計 token：顏色、字級、間距、狀態語意之實作單一來源為 `tokens.py` / `get_app_stylesheet()`。
- 版面/流程變更：若捲動範圍、欄位順序、步驟結構改變，需同步更新規格與對照報告。
- 響應式與 DPI：宣稱特定解析度/縮放行為時，需具體寫明環境矩陣與判定方式。
- 狀態與 QSS：`objectName`、`state`、`class` 變更須同步 `docs/specs/ui_state_semantics.md`。
- 問題解決流程：跨模組變更需依 `docs/specs/issue_resolution_workflow.md` 執行。

## 23. 2026-04-02 實作對齊快照

- `main.py` 使用 `run_app()` 進入主視窗。
- 主視窗流程導覽已移至左側 `NavigationPanel`；右側 `QTabWidget#workflowTabs` 作為內部頁面容器並隱藏 tab bar。
- 圖表分析前置由 `AnalysisOrchestrator` 統一處理，並以狀態碼回傳給 UI。
- 製程統計分析輸出（`DiagnosticPage`）依 `dashboard_layers` 呈現報告式多層工程資訊（含 Alarm／KPI／規格能力／診斷對策等）。
- 圖表頁主流程採五大分類（製程監控／製程能力／異常根源／變數關係／比較分析），分類與 `chart_registry` 一致。
- 圖表頁頂部工具列維持單列緊湊模式；`多特徵標準化` 與 `單特徵/雙特徵/三特徵` 同列，避免誤讀為獨立流程。
- 圖表頁新增 autoswitch reason 與全域脈絡列；脈絡列即時顯示 active features、顯示模式、已選圖表數、多特徵標準化狀態與 active filters，並承接操作提示。圖卡維持 `Ready/Incompatible/NoData/Error` 狀態 badge。
- 圖表頁每張圖卡新增 `解讀` 按鈕，使用共用視窗顯示完整四段說明（不再依賴 tooltip 才能看完整內容）。
- 診斷頁新增 `指標解讀` 按鈕，使用單一 registry 維護 layer_1~layer_7 工程判讀文案。
- 診斷頁新增組合證據分頁，依 `diagnostic_evidence_matrix` 呈現 feature/chart/filter/display 候選覆蓋、證據矩陣與多圖表關聯判讀；可見文字使用 readable rows 說明「判斷結果、原因、證據來源、下一步」，避免只顯示狀態碼或下一步圖表名稱。
- 報告輸出為工程導向 PPTX；UI 不提供 HTML 匯出入口，也不提供管理/工程模板切換。
- 報告頁以工程建議圖表為預設勾選，匯出範圍摘要置於緊湊頁首；群組卡片直接置於無框內容區並依內容高度靠上排列，避免卡片包卡片或空白容器；另存 PPTX 選檔後有確認清單再寫檔。
- `report_service` 已拆分多個 `report_*` 子模組以降低耦合。
