#!/bin/bash
# Usage: ./check_spec.sh "search term"
echo "=== Searching in Specification ==="
grep -n -i "$1" A2A_SPECIFICATION.md | head -20
echo -e "\n=== Searching in JSON Schema ==="
jq -r --arg term "$1" '. | .. | select(type == "object") | to_entries[] | select(.key | contains($term))' a2a_schema.json 2>/dev/null | head -20 