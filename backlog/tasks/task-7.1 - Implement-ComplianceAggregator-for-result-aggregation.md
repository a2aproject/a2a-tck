---
id: task-7.1
title: Implement ComplianceAggregator for result aggregation
status: To Do
assignee: []
created_date: '2026-01-28 09:13'
labels:
  - phase-7
  - reporting
  - aggregation
dependencies:
  - task-5.3
parent_task_id: task-7
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the aggregator that computes compliance metrics from collected test results.

**Reference**: PRD Section 6 Task 7.1, Section 5.5.1

**Location**: `tck/reporting/aggregator.py`

**Class to implement**: `ComplianceAggregator`

**Methods**:

1. `__init__(self, collector: ComplianceCollector)`:
   - Take collector with raw results

2. `aggregate() -> ComplianceReport`:
   - Compute all aggregated metrics
   - Return complete report structure

3. `_compute_per_requirement() -> dict`:
   - Group results by requirement ID
   - Show pass/fail per transport

4. `_compute_per_transport() -> dict`:
   - Group results by transport
   - Compute passed/failed/total counts

5. `_compute_overall_compliance() -> float`:
   - Calculate overall compliance percentage

6. `_compute_must_compliance() -> float`:
   - Calculate MUST-only compliance percentage

**Output**: ComplianceReport dataclass with all computed metrics
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 tck/reporting/aggregator.py exists
- [ ] #2 ComplianceAggregator takes ComplianceCollector as input
- [ ] #3 aggregate() returns ComplianceReport dataclass
- [ ] #4 Per-requirement grouping shows each transport's result
- [ ] #5 Per-transport grouping shows pass/fail counts
- [ ] #6 Overall compliance percentage is calculated correctly
- [ ] #7 MUST compliance percentage is calculated separately
<!-- AC:END -->
