# Structured A-E Health Audit

Use this reference only for a systematic, report-first code-health audit in an SPC/SPI repository.

## Coverage Contract

- Enumerate every in-scope Python file with `rg --files` before reviewing.
- Read all target files before claiming complete coverage.
- Search the full repository before calling a function, class, import, or branch unused.
- Account for Qt signals/slots, decorators, registries, reflection, string-based imports, plugin entrypoints, and test-only use.
- Mark evidence that remains ambiguous as `VERIFY`; do not convert absence of a simple text match into certainty.

## Categories

### A. Bug or Logic Error

Use for behavior that can crash, corrupt results, or violate the documented contract, including:

- missing `None`, empty-input, bounds, or zero-denominator guards
- reads before assignment or impossible/always-true branches
- swallowed errors that hide incorrect output
- off-by-one indexing or inconsistent state transitions

### B. Dead or Unused Code

Require full-repository reference evidence. Include the definition location, search pattern, matches, and eliminated dynamic-use mechanisms. Use `VERIFY` when dynamic use cannot be ruled out.

### C. Stale or Obsolete Code

Use for proven legacy shims, abandoned commented-out implementations, obsolete mappings, or TODO/FIXME items whose surrounding contract shows they are no longer valid. A marker alone is not a finding.

### D. Duplicate Logic

Use when two or more blocks implement the same semantic responsibility and consolidation would reduce drift without hiding meaningful differences. Do not report tiny or intentionally separate domain logic merely because text is similar.

### E. Optimization Target

Use only for performance or memory improvements supported by a hot path, complexity analysis, repeated expensive allocation, profiling, or a measurable benchmark. Correctness problems belong in A, not E.

## Severity

- `High`: incorrect results, crash, data loss, or broken critical workflow.
- `Medium`: credible failure in a bounded scenario or substantial maintainability/operability harm.
- `Low`: localized clarity, hygiene, or measured efficiency issue without behavior impact.

## Report Contract

Start with a category-by-severity summary table for A-E. For every finding include:

```text
[A1] High - path/to/file.py:123
Issue: concise statement of the observed defect
Evidence: execution, reference search, trace, test, or contract evidence
Impact: affected behavior and blast radius
Recommendation: smallest safe correction or VERIFY next check
```

State explicitly when a category has no supported findings and list residual coverage gaps. The audit is read-only by default. Enter a fix phase only after the user requests it; confirm the exact finding IDs and verify targeted behavior plus the repository gate.
