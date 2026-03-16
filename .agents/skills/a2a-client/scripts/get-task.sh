#!/bin/bash
# Get the status of an A2A task.
#
# Usage: get-task.sh [OPTIONS] <ENDPOINT_URL> <TASK_ID>
#
# Options:
#   --binding <jsonrpc|http>  Protocol binding (default: http)
#
# Examples:
#   get-task.sh http://localhost:8080 task-abc-123
#   get-task.sh --binding jsonrpc http://localhost:8080 task-abc-123

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
  echo "Usage: $0 [OPTIONS] <ENDPOINT_URL> <TASK_ID>" >&2
  echo "Use --help for details." >&2
  exit 1
fi

ENDPOINT_URL="${1%/}"
TASK_ID="$2"

if [ "$BINDING" = "jsonrpc" ]; then
  jq -n --arg tid "$TASK_ID" \
    '{jsonrpc:"2.0", id:1, method:"GetTask", params:{id:$tid}}' \
  | curl -sf -X POST "$ENDPOINT_URL" \
      -H "Content-Type: application/json" \
      -d @- | jq .
else
  curl -sf "${ENDPOINT_URL}/tasks/${TASK_ID}" | jq .
fi
