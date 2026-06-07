# Release validation — Step 1：資料流掛點與容差／SPC_RULES 對照

本檔對應發行驗證計畫 **G Step 1**：標出「一次分析 → 圖表 → 報表」主線上的程式掛點，並對照 **`docs/governance/SPC_RULES.md`** 與 **`golden_dataset/golden_tolerance.json`**（數值比對用，**不**取代 SPC_RULES 公式權威）。

權威順序見 **`docs/specs/spec_maintenance_and_alignment.md`**。

## 1. 主線掛點（驗證視角）

| 階段 | 模組／符號 | 角色 |
|------|------------|------|
| 座標／量測關聯 | `app.data.relation.join_engine.JoinEngine.join` | RefDes left merge、座標去重；**嚴格匹配率 &lt; 10%** 時對量測 RefDes 做 `[-_][0-9]+$` strip 再併（golden `refdes_suffix_strip_join`） |
| 摘要／Dashboard | `app.analytics.summary_engine.compute_summary` → `result["process"]["dashboard_layers"]` | `layer_1_alarm`、`layer_2_kpi`、`layer_3_info`、`per_feature_alarm`；`overall_yield_pct` 與 `layer_2_kpi["yield_pct"]` 同源 |
| 分析 payload | `app.viewmodels.chart_analysis_viewmodel.compute_analysis_payload` | 圖表與報表共用的純計算 payload；`payload["summary"]` 應與同條件 `compute_summary` 一致 |
| 圖表契約 | `app.analytics.chart_registry.resolve_chart_payload` | UI／report context 單一路徑解析 |
| 分析快取 | `app.data.session_store._analysis_cache_key`、`SessionStore._analysis_cache` | 維度：特徵、batch、refdes、part_type、product、time、line、`spec_version`（`spec_cache_token(workorder_spec)`） |
| 編排 | `app.services.analysis_orchestrator.AnalysisOrchestrator.prepare_refresh` | 命中快取時 `STATUS_CACHED` |
| 報表 | `app.services.report_service.ReportService.generate_pptx_report` → `pptx_report_builder.build_pptx_report` | PPTX 工程簡報 |

## 2. `golden_tolerance.json` 與 SPC_RULES 的關係

- **SPC_RULES**：定義 **公式、門檻、解讀**（例如能力指標定義、控制圖常數）。變更須先改 SPC_RULES，再動實作與測試期望。
- **golden_tolerance.json**：僅用於 **Golden／release_validation 自動比對** 時的 **浮點容差** 與 **整數嚴格相等** 清單，避免 CI 假陽／假陰；**不**定義新統計公式。

### 2.1 指標對照（摘要）

| `golden_tolerance.json` metrics 鍵 | 典型來源（摘要／引擎） | SPC_RULES 關聯（概念） |
|-----------------------------------|------------------------|-------------------------|
| `mean`, `std` | `distribution`／摘要統計 | 描述統計；容差 ±1e-6 |
| `cp`, `cpk`, `pp`, `ppk` | `capability_engine` | 能力指標定義見 SPC_RULES 能力章節；容差 ±0.001 |
| `yield_pct` | `per_measure`／`process` | 良率語意須與實作一致（0–1 或百分比）；容差 ±0.01（見政策檔） |
| `dpmo`, `sigma_level` | defect／zbench 衍生 | 對齊 SPC_RULES 缺陷／Sigma 敘述 |
| `percentile` | 分位數輸出 | ±0.5（政策檔） |
| `normality_pvalue` | `normality_engine` | ±0.01 |
| `cpk_ci` | Bissell 等 CI | ±0.01 |
| `histogram_bin_count` | 直方圖 | ±1 |
| `exact_integer_metrics`（`oos_count` 等） | OOS／join／列數 | **必須完全相等**，不容差 |

單一情境可於 `expected/manifest.json` 使用 **`tolerance_overrides`** 覆寫，並應註明理由（見計畫 F 節）。

## 3. Dashboard 鍵名（L 模組驗證用）

`compute_summary(..., ...)["process"]["dashboard_layers"]` 必含：

- `layer_1_alarm`：`ooc_rate`、`max_drift_ratio`、`anomaly_cluster_count`、`cpk_below_133_count` 等
- `layer_2_kpi`：`avg_cpk`、`avg_ppk`、`yield_pct`、`dpmo`、`sigma_level`
- `layer_3_info`：`driver_feature`、`sample_size`、`mean`、`std`、`range`
- `per_feature_alarm`：各量測之 `ooc_rate`、`ooc_count`、`sample_n`、CUSUM drift 等

實作細節以 `app/analytics/summary_engine.py` 為準。

## 4. 決定性（D.2 橫切）

- `tests/release_validation/conftest.py`：`random.seed(42)`、`numpy.random.seed(42)`。
- **D 數值契約**：`tests/release_validation/test_spc_rules_numeric_contract.py` 對 `docs/governance/SPC_RULES.md` 已明示之 **d2、Cpk CI z、Cp 6σ 分母** 與 **Xbar-R 因子表**（與 `xbar_r_engine`）做自動對照；變更常數須先改 `docs/governance/SPC_RULES.md` 再同步程式與測試期望。
- 涉及 BLAS 多執行緒時，Golden／P 量測建議在 **單執行緒** 或固定 thread 的環境執行，以降低時間漂移（非程式強制）。
- **`release_check` 與 ext／可選項**：預設僅 `tests/release_validation`；**`--with-release-ext`** 再跑三個 traceability 測試（報告欄位 `release_ext_paths`）。綜合收斂敘述：**`docs/open-questions.md` Watchlist #7**。
