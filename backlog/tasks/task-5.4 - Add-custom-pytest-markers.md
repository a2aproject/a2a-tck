---
id: task-5.4
title: Add custom pytest markers
status: To Do
assignee: []
created_date: '2026-01-28 09:11'
labels:
  - phase-5
  - testing
  - markers
dependencies: []
parent_task_id: task-5
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Define and register custom pytest markers for test categorization.

**Reference**: PRD Section 5.4 (Test Layer), existing tests/markers.py

**Location**: `tests/markers.py` and `pyproject.toml` (marker registration)

**Markers to define**:

1. `@pytest.mark.must` - MUST-level requirements
2. `@pytest.mark.should` - SHOULD-level requirements
3. `@pytest.mark.may` - MAY-level requirements
4. `@pytest.mark.grpc` - gRPC-specific tests
5. `@pytest.mark.jsonrpc` - JSON-RPC-specific tests
6. `@pytest.mark.rest` - REST-specific tests
7. `@pytest.mark.streaming` - Streaming-related tests
8. `@pytest.mark.integration` - Integration tests (require server)

**Usage**:
```bash
pytest -m must        # Only MUST requirements
pytest -m grpc        # Only gRPC tests
pytest -m "not integration"  # Skip integration tests
```

**Register in pyproject.toml**:
```toml
[tool.pytest.ini_options]
markers = [
    "must: MUST-level requirements",
    ...
]
```
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 tests/markers.py defines marker decorators
- [ ] #2 pyproject.toml registers all markers
- [ ] #3 pytest -m must filters to MUST requirements only
- [ ] #4 pytest -m grpc filters to gRPC tests only
- [ ] #5 No unknown marker warnings when running tests
- [ ] #6 Markers can be combined (e.g., -m 'must and grpc')
<!-- AC:END -->
