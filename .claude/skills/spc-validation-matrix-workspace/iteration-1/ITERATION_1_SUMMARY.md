# Iteration 1 — `spc-validation-matrix` skill

執行日期:2026-04-30
範圍:四個 eval prompt 各跑一次,確認 skill 在每個情境下行為符合預期。

## 結果一覽

| Eval | Cells | Wall-clock | 結論 |
|---|---:|---:|---|
| 1. happy_path_normal_baseline | 372 | 3.0 s | ✅ skill 完整收尾;查到兩類 engine bug(見 BUG_FINDINGS.md) |
| 2. subset_dual_with_short_timeout | 3 | 0.1 s | ✅ env timeout 生效、只跑指定 engine、全 PASS |
| 3. degenerate_fixtures_keep_contract | 18 | 0.7 s | ✅ sigma_zero_constant 全 PASS(契約守住);partial_spec 6 cells ERROR(spec 缺欄,合理) |
| 4. watchdog_catches_stall | 1 | 10.0 s | ✅ STALL section 出現,wall-clock = timeout × 5,daemon thread 沒卡死主程序 |

## 各 eval 詳細

### Eval 1 — Full sweep on `normal_baseline`

```
372 cells | 3.0 s | PASS 314 (84.4%) | FAIL 24 | ERROR 34
```

- 33 chart_id × 1/2/3 arity × 3 filter
- PASS 比例 84.4% 不是因為 skill 本身有問題,而是揪到了 engine 兩類契約違反(下一節)
- 0 STALL / 0 OVERLOAD,效能護欄沒誤殺
- 匯出驗證:PPTX (3 個) + XLSX (3 個) 全 parse 過

### Eval 2 — Subset with short timeout

```
3 cells | 0.1 s | PASS 3 | FAIL 0
```

- `--engines scatter_spec,quadrant,bivariate_outlier --features Height,Volume --filters full --arities 2`
- `SPC_VALIDATION_ENGINE_TIMEOUT_S=10` env 生效(印出 `per_cell=10.0s`)
- 只跑指定的 3 engine、單一 features pair、單一 filter,精準裁剪

### Eval 3 — Degenerate fixtures

```
18 cells | 0.7 s | PASS 12 | ERROR 6
```

- `sigma_zero_constant`:9 cells 全 PASS
  - 確認 SPC / Histogram / Boxplot 對 σ=0 退化資料返回 `is_valid=False, data={}, statistics={}` 是契約 PASS,不是 FAIL
- `partial_spec`:6 cells ERROR(`workorder_spec missing usl/lsl/target for Area/Height`)
  - 這是 fixture 故意只給 Volume 規格,Area/Height 沒得跑 → engine_invoker 在 payload-build 前就以 ERROR 回收,合理

### Eval 4 — Watchdog stall detection

```
1 cell | 10.0 s | PASS 0 | FAIL 0 | STALL 1
```

- monkey-patch `compute_analysis_payload` 改成 `time.sleep(60)`
- `SPC_VALIDATION_ENGINE_TIMEOUT_S=2` → effective 10 s(payload 預算 = 2 × 5)
- watchdog 在 10 s 命中,thread 是 daemon,主程序 0 殘餘
- SUMMARY.md 正確產生 `## STALL cells` 段落
- 整體 wall-clock = 10.0 s,遠低於 mock 的 60 s

## 對 skill 本身的判斷

- 4 個 eval 全達成預期
- 不需 iteration-2;skill 已可投入使用
- 兩類 engine bug 屬於「skill 找出真正問題」的成功案例,**不是 skill 缺陷**

## 工作目錄產物

```
spc-validation-matrix-workspace/iteration-1/
├── ITERATION_1_SUMMARY.md          ← 本檔
├── BUG_FINDINGS.md                 ← engine bug 清單(下一階段任務)
├── eval-1_happy_path/              ← 372 cells 的 matrix.csv + SUMMARY.md + failures/ + exports/
├── eval-2_subset_short_timeout/    ← 3 cells
├── eval-3_degenerate_fixtures/     ← 18 cells
├── eval-4_watchdog_stall/          ← 1 STALL cell
└── eval-4_watchdog_stall.py        ← monkey-patch 驅動腳本
```
