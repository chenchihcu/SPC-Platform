# SPC Audit Checklist

## Prep

- Read `AGENTS.md` / `SPC_RULES.md` if present; then README and docs (e.g. `docs/architecture.md`, `docs/project_architecture.md`, `docs/outstanding-items.md` if present).
- In a confirmed fix phase, baseline with the affected focused test. Use subsystem or full pytest only when the repository invalidation policy requires it.
- From skill root run: `python scripts/scan_repo_quality.py <repo-root> --inventory-spc`. The scanner auto-detects `src/` and `app/` production trees.
- Reconcile the printed statistical entrypoints with the chart registry, payload assembler, UI/report consumers, tests, formula authority, ordering policy, and any DB-backed semantic gate.

## Triage

- Triage findings in order: bytecode → broad except → encoding → silent chart-skip → root temp → packaging/README mismatch.

## Fix (smallest safe scope; preserve SPC/Cp/Cpk and pass/fail behavior)

- Remove bytecode coupling before UI polish.
- Replace broad exception swallowing with expected exception types (or log and re-raise).
- Fix true source encoding corruption (private-use/replacement codepoints) via codepoint inspection, not terminal rendering.
- Fix silent chart-skip paths; do not swallow chart renderer failures.
- Quarantine root temp artifacts under `tmp/` (move, do not delete unless user asks).
- Fix packaging or README/runtime mismatches if any.

## Verify

- Re-run only invalidated gates: focused tests first, subsystem validation next, and full pytest/UI only when V3 or the repository policy requires them.

## Report

- Document findings, patches, and verification (e.g. `pytest -q` result) in e.g. `docs/spc_code_audit_report.md`.

## Out of scope

- Do not: change SPC/Cp/Cpk formulas; style-only refactors; mix problem types in one patch.
