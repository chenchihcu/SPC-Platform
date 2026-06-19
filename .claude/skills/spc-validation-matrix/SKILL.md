---
name: spc-validation-matrix
version: 1.0.0
description: SPC/SPI Platform v2 跨組合整合驗證器 — 一次同時驗證圖表輸出、函數定義、統計數據、報告匯出在所有合理特徵組合下都正確,並且大量組合下不會停滯或超出系統計算負荷。Use this skill 當使用者要做交叉驗證、組合驗證、cross validation matrix、驗證所有 engine、圖表/統計/匯出整合驗證、確認大量組合下不會 stall、或在 release 前/合併新 engine 後做整體 sanity sweep。觸發詞包含「交叉驗證」「組合驗證」「驗證所有圖表」「跨特徵驗證」「stall test」「matrix validation」「regression sweep」。
type: validation
compatibility:
  python: ">=3.10"
  requires:
    - pandas
    - numpy
    - matplotlib
    - python-pptx
    - openpyxl
---

# spc-validation-matrix

跨組合整合驗證器。**Headless programmatic** — 不啟動 PySide6 UI,直接對 `compute_analysis_payload` + `chart_registry.resolve_chart_payload` + `build_pptx_report` + `export_diagnostic_summary_xlsx` 進行掃描。

## 何時觸發

- 新增或修改 analytics engine
- 改 `chart_router.py` / `chart_registry.py` 的特徵分派
- 改 `app/services/report_service.py` 或 PPTX/Excel exporter 的契約
- Release 前的整體 sanity sweep
- 使用者直接要求「驗證所有組合」「跨特徵驗證」「matrix validation」

## 何時不要觸發

- 單一 engine 的 contract 細節 → 用 `analytics-engine-contract` skill
- UI 操作層的 E2E 測試 → 用 `qa-auto-engineer` skill
- 像素級的圖表 baseline diff → 不在範圍內,改用 `tests/baseline_images/`

## 矩陣維度

| 維度 | 取值 |
|---|---|
| `fixture` | `golden_dataset/` 下任一目錄,預設 `normal_baseline` |
| `arity` | 1 / 2 / 3(從 `chart_registry.CHART_CATALOG[*].required_feature_count` 推得) |
| `features` | `Volume / Area / Height` 的 C(3,arity) 組合 |
| `chart_id` | `chart_registry.CHART_CATALOG` 全部 33 個 id;可用 `--engines` 子集 |
| `filter` | `full / top10pct / by_part_type / by_board` |

## 執行流程(每個 cell)

1. **載入 payload**(以 `(fixture, features, filter)` 為鍵快取)
   `compute_analysis_payload(filtered_df, features, usl, lsl, target, workorder_spec=spec)`
2. **解析 chart slice**
   `chart_registry.resolve_chart_payload(payload, chart_id, features=features)`
3. **契約檢查** — `tests/helpers/engine_contract.py::assert_engine_contract(slice, expect_valid=slice["metadata"]["is_valid"])`
4. **統計合理性** — `is_valid=True` 時 `data` 與 `statistics` 不可空、`statistics` 內所有 float 值不可 NaN/Inf;`is_valid=False` 時 `data == {} and statistics == {}` 且 `metadata.error` 非空(契約已涵蓋)
5. **圖表可渲染性** — 將 slice 餵 matplotlib `Figure.canvas.draw()` 一次(不存檔),確保 `data` 結構不致觸發 plot exception
6. **效能護欄** — `perf_monitor.run(fn, args, timeout=THRESHOLD_PER_ENGINE_S, peak_mb=THRESHOLD_PEAK_MB)`;timeout → `STALL`,memory → `OVERLOAD`
7. **記錄一列** → `matrix.csv`

匯出驗證(每個 fixture × 每個 arity 各跑一次,不每 cell 跑):
- `build_pptx_report(...)` → 確認檔案存在且 slide ≥ 1
- `export_diagnostic_summary_xlsx(...)` → 確認檔案存在且 sheet ≥ 1

## CLI

```bash
python .claude/skills/spc-validation-matrix/scripts/run_matrix.py \
    --fixture normal_baseline \
    [--engines imr,histogram_spec,scatter_spec,anomaly_3f,...] \
    [--features Volume,Area,Height] \
    [--filters full,top10pct,by_part_type] \
    [--arities 1,2,3] \
    [--output Outputs/cross_validation_<auto_timestamp>] \
    [--skip-export]              # 跳過 PPTX/XLSX 匯出驗證
    [--quick]                    # 等同 --filters full --arities 1,2,3 (~200 cells)
```

預設不傳任何旗標時:
- `fixture = normal_baseline`
- 全部 35 engines
- `features = Volume,Area,Height`
- `filters = full,top10pct,by_part_type`
- `arities = 1,2,3`

## 效能門檻

預設值寫死在 `references/thresholds.md`,可被環境變數覆寫:

| 門檻 | 預設 | 環境變數 |
|---|---|---|
| 單 cell timeout | 30 s | `SPC_VALIDATION_ENGINE_TIMEOUT_S` |
| 單 cell peak memory | 2048 MB | `SPC_VALIDATION_ENGINE_PEAK_MB` |
| 全矩陣 wall-clock | 600 s | `SPC_VALIDATION_MATRIX_TIMEOUT_S` |

讀取細節見 [references/thresholds.md](references/thresholds.md)。

## 輸出規格

`Outputs/cross_validation_YYYYMMDD_HHMM/`

- **`matrix.csv`** — 每 cell 一列。欄位:
  `fixture, arity, features, chart_id, filter, status, duration_ms, peak_mb, contract_ok, stats_ok, chart_render_ok, export_ok, error`
- **`SUMMARY.md`** — 統計總覽:PASS / FAIL / STALL / OVERLOAD / SKIP 計數、按 chart_id 失敗 top 10、按 fixture 失敗熱區、超時 cell 列表、整體 wall-clock。
- **`failures/<chart_id>__<arity>__<filter>.json`** — 失敗 cell 的 slice + traceback,方便人工 debug。
- **`exports/<fixture>__<arity>.pptx`** + **`.xlsx`** — 匯出驗證的實檔(若 `--skip-export` 則不產生)。

`status` 取值:

| status | 觸發條件 |
|---|---|
| `PASS` | 契約 + 統計 + 圖表渲染 + 匯出 全綠 |
| `FAIL` | 任一檢查失敗(契約違反、NaN/Inf、render exception 等) |
| `STALL` | 單 cell 執行時間超過 timeout |
| `OVERLOAD` | tracemalloc peak 超過 `peak_mb` |
| `SKIP` | fixture 不滿足前置條件(例如 `no_coords` 跑 spatial_heatmap) |

## 如何解讀結果

1. **看 SUMMARY.md 的「Overall」段** — PASS 比例 ≥ 95% 是健康基線
2. **看「Top failing chart_ids」** — 連續多個 fixture 都掛同一 chart 表示 engine 本身有 bug,而非 fixture 退化
3. **看「STALL cells」** — 同一 chart 在多個 fixture 都 STALL 表示 engine 有 O(N²) 以上的演算,要找演算複雜度
4. **看 `failures/*.json`** — 把 `slice["metadata"]["error"]` 對應到原始 engine 的 `_invalid()` 訊息,定位 guard

## 常見失敗模式 → 排查方向

| 觀察到的 status / 訊息 | 第一懷疑對象 |
|---|---|
| `FAIL` + `error="缺少欄位"` | `compute_analysis_payload` 沒把該特徵欄位納入,檢查 `SPEC_KEY_BY_COL` |
| `FAIL` + 契約違反(`is_valid=True` 但 `data={}`)| Engine `_invalid()` 與成功路徑混雜,看 `app/analytics/<engine>.py` |
| `FAIL` + `metadata.error == ""` 但 `is_valid=False` | 契約 violation:錯誤訊息漏填 |
| `STALL` 集中在 `parallel_coord` / `correlation_heatmap` | Triple-feature 引擎在大資料量下退化,確認是否有 sampling |
| `OVERLOAD` 集中在 `spatial_heatmap` | 高解析度 heatmap 沒做 downsample |
| 匯出驗證 FAIL 但 cell 全 PASS | `build_pptx_report` 在 `analysis_payload=None` fallback 出錯,或 `chart_ids_to_export` 包含未計算的 id |

## 重用的既有元件

| 用途 | 檔案 |
|---|---|
| 契約檢查 | `tests/helpers/engine_contract.py::assert_engine_contract` |
| Wall-clock 計時 | `tests/helpers/perf_timing.py::measure_wall_seconds` |
| Fixture 載入 | `tests/release_validation/helpers/golden_scenario.py` |
| 三特徵 payload | `tests/release_validation/helpers/three_feature_payload.py` |
| Payload 計算 | `app/viewmodels/chart_analysis_viewmodel.py::compute_analysis_payload` |
| Slice 解析 | `app/analytics/chart_registry.py::resolve_chart_payload` |
| Engine 列表 | `app/analytics/chart_registry.py::CHART_CATALOG` |
| 匯出 PPTX | `app/services/pptx_report_builder.py::build_pptx_report` |
| 匯出 XLSX | `app/services/diagnostic_excel_exporter.py::export_diagnostic_summary_xlsx` |

## 引擎清單

完整 33 個 chart_id 與 required_feature_count 對照,見 [references/engine_inventory.md](references/engine_inventory.md)。

## 延伸閱讀

- 契約細節:`.claude/skills/analytics-engine-contract/SKILL.md`
- UI 層 E2E:`.claude/skills/qa-auto-engineer/SKILL.md`
