# Global Plan Framework v2.2 (Permanent Self-Only)

> **Supersedes**: `GLOBAL_PLAN_FRAMEWORK_V2_1.md`  
> **Effective**: 2026-04-22  
> **Change summary**: Added KI-First principle, Gate A~F pass/fail criteria, user approval STOP node,
> Antigravity Artifacts alignment, Confidence auto-downgrade rules, Side-effect boundary requirement,
> L1 formal definition, and AI-agent failure mode validation scenarios.

This document defines a cross-project, implementation-ready planning framework for a permanent
single-developer model.

- Scope: global planning contract (not domain-specific implementation logic).
- Execution model: `executor=self` only.
- Compatibility rule: repository-level AGENTS or domain governance can be stricter, never weaker.

---

## 1) Core Objectives

Every plan must satisfy, in **priority order**:

1. **Contract-aware** [最優先]: Before any design work, check all applicable AGENTS/governance rules.
   Confirm no architectural violations exist.
2. **KI-First** [前置必要]: Before any research, check Knowledge Items (KI) summaries.
   Read all relevant KI artifacts before beginning independent research.
   Rationale: prevents redundant work and ensures established patterns are followed.
3. **Replayable**: Every plan step must be reproducible by the same tool set.
   For AI-agent execution, this means all tool calls have traceable inputs and outputs.
4. **Verifiable**: Every key claim has an evidence path — an executable command or a
   recorded tool call output. A `Pass` without evidence is invalid.
5. **Reversible**: Any step involving destructive operations (overwrite, delete, migration,
   schema change) must include an explicit rollback path.

---

## 2) Mandatory Capability Coverage

### 2a. Required for ALL tasks (no exceptions)

1. **Code-level precision**:
   - Explicit file paths
   - Class/module names
   - Key function signatures before/after changes

2. **Side-effect boundary**:
   - Explicit list of resources that WILL be modified
   - Explicit list of resources guaranteed NOT to be modified
   - Rationale: prevents AI agents from making unintended collateral changes

3. **Tool call evidence**:
   - Every key factual claim must correspond to at least one traceable tool call or
     command output captured in the current session
   - Inference or assumption is not valid evidence

### 2b. Conditionally required (enable only for matching task types)

- **[UI changes]** UX/premium preview:
  - Concrete layout description
  - Design standard/token constraints
  - Explicit premium acceptance criteria with visual evidence (screenshot)

- **[DB/data changes]** Migration risk and rollback:
  - Pre-check/forward/validation SQL
  - Failure criteria
  - Rollback SQL and recovery steps

- **[Cross-subsystem changes]** AGENTS deep-link compliance:
  - Proactive checks for architecture constraints
  - Naming/numbering rules
  - Contract compatibility rules

---

## 3) Mandatory Gates (A~F)

Gates must be executed in order: **A → B → C → D → E → F**. No gate may be skipped or
executed out of sequence.

Decision rule: any gate `Fail` => task status must be `blocked`.

| Gate | Name | Pass Condition | On Fail |
|------|------|----------------|---------|
| A | Scope | Task scope compared against AGENTS/governance rules; no violations found | Immediately `blocked`; no further steps permitted |
| B | Evidence | All current-state claims backed by tool call or command output; no assumption-only statements | Must supplement evidence before continuing |
| C | RCA | Root cause has a clear evidence chain (not speculation); cross-subsystem impact identified | Supplement RCA, then re-enter Gate B |
| D | Blast Radius | All affected files, functions, and resources explicitly listed; side-effect boundary declared | Must re-scope before continuing |
| E | Verify | Verification commands executed and output captured; OR explicitly marked `not verified` | Output `not verified`; plan cannot be marked `done` |
| F | Report | Delivery summary includes: root cause / fixes applied / residual risks / risk ledger update | Plan cannot be marked `done` |

---

## 4) AI Triage Policy (Fail-Safe, Mandatory)

Every new task plan must include an AI triage result before selecting plan depth.

### Decision algorithm (fixed, non-optional)

1. Evaluate hard triggers first.
2. Then evaluate confidence.
3. Route decision:
   - If any hard trigger = `true`, route = `Full`.
   - Else if `triage_confidence < 0.85`, route = `Full`.
   - Else route = `L1`.

### Hard triggers (fixed list)

- `impact_type` includes `ui`, `data`, or `contract`
- Function signature / public API / payload shape change
- Any migration SQL is involved
- Impact spans 2 or more subsystems
- RCA is unclear or not evidence-backed
- Task requires `Overwrite=true` on any existing file
- KI exists for the topic but shows signs of inconsistency with current code
- Task spans 3 or more architectural layers

### L1 (Lightweight) Task Definition

A task qualifies as L1 **only** when ALL of the following are true:

- No hard triggers apply
- `triage_confidence >= 0.85`
- Impact is confined to a single file or a single logical unit
- No destructive operations (no overwrite, delete, or migration)
- The change can be fully described in 3 lines or fewer

L1 execution: proceed directly without a full plan; update `walkthrough.md` after completion.

### Confidence auto-downgrade rules

The following conditions automatically set `triage_confidence < 0.85` (forcing `Full` route):

- A relevant KI exists but has not been read in the current session
- The task involves files not yet read in the current session
- The task description contains vague language: "minor tweak", "small change",
  "simple fix", "shouldn't be a problem"
- The most recent relevant KI was last updated more than **30 days** ago (treat as unverified)

### Override policy

- Manual override is one-way only: `L1 -> Full` is allowed.
- `Full -> L1` downgrade is prohibited.

### Evidence policy

- Any triage claim must include evidence paths or commands.
- Any `Pass` without evidence is invalid.

---

## 5) Required Deliverables

All deliverables map to the Antigravity Artifacts system. Use the paths below — do not use
external templates.

| Deliverable | Antigravity Artifact Path | Required Fields |
|-------------|--------------------------|-----------------|
| Plan | `brain/<conv-id>/implementation_plan.md` | Scope / Triage result / Gate A~F review / Proposed Changes / Verification Plan / Open Questions |
| Task tracker | `brain/<conv-id>/task.md` | `[ ]` uncompleted / `[/]` in-progress / `[x]` completed |
| Walkthrough | `brain/<conv-id>/walkthrough.md` | Root cause / Fixes applied / Verification results / Residual risks |
| Risk ledger | `brain/<conv-id>/risk_ledger.md` | Owner=self / Risk description / Mitigation / Status |
| Evidence | Embedded in walkthrough | Screenshot or command output; never inline assertion only |

---

## 6) Default Enforcement Rules

### Inherited rules (unchanged from v2.1)

- Multi-role approval flow is out of scope.
- `Owner` in risk ledger is always `self`.
- Any `Pass` without evidence is invalid.
- If verification is skipped, output exactly `not verified`.

### New mandatory positive-behavior rules (added in v2.2)

| Rule | Behavior Required |
|------|-------------------|
| **KI-First Rule** | At the start of every new task, check KI summaries. Read all relevant KI artifacts before beginning independent research. |
| **Clarify-Before-Execute Rule** | When task description contains ambiguous requirements, list them as Open Questions in the plan. Do not execute destructive operations until the user has confirmed. |
| **Minimal Blast Radius Rule** | Modifications must be the minimum set required to complete the task. Do not "while we're at it" modify unrelated files, styles, or schemas. |
| **Evidence-Before-Pass Rule** | In Gate review, every `Pass` must be accompanied by a tool call ID or command output. |
| **Stop-on-Discovery Rule** | If blast radius expands beyond the original plan during execution, immediately pause, update `implementation_plan.md`, re-set `RequestFeedback=true`, and wait for user approval before continuing. |

---

## 7) Adoption Workflow

```
0. [PRE]     KI Check
             → Review KI summaries. Read all relevant KI artifacts.

1. [TRIAGE]  Assess task using §4 decision algorithm.
             → L1: proceed directly to execution, update walkthrough afterward.
             → Full: continue to step 2.

2. [PLAN]    Create implementation_plan.md.
             → Fill in order: Triage → Open Questions → Gate A~F pre-check
               → Proposed Changes → Side-effect boundary → Verification Plan.

3. [REVIEW]  Set RequestFeedback=true. ⛔ STOP AND WAIT for explicit user approval.
             → Do NOT execute any destructive operation before approval is received.

4. [EXECUTE] Create task.md. Execute steps in order.
             → Update [ ] → [/] → [x] as work progresses.
             → If blast radius expands: invoke Stop-on-Discovery Rule immediately.

5. [VERIFY]  Run all verification commands and capture outputs.
             → If any step is skipped: output exactly `not verified`.

6. [CLOSE]   Run Gate A~F review in order.
             → All gates Pass: mark task `done`, update walkthrough.md and risk_ledger.md.
             → Any gate Fail: status = `blocked` until resolved.
```

---

## 8) Framework Validation Scenarios

### Original scenarios (from v2.1, unchanged)

1. Logic-only task: Code Change Matrix is complete.
2. UI task: UX Acceptance Pack is complete with visual evidence.
3. Migration task: SQL chain includes rollback and recovery.
4. Compliance conflict task: plan is blocked by AGENTS gate.
5. Verification missing task: output is explicitly `not verified`.
6. No hard trigger + confidence 0.91: route can be `L1`.
7. UI hard trigger + confidence 0.95: route must be `Full`.
8. No hard trigger + confidence 0.72: route must be `Full`.

### New scenarios (added in v2.2 — AI-agent failure modes)

9. **KI exists but last updated > 30 days**:
   Confidence auto-set to < 0.85 → route = `Full`.
   Plan must include note: "KI requires re-verification before use."

10. **User gives vague requirement** (e.g., "just tweak it a bit"):
    AI must list ambiguities as Open Questions.
    Direct execution without clarification = Gate A `Fail`.

11. **AI tool call fails** (e.g., file read error, command timeout):
    Failure must be recorded in the plan.
    The failed claim cannot be replaced with inference.
    Gate B auto-`Fail` until valid evidence is re-acquired.

12. **Blast radius exceeds plan during execution**:
    AI must pause immediately.
    Update `implementation_plan.md` with revised scope.
    Re-set `RequestFeedback=true` and await user approval before continuing.

13. **User inserts a new requirement mid-execution**:
    Treat as a new task; open a new plan flow.
    Do not append to the in-progress plan, unless the addition is assessed as L1
    and does not affect the current plan's blast radius.
