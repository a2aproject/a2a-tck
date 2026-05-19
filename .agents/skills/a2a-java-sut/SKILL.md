---
name: a2a-java-sut
description: Work with the a2a-java SUT (System Under Test). Use when the user wants to regenerate the Java SUT from Gherkin scenarios, build it, run it, or test it with the TCK.
compatibility: Requires Python 3.11+, uv, Java 17+, and Maven
allowed-tools: Bash(make:*) Bash(mvn:*) Bash(java:*) Bash(curl:*) Bash(kill:*) Bash(lsof:*) Bash(uv:*) Read Edit Write Glob Grep Agent
---

# Work with the a2a-java SUT

The a2a-java SUT is a Quarkus application that lives in the [`tck` module](https://github.com/a2aproject/a2a-java/tree/main/tck) of the a2a-java repository. The TCK code generator produces two CDI producer files (`TckAgentCardProducer.java` and `TckAgentExecutorProducer.java`) from Gherkin `.feature` files and copies them into the user's local clone of the a2a-java repo.

## Architecture overview

```
scenarios/*.feature → codegen (parser + steps + java_emitter) → $A2A_JAVA_DIR/tck/
```

- **Gherkin scenarios** (`scenarios/*.feature`) define SUT behavior via messageId prefix matching
- **Code generator** (`codegen/`) parses `.feature` files and emits Java sources
- **Jinja2 templates** (`codegen/a2a-java/*.j2`) produce the two CDI producer files
- **Generated output** goes into the `tck` module of the user's local a2a-java clone

### Key generated files

| File | Template | Purpose |
|------|----------|---------|
| `TckAgentExecutorProducer.java` | `TckAgentExecutorProducer.java.j2` | CDI producer for `AgentExecutor`; routes by messageId prefix |
| `TckAgentCardProducer.java` | `TckAgentCardProducer.java.j2` | CDI producer for `AgentCard` with all three transports |

### How the executor works

The generated `AgentExecutor` matches on the **messageId prefix** from incoming messages:

```java
if (messageId.startsWith("tck-complete-task")) {
    emitter.complete(A2A.toAgentMessage("Hello from TCK"));
    return;
}
```

The TCK tests use `tck_id("complete-task")` which generates `tck-complete-task-<session_hex>`, matching the prefix.

## Step 0: Set up the a2a-java clone

The `A2A_JAVA_DIR` environment variable must point to the root of a local clone of the [a2a-java](https://github.com/a2aproject/a2a-java) repository.

Check if the clone already exists as a sibling directory:

```bash
ls -d ../a2a-java 2>/dev/null && echo "Found at ../a2a-java"
```

If it exists, set:
```bash
export A2A_JAVA_DIR=$(cd ../a2a-java && pwd)
```

If not, clone it:
```bash
git clone https://github.com/a2aproject/a2a-java.git ../a2a-java
export A2A_JAVA_DIR=$(cd ../a2a-java && pwd)
```

## Step 1: Regenerate the SUT

When Gherkin scenarios change, regenerate the Java producer files:

```bash
A2A_JAVA_DIR=/path/to/a2a-java make codegen-a2a-java-sut
```

This runs `uv run python -m codegen.generator --target a2a-java --output $A2A_JAVA_DIR/tck` which:
1. Parses all `scenarios/*.feature` files
2. Resolves step text to Trigger/Action objects via `codegen/steps.py`
3. Emits `TckAgentCardProducer.java` and `TckAgentExecutorProducer.java` using Jinja2 templates from `codegen/a2a-java/`
4. Writes them into `$A2A_JAVA_DIR/tck/src/main/java/org/a2aproject/sdk/sut/`

### Adding new SUT behaviors

To add new behaviors:

1. Add a scenario to the appropriate `.feature` file in `scenarios/`
2. If the step text doesn't match existing patterns in `codegen/steps.py`, add a new entry
3. If the action type is new, add it to `codegen/model.py` and handle it in `codegen/java_emitter.py`
4. Regenerate with `make codegen-a2a-java-sut`

### Modifying templates

Templates are in `codegen/a2a-java/`:
- `TckAgentExecutorProducer.java.j2` — handler routing and action code
- `TckAgentCardProducer.java.j2` — agent card with capabilities and interfaces

After modifying templates, regenerate with `make codegen-a2a-java-sut`.

## Step 2: Build the SUT

Build from the root of the a2a-java repository so the parent pom and SDK modules are installed first:

```bash
cd $A2A_JAVA_DIR && mvn clean install
```

## Step 3: Start the SUT

```bash
cd $A2A_JAVA_DIR/tck && mvn quarkus:dev -Dquarkus.console.enabled=false
```

The `-Dquarkus.console.enabled=false` flag disables the interactive Quarkus console, which is required when running in the background or non-interactively.

The SUT listens on port **9999** and serves all three transports:
- **JSON-RPC** — `http://localhost:9999` (POST)
- **gRPC** — `localhost:9999` (same server, no separate port)
- **HTTP+JSON** — `http://localhost:9999` (REST routes)

### Verify the SUT is running

```bash
curl -s http://localhost:9999/.well-known/agent-card.json | python3 -m json.tool
```

The agent card should list all three `supportedInterfaces` (JSONRPC, GRPC, HTTP+JSON).

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

## Step 4: Run the TCK against the SUT

Use the **run-tck** skill to run the TCK against this SUT with the host being `http://localhost:9999`.

## Step 5: Diagnose failures

Read `reports/compatibility.json` for structured results. For detailed diagnosis, use the **diagnose-failure** skill.

### Common failure patterns

1. **Connection refused** — SUT is not running
2. **Agent card 404** — Wrong URL; the a2a-java SDK serves at `/.well-known/agent-card.json`
3. **Unmatched messageId prefix** — The scenario prefix doesn't match what the TCK test sends; check `tck_id()` usage in tests vs prefix in `.feature` file
4. **Missing action** — Scenario doesn't handle the expected behavior; add the appropriate Then/And step

## Step 6: Iterate

The typical development cycle is:

1. Add or modify a scenario in `scenarios/*.feature`
2. Regenerate: `A2A_JAVA_DIR=/path/to/a2a-java make codegen-a2a-java-sut`
3. Build: `cd $A2A_JAVA_DIR && mvn clean install`
4. Restart the SUT
5. Run the relevant TCK test: `uv run ./run_tck.py --sut-host http://localhost:9999 -- -k "test_name" -v`
6. Repeat until tests pass

## Running unit tests

The codegen has its own unit tests:

```bash
make unit-test
```

This runs tests in `tests/unit/codegen/` covering the parser, step resolution, Java emitter, and generator CLI.
