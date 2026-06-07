# Decision Log

後續決策若影響公開規格、契約或 `docs/governance/SPC_RULES.md`，請同步 **`docs/specs/spec_maintenance_and_alignment.md`** 所載之觸發條件與文件清單。

## 2026-03-24 — Apple Light UI Refactor (Global)

### Decision
- Adopt a single Apple-inspired light design baseline across UI pages and chart containers.
- Keep statistical semantics unchanged (SPC formulas, thresholds, interpretation text, and chart meaning remain intact).
- Move page-level inline styles (`setStyleSheet`, `setFont`) into `tokens.py` + global QSS.
- Use semantic incompatible state (`state="incompatible"`) instead of hard-coded red disabled text.
- Shift key dashboard/report layouts toward flexible sizing (remove fixed chart card height and reduce rigid width locks).

### Impact Scope
- UI theme tokens and global stylesheet.
- Major UI pages/widgets (chart analysis, report export, data management, navigation/root-cause panels).
- Multi-feature chart palette source alignment to theme tokens.

### Risks
- Minor visual regressions on uncommon DPI/OS font fallback combinations.
- Existing local environment without SF fonts will rely on fallback stacks and may differ slightly from macOS.

### Rollback Approach
- Revert `app/ui/theme/tokens.py` and `app/ui/theme/dark_stylesheet.py` first to restore prior visual baseline.
- Revert targeted UI pages/widgets if specific layout regressions appear.
- Keep analytics/services/viewmodels unchanged to avoid behavioral rollback risk.

## 2026-03-24 — DataSetup Typography Compression (3-column fixed)

### Decision
- DataSetup page keeps three-column layout as a hard constraint.
- For DataSetup only, apply dense typography/spacing via page-scoped QSS (`dataPage="dataSetup"`), not global token downscale.
- Long path lines (`目前載入量測檔 / 座標檔`) use single-line ellipsis with full tooltip text.

### Impact Scope
- `DataSetupPage`, `CoordinateManagerPage`, `DataUploadPage`, `StencilSpecEditor`.
- Local QSS rules under DataSetup scope.

### Risks
- At very small window heights, dense layout may still feel tight due no scroll fallback.
- Ellipsized path text depends on tooltip for full visibility.

### Rollback Approach
- Restore responsive tier switching in `DataSetupPage`.
- Remove DataSetup-scoped dense QSS block.
- Revert path-label elide methods to multi-line wrapping.

## 2026-03-24 — DataSetup Anti-Crowding Layout Correction (tier fallback restored)

### Decision
- Restore responsive tier fallback for `DataSetupPage` (1/2/3 columns by width) to prevent field/text crowding under narrow content width and high DPI.
- Keep DataSetup dense style scoped locally, but ensure form label styling applies via explicit `class="formLabel"` selectors.
- Restore practical minimum width for key product selectors (`FORM_COMBO_MIN_WIDTH`) and enable `QFormLayout` row wrapping on long-label forms.
- Keep `stepCard` containers, but reduce their layout cost on DataSetup only by shrinking page margins, column gaps, and card padding.

### Impact Scope
- `DataSetupPage` tier behavior.
- DataSetup form widgets in coordinate/stencil sections.
- DataSetup-related style selectors in global QSS.
- DataSetup-only spacing tokens.

### Risks
- On medium widths previously forced to 3-column, layout will now appear as 2-column.
- Screenshot baselines captured during fixed 3-column period may need regeneration.

### Rollback Approach
- Revert `DataSetupPage._sync_layout_from_width` to fixed tier 3.
- Revert DataSetup breakpoints and form label selector/class changes.

## 2026-03-24 — Windows High DPI Bootstrap

### Decision
- Configure Qt high DPI behavior before `QApplication` creation in a shared bootstrap helper.
- Support both PySide6 and PySide2 by setting environment defaults plus Qt application attributes where available.
- Keep launcher overrides possible by using `os.environ.setdefault(...)` instead of unconditional replacement.

### Impact Scope
- App startup path in `main.py` / `run_app()`.
- Windows fractional scaling behavior (for example 125% / 150%).

### Risks
- External launchers that rely on different Qt DPI defaults may render slightly differently unless they already set explicit environment overrides.

### Rollback Approach
- Revert `app/bootstrap/dpi.py` to the previous minimal rounding-policy-only implementation.
- Remove the dedicated DPI bootstrap test if startup policy is intentionally simplified again.

## 2026-03-24 — QLabel Sizing Rule For DataSetup

### Decision
- In DataSetup-related pages, avoid fixed-width label sizing for readable text.
- Use `setMinimumSize(0, 0)` plus `QSizePolicy.Preferred`, and rely on layout stretch factors to allocate width to fields and path labels.

### Impact Scope
- `DataSetupPage`, `CoordinateManagerPage`, `DataUploadPage`, `StencilSpecEditor`.

### Risks
- Labels may reflow slightly differently across OS font stacks, but this is safer than hard width locks under Windows DPI scaling.

### Rollback Approach
- Revert the label sizing policy changes in the affected DataSetup UI files.

## 2026-03-24 — QSS Font Unit Normalization

### Decision
- Keep QSS `padding` / `margin` non-negative.
- Normalize QSS `font-size` units in the global stylesheet to `pt` instead of `px` for more stable cross-device rendering.

### Impact Scope
- Global stylesheet in `app/ui/theme/dark_stylesheet.py`.

### Risks
- Visual density may shift slightly because Qt resolves `pt` through device DPI rather than raw pixels.

### Rollback Approach
- Revert `font-size` declarations in `app/ui/theme/dark_stylesheet.py` back to `px` if a platform-specific regression is confirmed.

## 2026-03-24 — Grid Layout Normalization For Analysis Conditions And Stencil Spec

### Decision
- Rewrite the `ControlPanel` "分析條件" section to a strict two-column `QGridLayout`, with each label in column 0 and its control in column 1.
- Rewrite the `StencilSpecEditor` "鋼板規格設定" form rows to a single `QGridLayout`, keeping the product action button in its own dedicated third column.
- Remove the previous blank-label `QFormLayout` row pattern for "指定板號" to avoid geometry instability when toggling visibility.

### Impact Scope
- `app/ui/widgets/control_panel.py`
- `app/ui/widgets/stencil_spec_editor.py`

### Risks
- Label widths will now be governed by the shared grid column, so localized text changes may slightly shift field widths.

### Rollback Approach
- Restore the previous `QFormLayout` / row-layout implementation in the two widgets if the normalized grid introduces an unexpected styling regression.

## 2026-03-24 — Text Widget SizePolicy Normalization

### Decision
- Normalize `QLabel` widgets to `QSizePolicy.Preferred / Preferred` and `QLineEdit` widgets to `QSizePolicy.MinimumExpanding / Preferred`.
- Install the normalization as a global UI policy so newly shown widgets also inherit the same rule, instead of relying on scattered page-level overrides.
- Remove remaining `setFixedWidth` / `setFixedHeight` / `setFixedSize` calls in the UI codebase and replace them with minimum/maximum size constraints where exact chrome sizing is still required.
- For `QGridLayout`-based checkbox/form regions, prefer layout spacing and column stretch over per-widget margin tuning.

### Impact Scope
- `app/ui/theme/layout_policy.py`
- `app/ui/main_window.py`
- `app/ui/theme/__init__.py`
- `app/ui/widgets/collapsible_sidebar.py`
- `app/ui/pages/data_management_page.py`
- `app/ui/tabs/control_chart_tab.py`
- `app/ui/widgets/status_bar.py`
- `app/ui/pages/report_export_page.py`

### Risks
- Some compact decorative labels may grow slightly because they are no longer hard-locked to fixed geometry.
- Sidebar rail buttons still use exact dimensions via min/max bounds; behavior is preserved but the implementation path changed.

### Rollback Approach
- Remove the global policy filter and explicit normalization call from `MainWindow`.
- Restore prior fixed-size calls in the affected widgets if any visual regression is confirmed.

## 2026-03-24 — ControlPanel RefDes Filter Is Combo-Only

### Decision
- Keep the left-sidebar component-name / RefDes filter as a dropdown-only control.
- Explicitly mark `refdes_combo` as non-editable and guard the condition-grid slot `(row=2, col=1)` so it cannot retain or reintroduce a `QLineEdit`.

### Impact Scope
- `app/ui/widgets/control_panel.py`
- `tests/test_control_panel_layout.py`

### Risks
- None beyond the intended behavior: free-text entry is not supported for this filter row.

### Rollback Approach
- Remove the combo-only guard if the product later requires an editable combo or separate text input for component filtering.

## 2026-03-24 — UI Failure Stabilization v2

### Decision
- Replace zero-height card/container baselines with conservative floors, then lock card minimum heights against their actual content size hints.
- Roll back the `DataSetup` dense-mode spacing and control compression to more stable values while keeping the page-scoped styling model.
- Rewrite the `CoordinateManagerPage` product-binding form from `QFormLayout` to a strict two-column `QGridLayout`.
- Add an opt-in runtime UI diagnostics snapshot behind `SPC_UI_DIAGNOSTICS=1` to log startup path, DPI environment, screen metrics, `DataSetup` tier, and card geometries.

### Impact Scope
- `app/ui/theme/tokens.py`
- `app/ui/theme/layout_policy.py`
- `app/ui/pages/coordinate_manager_page.py`
- `app/ui/pages/data_upload_page.py`
- `app/ui/widgets/stencil_spec_editor.py`
- `app/ui/widgets/control_panel.py`
- `app/ui/pages/workorder_page.py`
- `app/ui/debug/ui_runtime_diagnostics.py`

### Risks
- DataSetup and sidebar cards will look less dense than the prior Apple-style pass.
- Runtime diagnostics adds one startup log line when explicitly enabled.

### Rollback Approach
- Restore the prior dense tokens and zero-height baselines if a confirmed regression requires it.
- Remove the runtime diagnostics helper and startup hook if it proves noisy or unnecessary.

## 2026-03-24 — DataSetup Layout Regression Recovery

### Decision
- Roll back `stabilize_minimum_height()` to a floor-only helper so UI cards are no longer locked to transient `sizeHint()` values.
- Treat `CoordinateManagerPage`, `DataUploadPage`, and `StencilSpecEditor` as embeddable sections when hosted inside `DataSetupPage`; in embedded mode they no longer use bottom stretches to fill page height.
- Keep `DataSetupPage` responsive tiers, but make the tier layouts top-aligned so sections keep their natural height in 1/2/3-column arrangements.
- Remove `stepCard` padding from QSS and stop using DataSetup-scoped control min-height/padding overrides as geometry controls; card spacing is owned by the inner layouts.
- Expand runtime diagnostics and tests to include effective `DataSetup` widths, size hints, and tier-specific layout expectations.

### Impact Scope
- `app/ui/theme/layout_policy.py`
- `app/ui/pages/data_setup_page.py`
- `app/ui/pages/coordinate_manager_page.py`
- `app/ui/pages/data_upload_page.py`
- `app/ui/widgets/stencil_spec_editor.py`
- `app/ui/theme/dark_stylesheet.py`
- `app/ui/debug/ui_runtime_diagnostics.py`
- `tests/test_ui_geometry_stability.py`
- `tests/test_ui_runtime_diagnostics.py`

### Risks
- Standalone uses of the three DataSetup sections now depend on the default `embedded=False` path remaining intact.
- DataSetup will look less densely packed than the earlier Apple-style pass because geometry is no longer driven by scoped QSS padding/min-height overrides.

### Rollback Approach
- Restore the previous hint-based `stabilize_minimum_height()` behavior and remove the `embedded` mode if the top-aligned section layout causes an unacceptable standalone regression.
- Reintroduce the DataSetup-scoped QSS geometry overrides only if a validated follow-up design requires them.

## 2026-03-24 — DataSetup Visual Density Tuning

### Decision
- Keep the recovered DataSetup layout mechanics unchanged and tune density only through DataSetup-specific spacing and typography tokens.
- Reduce DataSetup page margins, column gap, row/form spacing, and local list padding.
- Introduce DataSetup-specific card content padding and section gap so the three embedded sections can be visually tighter than the global card baseline without changing app-wide cards.
- Do not change any minimum-height behavior or reintroduce hint-based geometry control.

### Impact Scope
- `app/ui/theme/tokens.py`
- `app/ui/pages/coordinate_manager_page.py`
- `app/ui/pages/data_upload_page.py`
- `app/ui/widgets/stencil_spec_editor.py`

### Risks
- DataSetup will render denser than other form pages by design; if future pages copy these widgets outside DataSetup, they may look tighter than neighboring cards.

### Rollback Approach
- Restore the previous DataSetup spacing/typography token values and revert the three widget files to the shared card padding/gap tokens if the page becomes too tight in real-machine DPI validation.

## 2026-03-24 — ControlPanel Visual Density Tuning

### Decision
- Tighten only the `ControlPanel` card density through local spacing and typography; do not change any minimum-height tokens or layout structure.
- Add a `sidebarPanel="controlDense"` scope so section titles, form labels, and status rows can be rendered slightly smaller without affecting other cards.
- Reduce `ControlPanel` card padding, card section gap, form column spacing, optional-filter spacing, and action-button stack spacing.

### Impact Scope
- `app/ui/theme/tokens.py`
- `app/ui/widgets/control_panel.py`
- `app/ui/theme/dark_stylesheet.py`

### Risks
- The sidebar control area will look denser than other panels by design.
- If Windows fallback fonts render taller than expected, the local typography reduction may need a slight rollback.

### Rollback Approach
- Restore the previous `ControlPanel` spacing tokens and remove the `sidebarPanel="controlDense"` scoped QSS rules if the sidebar becomes too cramped in real-machine validation.

## 2026-03-24 — UI Font Cap Normalization

### Decision
- Treat the previous UI maximum font as the baseline, shrink that maximum by 40%, and use the result (`13.2pt`) as the new UI font cap.
- Reduce every UI typography token that still exceeded that cap to exactly `13.2pt`.
- Leave smaller supporting text sizes unchanged so captions, hints, and compact labels do not become unreadably small.

### Impact Scope
- `app/ui/theme/tokens.py`
- `docs/reference/docs/reference/platform_overview.md`
- `tests/test_ui_font_caps.py`

### Risks
- Visual hierarchy is flatter because headings and body text are now much closer in size.

### Rollback Approach
- Restore the prior typography token values if the capped hierarchy is judged too flat in actual UI review.
