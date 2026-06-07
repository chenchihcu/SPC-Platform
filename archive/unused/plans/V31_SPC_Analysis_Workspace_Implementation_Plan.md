# V.31 — SPC Analysis Workspace 實作計畫

工程級 SPC 分析工作區設計與開發計畫。**僅規劃，不實作程式碼。**

> **與主線規格對齊**：計畫與 `docs/governance/AGENTS.md`、資料／圖表契約或實作衝突時，治理與更新順序見 **`docs/specs/spec_maintenance_and_alignment.md`**。

---

## 1. Repository 檔案結構對照

### 1.1 頂層與進入點

| 路徑 | 用途 |
|------|------|
| `main.py` | 應用進入點，`run_app()` |
| `chart_router.py` | 圖表可用性條件（量測載入、映射、批次、座標、元件類型、特徵數） |
| `docs/reference/requirements.txt` | 依賴 |
| `docs/governance/AGENTS.md` | 專案規範（UI/theme、重新整理按鈕 loading 狀態） |

### 1.2 App 模組結構

```
app/
├── analytics/          # 統計與圖表計算
│   ├── spc_engine.py           # I-MR、UCL/LCL、OOC
│   ├── capability_engine.py    # Cp/Cpk
│   ├── distribution_engine.py  # 直方圖
│   ├── pareto_engine.py        # 現為 DefectType Pareto
│   ├── spatial_engine.py       # 熱圖 (x,y,value)
│   ├── comparison_engine.py    # Boxplot by RefDes/PartType
│   ├── ewma_engine.py, cusum_engine.py
│   ├── run_chart_engine.py
│   ├── chart_registry.py       # CHART_ORDER, payload_key, 描述
│   └── ...
├── charts/              # Matplotlib 圖表繪製
│   ├── base_chart.py
│   ├── control_chart.py, histogram_chart.py
│   ├── heatmap_chart.py, pareto_chart.py, boxplot_chart.py
│   ├── ewma_chart.py, cusum_chart.py
│   └── ...
├── data/
│   ├── session_store.py        # 全域資料、篩選、cache
│   ├── loaders/                # measurement, coordinate, workorder — 不修改
│   ├── relation/join_engine.py # 不修改
│   └── mapping/schema_mapper.py# 不修改
├── services/
│   ├── import_service.py       # 不修改
│   ├── report_service.py       # 不修改邏輯
│   └── chart_render.py
├── ui/
│   ├── main_window.py          # 主視窗、refresh、payload 傳遞
│   ├── pages/
│   │   ├── chart_analysis_page.py  # 左清單 + 右 stacked 圖表
│   │   ├── component_select_page.py
│   │   └── ...
│   ├── tabs/                   # 各圖表分頁 (pareto_tab, spatial_tab, ...)
│   ├── theme/                  # tokens, dark_stylesheet
│   └── widgets/                # control_panel, page_templates, ...
└── viewmodels/
    └── chart_analysis_viewmodel.py  # analyze(), compute_analysis_payload()
```

---

## 2. 目前 UI 架構

- **主視窗**：`MainWindow` → `QSplitter`（`CollapsibleSidebar` + `QStackedWidget` workspace）。
- **導航**：`NavigationPanel` 步驟點擊；`ControlPanel`：分析批次、取樣模式、元件指標、元件類型、重新整理、下一步。
- **七頁**：資料設定 → 工單資料輸入 → 元件/量測選定 → 統計分析 → **圖表分析** → 報告輸出 → 資料管理。
- **圖表分析頁**：左側 `QListWidget` 圖表清單（依特徵數與 chart_router 條件顯示/隱藏），右側 `QStackedWidget` 對應各圖表頁；當前選中圖表由 `_last_payload` + `get_payload_slice(payload, chart_id)` 驅動 `update_data(slice)`。
- **資料流**：使用者點「重新整理分析」→ `main_window.refresh_analysis` → `filter_analysis_df(df, batch, refdes, part_type)` → `AnalysisWorker` 或 ViewModel.analyze() → `compute_analysis_payload()` → `data_ready.emit(payload)` → `chart_analysis_page.update_all_charts(payload)` → 各 tab 的 `update_data(slice)`。

---

## 3. 圖表繪製模組

| 規格步驟 | 現有圖表 | 模組 |
|----------|----------|------|
| Step 1 Global | 直方圖、I-MR、能力 | `distribution_engine` + `histogram_chart`；`spc_engine` + `control_chart`；`capability_engine` |
| Step 2 Pareto | 柏拉圖 | `pareto_engine`（DefectType） + `pareto_chart` |
| Step 3 Component SPC | I-MR、直方圖、能力 | 同上，資料來源為篩選後 component |
| Step 4 Footprint | 箱型/變異比較 | `comparison_engine`（boxplot by RefDes）+ `boxplot_chart` |
| Step 5 Heatmap | 空間熱圖 | `spatial_engine`（單一 value）+ `heatmap_chart` |
| Step 6 Correlation | volume vs height/area | `scatter_engine`、`quadrant_engine`、`density_engine` + 對應 chart |
| Step 7 Drift | EWMA、CUSUM | `ewma_engine`、`cusum_engine` + 對應 chart |

圖表順序由 `app/analytics/chart_registry.py` 的 `CHART_ORDER` 決定；各 tab 在 `chart_analysis_page._make_page()` 中註冊。

---

## 4. 資料處理模組

- **篩選**：`session_store.filter_analysis_df(df, batch, refdes, part_type)`，欄位為 BoardNo、RefDes、PartType。
- **分析入口**：`chart_analysis_viewmodel.compute_analysis_payload(filtered_df, selected_features, usl, lsl, target, workorder_spec)`，回傳單一 payload 含 spc、cap、dist、pareto、spatial、box、ewma、cusum 等 key。
- **SPC**：`SPCEngine.compute_imr(data_series, target_col)` 提供 UCL/LCL/OOC indices。
- **Pareto**：目前 `ParetoEngine.compute_pareto(meas_df, target_col)` 為 DefectType（Missing/Insufficient/Excess）次數，**非** component 維度 abnormal_rate。
- **空間**：`SpatialEngine.compute_heatmap(joined_df, target_col)` 輸出 (x, y, values)，無 UCL/LCL/OOS 密度模式。
- **Footprint**：`ComparisonEngine.compute_boxplot(df, target_col, group_col="RefDes")`，可改為 PartType 或「同 footprint」分組以支援同設計多位置比較。

---

## 5. 狀態管理

- **集中儲存**：`SessionStore` 單例，存 `meas_df`、`coord_df`、`joined_df`、`selected_features`、`last_analysis_payload`、`_analysis_cache`。
- **篩選來源**：`control_panel.batch_combo`、`refdes_combo`、`part_type_combo` 的 currentText；refresh 時帶入 `filter_analysis_df`。
- **Payload 脈絡**：payload 附帶 `_ctx_batch`、`_ctx_part_type` 供 chart_analysis_page 建 ChartContext。
- **未具備**：product、time range、line 等維度尚未納入篩選；所有圖表共用同一 payload，但**篩選維度**需擴充為「共享 filter state」。

---

## 6. 建議修改的檔案（候選）

| Phase | 候選檔案 | 變更性質 |
|-------|----------|----------|
| 1 | `app/ui/pages/chart_analysis_page.py` | 工作區版面、圖表順序/分組標題對齊工作流 |
| 2 | `app/data/session_store.py` | 擴充 filter 維度（product、time_range、line）、cache key |
| 2 | `app/ui/widgets/control_panel.py` | 新增 product/time/line 篩選 UI（可選，依資料有無欄位） |
| 2 | `app/ui/main_window.py` | refresh 時讀寫擴充後 filter state、傳入 filter_analysis_df |
| 3 | `app/analytics/pareto_engine.py` | 新增 component 維度 Pareto，abnormal_rate = (OOS+UCL+LCL)/total |
| 3 | `app/charts/pareto_chart.py`、`app/ui/tabs/pareto_tab.py` | 可點擊 bar、發出 component 選取 signal |
| 3 | `app/ui/main_window.py` 或 chart_analysis_page | 接 Pareto 點擊 → 設定 component 篩選 → 觸發 refresh |
| 4 | 沿用現有 spc、distribution、capability；確保預設 Volume | 必要時調整 chart_registry 預設 |
| 5 | 同 Step 3：component 資料來自篩選後 payload | 不需新檔，確保 Pareto 點擊後為 component SPC |
| 6 | `app/analytics/comparison_engine.py` | 支援「同 footprint」分組（PartType 或自訂 grouping） |
| 6 | `app/ui/tabs/comparison_tab.py` | 足印比較模式、boxplot/variance 呈現 |
| 7 | `app/analytics/spatial_engine.py` | 熱圖模式：UCL/LCL/OOS 密度、Volume 偏差 |
| 7 | `app/charts/heatmap_chart.py`、`app/ui/tabs/spatial_tab.py` | 模式切換 UI、對應 colorbar/說明 |
| 8 | 已有 scatter/quadrant/density | 確保預設 Volume 優先、說明一致 |
| 9 | 已有 ewma/cusum | 確保板序/時間軸正確、說明一致 |
| 10 | `app/analytics/*.py`、payload 結構 | 向量化、預先計算 abnormal flags、聚合後再傳圖表、lazy 渲染 |
| 10 | `app/analytics/spatial_engine.py` | 可選：scipy.spatial.cKDTree 用於熱圖/叢集 |

**不修改**：`app/data/loaders/*`、`app/data/relation/join_engine.py`、`app/data/mapping/schema_mapper.py`、`app/services/report_service.py` 之既有邏輯與對外介面。

---

## 7. 實作階段（Phase 1–10）

### Phase 1 — 建立 SPC Analysis Workspace 頁

- **目標**：圖表分析頁即為「SPC Analysis Workspace」，版面與流程標示清楚。
- **作法**：在既有 `ChartAnalysisPage` 上調整左側清單分組/標題，使順序對齊：Global Overview → Pareto → Component Analysis → Footprint Comparison → PCB Heatmap → Correlation → Drift（可與現有 CHART_ORDER 對應，或僅改顯示名稱/分組）。
- **產出**：工程師進入圖表分析頁即看到工作流導向的圖表清單與單一右側工作區。
- **檔案**：`app/ui/pages/chart_analysis_page.py`，必要時 `app/analytics/chart_registry.py`（僅顯示用）。

### Phase 2 — 共用篩選狀態（Shared Filter State）

- **目標**：所有圖表讀取同一 filter state；變更篩選即重新整理並更新所有圖表。
- **作法**：
  - 在 `SessionStore`（或獨立 FilterState 物件由 SessionStore 持有）中定義 filter 維度：product（或 product_name）、time_range、component（refdes/part_type）、measurement_type（已為 selected_features）、line；若資料無欄位則該維度不參與過濾。
  - 擴充 `filter_analysis_df` 簽名或新增輔助函式，在現有 batch/refdes/part_type 外，依欄位存在性加入 product、time、line 過濾。
  - Control panel 若有 product/time/line 下拉或輸入，其變更與既有 batch/refdes/part_type 一樣觸發 `_schedule_refresh_analysis`；refresh 時以擴充後 filter 產生 `filtered_df`，再傳入 `compute_analysis_payload`。
- **驗證**：改任一模擬篩選 → 一次 refresh → 所有圖表皆依新 filtered_df 更新。
- **檔案**：`app/data/session_store.py`、`app/ui/widgets/control_panel.py`（可選）、`app/ui/main_window.py`、`app/viewmodels/chart_analysis_viewmodel.py`。

### Phase 3 — Pareto 元件排名（Component Ranking）

- **目標**：Pareto 以「元件」為維度，abnormal_rate = (OOS + UCL + LCL violations) / total；點擊 Pareto 長條自動觸發元件級分析。
- **作法**：
  - **Pareto 計算**：在 `pareto_engine` 新增（或並存）component-based 計算：依 PartType 或 RefDes 分組，每組用 SPC 的 UCL/LCL 與規格 OOS 計算違反次數，得到 abnormal_rate 與排序；輸出結構含 component_id、abnormal_rate、total 等，供圖表與點擊使用。
  - **圖表**：Pareto 圖改為顯示 component 排名（長條為 component），可點擊 bar 取得 component_id。
  - **互動**：Pareto 點擊 → 設定 control_panel 的 refdes 或 part_type 為該 component → 呼叫既有 refresh → 下游圖表（I-MR、直方圖、能力等）自動變為該 component 的資料。
- **驗證**：點 Pareto 某一 component → 右側切到 I-MR/直方圖/能力時，資料僅為該 component。
- **檔案**：`app/analytics/pareto_engine.py`、`app/charts/pareto_chart.py`、`app/ui/tabs/pareto_tab.py`、`app/ui/main_window.py` 或 chart_analysis_page（signal 連接）。

### Phase 4 — 全域 SPC 圖表

- **目標**：Global volume 直方圖、I-MR、製程能力明確為「全域」且預設 Volume。
- **作法**：維持現有 distribution、spc、capability 計算與圖表；確認 `DEFAULT_SELECTED_FEATURES = ["Volume"]` 與 chart_registry 預設一致；工作區清單中將 I-MR、直方圖、能力歸於「Global Overview」區塊（僅標題/分組，不必改演算法）。
- **檔案**：必要時 `app/analytics/chart_registry.py`、`app/ui/pages/chart_analysis_page.py`（標題/順序）。

### Phase 5 — 元件 SPC 圖表

- **目標**：選定 component 後，同一組 I-MR、直方圖、能力顯示該 component 的趨勢與能力。
- **作法**：不新增新圖表類型；依 Phase 3，Pareto 點擊後篩選為該 component，再 refresh，則既有 I-MR/直方圖/能力 tab 收到的 payload 已是 component 篩選後結果。僅需在 UI 上標示「目前為 component 分析」或顯示當前 component 名稱。
- **檔案**：`app/ui/tabs/control_chart_tab.py`、distribution_capability_tab、chart_analysis_page 的說明文字或標題。

### Phase 6 — 同 Footprint 比較（Same Footprint Comparison）

- **目標**：同一 footprint（如 U14、U38、U52）不同 PCB 位置之 boxplot 與變異比較，用於鋼板開孔/版面影響。
- **作法**：
  - **分組**：以 PartType 或「component name prefix / CAD footprint」為 footprint 群組（現有 PartType 可視為 footprint 代理）；同一 PartType 下多個 RefDes 即「同設計不同位置」。
  - **comparison_engine**：支援「依 PartType 分組，組內以 RefDes 為子群」的 boxplot 或 variance 比較；輸出供 boxplot_chart 或新比較圖使用。
  - **UI**：在 comparison_tab 或獨立區塊可選「Footprint 比較」模式，顯示同 PartType 下各 RefDes 的 volume 分布/變異。
- **驗證**：選定 PartType 後，可看到多個 RefDes 的 boxplot 並排或變異比較。
- **檔案**：`app/analytics/comparison_engine.py`、`app/ui/tabs/comparison_tab.py`、`app/charts/boxplot_chart.py`。

### Phase 7 — PCB 熱圖分析（多模式）

- **目標**：熱圖支援四種模式 — UCL 違反密度、LCL 違反密度、OOS 密度、Volume 偏離平均。
- **作法**：
  - **spatial_engine**：新增 mode 參數；依 mode 計算 (x,y) 對應的聚合值：例如格點或點位上的 UCL/LCL/OOS 計數或密度、或 volume 與均值的偏差；必要時用 `scipy.spatial.cKDTree` 做空間聚合以加速。
  - **heatmap_chart / spatial_tab**：新增模式選擇（下拉或按鈕），依 mode 繪製不同 colorbar 與標題。
- **驗證**：切換模式後熱圖與 PCB 座標對應正確，四種模式皆可運作。
- **檔案**：`app/analytics/spatial_engine.py`、`app/charts/heatmap_chart.py`、`app/ui/tabs/spatial_tab.py`。

### Phase 8 — 相關分析（Correlation）

- **目標**：Volume vs Height、Volume vs Area 圖表，用於 paste collapse、stencil clogging、aperture mismatch 調查。
- **作法**：沿用現有 scatter_spec、quadrant、density；確保雙特徵選取時預設建議 Volume 為其一；圖表說明與工作區標籤對齊「Correlation」。
- **檔案**：必要時 `app/ui/pages/chart_analysis_page.py`、chart_registry 說明文字。

### Phase 9 — 漂移偵測（EWMA / CUSUM）

- **目標**：EWMA、CUSUM 用於緩慢劣化（paste drying、stencil contamination、squeegee wear）。
- **作法**：沿用現有 ewma_engine、cusum_engine 與圖表；確保資料依板序或時間排序；工作區中歸於「Trend Drift Detection」。
- **檔案**：必要時說明與順序。

### Phase 10 — 大資料效能優化

- **目標**：支援 100k–500k 筆，向量化、少迴圈、預先計算 abnormal、有效聚合、lazy 圖表。
- **作法**：
  - 計算層：abnormal flags（OOS、UCL、LCL）以向量化一次算完；Pareto、熱圖、能力等先 groupby/agg，再傳圖表；避免將整份 raw 傳給圖表。
  - 圖表層：僅當前可見圖表呼叫 draw；散點/平行座標等可依資料量取樣顯示。
  - 空間：在 spatial_engine 或專用模組用 `scipy.spatial.cKDTree` 做近鄰/密度查詢，加速熱圖密度模式。
- **檔案**：`app/analytics/*.py`（多檔）、`app/viewmodels/chart_analysis_viewmodel.py`、payload 結構設計。

---

## 8. 風險清單

| 風險 | 說明 | 緩解 |
|------|------|------|
| Pareto 定義變更 | 由 DefectType 改為 component abnormal_rate，可能影響既有依賴 | 並存兩者或僅新增 component Pareto；必要時保留 DefectType 為次要選項 |
| 篩選欄位不存在 | product/time/line 在 CSV 無對應欄位 | 僅在資料有該欄位時啟用對應篩選；filter 函式內若無欄位則跳過 |
| Pareto 點擊與 combo 同步 | 程式設定 part_type/refdes 觸發 currentTextChanged 導致雙重 refresh | 設定前 blockSignals(true)，設定後 blockSignals(false)；或以 flag 略過一次 refresh |
| 大資料記憶體與延遲 | 500k 筆全量傳遞或重複計算 | 嚴格「先聚合再繪圖」、lazy 渲染、必要時取樣；abnormal 預先算一次 |
| Footprint 分組定義 | 目前僅 PartType；若需 CAD/footprint 需額外欄位 | V.31 以 PartType 作為 footprint 代理；若未來有 footprint 欄位再擴充 |
| 熱圖四模式與 SPC 一致 | UCL/LCL 需與 I-MR 或規格一致 | 熱圖模式使用與 SPC 相同的 UCL/LCL/OOS 定義與資料來源 |

---

## 9. Minimal-Change 策略

- **不修改**：database schema（本專案為 in-memory + CSV/JSON，指 loaders/join/schema）、SPI import pipeline（loaders、join_engine）、raw SPI 格式（schema_mapper 必備欄位定義）、report 產生邏輯（report_service 對外介面與核心流程）。
- **僅擴充**：SessionStore 的 filter 維度與 cache key、payload 的 key（如 component_pareto、heatmap_mode）、analytics 的新函式或新回傳結構、圖表 tab 的 mode 與說明。
- **向後相容**：`DEFAULT_SELECTED_FEATURES = ["Volume"]` 不變；既有圖表 ID 與 chart_registry 不刪減；既有 Pareto DefectType 可保留為選項或隱藏，不破壞既有報表/匯出。
- **驗證檢查點**：Pareto 點擊會更新下游圖表；篩選變更會更新所有圖表；熱圖座標正確對應 PCB (x,y)；同 footprint 分組與比較正確；大資料下 refresh 與圖表在合理時間內完成。

---

## 10. 驗證對照表

| 項目 | 驗證方式 |
|------|----------|
| Pareto 點擊更新下游圖表 | 點 Pareto 某 component → 篩選更新 → 切到 I-MR/直方圖/能力 → 資料僅該 component |
| 篩選更新所有圖表 | 變更 batch/refdes/part_type（及 product/time/line 若有）→ 一次 refresh → 所有圖表一致更新 |
| 熱圖正確對應 PCB 座標 | 熱圖 X/Y 與 joined_df 的 X,Y 一致；四種模式切換後仍為同一座標系 |
| Footprint 分組 | 同 PartType 下多 RefDes 可並排 boxplot 或變異比較 |
| 大資料效能 | 100k–500k 筆下 refresh 與圖表渲染在可接受時間內；無明顯卡頓 |

---

*文件版本：V.31 規劃用；實作前需再確認與現有測試/回歸範圍。*
