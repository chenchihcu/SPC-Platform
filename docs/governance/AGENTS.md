\# docs/governance/AGENTS.md

\## SMT SPI / SPC Statistical Analysis Platform



This repository contains the engineering implementation of the \*\*SMT SPI / SPC Statistical Analysis Platform\*\*.



AI agents working on this repository must follow the rules defined in this document.



\---



\# 1. Project Purpose



The project implements a \*\*desktop engineering analysis tool\*\* for SMT SPI process monitoring.



Core functions:



\- SPI measurement analysis

\- SPC statistical monitoring

\- capability analysis (Cp / Cpk)

\- PCB spatial analysis

\- component comparison

\- engineering visualization



The application is \*\*not a demo UI project\*\*.  

Statistical accuracy is critical.



\---



\# 2. Technology Stack



UI: PySide6 (Qt for Python). Theme and styles live under app/ui/theme/ (tokens, dark_stylesheet).

\---



\# 3. UI State: Loading (Refresh Analysis)



When the user runs "重新整理分析", the refresh button (control_panel.refresh_btn) is put into a loading state: disabled, text "計算中…", and setProperty("state", "loading"). All exit paths (success, early return, exception) restore the button in a finally block. If refresh_analysis is later moved to QThread or async, the same state must be toggled in worker start/end and in error handlers.



\# 4. UI / Theme / Layout (mandatory rules)



- **Token single source**: Colors, font sizes, and spacing must be read from app/ui/theme/tokens.py. Do not hard-code colors, font sizes, or magic numbers in pages or widgets.
- **Typography via QSS**: Do not use setFont() on individual widgets; typography is driven by the global stylesheet for consistency.
- **CJK font-weight (Qt / Windows)**: For on-screen Chinese text in global QSS (`app/ui/theme/dark_stylesheet.py`), prefer **`font-weight: 400`** (normal) and **`700` / `bold`** only. **Do not add new `500` or `600` rules**: many Windows CJK fonts (e.g. Microsoft JhengHei UI) lack true intermediate masters, so Qt/DirectWrite may **synthesize** strokes and cause uneven glyphs (e.g. overly thin “工”), fragmented strokes, or poor legibility. Prefer **font-size hierarchy** and **color tokens** for emphasis instead of 500/600. Guardrail: `tests/test_ui_font_caps.py` keeps rendered stylesheet `500`/`600` counts at **zero baseline** (reintroduction is a regression).
- **Bundled vs system fonts**: `FONT_FAMILY` prefers Noto Sans TC; the repo ships `app/assets/fonts/NotoSansTC-VF.ttf`, registered by `app/bootstrap/font_runtime.py` for Qt and Matplotlib. System fonts remain fallback only. Changing bundled fonts or the stack requires updating `docs/specs/spec_maintenance_and_alignment.md` (design tokens section) and visual check at **100% / 125% / 150%** OS scaling where feasible.
- **CJK / typography — effectiveness validation**: Prevention rules are only valid if verified on three layers (see `docs/specs/spec_maintenance_and_alignment.md` §4.1): **(1) Rule compliance** — `tests/test_ui_font_caps.py` asserts rendered `font-weight: 500`/`600` counts remain at **zero baseline**; **(2) Outcome** — any typography or QSS change that targets legibility must record **before/after** visual check (or golden screenshot) on a **Windows** host at **≥ two** of {100%, 125%, 150%} scaling, including at least one **page title** and one **body** area with CJK; **(3) Environment coverage** — note OS build, single vs multi-monitor, and remote-desktop if relevant, so regressions are not dismissed as “only my machine.”
- **Page structure**: For new or revised pages, use app/ui/widgets/page_templates.py by page type: Form pages use page_margins_and_spacing plus add_form_page_centered_content or setup_two_column_form_page; Data/List pages use page_margins_and_spacing and empty_state_label; Preview pages use the same and set stretch on the preview area.
- **Form page layout (滿版 vs 限寬置中，全域適用)**: When the form page should use the full content area (e.g. left/right columns + primary action row), use **滿版模式** — `setup_two_column_form_page(layout, page_title)`; when readability is the priority and a narrow centered column is desired, use **限寬置中** — `add_form_page_centered_content(parent, layout)`. Choose by page type and apply consistently; do not introduce ad-hoc full-width layouts that bypass page_templates.
- **Data status semantics**: Use status-pending / status-ok / status-warning / status-error; do not use red for all states.
- **UI refactor limits**: Do not change business logic or signal/slot connections; do not change objectName arbitrarily (provide a mapping if changes are required).
- **Scrolling vs full-height preview (捲動)**: When the goal is to use vertical space for previews/tables (e.g. two-column form pages), avoid wrapping the entire page in a scroll area if a narrower region can scroll instead. Unbounded lists (e.g. registered items, RefDes) may use `QScrollArea` or table scrolling; whole-page scroll is simpler but weakens “stretch to fill remaining height” for nested previews. See `.cursor/skills/smt-spi-ui-conventions/SKILL.md` (Scrolling and full-height preview). Documented layout goals: `docs/plans/document_alignment_patch_plan.md`, `docs/reports/document_alignment_report.md`.

Implementation and acceptance reference: docs/reports/ui_refactor_patch_summary.md, docs/reports/ui_self_verification_report.md. Detailed conventions: .cursor/skills/smt-spi-ui-conventions/SKILL.md.


\# 5. Safe Change Rules (analytics, services, agents)



- **Small diffs only**: Each change set must address a single, clearly scoped problem type (for example, error handling for analysis, or data import state), and must avoid mixing unrelated concerns (for example, analytics logic + UI layout).
- **Do not change public interfaces**: Do not alter function signatures (parameters, return type/structure, or names) for analytics engines (`app/analytics/*Engine`), viewmodels (`app/viewmodels/*ViewModel`), `SessionStore` public methods, `chart_router.py` public APIs, or `ReportService` methods unless a spec or this file explicitly requires it. Behavioural extensions should be implemented via additional fields in existing dict payloads or wrapper functions, not by breaking callers.
- **SPC formulas and constants are immutable**: All SPC and capability formulas and constants defined in `docs/governance/SPC_RULES.md` (for example, d2=1.128, Cp/Cpk/Pp/Ppk definitions, interpretation thresholds) are the single source of truth and must not be changed or redefined in code. Analytics changes may only add validation or error messaging, not alter the math.
- **Adjusting SPC thresholds requires spec update first**: Any change to data requirements (for example, minimum sample size) or interpretation thresholds must be reflected in `docs/governance/SPC_RULES.md` or a dedicated spec document before updating code and tests.
- **No new bare `except Exception`**: New code must not introduce plain `except Exception:` blocks. Existing ones must be gradually tightened to specific exception types or changed to log context and re-raise, or return structured errors to callers.
- **No silent `pass` in error paths**: Do not use bare `pass` in exception handlers or critical control paths. If an error is intentionally ignored, it must have a clear inline comment explaining why, or at least a debug-level log entry.
- **Errors must propagate in a visible way**: Analytics, report export, and data import failures must surface a meaningful message or metadata to the caller (ViewModel/UI/ReportService). UI or reports must be able to distinguish “no data / process OK” from “analysis failed”.
- **UI layout changes require design reference**: Page layout, widget structure, and spacing must not be changed unless there is an explicit design document (for example, docs/specs/ui_target_layout.md) or owner instruction. New or revised pages should use `page_templates.py` and existing tokens rather than custom layouts.
- **Do not rename UI objectName/state semantics casually**: Do not change `objectName`, `state`, or `class` properties used by QSS or state semantics unless you also update all dependent QSS, docs (for example, `docs/specs/ui_state_semantics.md`), and provide a clear mapping from old to new.
- **Tests are mandatory for behavioural changes**: Any change that can affect observable behaviour (error messages, payload structure, chart availability) must be accompanied by updated or new tests, and `pytest -q` must pass before the change is considered complete.
- **Do not cross problem boundaries in one phase**: When working through phases (for example, Phase 1: error handling, Phase 2: data/import consistency), keep each phase strictly limited to its problem family. Optimisations, UI polish, or refactors belong in their own explicitly-scoped phase.


\# 6. Planning and owner confirmation (agents)


Before producing or committing to a **full implementation plan**, pause and ask the user when:

- The change involves a **major directional decision** (for example: whole-page scroll vs scroll only in overflow regions, public API shape, architecture split).
- The plan depends on **unconfirmed assumptions** (for example: target resolution, product priority between competing layouts).

Use a **short multiple-choice** format (2–6 options, last option “Other: …”) and continue only after the user replies. This does **not** block small, well-scoped fixes that are already specified in docs/governance/AGENTS.md, docs/governance/SPC_RULES.md, or an approved design doc.


\# 7. Chart Statistical Integrity Rules (strict, mandatory)

- **Time-first ordering for trend statistics**: For Run/EWMA/CUSUM computation, input data must be sorted by time-like columns first. `BoardNo`/`PanelId` may only be used as fallback when time-like columns are unavailable.
- **Natural sort for board decisions**: Any logic for `首件`/`末件` or board-order decisions must use natural sort. Plain string lexicographic sort is prohibited for board IDs.
- **Single-source payload slicing/merge**: Chart payload slicing and merge rules must be defined in one shared source (registry/helper). UI and report paths must not implement parallel duplicate merge logic for the same chart semantics.
- **Normalization toggle consistency**: A single normalization toggle must map to one consistent formula within the same chart family. If different formulas are needed, split into separate toggles/labels and document each formula explicitly.
- **Control-limit unit semantics must be explicit**: Chart legends/annotations must explicitly show control-limit units/meaning (for example `hσ`). Silent semantic changes in labels are prohibited.
- **Fallback must be visible**: Statistical fallback behavior (for example `mu0` fallback) must be visible in metadata and chart annotation/tooltips; no silent fallback for analytics decisions.
- **Downsampling transparency**: Any display downsampling must expose metadata (`n`, `displayed_n`, `downsample_step`, `sampled_for_display`) and show a user-visible cue in chart/report output.
- **Exception workflow for compatibility debt**: Temporary deviations from these rules require all of: (1) inline TODO with owner/date, (2) explicit risk note in docs, (3) regression test coverage, and (4) owner approval before merge.

\# 8. Chart Visual Readability & Layering Rules (strict, mandatory)

- **Single style entrypoint**: Matplotlib figure/axes background and grid style must be applied via `app/charts/base_chart.py` and theme tokens; do not define per-chart background styles ad-hoc.
- **Layered background semantics**: Keep explicit separation between chart page background and plotting-area background (page vs axes). Avoid pure white-on-white flattening that weakens density perception.
- **Token-only chart colors**: Prefer `app/ui/theme/tokens.py` semantic chart colors; avoid one-off hard-coded colors in chart files unless a documented per-feature palette is required.
- **Low-density visibility is required**: Density/hexbin/heatmap charts must preserve contrast in low-count regions and keep colorbar text/meaning readable.
- **Visual change must preserve statistical meaning**: Palette, legend, and annotation updates must not change formula semantics, thresholds, or interpretation wording.
- **Chart visual changes require tests**: Readability-related rendering behavior (for example colorbar existence, metadata-linked annotation, shared style application) must be covered by tests when changed.

# 9. Data Integrity & Scaling Limits (strict, mandatory)

- **Atomic File I/O Only**: All registry, configuration, and critical file writes must be atomic. Never use `with open("w")` directly on a target file. Write to a `.tmp` file and use `os.replace()` to prevent data destruction during crashes or OS file locks.
- **Deduplicate Before Merging**: Always call `.drop_duplicates(subset=[...])` on lookup DataFrames (e.g., coordinate data) before a `pd.merge()` to prevent catastrophic Cartesian memory explosions on O(10^7) row datasets.
- **Filter Infinite Values Safely**: Always explicitly sanitize `np.inf` and `-np.inf` (using `.replace([np.inf, -np.inf], np.nan)`) before `.dropna()` in SPC engines to prevent infinite bounds propagation to computations and Matplotlib axes.
- **Escape Unsafe Column Strings**: Never inject user-controlled data or Pandas column names directly into HTML/report preview templates or PPTX/report rendering paths without using `html.escape()` or the target renderer's structured text API.

# 10. PySide Lifecycle & UI Safety Rules (strict, mandatory)

- **Worker Cancellation & Teardown**: Any `QThread` objects MUST be gracefully terminated using `.cancel()`, `.wait()`, and `.deleteLater()` inside an overridden `QMainWindow.closeEvent()`. Emitting signals to destroyed C++ window objects will crash PySide heavily.
- **Asynchronous Unblocking**: Never call `QThread.wait()` directly on the main UI thread during active operational transitions. This freezes the event loop. Schedule thread cleanup asynchronously.
- **Headless Memory Deallocation**: When instantiating PySide Widgets (e.g., `QTableWidget`, Matplotlib `BaseChart`) without a parent for background tasks like PPTX/report chart generation, you MUST explicitly call `widget.deleteLater()`. Dropping the Python reference is insufficient and will exhaust OS GDI handles.
- **Avoid Box-Model Jello Jiggling**: In PySide `dark_stylesheet.py`, when specifying `:selected` states that introduce border widths (e.g., `border-left: 3px`), the base unselected state MUST include a corresponding transparent border (`border-left: 3px solid transparent`) to prevent text jitter across rows upon selection.

# 11. AI Problem-Solving Protocol (Mandatory Workflow)

- **Integrated workflow (single entry)**: For **L2** (non-trivial) issues—anything not an obvious single-file typo—follow the **ordered steps and gates** in **`docs/specs/issue_resolution_workflow.md`**. **Structured reply skeleton** (copy-paste): `docs/specs/ai_agent_response_template.md`. **Cursor minimal gates**: `.cursor/rules/agent-residence-minimal.mdc` (default **Apply Intelligently** per [Cursor Rules](https://cursor.com/docs/context/rules); for **every chat session** enforcement, set the rule to **Always Apply** in Cursor — see `.cursor/rules/README.md`). Output Scope/Evidence/RCA/Blast/Verify **before** large diffs; full detail remains in this file and `docs/plans/ai_change_and_planning_discipline.md`.
- **Verification Before Resolution**: AI agents MUST NOT propose or implement a structural code fix based purely on a "hypothetical" root cause. Do not guess. You must first use diagnostic prints, logs, or rigorous code tracing to precisely identify the failing line or bad data shape.
- **Lateral Expansion (Blast Radius Check)**: Whenever a bug is found and fixed (e.g., missing `QScrollArea`, missing `setWordWrap`, `except Exception:` silences), the AI MUST proactively search the entire codebase (`grep_search`, `list_dir`) for other pages, components, or modules suffering from the exact same anti-pattern. Do not limit fixes to the single page mentioned by the user. A fix is only complete when it is rolled out globally.
- **Cure the Disease, Not the Symptom**: If a UI component crashes because it received `NaN` or `None`, do not simply wrap the UI component in an `if x is not None` guard. You must trace the data stream backwards to the Loader/Engine upstream and fix the data mutation at its source.

# 12. Specification maintenance and alignment

- **Governance document**: `docs/specs/spec_maintenance_and_alignment.md` defines when specs, plans, and code must be reconciled (UI acceptance criteria, data/chart contracts, `docs/governance/SPC_RULES.md` thresholds, UI state / objectName changes, plan lifecycle). **Operational entry** for fixing problems end-to-end: **`docs/specs/issue_resolution_workflow.md`**. **CJK / font-weight remediations** must also satisfy **§4.1 effectiveness validation** (rule freeze + Windows visual + environment notes).
- **Authority**: When a plan or design doc disagrees with merged code behavior, treat **verifiable code behavior** as evidence until specs are explicitly updated; do not assume the plan is correct without implementation proof.
- **Cross-reference**: `docs/specs/ui_design_spec.md` §22, `docs/specs/data_contract.md` §11, and `docs/specs/ui_state_semantics.md` §4 point to the same governance rules. **`docs/specs/issue_resolution_workflow.md`** is the **operational** end-to-end sequence for problem solving (gates, L1/L2, checklist).

# 13. Planning discipline, root cause, and coupling (anti-hypothesis)

- **Full rules**: `docs/plans/ai_change_and_planning_discipline.md` (Preflight checklist before multi-file plans, RCA before countermeasures, blast radius / coupling). Plan template: `.cursor/plans/README.md`.
- **No cross-module edits from guesses**: Do not change module B based on an unverified assumption about module A. Confirm with read/grep/trace, list upstream/downstream in the plan.
- **Evidence before "already implemented" claims**: Plans must not state a stack or UI state is live without code references (paths + behavior). Stale examples are recorded in `docs/reports/document_alignment_report.md`.
- **Root cause before symptom patches**: Same rigor as §11 — trace data/call chain; avoid only adding `if x is None` or broad `except` at the leaf without fixing the source.
- **Lateral expansion for related failures**: When fixing one instance of a pattern, search the repo for the same pattern (§11 Lateral Expansion); coupling changes (payload keys, public APIs) require caller search.
- **Cursor rule**: `.cursor/rules/ai-planning-and-root-cause.mdc` applies to plan files and alignment docs.

# 14. UI Acceptance Priority (mandatory, execution order lock)

- **Execution order is fixed for UI/layout tasks**: Use this order and do not invert it:  
  **(1) Real user viewport conditions** (actual available window area, scaling, sidebar occupancy)  
  **> (2) Visual acceptance result** (can/cannot fully view required fields, unintended scrollbar presence)  
  **> (3) Automated tests/lint** (regression guard only).
- **Do not close a UI task on tests alone**: Passing pytest/lint is insufficient if the UI is not validated under the user's actual viewport conditions.
- **Conflict handling is mandatory**: If approved plan baseline (for example `1920x1080`) conflicts with actual viewport evidence, pause and ask owner which baseline has priority before further edits.
- **Completion report format is mandatory for UI tasks**: Report in this exact order:  
  `Real viewport conditions -> Visual acceptance outcome -> Test/lint results`.

# 15. Unified Governance Integration (all clauses consolidated)

- **Single-source enforcement**: This file is the unified governance source. New rules must be integrated here and cross-referenced by section ID.
- **No semantic override by reordering**: Section reordering, regrouping, or index cleanup must not change the original rule meaning.
- **Conflict precedence (global)**: When rules appear to conflict, resolve by this order:  
  **(1) Statistical/data integrity safety** (`§5`, `§7`, `§9`)  
  **> (2) UI safety/lifecycle and acceptance** (`§4`, `§10`, `§14`)  
  **> (3) workflow/planning discipline** (`§11`, `§12`, `§13`)  
  **> (4) local style/format preferences**.
- **Integrated execution gates (all implementation tasks)**:

  | Gate | Pass Condition | On Fail |
  |------|----------------|---------|
  | Gate A (Scope) | target problem family is defined and unrelated changes are rejected with evidence | blocked; no further steps permitted |
  | Gate B (Evidence) | real code path / runtime evidence supports current-state claims before structural fix | supplement evidence before continuing |
  | Gate C (RCA) | root cause is confirmed and not a symptom-only hypothesis | supplement RCA, then re-enter Gate B |
  | Gate D (Blast Radius) | repo-wide same-pattern expansion check and side-effect boundary are complete | re-scope before continuing |
  | Gate E (Verify) | required tests + lint + domain-specific acceptance checks are executed with captured results, or marked `not verified` | cannot mark done |
  | Gate F (Report) | completion output follows mandatory reporting order and records residual risk/risk-ledger status | cannot mark done |

  Any `Pass` without evidence is treated as `Fail`.
- **Unified completion condition**: A task is complete only when all applicable gates pass; partial pass is not completion.

# 16. UI Hard-Stop Rules (added by owner request)

- **Hard-stop #1 (non-closable)**: Any UI/layout change that violates the execution order in `§14` is automatically **NOT DONE** and must not be closed.
- **Hard-stop #2 (evidence required)**: UI/layout completion requires real viewport evidence (at minimum: viewport condition record + visual outcome statement; screenshot strongly recommended).
- **Hard-stop #3 (plan preflight for UI)**: Every UI/layout plan must explicitly declare target viewport conditions and acceptance thresholds before implementation.
- **Hard-stop #4 (combined enforcement)**: The three hard-stop conditions above are cumulative; satisfying only one or two is insufficient.

# 17. Table-Layout Quantitative Design Rules (hard, mandatory)

- **Design intent lock (non-negotiable)**: For Data Setup and owner-designated engineering forms, the required style is **one-page table layout** (表格式), **no full-page vertical scrolling**, and **de-containerized visual structure** (no card-stack semantics as the primary layout model).
- **Area budget is mandatory before implementation**: Any table-layout redesign must explicitly define page-level area budget (`A_total`) and per-region budgets (`A_left`, `A_right`, `A_bottom` or equivalent). Layout decisions without quantitative area budgeting are invalid.
- **Runtime budget pass is mandatory**: Table-layout pages must execute a runtime geometry budget pass on resize/show (compute region width/height budget first, then apply layout). Pure heuristic stretch-only layout without explicit computed budget is non-compliant.
- **Field geometry ratios are mandatory**: Each form row must define and enforce minimum geometry constraints for label/value/action regions (for example `Lw`, `Iw`, `Aw`, `Rh`). Use tokenized constraints; avoid per-widget ad-hoc geometry.
- **Text-fit constraints are mandatory**: Label and input regions must be sized from text metrics (or documented equivalent) to prevent semantic truncation in core fields. If clipping risk exists, adjust layout budget first; do not silently accept clipped critical labels.
- **Combination optimality requirement**: Layout is considered acceptable only when region composition satisfies all three simultaneously: (1) no overlap, (2) no critical-field clipping, (3) stable baseline alignment across same-role rows.
- **Compression order is fixed**: When viewport height is insufficient, compression must follow this order:  
  **(1) reduce non-critical description area -> (2) reduce spacing/padding -> (3) reduce secondary list region height**.  
  Core action controls and key data-entry rows must remain visible.
- **No design-direction override by convenience**: Agents must not revert to legacy container/card stacking or full-page scroll as a shortcut when table layout is difficult. If constraints are unsatisfied, escalate with quantitative conflict evidence instead of changing direction.
- **Verification gates for table layout**: UI task completion requires all:  
  **(a)** geometry checks (no overlap / aligned baselines),  
  **(b)** viewport check under declared target resolution/scaling,  
  **(c)** regression tests and lint pass.
- **Completion reporting order (table-layout tasks)**:  
  `Area/ratio budget used -> Visual result under target viewport -> Tests/lint outcome`.
- **Diagnostics for validation**: When `SPC_UI_DIAGNOSTICS` is enabled, table-layout pages must expose/log the latest computed budget values (at least region widths/heights and key ratio) for owner verification.
- **Specification reference (single source for quantitative details)**: `docs/specs/table_layout_quantitative_spec.md` defines formulas, geometry constraints, compression order, and verification gates used to execute this section.
