# A2A Protocol Technology Compatibility Kit (TCK)

A compatibility test suite that validates [A2A (Agent-to-Agent) Protocol](https://google.github.io/A2A/) implementations across three transports: gRPC, JSON-RPC, and HTTP+JSON.

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) for environment management

## Installation

```bash
git clone https://github.com/a2aproject/a2a-tck.git
cd a2a-tck

uv venv
source .venv/bin/activate

uv pip install -e .
```

## Quick Start

Run the full conformance suite against your A2A agent:

```bash
./run_tck.py --sut-host http://localhost:9999
```

Run a specific transport:

```bash
./run_tck.py --sut-host http://localhost:9999 --transport grpc
```

Compatibility reports are generated in the `reports/` directory after every run.

## CLI Reference

```
./run_tck.py --sut-host URL [options] [-- pytest_args...]
```

| Flag | Description |
|------|-------------|
| `--sut-host URL` | **(required)** Base URL of the System Under Test |
| `--transport LIST` | Comma-separated transport filter (e.g. `grpc`, `jsonrpc,http_json`). Default: all transports declared in the agent card |
| `--level LEVEL` | Run only requirements at a specific RFC 2119 level: `must`, `should`, or `may` |
| `-v, --verbose` | Verbose pytest output |
| `--verbose-log` | Verbose output with log capture (`-v -s --log-cli-level=INFO`) |
| `-- pytest_args...` | Additional arguments passed through to pytest (e.g. `-- -x --pdb`) |

### Examples

```bash
# Run only MUST-level requirements
./run_tck.py --sut-host http://localhost:9999 --level must

# Run gRPC and JSON-RPC transports with verbose output
./run_tck.py --sut-host http://localhost:9999 --transport grpc,jsonrpc -v

# Pass extra pytest flags
./run_tck.py --sut-host http://localhost:9999 -- -x --pdb
```

## Compatibility Levels

Tests are organized by [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) requirement levels:

| Level | Meaning | Test behavior |
|-------|---------|---------------|
| **MUST** | Absolute requirement | Hard failure if not met |
| **SHOULD** | Expected unless there is a valid reason to differ | Expected failure (`xfail`), does not block compatibility |
| **MAY** | Truly optional | Skipped if the agent doesn't declare the capability |

Use `--level` to run only a specific level:

```bash
./run_tck.py --sut-host http://localhost:9999 --level must
./run_tck.py --sut-host http://localhost:9999 --level should
./run_tck.py --sut-host http://localhost:9999 --level may
```

## Transports

The TCK supports three A2A transports:

| Transport | `--transport` value | Protocol binding |
|-----------|-------------------|------------------|
| gRPC | `grpc` | `GRPC` |
| JSON-RPC | `jsonrpc` | `JSONRPC` |
| HTTP+JSON | `http_json` | `HTTP+JSON` |

Transport selection is driven by the agent card's `supportedInterfaces`. The TCK fetches the agent card from `{sut-host}/.well-known/agent-card.json` and creates clients for each declared interface. Use `--transport` to filter which transports are tested.

## Reports

Reports are always generated in the `reports/` directory after every run:

| Report | File | Description |
|--------|------|-------------|
| Compatibility JSON | `reports/compatibility.json` | Machine-readable compatibility results with per-requirement and per-transport breakdowns |
| Compatibility HTML | `reports/compatibility.html` | Self-contained HTML report with executive summary, agent card details, and test results |
| pytest HTML | `reports/tck_report.html` | Standard pytest-html report |
| JUnit XML | `reports/junitreport.xml` | JUnit XML for CI integration |

## SUT Code Generation

The TCK includes a code generator that produces System Under Test (SUT) implementations from Gherkin scenario files in `scenarios/`. The generator supports a `--target` flag to select the SUT type. Currently, the `a2a-java` target (a Quarkus application using the [a2a-java SDK](https://github.com/a2aproject/a2a-java)) is supported.

```bash
# Generate the a2a-java SUT from Gherkin scenarios
make codegen-a2a-java-sut

# Build and start the SUT
cd sut/a2a-java && mvn package && mvn quarkus:dev

# Run the TCK against it
./run_tck.py --sut-host http://localhost:9999
```

The SDK version is controlled by the `A2A_JAVA_SDK_VERSION` environment variable (see `codegen/java_emitter.py` for the default).

## Development

| Command | Description |
|---------|-------------|
| `make lint` | Run ruff linter |
| `make unit-test` | Run unit tests (no SUT required) |
| `make spec` | Update A2A specification files from [https://github.com/a2aproject/A2A](A2A GitHub repository) |
| `make proto` | Regenerate gRPC stubs from `a2a.proto` |
| `make codegen-a2a-java-sut` | Generate the a2a-java SUT from Gherkin scenarios |

See [AGENTS.md](AGENTS.md) for architecture details and contribution guidelines.

## License

[Apache License 2.0](LICENSE)
