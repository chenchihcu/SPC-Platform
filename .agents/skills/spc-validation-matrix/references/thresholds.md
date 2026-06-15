# Thresholds — `spc-validation-matrix`

預設值寫死在 [scripts/run_matrix.py](../scripts/run_matrix.py),可被環境變數覆寫。沒設環境變數時就用 default。

| 門檻 | 預設值 | 環境變數 | 說明 |
|---|---|---|---|
| 單 cell timeout | `30 s` | `SPC_VALIDATION_ENGINE_TIMEOUT_S` | 單一 payload-build 的 wall-clock 上限。實際 timeout 會放大 5×(因為 `compute_analysis_payload` 內含多個子 engine);超過則整個 payload 標 STALL,該 (fixture, features, filter) 下所有 chart cell 連帶標 STALL |
| 單 cell peak memory | `2048 MB` | `SPC_VALIDATION_ENGINE_PEAK_MB` | tracemalloc.get_traced_memory peak;超過則標 OVERLOAD |
| 全矩陣 wall-clock | `600 s` | `SPC_VALIDATION_MATRIX_TIMEOUT_S` | 跨所有 cells 的硬上限;超過後剩下的 cells 全標 SKIP |

## 設定方式

Bash:
```bash
SPC_VALIDATION_ENGINE_TIMEOUT_S=60 \
SPC_VALIDATION_ENGINE_PEAK_MB=4096 \
SPC_VALIDATION_MATRIX_TIMEOUT_S=1800 \
python .claude/skills/spc-validation-matrix/scripts/run_matrix.py --fixture normal_baseline
```

PowerShell:
```powershell
$env:SPC_VALIDATION_ENGINE_TIMEOUT_S=60
$env:SPC_VALIDATION_ENGINE_PEAK_MB=4096
$env:SPC_VALIDATION_MATRIX_TIMEOUT_S=1800
python .claude/skills/spc-validation-matrix/scripts/run_matrix.py --fixture normal_baseline
```

## 為什麼是這個值

- **30 s × 5 (= 150 s) per payload**: 來自實測 — `normal_baseline` 上 triple-feature 的 anomaly_3f / parallel_coord 在主流筆電大約 3–8 s,留 5× 緩衝避開噪訊 timeout。triple-feature 全 fixture 跑一輪通常 60–120 s。
- **2048 MB peak**: 大型 fixture (≥ 50k rows) 三特徵 anomaly 一次抓滿大約 600–800 MB,留 2× 緩衝。觸發 OVERLOAD 通常意味著 engine 沒做 sampling。
- **600 s 全矩陣**: `--quick` 約 30 s,full sweep 約 3–5 min;留兩倍給較慢機器或大 fixture。

## 限制

- Watchdog 是 soft kill — `threading.Thread` 沒有可靠的中止方式,STALL 後 thread 仍在背景跑(但 daemon=True,主程序結束會收掉)。實務上夠用。
- tracemalloc 是 process-wide,因此 cells 必須序列化跑(目前實作就是序列化的)。
- 平行度尚未支援(架構上預留 `SPC_VALIDATION_PARALLEL`,但 v1 不啟用)。
