#!/bin/bash
# Usage: ./check_spec.sh "search term"
echo "=== Searching in Specification ==="
grep -n -i "$1" A2A_SPECIFICATION.md | head -20
echo -e "\n=== Searching in JSON Schema ==="
echo "Searching for term: '$1'"
# More efficient search - look in specific places rather than recursively
echo "Checking definitions..."
jq -r --arg term "$1" '.definitions | to_entries[] | select(.key | contains($term)) | "\(.key): \(.value.type // "object")"' a2a_schema.json 2>/dev/null | head -10
echo "Checking properties..."
jq -r --arg term "$1" '.definitions | to_entries[] | .value.properties // {} | to_entries[] | select(.key | contains($term)) | "\(.key)"' a2a_schema.json 2>/dev/null | head -10 