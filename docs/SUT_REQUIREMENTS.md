# SUT Requirements for A2A TCK

This document outlines **additional requirements** that a System Under Test (SUT) must implement to properly work with the A2A Technology Compatibility Kit (TCK). These are **testing-specific requirements** beyond the core A2A specification.

## ⚠️ Critical: Streaming Test Duration Requirement

**For testing purposes only**, your SUT must implement the following behavior:

When your SUT receives a `message/stream` request with a `messageId` that starts with `"test-resubscribe-message-id"`, the resulting task MUST remain active (not complete) for **at least `2 × TCK_STREAMING_TIMEOUT`** seconds.

### Configuration Details
- **Default**: `TCK_STREAMING_TIMEOUT = 2.0` seconds → Task must run for ≥ 4.0 seconds
- **Custom**: If `TCK_STREAMING_TIMEOUT = 5.0` → Task must run for ≥ 10.0 seconds
- **Detection**: Check if `params.message.messageId.startsWith("test-resubscribe-message-id")`

### Why This Is Required
- The TCK tests `tasks/resubscribe` functionality by creating a task, then resubscribing to it
- If tasks complete too quickly, the resubscribe test cannot validate proper streaming behavior
- This ensures sufficient time for the test to establish the initial stream, extract the task ID, and then test resubscription

## ⚙️ TCK Timeout Configuration

### Environment Variable Support (Optional)

If your SUT supports environment variables, it should respect `TCK_STREAMING_TIMEOUT` for test compatibility. This is **optional** but recommended for easier testing with different timeout values.

### Timeout Behavior in TCK

The TCK uses the `TCK_STREAMING_TIMEOUT` environment variable to configure all streaming-related timeouts:

- **Short timeout**: `TCK_STREAMING_TIMEOUT * 0.5` - Used for basic streaming operations
- **Normal timeout**: `TCK_STREAMING_TIMEOUT * 1.0` - Used for standard SSE client operations  
- **Async timeout**: `TCK_STREAMING_TIMEOUT * 1.0` - Used for `asyncio.wait_for` operations

### Configuration Examples

**Using .env file (recommended)**:
```bash
# Copy the TCK example file
cp .env.example .env

# Edit the file to customize settings
echo "TCK_STREAMING_TIMEOUT=5.0" > .env

# Run tests with custom timeout
./run_tck.py --sut-url http://your-sut:9999 --category capabilities
```

**Set directly for single run**:
```bash
TCK_STREAMING_TIMEOUT=1.0 ./run_tck.py --sut-url http://your-sut:9999 --category capabilities
```

**Debug with very slow timeouts**:
```bash
TCK_STREAMING_TIMEOUT=30.0 ./run_tck.py --sut-url http://your-sut:9999 --category capabilities --verbose
```

### When to Adjust Timeouts

- **Decrease (`1.0`)**: Fast CI/CD pipelines, local development
- **Increase (`5.0+`)**: Slow networks, debugging, resource-constrained environments
- **Debug (`10.0+`)**: Detailed troubleshooting, step-through debugging

## Message ID Patterns

The TCK uses specific message ID patterns for testing. **Only implement special behavior for the patterns listed**:

| Pattern | Required Behavior |
|---------|-------------------|
| `test-resubscribe-message-id-*` | Task must run ≥ 2×`TCK_STREAMING_TIMEOUT` seconds |
| All other `test-*` patterns | Normal task processing (no special behavior) |

## Testing Your Implementation

```bash
# Test streaming with custom timeout
echo "TCK_STREAMING_TIMEOUT=1.0" > .env
./run_tck.py --sut-url http://your-sut:9999 --category all
```

That's it! Everything else follows the standard A2A specification. 