# Global Plan Framework v2.1 (Permanent Self-Only)

> **Superseded**: This historical framework has been superseded by
> `docs/governance/GLOBAL_PLAN_FRAMEWORK_V2_2.md` as of 2026-04-22.
> Keep this file only for rollback/history; current entrypoints must use v2.2.

This document defines a cross-project, implementation-ready planning framework for a permanent single-developer model.

- Scope: global planning contract (not domain-specific implementation logic).
- Execution model: `executor=self` only.
- Compatibility rule: repository-level AGENTS or domain governance can be stricter, never weaker.

## 1) Core Objectives

Every plan must be:

1. Replayable: another person/tool can re-run the same checks and reach the same conclusion.
2. Verifiable: each key claim has an evidence path or executable command.
3. Reversible: risky changes include explicit rollback steps.
4. Contract-aware: plan is checked against existing AGENTS/governance rules before closure.

## 2) Mandatory Capability Coverage

The plan must include all of the following:

1. Code-level precision:
   - explicit file paths
   - class/module names
   - key function signature before/after changes
2. UX/premium preview for UI changes:
   - concrete layout description
   - design standard/token constraints
   - explicit premium acceptance criteria
3. Data migration risk and rollback:
   - pre-check/forward/validation SQL
   - failure criteria
   - rollback SQL and recovery steps
4. AGENTS deep-link compliance:
   - proactive checks for architecture constraints (for example, single-machine SQLite)
   - naming/numbering rules
   - contract compatibility rules

## 3) Mandatory Gates (A~F)

- Gate A `Scope`
- Gate B `Evidence`
- Gate C `RCA`
- Gate D `Blast Radius`
- Gate E `Verify`
- Gate F `Report`

Decision rule:

- Any gate `Fail` => task status must be `blocked`.

## 4) AI Triage Policy (Fail-Safe, Mandatory)

Every new task plan must include an AI triage result before selecting plan depth.

Decision algorithm (fixed, non-optional):

1. Evaluate hard triggers first.
2. Then evaluate confidence.
3. Route decision:
   - If any hard trigger = `true`, route = `Full`.
   - Else if `triage_confidence < 0.85`, route = `Full`.
   - Else route = `L1`.

Hard triggers (fixed list):

- `impact_type` includes `ui`, `data`, or `contract`
- function signature / public API / payload shape change
- any migration SQL is involved
- impact spans 2 or more subsystems
- RCA is unclear or not evidence-backed

Override policy:

- Manual override is one-way only: `L1 -> Full` is allowed.
- `Full -> L1` downgrade is prohibited.

Evidence policy:

- Any triage claim must include evidence paths/commands.
- Any `Pass` without evidence is invalid.

## 5) Required Deliverables

- Plan template instance using `docs/templates/PLAN.md`.
- Verification outputs (commands + result + evidence paths).
- Delivery summary with root cause, attempted fixes, and residual risks.
- Active risk ledger entry updates (single ledger policy).

## 6) Default Enforcement Rules

- Multi-role approval flow is out of scope.
- `Owner` in risk ledger is always `self`.
- Any `Pass` without evidence is invalid.
- If verification is skipped, output exactly `not verified`.

## 7) Adoption Workflow

1. Create a task-specific plan from `docs/templates/PLAN.md`.
2. Fill triage fields and resolve `triage_route` first.
3. Fill sections in order (Task Contract -> Evidence -> RCA -> Patch plan -> Compliance -> Verification).
4. Execute validation and capture evidence.
5. Run A~F gate review.
6. Mark `done` only when all gates pass.

## 8) Framework Validation Scenarios

1. Logic-only task: Code Change Matrix is complete.
2. UI task: UX Acceptance Pack is complete with visual evidence.
3. Migration task: SQL chain includes rollback and recovery.
4. Compliance conflict task: plan is blocked by AGENTS gate.
5. Verification missing task: output is explicitly `not verified`.
6. No hard trigger + confidence 0.91: route can be `L1`.
7. UI hard trigger + confidence 0.95: route must be `Full`.
8. No hard trigger + confidence 0.72: route must be `Full`.
