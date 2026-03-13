---
name: a2a-java-sut
description: Work with the a2a-java SUT (System Under Test). Use when the user wants to regenerate the Java SUT from Gherkin scenarios, build it, run it, or test it with the TCK.
compatibility: Requires Python 3.11+, uv, Java 17+, and Maven
allowed-tools: Bash(make:*) Bash(mvn:*) Bash(java:*) Bash(curl:*) Bash(kill:*) Bash(lsof:*) Bash(uv:*) Read Edit Write Glob Grep Agent
---

# Work with the a2a-java SUT

The a2a-java SUT is a Quarkus application generated from Gherkin `.feature` files in `scenarios/`. It implements the A2A protocol using the a2a-java SDK and serves as a conformance target for TCK tests.

## Architecture overview

```
scenarios/*.feature → codegen (parser + steps + java_emitter) → sut/a2a-java/
```

- **Gherkin scenarios** (`scenarios/core_operations.feature`) define SUT behavior via messageId prefix matching
- **Code generator** (`codegen/`) parses `.feature` files and emits a Quarkus project
- **Jinja2 templates** (`codegen/a2a-java/*.j2`) produce the Java sources, `pom.xml`, and `application.properties`
- **Generated output** (`sut/a2a-java/`) is a complete Maven project

### Key generated files

| File | Template | Purpose |
|------|----------|---------|
| `TckAgentExecutorProducer.java` | `TckAgentExecutorProducer.java.j2` | CDI producer for `AgentExecutor`; routes by messageId prefix |
| `TckAgentCardProducer.java` | `TckAgentCardProducer.java.j2` | CDI producer for `AgentCard` with all three transports |
| `pom.xml` | `pom.xml.j2` | Maven build with Quarkus BOM and a2a-java SDK dependencies |
| `application.properties` | `application.properties.j2` | Quarkus config: port 9999, gRPC on same server |

### How the executor works

The generated `AgentExecutor` matches on the **messageId prefix** from incoming messages:

```java
if (messageId.startsWith("tck-send-001")) {
    emitter.sendMessage(List.of(new TextPart("Hello from TCK")));
    emitter.complete();
    return;
}
```

The TCK tests use `tck_id("send-001")` which generates `tck-send-001-<session_hex>`, matching the prefix.

## Step 0: Inform the user of the version of a2a-java

The a2a-java SDK version is controlled by the `A2A_JAVA_SDK_VERSION` environment variable.
The default value is defined in `codegen/java_emitter.py` (`_DEFAULT_A2A_JAVA_SDK_VERSION`).

Report to the user which version will be used and propose setting the env var if they want a different version:

```bash
# Use default version
make codegen-a2a-java-sut

# Use a specific version
A2A_JAVA_SDK_VERSION=1.0.0.Final make codegen-a2a-java-sut
```

## Step 1: Regenerate the SUT

When Gherkin scenarios change, regenerate the Java project:

```bash
make codegen-a2a-java-sut
```

This runs `uv run python -m codegen.generator --output sut/a2a-java` which:
1. Parses all `scenarios/*.feature` files
2. Resolves step text to Trigger/Action objects via `codegen/steps.py`
3. Emits Java sources using Jinja2 templates from `codegen/a2a-java/`

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
- `pom.xml.j2` — Maven dependencies (Quarkus BOM, a2a-java SDK, protobuf override)
- `application.properties.j2` — Quarkus runtime config

After modifying templates, regenerate with `make codegen-a2a-java-sut`.

## Step 2: Build the SUT

```bash
cd sut/a2a-java && mvn package
```

### Common build issues

- **Protobuf version mismatch** — The a2a-java SDK gencode requires a specific protobuf version. The `pom.xml.j2` overrides `protobuf-java.version` in `dependencyManagement` to match.
- **Missing SDK snapshots** — The a2a-java SDK uses SNAPSHOT versions. Ensure they are installed in the local Maven repository (`~/.m2/repository/io/github/a2asdk/`).

## Step 3: Start the SUT

```bash
cd sut/a2a-java && mvn quarkus:dev
```

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
  -d '{"jsonrpc":"2.0","id":"1","method":"SendMessage","params":{"message":{"messageId":"tck-send-001-1234","role":"ROLE_USER","parts":[{"text":"Hello from TCK"}]}}}'
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
2. Regenerate: `make codegen-a2a-java-sut`
3. Build: `cd sut/a2a-java && mvn package`
4. Restart the SUT
5. Run the relevant TCK test: `uv run ./run_tck.py --sut-host http://localhost:9999 -- -k "test_name" -v`
6. Repeat until tests pass

## Running unit tests

The codegen has its own unit tests:

```bash
make unit-test
```

This runs tests in `tests/unit/codegen/` covering the parser, step resolution, Java emitter, and generator CLI.
