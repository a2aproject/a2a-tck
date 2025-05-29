#!/usr/bin/env python3
import json
import sys

print("=== A2A Specification Validation ===\n")

# Load the schema
with open('a2a_schema.json', 'r') as f:
    schema = json.load(f)

# Check 1: Part type field name
print("1. Message Part Field Name Check:")
text_part = schema['definitions'].get('TextPart', {})
if 'properties' in text_part:
    if 'kind' in text_part['properties']:
        print("   ✓ TextPart uses 'kind' field")
    elif 'type' in text_part['properties']:
        print("   ✓ TextPart uses 'type' field")
    else:
        print("   ✗ Could not determine field name")

# Check 2: Agent Card required fields
print("\n2. Agent Card Required Fields:")
agent_card = schema['definitions'].get('AgentCard', {})
required = agent_card.get('required', [])
print(f"   Required: {required}")
properties = list(agent_card.get('properties', {}).keys())
print(f"   All fields: {properties}")

# Check 3: Error codes
print("\n3. Error Codes Found:")
for name, definition in schema['definitions'].items():
    if name.endswith('Error'):
        code = definition.get('properties', {}).get('code', {}).get('const')
        if code:
            print(f"   {code}: {name}") 