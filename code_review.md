# Code Review Rubric

This repository uses a findings-first review style.

## Review Priorities

1. Logical correctness.
2. Behavioral regression risk.
3. Data/contract compatibility.
4. Performance and memory impact.
5. Readability and maintainability.

## Required Review Output

1. Findings first, ordered by severity (`P0`/`P1`/`P2`/`P3`).
2. For each finding, include:
   - file and line reference,
   - concrete impact,
   - minimal fix direction.
3. Explicitly list:
   - missing tests,
   - residual risks,
   - assumptions.
4. If no findings:
   - state "No functional findings",
   - still list residual risks/testing gaps.

## Severity Guidance

- `P0`: crash, data corruption, incorrect statistical conclusion affecting engineering decisions.
- `P1`: high-likelihood incorrect behavior or contract break.
- `P2`: edge-case bug, degraded reliability, or significant maintainability debt with near-term risk.
- `P3`: minor defect, clarity issue, or low-risk cleanup.

## Validation Baseline

- Python lint: `python -m ruff check .`
- Python type check: `python -m mypy app`
- Tests: `python -m pytest -q`

If any baseline item is unavailable, report as:
- `not configured`, or
- `not available`

Never report a check as passed unless it was actually executed.
