# Open Questions

Last updated: 2026-07-14

## Current Status

- 本檔是唯一 **active risk ledger**（single source）。
- Active 項目已由 6 項收斂為 0 項；所有移出項目均保留可機械重驗證的重新啟用條件。
- `Watchlist #7` 編號與跨文件引用維持不變。

### Blocker Escalation Rule

- 僅當風險直接導致交付 gate 無法通過時，升級為 blocker。
- 目前 blocker 判定：
  - 無 active blocker（依本次 mandatory gates 與 `run_release_gate.py` 證據）。
  - `Watchlist #7` 已收斂移出 active；若 performance gate 或 release gate 再次失敗，沿用原編號重新啟用並升級為 blocker。

## Active Risk Ledger

- Scope: none (no active risk items)
- Risk: none active
- Current guardrail: 所有 dormant 項目保留原編號、重驗 gate 與機械重新啟用條件。
- Next action (Owner: self): 僅在對應 reactivation condition 成立時恢復原項目，不建立重複編號。
- Revalidation gate: `powershell -ExecutionPolicy Bypass -File scripts/harness_check.ps1` + 對應 dormant 項目所列 gate
- Rollback: not applicable；若證據失效，將原項目移回 active 並恢復其完整 risk ledger 欄位。
- Status: empty

## Moved Out Of Active (Converged / Dormant)

- 5. Final audit runtime overhead — 理由：full profile 原本在完整 `pytest_full` 後重跑五組已被涵蓋的 targeted packs；2026-07-14 移除重複執行但保留完整 pytest 與 Qt policy audit，總時間由 `504.25s` 降為 `351.79s`（約 `30.2%`），最新 run PASS、exception scan 0。Quick 仍保留分相 targeted packs。若後續 full 總時間或 `pytest_full=330.97s` 增加超過 20%，以原編號重新啟用。
- 1. Import worker thread-path verification — 理由：2026-07-14 lifecycle/cancel/restart/stale-finish 兩檔共 18 tests PASS，當日 full audit 亦 PASS；guard 已成為 durable regression gate。後續若 lifecycle 改動或重現 race，再以原編號啟用。
- 7. Release validation performance gate (P) convergence — 理由：固定環境 5 次 100k 量測完成 Phase A/B；blocking metrics CoV 為 `analysis=6.80%`、`chart payload=4.59%`、`report export=6.07%`，performance regression test PASS，`run_release_gate.py` 150 tests PASS 且 `release_allowed=true`。若 ratio 超過 1.3 或 release gate 失敗，以 Watchlist #7 原編號重新啟用。
- 9. Windows runtime provider fragility (`_overlapped` / home-less shell) — 理由：2026-07-14 正常環境與移除 `HOME/USERPROFILE` 後均可 `import _overlapped`；`ensure_home_env()` 正確補回兩變數，home-less `check_launch.py` PASS，且 recovery runbook 已存在。若再出現 WinError 10106，依 runbook 重新啟用。
- 10. Bundled CJK font and chart visual parity — 理由：2026-07-14 CJK/font/readability 11 tests PASS，`check_launch.py` PASS；`Outputs/visual_verification/pad_image_selector_{1.0,1.25,1.5}.png` 已以原始尺寸逐張目視，CJK、圖例、selector、軸標籤與邊界無裁切。新 chart/theme 變更仍須依 UI gate 重新驗證，但不再作常駐 active risk。
- 12. Deferred dedup refactors (D3 / D6 / D14) — 理由：D14 先前已完成；2026-07-14 D3 將四張 3F 圖的 payload guard、axes/style 與 canvas lifecycle 收斂至 `BaseChart`，重構前後四張 deterministic PNG SHA-256 完全一致；D6 將 legacy validators 改為委派 `SchemaMapper`，保留相容 API 並消除必要欄位雙真本。focused 17 tests PASS。
- 11. Supplier code one-time renumber conflict cleanup — 理由：目前無現場衝突證據，且已有 e2e migration conflict guard；保留於 decision-log，遇到衝突再重新激活。
- Historical design backlog (formerly #12). Height 單位換算鋼板序號覆蓋 — 理由：屬設計擴充議題，未出現現場阻塞案例；暫列產品設計 backlog，不佔 active risk 配額。

## Historical Context

- 已結案與歷史風險請見 `docs/decision-log.md`。
- 本檔只追蹤 active 風險，不重複維護歷史快照。
