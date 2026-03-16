#!/bin/bash
# Fetch the AgentCard from an A2A agent's well-known endpoint.
#
# Usage: discover.sh <BASE_URL>
# Example: discover.sh http://localhost:8080

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <BASE_URL>" >&2
  exit 1
fi

BASE_URL="${1%/}"

curl -sf "${BASE_URL}/.well-known/agent-card.json" | jq .
