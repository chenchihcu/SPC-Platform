---
paths:
  - app/ui/**/*
  - app/charts/**/*
  - app/services/report_*
---
# UI & Theme Harness Profile for SPC Platform

This file defines the **UI/theme implementation harness** used by AI assistants.
Project-level governance stays in `AGENTS.md`.

## 1. Harness Goal
Prevent regressions in UI consistency, Qt compatibility, and theme contract stability by enforcing:
- explicit design-token contracts,
- complete interactive state definitions,
- auditable pre-delivery checks.

## 2. Applicability
Apply these rules when a task touches any of:
- `app/ui/**`
- `app/charts/**` (color/style related)
- `app/services/report_*` (report visual tokens)
- `app/ui/theme/**`

## 3. Pre-Change Checklist (must pass before coding)
- Confirm required tokens exist in `app/ui/theme/tokens.py`.
- Confirm target widget states to be edited (`default/hover/focus/disabled/...`).
- Confirm Qt QSS capability (unsupported CSS must not be used).

## 4. Token Contract Rules
### T-1 Token First
Any new color/spacing/font/size value must be defined in `tokens.py` first.
No raw hex or bare px values outside `tokens.py`.

### T-2 Three Rendering Contexts
Tokens must cover all required targets:
- Qt QSS (default token names)
- Matplotlib (`CHART_PALETTE_*`)
- Report visuals (`RPT_*`)

### T-3 Semantic Naming
Use intent-based names, not appearance-based names.
- Correct: `TEXT_DISABLED`, `TEXT_MUTED`, `SURFACE_ACTIVE`
- Avoid: `GREY_DARK`, `BLUE_LIGHT`

### T-4 Disabled vs Muted
`TEXT_DISABLED` is for non-interactive/disabled controls.
`TEXT_MUTED` is for secondary but active-readable content.
Do not interchange.

## 5. Qt QSS Compatibility Rules
Unsupported in Qt QSS: `box-shadow`, `transition`, `animation`, `transform`, `outline`, CSS border-triangle hacks, `opacity`.

Enforced behavior:
- Use `border` + contrast for emphasis.
- Use `QPropertyAnimation` in Python when motion is required.
- Use `rgba()` instead of `opacity`.
- Focus ring standard: `border: 2px solid {ACCENT_PRIMARY}`.

## 6. Theme Application Rules (QPalette + QSS)
- Always apply `setPalette()` before `setStyleSheet()`.
- Required QPalette roles: `Window`, `WindowText`, `Base`, `AlternateBase`, `Text`, `Button`, `ButtonText`, `Highlight`, `HighlightedText`, `PlaceholderText`, plus Disabled overrides for `WindowText`, `Text`, `ButtonText`, `Button`, `Base`.

## 7. Interactive State Matrix Rules
For each edited interactive widget, define all applicable states in same commit.

Minimum matrix:
- `QPushButton`: default / hover / focus / disabled / pressed / checked
- `QLineEdit`: default / hover / focus / disabled / read-only
- `QComboBox`: default / hover / focus / disabled
- `QCheckBox`: default / hover / indicator:focus / disabled
- `QTabBar::tab`: default / hover / selected / disabled
- `QListWidget::item`: item / hover / selected / selected:hover

No partial-state merges.

## 8. No Magic Numbers Rules
- Move all UI px values to tokens.
- If offset math is used (`TOKEN_X - 4`), replace with named token or add concise rationale comment.
- Replace Qt internal literal max size with named constant (e.g., `QT_MAX_WIDGET_DIM`).

## 9. String/CSS Generation Safety
- Do not place logical expressions like `{TOKEN_A or TOKEN_B}` in f-string CSS braces.
- Compute fallbacks before formatting.

## 10. Code Quality Rules (UI Scope)
- No bare `except:`.
- No debug `print()`; use logger.
- Public methods should include docstrings.
- Function signatures should include return type hints.

## 11. Delivery Gates (must run before completion)
- `python scripts/qt_audit.py app/`
- `python -m ruff check .`
- `python -m mypy app`
- `python -m pytest -q`
- `python scripts/check_launch.py`

If any command is unavailable, report `not configured` or `not available`.

## 12. Frozen Design Decisions
Do not modify without explicit owner instruction:
- `app/ui/main_window.py`: `NAV_PHASES` labels must remain empty strings `""`.

## 13. Expected Task Report Format
When finishing UI-related tasks, include:
- changed files,
- root cause / purpose,
- gates executed + results,
- residual risks/assumptions,
- rollback hint for risky edits.

## 14. UI/UX RCA & 驗證規則 (專屬加嚴)

### 14.1 RCA 診斷強制項目
當任務涉及 `ui` 類型時，RCA 必須包含：
- **幾何衝突分析 (Geometric Audit)**：若元件有固定尺寸 (`setFixedWidth`, `setFixedHeight`)，必須計算 `(總寬/高) - (內距 padding) - (邊框 border)`，確保剩餘空間足以顯示內容。
- **全局樣式追蹤 (Theme Trace)**：檢查近期 `theme.py` 或全局 CSS 的變更，是否與目標元件的區域樣式產生覆蓋或衝突。
- **佈局伸縮性檢查 (Layout Elasticity)**：確認父容器是否限制了子元件的擴展 (Expanding)，導致內容被壓縮。

### 14.2 計畫與驗證強制要求
- **Plan 階段**：必須明確列出受影響元件的「空間計算結果」，而非僅描述「修改字串或符號」。
- **Verify 階段**：
    - 必須驗證在「最小可用寬度」下內容是否會被切除 (Clipped)。
    - 若修改涉及圖示，必須驗證其在不同系統環境下的渲染一致性，優先使用 `role` 型樣式隔離（Style Isolation）而非直接修改全局變體。
