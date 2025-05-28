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

## Test Categories

The TCK includes the following test categories:

1. **JSON-RPC Compliance** - Tests basic JSON-RPC 2.0 compliance (request/response structure, error codes).
2. **Core A2A Methods** - Tests for essential A2A methods:
   - `message/send` - Send messages to create or continue tasks
   - `tasks/get` - Retrieve task state and history
   - `tasks/cancel` - Cancel a task
   - `tasks/pushNotificationConfig/set` and `tasks/pushNotificationConfig/get` - Manage push notifications
3. **Streaming Methods** - Tests for streaming capabilities:
   - `message/stream` - Send messages with streaming responses
   - `tasks/resubscribe` - Resubscribe to an active task's event stream

## Understanding Test Results

Test results are displayed in the console by default. Each test will be marked as:

- **PASSED**: The SUT behaved as expected
- **FAILED**: The SUT did not behave as expected
- **SKIPPED**: The test was skipped (e.g., if the SUT doesn't support a feature)
- **ERROR**: An unexpected error occurred during the test

If you generate an HTML report (using the `--report` option), a file named `tck_report.html` will be created with detailed test results.

## Advanced Configuration

### Environment Variables

- `TCK_LOG_LEVEL`: Sets the logging level (equivalent to the `--log-level` option)

### Test Selection

You can select specific test groups or patterns using pytest's `-k` option:

```bash
# Run only message/send tests
./run_tck.py --sut-url http://localhost:9999 --test-pattern "test_message_send"

# Run all tests except streaming tests
./run_tck.py --sut-url http://localhost:9999 --test-pattern "not test_streaming"
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
