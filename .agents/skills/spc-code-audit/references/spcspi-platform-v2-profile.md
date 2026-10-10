# spcspi platform v2 Audit Profile

Read this profile only when repository identity, repository rules, or matching symbols establish that the target is `spcspi platform v2`. Prefer equivalent rules from that repository's own `AGENTS.md` or `SPC_RULES.md` when present.

## P1. Qt Signal Blocking

- Every `blockSignals(True)` path must restore the previous signal-blocked state in `finally`.
- Early return or exception must not leave signals blocked.

## P2. Worker Lifecycle

- Verify each `QThread` or worker has a safe ownership and cleanup path.
- `finished.connect(...deleteLater)` is one valid pattern; parent ownership or another documented lifecycle can also be valid.

## P3. Analytics Guards

For `compute_*` analysis entrypoints, verify in order:

1. statistical/SPC input validity
2. required parameters such as USL/LSL
3. degenerate inputs such as equal limits

Invalid results must use the repository's canonical invalid-result shape; do not return partially valid data as success.

## P4. Matplotlib Axis Lifecycle

After `figure.clear()`, recreate and reassign every axis before use. Multi-chart paths must create the correct subplot set and reapply the centralized style.

## P5. Payload Resolution

Use single-feature payload helpers only on single-feature data. Multi-feature paths must use their dedicated resolver and preserve the expected payload schema.

## P6. Chart-to-Parameter Mapping

Compare every chart ID in the canonical chart registry/order with its parameter-key mapping or documented fallback. Report missing or stale mappings.

## P7. QSS Object Names

Verify semantic frames used by object-name selectors actually set the expected `objectName`. Missing names can silently disable QSS rules.

## P8. Canvas Refresh

Every user-visible chart update path, including empty/error states, must reach a valid refresh mechanism such as `draw()`, `draw_idle()`, or the repository's centralized redraw scheduler. Do not require duplicate redraws when a valid central scheduler already owns refresh.

For each profile finding, cite the matching symbol and execution path. If project identity or the required contract cannot be proven, mark the check `VERIFY` instead of treating this profile as universal.
