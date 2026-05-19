---
name: a2a-python-sut
description: Work with the a2a-python SUT (System Under Test). Use when the user wants to regenerate the Python SUT from Gherkin scenarios, build it, run it, or test it with the TCK.
compatibility: Requires Python 3.11+ and uv
allowed-tools: Bash(make:*) Bash(uv:*) Bash(python:*) Bash(python3:*) Bash(curl:*) Bash(kill:*) Bash(lsof:*) Bash(pkill:*) Read Edit Write Glob Grep Agent
---

# Work with the a2a-python SUT

The a2a-python SUT is a Python application generated from Gherkin `.feature` files in `scenarios/`. It implements the A2A protocol using the a2a-python SDK (`a2a-sdk`) and serves as a conformance target for TCK tests.

## Architecture overview

```
scenarios/*.feature → codegen (parser + steps + python_emitter) → sut/a2a-python/
```

- **Gherkin scenarios** (`scenarios/*.feature`) define SUT behavior via messageId prefix matching
- **Code generator** (`codegen/`) parses `.feature` files and emits a Python project
- **Jinja2 templates** (`codegen/a2a-python/*.j2`) produce `sut_agent.py` and `pyproject.toml`
- **Generated output** (`sut/a2a-python/`) is a complete runnable Python project

### Key generated files

| File | Template | Purpose |
|------|----------|---------|
| `sut_agent.py` | `sut_agent.py.j2` | Main entry point; `TckAgentExecutor` with messageId-prefix routing, agent card, and server setup for all three transports |
| `pyproject.toml` | `pyproject.toml.j2` | Project config with a2a-sdk dependency (installed from local path) |

### How the executor works

The generated `TckAgentExecutor` matches on the **messageId prefix** from incoming messages:

```python
if message_id.startswith('tck-complete-task'):
    await updater.complete(updater.new_agent_message([Part(text="Hello from TCK")]))
    return
```

The TCK tests use `tck_id("complete-task")` which generates `tck-complete-task-<session_hex>`, matching the prefix.

### Server architecture

The SUT runs all three transports in a single process:
- **JSON-RPC** via `A2AStarletteApplication` (Starlette)
- **HTTP+JSON** via `A2ARESTFastAPIApplication` (FastAPI mounted on the Starlette app)
- **gRPC** via `GrpcHandler` (grpc.aio server on a separate port)

## Step 0: Inform the user of the version of a2a-python

The a2a-python SDK version is controlled by the `A2A_PYTHON_SDK_VERSION` environment variable.
The default value is defined in `codegen/python_emitter.py` (`_DEFAULT_A2A_PYTHON_SDK_VERSION`).

The SDK is installed from a local path controlled by `A2A_PYTHON_SDK_PATH` (default: `../../../a2a-python`, i.e., `~/Developer/a2aproject/a2a-python/`).

Read the actual default version from `codegen/python_emitter.py` (grep for `_DEFAULT_A2A_PYTHON_SDK_VERSION`) and check the env var. Also check the local SDK's git tag to report its actual version:

```bash
cd ~/Developer/a2aproject/a2a-python && git describe --tags 2>/dev/null || git tag --sort=-creatordate | head -1
```

Report to the user which version will be used and propose setting the env var if they want a different version:

```bash
# Use default version
make codegen-a2a-python-sut

# Use a specific version
A2A_PYTHON_SDK_VERSION=1.0.0 make codegen-a2a-python-sut
```

## Step 1: Regenerate the SUT

When Gherkin scenarios change, regenerate the Python project:

```bash
make codegen-a2a-python-sut
```

This runs `uv run python -m codegen.generator --target a2a-python --output sut/a2a-python` which:
1. Parses all `scenarios/*.feature` files
2. Resolves step text to Trigger/Action objects via `codegen/steps.py`
3. Emits Python sources using Jinja2 templates from `codegen/a2a-python/`

### Adding new SUT behaviors

To add new behaviors:

1. Add a scenario to the appropriate `.feature` file in `scenarios/`
2. If the step text doesn't match existing patterns in `codegen/steps.py`, add a new entry
3. If the action type is new, add it to `codegen/model.py` and handle it in `codegen/python_emitter.py`
4. Regenerate with `make codegen-a2a-python-sut`

### Modifying templates

Templates are in `codegen/a2a-python/`:
- `sut_agent.py.j2` — handler routing, agent card, and server setup
- `pyproject.toml.j2` — Python project dependencies

After modifying templates, regenerate with `make codegen-a2a-python-sut`.

## Step 2: Install dependencies

```bash
cd sut/a2a-python && uv sync
```

This installs the a2a-sdk from the local path and all other dependencies into a `.venv` in `sut/a2a-python/`.

### Common dependency issues

- **a2a-sdk not found** — Ensure `~/Developer/a2aproject/a2a-python/` exists and is the correct checkout. The `pyproject.toml` references it via `[tool.uv.sources]`.
- **Version mismatch** — If the SDK's API has changed, the generated code may use stale imports or method signatures. Check the SDK's changelog or recent commits.

## Step 3: Start the SUT

```bash
cd sut/a2a-python && uv run python sut_agent.py
```

Or to run in the background. **Note:** When using Claude Code's `run_in_background`,
`cd` does not work — use `uv run python sut_agent.py` from the TCK project root
instead (which uses the project-level venv, not the SUT's):

```bash
cd sut/a2a-python && uv run python sut_agent.py &
```

The SUT listens on:
- **JSON-RPC** — `http://localhost:9999` (POST)
- **HTTP+JSON** — `http://localhost:9999/a2a/rest` (REST routes)
- **gRPC** — `localhost:10000` (separate port, default is HTTP port + 1)

### Verify the SUT is running

```bash
curl -s http://localhost:9999/.well-known/agent-card.json | python3 -m json.tool
```

The agent card should list all three `supportedInterfaces` (JSONRPC, HTTP+JSON, GRPC).

### Manual curl commands

When sending manual requests to the SUT, use `tck/requirements/base.py` as the source of truth for method names and `sample_input` fields in requirement specs (e.g., `tck/requirements/core_operations.py`) for request payload format.

The A2A protocol uses **protobuf enum naming conventions**:
- Roles: `ROLE_USER`, `ROLE_AGENT` (not `user`/`USER`)
- Task states: `TASK_STATE_COMPLETED`, `TASK_STATE_WORKING`, etc.
- Parts: `{"text": "..."}` (not `{"kind": "text", "text": "..."}` — the protobuf `oneof` uses the field name to indicate part type)

**SendMessage (JSON-RPC):**
```bash
curl -s -X POST http://localhost:9999/ \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"1","method":"SendMessage","params":{"message":{"messageId":"tck-complete-task-1234","role":"ROLE_USER","parts":[{"text":"Hello from TCK"}]}}}'
```

**ListTasks (JSON-RPC):**
```bash
curl -s -X POST http://localhost:9999/ \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"1","method":"ListTasks","params":{"contextId":"<contextId>"}}'
```

**GetTask (JSON-RPC):**
```bash
curl -s -X POST http://localhost:9999/ \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"1","method":"GetTask","params":{"id":"<taskId>"}}'
```

### Port conflicts

If port 9999 is already in use:

```bash
lsof -ti:9999 | xargs kill -9
```

If gRPC port 10000 is already in use:

```bash
lsof -ti:10000 | xargs kill -9
```

## Step 4: Run the TCK against the SUT

Use the **run-tck** skill to run the TCK against this SUT with the host being `http://localhost:9999`.

## Step 5: Diagnose failures

Read `reports/compatibility.json` for structured results. For detailed diagnosis, use the **diagnose-failure** skill.

### Common failure patterns

1. **Connection refused** — SUT is not running
2. **Agent card 404** — Wrong URL; the a2a-python SDK serves at `/.well-known/agent-card.json`
3. **Unmatched messageId prefix** — The scenario prefix doesn't match what the TCK test sends; check `tck_id()` usage in tests vs prefix in `.feature` file
4. **Missing action** — Scenario doesn't handle the expected behavior; add the appropriate Then/And step
5. **SDK-level issue** — Some failures (e.g., `A2A-Version` header validation) are in the SDK itself, not the SUT; check if the SDK's server handlers implement the required behavior

### Distinguishing SUT vs SDK issues

The SUT only controls behavior inside `TckAgentExecutor.execute()` and `cancel()`. Protocol-level behavior (header validation, error code mapping, transport framing) is handled by the a2a-python SDK. If a failure is in protocol handling rather than business logic, it's an SDK issue — file it against `a2aproject/a2a-python`.

## Step 6: Iterate

The typical development cycle is:

1. Add or modify a scenario in `scenarios/*.feature`
2. Regenerate: `make codegen-a2a-python-sut`
3. Install deps: `cd sut/a2a-python && uv sync`
4. Restart the SUT: kill the old process, then `cd sut/a2a-python && uv run python sut_agent.py`
5. Run the relevant TCK test: `uv run ./run_tck.py --sut-host http://localhost:9999 -- -k "test_name" -v`
6. Repeat until tests pass

## Running unit tests

The codegen has its own unit tests:

```bash
make unit-test
```

This runs tests in `tests/unit/codegen/` covering the parser, step resolution, Python emitter, and generator CLI.
