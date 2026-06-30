# SMT SPI / SPC 統計分析平台
## 資料契約 (Data Contract)

# 1. 資料來源

系統支援三種主要資料來源：
1. 座標檔 (Coordinate File)
2. 量測記錄檔 (Measurement Record)
3. 工單主檔 (Workorder Master)

# 2. 座標檔

## 用途
建立 PCB 元件位置與元件屬性。

## 標準欄位

| 欄位 | 說明 |
|-----|-----|
| RefDes | 元件代號 |
| X | X 座標 |
| Y | Y 座標 |
| Layer | Top / Bottom |
| Rotation | 旋轉角度 |
| PartType | 元件類型 |
| Width | 元件寬度 |
| Height | 元件高度 |

## 最低必要欄位

```text
RefDes
X
Y
```

若缺少：
- 禁用空間分析

# 3. 量測記錄檔

## 用途
SPI 檢測數據來源。

## 常見欄位

| 欄位 | 說明 |
|-----|-----|
| RefDes | 元件代號 |
| BoardNo | 板編號 |
| Time | 檢測時間 |
| Volume | 錫膏體積 |
| Area | 錫膏面積 |
| Height | 錫膏高度 |
| XOffset | X 偏移 |
| YOffset | Y 偏移 |
| Result | 判定結果 |
| Pad | 焊墊/Pad 識別（選用；供缺陷結構彙整使用） |

## 最低必要欄位

```text
RefDes
至少一個量測值 (Volume / Area / Height)
BoardNo 或 Time
```

# 4. 欄位映射

因不同 SPI 機台 CSV 格式不同，系統必須支援 **欄位別名映射**。

## 例

| 標準欄位 | 可能別名 |
|---------|---------|
| RefDes | Ref, Component |
| BoardNo | BoardID, Panel |
| Volume | Vol |
| Height | H |
| Area | A |

## 供應商限定映射：振順豐 TOP.csv

振順豐量測檔使用專用 profile，不屬於全域別名表。啟用條件：

- 供應商欄位為 `振順豐` 時啟用。
- 若未選供應商，僅當檔案路徑含 `振順豐` 且欄位簽名完全符合時自動啟用。
- 若已選其他供應商，即使檔名或路徑含 `振順豐` 也不套用此 profile。

欄位簽名：

```text
Component ID
PAD ID
Volume(mm)<n>
Height(mm)<n>
Area(mm)<n>
```

轉換契約：

| 原始欄位 | 標準欄位 |
|---------|---------|
| Component ID | RefDes |
| PAD ID | Pad |
| Volume(mm)<n> | Volume |
| Height(mm)<n> | Height |
| Area(mm)<n> | Area |
| <n> | BoardNo = Board_<n> |

此 profile 將寬表轉為長表，並於 `meas_meta` 記錄 `vendor_profile`、
`raw_rows`、`raw_columns`、`board_count` 與 `measurement_units`。`Volume`、
`Area`、`Height` 會轉為 numeric，但系統不隱性把絕對量測值轉成百分比；規格比對仍需由產品規格單位模式保證語意一致。

量測庫 session 需保存 `supplier` 供應商名稱；從量測庫回載量測檔時，
`MeasurementLibraryPage` 會把 `supplier` 放入 context，`MainWindow` 會同步寫回
`SessionStore.workorder_master["supplier"]`，確保不依賴檔案路徑即可再次啟用供應商限定 profile。

# 5. 資料關聯

## 關聯鍵

```text
RefDes
```

可輔助：
- Layer
- Product
- BoardNo

## 關聯結果
系統必須輸出：
- 匹配數量
- 未匹配數量
- 匹配率

# 6. 空間分析條件

必須同時具備：
- 座標檔
- 量測記錄檔
- 成功 RefDes 關聯

否則禁用：
- Heatmap
- PCB 空間分布分析

# 7. 能力分析條件

必須具備：
- 量測資料
- 規格上下限 (USL / LSL)

否則只顯示：
- Histogram

不顯示：
- Cp / Cpk

# 8. 錯誤處理

| 問題 | 處理 |
|----|----|
| 缺座標 | 禁用空間分析 |
| 缺 RefDes | 無法關聯 |
| 缺量測值 | 無法統計 |
| 欄位錯誤 | 顯示 schema error |

# 9. 資料驗證

系統需自動檢查：
- 必要欄位
- 空值比例
- 異常數據

# 10. 未來擴展

可支援：
- AOI 檢測數據
- Reflow Profile
- 多工站資料整合

# 11. 契約與實作對齊（單一真相與變更流程）

本節連結 **`docs/specs/spec_maintenance_and_alignment.md`**。

- **必填欄位、別名映射、關聯鍵**：以本文件 §2–§5 為準；若 Loader、SessionStore 或 join 行為變更，**必須** 先更新本契約再改程式（或同步 PR 內更新本節與表格）。
- **圖表／分析 payload**：切片與合併規則應由 **單一共享來源**（如 `chart_registry`、共用 helper）定義；UI 與報表路徑 **不得** 重複實作同一語意的 merge 邏輯（見 `docs/governance/AGENTS.md` §7 與 `docs/reports/chart_contract_audit.md`）。
- **單一解析入口**：UI/報表的 chart payload 解析應統一走 `chart_registry.resolve_chart_payload(...)`；不得在 `chart_analysis_page` 或 `chart_render/report_service` 內自行維護平行 3F merge/slice 規則。
- **抽樣契約欄位**：有抽樣圖表至少需提供 `n`、`displayed_n`、`sampled_for_display`、`sampling_method`；舊欄位（例如 `n_points`）僅能作過渡別名，最終應退場。
- **正規化語義**：若顯示抽樣與統計母體不同，需明確標示 `normalization_basis`（例如 `full_valid_data`）。
- **CUSUM_3F 正規化標註**：當 Y 軸為正規化尺度時，圖例需標明 `hσ(raw)` 或等價語意，避免將原始參數誤讀為軸上單位。
- **隱性截樣禁止（預設全量）**：統計圖表預設不得隱性 `top_n` 或固定筆數截取；若呼叫端明確要求截取（例如 repeated-offender `top_n`），必須同時輸出 `n`、`displayed_n`、`sampled_for_display`，並於圖上提供可見提示。
- **聚合視為顯示壓縮**：座標格網聚合（如 spatial heatmap grid aggregation）屬顯示壓縮，需同樣輸出 `n/displayed_n/sampled_for_display/sampling_method`，並建議包含聚合參數（例如 `aggregation_bins`）。
- **常態檢定樣本透明度**：normality payload 必須輸出 `total_n`、`tested_n`、`sampled_for_test`；若採大樣本替代檢定法，`test_name` 需可辨識且不得隱性抽樣。
- **與計畫／設計書衝突**：以主分支 **可驗證行為** 與本契約為優先；過期計畫應標示 `needs-update` 或歸檔，避免「文件宣稱已支援欄位 X」但程式未實作。
- **領域門檻與分類**（例如無規格時是否可計算、fallback）：統計決策以 **`docs/governance/SPC_RULES.md`** 為準；契約僅描述 **資料是否到齊**，不重新定義公式。

# 12. 統計摘要（summary）缺陷指標契約

本節之「統計摘要」指 **`payload["summary"]`** 結構（含儀表板用 `process.dashboard_layers`），**不是**已移除之獨立「統計」分頁名稱。

本節定義 `payload["summary"]` 的擴充欄位（工程版統計摘要使用）。

## 12.1 輸出結構

- `summary.per_measure[col].defect`
  - `ppm_below_lsl`
  - `ppm_above_usl`
  - `ppm_total`
  - `dpmo_feature`
  - `zbench_st`
  - `zbench_lt`
  - `cpk_ci`（`[lower, upper]` 字串；若無法估計則 `N/A`）
  - `cpk_ci_method`（CI 公式版本字串；若無法估計則 `N/A`）

- `summary.process.defect_combined`
  - `dpmo_combined_event`
  - `dpmo_combined_board`
  - `combined_defect_event_count`
  - `combined_defect_board_count`
  - `board_n`
  - `opportunity_per_board`（本次分析納入規格的特徵數，通常為 `3`）
  - `opportunity_count_feature`
  - `opportunity_count_combined_event`
  - `opportunity_count_combined_board`

## 12.2 公式與口徑

- Feature 級（單一量測特徵）：
  - `PPM(<LSL) = count(x < LSL) / n_valid * 1,000,000`
  - `PPM(>USL) = count(x > USL) / n_valid * 1,000,000`
  - `PPM(Total) = PPM(<LSL) + PPM(>USL)`
  - `DPMO(Feature) = defect_count / n_valid * 1,000,000`
- Combined 級（跨特徵）：
  - `DPMO(Combined-Event) = combined_defect_event_count / (n_complete_rows * feature_count) * 1,000,000`
  - `DPMO(Combined-Board) = combined_defect_board_count / board_n * 1,000,000`
- `Zbench(ST/LT)`：以 ST/LT 對應缺陷率路徑反推，維持 ST/LT 雙口徑語意。
- `Cpk 95% CI`：採 **Bissell 近似式**（NIST/AIAG 常見口徑）估計兩側 95% 區間；下限最小截斷為 `0`。統計規則定義見 `docs/governance/SPC_RULES.md`。

## 12.3 無效值處理

- 任一特徵缺 `USL/LSL`、有效樣本為 0、或分母為 0 時，對應欄位輸出 `null`（UI 顯示 `—`）。
- `n_valid`、`PPM`、`DPMO`、`Yield` 的分母口徑一致：皆使用去除 `NaN` 與 `±inf` 後的有效樣本。
- 本節僅定義資料契約與口徑，不重定義 `docs/governance/SPC_RULES.md` 之能力判定門檻。

## 12.4 SPI 製程對應知識庫（Excel 權威稿 → JSON 運行稿）

- **人維護權威稿檔名**：`SPI_製程對應知識庫_v1.0.xlsx`（與程式常數 `app.services.spi_process_kb_loader.CANONICAL_SPI_KB_WORKBOOK_BASENAME` 一致）。
- **匯入腳本**：`scripts/import_spi_process_kb_xlsx.py`，將工作表轉成 `data/spi_process_kb/v1/*.json`；`manifest.json` 可含 `source_xlsx_basename`、`source_xlsx_sha256`（匯入後寫入）。
- **執行期讀取**：僅讀 JSON bundle（`multi_signal_rules`、`dimension_abnormality_matrix`、`inspection_checklist`、`chart_signal_lookup`），不直接讀 xlsx。
- **預設工作表名**（與 `SPI_製程對應知識庫_v1.0.xlsx` v1 版一致；匯入腳本 `--sheet-*` 預設已對齊）：`🔗 多訊號關聯規則`、`📊 訊號×異常×原因`、`🔧 製程原因檢查清單`、`⚡ 訊號速查矩陣`。第一列為標題列時使用 **`--header-row 1`**（預設）；舊版無標題列、工作表名為 `多訊號關聯診斷規則表` 等時，請改用 **`--header-row 0`** 並以 `--sheet-*` 覆寫工作表名。

# 13. 2026-04-19 實作對齊快照

- 分析入口 `app/ui/main_window.py::_run_refresh_analysis()` 在有產品名稱時，先呼叫 `can_run_analysis()` 再呼叫 `resolve_workorder_spec()`。
- `resolve_workorder_spec()` 失敗（無規格、階梯鋼板未指定精密元件）時，流程會中止並回報錯誤訊息。
- 工單欄位契約：優先使用 `supplier_work_order_no` 與 `outsource_work_order_no`；`work_order_no` 保留相容鍵但寫入固定空字串（讀取端可保留舊值 fallback）。

# 14. 工程儀表板層級契約（`summary.process.dashboard_layers`）

`payload["summary"]["process"]["dashboard_layers"]` 為 UI（`DiagnosticPage` 製程統計分析輸出）與報告共用契約。

## 14.1 Layer 1（Alarm）

- `ooc_rate = max_f(ooc_count_f / n_f)`
- `cpk_below_133_count = count_f(cpk_f < 1.33)`
- `max_drift_ratio = max_f(max(|C+_f|, |C-_f|) / h_sigma_f)`
- `anomaly_cluster_count = max_f(contiguous_ooc_clusters_f)`

狀態欄位：
- `ooc_rate_state`
- `cpk_below_133_state`
- `max_drift_ratio_state`
- `anomaly_cluster_state`

若 `h_sigma_f` 不可用或非正值，`max_drift_ratio` 輸出 `null`（UI 顯示 `UNKNOWN/VERIFY`），不得推估。

## 14.2 Layer 2（KPI）

- `avg_cpk`
- `avg_ppk`
- `yield_pct`
- `dpmo`
- `sigma_level`

## 14.3 Layer 3（Info）

- `driver_feature`
- `sample_size`
- `mean`
- `std`
- `range`

`driver_feature` 選擇規則：
1. 優先使用 `min_cpk_measure`（Alarm driver）
2. 若無可用 Cpk，改用首個可分析特徵（`Volume -> Area -> Height`）

## 14.4 Layer 4（Defect structure）

- `top_oos_refdes`: `List[{"id": str, "oos_count": int}]`，依 RefDes 聚合 USL/LSL 外筆數（僅 `primary_feature` 有規格且資料含 `RefDes` 時填充；否則 `[]`）。
- `top_oos_pad`: 同上，欄位優先序 `PadName` → `Pad` → `Footprint`。
- `abnormal_cluster_location`: 保留 `null`（待擴充）。
- `cluster_ratio`: `anomaly_cluster_count / sample_size`（Layer 3 之樣本數），可能為 `null`。
- `step_stencil_area_oos_rate`: 保留 `null`（待與階梯鋼板 Area 規格對齊）。

## 14.5 Layer 5（Spec analysis）

以 `compute_summary(..., primary_feature=...)` 所選特徵為主（無則與 `driver_feature` 對齊）。僅當該特徵具 USL/LSL 且 `spec_range > 0` 時為非空物件，欄位含：`feature`、`target`、`spec_range`、`usl`、`lsl`、`mean_shift_pct`、`std_spec_ratio`、`cp`、`cpk`、`oos_count`、`oos_rate`（0–1 比例）、`spec_tightness_level`。

## 14.6 Layer 6（Product / stencil context）

來自選用參數 `workorder_master` 的已知鍵子集（如 `product_name`、`supplier_work_order_no`、`outsource_work_order_no`、`stencil_thickness` 等）；`work_order_no` 僅作相容鍵，寫入路徑固定為空字串，讀取端可保留舊資料 fallback；未提供之鍵不出現在物件中。

## 14.7 Layer 7（Engineering info）

與 Layer 3 同一驅動特徵之樣本統計，並附 `usl`、`lsl`、`selected_feature`、`stencil_thickness`（自 `workorder_master`）。

## 14.8 製程診斷組合證據矩陣（`diagnostic_evidence_matrix`）

`payload["diagnostic_evidence_matrix"]` 為診斷 UI、Excel 與 PPTX 共用的組合判讀契約。此層只彙整既有 chart payload、`statistical_signals`、`dashboard_layers` 與篩選上下文，不重新計算 SPC/能力公式。

核心欄位：
- `schema_version`
- `selected_features`, `selected_feature_count`
- `filter_scope`: batch/refdes/part_type/product/time/line 與 `scope_zh`
- `coverage`: `candidate_count`, `applicable_candidate_count`, `covered_candidate_count`, `coverage_pct`, `availability_counts`
- `combination_summary`: `1F charts × features + 2F charts × feature pairs + 3F charts × triple set` 之候選計數
- `candidates`: 每筆含 `feature_set`, `chart_id`, `chart_family`, `availability`, `evidence_dimension`, `severity`, `relevance`, `payload_path`
- `evidence_matrix`: 圖表族群 × 異常維度之 `support/refute/neutral/unavailable`
- `relation`: 由矩陣支持訊號推導的多圖表關聯、原因假設與檢查項
- `summary`: 結論、信心、top evidence、衝突證據、下一步圖表
- `tabs`: legacy/fallback 固定分頁資料，保留既有 key/shape 以維持相容

可用狀態固定為 `analyzed / available-not-selected / unavailable / not-applicable / missing-data`。`not-applicable` 代表特徵數不適用，不得作為異常或正常證據；`missing-data` 與 `unavailable` 必須揭露原因，不得默認為正常。

呈現層以 `app.services.diagnostic_evidence_matrix.build_readable_diagnostic_tabs(matrix)` 作為 UI、Excel 與 PPTX 的主要文字來源。此 helper 不改變上述 payload key/shape，也不改變內部 `support/refute/neutral/unavailable` 狀態；只將可見列轉為固定欄位 `title`、`result_zh`、`reason_zh`、`evidence_zh`、`next_action_zh`、`source_zh`。可見文字不得只輸出孤立狀態碼，例如 `refute` 應顯示為「不支持此假設」，`unavailable/missing-data` 應顯示為「資料不足/不可判讀」，並需附證據來源與下一步。

# 15. 工程報告匯出契約（PPTX only）

報告介面輸入：
- `template_type`：僅 `engineering`（服務層一律以此解析；舊呼叫端傳入其他值時仍視為工程報告）
- `chart_ids_to_export: List[str]`（可由 UI 微調勾選）

工程報告預設圖表 ID 清單（現行）：
- `imr`, `xbar_r`, `run_chart`, `ewma`, `cusum`, `histogram_spec`, `boxplot`, `normality`, `ooc_analysis`, `shift_detection`, `drift_detection`, `pattern_recognition`, `pareto`, `repeated_offender`, `spatial_heatmap`, `correlation_heatmap`

限制：
- UI 不提供 HTML 匯出入口。
- 當診斷條目對應圖表不在匯出勾選清單時，診斷條目保留，但 `chart_bytes = null`，並於 `chart_missing_reason` 標示未納入匯出清單。
- 報告維持核心工程章節骨架；製程診斷架構頁與多訊號診斷頁會同步呈現 `diagnostic_evidence_matrix` 的組合覆蓋、白話證據列與關聯判讀；若 `chart_ids_to_export` 中有可渲染圖表，會在第 8 節後追加 `5A. Chart Evidence Gallery`（2x2 版面，可多頁）。

# 16. 介面互動內部契約（Chart / Report UI-local）

本節為 UI 內部狀態契約，供頁面元件共享，不改變對外 analytics/report API。

## 16.1 ChartAnalysisPage state model

- `active_features: List[str]`
  - 來源：`_display_features` 與目前頁籤（1F/2F/3F）切片結果。
- `selected_chart_ids: List[str]`
  - 來源：目前 selector 勾選。
- `autoswitch_reason: str`
  - 觸發：特徵數切換導致原圖不相容，系統自動改選相容圖時寫入。
- `render_status: Dict[chart_id, {status, reason}]`
  - `status in {Ready, Incompatible, NoData, Error}`
  - 用於圖卡標籤與缺圖可解釋性。

## 16.2 ReportExportPage 圖表勾選（UI-local）

- 首次載入：以工程報告建議圖表 ID 為預設勾選（依資料可視性啟用／停用 checkbox）。
- 產生預覽：若某圖表已不可選，自動取消勾選；其餘手動勾選保留。
- 預覽補充欄位：匯出範圍摘要（已選/可用/不相容 + 建議未選示例）。
