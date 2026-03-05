# AGENTS.md

## Project Overview

A2A Protocol Technology Compatibility Kit (TCK) — a conformance test suite that validates A2A-protocol-compliant agents across three transports: gRPC, JSON-RPC, and HTTP+JSON.

## Architecture

```
tck/                        # Main package
  requirements/             # Requirement specs and error bindings
  transport/                # Implemenation of Transport clients
  validators/               # Response validators per transport
  reporting/                # Compliance reporting
tests/
  unit/                     # Unit tests (no SUT needed)
  compatibility/            # Conformance tests (require running SUT)
    conftest.py             # Fixtures: transport_clients, agent_card, compliance_collector
    markers.py              # Pytest marker aliases: grpc, jsonrpc, http_json, must, should, may
    core_operations/        # Cross-transport parametrized tests
    grpc/                   # gRPC-specific tests
    jsonrpc/                # JSON-RPC-specific tests
    http_json/              # HTTP+JSON-specific tests
specification/              # A2A spec files and derived resources (JSON schema, proto stubs)
  generated/                # Stubs Generated from a2a.proto
skills/                     # Agent skills (see Skills section below)
```

## Key Conventions

### Transport Bindings

All A2A bindings (for transport methods, error codes, etc.) are defined centrally in `tck/requirements/base.py`.

### Requirement IDs

- Core: `CORE-OPS-*`
- gRPC: `GRPC-*` (e.g., GRPC-ERR-001, GRPC-SVC-001)
- JSON-RPC: `JSONRPC-*`
- HTTP+JSON: `HTTP_JSON-*`

### Test Patterns

- Transport-specific test classes use the corresponding marker decorator (`@grpc`, `@jsonrpc`, `@http_json` from `tests/compatibility/markers.py`)
- Tests get clients via `transport_clients` fixture (dict keyed by transport name: `"grpc"`, `"jsonrpc"`, `"http_json"`)
- Each test records results with `compliance_collector.record(requirement_id, transport, level, passed, errors)`

### Code Style

- Python 3.11+, `from __future__ import annotations` in every file
- Linter: run `make lint`
- Third-party imports used only as type hints go under `if TYPE_CHECKING:` (ruff TC002 rule)
- Import statemments are sorted
- No private member access across modules (ruff SLF001 rule) — use public properties

### Code generation

- Be concise
- Try to use existing code instead of generating new similar code
- Use the same code convention than existing code. If the existing convention seems incorrect, make suggestion before doing any changes

### PR instructions
- Follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/#summary) for the commit title and message
- Always ask if the commit is related to a GitHub issue. If that's the case, add a `This fixes #{issue}" at the end of the commit message
- Always run `make lint` and `make unit-test` before committing.

## Skills

- **update-a2a-spec** (`skills/update-a2a-spec/SKILL.md`): Step-by-step workflow for updating the TCK when the A2A protocol specification changes. Read the full skill file before starting an update.
- **run-tck** (`skills/run-tck/SKILL.md`): Guide an SDK implementor through running the TCK against their System Under Test (SUT), diagnosing failures, and achieving compliance.

## Commands

- `make lint` — run ruff linter
- `make unit-test` — run unit tests (no SUT required)
- `make spec` — update A2A specification files
- `make proto` — regenerate gRPC stubs from a2a.proto
- `./run_tck.py --sut-host http://localhost:9999` — run full conformance suite against the SUT that exposes its agent card on `localhost:9999`
- `./run_tck.py --sut-host http://localhost:9999 --transport grpc` — run single transport
- `./run_tck.py --sut-host http://localhost:9999 --level must` — run only MUST requirements
