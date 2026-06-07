# Qt Release Checklist — SPC Platform

Use this checklist before every release or delivery. Supplements the standard `validate-production-release` skill with Qt/PySide6-specific quality gates.

---

## Quick Run

```bash
# Run the full automated audit (all categories must be 0)
python scripts/qt_audit.py app/

# Run with verbose output to see file-level details
python scripts/qt_audit.py app/ --verbose
```

**Expected output when ready:**

```
  ALL CLEAR — ready for delivery
```

---

## Manual Checklist (in addition to automated audit)

### Design Token System

- [ ] Zero raw hex values outside `app/ui/theme/tokens.py`
- [ ] New colors added this release are in `tokens.py` with semantic names
- [ ] Chart palette colors use `CHART_PALETTE_*` prefix
- [ ] HTML report colors use `RPT_*` prefix

### Qt QSS

- [ ] No `box-shadow`, `transition`, `animation`, `transform` in QSS strings (Qt ignores silently)
- [ ] No CSS border-trick triangles (`width:0; height:0; border-*`) in `::down-arrow` rules
- [ ] All new interactive widgets have complete state matrix: `:hover` / `:focus` (2px) / `:disabled` / `:pressed`
- [ ] Focus ring is `border: 2px solid {ACCENT_PRIMARY}` everywhere — no 1px, no `outline`

### Qt Theme Application

- [ ] `apply_dark_theme()` (or equivalent) calls `setPalette()` **before** `setStyleSheet()`
- [ ] `QPalette` covers Disabled group: `WindowText`, `Text`, `ButtonText`, `Button`, `Base`

### Python Code Quality

- [ ] All public methods have docstrings
- [ ] All public methods have `-> ReturnType` annotation (including `-> None`)
- [ ] No bare `except:` — all exceptions are typed (`except OSError`, `except ValueError`, etc.)
- [ ] No `print()` statements — use `logging.getLogger(__name__)`

### Layout & Magic Numbers

- [ ] All pixel values are token references — no bare integers in `setFixedWidth()`, `setMinimumHeight()`, etc.
- [ ] `setMaximumWidth(QT_MAX_WIDGET_DIM)` used instead of `setMaximumWidth(16777215)`
- [ ] No `SOME_TOKEN - N` offset expressions without named token or comment

---

## Audit Script Checks Reference

| Check | Rule | Tolerance |
|---|---|---|
| Raw hex outside tokens.py | T-1 | 0 |
| Magic pixel values | M-1 | 0 |
| Python syntax errors | — | 0 |
| `bare except:` | C-1 | 0 |
| `debug print()` | C-4 | 0 |
| Public methods without docstring | C-2 | 0 |
| QSS :hover without :disabled | I-1 | 0 |
| f-string `or` fallback bug | F-1 | 0 |
| Public methods missing `-> type` | C-3 | 0 |

---

## Rules Reference

See `AI_RULES.md` in the project root for the full rule set with rationale.
