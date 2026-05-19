#!/bin/bash
# Test suite for a2a-client scripts.
#
# Tests use a mock curl that captures requests instead of making real HTTP calls.
# Run from anywhere: the script finds its own location.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
MOCK_DIR="$(mktemp -d)"
PASS=0
FAIL=0

cleanup() {
  rm -rf "$MOCK_DIR"
}
trap cleanup EXIT

# Create a mock curl that logs its arguments and outputs a canned response
setup_mock_curl() {
  # Write the canned response to a file (avoids heredoc quoting issues)
  printf '%s' "$1" > "$MOCK_DIR/curl_response"
  cat > "$MOCK_DIR/curl" <<MOCK
#!/bin/bash
# Save all arguments for inspection
printf '%s\n' "\$@" > "$MOCK_DIR/curl_args"
# Save stdin if piped
if [ ! -t 0 ]; then
  cat > "$MOCK_DIR/curl_stdin"
fi
cat "$MOCK_DIR/curl_response"
MOCK
  chmod +x "$MOCK_DIR/curl"
  rm -f "$MOCK_DIR/curl_args" "$MOCK_DIR/curl_stdin"
}

# Create a mock uuidgen that returns a predictable value
setup_mock_uuidgen() {
  cat > "$MOCK_DIR/uuidgen" <<'MOCK'
#!/bin/bash
echo "00000000-0000-0000-0000-000000000001"
MOCK
  chmod +x "$MOCK_DIR/uuidgen"
}

# Get the request body sent to curl (from stdin or -d argument)
get_request_body() {
  if [ -f "$MOCK_DIR/curl_stdin" ]; then
    cat "$MOCK_DIR/curl_stdin"
  elif [ -f "$MOCK_DIR/curl_args" ]; then
    # Find -d argument
    local next=false
    while IFS= read -r arg; do
      if [ "$next" = true ]; then
        echo "$arg"
        return
      fi
      if [ "$arg" = "-d" ]; then
        next=true
      fi
    done < "$MOCK_DIR/curl_args"
  fi
}

# Check if curl args contain a specific string
curl_args_contain() {
  grep -qF "$1" "$MOCK_DIR/curl_args" 2>/dev/null
}

assert_eq() {
  local desc="$1" expected="$2" actual="$3"
  if [ "$expected" = "$actual" ]; then
    echo "  PASS: $desc"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $desc"
    echo "    expected: $expected"
    echo "    actual:   $actual"
    FAIL=$((FAIL + 1))
  fi
}

assert_contains() {
  local desc="$1" needle="$2" haystack="$3"
  if echo "$haystack" | grep -qF "$needle"; then
    echo "  PASS: $desc"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $desc"
    echo "    expected to contain: $needle"
    echo "    actual: $haystack"
    FAIL=$((FAIL + 1))
  fi
}

assert_json_field() {
  local desc="$1" json="$2" jq_expr="$3" expected="$4"
  local actual
  actual=$(echo "$json" | jq -r "$jq_expr" 2>/dev/null || echo "JQ_ERROR")
  assert_eq "$desc" "$expected" "$actual"
}

assert_exit_code() {
  local desc="$1" expected="$2" actual="$3"
  assert_eq "$desc (exit code)" "$expected" "$actual"
}

# Prepend mock dir to PATH so our mock curl/uuidgen are used
export PATH="$MOCK_DIR:$PATH"
setup_mock_uuidgen

# ============================================================
echo "=== discover.sh ==="
# ============================================================

echo "-- missing arguments --"
setup_mock_curl '{}'
rc=0; "$PARENT_DIR/discover.sh" 2>/dev/null || rc=$?
assert_exit_code "exits with error" "1" "$rc"

echo "-- fetches agent card --"
AGENT_CARD='{"name":"test-agent","skills":[]}'
setup_mock_curl "$AGENT_CARD"
"$PARENT_DIR/discover.sh" http://localhost:8080 > /dev/null 2>&1
curl_args_contain "http://localhost:8080/.well-known/agent-card.json"
assert_exit_code "URL contains well-known path" "0" "$?"

echo "-- strips trailing slash --"
setup_mock_curl '{}'
"$PARENT_DIR/discover.sh" http://localhost:8080/ > /dev/null 2>&1
curl_args_contain "http://localhost:8080/.well-known/agent-card.json"
assert_exit_code "trailing slash stripped" "0" "$?"

# ============================================================
echo ""
echo "=== send-message.sh ==="
# ============================================================

echo "-- missing arguments --"
setup_mock_curl '{}'
rc=0; "$PARENT_DIR/send-message.sh" 2>/dev/null || rc=$?
assert_exit_code "exits with error" "1" "$rc"

echo "-- HTTP+JSON binding (default) --"
setup_mock_curl '{"task":{"id":"t1"}}'
"$PARENT_DIR/send-message.sh" http://localhost:8080 "Hello" > /dev/null 2>&1
curl_args_contain "http://localhost:8080/message:send"
assert_exit_code "URL is /message:send" "0" "$?"
BODY=$(get_request_body)
assert_json_field "has message_id" "$BODY" ".message.message_id" "00000000-0000-0000-0000-000000000001"
assert_json_field "has role" "$BODY" ".message.role" "ROLE_USER"
assert_json_field "has text part" "$BODY" ".message.parts[0].text" "Hello"
assert_json_field "has accepted_output_modes" "$BODY" ".configuration.accepted_output_modes[0]" "text/plain"

echo "-- JSON-RPC binding --"
setup_mock_curl '{"jsonrpc":"2.0","id":1,"result":{"task":{"id":"t1"}}}'
"$PARENT_DIR/send-message.sh" --binding jsonrpc http://localhost:8080 "Hello" > /dev/null 2>&1
BODY=$(get_request_body)
assert_json_field "method is SendMessage" "$BODY" ".method" "SendMessage"
assert_json_field "has jsonrpc field" "$BODY" ".jsonrpc" "2.0"
assert_json_field "uses camelCase messageId" "$BODY" ".params.message.messageId" "00000000-0000-0000-0000-000000000001"
assert_json_field "uses camelCase acceptedOutputModes" "$BODY" ".params.configuration.acceptedOutputModes[0]" "text/plain"

echo "-- with context-id and task-id (HTTP) --"
setup_mock_curl '{}'
"$PARENT_DIR/send-message.sh" --context-id ctx-1 --task-id task-1 http://localhost:8080 "Follow-up" > /dev/null 2>&1
BODY=$(get_request_body)
assert_json_field "has context_id" "$BODY" ".message.context_id" "ctx-1"
assert_json_field "has task_id" "$BODY" ".message.task_id" "task-1"

echo "-- with context-id and task-id (JSON-RPC) --"
setup_mock_curl '{}'
"$PARENT_DIR/send-message.sh" --binding jsonrpc --context-id ctx-1 --task-id task-1 http://localhost:8080 "Follow-up" > /dev/null 2>&1
BODY=$(get_request_body)
assert_json_field "has contextId" "$BODY" ".params.message.contextId" "ctx-1"
assert_json_field "has taskId" "$BODY" ".params.message.taskId" "task-1"

echo "-- custom message-id --"
setup_mock_curl '{}'
"$PARENT_DIR/send-message.sh" --message-id my-custom-id http://localhost:8080 "Hi" > /dev/null 2>&1
BODY=$(get_request_body)
assert_json_field "uses custom message_id" "$BODY" ".message.message_id" "my-custom-id"

# ============================================================
echo ""
echo "=== send-streaming-message.sh ==="
# ============================================================

echo "-- missing arguments --"
setup_mock_curl '{}'
rc=0; "$PARENT_DIR/send-streaming-message.sh" 2>/dev/null || rc=$?
assert_exit_code "exits with error" "1" "$rc"

echo "-- HTTP+JSON binding (default) --"
setup_mock_curl ''
"$PARENT_DIR/send-streaming-message.sh" --raw http://localhost:8080 "Stream me" > /dev/null 2>&1
curl_args_contain "http://localhost:8080/message:stream"
assert_exit_code "URL is /message:stream" "0" "$?"
curl_args_contain "text/event-stream"
assert_exit_code "Accept header is SSE" "0" "$?"

echo "-- JSON-RPC binding --"
setup_mock_curl ''
"$PARENT_DIR/send-streaming-message.sh" --raw --binding jsonrpc http://localhost:8080 "Stream me" > /dev/null 2>&1
BODY=$(get_request_body)
assert_json_field "method is SendStreamingMessage" "$BODY" ".method" "SendStreamingMessage"

# ============================================================
echo ""
echo "=== get-task.sh ==="
# ============================================================

echo "-- missing arguments --"
setup_mock_curl '{}'
rc=0; "$PARENT_DIR/get-task.sh" 2>/dev/null || rc=$?
assert_exit_code "exits with error" "1" "$rc"

echo "-- HTTP+JSON binding (default) --"
setup_mock_curl '{"id":"t1","status":{"state":"TASK_STATE_COMPLETED"}}'
"$PARENT_DIR/get-task.sh" http://localhost:8080 task-abc > /dev/null 2>&1
curl_args_contain "http://localhost:8080/tasks/task-abc"
assert_exit_code "URL contains task ID" "0" "$?"

echo "-- JSON-RPC binding --"
setup_mock_curl '{"jsonrpc":"2.0","id":1,"result":{}}'
"$PARENT_DIR/get-task.sh" --binding jsonrpc http://localhost:8080 task-abc > /dev/null 2>&1
BODY=$(get_request_body)
assert_json_field "method is GetTask" "$BODY" ".method" "GetTask"
assert_json_field "params.id is task ID" "$BODY" ".params.id" "task-abc"

# ============================================================
echo ""
echo "=== list-tasks.sh ==="
# ============================================================

echo "-- missing arguments --"
setup_mock_curl '{}'
rc=0; "$PARENT_DIR/list-tasks.sh" 2>/dev/null || rc=$?
assert_exit_code "exits with error" "1" "$rc"

echo "-- HTTP+JSON binding (default) --"
setup_mock_curl '[]'
"$PARENT_DIR/list-tasks.sh" http://localhost:8080 ctx-abc > /dev/null 2>&1
curl_args_contain "http://localhost:8080/tasks?context_id=ctx-abc"
assert_exit_code "URL contains context_id query param" "0" "$?"

echo "-- JSON-RPC binding --"
setup_mock_curl '{"jsonrpc":"2.0","id":1,"result":[]}'
"$PARENT_DIR/list-tasks.sh" --binding jsonrpc http://localhost:8080 ctx-abc > /dev/null 2>&1
BODY=$(get_request_body)
assert_json_field "method is ListTasks" "$BODY" ".method" "ListTasks"
assert_json_field "params.contextId is context ID" "$BODY" ".params.contextId" "ctx-abc"

# ============================================================
echo ""
echo "=== cancel-task.sh ==="
# ============================================================

echo "-- missing arguments --"
setup_mock_curl '{}'
rc=0; "$PARENT_DIR/cancel-task.sh" 2>/dev/null || rc=$?
assert_exit_code "exits with error" "1" "$rc"

echo "-- HTTP+JSON binding (default) --"
setup_mock_curl '{"id":"t1","status":{"state":"TASK_STATE_CANCELED"}}'
"$PARENT_DIR/cancel-task.sh" http://localhost:8080 task-abc > /dev/null 2>&1
curl_args_contain "http://localhost:8080/tasks/task-abc:cancel"
assert_exit_code "URL contains :cancel suffix" "0" "$?"

echo "-- JSON-RPC binding --"
setup_mock_curl '{"jsonrpc":"2.0","id":1,"result":{}}'
"$PARENT_DIR/cancel-task.sh" --binding jsonrpc http://localhost:8080 task-abc > /dev/null 2>&1
BODY=$(get_request_body)
assert_json_field "method is CancelTask" "$BODY" ".method" "CancelTask"
assert_json_field "params.id is task ID" "$BODY" ".params.id" "task-abc"

# ============================================================
echo ""
echo "================================"
echo "Results: $PASS passed, $FAIL failed"
echo "================================"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
