# Golden dataset (system baseline)

Canonical location: **repository root `golden_dataset/`** (single source of truth). Pytest resolves this via `tests/release_validation/conftest.py` or env **`GOLDEN_DATASET_ROOT`**.

- **`golden_tolerance.json`** — default numeric tolerances; scenarios may set `tolerance_overrides` in `expected/manifest.json`.
- **`performance_baselines.json`** — performance regression gate (P): reference timings for `synthetic_large_100k` (concat `normal_baseline` to 100k rows). Refresh with `python scripts/record_performance_baseline.py`. Set `performance_gate.skip` to `true` or env `RELEASE_PERF_GATE=0` to skip the gate locally.
- **`normal_baseline/`** — 10 筆量測、`coords.csv`（R1/R2）、`workorder_spec.json`、join 與 volume 期望（`expected/manifest.json`）。
- **`sample_lt_10/`** — 7 筆（N&lt;10），用於 SPC / capability 不可算驗證。
- **`sigma_zero_constant/`** — 12 筆常數 Volume，σ=0 不可算驗證。
- **`partial_spec/`** — 僅 `volume` 規格；Area/Height 無 spec（summary／parameters 退化）。
- **`no_coords/`** — 與 normal 相同量測但無 X/Y（未 join 座標），spatial 應無效。
- **`panel_id_instead_of_board/`** — 與 `normal_baseline` 相同數值網格，但量測檔以 **`PanelId`** 取代 `BoardNo`（對照 `docs/specs/data_contract.md` 之 Board／Panel 別名）；join／summary 與 normal 對齊。
- **`time_only_measurements/`** — 同網格但**無** `BoardNo`／`PanelId`，以 **`Time`** 滿足資料契約；`detect_order_col` 應為 `Time`；manifest 含 `time_filter_probe` 供 `filter_analysis_df` 時間區間測試。
- **`timestamp_alias_measurements/`** — 與 `time_only_measurements` 相同數值與時間序列，欄位名為 **`Timestamp`**（`docs/specs/data_contract.md`／`ORDER_COL_PRIORITY` 別名路徑）。
- **`duplicate_refdes_coords/`** — 量測同 `normal_baseline`；**座標檔中 `R1` 重複兩列**（第二列為假的大座標），驗證 JoinEngine **`drop_duplicates(RefDes)` 保留第一列**，量測列數不爆炸。
- **`datetime_alias_measurements/`** — 與 time-only 網格相同，時間欄名為 **`DateTime`**（`ORDER_COL_PRIORITY`／篩選別名）。
- **`partial_coord_match/`** — 前 10 筆同 normal，另 2 筆 **`R99` 無座標列**；join 報告 **match 10 / unmatch 2**，未匹配列 **X/Y 為 NaN**（左連接保留量測）。
- **`timestamp_lowercase_measurements/`** — 與 time-only 網格相同，時間欄名為小寫 **`timestamp`**。
- **`refdes_suffix_strip_join/`** — 量測 **RefDes 為 `R1_1`／`R2_1`**，座標仍為 **R1／R2**；觸發 JoinEngine **尾碼 strip fallback** 後 10/10 匹配且 X/Y 正確。
- **三特徵分析**：無獨立資料夾；測試使用 **`normal_baseline` join 後** 呼叫 `compute_analysis_payload(..., ["Volume","Area","Height"], ...)`。
- **雙特徵 resolver**：同樣使用 **`normal_baseline` join**；`tests/release_validation/test_resolve_chart_payload_two_feature_golden.py` 以 `["Volume","Area"]` 組裝 payload 後驗證 `resolve_chart_payload` 的 UI／report 一致性。

Keep fixtures small and non-sensitive; prefer deterministic CSV over generated blobs.

覆蓋矩陣（情境 ↔ 測試 ↔ 閘門）：`docs/specs/release_validation_coverage.md`。**資料契約別名／排序** 與 `SchemaMapper`／`ORDER_COL_PRIORITY` 之靜態對照見全庫測試 `tests/test_data_contract_code_alignment.py`。

**計畫對照文件**：資料流／容差與 SPC_RULES → `docs/specs/release_validation_data_flow_and_tolerance.md`；A–P 缺口矩陣 → `docs/specs/release_validation_gap_matrix.md`。

**情境目錄**：目前 **13** 個 CSV golden 目錄（見上列）；**階梯鋼板**：`tests/release_validation/test_spec_stencil_stepped_resolver.py`（mock 主檔）；真 **`save_spec`／`save_assignments`／SQLite** 路徑見 **`tests/test_spec_resolver_master_db_e2e.py`**（環境變數 **`SPC_MASTER_DB_PATH`** 指向暫存檔，子程序隔離）。其餘 roadmap（大量級匯入、多工單等）可再擴充。
