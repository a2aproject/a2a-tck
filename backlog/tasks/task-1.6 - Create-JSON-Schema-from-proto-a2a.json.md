---
id: TASK-1.6
title: Create JSON Schema from proto (a2a.json)
status: Done
assignee: []
created_date: '2026-01-28 09:07'
updated_date: '2026-02-16 10:03'
labels:
  - phase-1
  - foundation
  - schema
dependencies:
  - task-1.3
parent_task_id: TASK-1
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Generate the JSON Schema (a2a.json) derived from a2a.proto for validating JSON-RPC and REST responses.

**Reference**: PRD Section 3.2, Section 6 Task 1.5

**Target**: `specification/a2a.json`

**Options**:
1. Reuse the script https://github.com/a2aproject/A2A/blob/main/scripts/proto_to_json_schema.sh
2. Manually derive from proto definitions
3. Obtain from official A2A spec if available

**Requirements**:
- Schema must use JSON Schema Draft 2020-12
- Must define all message types as referenceable definitions ($defs)
- Must match proto semantics exactly (oneof → oneOf, repeated → array, etc.)

**Key definitions needed**:
- Task, Message, Part (oneof: text|file|data)
- Artifact, AgentCard, SendMessageRequest, SendMessageResponse
- All error response structures
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 specification/a2a.json exists and is valid JSON
- [x] #2 Schema uses JSON Schema Draft 2020-12 ($schema field)
- [x] #3 All proto message types have corresponding $defs entries
- [x] #4 Task, Message, Part, Artifact, AgentCard definitions are present
- [x] #5 Schema can be loaded by jsonschema library without errors
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Implementation Plan

Use a tool to genereate the JSON scheme from the proto definition.
Reuse the script  `https://github.com/a2aproject/A2A/blob/main/scripts/proto_to_json_schema.sh` 
and store the generated `a2a.json` in `specification/a2a.json`

### Schema Requirements
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$defs": {
    "Task": { ... },
    "Message": { ... },
    "Part": { "oneOf": [...] },
    "Artifact": { ... },
    "AgentCard": { ... },
    "SendMessageRequest": { ... },
    "SendMessageResponse": { ... }
  }
}
```

### Verification
```python
import json
from jsonschema import Draft202012Validator

with open("specification/a2a.json") as f:
    schema = json.load(f)

# Verify valid JSON Schema
Draft202012Validator.check_schema(schema)

# Verify key definitions exist
assert "Task" in schema.get("$defs", {})
assert "Message" in schema.get("$defs", {})
```

### Notes
- Schema MUST use Draft 2020-12 ($schema field)
- Must match proto semantics exactly
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Generated JSON Schema from a2a.proto using the official A2A script:

**Script:** `scripts/proto_to_json_schema.sh` (from A2A repository)

**Output:** `specification/a2a.json`
- Schema version: JSON Schema Draft 2020-12
- 49 definitions including Task, Message, Part, Artifact, Agent Card, Send Message Request/Response

**Prerequisites installed:**
- protoc (libprotoc 33.4)
- protoc-gen-jsonschema v0.5.2 (bufbuild/protoschema-plugins)
- jq 1.6
- googleapis repository cloned to ~/Developer/googleapis

**Makefile target:** `make jsonschema`

**Environment required:**
```bash
export PATH="$HOME/go/bin:$PATH"
export GOOGLEAPIS_DIR="$HOME/Developer/googleapis"
```
<!-- SECTION:FINAL_SUMMARY:END -->
