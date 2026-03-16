#!/bin/bash
# List tasks for a given context.
#
# Usage: list-tasks.sh [OPTIONS] <ENDPOINT_URL> <CONTEXT_ID>
#
# Options:
#   --binding <jsonrpc|http>  Protocol binding (default: http)
#
# Examples:
#   list-tasks.sh http://localhost:8080 ctx-abc-123
#   list-tasks.sh --binding jsonrpc http://localhost:8080 ctx-abc-123

set -euo pipefail

BINDING="http"

while [[ $# -gt 0 ]]; do
  case $1 in
    --binding) BINDING="$2"; shift 2 ;;
    --help|-h)
      sed -n '2,/^$/{ s/^# //; s/^#$//; p }' "$0"
      exit 0
      ;;
    *) break ;;
  esac
done

if [ $# -lt 2 ]; then
  echo "Usage: $0 [OPTIONS] <ENDPOINT_URL> <CONTEXT_ID>" >&2
  echo "Use --help for details." >&2
  exit 1
fi

ENDPOINT_URL="${1%/}"
CONTEXT_ID="$2"

if [ "$BINDING" = "jsonrpc" ]; then
  jq -n --arg cid "$CONTEXT_ID" \
    '{jsonrpc:"2.0", id:1, method:"ListTasks", params:{contextId:$cid}}' \
  | curl -sf -X POST "$ENDPOINT_URL" \
      -H "Content-Type: application/json" \
      -d @- | jq .
else
  curl -sf "${ENDPOINT_URL}/tasks?context_id=${CONTEXT_ID}" | jq .
fi
