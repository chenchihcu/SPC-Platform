# GLOBAL_AGENTS.md (8-Class Integrated Template, Cross-Project)

This template is a global baseline for agent execution governance.

- Scope: cross-project generic rules only.
- Policy: repository rules may be stricter, never weaker.
- Non-goal: do not add project-specific paths, module names, or stack-bound instructions here.
- Companion implementation framework: `docs/governance/GLOBAL_PLAN_FRAMEWORK_V2_2.md`
- Ready-to-copy task template: `docs/templates/PLAN.md`

---

## 1) Task Contract (Before Edits)

Required fields:

- `Done`: one sentence completion target.
- `Output Contract`: expected behavior/payload/report/file format.
- `Non-goals`: what this task will not change.
- `Priority & Scope`: priority level, in-scope boundary, explicit out-of-scope list.

Rules:

- No edits before all required fields are declared.
- If scope is ambiguous and cannot be derived from evidence, stop with:
  - `BLOCKER + required verification path`

---

## 2) Preflight (Before Decision)

Required evidence sources:

- Runtime/program entrypoint evidence.
- Contract/spec source-of-truth evidence.
- Latest decision/change-log evidence.

Required reproducibility fields:

- Environment (OS/runtime/toolchain).
- Version set (runtime/application/dependency if relevant).
- Data/sample/seed inputs (or `not applicable`).
- Reproduction preconditions.

Rules:

- Verify at least the three evidence sources before deciding the fix direction.
- If source statements conflict and code/runtime evidence is insufficient, stop with:
  - `BLOCKER + required verification path`

---

## 3) Reproduce & RCA

Required fields:

- Reproduction steps.
- Expected vs observed behavior.
- Evidence locations (logs/metrics/errors/check outputs).
- Root cause statement (single primary cause, evidence-backed).
- Eliminated hypotheses (what was checked and ruled out).

Rules:

- No blind fix.
- No symptom-only patch without upstream/root verification.
- If RCA is unclear, stop and request diagnostics instead of guessing.

---

## 4) Patch Plan (Minimal Change)

Required fields:

- Minimal patch boundary (smallest reversible scope).
- Change units (files/modules/interfaces touched).
- Compatibility statement (what remains backward compatible).
- Explicit "will not change" list.

Rules:

- Prefer minimal and reusable changes.
- Do not cross subsystem boundaries unless correctness/stability requires it.
- Do not mix unrelated changes in one patch.

---

## 5) Blast Radius Guard (Contract + Security/Privacy)

Trigger words (contract-impact check):

- `gate`, `payload`, `template`, `navigation/workflow`, `data path/schema`

Required when triggered:

- Sync `code + tests + core docs + decision/change log` in the same task.

Required security/privacy checks:

- Input validation boundary.
- Permission/access boundary.
- Sensitive data handling and exposure risk.

Rules:

- Any contract-impact change without synchronization is `not pass`.

---

## 6) Verification Gates (Execution Evidence)

Required Test Strategy fields:

- Test levels used (unit/integration/regression or equivalent).
- Minimum coverage intent for this change.
- Required boundary/edge cases.

Required observability/performance fields:

- Verification evidence paths for logs/metrics/errors.
- Performance budget trigger condition and threshold (or `not triggered`).
- Measurement method/command/check path.

Rules:

- Never claim success without execution evidence.
- If verification is not executed, state exactly: `not verified`.
- Report exact commands/check paths and pass/fail status.

---

## 7) Self-Review & Regression (Gate Checklist + Release/Rollback)

Use mandatory Gate checklist:

| Gate | Pass Condition | On Fail |
|------|----------------|---------|
| Gate A `Scope` | In-scope/non-goals are compared against AGENTS/governance rules with no unrelated change | `blocked`; no further steps permitted |
| Gate B `Evidence` | Current-state claims are supported by verified tool calls or command output | Supplement evidence before continuing |
| Gate C `RCA` | Root cause is evidence-backed, not hypothesis, and lateral impact is identified | Supplement RCA, then re-enter Gate B |
| Gate D `Blast Radius` | Same-pattern/lateral checks and side-effect boundaries are complete | Re-scope before continuing |
| Gate E `Verify` | Required gates executed with captured results, or explicitly marked `not verified` | Output `not verified`; cannot mark done |
| Gate F `Report` | Required completion sections and risk ledger status are present | Cannot mark done |

Any `Pass` without evidence is treated as `Fail`.

Release/Rollback required fields:

- Pre-release checks and go/no-go condition.
- Rollback approach (exact files/modules/steps).
- Post-release observation window and monitor points.

Decision rule:

- Any gate = `Fail` -> whole task = `not pass` (cannot close).

---

## 8) Delivery & Risk Ledger

Every completion output must include:

- `Changed files`
- `Root cause`
- `What was attempted`
- `Verification result`
- `Self-review conclusion`
- `Remaining risks`

Active risk ledger policy:

- Maintain exactly one active risk ledger per repository.
- Each active risk item must include:
  - `Scope`
  - `Risk`
  - `Current guardrail`
  - `Next action` (owner-explicit)
  - `Revalidation gate` (exact command/check path)
  - `Rollback`
  - `Status`

Stop conditions:

- Missing data.
- Unclear root cause.
- Cannot verify.

Stop output format:

- `BLOCKER + required input`

Completion condition:

- Issue resolved.
- Verification passed.
- No obvious regressions.
- Gate A~F all `Pass`.
