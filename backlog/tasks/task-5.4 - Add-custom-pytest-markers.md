---
id: TASK-5.4
title: Add custom pytest markers
status: Done
assignee: []
created_date: '2026-01-28 09:11'
updated_date: '2026-02-27 14:00'
labels:
  - phase-5
  - testing
  - markers
dependencies: []
parent_task_id: TASK-5
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Define and register custom pytest markers for test categorization.

**Reference**: PRD Section 5.4 (Test Layer), existing tests/markers.py

**Location**: `tests/compatibility/markers.py` and `pyproject.toml` (marker registration)

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
- [x] #1 tests/markers.py defines marker decorators
- [x] #2 pyproject.toml registers all markers
- [x] #3 pytest -m must filters to MUST requirements only
- [x] #4 pytest -m grpc filters to gRPC tests only
- [x] #5 No unknown marker warnings when running tests
- [x] #6 Markers can be combined (e.g., -m 'must and grpc')
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented custom pytest markers for test categorization and filtering.

**Changes:**
- `pyproject.toml` — Registered `must`, `should`, `may`, `streaming`, and `integration` markers alongside existing `core`, `grpc`, `jsonrpc`, `http_json`
- `tests/compatibility/markers.py` — New module with convenient decorator aliases (`must`, `should`, `may`, `core`, `grpc`, `jsonrpc`, `http_json`, `streaming`, `integration`)
- `test_requirements.py` — Applied `@must`, `@should`, `@may` to the three requirement-level test functions
- `test_agent_card.py` — Applied `@core` to all 4 test classes
- `test_data_model.py` — Applied `@core` to all 4 test classes
- `test_error_handling.py` — Applied `@core` to core/capability/version classes, `@jsonrpc`/`@http_json`/`@grpc` to transport-specific error classes
- `test_transport_behavior.py` — Applied `@jsonrpc`/`@http_json`/`@grpc` transport markers and `@streaming` to streaming test classes

**Verification:** `make lint` passes, `pytest --co -q` shows no unknown marker warnings, filtering by `-m must`, `-m grpc`, and combined `-m "streaming and jsonrpc"` all work correctly.

Commit: ad2db89
<!-- SECTION:FINAL_SUMMARY:END -->
