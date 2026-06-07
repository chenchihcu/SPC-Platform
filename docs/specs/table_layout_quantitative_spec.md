# Table Layout Quantitative Specification

## 1. Purpose

This document defines hard, quantitative layout rules for owner-designated engineering forms (especially `Data Setup`) using a one-page table layout.

Required design intent:
- One-page table layout (表格式)
- No full-page vertical scrolling
- De-containerized visual structure (do not rely on card-stack semantics)


## 2. Quantitative Layout Model

### 2.1 Area Budget

Before implementation, define a page-level area budget:

- `A_total = W_content * H_content`
- `A_total = A_header + A_main`
- `A_main = sum(A_region_i) + sum(A_gap_j)`

For `Data Setup`:
- `A_left` (coordinate section)
- `A_right_top` (stencil/spec section)
- `A_bottom` (measurement upload section)

Each region must satisfy:
- `A_region_i >= A_region_min_i`

Do not accept layouts without explicit region budget.

### 2.2 Row Geometry Constraints

Each table-like row must define:
- `Lw`: label region width (fixed or bounded)
- `Iw`: input/value region width (elastic with min constraint)
- `Aw`: action region width (min constraint when action exists)
- `Rh`: row minimum height

Hard constraints:
- `Lw >= Lw_min`
- `Iw >= Iw_min`
- `Aw >= Aw_min` (if action exists)
- `Rh >= Rh_min`

### 2.3 Text-Fit Constraints

Critical fields must satisfy text-fit constraints:
- `Lw_min >= max(label_text_pixel_width) + label_padding`
- `Iw_min >= max(value_or_placeholder_pixel_width) + input_padding`

If a critical field cannot fit:
1. Reallocate region budget
2. Rebalance row composition
3. Adjust spacing

Do not silently clip critical labels.


## 3. Composition Optimality Criteria

A layout is acceptable only when all pass:
- No overlap between sibling regions
- No clipping in critical labels/fields
- Stable baseline alignment across same-role rows

Recommended evaluation:
- Overlap check: all major section geometries are disjoint
- Critical text check: no truncation for required labels
- Baseline check: same-row controls align to common baseline


## 4. Compression Policy (Height Pressure)

When vertical space is insufficient, compression order is fixed:
1. Reduce non-critical descriptions
2. Reduce spacing and paddings
3. Reduce secondary list/auxiliary region height

Core data entry rows and primary actions must remain visible.

Prohibited:
- Changing to full-page scroll as a shortcut
- Reverting to legacy container/card stacking to hide geometry conflicts


## 5. Tokenization Requirements

Geometry values must be tokenized (single source):
- Label width token (example: `DATA_SETUP_TABLE_LABEL_WIDTH`)
- Row min-height token (example: `DATA_SETUP_TABLE_ROW_MIN_HEIGHT`)
- Action min-width token
- Compact/dense thresholds (if used)

Avoid per-widget hard-coded geometry.


## 6. Verification Gates

A table-layout task is complete only if all pass:

1. **Geometry gate**
   - No overlap
   - Baseline alignment stable
   - Critical field fit guaranteed

2. **Viewport gate**
   - Validate in declared target viewport/resolution/scaling
   - Record actual viewport conditions and visual outcome

3. **Regression gate**
   - Related UI/layout tests pass
   - `pytest -q` passes
   - Lint/diagnostics clean for changed files

4. **Visual quality gate**
   - No wasteful header/card row remains when it carries only duplicate status or count text
   - Main table/chart/work area receives the freed first-screen height
   - Screenshots show no clipped text, overlap, hidden primary action, or confusing repeated status


## 7. Completion Reporting Format

For table-layout tasks, report in this order:

1. Area/ratio budget used
2. Visual result under target viewport
3. Test/lint outcome


## 8. Non-Negotiable Rule

If constraints are unsatisfied, escalate with quantitative conflict evidence.
Do not change design direction by convenience.
