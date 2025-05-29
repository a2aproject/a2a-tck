# A2A Protocol Technology Compatibility Kit (TCK)

A test suite for verifying compliance with the A2A (Application-to-Application) JSON-RPC protocol specification.

## Overview

The A2A Protocol TCK is a comprehensive test suite designed to validate that an implementation of the A2A protocol adheres to the A2A JSON-RPC specification. It exercises various aspects of the protocol through a series of tests that verify both normal operation and error handling.

The TCK acts as a client, sending requests to a running A2A implementation (the System Under Test, or SUT) and validating the responses against the specification.

## Features

- **Comprehensive Coverage**: Tests all core A2A JSON-RPC methods.
- **Protocol Validation**: Ensures proper message structure, error codes, and response formats.
- **Conditional Testing**: Adapts to the capabilities of the SUT (e.g., streaming, push notifications).
- **Detailed Logging**: Provides clear logs of all interactions and test results.
- **HTML Reports**: Optional HTML report generation for easy interpretation of results.

## Requirements

- uv (recommended for environment management and dependency installation)
- Python 3.8+
- A running A2A implementation (SUT) with an accessible HTTP/HTTPS endpoint

## Installation

1. Install uv:
   ```bash
   # Install uv (see https://github.com/astral-sh/uv#installation)
   curl -LsSf https://astral.sh/uv/install.sh | sh
   # Or using pipx: pipx install uv
   # Or using brew: brew install uv
   ```

2. Clone this repository:
   ```bash
   git clone https://github.com/maeste/a2a-tck.git
   cd a2a-tck
   ```

3. Create and activate a virtual environment using uv:
   ```bash
   uv venv
   source .venv/bin/activate  # Linux/macOS
   # .venv\\Scripts\\activate   # Windows
   ```

4. Install the required dependencies using uv:
   ```bash
   # Install using requirements.txt (basic installation)
   uv pip install -r requirements.txt

   # Or install using uv with the package (development mode)
   uv pip install -e .

   # For development with additional tools (linting, formatting)
   uv pip install -e ".[dev]"
   ```
5. Run the SUT (here the example to run the local python based on python sdk https://github.com/google/a2a-python to run core tests)
   ```bash
   cd a2a-tck/python-sut/tck_core_agent
   uv run .

## Usage

### Basic Usage

Run the TCK against your A2A implementation using the included runner script:

```bash
./run_tck.py --sut-url http://your-sut-host:port/api
```

This will execute all core tests against the specified SUT endpoint.

### Command-Line Options

The runner script supports several options:

```
--sut-url URL          URL of the SUT's A2A JSON-RPC endpoint (required)
--test-scope SCOPE     Test scope: 'core' (default) or 'all'
--log-level LEVEL      Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
--test-pattern PATTERN Only run tests matching the pattern (e.g., 'test_message_send')
--verbose, -v          Enable verbose output
--report               Generate an HTML test report
--skip-agent-card      Skip fetching and validating the Agent Card, useful for SUTs without Agent Card support
```

### Examples

Run only core tests with verbose output:
```bash
./run_tck.py --sut-url http://localhost:9999 --verbose
```

Run all tests and generate an HTML report:
```bash
./run_tck.py --sut-url http://localhost:9999 --test-scope all --report
```

Run only streaming tests:
```bash
./run_tck.py --sut-url http://localhost:9999 --test-pattern "test_message_stream"
```

Run without fetching the Agent Card (for SUTs that don't expose one):
```bash
./run_tck.py --sut-url http://localhost:9999 --skip-agent-card
```

### Running Without the Runner Script

You can also run pytest directly:

```bash
pytest --sut-url http://localhost:9999 -m core
```

## Test Categories and Compliance Levels

The TCK uses a marker-based system to categorize tests by A2A specification compliance requirements:

### Mandatory Tests (MUST Requirements)
These tests **MUST** pass for A2A compliance. Any failure indicates the implementation is not A2A compliant.

- **`mandatory_jsonrpc`** - JSON-RPC 2.0 compliance tests
  - Parse error handling (-32700)
  - Invalid request validation (-32600)
  - Method not found handling (-32601)
  - Invalid parameters handling (-32602)

- **`mandatory_protocol`** - Core A2A protocol requirements
  - Agent Card availability and mandatory fields
  - Core message/send functionality with text
  - Task management (tasks/get, tasks/cancel)
  - Required parameter support (e.g., historyLength)
  - Error handling for non-existent resources

### Optional Tests (SHOULD/MAY Requirements)
These tests validate optional features and implementation quality.

- **`optional_capability`** - Capability-dependent tests
  - File/data modality support (if declared in Agent Card)
  - Streaming capabilities (if declared)
  - Push notifications (if declared)
  - Multiple message parts (if modalities supported)

- **`quality_basic`** - Implementation quality indicators
  - State transition handling
  - Idempotent operations
  - Edge case robustness

### Legacy Test Categories
For backward compatibility, the following legacy markers are still supported:

- **`core`** - Essential tests (mix of mandatory and core optional)
- **`all`** - All tests including advanced features

## Test Selection Examples

### Run Mandatory Tests Only (Compliance Validation)
```bash
# Run all mandatory tests (JSON-RPC + A2A protocol)
./run_tck.py --sut-url http://localhost:9999 -m "mandatory_jsonrpc or mandatory_protocol"

# Run only JSON-RPC compliance tests
./run_tck.py --sut-url http://localhost:9999 -m "mandatory_jsonrpc"

# Run only A2A protocol mandatory tests
./run_tck.py --sut-url http://localhost:9999 -m "mandatory_protocol"
```

### Run Capability-Based Tests
```bash
# Run tests for declared capabilities (file, data, streaming, etc.)
./run_tck.py --sut-url http://localhost:9999 -m "optional_capability"

# Run mandatory tests + capability tests (recommended for full validation)
./run_tck.py --sut-url http://localhost:9999 -m "mandatory_jsonrpc or mandatory_protocol or optional_capability"
```

### Run Quality Tests
```bash
# Run implementation quality tests
./run_tck.py --sut-url http://localhost:9999 -m "quality_basic"

# Run everything except quality tests (focus on compliance)
./run_tck.py --sut-url http://localhost:9999 -m "not quality_basic"
```

### Generate Compliance Reports
```bash
# Generate HTML report focusing on mandatory compliance
./run_tck.py --sut-url http://localhost:9999 -m "mandatory_jsonrpc or mandatory_protocol" --report

# Generate comprehensive report with all test categories
./run_tck.py --sut-url http://localhost:9999 --test-scope all --report
```

## Understanding Test Results

### Compliance Interpretation
- **Mandatory test failures** = Implementation is **NOT A2A compliant**
- **Optional test failures** = Implementation may be compliant but missing recommended features
- **Quality test failures** = Implementation works but may have robustness/performance issues

Test results are displayed in the console by default. Each test will be marked as:

- **PASSED**: The SUT behaved as expected
- **FAILED**: The SUT did not behave as expected (check if mandatory vs optional)
- **SKIPPED**: The test was skipped (e.g., capability not declared in Agent Card)
- **ERROR**: An unexpected error occurred during the test

If you generate an HTML report (using the `--report` option), a file named `tck_report.html` will be created with detailed test results including marker information.

**Note**: Pytest markers are used for test selection but do not appear in standard HTML reports by default. To see which tests belong to which categories, use the marker selection commands shown above.

## Current Test Suite Statistics

The TCK contains **75 total tests** categorized as follows:

- **24 mandatory tests** (MUST pass for A2A compliance)
  - 11 JSON-RPC 2.0 compliance tests (`mandatory_jsonrpc`)
  - 13 A2A protocol requirements (`mandatory_protocol`)
- **7 optional capability tests** (`optional_capability`)
- **2 quality tests** (`quality_basic`)
- **42 additional tests** (legacy categories and utilities)

### Verification Commands
```bash
# Count mandatory tests
pytest -m "mandatory_jsonrpc or mandatory_protocol" --collect-only -q | grep "collected"

# Count capability tests  
pytest -m "optional_capability" --collect-only -q | grep "collected"

# Count quality tests
pytest -m "quality_basic" --collect-only -q | grep "collected"
```

## Advanced Configuration

### Environment Variables

- `TCK_LOG_LEVEL`: Sets the logging level (equivalent to the `--log-level` option)

### Test Selection

You can combine markers with pytest's `-k` option for fine-grained control:

```bash
# Run mandatory tests for message/send only
./run_tck.py --sut-url http://localhost:9999 -m "mandatory_protocol" -k "message_send"

# Run all tests except streaming tests
./run_tck.py --sut-url http://localhost:9999 -k "not streaming"

# Run mandatory tests and generate detailed logs
./run_tck.py --sut-url http://localhost:9999 -m "mandatory_jsonrpc or mandatory_protocol" --log-level DEBUG
```

## Debugging

For detailed debugging information, increase the log level:

```bash
./run_tck.py --sut-url http://localhost:9999 --log-level DEBUG
```

This will show:
- Full JSON-RPC request and response bodies
- HTTP status codes
- Parsing and validation details

## Development

### Dependencies

The project uses the following dependencies:
- `pytest`: Testing framework
- `pytest-asyncio`: Async testing support for pytest
- `httpx`: HTTP client with async support
- `requests`: HTTP client for sync requests
- `responses`: Mocking library for HTTP responses
- `pytest-html`: HTML report generation
- `types-requests`: Type stubs for the requests library (for mypy type checking)

Development dependencies:
- `black`: Code formatter
- `isort`: Import sorter
- `mypy`: Type checking
- `flake8`: Linting

### Project Structure

The project is structured as follows:
- `tck/`: Core TCK modules
- `tests/`: Test modules
- `run_tck.py`: Script to run the TCK
- `requirements.txt`: Dependencies list
- `pyproject.toml`: Project configuration

### Type Checking

The project uses mypy for static type checking. You can run mypy with:

```bash
mypy .
```

## License

[Add your license information here]

## Contributing

[Add contribution guidelines if applicable]
