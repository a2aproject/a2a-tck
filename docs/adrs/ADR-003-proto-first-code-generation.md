# ADR-003: Proto-First Code Generation with Buf

## Status

**Accepted**

**Date**: 2026-01-20

**Authors**: @jmesnil

## Context

### Problem Statement

In the `spec_1.0` branch, the A2A TCK (Technology Compatibility Kit) was tracking the specification based on the JSON schema stored in the A2A Git repository.
It also maintained Python gRPC stubs that were generated using traditional protoc/grpcio-tools workflows. This created several issues:

1. **Version Skew**: Python stubs could drift from the official a2a.proto specification
2. **Manual Maintenance**: Regenerating stubs required complex Python dependencies and tooling
3. **Source of Truth Ambiguity**: Unclear whether a2a.proto or the JSON schema was authoritative
4. **Dependency Management**: Required grpcio-tools, googleapis-common-protos, and complex Python environment setup
5. **Build Complexity**: The generation script was ~186 lines with extensive dependency checking and error handling

### A2A Specification Context

Per A2A Specification structure:
- The official A2A protocol is defined in `specification/grpc/a2a.proto`
- The proto file is the canonical source of truth for the protocol. The JSON schema is now derived from the a2a.proto and is no longer used by the TCK
- All language bindings should be generated from this proto file
- The TCK should validate against the official specification, not a derivative

### Requirements

1. **Proto as Source of Truth**: a2a.proto must be the single source of truth. It is no longer the json schema.
2. **Automated Generation**: Code generation should be simple and reproducible
3. **Version Tracking**: Track which version of the spec is being used
4. **Minimal Dependencies**: Reduce Python-specific tooling requirements
5. **Modern Tooling**: Use contemporary protocol buffer tooling
6. **Build Simplicity**: Simplify the generation process

## Decision

### Implementation Overview

We implemented a **proto-first architecture** where `a2a.proto` is downloaded from the official A2A repository and used as the single source of truth, with [buf](https://buf.build) handling code generation.

### Architecture

```
┌─────────────────────────────────────────────────────┐
│ GitHub: a2aproject/A2A Repository                   │
│  - specification/grpc/a2a.proto, buf.yaml, buf.lock │
│  - docs/specification.md                            │
└──────────────────┬──────────────────────────────────┘
                   │
                   │ update_spec.sh (download)
                   ▼
┌─────────────────────────────────────────────────────┐
│ current_spec/ (local cache, stored in Git)          │
│  - a2a.proto, buf.yaml, buf.lock                    │
│  - specification.md                                 │
│  - info.json (metadata: org, branch, timestamp)     │
└──────────────────┬──────────────────────────────────┘
                   │
                   │ scripts/generate_grpc_stubs.sh
                   │ (uses bin/buf)
                   ▼
┌─────────────────────────────────────────────────────┐
│ tck/grpc_stubs/ (generated code, stored in Git)     │
│  - a2a_pb2.py (Protocol Buffer messages)            │
│  - a2a_pb2_grpc.py (gRPC service stubs)             │
└─────────────────────────────────────────────────────┘
```

### Key Components

#### 1. Specification Download (`update_spec.sh`)

**Purpose**: Download official specification files from GitHub

**Features**:
- Downloads from configurable GitHub org and branch
- Default: `a2aproject/A2A` repository, `main` branch
- Saves to `current_spec/` directory
- Creates `info.json` with download metadata

**Usage**:
```bash
./update_spec.sh                           # Default: a2aproject/main
./update_spec.sh --org myorg               # Custom organization
./update_spec.sh --branch feature-branch   # Custom branch
```

**Metadata Tracking** (`info.json`):
```json
{
  "downloadTime": "2026-01-20T14:30:45Z",
  "organization": "a2aproject",
  "branch": "main",
  "repository": "A2A",
  "files": ["a2a.proto", "specification.md"]
}
```

#### 2. Buf Binary Management (`install_buf.sh`)

**Purpose**: Install buf CLI tool locally

**Features**:
- Downloads platform-specific buf binary
- Installs to `bin/buf` (project-local)
- No global installation required
- Supports macOS (Intel/ARM) and Linux

#### 3. Code Generation (`scripts/generate_grpc_stubs.sh`)

**Old Approach** (spec_1.0 branch):
- ~186 lines of bash
- Python dependency checking (grpcio-tools, googleapis-common-protos)
- Complex proto path resolution
- Virtual environment management
- Manual protoc invocation

**New Approach** (this branch):
- ~77 lines of bash (57% reduction)
- Single dependency: `bin/buf`
- No Python tooling required
- Simple configuration via `buf.gen.yaml`
- Automatic backup of existing stubs

**buf.gen.yaml Configuration**:
```yaml
version: v2
plugins:
  - remote: buf.build/protocolbuffers/python
    out: tck/grpc_stubs
  - remote: buf.build/grpc/python
    out: tck/grpc_stubs
```

This file is not downloaded from the A2A repository but is specific to the a2a-tck repository

#### 4. Workflow

```bash
# Step 1: Install buf (once)
./install_buf.sh

# Step 2: Download latest spec (downloaded files are stored in this Git repository)
./update_spec.sh

# Step 3: Generate Python stubs (required only if working with updated spec)
./scripts/generate_grpc_stubs.sh
```

### Design Principles

1. **Single Source of Truth**: a2a.proto is the authoritative definition
2. **Reproducibility**: Same inputs always produce same outputs
3. **Traceability**: `info.json` tracks exactly what was downloaded and when
4. **Simplicity**: Minimal dependencies, clear workflow
5. **Flexibility**: Support testing against different branches/forks
6. **Automation**: Simple scripts that can run in CI/CD

## Consequences

### Positive

✅ **Clarity**: a2a.proto is unambiguously the source of truth
✅ **Simplified Build**: 57% reduction in generation script complexity
✅ **Reduced Dependencies**: No Python tooling required for generation
✅ **Version Control**: Track exact spec version via `info.json`
✅ **Modern Tooling**: Buf provides better error messages and validation
✅ **Reproducible**: Same spec version always generates same code
✅ **Flexible Testing**: Easy to test against different spec branches/forks
✅ **CI/CD Friendly**: Simple, scriptable workflow

### Negative

⚠️ **New Dependency**: Requires buf binary (but project-local, no global install)
⚠️ **Breaking Change**: Incompatible with spec_1.0 branch workflow

### Neutral

ℹ️ **Learning Curve**: Team must learn buf (but simpler than protoc workflows)
ℹ️ **Cache Management**: Developers must remember to update spec when needed

## Alternatives Considered

### Alternative 1: Continue with grpcio-tools

**Approach**: Keep using `python -m grpc_tools.protoc`

**Rejected Because**:
- Complex dependency management
- Python-specific tooling for language-agnostic task
- Poor error messages compared to buf
- Difficult to maintain across different environments

### Alternative 4: Git Submodule

**Approach**: Add A2A repository as git submodule

**Rejected Because**:
- Submodules are complex to manage
- Forces pinning to specific commits
- Difficult for new contributors
- Can't easily test against different orgs/forks

## Usage Examples

### Initial Setup

```bash
# Install buf
./install_buf.sh

# Download spec from default (a2aproject/main)
./update_spec.sh

# Generate Python stubs
./scripts/generate_grpc_stubs.sh
```

### Testing Against Different Spec Version

```bash
# Test against development branch
./update_spec.sh --branch develop
./scripts/generate_grpc_stubs.sh

# Test against fork
./update_spec.sh --org mycompany --branch custom-feature
./scripts/generate_grpc_stubs.sh
```

### Verify Spec Version

```bash
# Check which version is currently downloaded
cat current_spec/info.json
```

## References

- [Buf Documentation](https://buf.build/docs)
- [A2A Specification Repository](https://github.com/a2aproject/A2A)
- [Protocol Buffers Best Practices](https://protobuf.dev/programming-guides/dos-donts/)
- Related Scripts:
  - `scripts/update_spec.sh` - Specification download
  - `scripts/install_buf.sh` - Buf installation
  - `scripts/generate_grpc_stubs.sh` - Code generation
  - `current_spec/buf.gen.yaml` - Buf configuration

## Notes

### File Tracking

The `current_spec/info.json` file provides essential traceability:
- **When**: Timestamp of download
- **Where**: GitHub organization and repository
- **What**: Branch and list of downloaded files

This enables:
- Debugging version-specific issues
- Reproducing exact test conditions
- Auditing which spec version was tested

### Backward Compatibility

This change is **not backward compatible** with the spec_1.0 branch workflow. Migration requires:

1. Install buf: `./install_buf.sh`
2. Download spec: `./update_spec.sh`
3. Remove old Python tooling dependencies (if desired)
4. Update CI/CD scripts

### Future Enhancements

Potential improvements:
- Automatic spec update checking (compare remote vs local)
- Support for multiple spec versions simultaneously
- Buf schema validation and breaking change detection
- Buf linting for custom proto definitions (if TCK adds extensions)

## Decision Outcome

**Status**: ✅ Accepted and Implemented

This ADR documents the architectural shift to a proto-first approach with buf for code generation. The implementation provides a clearer source of truth, simpler tooling, and better traceability while reducing complexity and dependencies.
Any reference to the A2A JSON schema have been removed.