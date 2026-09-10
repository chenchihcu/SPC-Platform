---
name: qt-dynamic-parameter-selector
description: "SPC Platform PySide6 tab 中以 ComboBox 切換已預先計算的多組參數/特徵，即時切換不重算。Use when 為本專案單特徵分析圖加 ComboBox 下拉或多參數結果即時切換。Do NOT use for 新建通用 Qt parameter panel（改用 build-qt-parameter-selector）、Qt theme/entrypoint 版面（改用 configure-qt-layout-theme）或 Web CSS（改用 configure-web-layout-theme）。"
version: 1.1.0
---

# Qt Dynamic Parameter Selector

Interactive parameter/feature switching in PySide6 tabs with real-time view updates and **no re-computation** — variants are pre-computed once, switched instantly client-side.

> **Scope note (Opus 4.8):** basic Qt — `QComboBox`, signal/slot, `blockSignals`, layout — is assumed known. This skill carries only the **project-specific contract and non-obvious gotchas**. The `payload["parameters"]` shape itself is owned by the **analytics-engine-contract** skill (`.claude/skills/analytics-engine-contract/SKILL.md`); this skill covers how the **UI consumes** it.

## When to Use

- Adding instant feature/parameter switching to single-feature analysis views
- Switching between pre-computed parameter sets without re-analysis
- In-tab sub-selectors (mode, group, footprint) that re-filter an already-loaded payload

## The two switching mechanisms (don't confuse them)

1. **Analysis-feature switching (Volume / Area / Height)** — handled by the left sidebar and updates `ComponentSelectPage`; changing it starts a new analysis.
2. **Precomputed display switching** — `ChartAnalysisPage.feature_combination_combo` selects a stable key such as `Volume|Height`, then resolves `parameters` / `dual_parameters` / triple top-level results without starting a new analysis. In-tab selectors (spatial mode, comparison footprint) follow the same stable-key and signal-blocking rules.

## Core in-tab ComboBox pattern

The only two things that bite in practice: **symmetric `blockSignals`** and **index/key validation**.

```python
def update_data(self, payload: dict):
    self._last_payload = payload or {}
    self._parameters = (payload or {}).get("parameters", {})

    self.param_combo.blockSignals(True)
    try:                                    # symmetric even on early return — see P1 below
        self.param_combo.clear()
        if self._parameters:
            self.param_combo.addItems(sorted(self._parameters))
        self.param_combo.setVisible(bool(self._parameters))   # auto-hide multi-feature
    finally:
        self.param_combo.blockSignals(False)

    self.chart_view.draw_chart(self._last_payload)

def _on_parameter_selected(self, index: int) -> None:
    if index < 0:
        return
    name = self.param_combo.currentText()
    if name not in self._parameters:        # guard invalid/stale selection
        return
    self._last_payload = self._parameters[name]
    self.chart_view.draw_chart(self._last_payload)
```

**P1 — `blockSignals` must be symmetric on every path.** A `return` between `blockSignals(True)` and `blockSignals(False)` permanently deadens the widget's signals. Use `try/finally`. This rule's authoritative source is the project audit rule **P1** in [`.claude/rules/code_audit_rules.md`](../../../.claude/rules/code_audit_rules.md) (also checked by the global `/code-audit` when run in this repo).

## Dual / hierarchical selectors

When a tab has a parameter selector **plus** a mode/group/footprint sub-selector: on parameter change, reload the sub-selector's items (under `blockSignals`) and redraw with the first sub-item.

```python
def _on_parameter_selected(self, index: int) -> None:
    if index < 0:
        return
    name = self.param_combo.currentText()
    if name not in self._parameters:
        return
    param_data = self._parameters[name]
    self._last_payload = param_data

    modes = param_data.get("modes", {})
    self.mode_combo.blockSignals(True)
    try:
        self.mode_combo.clear()
        self.mode_combo.addItems([mode_label[k] for k in modes])
    finally:
        self.mode_combo.blockSignals(False)

    if modes:
        first = next(iter(modes))
        self.chart_view.draw_chart({**param_data, "data": modes[first]})
```

Real in-repo examples: `spatial_tab.mode_combo` (Value / PassRate / DefectRate) and `comparison_tab.footprint_combo` (PartType filter).

## Backward compatibility

`payload["parameters"]` is available for the analyzed feature set. `dual_parameters` is additive: n=1 may cache all available pairs, n=2 caches the selected pair, and n=3 caches all three selected pairs. Consumers must still tolerate missing cache keys and use the documented resolver fallback. `feature_tab_count` remains a derived compatibility field; new code should use `active_feature_combination`.

## Verify before done

- [ ] ComboBox lists only legal combinations of analyzed features and hides when no alternative exists
- [ ] Stable item-data keys resolve the exact feature tuple; chart updates instantly with no analysis generation change
- [ ] `index < 0` and unknown-name selections handled without crash
- [ ] Every `blockSignals(True)` path reaches `blockSignals(False)` (try/finally)
