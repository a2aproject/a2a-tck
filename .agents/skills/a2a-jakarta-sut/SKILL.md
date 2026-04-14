---
name: a2a-jakarta-sut
description: Work with the a2a-jakarta SUT (System Under Test). Use when the user wants to regenerate the Jakarta SUT from Gherkin scenarios, build it, run it, or test it with the TCK.
compatibility: Requires Python 3.11+, uv, Java 17+, and Maven
allowed-tools: Bash(make:*) Bash(mvn:*) Bash(java:*) Bash(curl:*) Bash(kill:*) Bash(lsof:*) Bash(uv:*) Read Edit Write Glob Grep Agent
---

# Work with the a2a-jakarta SUT

The a2a-jakarta SUT is a WildFly application generated from Gherkin `.feature` files in `scenarios/`. It implements the A2A protocol using the Jakarta EE A2A SDK and serves as a conformance target for TCK tests.

## Architecture overview

```
scenarios/*.feature → codegen (parser + steps + jakarta_emitter) → sut/a2a-jakarta/
```

- **Gherkin scenarios** (`scenarios/*.feature`) define SUT behavior via messageId prefix matching
- **Code generator** (`codegen/`) parses `.feature` files and emits a WildFly project
- **Jinja2 templates** (`codegen/a2a-jakarta/*.j2`) produce the Java sources, `pom.xml`, `beans.xml`, and JAX-RS Application class
- **Generated output** (`sut/a2a-jakarta/`) is a complete Maven WAR project

### Key generated files

| File | Template | Purpose |
|------|----------|---------|
| `TckAgentExecutorProducer.java` | `TckAgentExecutorProducer.java.j2` | CDI producer for `AgentExecutor`; routes by messageId prefix |
| `TckAgentCardProducer.java` | `TckAgentCardProducer.java.j2` | CDI producer for `AgentCard` with all three transports |
| `TckApplication.java` | `TckApplication.java.j2` | JAX-RS `@ApplicationPath("/")` entry point |
| `beans.xml` | `beans.xml.j2` | CDI descriptor with gRPC exclusion |
| `pom.xml` | `pom.xml.j2` | Maven build with WildFly plugin and Jakarta SDK dependencies |

### How the executor works

The generated `AgentExecutor` matches on the **messageId prefix** from incoming messages:

```java
if (messageId.startsWith("tck-complete-task")) {
    emitter.complete(A2A.toAgentMessage("Hello from TCK"));
    return;
}
```

The TCK tests use `tck_id("complete-task")` which generates `tck-complete-task-<session_hex>`, matching the prefix.

## Step 0: Inform the user of the version of the Jakarta SDK

The Jakarta SDK version is controlled by the `A2A_JAKARTA_SDK_VERSION` environment variable.
The default value is defined in `codegen/jakarta_emitter.py` (`_DEFAULT_A2A_JAKARTA_SDK_VERSION`).

Read the actual default version from `codegen/jakarta_emitter.py` (grep for `_DEFAULT_A2A_JAKARTA_SDK_VERSION`) and check the env var. Report to the user which version will be used and propose setting the env var if they want a different version:

```bash
# Use default version
make codegen-a2a-jakarta-sut

# Use a specific version
A2A_JAKARTA_SDK_VERSION=1.0.0.Alpha4 make codegen-a2a-jakarta-sut
```

The a2a-java SDK version (used for `a2a-java-sdk-client` and `a2a-java-sdk-server-common` dependencies) is controlled by `A2A_JAVA_SDK_VERSION`. Its default is defined in `codegen/java_emitter.py` (`_DEFAULT_A2A_JAVA_SDK_VERSION`).

The WildFly and gRPC feature pack versions can also be overridden:
- `WILDFLY_VERSION` (default in `codegen/jakarta_emitter.py`)
- `WILDFLY_GRPC_VERSION` (default in `codegen/jakarta_emitter.py`)

## Step 1: Regenerate the SUT

When Gherkin scenarios change, regenerate the Jakarta project:

```bash
make codegen-a2a-jakarta-sut
```

This runs `uv run python -m codegen.generator --target a2a-jakarta --output sut/a2a-jakarta` which:
1. Parses all `scenarios/*.feature` files
2. Resolves step text to Trigger/Action objects via `codegen/steps.py`
3. Emits Java sources using Jinja2 templates from `codegen/a2a-jakarta/`

### Adding new SUT behaviors

To add new behaviors:

1. Add a scenario to the appropriate `.feature` file in `scenarios/`
2. If the step text doesn't match existing patterns in `codegen/steps.py`, add a new entry
3. If the action type is new, add it to `codegen/model.py` and handle it in `codegen/java_emitter.py` (shared with `jakarta_emitter.py`)
4. Regenerate with `make codegen-a2a-jakarta-sut`

### Modifying templates

Templates are in `codegen/a2a-jakarta/`:
- `TckAgentExecutorProducer.java.j2` — handler routing and action code
- `TckAgentCardProducer.java.j2` — agent card with capabilities and interfaces
- `TckApplication.java.j2` — JAX-RS Application class
- `beans.xml.j2` — CDI beans descriptor
- `pom.xml.j2` — Maven dependencies (WildFly plugin, Jakarta SDK, transport profiles)

After modifying templates, regenerate with `make codegen-a2a-jakarta-sut`.

## Step 2: Build the SUT

```bash
cd sut/a2a-jakarta && mvn package
```

The default Maven profile includes JSONRPC, gRPC, and HTTP+JSON transports.

### Common build issues

- **Missing SDK snapshots** — The Jakarta SDK may use SNAPSHOT versions. Ensure they are installed in the local Maven repository (`~/.m2/repository/org/wildfly/a2a/`).
- **WildFly provisioning failures** — The WildFly Maven plugin provisions a server via Galleon. Network issues or missing feature packs can cause failures.

## Step 3: Start the SUT

```bash
cd sut/a2a-jakarta && mvn wildfly:dev
```

The SUT listens on:
- **JSON-RPC** — `http://localhost:8080` (POST)
- **gRPC** — `localhost:9555` (separate port)
- **HTTP+JSON** — `http://localhost:8080` (REST routes)

### Verify the SUT is running

```bash
curl -s http://localhost:8080/.well-known/agent-card.json | python3 -m json.tool
```

The agent card should list all three `supportedInterfaces` (JSONRPC, GRPC, HTTP+JSON).

### Manual curl commands

When sending manual requests to the SUT, use `tck/requirements/base.py` as the source of truth for method names and `sample_input` fields in requirement specs (e.g., `tck/requirements/core_operations.py`) for request payload format.

**SendMessage (JSON-RPC):**
```bash
curl -s -X POST http://localhost:8080/ \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"1","method":"SendMessage","params":{"message":{"messageId":"tck-complete-task-1234","role":"ROLE_USER","parts":[{"text":"Hello from TCK"}]}}}'
```

### Port conflicts

If port 8080 is already in use:

```bash
lsof -ti:8080 | xargs kill -9
```

## Step 4: Run the TCK against the SUT

Use the **run-tck** skill to run the TCK against this SUT with the host being `http://localhost:8080`.

## Step 5: Diagnose failures

Read `reports/compatibility.json` for structured results. For detailed diagnosis, use the **diagnose-failure** skill.

### Common failure patterns

1. **Connection refused** — SUT is not running
2. **Agent card 404** — Wrong URL; the SDK serves at `/.well-known/agent-card.json`
3. **Unmatched messageId prefix** — The scenario prefix doesn't match what the TCK test sends; check `tck_id()` usage in tests vs prefix in `.feature` file
4. **Missing action** — Scenario doesn't handle the expected behavior; add the appropriate Then/And step

## Step 6: Iterate

The typical development cycle is:

1. Add or modify a scenario in `scenarios/*.feature`
2. Regenerate: `make codegen-a2a-jakarta-sut`
3. Build: `cd sut/a2a-jakarta && mvn package`
4. Restart the SUT
5. Run the relevant TCK test: `uv run ./run_tck.py --sut-host http://localhost:8080 -- -k "test_name" -v`
6. Repeat until tests pass

## Running unit tests

The codegen has its own unit tests:

```bash
make unit-test
```

This runs tests in `tests/unit/codegen/` covering the parser, step resolution, Jakarta emitter, and generator CLI.
