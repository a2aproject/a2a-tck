---
id: TASK-5.2
title: Implement parametrized requirement tests
status: Done
assignee: []
created_date: '2026-01-28 09:11'
updated_date: '2026-02-27 13:36'
labels:
  - phase-5
  - testing
  - parametrization
dependencies:
  - task-5.1
parent_task_id: TASK-5
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the core parametrized tests that run each requirement across all transports.

**Reference**: PRD Section 5.4.1 (Core Parametrised Tests), Section 4.3.2

**Location**: `tests/compatibility/core_operations/test_requirements.py`

**Test structure**:
```python
TRANSPORTS = ["grpc", "jsonrpc", "http+json"]

@pytest.mark.parametrize("transport", TRANSPORTS)
@pytest.mark.parametrize("requirement", MUST_REQUIREMENTS, ids=lambda r: r.id)
def test_must_requirement(transport, requirement, transport_clients, validators, compatibility_collector):
    # Execute
    client = transport_clients[transport]
    response = client.execute(requirement.operation, requirement.sample_input)
    
    # Validate
    validator = validators[transport]
    result = validator.validate(response, requirement)
    
    # Record
    compatibility_collector.record(requirement.id, transport, result.valid, result.errors)
    
    # Assert
    assert result.valid, f"{requirement.id} failed: {result.errors}"
```

**Similar tests for**:
- SHOULD requirements (warnings, not failures)
- MAY requirements (skip if capability not declared)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 tests/core_operations/test_requirements.py exists
- [ ] #2 test_must_requirement is parametrized by transport and requirement
- [ ] #3 test_should_requirement handles SHOULD-level as warnings
- [ ] #4 Test IDs include requirement ID (e.g., test[grpc-REQ-3.1.1])
- [ ] #5 Failure messages include requirement ID, title, and spec_url
- [ ] #6 Results are recorded to compatibility_collector
<!-- AC:END -->
