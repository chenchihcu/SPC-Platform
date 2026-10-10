---
name: spc-code-audit
description: "以證據化 A-E 發現稽核或修復 SPC/SPI analytics 程式碼（統計語意、finite-value、ordering、payload parity）。Use when 對本 repo SPC/SPI analytics 程式碼做深度稽核或修復。Do NOT use for 通用 OWASP/SAST（改用 audit-codebase-security）、單一 runtime bug（改用 debug-and-fix-bug）或任務路由（改用 spc-change-router）。"
---

# SPC Code Audit

Use this skill for deep audit and recovery work in SPC / SPI engineering repos where correctness and traceability matter more than broad rewrites.

## Reference Routing

- Read `references/structured-health-audit.md` only for systematic code-health audits, report-first review, or requested A-E findings.
- Read `references/spcspi-platform-v2-profile.md` only when the repository name, its rules, or matching code symbols establish that the target is `spcspi platform v2`.
- Read `references/checklist.md` during a confirmed fix phase or final verification pass.

## Workflow

1. If the repo has `AGENTS.md` or `SPC_RULES.md`, read them first; all triage and patches must comply. Then read `README.md` and relevant docs (e.g. `docs/architecture.md`, `docs/project_architecture.md`, `docs/outstanding-items.md` if present) before changing code.
2. Choose the mode. Default to audit-only and report-first. Repair code only when the current user request explicitly authorizes fixes and the finding is supported by evidence.
3. Audit-only work does not run full pytest first. In a confirmed fix phase, start with the affected focused test; use subsystem validation next. Run full pytest only when the repository V3 conditions apply (shared/cross-subsystem/public contract/release, weak impact oracle, or targeted failure).
4. Run the bundled scanner from the **skill installation directory**: `python scripts/scan_repo_quality.py <repo-root> --inventory-spc`. It auto-discovers production Python under `src/` and `app/`, prints candidate statistical entrypoints, and checks quality plus raw analytics slices that drop NaN without explicitly removing `+/-inf`.
5. Triage in this order:
   - bytecode/runtime coupling
   - broad `except Exception` handlers
   - true source encoding corruption (private-use or replacement codepoints)
   - silent chart-skip paths that hide renderer failures
   - root-level temp or decompiled artifacts
   - packaging or README/runtime mismatches
6. Before calling code dead or unused, search the full repository and account for Qt signals/slots, decorators, registries, reflection, string-based imports, and plugin entrypoints. Mark unresolved cases `VERIFY` rather than guessing.
7. Reconcile the statistical inventory with the chart registry, payload assembler, UI/report consumers, and focused tests. Check formula/spec authority, sample and denominator semantics, `ddof`, degenerate inputs, time ordering for trend charts, finite-value sanitation immediately before aggregation, and visible fallback metadata. Use an independent DB/session recomputation gate when the repository provides one; contract/renderability alone is not proof of numeric correctness.
8. Produce an evidence-backed report. Use the A-E structure and finding IDs from `references/structured-health-audit.md` when that report shape was requested.
9. In a confirmed fix phase, patch the smallest safe scope. Preserve SPC, Cp, Cpk, yield, spec-limit, and pass/fail behavior unless a reproduced bug proves the current logic is wrong.
10. Re-run only gates invalidated by the patch. Escalate to full pytest and UI validation only under V3 conditions. Document findings, applied patches, and verification using the repo's convention when a persistent report is requested.

## Audit Rules

- If the repo has `AGENTS.md` or `SPC_RULES.md`, treat them as mandatory; do not change SPC/Cp/Cpk formulas or break its Safe Change Rules.
- Prefer source-owned desktop code over checked-in bytecode.
- Treat `except Exception` as a bug unless it is clearly infrastructure-level cleanup or transaction rollback.
- For charts, keep expected "insufficient data, skip chart" behavior as explicit preconditions. Do not swallow unexpected renderer failures.
- For import/preview flows, surface deterministic file or parse errors instead of silently falling back.
- Quarantine temp artifacts under a single ignored root such as `tmp/`; move them instead of deleting them unless the user explicitly asks.
- Treat optimization findings as evidence-backed only when a hot path, complexity issue, repeated allocation, or measurement supports the claim.
- Treat `NaN`/`+inf`/`-inf` rows as invalid observations, not failures, OOS points, or denominator members, unless the repository contract explicitly defines another visible data-quality category.
- Compare trend-engine input ordering with the repository's time-like ordering policy; row order is not automatically process order.
- Inventory output is a candidate map, not completeness proof. Reconcile it with registries, reflection, aliases, report expansion, and real-data validation before claiming full coverage.

## Out of scope

- Do not change SPC/Cp/Cpk/Pp/Ppk formulas or interpretation constants (use `SPC_RULES.md` or existing spec as source of truth).
- Do not do style-only or layout-only refactors in the same phase as correctness fixes.
- Do not mix problem types in one patch (e.g. error handling and UI layout in the same change set).

## Bundled Resources

- `scripts/scan_repo_quality.py`
  Run from the skill directory against the target repo root for a deterministic scan. It auto-detects `src/` and `app/`; add `--inventory-spc` to print candidate statistical entrypoints. The script may include repo-specific allowlists; triage findings manually rather than treating inventory as proof of semantic correctness.
- `references/checklist.md`
  Use when you need a terse execution checklist while applying fixes.
- `references/structured-health-audit.md`
  Use for audit-only A-E categorization, severity, finding IDs, and report structure.
- `references/spcspi-platform-v2-profile.md`
  Use only for the matching repository to apply its PySide6, analytics, chart, payload, and QSS checks.
