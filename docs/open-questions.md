# Open Questions

Last updated: 2026-05-26

## Current Status

- 本檔是唯一 **active risk ledger**（single source）。
- Active 項目已由 7 項收斂為 5 項（保留必要且可重驗證項目）。
- `Watchlist #7` 編號與跨文件引用維持不變。

### Blocker Escalation Rule

- 僅當風險直接導致交付 gate 無法通過時，升級為 blocker。
- 目前 blocker 判定：
  - 無 active blocker（依本次 mandatory gates 與 `run_release_gate.py` 證據）。
  - `Watchlist #7` 維持 `status=monitoring`；若 performance gate 或 release gate 再次失敗，立即升級為 blocker。

## Active Risk Ledger

### 1. Import worker thread-path verification

- Scope: `DataLoaderWorker.start()` 與 `MainWindow` 連續操作下的 thread timing/cancel 邊界。
- Risk: 真實使用節奏可能觸發尚未覆蓋的時序 race。
- Guardrail: `tests/test_data_loader_worker_thread.py` 與 `tests/test_main_window_data_loader_lifecycle.py` 覆蓋 cancel/restart 與 stale-finish。
- Next action (Owner: self): 後續若調整 loader lifecycle，必須同步新增兩檔對應情境測試。
- Revalidation gate: `.venv\\Scripts\\python.exe -m pytest -q tests/test_data_loader_worker_thread.py tests/test_main_window_data_loader_lifecycle.py` + `.venv\\Scripts\\python.exe -m pytest -q`
- Rollback: 回退 worker lifecycle 相關變更到 queued-signal 優先路徑。
- Status: monitoring
- Latest evidence: lifecycle 兩檔測試可重複通過；全庫 pytest（2026-04-22）除 performance gate 之外通過。

### 5. Final audit runtime overhead

- Scope: `scripts/run_final_audit_suite.py --profile full` 執行時間。
- Risk: 關帳週期在慢機器或高負載主機下過長。
- Guardrail: 日常使用 `--profile quick`，關帳才使用 `--profile full`；保留 runtime 報表。
- Next action (Owner: self): 每次 release 產出並更新 `Outputs/final_audit/runtime_report.json`，追蹤 quick/full 中位數差異。
- Revalidation gate: `.venv\\Scripts\\python.exe scripts/run_final_audit_suite.py --repo-root . --profile quick` + `.venv\\Scripts\\python.exe scripts/run_final_audit_suite.py --repo-root . --profile full` + `.venv\\Scripts\\python.exe scripts/final_audit_runtime_report.py --input-root Outputs/final_audit --output Outputs/final_audit/runtime_report.json --recent-limit 5`
- Rollback: 暫停非關鍵 targeted pack，full 僅保留 release closeout 使用。
- Status: monitoring
- Latest evidence: `Outputs/final_audit/runtime_report.json` 與最近兩筆 final audit summary（2026-04-20）。

### 7. Release validation performance gate (P) convergence

- Scope: `tests/release_validation/test_performance_regression.py::test_performance_regression_synthetic_large_100k` 與 `golden_dataset/performance_baselines.json`。
- Risk: performance gate 曾出現真實回歸與 host/基線敏感性；最近 release-validation 證據已回到 PASS，但仍需監控避免再次影響 release gate。
- Guardrail: gate 僅阻擋「端到端可觀測」時間片段（`analysis_total_sec/chart_payload_sec/report_export_sec`）；`spc_sec` 與 `nelson_sec` 為 micro/segment 觀測指標（不作 hard gate）。fail-then-retry policy（near-boundary 才補跑）仍存在；超過 `ratio > 1.3` 仍直接 fail。
- Next action (Owner: self): 依三階段收斂執行  
  Phase A（降噪）: 固定環境連續量測 >= 5 次；  
  Phase B（判因）: 以 median + CoV 判斷 noise vs regression；  
  Phase C（修正）:  
  - 若 noise：附審計註記後重錄 baseline；  
  - 若 regression：建立修復任務（明確 module/metric 目標）並維持 active。
- Revalidation gate: `.venv\\Scripts\\python.exe -m pytest -q tests/release_validation/test_performance_regression.py::test_performance_regression_synthetic_large_100k` + `.venv\\Scripts\\python.exe scripts/release_check.py --skip-ruff --skip-mypy --with-release-ext` + `.venv\\Scripts\\python.exe -m pytest -q`
- Rollback: 若 release gate 不穩，暫時將 performance 結果降為觀測訊號（不改 CI，不改門檻），並以 full pytest 作主判定直到修復完成。
- Status: monitoring
- Latest evidence:
  - `Outputs/release/performance_noise_analysis_20260422.json`（5-run 降噪）曾顯示 true regression，非純主機噪音。
  - `Outputs/release/release_report.json`（generated_at_utc `2026-04-22T22:59:45`）顯示 `overall_ok=true`、`performance_status=PASS`、`failures=[]`。
  - `Outputs/release_validation_report.json`（本次重跑 generated_at_utc `2026-05-15T23:05:24`）顯示 `overall_status=PASS`、`release_allowed=true`，且 `test_performance_regression_synthetic_large_100k` passed。
  - `scripts/record_performance_baseline.py --samples 1 --emit-sample-json`（本次 100k synthetic）顯示 `chart_payload_sec=2.6905`、`report_export_sec=0.3479`、`measurement_wall_sec=3.8643`，並輸出 `nelson_sec=0.0639`、`report_payload_cache_seeded=true`。
  - `scripts/run_release_gate.py`（本次重跑）顯示 `release_allowed=true`，`150 passed in 13.26s`。

### 9. Windows runtime provider fragility (`_overlapped` / home-less shell)

- Scope: Windows host 在 `HOME/USERPROFILE` 缺失與 `_overlapped` import 路徑下的穩定性。
- Risk: host provider 異常時仍可能觸發 `WinError 10106`。
- Guardrail: `runtime_env.ensure_home_env()` 已接入 main/check_launch/tests；pytest 預設停用 debugging plugin。
- Next action (Owner: self): 依 `docs/reference/windows_runtime_recovery.md` 完成 host runbook 並留下證據。
- Revalidation gate: `.venv\\Scripts\\python.exe -m pytest -q` + `.venv\\Scripts\\python.exe scripts/check_launch.py` + `.venv\\Scripts\\python.exe -c "import _overlapped"`
- Rollback: 回退 runtime_env 接入並改用會話級 workaround（短期）。
- Status: stabilizing
- Latest evidence: `check_launch` pass；`import _overlapped` 在 host 仍可能失敗（需 host 修復）。

### 10. Bundled CJK font and chart visual parity (100%/125%/150%)

- Scope: `app/assets/fonts/NotoSansTC-VF.ttf`、`font_runtime`/`mpl_font_config`、`BaseChart` shared visual semantics 在不同 DPI/顯示環境的一致性。
- Risk: 自動化測試已覆蓋字形警告與 chart semantic helpers，但缺少跨縮放人工目視證據。
- Guardrail: `tests/test_mpl_font_config.py`、`tests/test_chart_glyph_rendering.py`、`tests/test_chart_label_glyph_safety.py` + baseline gates。
- Next action (Owner: self): 補 Windows 100% + 125%（或 150%）人工視覺驗證紀錄（含 OS/單多螢幕/RDP），並抽查 chart status badge、limit labels、sample disclosure 無裁切。
- Revalidation gate: `.venv\\Scripts\\python.exe -m pytest -q tests/test_mpl_font_config.py tests/test_chart_glyph_rendering.py tests/test_chart_label_glyph_safety.py tests/test_chart_visual_readability.py` + `.venv\\Scripts\\python.exe scripts/check_launch.py` + manual visual check record
- Rollback: 回退 bundled font 路徑，恢復系統字型 fallback-only。
- Status: stabilizing
- Latest evidence: 已調整 `CHART_FONT_MICRO` (8pt) 與 `CHART_FONT_ANNOTATION` (9pt)；優化 `base_chart.py` 標籤偏移量與 BBox padding；通過 `test_chart_glyph_rendering.py` 與 `check_launch.py` 驗證。2026-05-26 於目前螢幕 `1280x752` available / DPR `2.0` / logical DPI `96` 完成 Data Setup、Measurement Library、Chart Analysis、Diagnostic、Report Export 與代表性對話框原生 Qt 截圖；視窗 frame 均落在 available geometry 內，Data Setup budget 無 sibling overlap，Report Export 改為無水平捲動的兩欄群組布局。100%/125%/150% 跨縮放人工紀錄仍維持 monitoring。

## Moved Out Of Active (Converged / Dormant)

- 11. Supplier code one-time renumber conflict cleanup  
  理由：目前無現場衝突證據，且已有 e2e migration conflict guard；保留於 decision-log，遇到衝突再重新激活。
- 12. Height 單位換算鋼板序號覆蓋  
  理由：屬設計擴充議題，未出現現場阻塞案例；暫列產品設計 backlog，不佔 active risk 配額。

## Historical Context

- 已結案與歷史風險請見 `docs/decision-log.md`。
- 本檔只追蹤 active 風險，不重複維護歷史快照。
