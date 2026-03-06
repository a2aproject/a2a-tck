---
name: update-a2a-spec
description: Update the A2A TCK when the A2A protocol specification changes. Use when the user mentions updating the spec, syncing with upstream A2A, or when a new version of the A2A protocol is released.
compatibility: Requires curl, git, buf, and uv
allowed-tools: Bash(make:*) Bash(git:*) Bash(curl:*) Read Edit Write Glob Grep
---

# Update A2A Protocol Specification

Follow these steps to update the TCK after an A2A protocol specification change.

## Step 1: Capture the current state

Before updating, record what we have now so we can diff later.

1. Read `specification/version.json` to note the current commit hash.
2. Save copies of the key spec files for diffing:
   - `specification/specification.md`
   - `specification/a2a.proto`

## Step 2: Download the updated specification

Ask the user if they want to update from the `main` branch or pass a `tag` or a `commit cheksum`

Run:
```bash
make spec
```

This executes `scripts/update_spec.sh`, which downloads the latest spec files from the upstream `a2aproject/A2A` GitHub repository and updates `specification/version.json`.

If updating from a fork or a different branch, pass arguments:
```bash
./scripts/update_spec.sh --org <org> --branch <branch>
```

## Step 3: Regenerate gRPC stubs and JSON schema

### gRPC stubs

Run:
```bash
make proto
```

This executes `scripts/generate_grpc_stubs.sh`, which uses `buf` to regenerate `specification/generated/a2a_pb2.py` and `specification/generated/a2a_pb2_grpc.py` from the updated `a2a.proto`.

If `buf` is not installed, first run `./scripts/install_buf.sh`.

After regenerating, check the protobuf version in the generated stubs (`head -5 specification/generated/a2a_pb2.py`) and verify it is compatible with the `protobuf` runtime version installed in the project (see `pyproject.toml`). If the gencode version is newer than the runtime allows, pin the plugin versions in `specification/buf.gen.yaml` to a compatible release (e.g., `buf.build/protocolbuffers/python:v30.2`).

### JSON schema

Run:
```bash
PATH="$HOME/go/bin:$PATH" GOOGLEAPIS_DIR=<path-to-googleapis> make jsonschema
```

This regenerates `specification/a2a.json` from the updated `a2a.proto`. It requires:
- `protoc-gen-jsonschema`, installed via `go install github.com/bufbuild/protoschema-plugins/cmd/protoc-gen-jsonschema@latest`
- `GOOGLEAPIS_DIR` set to a local checkout of the [googleapis](https://github.com/googleapis/googleapis) repository

**IMPORTANT:** Never edit `specification/a2a.json` manually — always regenerate it from the proto.

## Step 4: Analyze specification changes

Compare the old and new versions of the specification to identify changes:

1. Diff `specification/specification.md` to find:
   - New operations or endpoints
   - Changed request/response schemas
   - New or modified MUST/SHOULD/MAY requirements
   - Removed or deprecated features

2. Diff `specification/a2a.proto` to find:
   - New or changed message types
   - New or changed RPC methods
   - New or changed fields

3. Summarize the changes for the user before proceeding.

## Step 5: Update transport bindings and requirements

Based on the spec diff, update the relevant files in `tck/requirements/`:

- `base.py` - Core enums (`OperationType`, HTTP methods, error codes) and base classes
- `core_operations.py` - Core operation requirements (CORE-OPS-*)
- `binding_grpc.py` - gRPC-specific requirements (GRPC-*)
- `binding_jsonrpc.py` - JSON-RPC-specific requirements (JSONRPC-*)
- `binding_http_json.py` - HTTP+JSON-specific requirements (HTTP_JSON-*)
- `data_model.py` - Data model requirements
- `streaming.py` - Streaming requirements
- `push_notifications.py` - Push notification requirements
- `agent_card.py` - Agent card requirements
- `auth.py` - Authentication requirements
- `versioning.py` - Versioning requirements
- `interop.py` - Interoperability requirements

For each spec change:
- If a new requirement is added, create a new requirement entry with the appropriate ID prefix and level (MUST/SHOULD/MAY).
- If a requirement is modified, update the existing entry.
- If a requirement is removed, remove the entry and note it.

Summarize the changes for the user before proceeding.

## Step 6: Update transport clients and validators

If the spec changes affect transport-level behavior:

- Transport clients are in `tck/transport/`
- Response validators are in `tck/validators/`

## Step 7: Update or add conformance tests

Tests are in `tests/compatibility/`:

- `core_operations/` - Cross-transport parametrized tests
- `grpc/` - gRPC-specific tests
- `jsonrpc/` - JSON-RPC-specific tests
- `http_json/` - HTTP+JSON-specific tests

Each test class uses markers from `tests/compatibility/markers.py` (`@grpc`, `@jsonrpc`, `@http_json`, `@must`, `@should`, `@may`).

Tests record results with:
```python
compliance_collector.record(requirement_id, transport, level, passed, errors)
```

## Step 8: Validate

Run the linter and unit tests:

```bash
make lint
make unit-test
```

Fix any issues before proceeding. Common failures after a spec update:
- Proto package namespace changes (e.g., `a2a.v1` to `lf.a2a.v1`) can break unit tests that assert on fully-qualified proto type names. Search for hardcoded package names in `tests/unit/`.
- Proto package namespace changes also affect `$ref` values in the regenerated JSON schema (e.g., `a2a.v1.Task.jsonschema.json` → `lf.a2a.v1.Task.jsonschema.json`). The `$ref` mapping in `tck/validators/json_schema.py` must support the new prefix, otherwise nested schema validation silently passes (refs resolve to permissive fallbacks).
- Protobuf runtime version mismatches (see Step 3).

## Step 9: Audit requirements

Before committing, audit all requirement files to verify:
- Each requirement's `section` field matches the correct section in the updated specification.
- Each requirement's `spec_url` anchor resolves to the right heading.
- No requirements reference sections or content that was removed or renamed.
- Any new MUST/SHOULD/MAY requirements in the spec have corresponding entries.

Highlight any new, modified, or removed requirements for the user.

## Step 10: Summarize

Present the user with a summary of:
- The old and new spec commit hashes (from `specification/version.json`)
- What changed in the specification
- What was updated in the TCK (requirements, tests, transport code)
- Any areas that need manual review or additional test coverage
