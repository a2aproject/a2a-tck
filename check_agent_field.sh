#!/bin/bash
field=$1
echo "Checking if '$field' exists in AgentCard schema..."
jq --arg f "$field" '.definitions.AgentCard.properties | has($f)' a2a_schema.json
echo "Is it required?"
jq --arg f "$field" '.definitions.AgentCard.required // [] | index($f) != null' a2a_schema.json 