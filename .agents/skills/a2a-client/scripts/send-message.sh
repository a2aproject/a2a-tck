#!/bin/bash
# Send a message to an A2A agent.
#
# Usage: send-message.sh [OPTIONS] <ENDPOINT_URL> <MESSAGE_TEXT>
#
# Options:
#   --binding <jsonrpc|http>  Protocol binding (default: http)
#   --context-id <ID>         Context ID for multi-turn conversations
#   --task-id <ID>            Task ID for continuing a specific task
#   --message-id <ID>         Message ID (default: auto-generated UUID)
#
# Examples:
#   send-message.sh http://localhost:8080 "Hello, agent!"
#   send-message.sh --binding jsonrpc http://localhost:8080 "What is 2+2?"
#   send-message.sh --context-id abc-123 http://localhost:8080 "Follow-up message"

set -euo pipefail

BINDING="http"
CONTEXT_ID=""
TASK_ID=""
MESSAGE_ID=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --binding)    BINDING="$2"; shift 2 ;;
    --context-id) CONTEXT_ID="$2"; shift 2 ;;
    --task-id)    TASK_ID="$2"; shift 2 ;;
    --message-id) MESSAGE_ID="$2"; shift 2 ;;
    --help|-h)
      sed -n '2,/^$/{ s/^# //; s/^#$//; p }' "$0"
      exit 0
      ;;
    *) break ;;
  esac
done

if [ $# -lt 2 ]; then
  echo "Usage: $0 [OPTIONS] <ENDPOINT_URL> <MESSAGE_TEXT>" >&2
  echo "Use --help for details." >&2
  exit 1
fi

ENDPOINT_URL="${1%/}"
MESSAGE_TEXT="$2"
MESSAGE_ID="${MESSAGE_ID:-$(uuidgen | tr '[:upper:]' '[:lower:]')}"

if [ "$BINDING" = "jsonrpc" ]; then
  # Build message object with camelCase fields
  MSG=$(jq -n \
    --arg mid "$MESSAGE_ID" \
    --arg text "$MESSAGE_TEXT" \
    --arg cid "$CONTEXT_ID" \
    --arg tid "$TASK_ID" \
    '{
      messageId: $mid,
      role: "ROLE_USER",
      parts: [{text: $text}]
    }
    | if $cid != "" then .contextId = $cid else . end
    | if $tid != "" then .taskId = $tid else . end')

  jq -n \
    --argjson msg "$MSG" \
    '{
      jsonrpc: "2.0",
      id: 1,
      method: "SendMessage",
      params: {
        message: $msg,
        configuration: {
          acceptedOutputModes: ["text/plain", "application/json"]
        }
      }
    }' \
  | curl -sf -X POST "$ENDPOINT_URL" \
      -H "Content-Type: application/json" \
      -d @- | jq .
else
  # HTTP+JSON with snake_case fields
  MSG=$(jq -n \
    --arg mid "$MESSAGE_ID" \
    --arg text "$MESSAGE_TEXT" \
    --arg cid "$CONTEXT_ID" \
    --arg tid "$TASK_ID" \
    '{
      message_id: $mid,
      role: "ROLE_USER",
      parts: [{text: $text}]
    }
    | if $cid != "" then .context_id = $cid else . end
    | if $tid != "" then .task_id = $tid else . end')

  jq -n \
    --argjson msg "$MSG" \
    '{
      message: $msg,
      configuration: {
        accepted_output_modes: ["text/plain", "application/json"]
      }
    }' \
  | curl -sf -X POST "${ENDPOINT_URL}/message:send" \
      -H "Content-Type: application/json" \
      -d @- | jq .
fi
