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

## 3. Universal Base Rules (pointer — do not restate here)
本檔只保留 **SPC 專屬 delta**;通用 Qt/UI 規則以 Institution 正本為準,不在此重述
(2026-07-08 裁剪:原 §4 T-3/T-4、§5、§6 規則句、§7 矩陣、§9 與正本逐字重複,已移除):

- 正本:`C:/Dropbox/AI_Coding_Agent_Governance/Institution/06-ui-ux-universal.md`
  - §3 視覺與排版:token 集中管理、語意命名(`TEXT_DISABLED` vs `TEXT_MUTED` 不互換)、不寫死 hex / 裸 px。
  - §8 桌面 Qt:QSS 不支援屬性清單、`setPalette()` 先於 `setStyleSheet()`、逐元件狀態矩陣
    同一 commit 補齊、固定尺寸幾何稽核公式、`role`/property-based 樣式隔離、
    f-string CSS 禁邏輯運算式。
- 本 repo 的 Cursor 全文副本(自動載入,由 `sync-ai-rules.ps1` 散佈,勿手改):
  `.cursor/rules/ui-ux-universal.mdc`。Claude Code 端由全域 CLAUDE.md @import 正本。
- 衝突時以 Institution 正本為準;本檔其餘各節只寫「正本之上」的專案具體化。

## 4. Pre-Change Checklist (must pass before coding)
- Confirm required tokens exist in `app/ui/theme/tokens.py`.
- Confirm target widget states to be edited (`default/hover/focus/disabled/...`).
- Confirm Qt QSS capability (unsupported CSS must not be used; list = 正本 §8).

## 5. Token Contract Rules (SPC deltas)
### T-1 Token First
Any new color/spacing/font/size value must be defined in `app/ui/theme/tokens.py` first.
No raw hex or bare px values outside `tokens.py`.

### T-2 Three Rendering Contexts
Tokens must cover all required targets:
- Qt QSS (default token names)
- Matplotlib (`CHART_PALETTE_*`)
- Report visuals (`RPT_*`)

(語意命名與 DISABLED/MUTED 區分 → 正本 §3,不重述。)

## 6. SPC Qt Concretizations(正本 §8 之上的專案具體化)
- **Focus ring token**:正本 §8 的 `border: 2px solid <accent>` 在本專案 = `{ACCENT_PRIMARY}`。
- **Required QPalette roles**(正本只要求「含 disabled 覆寫」,本專案固定清單):
  `Window`, `WindowText`, `Base`, `AlternateBase`, `Text`, `Button`, `ButtonText`,
  `Highlight`, `HighlightedText`, `PlaceholderText`,
  plus Disabled overrides for `WindowText`, `Text`, `ButtonText`, `Button`, `Base`.
- **狀態矩陣具體清單**(`QPushButton` / `QLineEdit` 已由正本 §8 明列;其餘如下,同 commit 補齊):
  - `QComboBox`: default / hover / focus / disabled
  - `QCheckBox`: default / hover / indicator:focus / disabled
  - `QTabBar::tab`: default / hover / selected / disabled
  - `QListWidget::item`: item / hover / selected / selected:hover
- **No magic numbers(專案加嚴)**:
  - If offset math is used (`TOKEN_X - 4`), replace with named token or add concise rationale comment.
  - Replace Qt internal literal max size with named constant (e.g., `QT_MAX_WIDGET_DIM`).

## 7. Code Quality Rules (UI Scope)
> 2026-07-10 歸位:本節內容移至 `.claude/rules/code_audit_rules.md` **P11**(程式衛生屬稽核規則,非 UI/theme delta;裸例外一項屬全域 A 類)。本檔不重述。

## 8. Delivery Gates (must run before completion)
- `python scripts/qt_audit.py app/`
- `python -m ruff check .`
- `python -m mypy app`
- `python -m pytest -q`
- `python scripts/check_launch.py`

If any command is unavailable, report `not configured` or `not available`.

## 9. Frozen Design Decisions
Do not modify without explicit owner instruction:
- `app/ui/main_window.py`: `NAV_PHASES` labels must remain empty strings `""`.

## 10. Expected Task Report Format
When finishing UI-related tasks, include:
- changed files,
- root cause / purpose,
- gates executed + results,
- residual risks/assumptions,
- rollback hint for risky edits.

## 11. UI/UX RCA & 驗證規則 (專屬加嚴)

### 11.1 RCA 診斷強制項目
當任務涉及 `ui` 類型時，RCA 必須包含：
- **幾何衝突分析 (Geometric Audit)**：若元件有固定尺寸 (`setFixedWidth`, `setFixedHeight`)，必須計算 `(總寬/高) - (內距 padding) - (邊框 border)`，確保剩餘空間足以顯示內容（公式同正本 §8）。
- **全局樣式追蹤 (Theme Trace)**：檢查近期 `theme.py` 或全局 CSS 的變更，是否與目標元件的區域樣式產生覆蓋或衝突。
- **佈局伸縮性檢查 (Layout Elasticity)**：確認父容器是否限制了子元件的擴展 (Expanding)，導致內容被壓縮。

### 11.2 計畫與驗證強制要求
- **Plan 階段**：必須明確列出受影響元件的「空間計算結果」，而非僅描述「修改字串或符號」。
- **Verify 階段**：
    - 必須驗證在「最小可用寬度」下內容是否會被切除 (Clipped)。
    - 若修改涉及圖示，必須驗證其在不同系統環境下的渲染一致性，優先使用 `role` 型樣式隔離（Style Isolation）而非直接修改全局變體。
