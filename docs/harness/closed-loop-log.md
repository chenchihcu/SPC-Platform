# Closed-loop Log

Use this file for reusable lessons from debugging, regressions, repeated failures, or Investigation Path work.

## Entry Template

```text
Date:
Task:
Changes:
Impact:
Verification:
Residual risk:
Next action:
Debug/RCA (when applicable):
Observed:
Root cause:
Fix:
Harness update needed:
Destination:
```

## Initial Entry

Date: 2026-05-16
Task: Install closed-loop harness.
Changes: Added harness docs, exec-plan directories, a harness structure check, a full PowerShell verification entrypoint, and project command rules.
Impact: The repo now exposes a common harness layer while preserving strict SPC/SPI governance and release-focused validation boundaries.
Verification: Run `scripts\harness_check.ps1` and `scripts\verify.ps1`.
Residual risk: active residual risks remain only in `docs/open-questions.md`; this log is not a parallel ledger.
Next action: Use weekly harness gardening to report drift and keep remediation explicitly requested.
Debug/RCA (when applicable):
Observed: The repo already had strict AGENTS governance, AI_RULES, SPC rules, active risk ledger, release gates, and verification scripts, but no shared `docs/harness` structure or single PowerShell verification entrypoint.
Root cause: Harness behavior was strong but distributed across several governance and script files.
Fix: Add harness docs, exec-plan directories, a harness structure check, a full verification script, and project command rules.
Harness update needed: yes
Destination: `AGENTS.md`, `docs/harness/`, `docs/exec-plans/`, `scripts/harness_check.ps1`, `scripts/verify.ps1`, `.codex/rules/project.rules`
