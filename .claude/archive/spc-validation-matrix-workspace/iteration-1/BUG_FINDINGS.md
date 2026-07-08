# Bug findings — `spc-validation-matrix` iteration-1

從跑 iteration-1(372 cells × `normal_baseline`)挖出兩類 engine 真實問題。所有 cells 都對應到 `eval-1_happy_path/failures/*.json` 有完整 slice + cell 上下文。

---

## 🔴 Bug A — `DensityEngine.compute_univariate_density` 在退化資料 raise 例外

| 屬性 | 值 |
|---|---|
| 檔案 | [app/analytics/density_engine.py:41](../../../../app/analytics/density_engine.py) |
| Engine | `DensityEngine.compute_univariate_density` |
| 觀測影響範圍 | **34 cells / ERROR**;**top10pct filter 全部 33 個 chart_id 連帶被擊倒** |
| 嚴重度 | **HIGH**(任何單一特徵 series 的有效樣本進入低維子空間就會炸,跨整個 payload) |
| 違反項目 | analytics-engine-contract:engine 不應 raise,失敗時應返回 `is_valid=False, data={}, statistics={}` |

### 根因

```python
# app/analytics/density_engine.py:32-42
if len(valid) < 3:
    return {... "is_valid": False ...}
values = valid.to_numpy(dtype=float)
x_grid = np.linspace(float(np.min(values)), float(np.max(values)), points)
kde = stats.gaussian_kde(values)        # ← 沒守 np.std == 0 / 接近 0 / lower-dim 的 case
y_density = kde.evaluate(x_grid)
```

`scipy.stats.gaussian_kde` 對全相同值或近全相同值的 series 會丟 `numpy.linalg.LinAlgError: singular data covariance matrix`。`top10pct` filter 在常出現大量 ties 的數據(例如「Height 取頂 10%」很多剛好等於該分位點)會穩定觸發。

### 連動影響

`compute_analysis_payload` 在 single-feature 路徑會**對每個可用 feature** 預算所有 12 個 single-feature engines 包含 density(`chart_analysis_viewmodel.py::_build_feature_parameters`)。density 一炸,整個 `compute_analysis_payload` 拋例外,**所有** chart_id 在這個 (fixture, features, filter) 都被打成 ERROR — 不只 density 本身。

### 建議修法

於 [density_engine.py](../../../../app/analytics/density_engine.py) 第 32-38 行的 guard 後追加:

```python
if not np.isfinite(values).all() or float(np.std(values)) < 1e-12:
    return {
        "chart_type": "Density",
        "data": {},
        "statistics": {},
        "metadata": {"is_valid": False, "error": "資料變異不足,無法估計密度。"},
    }
```

或更保險:把 `gaussian_kde` 包進 try/except `linalg.LinAlgError` → 返回契約 `is_valid=False`。

雙重防線最穩。

### 回歸測試

- 加入 fixture / case:全等值 series(np.full(50, 5.0))→ 期望 `is_valid=False, data={}`
- 加入 fixture / case:接近共線(values + tiny noise)→ 期望 `is_valid=False, data={}`
- 修完後再跑一次 `python .claude/skills/spc-validation-matrix/scripts/run_matrix.py --fixture normal_baseline`,確認 ERROR count 從 34 → 0

---

## 🟡 Bug B — `anova_parttype` 與 `drift_detection` 失敗時 `data` 沒清空

| 屬性 | 值 |
|---|---|
| 檔案 | [app/analytics/anova_engine.py](../../../../app/analytics/anova_engine.py)、[app/analytics/analysis_cards_engine.py](../../../../app/analytics/analysis_cards_engine.py)(`drift_detection`) |
| 觀測影響範圍 | **24 cells / FAIL**(anova_parttype: 14、drift_detection: 14;有重疊) |
| 嚴重度 | **MEDIUM**(契約違反,UI/report 路徑可能誤判) |
| 違反項目 | analytics-engine-contract:`is_valid=False` 時 `data` 與 `statistics` MUST be `{}` |

### 根因 1 — `anova_parttype`

從 [eval-1_happy_path/failures/anova_parttype__1f__Volume__top10pct__normal_baseline.json](eval-1_happy_path/failures/anova_parttype__1f__Volume__top10pct__normal_baseline.json) 可見:

```json
{
  "chart_type": "ANOVA",
  "data": {
    "group_labels": [],
    "n_by_group": [],
    "mean_by_group": []
  },
  "statistics": {},
  "metadata": {
    "is_valid": false,
    "error": "有效分組不足（至少需 2 組且每組 >= 2 筆）。"
  }
}
```

問題點:`data` 是**含三個空陣列的 dict**,不是 `{}`。

### 根因 2 — `drift_detection`

從 [eval-1_happy_path/failures/drift_detection__1f__Volume__top10pct__normal_baseline.json](eval-1_happy_path/failures/drift_detection__1f__Volume__top10pct__normal_baseline.json):

```json
{
  "chart_type": "DriftDetection",
  "data": {
    "summary_lines": ["EWMA data: UNKNOWN/VERIFY"]
  },
  "statistics": {},
  "metadata": {
    "is_valid": false,
    "error": "缺少 EWMA 資料。"
  }
}
```

`data` 留了 `summary_lines`。

### 建議修法

兩個 engine 都應改用 `_invalid()` helper(或等價的字面 dict)在失敗 path:

```python
def _invalid(chart_type: str, error: str) -> dict:
    return {
        "chart_type": chart_type,
        "data": {},
        "statistics": {},
        "metadata": {"is_valid": False, "error": error},
    }
```

定位行:
- `app/analytics/anova_engine.py::compute_one_way` — 在「有效分組不足」guard 後返回上面的 `_invalid("ANOVA", "...")`
- `app/analytics/analysis_cards_engine.py` 的 drift_detection 卡片產生函式 — 把 `summary_lines` 等資訊改放 `metadata.error` 或保留欄位但同時清空 `data`

### 回歸測試

修完後預期:
- 全 372 cells 的 PASS 比例從 84.4% → ≥ 99%(若 Bug A 同時修則應接近 100%)
- 「contract: On failure data must be {}」這串 error 從 matrix.csv 消失

---

## ⚪ 非 bug,但可考慮的 follow-up

### F1 — IMR slice 的 schema 與其他 chart 不同

`chart_registry.py::get_feature_payload_slice` 對 `chart_id == "imr"` 的特殊路徑:回傳整個 payload(把 `spc/cap/dist` 灌進去),而不是 engine result(`{chart_type, data, statistics, metadata}`)。

我已在 skill 的 `engine_invoker.check_data_renderability()` 處理(允許 composite slice 的 `data` 為空),但 `analytics-engine-contract` skill 的契約沒提到「resolved slice 與 engine result 不同」。建議:在 `analytics-engine-contract/SKILL.md` 加一節「Resolved slice 形式」說明 IMR 等 chart 的 slice 是 payload-shaped。

### F2 — `compute_analysis_payload` 沒 isolate engine 失敗

目前 `compute_analysis_payload` 任一個內部 engine 拋例外都會把整個 payload-build 失敗。理想行為是:單一 engine 失敗時 catch 並把該 engine 的 slot 設為 contract-compliant invalid,不影響其他 engine。

修這個會大幅減少跨 chart 連帶失敗(Bug A 之所以擊倒 33 個 chart 就是這個原因)。

---

## 修復後驗證指令

每修一個 engine 後跑:

```bash
# 全 sweep,確認 PASS 比例上升
python .claude/skills/spc-validation-matrix/scripts/run_matrix.py --fixture normal_baseline

# Density 退化資料專項
python .claude/skills/spc-validation-matrix/scripts/run_matrix.py --fixture normal_baseline --filters top10pct --engines density --arities 1

# Anova / drift 契約專項
python .claude/skills/spc-validation-matrix/scripts/run_matrix.py --fixture normal_baseline --engines anova_parttype,drift_detection --arities 1
```

理想:三條命令的 SUMMARY 都顯示 0 FAIL / 0 ERROR。
