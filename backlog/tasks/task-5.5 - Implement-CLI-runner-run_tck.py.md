---
id: TASK-5.5
title: Implement CLI runner (run_tck.py)
status: Done
assignee: []
created_date: '2026-01-28 09:11'
updated_date: '2026-02-27 13:36'
labels:
  - phase-5
  - testing
  - cli
dependencies:
  - task-5.1
  - task-5.2
  - task-5.4
parent_task_id: TASK-5
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the main CLI entry point for running the TCK.

**Reference**: PRD Section 7.3 (Running Tests), Section 4.2 (run_tck.py)

**Location**: `run_tck.py` (project root)

**Test path**: `tests/compatibility/` (SUT conformance tests only)

**CLI interface**:
```bash
# Run all tests against a SUT
./run_tck.py --sut-url http://localhost:9999

# Run only gRPC tests
./run_tck.py --sut-url http://localhost:9999 --transport grpc

# Run with compliance report
./run_tck.py --sut-url http://localhost:9999 --compliance-report report.json

# Run only MUST requirements
./run_tck.py --sut-url http://localhost:9999 --level must

# Run specific requirement
./run_tck.py --sut-url http://localhost:9999 --requirement REQ-3.1.1
```

**Implementation**:
- Use argparse for CLI argument parsing
- Delegate to pytest with appropriate arguments
- Handle compliance report generation
- Return appropriate exit codes (0=pass, 1=fail)

**Also register as console script** in pyproject.toml:
```toml
[project.scripts]
a2a-tck = "run_tck:main"
```
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 run_tck.py exists and is executable
- [ ] #2 --sut-url option is required
- [ ] #3 --transport option filters to specific transport
- [ ] #4 --compliance-report option generates report file
- [ ] #5 --level option filters by requirement level
- [ ] #6 --requirement option runs specific requirement
- [ ] #7 Exit code 0 on success, 1 on failure
- [ ] #8 a2a-tck console script works after pip install
<!-- AC:END -->
