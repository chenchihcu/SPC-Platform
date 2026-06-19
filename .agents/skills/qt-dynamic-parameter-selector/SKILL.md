---
name: qt-dynamic-parameter-selector
description: Qt 動態參數選擇器 — 在 PySide6 tab 介面中加入 ComboBox 切換已預先計算好的多組參數/特徵,支援即時切換視圖而不重算。Use this skill 當使用者要為單特徵分析圖表加上下拉選單、在多參數結果間即時切換,或避免重複計算造成的卡頓。觸發詞包含「parameter switching」「feature selector」「dynamic tabs」「ComboBox」「即時切換」「動態參數」。
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

1. **Feature switching (Volume / Area / Height)** — handled by **toolbar buttons**, not per-tab ComboBoxes. `chart_analysis_page._on_feature_shortcut_clicked()` sets `_display_feature` → `_update_current_chart()` → `_resolve_chart_data(chart_id)` returns `parameters[_display_feature][key]`. The `chart_id → key` mapping lives in `_PARAM_KEY_FOR_CHART`. Instant, no re-analysis.
2. **In-tab ComboBox** — used only for **sub-selections within one tab** (spatial display mode, comparison footprint). This is the pattern the code below implements.

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

**P1 — `blockSignals` must be symmetric on every path.** A `return` between `blockSignals(True)` and `blockSignals(False)` permanently deadens the widget's signals. Use `try/finally`. This rule's authoritative source is the project audit rule **P1** in [`.claude/rules/code_audit_rules.md`](../../rules/code_audit_rules.md) (also checked by the global `/code-audit` when run in this repo).

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

`payload["parameters"]` is present **only in n=1 (single-feature) mode**. For n=2/n=3 it is absent — `.get("parameters", {})` yields `{}`, the ComboBox auto-hides, and the view falls back to `_last_payload`. Never assume the key exists.

## Verify before done

- [ ] ComboBox visible only when `parameters` is non-empty (n=1); hidden for n=2/n=3
- [ ] Items sorted; each selectable; chart updates instantly (no re-analysis)
- [ ] `index < 0` and unknown-name selections handled without crash
- [ ] Every `blockSignals(True)` path reaches `blockSignals(False)` (try/finally)
