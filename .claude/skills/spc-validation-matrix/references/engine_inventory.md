# Engine Inventory — `spc-validation-matrix`

依 `app/analytics/chart_registry.py::CHART_CATALOG` 為單一事實來源。本檔僅整理閱讀用對照,實際清單由 `matrix_builder.list_engines()` 在 runtime 從 catalog 拉。

## 33 個 chart_id 與必需特徵數

| arity 桶 | chart_id | required | 備註 |
|---|---|---|---|
| **single (n=1)** | `imr` | 1 | 個別值與移動極差圖 |
| | `xbar_r` | 1 | Xbar-R 管制圖 |
| | `run_chart` | 1 | 趨勢圖 |
| | `ewma` | 1 | EWMA |
| | `cusum` | 1 | CUSUM |
| | `subgroup` | 1 | 子群比較 |
| | `repeated_offender` | 1 | 重複異常點 |
| | `spatial_heatmap` | 1 | 空間熱圖(需座標) |
| | `pareto` | 1 | 柏拉圖 |
| **single-or-more (1..N)** | `histogram_spec` | ≥1 | 分布與能力(MULTI_FEATURE_FAMILIES) |
| | `boxplot` | ≥1 | 箱型圖 |
| | `normality` | ≥1 | 常態分析 |
| | `density` | ≥1 | 密度圖 |
| | `anova_parttype` | ≥1 | ANOVA |
| | `ooc_analysis` | ≥1 | 失控分析 |
| | `shift_detection` | ≥1 | 偏移偵測 |
| | `drift_detection` | ≥1 | 漂移偵測 |
| | `outlier_analysis` | ≥1 | 離群分析 |
| | `pattern_recognition` | ≥1 | 規則辨識 |
| **dual-or-more (≥2)** | `scatter_spec` | ≥2 | 散點+規格區 |
| | `correlation_matrix` | ≥2 | 關聯矩陣 |
| | `correlation_heatmap` | ≥2 | 關聯熱圖 |
| **dual (n=2)** | `quadrant` | 2 | 四象限 |
| | `bivariate_outlier` | 2 | 雙變量離群 |
| **triple (n=3)** | `anomaly_3f` | 3 | 三特徵異常分數 |
| | `consistency_3f` | 3 | 多特徵一致性 |
| | `parallel_coord` | 3 | 平行座標 |
| | `pass_fail_matrix` | 3 | 過關/失敗矩陣 |
| | `imr_3f` | 3 | 三特徵 I-MR 並列 |
| | `run_chart_3f` | 3 | 三特徵趨勢並列 |
| | `ewma_3f` | 3 | 三特徵 EWMA 並列 |
| | `cusum_3f` | 3 | 三特徵 CUSUM 並列 |
| | `boxplot_3f` | 3 | 三特徵箱型概覽 |

合計 33 個 chart_id;各桶大小:single=9、1..N=10、dual+=3、dual=2、triple=9。

## arity 相容判斷

由 [scripts/matrix_builder.py](../scripts/matrix_builder.py) `_arity_compatible(chart_id, entry, arity)`:

```
chart_id ∈ MULTI_FEATURE_FAMILIES        → arity ≥ 1
chart_id ∈ DUAL_AT_LEAST_TWO             → arity ≥ 2
otherwise                                → arity == required_feature_count
```

## 與 chart_registry 同步

新增/移除 engine 時:**不需要改本檔**(資訊只是輔助閱讀),但需確認 `chart_registry.CHART_CATALOG` 與 `MULTI_FEATURE_FAMILIES` / `DUAL_AT_LEAST_TWO` 兩個集合是否需要更新。matrix_builder 從 catalog 讀,所以新 chart_id 自動納入掃描。

## 已知不會被矩陣覆蓋的情境

- 沒有 `coords` 欄位的 fixture(例如 `no_coords`)→ `spatial_heatmap` 必然 SKIP
- 沒有 `PartType` 欄位的 fixture → `pareto` / `pass_fail_matrix` / `anova_parttype` 多半會 `is_valid=False`(這仍是契約 PASS,不是 FAIL)
- 沒有 `BoardNo`/`PanelId` 欄位 → 時序類圖表會 fallback 為依索引序
