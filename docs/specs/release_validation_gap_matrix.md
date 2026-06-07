# Release validation — Step 2：缺口矩陣（A–P + 橫切）

對照計畫模組編號與 **目前** `tests/release_validation` + 橫切政策覆蓋狀態。狀態：`Y` 已有對應測試、`P` 部分（煙霧或單一路徑）、`N` 未納入本 pack、`ext` 由 repo 其他測試／閘門涵蓋。

| 模組 | 意義（計畫） | 狀態 | 主要落點 |
|------|----------------|------|----------|
| **A** | data_contract | **Y** | `test_data_contract_golden.py`（golden CSV／join）；**ext** `tests/test_data_contract_code_alignment.py`（`SchemaMapper` 別名與 `ORDER_COL_PRIORITY` 對齊契約表）；**匯入欄位／缺欄／編碼** 見 `tests/test_measurement_loader_column_contract.py`；完整敘述見 `docs/specs/data_contract.md` |
| **B** | spec_stencil | **Y** | `partial_spec`、`test_partial_spec_golden.py`；**階梯鋼板** resolver 見 `test_spec_stencil_stepped_resolver.py`（mock）；**SQLite 端到端**（`save_spec`／`save_assignments`／`resolve_workorder_spec`）見 **ext** `tests/test_spec_resolver_master_db_e2e.py`（`SPC_MASTER_DB_PATH` 子程序隔離 DB）；**CSV golden + 主 DB + 分析 payload** 同路徑見 `tests/test_golden_csv_master_db_analysis_e2e.py` |
| **C** | statistical | Y | `test_non_computable_golden.py`、`test_phase1_infrastructure.py`（volume 統計 vs manifest）、payload／summary |
| **D** | spc_rules 對齊 | **Y** | `test_spc_rules_release_authority.py`（檔案／錨點）+ **`test_spc_rules_numeric_contract.py`**（I-MR **d2**、Cpk CI **z₀.₉₇₅**、Cp **6σ**／**3σ** 單側、**Xbar-R** A2/D3/D4 表、N&lt;10 語意與 `StatisticalUtils`）+ `test_step4_tolerance_policy_coverage.py` + 不可算 golden；**全文公式證明**仍以 `docs/governance/SPC_RULES.md` 為準，測試鎖**已寫死數值與表** |
| **E** | chart_registry | Y | `test_resolve_chart_payload_*`、`test_chart_registry` 於 **ext** `tests/test_chart_registry_acceptance.py` |
| **F** | chart_integrity | Y | 與 E 併行：resolver parity、三特徵 `test_three_feature_golden.py` |
| **G** | transparency | Y | `test_chart_transparency_golden.py`（`get_payload_slice` 保留無效 SPC 之 metadata／error） |
| **H** | cache | Y | `test_cache_state_release_golden.py`（`_analysis_cache_key`、SessionStore 快取／clear） |
| **I** | state | Y | 同上（singleton 狀態與 golden 資料隔離） |
| **J** | report | Y | `test_report_pptx_golden_alignment.py` |
| **K** | export | Y | 同上（PPTX 匯出路徑） |
| **L** | dashboard_layers | Y | `test_dashboard_layers_alignment_golden.py`（KPI 與 per_measure／process 一致） |
| **M** | join | Y | `test_join_conservation_golden.py`（全匹配、**PanelId**、**部分未匹配** `partial_coord_match`、coords **重複 RefDes**） |
| **N** | feature 切換 | Y | `test_analysis_payload_golden.py` |
| **O** | spec 傳遞 | Y | `test_analysis_payload_golden.py` |
| **P** | perf gate | Y | `test_performance_regression.py`、`performance_baselines.json` |
| **TOL** | 數值容差 | Y | `golden_tolerance.json`、`helpers/tolerance.py` |
| **RNG** | 種子 42 | **Y** | `conftest.py`（`random`／`numpy` 種子 42）；`test_determinism_surface_release.py`（`app/` 禁止 `np.random`／`numpy.random`）；各 manifest `determinism.notes` + `engine_seed_params`（見 `test_manifest_release_contract.py`） |
| **12 scenarios** | 計畫 12 類情境 | **Y**（目錄數已 ≥12） | **13** 個 golden 目錄 + synthetic 100k（P）；擴充以別名／fallback／邊角為主 |

## 後續擴充（可選）

**單一收斂說明**（`release_check` 與全庫／ext 測試分工、可選 **`--with-release-ext`**、可選 B／A／RNG、SPC Xbar-R 表權威）：**`docs/open-questions.md` Watchlist #7**。
