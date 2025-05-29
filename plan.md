# TCK and SUT Fix Implementation Plan

## Overview

This plan addresses the issues identified in the TCK and SUT implementation. Since the SDK is out of our control, we will align tests with the specification and accept that some tests may fail if the SDK doesn't comply.

## Understanding Your References

You have three key documents:
1. **A2A_SPECIFICATION.md** - Human-readable specification
2. **a2a_schema.json** - Machine-readable JSON schema (this is the source of truth for field names!)
3. **The SDK source code** - Shows what's actually implemented

When in doubt: **JSON Schema > Markdown Spec > SDK Code**

### Quick Start Commands
```bash
# When you need to know a field name
jq '.definitions.TextPart.properties | keys' a2a_schema.json

# When you need to know what's required
jq '.definitions.Message.required' a2a_schema.json

# When you need to find something in the spec
grep -n "authentication" A2A_SPECIFICATION.md
```

## Guiding Principles

1. **Specification is Truth**: The JSON schema is the definitive source
2. **Test What's Right**: Write tests for what the spec says, not what the SDK does
3. **Document SDK Gaps**: When tests fail due to SDK issues, document it clearly
4. **Small Steps**: Make one change at a time and verify nothing breaks
5. **Version Control**: Commit after each successful task completion

## Pre-Work Setup

### Step 1: Environment Preparation

Ask the user to start the SUT

```bash
# Create a new branch for the fixes
git checkout -b fix/tck-specification-alignment

# Run all tests and save current state
./run_tck.py --sut-url http://localhost:9999 --test-scope all --verbose
# Create a working notes file
touch WORKING_NOTES.md
```

### Step 2: Download Specification References
```bash
# Download the specification in markdown format
curl -o A2A_SPECIFICATION.md https://raw.githubusercontent.com/google-a2a/A2A/refs/heads/main/docs/specification.md

# Download the JSON schema (this is the definitive source for field names!)
curl -o a2a_schema.json https://raw.githubusercontent.com/google-a2a/A2A/refs/heads/main/specification/json/a2a.json

# Create a quick reference script
cat > check_spec.sh << 'EOF'
#!/bin/bash
# Usage: ./check_spec.sh "search term"
echo "=== Searching in Specification ==="
grep -n -i "$1" A2A_SPECIFICATION.md | head -20
echo -e "\n=== Searching in JSON Schema ==="
jq -r --arg term "$1" '. | .. | select(type == "object") | to_entries[] | select(.key | contains($term))' a2a_schema.json 2>/dev/null | head -20
EOF
chmod +x check_spec.sh
```

### Step 3: Install JSON Tools
```bash
# Install jq for JSON schema inspection (if not already installed)
# On macOS: brew install jq
# On Ubuntu: sudo apt-get install jq
# On Windows: choco install jq

# Test it works
jq --version
```

## Helpful JSON Schema Investigation Commands

### Quick Reference Card
Save this as `schema_helpers.md` for easy access:

```bash
# 1. List all defined types in the schema
jq '.definitions | keys' a2a_schema.json

# 2. Check if a specific type exists
jq '.definitions | has("TaskNotFoundError")' a2a_schema.json

# 3. Get complete definition of a type
jq '.definitions.Message' a2a_schema.json

# 4. Find all properties of a type
jq '.definitions.Message.properties | keys' a2a_schema.json

# 5. Check if a property is required
jq '.definitions.Message.required' a2a_schema.json

# 6. Find all types with a specific property
jq '.definitions | to_entries[] | select(.value.properties.taskId) | .key' a2a_schema.json

# 7. Get the type of a specific property
jq '.definitions.Message.properties.parts.items' a2a_schema.json

# 8. Find all enum values
jq '.. | .enum? // empty' a2a_schema.json | sort -u

# 9. Check discriminator fields (like "kind" or "type")
jq '.definitions.Part' a2a_schema.json

# 10. Find all error codes
jq '[.. | .properties?.code?.const? // empty] | unique' a2a_schema.json
```

### Common Investigations

**"What fields does X have?"**
```bash
TYPE="Message"  # Change this
jq --arg type "$TYPE" '.definitions[$type].properties | keys' a2a_schema.json
```

**"Is field Y required in X?"**
```bash
TYPE="Message"  # Change this
FIELD="messageId"  # Change this
jq --arg type "$TYPE" --arg field "$FIELD" '
  .definitions[$type].required // [] | index($field) != null
' a2a_schema.json
```

**"What's the exact structure of a request?"**
```bash
METHOD="SendMessageRequest"  # Change this
jq --arg method "$METHOD" '.definitions[$method]' a2a_schema.json | less
```

### Step 4: Validate Your Understanding
Before making any code changes, validate your findings:

```bash
# Create a validation script
cat > validate_findings.py << 'EOF'
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

EOF
chmod +x validate_findings.py
python3 validate_findings.py
```

This will give you a clear picture of what the specification actually says before you start changing code.

## Task Implementation Plan

### Phase 1: Field Name Standardization

#### Task 1.1: Audit Message Part Field Usage
**Goal**: Determine what field name the specification uses for part types

**Steps**:
1. Check the JSON schema for the definitive answer:
   ```bash
   # Find TextPart definition in schema
   jq '.definitions.TextPart' a2a_schema.json
   
   # Look for the field that defines the type
   jq '.definitions.TextPart.properties' a2a_schema.json
   
   # Check all part types
   jq '.definitions | to_entries[] | select(.key | endswith("Part")) | {name: .key, properties: .value.properties | keys}' a2a_schema.json
   ```

2. Verify in the markdown specification:
   ```bash
   # Search for part definitions
   ./check_spec.sh "TextPart"
   ./check_spec.sh "part type"
   
   # Look for example messages
   grep -A 10 -B 5 '"parts"' A2A_SPECIFICATION.md
   ```

3. Create a file `SPECIFICATION_FINDINGS.md`:
   ```markdown
   # Part Type Field Name Finding
   
   ## JSON Schema Evidence
   ```json
   [Paste the relevant JSON schema snippet here]
   ```
   
   ## Specification Text Evidence
   [Paste relevant sections from the markdown spec]
   
   ## Conclusion
   The specification uses: [ ] "type" [ ] "kind"
   
   ## SDK Mismatch
   The SDK uses "kind" while the specification uses [answer]
  

**Verification**: 
- [ ] JSON schema checked
- [ ] Markdown spec checked
- [ ] Clear conclusion documented
- [ ] SPECIFICATION_FINDINGS.md created

#### Task 1.2: Create Field Name Compatibility Layer
**Goal**: Handle the field name issue systematically

**Steps**:
1. First, let's confirm what we found in Task 1.1. The schema check should show:
   ```bash
   # Example: Checking TextPart structure
   jq '.definitions.TextPart.properties' a2a_schema.json
   # Likely output showing "kind" field with const: "text"
   ```

2. If spec uses "kind" (as suggested by the SDK following the schema), create `tests/utils/spec_adapter.py`:
   ```python
   """
   Adapter to ensure tests use specification-compliant field names.
   
   Based on investigation of a2a_schema.json:
   - TextPart uses 'kind' field with value 'text'
   - FilePart uses 'kind' field with value 'file'
   - DataPart uses 'kind' field with value 'data'
   """
   
   def ensure_spec_field_names(message_params):
       """Ensure message uses specification field names.
       
       Currently the spec and SDK both use 'kind', but some tests
       incorrectly use 'type'. This normalizes to spec-compliant format.
       """
       if "parts" in message_params.get("message", {}):
           for part in message_params["message"]["parts"]:
               # If test mistakenly used 'type', convert to 'kind'
               if "type" in part and "kind" not in part:
                   part["kind"] = part.pop("type")
       return message_params
   
   def validate_part_structure(part):
       """Validate part follows specification structure."""
       assert "kind" in part, "Specification requires 'kind' field (not 'type')"
       assert part["kind"] in ["text", "file", "data"], f"Invalid kind: {part['kind']}"
   ```

3. **Important Discovery**: If both spec and SDK use "kind", then the issue is that some tests incorrectly use "type"! Update the adapter docstring to reflect this.

**Verification**:
- [ ] Confirmed actual field name from schema
- [ ] Adapter handles the correct transformation
- [ ] Clear documentation of the issue

#### Task 1.3: Update All Test Fixtures
**Goal**: Make all tests use specification field name

**Important Note**: If you discovered that BOTH the spec and SDK use "kind", then the bug is in the tests that use "type"!

**Steps**:
1. Find all incorrect usages:
   ```bash
   # Find test files using wrong field name 'type'
   grep -r '"type".*:.*"text"' tests/ | grep -v "content-type" > files_with_wrong_field.txt
   grep -r '"type".*:.*"file"' tests/ >> files_with_wrong_field.txt
   grep -r '"type".*:.*"data"' tests/ >> files_with_wrong_field.txt
   
   # Count how many files need fixing
   cat files_with_wrong_field.txt | cut -d: -f1 | sort -u | wc -l
   ```

2. Fix each file systematically:
   ```python
   # Change all instances of:
   "parts": [{"type": "text", "text": "Hello"}]
   # To:
   "parts": [{"kind": "text", "text": "Hello"}]
   
   # Also fix:
   "parts": [{"type": "file", "file": {...}}]
   # To:
   "parts": [{"kind": "file", "file": {...}}]
   ```

3. **Use sed for bulk updates** (after backing up):
   ```bash
   # Backup first!
   cp -r tests/ tests_backup/
   
   # Fix text parts
   find tests/ -name "*.py" -exec sed -i 's/"type": "text"/"kind": "text"/g' {} \;
   
   # Fix file parts  
   find tests/ -name "*.py" -exec sed -i 's/"type": "file"/"kind": "file"/g' {} \;
   
   # Fix data parts
   find tests/ -name "*.py" -exec sed -i 's/"type": "data"/"kind": "data"/g' {} \;
   
   # Verify changes
   diff -r tests_backup/ tests/ | less
   ```

4. Run tests incrementally:

Ask the user to start the SUT

   ```bash
   # Test each module as you fix it
   ./run_tck.py --sut-url http://localhost:9999 --test-pattern "test_message_send_method"
   ./run_tck.py --sut-url http://localhost:9999 --test-pattern "test_edge_cases.py" -v
   # etc.
   ```

**File Update Order** (to avoid breaking dependencies):
1. `tests/test_message_send_method.py` - Core functionality
2. `tests/test_edge_cases.py` - Edge cases
3. `tests/test_invalid_business_logic.py` - Business logic
4. `tests/test_protocol_violations.py` - Protocol tests
5. `tests/test_state_transitions.py` - State management
6. `tests/test_concurrency.py` - Concurrent operations
7. `tests/test_resilience.py` - Resilience tests
8. All others

**Verification**:
- [ ] All wrong "type" usages found
- [ ] Files backed up
- [ ] Bulk replacement completed
- [ ] Each module tested individually
- [ ] No remaining "type" fields for parts

### Phase 2: Agent Card Specification Alignment

#### Task 2.1: Document Agent Card Requirements
**Goal**: List all required Agent Card fields from specification

**Steps**:
1. Extract Agent Card schema definition:
   ```bash
   # Get the complete Agent Card definition
   jq '.definitions.AgentCard' a2a_schema.json > agent_card_schema.json
   
   # List all properties and their requirements
   jq '.definitions.AgentCard | {
     required: .required,
     properties: .properties | keys,
     property_types: .properties | map_values(.type)
   }' a2a_schema.json
   
   # Check if protocolVersion and id are in the schema
   jq '.definitions.AgentCard.properties | keys | map(select(. == "protocolVersion" or . == "id"))' a2a_schema.json
   ```

2. Cross-reference with markdown specification:
   ```bash
   # Find Agent Card section
   grep -n "## Agent Card" A2A_SPECIFICATION.md
   grep -n "### Agent Card" A2A_SPECIFICATION.md
   
   # Get the section content
   sed -n '/## Agent Card/,/## [^#]/p' A2A_SPECIFICATION.md > agent_card_section.md
   ```

3. Create comparison table in SPECIFICATION_FINDINGS.md:
   ```markdown
   ## Agent Card Required Fields
   
   ### From JSON Schema
   Required fields: [paste jq output]
   
   | Field | Type | Required | In SDK | Notes |
   |-------|------|----------|--------|-------|
   | name | string | Yes | Yes | |
   | description | string | Yes | Yes | |
   | version | string | ? | Yes | |
   | url | string | ? | Yes | |
   | protocolVersion | string | ? | No | Check if exists in schema |
   | id | string | ? | No | Check if exists in schema |
   | capabilities | object | ? | Yes | |
   | defaultInputModes | array | ? | Yes | |
   | defaultOutputModes | array | ? | Yes | |
   | skills | array | ? | Yes | |

   ### Schema Definition
   ```json
   [Paste the complete AgentCard schema here]
   ```
   ```

**Quick Check Script**:
```bash
# Create a script to check if a field exists in Agent Card
cat > check_agent_field.sh << 'EOF'
#!/bin/bash
field=$1
echo "Checking if '$field' exists in AgentCard schema..."
jq --arg f "$field" '.definitions.AgentCard.properties | has($f)' a2a_schema.json
echo "Is it required?"
jq --arg f "$field" '.definitions.AgentCard.required // [] | index($f) != null' a2a_schema.json
EOF
chmod +x check_agent_field.sh

# Use it:
./check_agent_field.sh protocolVersion
./check_agent_field.sh id
```

**Verification**:
- [ ] JSON schema analyzed
- [ ] Required fields identified
- [ ] SDK gaps documented
- [ ] Quick check script works

#### Task 2.2: Update Agent Card Tests
**Goal**: Test for specification-required fields only

**Steps**:
1. Open `tests/test_agent_card.py`
2. Update `test_mandatory_fields_present()`:
   ```python
   def test_mandatory_fields_present(fetched_agent_card):
       """Test fields required by A2A specification section X.Y"""
       # Based on your findings, update this list
       mandatory_fields = ["name", "description", ...]  # As per spec
       
       missing_in_sdk = []  # Track what SDK doesn't provide
       
       for field in mandatory_fields:
           if field not in fetched_agent_card:
               # Check if this is a known SDK limitation
               if field in ["protocolVersion", "id"]:  # Known missing
                   missing_in_sdk.append(field)
                   pytest.skip(f"SDK missing required field: {field}")
               else:
                   pytest.fail(f"Agent Card missing required field: {field}")
   ```

**Verification**:
- [ ] Test updated with spec requirements
- [ ] Test documents SDK limitations
- [ ] Test runs (may skip/fail as expected)

#### Task 2.3: Remove SUT Agent Card Workaround
**Goal**: Remove field injection from SUT, let tests fail properly

**Steps**:
1. Open `python-sut/tck_core_agent/__main__.py`
2. Find `TckA2AStarletteApplication` class
3. Delete the entire custom class
4. Change the app initialization:
   ```python
   # From:
   app = TckA2AStarletteApplication(...)
   # To:
   app = A2AStarletteApplication(...)
   ```

**Verification**:
- [ ] Custom class removed
- [ ] SUT uses standard SDK class
- [ ] Run agent card tests - document failures

### Phase 3: Authentication Test Improvements

#### Task 3.1: Research Specification Authentication
**Goal**: Understand exact authentication requirements

**Steps**:
1. Find authentication section in specification:
   ```bash
   # Search for authentication sections
   grep -n -i "authentication" A2A_SPECIFICATION.md | head -20
   
   # Extract the authentication section
   grep -A 50 "## Authentication" A2A_SPECIFICATION.md > auth_section.md
   
   # Look for security schemes
   ./check_spec.sh "securitySchemes"
   ./check_spec.sh "security"
   ```

2. Check JSON schema for authentication structures:
   ```bash
   # Find authentication-related definitions
   jq '.definitions | keys | map(select(contains("Auth") or contains("Security")))' a2a_schema.json
   
   # Check AgentCard for security fields
   jq '.definitions.AgentCard.properties | keys | map(select(contains("auth") or contains("security")))' a2a_schema.json
   
   # Look at security scheme definitions
   jq '.definitions.SecurityScheme' a2a_schema.json
   ```

3. Document findings in SPECIFICATION_FINDINGS.md:
   ```markdown
   ## Authentication Requirements
   
   ### Specification Says
   [Quote relevant sections]
   
   ### Expected HTTP Behavior
   - Missing auth: [401/403/other?]
   - Invalid auth: [401/403/other?]
   - Before JSON-RPC layer: [Yes/No]
   
   ### Security Scheme Format
   ```json
   [Paste schema definition]
   ```
   
   ### How SUTs Should Declare Authentication
   - Field name: securitySchemes
   - Location: [Agent Card root? Other?]
   - Format: [OpenAPI 3.x Security Scheme objects]
   ```

**Verification**:
- [ ] Authentication spec section found
- [ ] HTTP behavior documented
- [ ] Security scheme format clear
- [ ] Declaration method understood

#### Task 3.2: Remove SUT Authentication Middleware
**Goal**: Use SDK features only, accept limitations

**Steps**:
1. Open `python-sut/tck_core_agent/__main__.py`
2. Remove `AuthenticationMiddleware` class entirely
3. Remove middleware from app:
   ```python
   # Remove this line:
   # starlette_app.add_middleware(AuthenticationMiddleware)
   ```
4. Document in WORKING_NOTES.md that auth is now not enforced

**Verification**:
- [ ] Middleware class deleted
- [ ] Middleware not added to app
- [ ] SUT starts successfully

#### Task 3.3: Update Authentication Tests
**Goal**: Test specification behavior, expect failures

**Steps**:
1. Open `tests/test_authentication.py`
2. Add specification references:
   ```python
   def test_missing_authentication(sut_client, auth_schemes):
       """
       A2A Specification Section X.Y: Authentication Requirements
       
       Note: This test expects HTTP 401/403 but SDK doesn't enforce auth.
       This is a known SDK limitation.
       """
       # ... existing test code ...
       
       # Add after the test:
       if response.status_code == 200:
           pytest.xfail("SDK doesn't enforce authentication - specification violation")
   ```

**Verification**:
- [ ] Tests document spec requirements
- [ ] Tests use pytest.xfail for SDK issues
- [ ] All auth tests updated

### Phase 4: Fix History Length Parameter

#### Task 4.1: Verify Specification Behavior
**Goal**: Understand how historyLength should work

**Steps**:
1. Find tasks/get method in specification
2. Document expected behavior:
   - Should it modify the response?
   - Which messages to return?
   - Edge cases?

**Verification**:
- [ ] Spec behavior documented
- [ ] Edge cases identified

#### Task 4.2: Test Correct Behavior
**Goal**: Write tests that verify spec behavior

**Steps**:
1. Keep SUT workaround for now (it implements correct behavior)
2. Add test to verify SDK default handler fails:
   ```python
   def test_sdk_history_length_bug():
       """Verify SDK DefaultRequestHandler doesn't handle historyLength"""
       # Create a test that would fail with SDK's handler
       # This documents the SDK bug
   ```

**Verification**:
- [ ] Test written for SDK bug
- [ ] Test properly documents issue

### Phase 5: Capability-Based Testing Enhancement

#### Task 5.1: Strict Capability Checking
**Goal**: Skip tests when capabilities not declared

**Steps**:
1. Update all streaming tests to check capability:
   ```python
   def test_message_stream_basic(async_http_client, agent_card_data):
       if not agent_card_data:
           pytest.skip("No agent card available")
       
       if not agent_card_utils.get_capability_streaming(agent_card_data):
           pytest.fail("Agent doesn't declare streaming capability - spec violation")
   ```

**Verification**:
- [ ] All capability-dependent tests updated
- [ ] Tests fail (not skip) when capability missing

### Phase 6: Error Code Validation

#### Task 6.1: Document Specification Error Codes
**Goal**: List all error codes from specification

**Steps**:
1. Extract all error definitions from JSON schema:
   ```bash
   # Find all error types
   jq '.definitions | to_entries[] | select(.key | endswith("Error")) | {
     name: .key,
     code: .value.properties.code.const,
     message: .value.properties.message.default
   }' a2a_schema.json > error_codes.json
   
   # Create a formatted table
   jq -r '.definitions | to_entries[] | select(.key | endswith("Error")) | 
     "\(.key)|\(.value.properties.code.const // "N/A")|\(.value.properties.message.default // "N/A")"' a2a_schema.json | 
     sort | 
     (echo "Error Type|Code|Default Message"; echo "---|---|---"; cat) > error_codes_table.md
   ```

2. Find error code documentation in spec:
   ```bash
   # Search for error codes section
   grep -n "Error Codes" A2A_SPECIFICATION.md
   grep -n "JSON-RPC.*error" A2A_SPECIFICATION.md
   
   # Look for standard JSON-RPC errors
   ./check_spec.sh "-32700"  # Parse error
   ./check_spec.sh "-32600"  # Invalid Request
   ./check_spec.sh "-32601"  # Method not found
   ./check_spec.sh "-32602"  # Invalid params
   ./check_spec.sh "-32603"  # Internal error
   ```

3. Create error code reference in SPECIFICATION_FINDINGS.md:
   ```markdown
   ## A2A Error Codes
   
   ### Standard JSON-RPC Errors
   | Code | Name | SDK Constant | Description |
   |------|------|--------------|-------------|
   | -32700 | Parse error | JSONParseError | Invalid JSON |
   | -32600 | Invalid Request | InvalidRequestError | Not a valid Request |
   | -32601 | Method not found | MethodNotFoundError | Method doesn't exist |
   | -32602 | Invalid params | InvalidParamsError | Invalid parameters |
   | -32603 | Internal error | InternalError | Internal JSON-RPC error |
   
   ### A2A-Specific Errors
   | Code | Name | SDK Constant | Description |
   |------|------|--------------|-------------|
   | -32001 | Task Not Found | TaskNotFoundError | |
   | -32002 | Task Not Cancelable | TaskNotCancelableError | |
   | -32003 | Push Notification Not Supported | PushNotificationNotSupportedError | |
   | -32004 | Unsupported Operation | UnsupportedOperationError | |
   | -32005 | Content Type Not Supported | ContentTypeNotSupportedError | |
   | -32006 | Invalid Agent Response | InvalidAgentResponseError | |
   
   ### Complete Schema Definition
   [Paste error_codes.json content]
   ```

**Create Error Code Checker**:
```bash
cat > check_error_code.sh << 'EOF'
#!/bin/bash
code=$1
echo "Checking error code $code..."
jq --arg code "$code" '.definitions | to_entries[] | 
  select(.value.properties.code.const == ($code | tonumber)) | 
  {name: .key, code: .value.properties.code.const, message: .value.properties.message}' a2a_schema.json
EOF
chmod +x check_error_code.sh
```

**Verification**:
- [ ] All error codes extracted from schema
- [ ] Error table created
- [ ] SDK constants mapped
- [ ] Error checker script works

#### Task 6.2: Update Error Assertions
**Goal**: Reference specification in error checks

**Steps**:
1. Update all error code assertions:
   ```python
   # From:
   assert resp["error"]["code"] == -32001
   # To:
   assert resp["error"]["code"] == -32001  # Spec: TaskNotFoundError
   ```

**Verification**:
- [ ] All error assertions commented
- [ ] Spec references added

## Progress Tracking Table

| Phase | Task | Status | Notes | Commit Hash |
|-------|------|--------|-------|-------------|
| Setup | Environment Prep | ⬜ | | |
| Setup | Download Spec | ⬜ | | |
| 1 | 1.1 Audit Fields | ⬜ | | |
| 1 | 1.2 Fix Fixtures | ⬜ | | |
| 2 | 2.1 Document Agent Card | ⬜ | | |
| 2 | 2.2 Update Tests | ⬜ | | |
| 2 | 2.3 Remove Workaround | ⬜ | | |
| 3 | 3.1 Research Auth | ⬜ | | |
| 3 | 3.2 Remove Middleware | ⬜ | | |
| 3 | 3.3 Update Tests | ⬜ | | |
| 4 | 4.1 Verify historyLength | ⬜ | | |
| 4 | 4.2 Test SDK Bug | ⬜ | | |
| 5 | 5.1 Capability Checks | ⬜ | | |
| 6 | 6.1 Document Errors | ⬜ | | |
| 6 | 6.2 Update Assertions | ⬜ | | |

**Legend**: ⬜ Not Started | 🟦 In Progress | ✅ Complete | ❌ Blocked

## Daily Workflow

1. **Start of Day**:
   ```bash
   git pull origin main
   git checkout fix/tck-specification-alignment
   ```

2. **Before Each Task**:
   - Read the task completely
   - Check specification section
   - Run related tests to see current state

3. **After Each Task**:
   - Run tests: `./run_tck.py --sut-url http://localhost:9999 --test-pattern "[affected_test].py"`
   - Update progress table
   - Commit with message: `fix(tck): [Task X.Y] Description`
   
4. **End of Day**:
   - Update WORKING_NOTES.md with findings
   - Push branch: `git push origin fix/tck-specification-alignment`

## Expected Outcomes

### Tests That Should PASS:
- Tests that verify correct specification behavior
- Tests with proper workarounds in SUT

### Tests That Should FAIL/XFAIL:
- Agent Card field tests (SDK missing fields)
- Authentication tests (SDK doesn't enforce)
- Any test where SDK doesn't match spec

### Document All Failures:
Create `SDK_GAPS.md` listing every place SDK doesn't match specification:
```markdown
# SDK Gaps from A2A Specification

## Agent Card
- Missing field: protocolVersion (required by spec section X.Y)
- Missing field: id (required by spec section X.Y)

## Authentication
- No middleware support (spec section A.B requires auth enforcement)
```

## Risk Mitigation and Rollback

### Before Starting Any Phase

1. **Create a backup branch**:
   ```bash
   git checkout -b backup/pre-phase-X main
   ```

2. **Run and save baseline**:
   ```bash
   ./run_tck.py --sut-url http://localhost:9999 --verbose > baseline_phase_X.txt 2>&1
   ```

3. **Create restore point**:
   ```bash
   git add -A
   git commit -m "checkpoint: Before Phase X changes"
   git tag checkpoint-phase-X
   ```

### If Things Go Wrong

**Scenario**: Tests are failing in unexpected ways
```bash
# See what changed
git diff checkpoint-phase-X

# If needed, restore to checkpoint
git reset --hard checkpoint-phase-X
```

**Scenario**: SUT won't start after changes
1. Check the error message carefully
2. Most likely issues:
   - Import error: You removed a class still being imported
   - Missing method: You removed a workaround still being called
3. Temporary fix: Comment out the problematic line, add TODO

**Scenario**: Hundreds of tests failing after field name change
1. You probably missed updating the adapter
2. Check that `fix_message_parts_for_sdk` is being called
3. Verify the adapter is converting correctly

### Safe Testing Approach

Always test in this order:
1. **Unit test** the specific test file:
   ```bash
   ./run_tck.py --sut-url http://localhost:9999 --test-pattern "test_specific_file.py" -v
   ```

2. **Test related files**:
   ```bash
   ./run_tck.py --sut-url http://localhost:9999 --test-pattern "pytest tests/test_message*.py" -v
   ```

3. **Full test suite** only after above pass:
   ```bash
    ./run_tck.py --sut-url http://localhost:9999 -v
   ```

## Important Discovery Scenarios

### Scenario 1: TCK Tests Expect Fields Not in Specification
**Example**: Tests expect `protocolVersion` and `id` in Agent Card, but they're not in the schema

**What to do**:
1. Double-check the schema:
   ```bash
   jq '.definitions.AgentCard.properties | keys | map(select(. == "protocolVersion" or . == "id"))' a2a_schema.json
   ```
2. If fields are truly not in spec, the TCK tests are wrong
3. Update tests to NOT expect these fields:
   ```python
   def test_mandatory_fields_present(fetched_agent_card):
       """Test only fields required by specification"""
       # Remove protocolVersion and id from this list
       mandatory_fields = ["name", "description", "version", "url"]
   ```
4. Document this in SDK_GAPS.md as "TCK Bug" not "SDK Gap"

### Scenario 2: Both Spec and SDK Use Same Field, Tests Are Inconsistent
**Example**: Both use "kind" but some tests use "type"

**What to do**:
1. This is a test bug, not an SDK issue
2. Fix all tests to use the correct field
3. No adapter needed - just fix the tests
4. Document in FIX_SUMMARY.md under "Test Bugs Fixed"

### Scenario 3: Spec Says One Thing, SDK Does Another
**Example**: Spec requires field X, SDK doesn't have it

**What to do**:
1. Test for what spec requires
2. Use pytest.xfail when SDK doesn't comply
3. Keep SUT workaround only if needed for other tests
4. Document as legitimate SDK gap

## Decision Tree

```
Is the field/behavior in the JSON schema?
├─ NO: TCK test is wrong, fix the test
└─ YES: Does SDK implement it correctly?
    ├─ YES: Test should pass, any failure is a test bug
    └─ NO: Use pytest.xfail, document SDK gap
```

## Questions to Ask

If stuck, ask your senior developer:
1. "I can't find X in the specification, which section should I look in?"
2. "The specification says X but SDK does Y, should I test for X and expect failure?"
3. "Should I remove this SUT workaround even though tests will fail?"
4. "This change breaks 50+ tests, should I continue or try a different approach?"

## Priority Order (If Time Limited)

If you can't complete everything, focus on these in order:

### Must Do (Critical for Specification Compliance):
1. **Phase 1**: Field name standardization - This affects everything
2. **Phase 6**: Error code validation - Core to protocol compliance
3. **Task 2.1**: Document Agent Card requirements - Know what's correct

### Should Do (Improves Test Quality):
4. **Phase 2**: Agent Card alignment - Makes gaps visible
5. **Phase 5**: Capability checking - Ensures proper test skipping
6. **Phase 4**: History length parameter - Documents SDK bug

### Nice to Have (Cleanup):
7. **Phase 3**: Authentication improvements - Complex, lower impact

## Completion Criteria by Priority

**Minimum Viable Completion**:
- [ ] Field names consistent with spec
- [ ] All tests run (even if failing)
- [ ] SDK_GAPS.md lists critical issues

**Good Completion**:
- [ ] Above plus Agent Card tests aligned
- [ ] Capability-based skipping works
- [ ] Most SUT workarounds removed

**Excellent Completion**:
- [ ] All phases complete
- [ ] Comprehensive documentation
- [ ] Clean PR with full test results

## Testing Philosophy When SDK Doesn't Match Spec

### Use pytest Markers Appropriately

```python
# When SDK is completely missing a feature
@pytest.mark.xfail(reason="SDK doesn't implement Agent Card 'id' field - Spec section 2.1")
def test_agent_card_id_field():
    # Test the correct behavior
    pass

# When SDK implements incorrectly
@pytest.mark.xfail(reason="SDK uses 'kind' but spec requires 'type' - Spec section 3.2")
def test_message_part_type_field():
    # Test for spec-compliant 'type' field
    pass

# When we need SUT workaround for other tests to work
@pytest.mark.skip(reason="Requires SUT workaround for SDK limitation")
def test_that_needs_workaround():
    pass
```

### Decision Tree for Workarounds

```
Is the workaround required for OTHER tests to run?
├─ YES: Keep it, but document clearly
│   └─ Example: historyLength handling (needed for state transition tests)
└─ NO: Remove it
    └─ Example: Agent Card field injection (only needed for agent card tests)
```

## Troubleshooting Guide

### Problem: Tests fail after removing workaround
**Solution**: 
1. Check if other tests depend on this functionality
2. If yes, consider keeping minimal workaround
3. If no, use pytest.xfail with clear reason

### Problem: Can't find info in specification
**Solution**:
1. Use the search script:
   ```bash
   ./check_spec.sh "your search term"
   ```
2. Try related terms:
   ```bash
   # If looking for "message part"
   ./check_spec.sh "part"
   ./check_spec.sh "TextPart"
   ./check_spec.sh "message.*part"
   ```
3. Check the schema directly:
   ```bash
   # See all types containing "Part"
   jq '.definitions | keys | map(select(contains("Part")))' a2a_schema.json
   ```
4. Ask senior dev with specific section/term you're looking for

### Problem: Unclear if field name is type or kind
**Solution**:
1. **Check the JSON schema first** (this is definitive):
   ```bash
   # For TextPart
   jq '.definitions.TextPart.properties | keys' a2a_schema.json
   
   # For any discriminator field
   jq '.definitions.TextPart.properties | to_entries[] | select(.value.const != null)' a2a_schema.json
   ```
2. Look for examples in the spec:
   ```bash
   grep -B5 -A5 '"text"' A2A_SPECIFICATION.md | grep -E '"(type|kind)"'
   ```
3. The spec is truth - if schema shows `"kind"` but tests expect `"type"`, the schema wins

### Problem: Not sure what's required vs optional
**Solution**:
```bash
# For any type, check required fields
TYPE="Message"
jq --arg t "$TYPE" '.definitions[$t] | {
  required_fields: .required,
  all_fields: .properties | keys,
  optional_fields: (.properties | keys) - .required
}' a2a_schema.json
```

### Problem: Authentication tests are confusing
**Solution**:
1. Check if Agent Card has security fields:
   ```bash
   jq '.definitions.AgentCard.properties | keys | map(select(contains("security") or contains("auth")))' a2a_schema.json
   ```
2. Look for OpenAPI security definitions:
   ```bash
   jq '.definitions | keys | map(select(contains("Security")))' a2a_schema.json
   ```
3. The spec should indicate HTTP behavior (401/403) before JSON-RPC layer

### Problem: Don't know which error code to expect
**Solution**:
```bash
# List all errors with their codes
jq -r '.definitions | to_entries[] | 
  select(.key | endswith("Error")) | 
  "\(.value.properties.code.const): \(.key)"' a2a_schema.json | sort -n

# Find error by code
./check_error_code.sh -32001
```

## Final Validation Steps

### 1. Run Full Test Suite
```bash
# Run all tests and capture output
./run_tck.py --sut-url http://localhost:9999  -v > final_test_results.txt 2>&1

# Generate test report
./run_tck.py --sut-url http://localhost:9999 --report  

# Count xfail and failures
grep -c "XFAIL" final_test_results.txt
grep -c "FAILED" final_test_results.txt
```

### 2. Create Summary Document
Create `FIX_SUMMARY.md`:
```markdown
# TCK/SUT Fix Summary

## Changes Made
- Listed all changes...

## SDK Non-Compliance Issues Found
1. Agent Card missing required fields (protocolVersion, id)
2. Message parts field naming (type vs kind)
3. [List all findings]

## Test Statistics
- Total tests: X
- Passing: Y
- Expected failures (xfail): Z
- Unexpected failures: W

## Recommendations for SDK Team
[If we could fix SDK, what would we change]
```

### 3. Prepare Pull Request
```bash
# Ensure all changes committed
git add -A
git commit -m "fix(tck): Align tests with A2A specification"

# Create comprehensive PR description
git push origin fix/tck-specification-alignment
```

PR Description Template:
```markdown
## TCK and SUT Specification Alignment

### Summary
Aligned TCK tests and SUT implementation with A2A specification, removing workarounds where possible.

### Specification References
- Markdown: https://raw.githubusercontent.com/google-a2a/A2A/refs/heads/main/docs/specification.md
- JSON Schema: https://raw.githubusercontent.com/google-a2a/A2A/refs/heads/main/specification/json/a2a.json

### Key Findings
- Some TCK tests expected fields not in specification (protocolVersion, id)
- Test inconsistency: some used 'type' instead of 'kind' for message parts
- [Other findings from JSON schema analysis]

### Changes
- Fixed message part field naming consistency
- Removed Agent Card field injection workaround  
- Updated tests to expect specification-compliant behavior
- Documented all SDK gaps

### Test Results
- X tests now properly verify specification
- Y tests marked as xfail due to SDK limitations
- Z test bugs fixed (tested for non-spec fields)
- See SDK_GAPS.md for complete list

### Breaking Changes
- Some tests now fail when SDK doesn't match spec (this is intended)
- Removed tests for non-specification fields
```

## Final Checklist

- [ ] All specification findings documented in SPECIFICATION_FINDINGS.md
- [ ] All tests reference specification sections in docstrings
- [ ] SDK gaps documented in SDK_GAPS.md
- [ ] Minimal necessary SUT workarounds remain (with clear comments)
- [ ] Progress table complete with commit hashes
- [ ] Full test suite run and results analyzed
- [ ] FIX_SUMMARY.md created
- [ ] Pull request created with comprehensive description
- [ ] Team notified of significant findings

## Success Criteria

The implementation is successful when:
1. **Every test clearly indicates** whether it's testing specification compliance
2. **SDK limitations are visible** through xfail markers, not hidden by workarounds
3. **The TCK can be used** to validate other A2A implementations against the spec
4. **Documentation exists** for every decision made during implementation

## Quick Validation Checklist

Run these commands to verify your work:

```bash
# 1. Verify no test uses wrong field names
grep -r '"type".*:.*"text"' tests/ | grep -v "content-type" | wc -l  # Should be 0

# 2. Check all xfail markers have reasons
grep -r "pytest.xfail" tests/ | grep -v "reason="  # Should be empty

# 3. Verify agent card workaround is removed
grep -r "TckA2AStarletteApplication" python-sut/  # Should be empty

# 4. Count SDK gaps documented
grep -c "^-" SDK_GAPS.md  # Should match number of xfail tests

# 5. Run the validation script one more time
python3 validate_findings.py
```

## Remember

- The JSON schema is your source of truth
- When confused, run: `jq '.definitions.TypeYouAreLookingFor' a2a_schema.json`
- Document everything - future developers will thank you
- It's okay if tests fail - that's what a TCK is supposed to do when implementations don't match the spec!