# Authentication Setup for A2A TCK

This guide explains how to configure authentication when testing A2A implementations (SUTs) that require authentication.

## Overview

The A2A TCK now supports automatic authentication header injection for all requests. This allows you to test SUTs that require authentication without modifying the test code.

## Quick Start

### 1. Copy the environment file
```bash
cp .env.example .env
```

### 2. Configure authentication in `.env`

Choose one of the authentication methods below and uncomment the relevant lines in your `.env` file.

## Authentication Methods

### Bearer Token (JWT/OAuth2)

**Use case**: Your SUT requires a JWT or OAuth2 bearer token in the Authorization header.

```bash
# .env
A2A_AUTH_TYPE=bearer
A2A_AUTH_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**What it does**: Adds header `Authorization: Bearer <token>` to all requests.

### Basic Authentication

**Use case**: Your SUT requires HTTP Basic Authentication (username and password).

```bash
# .env
A2A_AUTH_TYPE=basic
A2A_AUTH_USERNAME=admin
A2A_AUTH_PASSWORD=secretpassword
```

**What it does**: Encodes credentials and adds header `Authorization: Basic <base64-encoded-credentials>` to all requests.

### API Key

**Use case**: Your SUT requires an API key in a custom header.

```bash
# .env
A2A_AUTH_TYPE=apikey
A2A_AUTH_TOKEN=sk_test_1234567890abcdef
A2A_AUTH_HEADER=X-API-Key  # Optional: defaults to X-API-Key
```

**What it does**: Adds header `X-API-Key: <token>` (or your custom header name) to all requests.

### Custom Header

**Use case**: Your SUT requires authentication in a custom header format.

```bash
# .env
A2A_AUTH_TYPE=custom
A2A_AUTH_TOKEN=your-custom-token
A2A_AUTH_HEADER=X-Custom-Auth
```

**What it does**: Adds header `X-Custom-Auth: your-custom-token` to all requests.

### Multiple Headers (Advanced)

**Use case**: Your SUT requires multiple authentication headers or complex authentication.

```bash
# .env
A2A_AUTH_HEADERS={"Authorization":"Bearer token123","X-API-Key":"key456","X-Request-ID":"test-001"}
```

**What it does**: Adds all specified headers to all requests. Must be valid JSON.

## Running Tests with Authentication

Once configured, run tests normally:

```bash
# Run all tests with authentication
./run_tck.py --sut-url https://your-sut.example.com --category all

# Run mandatory tests only
./run_tck.py --sut-url https://your-sut.example.com --category mandatory
```

The TCK will automatically inject authentication headers into every request.

## Environment Variable Reference

| Variable | Purpose | Example |
|----------|---------|---------|
| `A2A_AUTH_TYPE` | Authentication method | `bearer`, `basic`, `apikey`, `custom` |
| `A2A_AUTH_TOKEN` | Token/API key value | `eyJhbG...` or `sk_test_123` |
| `A2A_AUTH_HEADER` | Custom header name | `X-API-Key`, `X-Custom-Auth` |
| `A2A_AUTH_USERNAME` | Basic auth username | `admin` |
| `A2A_AUTH_PASSWORD` | Basic auth password | `secretpass` |
| `A2A_AUTH_HEADERS` | Multiple headers (JSON) | `{"Header1":"value1"}` |

## Per-Request Authentication Override

If you need to override authentication for specific tests, you can use the `extra_headers` parameter:

```python
# In test code
client.send_message(
    message=msg,
    extra_headers={"Authorization": "Bearer different-token"}
)
```

Extra headers will **override** the configured authentication headers for that specific request.

## Testing Authentication Enforcement

The TCK includes tests to verify authentication enforcement:

### For SUTs without Authentication

- **Don't** set any `A2A_AUTH_*` variables
- **Don't** declare authentication in your Agent Card
- Authentication tests will be skipped

### For SUTs with Authentication

1. **Declare authentication** in your Agent Card (`securitySchemes`)
2. **Configure auth** credentials in `.env` (for successful requests)
3. **Run tests** - The TCK will:
   - Test that missing auth is **rejected** (HTTP 401/403)
   - Test that invalid auth is **rejected** (HTTP 401/403)
   - Test that valid auth is **accepted** (using your configured credentials)
   - Test that auth scheme declarations are properly structured

## Transport-Specific Behavior

### JSON-RPC Transport
- Authentication headers are added to HTTP POST requests
- Works with both regular and streaming methods

### gRPC Transport
- Authentication headers are converted to gRPC metadata
- Headers are lowercased per gRPC specification
- Works with all gRPC methods

### REST Transport
- Authentication headers are added to all HTTP requests
- Works with GET, POST, and streaming methods

## Troubleshooting

### Tests fail with 401/403 errors

**Cause**: Authentication credentials are incorrect or not being sent.

**Solution**:
1. Verify your `.env` file has the correct credentials
2. Check that the `.env` file is in the TCK root directory
3. Ensure the `.env` file is loaded (you should see auth headers in verbose output)

```bash
# Run with verbose logging to see headers
./run_tck.py --sut-url https://your-sut.example.com --category mandatory --verbose-log
```

### Authentication headers not being sent

**Cause**: `.env` file not loaded or malformed.

**Solution**:
1. Check `.env` file exists: `ls -la .env`
2. Verify format (no extra spaces, valid JSON for `A2A_AUTH_HEADERS`)
3. Restart the test run after modifying `.env`

### "Failed to parse A2A_AUTH_HEADERS" warning

**Cause**: `A2A_AUTH_HEADERS` contains invalid JSON.

**Solution**:
- Ensure JSON is valid: `{"key":"value"}` not `{key:value}`
- Use double quotes, not single quotes
- Escape special characters if needed

### SUT accepts requests without authentication

**Cause**: SUT not enforcing authentication despite declaring it.

**Solution**: This is a **SUT bug**. Per A2A specification:
- If `securitySchemes` are declared, authentication **MUST** be enforced
- Fix your SUT to return HTTP 401/403 for unauthenticated requests

## Examples

### Example 1: Testing a SUT with JWT Authentication

```bash
# .env
A2A_AUTH_TYPE=bearer
A2A_AUTH_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0Y2stdGVzdCJ9.abc123
```

```bash
# Run tests
./run_tck.py --sut-url https://my-sut.example.com --category all
```

### Example 2: Testing a SUT with API Key

```bash
# .env
A2A_AUTH_TYPE=apikey
A2A_AUTH_TOKEN=sk_live_1234567890abcdef
A2A_AUTH_HEADER=X-API-Key
```

```bash
# Run tests
./run_tck.py --sut-url https://api.example.com --category mandatory
```

### Example 3: Testing a SUT with Basic Auth

```bash
# .env
A2A_AUTH_TYPE=basic
A2A_AUTH_USERNAME=testuser
A2A_AUTH_PASSWORD=testpass123
```

```bash
# Run tests
./run_tck.py --sut-url http://localhost:9999 --category all
```

### Example 4: Testing with Multiple Headers

```bash
# .env
A2A_AUTH_HEADERS={"Authorization":"Bearer token123","X-Tenant-ID":"tenant-001","X-Request-ID":"tck-test"}
```

```bash
# Run tests
./run_tck.py --sut-url https://multi-tenant.example.com --category all
```

## Security Best Practices

### DO NOT commit credentials

❌ **Never commit `.env` with real credentials to version control**

✅ **Best practices**:
- Keep `.env` in `.gitignore` (already configured)
- Use test/development credentials only
- Rotate credentials regularly
- Use environment variables in CI/CD instead of `.env` files

### Use environment variables in CI/CD

For CI/CD pipelines, set environment variables directly instead of using `.env`:

```bash
# GitHub Actions example
export A2A_AUTH_TYPE=bearer
export A2A_AUTH_TOKEN=${{ secrets.TCK_AUTH_TOKEN }}
./run_tck.py --sut-url ${{ secrets.SUT_URL }} --category all
```

## See Also

- [SUT Requirements](SUT_REQUIREMENTS.md) - General requirements for testing
- [A2A Specification §4](https://google.github.io/A2A/specification/#authentication) - Authentication specification
- Agent Card `securitySchemes` documentation
