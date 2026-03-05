---
name: run-tck
description: Help an SDK implementor run the A2A TCK against their System Under Test (SUT). Use when the user wants to validate their A2A agent implementation, debug TCK failures, or understand conformance results.
compatibility: Requires Python 3.11+ and uv
allowed-tools: Bash Read Glob Grep Agent
---

# Run TCK Against an SDK Implementation

Follow these steps to help an SDK implementor run the A2A TCK against their SUT.

## Step 1: Verify prerequisites

Check that the TCK project is set up:

```bash
uv run python --version   # Python 3.11+ required
```

If dependencies are not installed, run:

```bash
uv pip install -e .
```

## Step 2: Confirm the SUT is running and reachable

Ask the user for their SUT URL (e.g., `http://localhost:9999`).

Verify the SUT is running by fetching its agent card:

```bash
curl -s <sut-host>/.well-known/agent-card.json | python -m json.tool
```

The agent card **must** be served at `{sut-host}/.well-known/agent-card.json` per A2A spec Section 8.2.

### Agent card requirements

The agent card must include a `supportedInterfaces` array. Each entry needs:
- `protocolBinding` — one of `"JSONRPC"`, `"GRPC"`, or `"HTTP+JSON"`
- `url` — the endpoint URL for that transport

Example:
```json
{
  "name": "My Agent",
  "supportedInterfaces": [
    { "protocolBinding": "JSONRPC", "url": "http://localhost:9999/jsonrpc" },
    { "protocolBinding": "HTTP+JSON", "url": "http://localhost:9999/a2a" }
  ]
}
```

If the agent card is missing or malformed, help the user fix it before proceeding.

## Step 3: Run the TCK

Start with MUST-level requirements on a single transport to get quick feedback:

```bash
./run_tck.py --sut-host <sut-host> --level must --transport <transport> -v
```

Where `<transport>` is one of: `grpc`, `jsonrpc`, `http_json`.

Once MUST tests pass, run the full suite:

```bash
./run_tck.py --sut-host <sut-host> -v
```

To generate compliance reports:

```bash
./run_tck.py --sut-host <sut-host> --report
```

Reports are written to `reports/` (compliance JSON + HTML, pytest-html, JUnit XML).

## Step 4: Diagnose failures

When tests fail, help the user understand and fix the issues.

### Read the test code

Find the failing test and read its source to understand the exact requirement:

```bash
# Tests are in tests/compatibility/
# Core operations: tests/compatibility/core_operations/
# Transport-specific: tests/compatibility/grpc/, jsonrpc/, http_json/
```

Each test documents its requirement ID in its docstring (e.g., `CORE-OPS-001`, `GRPC-ERR-001`).

### Look up the requirement

Requirements are defined in `tck/requirements/`. Use the requirement ID prefix to find the right file:
- `CORE-OPS-*` — `tck/requirements/core_operations.py`
- `GRPC-*` — `tck/requirements/binding_grpc.py`
- `JSONRPC-*` — `tck/requirements/binding_jsonrpc.py`
- `HTTP_JSON-*` — `tck/requirements/binding_http_json.py`

Each requirement includes a `spec_url` linking to the relevant specification section.

### Common failure patterns

1. **Connection refused** — SUT is not running or is on a different port
2. **Agent card not found (404)** — SUT doesn't serve `/.well-known/agent-card.json`
3. **No usable transports** — Agent card's `protocolBinding` values don't match any known transport, or `--transport` filter excludes all declared transports
4. **Schema validation failures** — Response payloads don't match the A2A JSON Schema or protobuf definitions
5. **Missing required fields** — Response is missing MUST-level fields per the spec
6. **Wrong error codes** — SUT returns incorrect error codes for error scenarios

### Re-run a single failing test

Use pytest's `-k` flag to isolate a specific test:

```bash
./run_tck.py --sut-host <sut-host> -- -k "test_name" -v
```

Or use verbose log output for maximum detail:

```bash
./run_tck.py --sut-host <sut-host> --verbose-log -- -k "test_name"
```

## Step 5: Interpret compliance results

### Requirement levels

| Level | Meaning | Test behavior |
|-------|---------|---------------|
| **MUST** | Absolute requirement | Hard failure — blocks compliance |
| **SHOULD** | Expected unless valid reason to differ | Expected failure (`xfail`) — does not block |
| **MAY** | Truly optional | Skipped if agent doesn't declare the capability |

### Compliance reports

When run with `--report`, the TCK generates:
- `reports/compliance.json` — machine-readable results with per-requirement and per-transport breakdowns
- `reports/compliance.html` — self-contained HTML report with executive summary
- `reports/tck_report.html` — standard pytest-html report
- `reports/junitreport.xml` — JUnit XML for CI integration

Read `reports/compliance.json` to get a structured view of which requirements passed/failed per transport.

## Step 6: Iterate

Guide the user through a fix-and-retest cycle:

1. Identify the highest-priority failure (MUST > SHOULD > MAY)
2. Read the requirement spec and the failing test
3. Help the user understand what their SUT needs to change
4. Re-run the specific failing test to verify the fix
5. Once fixed, run the full suite again to check for regressions
