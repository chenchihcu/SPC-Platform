# Workflow Governance Monthly Checklist

Use this checklist to ensure the integrated issue-resolution workflow stays effective and aligned.

## A. Rules and Policy Alignment
- [ ] Re-check Cursor Rules semantics against https://cursor.com/docs/context/rules
- [ ] Confirm `.cursor/rules/README.md` still matches official terms and precedence
- [ ] Confirm `agent-residence-minimal.mdc` mode choice is intentional (Intelligent vs Always Apply)
- [ ] Confirm no legacy `.cursorrules` file was introduced

## B. L2 Execution Quality
- [ ] Sample at least 5 recent L2 changes and verify they include `Scope/Evidence/RCA/Blast/Verify`
- [ ] Verify PRs used `.github/pull_request_template.md` fields (or documented N/A with reason)
- [ ] Check for symptom-only patches (guard added without upstream root-cause fix)

## C. Blast-Radius Discipline
- [ ] Verify caller/consumer search was recorded for payload/API/key changes
- [ ] Verify same anti-pattern repo-wide search was done when a bug pattern was fixed
- [ ] Verify chart-related changes followed single-source slice/merge policy

## D. Verification and Regression Guards
- [ ] CI `pytest` workflow is green for default branches
- [ ] `tests/test_ui_font_caps.py` still enforces `500/600 = 0` baseline
- [ ] If QSS/font changed, visual verification evidence exists per `spec_maintenance` §4.1

## E. Outcomes and Actions
- [ ] Track incidents: “fixed A but missed B” count this month
- [ ] Track incidents: “no confirmed root cause before fix” count this month
- [ ] Create action items for any failed checks (owner + due date)

## Monthly Log
| Month | Reviewer | Key Findings | Actions |
|------|----------|--------------|---------|
| YYYY-MM |  |  |  |
