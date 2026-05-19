---
id: TASK-1.2
title: Set up pyproject.toml with uv build configuration
status: Done
assignee: []
created_date: '2026-01-28 09:07'
updated_date: '2026-02-12 13:19'
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
- google-protobuf (proto runtime)
- jsonschema (JSON Schema validation, Draft 2020-12 support)

**Proto compilation**:
- use bufbuild/buf to generate Python code from protobuf

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
- [x] #1 pyproject.toml file exists with all required dependencies
- [x] #2 uv sync succeeds without errors
- [x] #3 uv sync --dev installs dev dependencies
- [x] #4 uv.lock file is generated and committed
- [x] #5 ruff check . runs without import errors
- [x] #6 pytest --version runs successfully
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

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
## Summary

Updated pyproject.toml with uv-compatible build configuration for A2A TCK v1.0.

### Changes Made

**pyproject.toml updates:**
- Build system: Changed from setuptools to hatchling
- Version: Updated to 1.0.0
- Python: Required >=3.11
- Dependencies: pytest>=8.0, pytest-asyncio>=0.23, httpx>=0.27, grpcio>=1.60, protobuf>=4.25, jsonschema>=4.21
- Dev dependencies: ruff>=0.3, mypy>=1.8
- Tool config: ruff line-length=130, updated pytest markers

**Dependencies installed:**
- Core: 27 packages resolved
- Dev: ruff 0.15.0, mypy 1.19.1

### Verification
- `uv sync` succeeds
- `uv sync --extra dev` installs dev dependencies  
- `uv.lock` generated (84KB)
- `uv run pytest --version` returns pytest 9.0.2
- `uv run ruff check .` runs successfully
<!-- SECTION:FINAL_SUMMARY:END -->
