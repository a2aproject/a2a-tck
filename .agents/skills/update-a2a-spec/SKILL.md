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

Skip this step if `specification/a2a.proto` did not change (diff shows no proto changes).

### gRPC stubs

Run:
```bash
make proto
```

This executes `scripts/generate_grpc_stubs.sh`, which uses `buf` to regenerate `specification/generated/a2a_pb2.py` and `specification/generated/a2a_pb2_grpc.py` from the updated `a2a.proto`.

If `buf` is not installed, first run `./scripts/install_buf.sh`.

After regenerating, check the protobuf version in the generated stubs (`head -5 specification/generated/a2a_pb2.py`) and verify it is compatible with the `protobuf` runtime version installed in the project (see `pyproject.toml`). If the gencode version is newer than the runtime allows, pin the plugin versions in `specification/buf.gen.yaml` to a compatible release (e.g., `buf.build/protocolbuffers/python:v30.2`).

### JSON schema

Ask the user for the path to their local [googleapis](https://github.com/googleapis/googleapis) checkout, then run:
```bash
PATH="$HOME/go/bin:$PATH" GOOGLEAPIS_DIR=<path-to-googleapis> make jsonschema
```

This regenerates `specification/a2a.json` from the updated `a2a.proto`. It requires:
- `protoc-gen-jsonschema`, installed via `go install github.com/bufbuild/protoschema-plugins/cmd/protoc-gen-jsonschema@latest`
- `GOOGLEAPIS_DIR` set to the user's local googleapis checkout

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
  - `tck/validators/error_info.py` — shared ErrorInfo validation for JSON-RPC and HTTP+JSON (ProtoJSON `@type` format)
  - `tck/validators/grpc/error_validator.py` — gRPC ErrorInfo extraction (binary protobuf)
  - `tck/validators/http_json/error_validator.py` — AIP-193 error format parsing
  - `tck/validators/jsonrpc/error_validator.py` — JSON-RPC error code validation
  - `tck/validators/error_binding.py` — cross-transport expected-error validation

## Step 7: Update or add conformance tests

Tests are in `tests/compatibility/`:

- `core_operations/` - Cross-transport parametrized tests
- `grpc/` - gRPC-specific tests
- `jsonrpc/` - JSON-RPC-specific tests
- `http_json/` - HTTP+JSON-specific tests
- `agent_card/` - Agent card tests (discovery, caching, signing)

Each test class uses markers from `tests/compatibility/markers.py` (`@grpc`, `@jsonrpc`, `@http_json`, `@core`, `@must`, `@should`, `@may`).

Tests use helpers from `tests/compatibility/_test_helpers.py`:
- `get_client()` — get transport client with skip-on-missing handling
- `record()` — record result to compatibility collector
- `fail_msg()` — format assertion message with requirement context

Tests record results with:
```python
compatibility_collector.record(requirement_id, transport, level, passed, errors)
```

When writing tests, prefer using transport clients (`client.get_task()`, `client.cancel_task()`, etc.) over raw HTTP calls. Only use raw `httpx` calls when the test needs custom headers (e.g., `A2A-Version`), invalid methods, malformed payloads, or wrong `Content-Type`.

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

To verify anchors programmatically, note that GitHub strips dots and special characters from heading text when generating anchors. For example, heading `#### 3.1.1. Send Message` produces anchor `#311-send-message` (not `#3.1.1.-send-message`). The `SPEC_BASE` constant in `base.py` is `specification/specification.md#`, and the `_spec_url_to_href()` function in `html_formatter.py` converts these to absolute GitHub URLs using the commit hash from `version.json`.

Highlight any new, modified, or removed requirements for the user.

## Step 10: Summarize

Present the user with a summary of:
- The old and new spec commit hashes (from `specification/version.json`)
- What changed in the specification
- What was updated in the TCK (requirements, tests, transport code)
- Any areas that need manual review or additional test coverage
