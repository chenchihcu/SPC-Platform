# Document Inventory Master

- Snapshot date: `2026-05-25`
- Sync evidence: `docs/reports/document_sync_full_audit_2026-05-25.md`
- Scope: active root documentation, `docs/**`, `.github` text/workflow files, and test README files that encode commands or contracts.
- Excluded from active-sync counting: `.venv/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `node_modules/`, `Outputs/`, `archive/`, generated caches, screenshots, and scratch/runtime data.

## Count by active sync surface

| surface | count | disposition |
|---|---:|---|
| root documentation (`README.md`, `AGENTS.md`, `AI_RULES.md`, `CLAUDE.md`, `code_review.md`, `LESSONS_LEARNED.md`, `requirements.txt`) | 7 | active |
| root config/source evidence (`pyproject.toml`, `.github/workflows/pytest.yml`) | 2 | evidence |
| `.github/` text/workflow files | 2 | active/evidence |
| `docs/` Markdown/text files after this sync | 62 | active docs + historical snapshots |
| test README files | 4 | active contract notes |

## Alignment rules used in this snapshot

1. **Current-contract-first**: current architecture and contracts are sourced from live code/config plus authoritative docs:
   - `README.md`
   - `docs/specs/project_architecture.md`
   - `docs/specs/data_contract.md`
   - `docs/specs/spec_maintenance_and_alignment.md`
   - `.github/workflows/pytest.yml`
2. **Historical reports stay historical**: time-stamped audits and closeout reports may retain superseded wording when `docs/reports/README.md` marks them as snapshots.
3. **No behavior sync by documentation**: if a doc implies a needed runtime or release-gate behavior change, stop for implementation approval instead of changing code.
4. **Safe deletion only**: no active documentation file was deleted or moved in this pass. Superseded governance v2.1 remains active because `scripts/check_governance_alignment.py` requires it.

## Current classifications

### sync

- `README.md`: current architecture heading aligned to the 2026-05-24 architecture/performance snapshot.
- `docs/README.md`: snapshot date, process-statistics wording, and latest sync audit entry updated.
- `docs/reference/platform_overview.md`: UI shell wording aligned to the current left-sidebar workflow and hidden `QTabWidget#workflowTabs`.
- `docs/specs/data_contract.md`: Layer 6 workorder context clarified for `supplier_work_order_no` / `outsource_work_order_no` and compatibility-only `work_order_no`.
- `docs/open-questions.md`: active risk ledger updated from latest release evidence; `Watchlist #7` remains monitoring, not an active blocker.
- `docs/governance/AGENTS.md`: bundled font guidance aligned to `app/assets/fonts/NotoSansTC-VF.ttf` and `font_runtime.py`.
- `docs/specs/project_architecture.md`, `docs/specs/ui_design_spec.md`, `docs/specs/ui_target_layout.md`, `docs/specs/ui_state_semantics.md`: workflow and DiagnosticPage terminology aligned to the current visible-copy contract.
- `docs/decision-log.md`: this sync recorded as a new decision.
- `tests/fixtures/golden/README.md`: broken relative link to release-validation conftest fixed.
- `docs/reports/README.md`, `docs/reports/document_inventory_master.csv`: refreshed to this snapshot.

### delete / move candidate

- None executed.
- `docs/governance/GLOBAL_PLAN_FRAMEWORK_V2_1.md` was reviewed as a superseded active file, but kept because `scripts/check_governance_alignment.py` reads it and validates its superseded notice.

### keep

- `docs/governance/SPC_RULES.md`: formula/threshold authority; no statistical contract drift was changed.
- `docs/specs/project_architecture.md`: aligned with current workflow navigation, report service split, and validation baseline.
- `docs/specs/release_validation_*.md`: release command contracts still match scripts; `Watchlist #7` status details live in `docs/open-questions.md`.
- `docs/reports/*.md`: historical snapshots retained with `docs/reports/README.md` caveat.
- `archive/**`: historical/recoverable archive; not freshened during active docs sync.

### exclude

- `.venv/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `node_modules/`: dependency/cache output.
- `Outputs/**`: generated validation, release, and audit artifacts; used as evidence only.
- `archive/**`: historical archive, not active docs.
- `tmp/**`, screenshots, generated images, and runtime scratch output: outside active documentation sync.
