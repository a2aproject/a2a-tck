---
id: TASK-12
title: Replace "compliance" with "compatibility" throughout the codebase
status: Done
assignee: []
created_date: '2026-03-12 08:07'
updated_date: '2026-03-12 08:26'
labels:
  - refactoring
  - naming
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TCK stands for "Technology Compatibility Kit", so the project should use "compatibility" instead of "compliance" consistently. There are currently ~852 occurrences of "compliance" (case-insensitive) across 64 files that need to be renamed.

**Scope includes:**
- Source code: `tck/reporting/` (aggregator, collector, formatters, `__init__`)
- Test code: `tests/unit/reporting/`, `tests/compatibility/` (conftest, test helpers, all test files)
- CLI runner: `run_tck.py` (flags like `--compliance-report`)
- Output artifacts: `compliance.json` → `compatibility.json`
- Documentation: `AGENTS.md`, `README.md`, `docs/` (SDK_VALIDATION_GUIDE, DOCUMENTATION_STANDARDS, A2A_V030_FEATURES, SPEC_UPDATE_WORKFLOW, ADRs)
- PRD files: `PRD/PRD.md`, `PRD/architecture.mmd`, `PRD/compliance-report.mmd`, `PRD/validation-flow.mmd`
- Skills: `.agents/skills/` (run-tck, diagnose-failure, learn-requirement, update-a2a-spec)
- Backlog tasks: `backlog/tasks/` and `backlog/completed/`

**Key renames:**
- `ComplianceCollector` → `CompatibilityCollector`
- `ComplianceAggregator` → `CompatibilityAggregator`
- `compliance_collector` fixture → `compatibility_collector`
- `compliance_report` CLI flag → `compatibility-report`
- `compliance.json` / `compliance.html` → `compatibility.json` / `compatibility.html`
- `compliance_level`, `compliance_badge` fields in JSON output
- `PRD/compliance-report.mmd` → `PRD/compatibility-report.mmd`
- All doc/comment references to "compliance" → "compatibility"
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 No occurrences of 'compliance' (case-insensitive) remain in source code, tests, or documentation (except LICENSE file)
- [x] #2 All class/function/variable renames are applied consistently (e.g. ComplianceCollector → CompatibilityCollector)
- [x] #3 CLI flag --compliance-report renamed to --compatibility-report
- [x] #4 Output file names updated (compliance.json → compatibility.json, compliance.html → compatibility.html)
- [x] #5 PRD/compliance-report.mmd renamed to PRD/compatibility-report.mmd
- [x] #6 All existing tests pass after the rename
- [x] #7 AGENTS.md and skill files reflect the new naming
<!-- AC:END -->
