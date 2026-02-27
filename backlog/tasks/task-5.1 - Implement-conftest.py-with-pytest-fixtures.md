---
id: TASK-5.1
title: Implement conftest.py with pytest fixtures
status: Done
assignee: []
created_date: '2026-01-28 09:11'
updated_date: '2026-02-27 13:36'
labels:
  - phase-5
  - testing
  - fixtures
dependencies: []
parent_task_id: TASK-5
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the pytest configuration and fixtures for the TCK test suite.

**Reference**: PRD Section 7.2 (Test Fixtures)

**Location**: `tests/compatibility/conftest.py`

**CLI options to add**:
- `--sut-url`: SUT base URL (required)
- `--transport`: Transport to test (default: "all")
- `--compliance-report`: Output report path (optional)

**Fixtures to implement**:

1. `sut_url(request)` - Session scope:
   - Returns --sut-url option value

2. `transport_clients(sut_url)` - Session scope:
   - Returns dict: {"grpc": GrpcClient, "jsonrpc": JsonRpcClient, "http+json": HttpJsonClient}

3. `validators()` - Session scope:
   - Returns dict: {"grpc": ProtoSchemaValidator, "jsonrpc": JSONSchemaValidator, "http+json": JSONSchemaValidator}

4. `compliance_collector()` - Session scope:
   - Returns ComplianceCollector instance for result aggregation

5. `agent_card(transport_clients)` - Session scope:
   - Fetches agent card from SUT for capability checking
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 tests/conftest.py exists
- [ ] #2 pytest_addoption adds --sut-url, --transport, --compliance-report options
- [ ] #3 sut_url fixture returns URL from command line
- [ ] #4 transport_clients fixture creates all three clients
- [ ] #5 validators fixture creates appropriate validator per transport
- [ ] #6 compliance_collector fixture provides result collection
- [ ] #7 agent_card fixture fetches SUT agent card
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Created `tests/conftest.py` with shared pytest fixtures for the A2A TCK:

- **CLI options** via `pytest_addoption`: `--sut-host` (default "localhost"), `--transport` (default "all", supports comma-separated filter), `--compliance-report` (optional output path)
- **`sut_host` fixture** (session): returns the SUT hostname
- **`transport_clients` fixture** (session): uses `TransportManager` with transport filtering, yields client dict, closes on teardown
- **`validators` fixture** (session): returns `{"grpc": ProtoSchemaValidator(), "jsonrpc": JSONSchemaValidator(...), "http_json": JSONSchemaValidator(...)}`
- **`compliance_collector` fixture** (session): placeholder `_ComplianceCollector` dataclass with `record()`, `get_results()`, `reset()` methods (to be replaced by task 5.3)
- **`agent_card` fixture** (session): fetches agent card from `https://{sut_host}/.well-known/agent-card.json` per the A2A spec
<!-- SECTION:FINAL_SUMMARY:END -->
