# ADR-001: Authentication Support for Testing Authenticated SUTs

## Status

**Accepted** - Implemented in `extended_security_tests` branch

**Date**: 2024-01-14

**Authors**: @jmesnil

## Context

### Problem Statement

The A2A TCK (Technology Compatibility Kit) previously had no mechanism to test Systems Under Test (SUTs) that require authentication. This created several critical issues:

1. **Testing Gap**: SUTs implementing authentication could not be tested by the TCK
2. **Specification Compliance**: A2A v1.0.0 specification requires authentication support, but the TCK couldn't validate it
3. **Test Failures**: All mandatory tests would fail for authenticated SUTs because credentials couldn't be provided
4. **Manual Workarounds**: Developers had to disable authentication or manually modify test code

### A2A Specification Context

Per A2A Specification v1.0.0 §4 (Authentication and Authorization):
- Authentication schemes MUST be declared in the Agent Card (`securitySchemes`)
- When declared, authentication MUST be enforced on all requests
- Multiple authentication methods are supported: Bearer, Basic, API Key, OAuth2, etc.
- The extended agent card endpoint requires authentication

### Requirements

1. **Automatic Header Injection**: Auth headers must be automatically added to all requests
2. **Multi-Transport Support**: Must work across JSON-RPC, gRPC, and REST transports
3. **Multiple Auth Methods**: Support common authentication schemes
4. **Zero Test Changes**: Existing tests must work without modification
5. **Optional**: Authentication should be opt-in via configuration
6. **Security**: Credentials must not be committed to version control

## Decision

### Implementation Overview

We implemented **automatic authentication header injection** via environment variable configuration, integrated at the transport client level.

### Architecture

```
┌─────────────────────────────────────────────────────┐
│ Environment Variables (.env file)                   │
│  - A2A_AUTH_TYPE                                    │
│  - A2A_AUTH_TOKEN                                   │
│  - A2A_AUTH_USERNAME / A2A_AUTH_PASSWORD            │
│  - A2A_AUTH_HEADER                                  │
│  - A2A_AUTH_HEADERS (JSON)                          │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│ tck/config.py                                       │
│  - get_auth_headers() → parses env vars             │
│  - set_auth_headers() → programmatic config         │
│  - Returns: Dict[str, str] of headers               │
└──────────────────┬──────────────────────────────────┘
                   │
    ┌──────────────┼──────────────┐
    │              │              │
    ▼              ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│ JSON-RPC │  │  gRPC    │  │  REST    │
│ Client   │  │ Client   │  │ Client   │
└──────────┘  └──────────┘  └──────────┘
│ Injects  │  │ Converts │  │ Injects  │
│ headers  │  │ to       │  │ headers  │
│ into     │  │ metadata │  │ into     │
│ HTTP     │  │ via      │  │ helper   │
│ requests │  │ helper   │  │ requests │
└──────────┘  └──────────┘  └──────────┘
```

### Key Components

#### 1. Configuration Layer (`tck/config.py`)

**New Functions**:
```python
def get_auth_headers() -> Dict[str, str]:
    """Parse environment variables and return auth headers"""

def set_auth_headers(headers: Optional[Dict[str, str]]):
    """Programmatically set auth headers"""
```

**Supported Authentication Types**:
- `bearer`: JWT/OAuth2 bearer tokens
- `basic`: HTTP Basic Authentication (username/password)
- `apikey`: API key in custom header
- `custom`: Custom header authentication
- JSON-based: Multiple headers via `A2A_AUTH_HEADERS`

#### 2. Transport Client Updates

**JSON-RPC Client** (`tck/transport/jsonrpc_client.py`):
```python
# In _make_jsonrpc_request() and _make_streaming_jsonrpc_request()
headers = {"Content-Type": "application/json"}
auth_headers = config.get_auth_headers()
if auth_headers:
    headers.update(auth_headers)
if extra_headers:
    headers.update(extra_headers)  # Can override auth
```

**gRPC Client** (`tck/transport/grpc_client.py`):
```python
def _prepare_metadata(self, extra_headers: Optional[Dict[str, str]] = None) -> list:
    """Convert auth headers to gRPC metadata"""
    metadata = []
    auth_headers = config.get_auth_headers()
    if auth_headers:
        for key, value in auth_headers.items():
            metadata.append((key.lower(), value))
    # Add extra_headers...
    return metadata
```

**REST Client** (`tck/transport/rest_client.py`):
```python
def _prepare_headers(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Merge default, auth, and extra headers"""
    headers = self.default_headers.copy()
    auth_headers = config.get_auth_headers()
    if auth_headers:
        headers.update(auth_headers)
    if extra_headers:
        headers.update(extra_headers)
    return headers
```

#### 3. Configuration Files

**`.env.example`**: Added comprehensive authentication examples (+54 lines)

**`docs/AUTHENTICATION_SETUP.md`**: Complete user guide (+282 lines)

### Design Principles

1. **Layer Separation**: Auth config in `tck/config.py`, injection in transport clients
2. **Override Capability**: `extra_headers` can override configured auth per-request
3. **Fail-Safe**: Missing config means no auth headers (backward compatible)
4. **Transport Agnostic**: Same config works for JSON-RPC, gRPC, and REST
5. **Security First**: `.env` already in `.gitignore`, credentials never committed

## Consequences

### Positive

✅ **Testing Enabled**: SUTs requiring authentication can now be tested
✅ **Zero Test Changes**: Existing tests work without modification
✅ **Multi-Transport**: Works seamlessly across all transport types
✅ **Flexible**: Supports 5 authentication methods + custom JSON headers
✅ **Secure**: Credentials managed via `.env` file (git-ignored)
✅ **Developer Friendly**: Simple configuration, comprehensive documentation
✅ **Specification Aligned**: Enables testing A2A v1.0.0 auth requirements
✅ **Backward Compatible**: Auth is optional, doesn't affect non-authenticated SUTs

### Negative

⚠️ **Configuration Overhead**: Users must configure `.env` for authenticated SUTs
⚠️ **Environment Dependency**: Relies on environment variables being loaded
⚠️ **Static Credentials**: Doesn't support dynamic token refresh (acceptable for testing)
⚠️ **Test Isolation**: Auth headers apply to ALL requests (can override per-test if needed)

### Neutral

ℹ️ **Documentation**: Added new user-facing documentation requirements
ℹ️ **Maintenance**: New code path to maintain across transport clients
ℹ️ **CI/CD**: Requires environment variable configuration in CI pipelines

## Alternatives Considered

### Alternative 1: Per-Test Authentication
**Approach**: Pass credentials to each test function
**Rejected Because**:
- Requires modifying every test
- Violates DRY principle
- Difficult to maintain

### Alternative 2: CLI Arguments
**Approach**: `--auth-token`, `--auth-type` command-line flags
**Rejected Because**:
- Credentials visible in process list (security risk)
- Less flexible for complex auth scenarios
- Harder to use in CI/CD

### Alternative 3: Config File (YAML/JSON)
**Approach**: Dedicated auth config file
**Rejected Because**:
- Additional file management complexity
- `.env` is standard practice for credentials
- Would require custom parsing logic

### Alternative 4: Programmatic Only
**Approach**: Only `set_auth_headers()`, no environment variables
**Rejected Because**:
- Requires code changes for each SUT
- Less accessible to end users
- Doesn't work well with `run_tck.py` script

## Usage Examples

### Basic Bearer Token
```bash
# .env
A2A_AUTH_TYPE=bearer
A2A_AUTH_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Run tests
./run_tck.py --sut-url https://my-sut.com --category all
```

### API Key
```bash
# .env
A2A_AUTH_TYPE=apikey
A2A_AUTH_TOKEN=sk_test_1234567890
A2A_AUTH_HEADER=X-API-Key
```

### HTTP Basic Auth
```bash
# .env
A2A_AUTH_TYPE=basic
A2A_AUTH_USERNAME=admin
A2A_AUTH_PASSWORD=secretpass
```

## References

- [A2A Specification v1.0.0 §4 - Authentication](https://google.github.io/A2A/specification/#authentication)
- [AUTHENTICATION_SETUP.md](../AUTHENTICATION_SETUP.md) - User documentation
- Issue: Testing authenticated SUTs
- Related ADRs: [ADR-002: Extended Agent Card Separation](ADR-002-extended-agent-card-separation.md)

## Notes

### Security Considerations

- `.env` file is git-ignored by default
- Credentials should be test/development only
- CI/CD should use environment variables, not `.env` files
- No credentials are logged or exposed in test output

### Future Enhancements

Potential future improvements:
- OAuth2 token refresh support
- Certificate-based authentication (mTLS)
- Per-transport authentication configuration

## Decision Outcome

**Status**: ✅ Accepted and Implemented

This ADR documents the accepted approach for authentication support in the A2A TCK. The implementation successfully enables testing of authenticated SUTs while maintaining backward compatibility and security best practices.
