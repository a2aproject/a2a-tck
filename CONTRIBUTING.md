# Contributing to A2A TCK

Thank you for your interest in contributing to the A2A Protocol Technology Compatibility Kit.

## Development Setup

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) for environment management

### Getting started

```bash
git clone https://github.com/a2aproject/a2a-tck.git
cd a2a-tck

uv venv
source .venv/bin/activate

uv pip install -e ".[dev]"
```

### Running checks

```bash
make lint        # Run ruff linter
make unit-test   # Run unit tests (no SUT required)
```

## Code Style

- Python 3.11+, `from __future__ import annotations` in every file
- Linter: [ruff](https://docs.astral.sh/ruff/), line length 130 (`make lint`)
- Import statements are sorted
- Third-party imports used only as type hints go under `if TYPE_CHECKING:` (ruff TC002)
- No private member access across modules (ruff SLF001) — use public properties

## Project Structure

See [AGENTS.md](AGENTS.md) for the full architecture overview.

```
tck/
  requirements/     # Requirement specs and error bindings
  transport/        # Transport client implementations
  validators/       # Response validators per transport
  reporting/        # Compatibility reporting
tests/
  unit/             # Unit tests (no SUT needed)
  compatibility/    # Conformance tests (require running SUT)
specification/      # A2A spec files and derived resources
```

## Adding a Requirement

Requirements are defined as `RequirementSpec` instances in `tck/requirements/`.

### 1. Create the requirement

Add a `RequirementSpec` to the appropriate file (e.g., `tck/requirements/core_operations.py`):

```python
from tck.requirements.base import (
    RequirementLevel,
    RequirementSpec,
    OperationType,
    SEND_MESSAGE_BINDING,
    SPEC_BASE,
    tck_id,
)

MY_REQUIREMENT = RequirementSpec(
    id="CORE-FEAT-001",
    section="3.1",
    title="Short description of the requirement",
    level=RequirementLevel.MUST,
    description="Detailed description of what the spec mandates.",
    operation=OperationType.SEND_MESSAGE,
    binding=SEND_MESSAGE_BINDING,
    sample_input={
        "message": {
            "role": "user",
            "parts": [{"kind": "text", "text": "hello"}],
            "messageId": tck_id("my-feat"),
        }
    },
    spec_url=f"{SPEC_BASE}31-section-anchor",
)
```

### 2. Register it

Add the requirement to the module-level list (e.g., `CORE_OPERATIONS_REQUIREMENTS`) in the same file. The registry in `tck/requirements/registry.py` automatically picks it up. Duplicate IDs cause an import-time error.

### 3. Requirement ID conventions

| Prefix | Source file |
|--------|------------|
| `CORE-*` | `core_operations.py` |
| `DM-*` | `data_model.py` |
| `STREAM-*` | `streaming.py` |
| `PUSH-*` | `push_notifications.py` |
| `CARD-*` | `agent_card.py` |
| `AUTH-*` | `auth.py` |
| `GRPC-*` | `binding_grpc.py` |
| `JSONRPC-*` | `binding_jsonrpc.py` |
| `HTTP_JSON-*` | `binding_http_json.py` |
| `INTEROP-*` | `interop.py` |
| `VER-*` | `versioning.py` |

## Adding Tests

### Parametrized requirement tests

Most requirements are tested automatically via `tests/compatibility/core_operations/test_requirements.py`. If your requirement has an `operation`, `binding`, and `sample_input`, it will be picked up by the parametrized test runner — no additional test code needed.

### Transport-specific tests

For behavior that is specific to a single transport, add tests under the appropriate directory:

- `tests/compatibility/grpc/` — gRPC-specific tests
- `tests/compatibility/jsonrpc/` — JSON-RPC-specific tests
- `tests/compatibility/http_json/` — HTTP+JSON-specific tests

Use marker decorators from `tests/compatibility/markers.py`:

```python
from tests.compatibility.markers import jsonrpc, must

@must
@jsonrpc
class TestMyFeature:
    def test_something(self, transport_clients, compatibility_collector):
        client = transport_clients["jsonrpc"]
        # ... test logic ...
        compatibility_collector.record(
            requirement_id="JSONRPC-FEAT-001",
            transport="jsonrpc",
            level="MUST",
            passed=True,
        )
```

### Key fixtures

| Fixture | Scope | Description |
|---------|-------|-------------|
| `transport_clients` | session | Dict of transport clients keyed by name (`"grpc"`, `"jsonrpc"`, `"http_json"`) |
| `agent_card` | session | The SUT's agent card (fetched once) |
| `compatibility_collector` | session | Records test results for compatibility reporting |
| `validators` | session | Dict of validators keyed by transport name |

### Unit tests

Unit tests go in `tests/unit/` and do not require a running SUT. Always add unit tests for new validators or utility functions.

## Pull Request Process

1. Follow [Conventional Commits](https://www.conventionalcommits.org/) for commit messages:
   - `feat:` — new feature (SemVer minor)
   - `fix:` — bug fix (SemVer patch)
   - `refactor:`, `chore:`, `docs:`, `test:` — non-release changes
   - Append `!` for breaking changes (e.g., `feat!:`)

2. Run checks before submitting:
   ```bash
   make lint
   make unit-test
   ```

3. If the PR fixes a GitHub issue, add `Fixes #<number>` to the commit message.

4. Keep PRs focused — one logical change per PR.

## Updating the A2A Specification

When the upstream A2A protocol specification changes:

```bash
make spec    # Update specification files
make proto   # Regenerate gRPC stubs (if proto changed)
```

See `.agents/skills/update-a2a-spec/SKILL.md` for the full update workflow.

## License

By contributing, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).
