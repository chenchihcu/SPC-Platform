# Release validation 覆蓋矩陣（Golden × 測試 × 閘門）

本檔對照 **`tests/release_validation/`** 與 repo 根目錄 **`golden_dataset/`** 的意圖，並標註自動化閘門入口。變更 golden 目錄、payload 契約或 `resolve_chart_payload` 行為時，應同步檢查此表與 `golden_dataset/README.md`。

- 資料流／**SPC_RULES** 與 **`golden_tolerance.json`**：`docs/specs/release_validation_data_flow_and_tolerance.md`
- **A–P** 缺口矩陣：`docs/specs/release_validation_gap_matrix.md`

## 1. 執行入口

| 入口 | 指令 | 產出 |
|------|------|------|
| 發行前精簡檢查 | `python scripts/release_check.py` | `Outputs/release/release_report.json` |
| 發行前檢查 + traceability ext | `python scripts/release_check.py --with-release-ext` | 同上（`release_ext_enabled` 為 true） |
| 最終稽核（含本 pack） | `python scripts/run_final_audit_suite.py --repo-root . --profile full` | `Outputs/final_audit/<timestamp>/` |
| 僅 pytest | `python -m pytest -q tests/release_validation` | （終端機） |

## 2. 情境 ↔ 測試對照

| 關注點 | Golden／資料情境 | 主要測試模組 |
|--------|------------------|--------------|
| 基礎設施（種子 42、tolerance 載入） | `golden_tolerance.json`、`normal_baseline` | `test_phase1_infrastructure.py` |
| Join 與列數／鍵守恆 | 含 coords 之 golden（含 `timestamp_alias`、`duplicate_refdes_coords`） | `test_join_conservation_golden.py` |
| Time／Timestamp／DateTime／`timestamp` 主鍵與時間篩選 | `time_only_measurements`、`timestamp_alias_measurements`、`datetime_alias_measurements`、`timestamp_lowercase_measurements` | `test_join_conservation_golden.py` |
| RefDes 尾碼 strip fallback | `refdes_suffix_strip_join` | `test_join_conservation_golden.py`、`test_phase1_infrastructure.py` |
| 座標檔重複 RefDes（第一列生效） | `duplicate_refdes_coords` | `test_join_conservation_golden.py`、`test_phase1_infrastructure.py` |
| Time 類欄位 volume 摘要 | `time_only_measurements`、`timestamp_alias_measurements`、`datetime_alias_measurements`、`timestamp_lowercase_measurements` join | `test_phase1_infrastructure.py` |
| 部分 RefDes 無座標（未匹配） | `partial_coord_match` | `test_join_conservation_golden.py`、`test_phase1_infrastructure.py` |
| 資料契約最低欄位（A） | 所有含 `measurements.csv` 之 golden | `test_data_contract_golden.py` |
| 資料契約別名／排序與程式一致（A，ext） | `docs/specs/data_contract.md` ↔ `SchemaMapper`、`ORDER_COL_PRIORITY` | `tests/test_data_contract_code_alignment.py`（全庫 pytest） |
| `compute_analysis_payload` 與 `compute_summary` 一致 | `normal_baseline`（join + spec） | `test_analysis_payload_golden.py` |
| 不可算：N&lt;10、σ=0 | `sample_lt_10`、`sigma_zero_constant` | `test_non_computable_golden.py` |
| 部分規格（僅 volume） | `partial_spec` | `test_partial_spec_golden.py` |
| 階梯鋼板規格解析（B，mock 主檔／指派） | （無獨立目錄） | `test_spec_stencil_stepped_resolver.py` |
| 階梯鋼板 SQLite 端到端（B，ext） | 暫存 DB（`SPC_MASTER_DB_PATH`） | `tests/test_spec_resolver_master_db_e2e.py`（全庫 pytest，非僅 release pack） |
| 無座標時 spatial 無效 | `no_coords` | `test_no_coords_spatial_golden.py` |
| `resolve_chart_payload` UI／report 一致（1F） | `normal_baseline` | `test_resolve_chart_payload_golden.py` |
| `resolve_chart_payload` UI／report 一致（2F：Volume+Area） | `normal_baseline` | `test_resolve_chart_payload_two_feature_golden.py` |
| `resolve_chart_payload` UI／report 一致（3F／平行圖） | `normal_baseline` join | `test_resolve_chart_payload_three_feature_golden.py` |
| 三特徵 payload 結構與引擎輸出 | `normal_baseline` join | `test_three_feature_golden.py` |
| PPTX 統計表與摘要數值對齊 | `normal_baseline` + `SessionStore` | `test_report_pptx_golden_alignment.py` |
| 效能回歸（P）：分段計時 vs baseline（單次；僅 near-boundary time fail 觸發補跑 2 次，以 3 次中位數判定） | `performance_baselines.json` + synthetic 100k | `test_performance_regression.py`、`test_performance_retry_policy.py` |
| Dashboard `layer_2_kpi` 與 `process`／`per_measure` 一致（L） | `normal_baseline` join | `test_dashboard_layers_alignment_golden.py` |
| 無效 SPC 時 payload slice 仍暴露 metadata（G） | `sample_lt_10` | `test_chart_transparency_golden.py` |
| 分析快取鍵／SessionStore clear（H+I） | `normal_baseline` join | `test_cache_state_release_golden.py` |
| manifest 契約（determinism、schema） | 各 `expected/manifest.json` | `test_manifest_release_contract.py` |
| 容差政策鍵完整（Step 4） | `golden_tolerance.json` | `test_step4_tolerance_policy_coverage.py` |
| **D** `docs/governance/SPC_RULES.md` 權威檔與維護規格錨點 | （無 golden） | `test_spc_rules_release_authority.py` |
| **D** 數值／常數表與引擎交叉檢查 | `docs/governance/SPC_RULES.md` 字面 + `xbar_r_engine` 表 | `test_spc_rules_numeric_contract.py` |
| **RNG** 無隱含 numpy 隨機、`determinism.notes` | 各 manifest、`app/` | `test_determinism_surface_release.py`、`test_manifest_release_contract.py`、`conftest.py` |

## 3. 刻意未納入（後續可擴充）

- **端到端 Qt／Playwright 互動**：由 `run_final_audit_suite` 的 `pytest_ui_runtime_pack` 等閘門涵蓋，不在 `tests/release_validation` 內。
- **完整 `pytest -q` 全庫**：CI 與 baseline 仍以全庫 pytest 為準；`release_check` 預設僅 `tests/release_validation`；**`--with-release-ext`** 再納入三個 traceability 測試（`release_report.json` 之 `release_ext_paths`）。
- **綜合收斂**（ext 測試、`release_check` 邊界、可選擴充項）：**`docs/open-questions.md` Watchlist #7**。

## 4. 維護觸發

- 新增 golden 子目錄：更新 `golden_dataset/README.md` 與**本檔 §2**。
- 新增 `resolve_chart_payload` 分支或圖表 ID：檢查 1F／2F／3F parity 測試是否需擴充參數列表。
