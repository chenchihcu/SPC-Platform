# UI State Semantics and Token Reference

This document describes the project's semantic UI state system and design token usage. Use it when adding or changing UI that must distinguish enabled, disabled, incompatible, loading, error, and other states without relying on color alone.

## 1. Semantic States

| State | Definition | Typical use |
|-------|------------|-------------|
| enabled | Can be used / clicked / selected | Chart available, button active, option selectable |
| disabled | Cannot be used (generic) | Precondition not met, feature off |
| selected | Currently selected | List current item, nav current step, active tab |
| hover | Mouse over | Interactive element hover feedback |
| active / pressed | Being pressed | Button or tab press moment |
| incompatible | Unavailable due to condition mismatch | Chart needs 2 features but 1 selected; export checkbox disabled by feature count |
| loading | Computing / loading | Refresh analysis in progress |
| ready | Render/output ready | Chart card can render and export |
| nodata | Data insufficient but not crash | Chart payload invalid due missing samples/inputs |
| empty | No data yet | Not loaded, no selection, empty list |
| warning | Risk but can proceed | Match rate &lt; 90%, low data warning |
| error | Error, cannot continue | Load failed, compute failed, required field missing |
| success | Done / ready to produce | Data loaded, analysis done, export ready |
| info | Hint / explanation | Neutral hint text |

## 2. Token Mapping (app/ui/theme/tokens.py)

- **Text**: `TEXT_STATE_ENABLED`, `TEXT_STATE_DISABLED`, `TEXT_STATE_INCOMPATIBLE`, `TEXT_STATE_SELECTED`, `TEXT_STATE_WARNING`, `TEXT_STATE_ERROR`, `TEXT_STATE_SUCCESS`, `TEXT_STATE_INFO`
- **Background**: `BG_STATE_ENABLED`, `BG_STATE_DISABLED`, `BG_STATE_SELECTED`, `BG_STATE_INCOMPATIBLE`, `BG_STATE_HOVER`
- **Border**: `BORDER_SELECTED`, `BORDER_WARNING`, `BORDER_ERROR`, `BORDER_INCOMPATIBLE`
- **Icon**: `ICON_LOCK`, `ICON_LOCK_FALLBACK` (e.g. for incompatible / blocked)

## 2.1 Font Standard (Typography)

全系統統一採用 **Noto Sans TC (思源黑體)**。
- **實作**: `app/ui/theme/tokens.py` 中的 `FONT_FAMILY` 優先序。
- **限制**: 避免在頁面 hard-code 其他字型；管制圖與 PPTX 報告渲染均對齊此標準以確保 CJK 一致性。

工程儀表板狀態色（`DiagnosticPage` / dashboard_layers）:
- `Normal`: Green
- `Warning`: Orange
- `Alarm`: Red
- `Info`: Blue

儀表板值樣式 class:
- `dashValueGood` / `dashValueWarning` / `dashValueBad` / `dashValueNeutral`

QSS in `app/ui/theme/dark_stylesheet.py` references these tokens for `state` or `class` attributes so that different states are distinguishable (e.g. incompatible uses amber, not only grey).

## 3. Usage by Component

| Location | States used | How |
|----------|-------------|-----|
| Chart analysis selector | enabled, incompatible, selected | 圖表選擇區使用 `QCheckBox`；不相容項設 `state="incompatible"` 並 disabled；頁籤切換（1F/2F/3F）時依相容性重建。 |
| Chart analysis autoswitch hint | info | 特徵切換觸發自動改選時顯示 `autoswitch_reason`（來源圖/目標圖/原因），屬可追溯提示，不使用 alarm 色。 |
| Chart analysis context strip | info | 圖表頁在 chart card 區上方常駐顯示 active features、1F/2F/3F 模式、選取圖表數、標準化狀態與 batch/PartType/RefDes filter，避免使用者只靠 tooltip 判讀。 |
| Chart analysis card status | ready, incompatible, nodata, error | 每張圖卡顯示 `Ready/Incompatible/NoData/Error`；來源為 `render_status[chart_id]`，並帶原因文案；`QLabel[class="statusIndicator"][state=*]` 在 QSS 中提供不同邊框/背景/文字色。 |
| Statistics data page | success, warning, error, nodata, info | `StatisticsDataPage` 將 OOC/Shift/Drift/Outlier 文字摘要集中為一頁式 `QTableWidget`，不使用左側子清單；項目欄使用 Qt standard icons，狀態欄使用 `create_status_badge(...)`，長 CJK 摘要與來源文字以 tooltip 保留完整內容。 |
| 製程統計分析輸出（`DiagnosticPage`） | Normal, Warning, Alarm, Info | 報告式欄位值依 `summary.process.dashboard_layers` 狀態欄位轉為 `dashValue*` class；缺值顯示 `UNKNOWN/VERIFY`。 |
| Report export page | selected, incompatible, info | Chart checkboxes：不相容時 `state="incompatible"`；首次載入套用工程建議預設勾選；產生預覽時僅取消不相容勾選、其餘保留；預覽 **[F] 匯出範圍摘要** 顯示已選/可用/不相容；另存 PPTX 選檔後有唯讀確認清單（證據圖、預估畫廊頁、分布分析敘事頁）再寫檔。 |
| Control panel status row | ok, pending, warning | QLabel `class`: status-ok / status-pending / status-warning; Phase 2 added Unicode prefix (✓ / ○ / ⚠). |
| Refresh button (control_panel) | loading | On refresh: disabled + text "計算中…" + `state="loading"`; restored in `finally`. See docs/governance/AGENTS.md §3 and main_window.refresh_analysis. |
| BaseChart visual contract | info | `BaseChart` 在畫面與報告渲染共用同一視覺收斂層：legend 樣式、N/displayed/tested/top_n/grid/normalized disclosure、統一 reference-line helper、OOC/OOS marker helper。 |
| BaseChart placeholder | incompatible, error, empty | `_placeholder_class_for()` sets `chartPlaceholder-incompatible`, `chartPlaceholder-error`, or `chartPlaceholder-empty`; QSS gives distinct border/background. Incompatible = condition mismatch; error = compute/load failure; empty = no data or not yet computed. |
| Navigation panel | selected | Step buttons: `isCurrent="true"` (and optionally `state="selected"`); QSS uses NAV_STEP_ACTIVE_BG and ACCENT_PRIMARY. |
| Drop zones | active | Coordinate and measurement upload drag-over feedback must use `set_drop_zone_active(...)`, which sets `state="active"` so `QFrame[class="dropZone"][state="active"]` and embedded drop targets share one contract. |
| Page status lamps | idle, loading, success, warning, error | Page-level status indicators use `create_status_lamp()` plus `apply_status_accessibility(...)`; measurement library refresh maps loading to `loading`, records present to `success`, and empty to `idle`. |
| Secondary tab groups | selected, hover, disabled | Library, IPC pillar, and diagnostic matrix tabs set `class="secondaryTabs"` and use the shared `QTabWidget[class~="secondaryTabs"]` selected/hover/disabled QSS. Page-specific pane/card differences may add another class such as `processMatrixTabs`. |
| Shared empty states | empty | Use `empty_state_label(...)` for chart and feature-selection placeholders. Presentation-only emoji are not part of the visible empty-state contract. |
| Shared table roles | default, reference, library, diagnostic | Use `style_table(table, role=...)` for edit trigger, row selection, header alignment, word-wrap, and diagnostic overflow behavior instead of page-local repeated table setup. |

When adding new pages or controls that have "can use / cannot use" or "condition mismatch" semantics, set the appropriate `state` or `class` and reuse these tokens in QSS so behaviour stays consistent.

## 4. 規格變更與對照（與 `docs/specs/spec_maintenance_and_alignment.md` 一致）

- 任何會影響 **QSS 選擇器**、**自動化測試**、或 **使用者可辨識之狀態語意** 的變更（`objectName`、`state`、`class`、新增狀態列），必須同步更新本文件 **§1 表格** 與 **§3 元件表**，並在 `app/ui/theme/dark_stylesheet.py` 完成對應規則。
- 重新命名或合併狀態時，請在 PR／變更說明中提供 **舊 → 新** 對照，並檢查 `docs/governance/AGENTS.md` 與 `docs/specs/ui_design_spec.md` §22 是否需一併提及。
- 完整治理流程見 **`docs/specs/spec_maintenance_and_alignment.md`** §1、§4。
