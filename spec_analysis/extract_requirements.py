#!/usr/bin/env python3
import json
import re

print("=== A2A Specification Requirement Analysis ===\n")

# Load schema
with open("a2a_schema.json", "r") as f:
    schema = json.load(f)

# Load specification
with open("A2A_SPECIFICATION.md", "r") as f:
    spec_text = f.read()

# Extract MUST/SHALL requirements
must_pattern = r"(.*?)(MUST|SHALL|REQUIRED)(?! NOT)(.*?)(?:\.|$)"
must_matches = re.findall(must_pattern, spec_text, re.MULTILINE | re.IGNORECASE)

print("## Mandatory Requirements (MUST/SHALL/REQUIRED)")
for i, match in enumerate(must_matches[:20], 1):  # First 20
    context = f"{match[0][-50:]}{match[1]}{match[2][:50]}"
    print(f"{i}. ...{context}...")

# Extract SHOULD requirements
should_pattern = r"(.*?)(SHOULD|RECOMMENDED)(?! NOT)(.*?)(?:\.|$)"
should_matches = re.findall(should_pattern, spec_text, re.MULTILINE | re.IGNORECASE)

print("\n## Optional Strong Requirements (SHOULD/RECOMMENDED)")
for i, match in enumerate(should_matches[:20], 1):  # First 20
    context = f"{match[0][-50:]}{match[1]}{match[2][:50]}"
    print(f"{i}. ...{context}...")

# Analyze required fields from schema
print("\n## Required Fields Analysis")
for type_name in ["AgentCard", "Message", "Task", "Part"]:
    if type_name in schema["definitions"]:
        required = schema["definitions"][type_name].get("required", [])
        print(f"\n{type_name}: {required}")
