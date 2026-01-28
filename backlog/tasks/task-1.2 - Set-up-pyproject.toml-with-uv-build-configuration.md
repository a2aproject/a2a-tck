---
id: TASK-1.2
title: Set up pyproject.toml with uv build configuration
status: To Do
assignee: []
created_date: '2026-01-28 09:07'
updated_date: '2026-01-28 09:21'
labels:
  - phase-1
  - foundation
  - infrastructure
dependencies:
  - TASK-1.1
parent_task_id: TASK-1
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create the pyproject.toml file with all required dependencies and build configuration for A2A TCK v1.0, using `uv` as the package manager.

**Reference**: PRD Section 6 Task 1.2

**Required dependencies**:
- pytest (test framework)
- httpx (HTTP client for JSON-RPC and REST)
- grpcio (gRPC client)
- grpcio-tools (proto compilation)
- google-protobuf (proto runtime)
- jsonschema (JSON Schema validation, Draft 2020-12 support)

**Dev dependencies**:
- ruff (linting and formatting)
- mypy (type checking)

**Configuration**:
- Package name: a2a-tck
- Python version: >=3.11
- Entry point: run_tck.py console script
- Line length: 130 (per existing project style)
- Package manager: uv (generates uv.lock for reproducible builds)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 pyproject.toml file exists with all required dependencies
- [ ] #2 uv sync succeeds without errors
- [ ] #3 uv sync --dev installs dev dependencies
- [ ] #4 uv.lock file is generated and committed
- [ ] #5 ruff check . runs without import errors
- [ ] #6 pytest --version runs successfully
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Implementation Plan

### Steps
1. Create `pyproject.toml` with uv-compatible configuration:

```toml
[project]
name = "a2a-tck"
version = "1.0.0"
description = "A2A Protocol Technology Compatibility Kit"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "pytest>=8.0",
    "httpx>=0.27",
    "grpcio>=1.60",
    "grpcio-tools>=1.60",
    "protobuf>=4.25",
    "jsonschema>=4.21",
]

[project.optional-dependencies]
dev = [
    "ruff>=0.3",
    "mypy>=1.8",
]

[project.scripts]
run-tck = "run_tck:main"

[tool.ruff]
line-length = 130

[tool.ruff.lint]
select = ["E", "F", "I", "W"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

2. Initialize uv and generate lock file:
```bash
uv sync
uv sync --dev
```

3. Verify installation:
```bash
uv run pytest --version
uv run ruff --version
```

### Verification
- `uv.lock` file exists
- `uv sync` completes without errors
- `uv run pytest --collect-only` runs (even with no tests)
<!-- SECTION:PLAN:END -->
