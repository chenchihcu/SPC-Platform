# Temporary Artifact Quarantine

This directory is the repository-local quarantine area for temporary runtime artifacts.

Rules:
- Put transient logs, one-off debug dumps, and local experiment outputs under `tmp/`.
- Do not place production datasets or release evidence that must be versioned in `tmp/`.
- Historical root artifacts are preserved for traceability unless explicitly removed by owner request.

Examples:
- `tmp/logs/*.log`
- `tmp/debug/*.txt`
- `tmp/snapshots/*`
