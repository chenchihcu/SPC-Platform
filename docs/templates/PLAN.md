# PLAN Template v2.2 (Global, Self-Only)

> Purpose: A cross-project implementation plan template for a permanent single-developer workflow (`executor=self`).

## 0) Metadata

- `plan_id`: `YYYYMMDD-<topic>-vN`
- `change_mode`: `fix` | `optimize` | `refactor` | `migration`
- `impact_type`: one or more of `logic`, `ui`, `data`, `contract`, `infra`
- `risk_level`: `L1` | `L2` | `L3`
- `status`: `draft` | `approved` | `blocked` | `done`
- `executor`: `self`
- `done_definition`: one-sentence completion target
- `output_contract`: expected behavior/payload/report/file format
- `non_goals`: explicit out-of-scope list
- `triage_route`: `L1` | `Full`
- `triage_confidence`: float in `[0, 1]`
- `triage_triggers`: string array
- `triage_evidence`: evidence path/command array
- `triage_decision_note`: brief decision reason

## 0.1) AI Triage Decision (Mandatory Before Planning)

Decision algorithm (fixed):

1. Evaluate hard triggers:
   - `impact_type` includes `ui`, `data`, or `contract`
   - function signature / public API / payload shape changes
   - any migration SQL is involved
   - impact spans 2 or more subsystems
   - RCA is unclear
2. Route:
   - any hard trigger = `true` -> `triage_route=Full`
   - else if `triage_confidence < 0.85` -> `triage_route=Full`
   - else -> `triage_route=L1`
3. Override rule:
   - `L1 -> Full` is allowed
   - `Full -> L1` is prohibited

Hard rules:

- Missing `triage_evidence` => triage result is invalid
- Invalid triage result => `status=blocked`

## 1) Task Contract (Before Edits)

- `Priority`: `P0` | `P1` | `P2`
- `In Scope`:
- `Out of Scope`:
- `Stop Rule`: if scope is ambiguous, output `BLOCKER + required verification path`

## 2) Evidence Baseline (Before Decision)

- Runtime/Entrypoint evidence:
- Contract/spec source of truth:
- Latest decision/changelog evidence:
- Environment (OS/runtime/toolchain):
- Version set:
- Data/sample/seed:
- Reproduction preconditions:

## 3) Reproduce & RCA

- Reproduction steps:
- Expected behavior:
- Observed behavior:
- Evidence locations (logs/metrics/errors/check paths):
- Root cause (single primary cause, evidence-backed):
- Eliminated hypotheses:

## 4) Minimal Patch Plan

- Minimal patch boundary:
- Change units (files/modules/interfaces):
- Compatibility statement:
- Will not change:

## 5) Code Change Matrix (Mandatory)

| File Path | Class/Module | Function/Method | Signature Before | Signature After | Compatibility Impact | Related Tests |
|---|---|---|---|---|---|---|
| `<path>` | `<name>` | `<name>` | `<before>` | `<after>` | `<none/minor/breaking>` | `<test path/id>` |

## 6) UX Acceptance Pack (Required when `impact_type` includes `ui`)

- Layout spec (explicit region/component structure):
- Design standard (token-driven typography/spacing/color):
- Responsive breakpoints (or fixed viewport contract):
- Accessibility acceptance:
- Premium design acceptance criteria:
- Visual evidence plan (screenshots or equivalent artifacts):

## 7) Data Migration Runbook (Required when `impact_type` includes `data` or `contract`)

- Preconditions (backup/lock/time window):
- Pre-check SQL:

```sql
-- pre-check SQL
```

- Forward SQL:

```sql
-- migration SQL
```

- Validation SQL:

```sql
-- post-check SQL
```

- Failure criteria:
- Rollback SQL:

```sql
-- rollback SQL
```

- Recovery steps:

## 8) AGENTS Compliance Gate (Mandatory Every Time)

| Rule ID | Rule Statement | Triggered (Y/N) | Evidence (file/command/check path) | Result (Pass/Fail) | Blocker/Action |
|---|---|---|---|---|---|
| `ARCH-*` | Architecture boundaries and layering rules | `Y/N` | `<evidence>` | `Pass/Fail` | `<action>` |
| `DB-*` | Data store rules (for example, single-machine SQLite) | `Y/N` | `<evidence>` | `Pass/Fail` | `<action>` |
| `ID-*` | Identifier/numbering rules | `Y/N` | `<evidence>` | `Pass/Fail` | `<action>` |
| `CONTRACT-*` | External payload/UI/report compatibility rules | `Y/N` | `<evidence>` | `Pass/Fail` | `<action>` |

Hard rules:

- Any key rule `Fail` => `status=blocked`
- Any `Pass` without evidence => treated as `Fail`

## 9) Verification Matrix

| Level | Command/Check Path | Target | Result (Pass/Fail) | Evidence Path |
|---|---|---|---|---|
| Unit | `<command>` | `<intent>` | `<Pass/Fail>` | `<path>` |
| Integration | `<command>` | `<intent>` | `<Pass/Fail>` | `<path>` |
| Regression | `<command>` | `<intent>` | `<Pass/Fail>` | `<path>` |
| Launch/Smoke | `<command>` | `<intent>` | `<Pass/Fail>` | `<path>` |

- Edge cases:
- Performance trigger and threshold (`or not triggered`):
- If verification is not executed, write exactly: `not verified`

## 10) Release & Rollback

- Pre-release checks:
- Go/No-Go decision:
- Rollback steps (exact modules/files):
- Post-release observation window and monitor points:

## 11) Delivery Output

- Changed files:
- Root cause:
- What was attempted:
- Verification result:
- Self-review conclusion:

### Gate A~F Enforcement Table

| Gate | Name | Pass Condition | Required Evidence | On Fail | Result | Evidence | On Fail Action |
|---|---|---|---|---|---|---|---|
| Gate A | Scope | Task scope is compared against AGENTS/governance rules and no violations are found | In-scope/non-goals list plus affected files/modules | Immediately `blocked`; no further steps permitted | `Pass/Fail` | `<path/command/output>` | `<action>` |
| Gate B | Evidence | All current-state claims are backed by tool call or command output; no assumption-only statements | File paths, command outputs, logs, or rendered evidence | Supplement evidence before continuing | `Pass/Fail` | `<path/command/output>` | `<action>` |
| Gate C | RCA | Root cause has a clear evidence chain and is not speculation; cross-subsystem impact is identified | Reproduction, expected vs observed, eliminated hypotheses | Supplement RCA, then re-enter Gate B | `Pass/Fail` | `<path/command/output>` | `<action>` |
| Gate D | Blast Radius | Affected files, functions, resources, and side-effect boundary are explicitly listed | Same-pattern search and not-change list | Re-scope before continuing | `Pass/Fail` | `<path/command/output>` | `<action>` |
| Gate E | Verify | Verification commands executed and output captured, or explicitly marked `not verified` | Exact commands/check paths with pass/fail status | Output `not verified`; plan cannot be marked `done` | `Pass/Fail` | `<path/command/output>` | `<action>` |
| Gate F | Report | Delivery summary includes root cause, fixes applied, residual risks, and risk ledger status | Final response sections and risk ledger decision | Plan cannot be marked `done` | `Pass/Fail` | `<path/command/output>` | `<action>` |

Hard rules:

- Any Gate A~F `Fail` => `status=blocked`
- Any Gate A~F `Pass` without evidence => treated as `Fail`
- Remaining risks:

## 12) Active Risk Ledger (Single Ledger Only)

| Scope | Risk | Current Guardrail | Next Action (`Owner: self`) | Revalidation Gate (exact command/check path) | Rollback | Status |
|---|---|---|---|---|---|---|
| `<scope>` | `<risk>` | `<guardrail>` | `<next action>` | `<command/path>` | `<rollback>` | `<open/monitoring/closed>` |

## 13) Exit Criteria

- Done state met
- Output contract preserved or explicitly approved as changed
- Required verifications executed and reported
- No obvious regressions
- Gate A~F all `Pass`

If any unmet:

- Output exactly: `BLOCKER + required input`

## 14) Framework Self-Test Scenarios

1. Logic-only task: `Code Change Matrix` is complete; UI/Migration sections can be marked not applicable.
2. UI task: `UX Acceptance Pack` is complete and includes premium acceptance plus visual evidence.
3. Migration task: pre-check/forward/validation/rollback SQL chain is executable.
4. Rule conflict task: `AGENTS Compliance Gate` blocks closure when any key rule fails.
5. Unverified task: output must be `not verified`; task cannot be marked done.

## 15) Path Rules (`L1 Quick Path` vs `Full Path`)

### L1 Quick Path (allowed only when `triage_route=L1`)

Required sections:

- `0) Metadata` + `0.1) AI Triage Decision`
- `1) Task Contract`
- `2) Evidence Baseline`
- `5) Code Change Matrix` (minimal but explicit)
- `8) AGENTS Compliance Gate`
- `9) Verification Matrix`
- `11) Delivery Output`

All other sections must be marked as `N/A (L1 Quick Path)` with reason.

### Full Path (mandatory when `triage_route=Full`)

All sections are required, especially:

- `6) UX Acceptance Pack` (when UI is involved)
- `7) Data Migration Runbook` (when data/contract is involved)
- Gate A~F completion in `11) Delivery Output`
