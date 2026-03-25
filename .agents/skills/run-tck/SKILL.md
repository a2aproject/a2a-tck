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
curl -s <sut-host>/.well-known/agent-card.json | uv run python -m json.tool
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

**Important:** Always use `uv run` to invoke the test runner so that the
project's virtual environment and dependencies are available.
Running `./run_tck.py` directly may fail if the system Python lacks pytest or
other dependencies.

Reports are always generated in `reports/` after every run. Point the user to
`reports/compatibility.html` and `reports/tck_report.html` after the run completes.

Start with MUST-level tests to catch blocking issues first:

```bash
uv run ./run_tck.py --sut-host <sut-host> --level must -v
```

Optionally filter by transport (`grpc`, `jsonrpc`, `http_json`):

```bash
uv run ./run_tck.py --sut-host <sut-host> --transport jsonrpc --level must -v
```

Once MUST tests pass, run the full suite:

```bash
uv run ./run_tck.py --sut-host <sut-host> -v
```

## Step 4: Review failures

After a run completes, read `reports/compatibility.json` to get a structured
overview of all failures. The `per_requirement` object lists every requirement
with its status, transports, errors, and test IDs.

To show the user all failures at a glance, extract requirements where
`status` is `"FAIL"` and present them in a table with:
- Requirement ID
- Transport(s) that failed
- Error summary

For detailed diagnosis and GitHub issue drafting, use the **diagnose-failure**
skill. It will gather the requirement context, spec text, failure details,
build a curl reproducer, and draft a ready-to-file issue.

For a quick triage without a full diagnosis, you can also:

### Re-run a single failing test

Use pytest's `-k` flag to isolate a specific test:

```bash
uv run ./run_tck.py --sut-host <sut-host> -- -k "test_name" -v
```

Or use verbose log output for maximum detail:

```bash
uv run ./run_tck.py --sut-host <sut-host> --verbose-log -- -k "test_name"
```

### Deselecting stuck tests

Some tests (e.g., gRPC streaming subscribe) may hang indefinitely due to SUT
bugs. Use pytest's `--deselect` flag to skip them:

```bash
uv run ./run_tck.py --sut-host <sut-host> -v -- --deselect "tests/path/to/stuck_test"
```

Multiple `--deselect` flags can be combined. This lets the rest of the suite
run to completion while the stuck test is investigated separately.

### Common failure patterns

1. **Connection refused** — SUT is not running or is on a different port
2. **Agent card not found (404)** — SUT doesn't serve `/.well-known/agent-card.json`
3. **No usable transports** — Agent card's `protocolBinding` values don't match any known transport, or `--transport` filter excludes all declared transports
4. **Schema validation failures** — Response payloads don't match the A2A JSON Schema or protobuf definitions
5. **Missing required fields** — Response is missing MUST-level fields per the spec
6. **Wrong error codes** — SUT returns incorrect error codes for error scenarios
7. **Test hangs indefinitely** — Usually a streaming test where the SUT never closes the stream or never sends the first event. Deselect the test and file an issue against the SUT

### Tips

- **Empty errors in `compatibility.json`:** The `errors` field is often empty
  for failing requirements. Re-run the specific test with `--verbose-log` and
  `-- --tb=long` to get the actual error message and stack trace.
- **Background tasks with pipes:** Do not pipe TCK output through `tail` or
  other commands when running in the background — the pipe buffers all output
  and produces nothing until the process finishes. Run without pipes instead.

## Step 5: Interpret compatibility results

### Requirement levels

| Level | Meaning | Test behavior |
|-------|---------|---------------|
| **MUST** | Absolute requirement | Hard failure — blocks compatibility |
| **SHOULD** | Expected unless valid reason to differ | Expected failure (`xfail`) — does not block |
| **MAY** | Truly optional | Skipped if agent doesn't declare the capability |

### Compatibility reports

Every TCK run generates:
- `reports/compatibility.json` — machine-readable results with per-requirement and per-transport breakdowns
- `reports/compatibility.html` — self-contained HTML report with executive summary
- `reports/tck_report.html` — standard pytest-html report
- `reports/junitreport.xml` — JUnit XML for CI integration

Read `reports/compatibility.json` to get a structured view of which requirements passed/failed per transport.

## Step 6: Iterate

Guide the user through a fix-and-retest cycle:

1. Identify the highest-priority failure (MUST > SHOULD > MAY)
2. Read the requirement spec and the failing test
3. Help the user understand what their SUT needs to change
4. Re-run the specific failing test to verify the fix
5. Once fixed, run the full suite again to check for regressions
