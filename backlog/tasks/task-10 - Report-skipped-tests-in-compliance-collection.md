---
id: TASK-10
title: Report skipped tests in compatibility collection
status: Done
assignee: []
created_date: '2026-03-03 11:50'
updated_date: '2026-03-04 07:34'
labels:
  - phase-7
  - reporting
  - enhancement
dependencies:
  - TASK-7.5
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Enhance the compatibility reporting pipeline to track and report skipped tests (e.g. when a MAY-level capability is not declared by the SUT, or when a transport is not configured).

Currently, skipped tests are invisible in the compatibility report — only PASS and FAIL are recorded. This makes it unclear whether a requirement was not tested vs. tested and passed.

**Changes needed**:

1. **`CompatibilityCollector`** — Allow recording a `skipped` result (new status or a `skipped: bool` field alongside `passed`), with an optional `reason` string.

2. **`CompatibilityAggregator`** — Handle skipped results in aggregation:
   - A requirement that is only skipped (never passed/failed) should show status `SKIPPED`, not `PASS` or `FAIL`.
   - Skipped results should not count toward compatibility percentages.
   - Per-transport counts should include a `skipped` field.

3. **Formatters** (JSON, HTML, Console) — Display skipped status:
   - JSON: include `"skipped"` count in per-transport, `"SKIPPED"` status in per-requirement.
   - HTML: use a neutral colour (e.g. grey) for skipped cells.
   - Console: show skipped counts in the level table and transport summary.

4. **Test hooks / test helpers** — Update `record()` helper and/or `pytest_runtest_makereport` to capture pytest-skipped outcomes and record them in the collector.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Skipped tests are recorded in CompatibilityCollector with a reason
- [x] #2 CompatibilityAggregator produces SKIPPED status for requirements that were only skipped
- [x] #3 Skipped results do not affect compatibility percentages
- [x] #4 Per-transport summary includes skipped count
- [x] #5 All three formatters (JSON, HTML, Console) display skipped status
- [x] #6 Existing PASS/FAIL behaviour is unchanged
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented SKIPPED status throughout the compatibility reporting pipeline:

- Added `skipped: bool = False` to `TestResult` and `CompatibilityCollector.record()`
- Aggregator produces SKIPPED status for requirements only skipped, excludes them from compatibility %
- Per-transport counts include `skipped` field
- All three formatters (JSON, HTML, Console) display SKIPPED status with appropriate styling
- All compatibility test files record skips before `pytest.skip()` for transport/capability checks
- Added requirement description tooltips, transport-prefixed errors, test ID tracking, agent card rendering, and SUT URL as link in HTML report
- 182 unit tests pass, lint clean
<!-- SECTION:FINAL_SUMMARY:END -->
