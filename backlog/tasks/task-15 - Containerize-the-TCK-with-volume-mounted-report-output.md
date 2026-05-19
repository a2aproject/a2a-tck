---
id: TASK-15
title: Containerize the TCK with volume-mounted report output
status: To Do
assignee: []
created_date: '2026-03-12 09:53'
updated_date: '2026-03-12 15:22'
labels:
  - container
  - infrastructure
dependencies: []
references:
  - run_tck.py
  - pyproject.toml
  - Makefile
  - tests/compatibility/conftest.py
  - .env
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create a container image that runs the A2A TCK against a System Under Test (SUT) and outputs generated reports to a mounted volume.

## Files to Create

### 1. `Containerfile`
- Base image: `python:3.11-slim`
- Install `uv` via `COPY --from=ghcr.io/astral-sh/uv:latest`
- Layer caching: copy `pyproject.toml` + `uv.lock` first, run `uv sync --frozen --no-dev`, then copy source
- Entrypoint: `docker-entrypoint.sh`
- No EXPOSE — container exits after TCK run, no web server

### 2. `docker-entrypoint.sh`
- SUT URL passed as a positional argument (`$1`), not an env var
- Optional configuration via env vars: `TCK_TRANSPORT`, `TCK_LEVEL`, `TCK_VERBOSE`, `TCK_STREAMING_TIMEOUT`, `A2A_AUTH_*`
- Runs `uv run ./run_tck.py --sut-host "$1" [options]`
- Exits with the TCK exit code (useful for CI pass/fail detection)
- Helpful error message if SUT URL is missing, including `host.docker.internal` guidance

### 3. `run_containerized_tck.sh`
- Wrapper script that simplifies `docker run` invocation
- Handles volume mount (`-v ./reports:/app/reports`) automatically
- Forwards SUT URL as argument and optional flags (--transport, --level, etc.)
- Usage: `./run_containerized_tck.sh http://host.docker.internal:9999`
- With options: `./run_containerized_tck.sh --transport grpc --level must http://host.docker.internal:9999`

### 4. `.dockerignore`
- Exclude: `.git`, `.venv`, `__pycache__`, `*.pyc`, `reports/`, `.env`, `.claude/`, `.agents/`, `backlog/`, `docs/`, `PRD/`, `.ruff_cache`, `.mypy_cache`, `.pytest_cache`, `bin/`, `a2a-python`, `a2a-java-sdk`
- Must NOT exclude: `specification/` (needed at runtime for schema validation), `tests/` (pytest test discovery)

### 5. Update `Makefile`
- Add `docker-build` target: builds the image as `a2a-tck`
- Add `docker-run` target: runs with volume mount, requires `SUT_HOST` make variable

## Design Decisions
- **No web server**: reports are accessed via volume mount, container exits when done
- **SUT URL as argument**: required parameter is a CLI argument, optional config as env vars
- **Exit code passthrough**: container exits with TCK's exit code for CI integration
- **`Containerfile`**: OCI-standard name, works with both Docker and Podman

## Localhost SUT Access
When SUT runs on the host:
- macOS/Windows: use `host.docker.internal` (automatic with Docker Desktop)
- Linux: use `--network host` or `--add-host=host.docker.internal:host-gateway`

## Potential Issues
- `grpcio` needs binary wheels — should work on `python:3.11-slim` for x86_64/aarch64, but may need `gcc` if building from source
- Relative paths in `run_tck.py` (e.g. `Path("tests/compatibility")`) require WORKDIR to be `/app`
- `uv.lock` must not be in `.dockerignore` since `uv sync --frozen` requires it
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Container builds successfully with `docker build -f Containerfile -t a2a-tck .`
- [ ] #2 TCK runs against a SUT: `docker run --rm -v ./reports:/app/reports a2a-tck http://host.docker.internal:9999`
- [ ] #3 Reports (compatibility.html, compatibility.json, tck_report.html, junitreport.xml) appear in the mounted ./reports/ directory
- [ ] #4 Container exits with TCK exit code (0 for pass, non-zero for failures)
- [ ] #5 run_containerized_tck.sh wrapper script works with positional SUT URL and optional flags
- [ ] #6 Env vars (TCK_TRANSPORT, TCK_LEVEL, TCK_VERBOSE, A2A_AUTH_*) are forwarded correctly
- [ ] #7 Missing SUT URL argument produces a helpful error message
- [ ] #8 Image size is reasonable (under 500MB)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Multi-arch (linux/amd64, linux/arm64) to be handled at CI/push time, not in local build targets. Colima already supports both architectures via QEMU emulation.

Fixed bash 3.2 compatibility issue: negative array indices (`${ARGS[-1]}`) not supported on macOS default bash. Used `LAST_INDEX=$(( ${#ARGS[@]} - 1 ))` instead.

Audit (2026-04-20): Reset all acceptance criteria to unchecked — no container files (Containerfile, docker-entrypoint.sh, run_containerized_tck.sh, .dockerignore) exist in the repo. Previous checks were erroneous.
<!-- SECTION:NOTES:END -->
