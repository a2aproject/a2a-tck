# Working Notes - TCK Specification Alignment

## Current Status: Phase 2 Complete ✅

### Setup Completed:
- ✅ Created branch: fix/tck-specification-alignment
- ✅ Downloaded A2A_SPECIFICATION.md
- ✅ Downloaded a2a_schema.json
- ✅ Created check_spec.sh script
- ✅ Created validate_findings.py script
- ✅ Created schema_helpers.md
- ✅ Created SPECIFICATION_FINDINGS.md

### Phase 1: Field Name Standardization ✅
- ✅ Task 1.1: Audit Message Part Field Usage
- ✅ Task 1.2: Create Field Name Compatibility Layer (spec_adapter.py)
- ✅ Task 1.3: Update All Test Fixtures
  - Fixed 17 instances in 7 test files: "type" → "kind"
  - Verified fixes work (response shows correct 'kind': 'text')
  - Commit: 3906949

### Phase 2: Agent Card Specification Alignment ✅
- ✅ Task 2.1: Document Agent Card Requirements
  - Created check_agent_field.sh script
  - Confirmed protocolVersion and id are NOT in specification
  - Required fields: capabilities, defaultInputModes, defaultOutputModes, description, name, skills, url, version
- ✅ Task 2.2: Update Agent Card Tests
  - Fixed test_mandatory_fields_present() to use specification fields
  - Fixed test_mandatory_field_types() to check correct types
  - Agent Card tests now PASS (was failing before)
  - Commit: 6c4b82e
- ✅ Task 2.3: Remove SUT Agent Card Workaround
  - Removed TckA2AStarletteApplication custom class
  - Changed to use standard A2AStarletteApplication
  - No more injection of protocolVersion/id fields
  - SUT restart required to test

### Key Findings from Validation:

1. **Message Part Field Name Issue FIXED**:
   - Specification uses "kind" field (not "type")
   - Found 17 instances in 7 test files using wrong "type" field:
     - tests/test_concurrency.py ✅
     - tests/test_edge_cases.py ✅
     - tests/test_invalid_business_logic.py ✅
     - tests/test_protocol_violations.py ✅
     - tests/test_resilience.py ✅
     - tests/test_streaming_methods.py ✅
     - tests/test_tasks_get_method.py ✅

2. **Agent Card Fields FIXED**:
   - Required: capabilities, defaultInputModes, defaultOutputModes, description, name, skills, url, version
   - Optional: documentationUrl, provider, security, securitySchemes, supportsAuthenticatedExtendedCard
   - NOT in spec: protocolVersion, id (tests updated to not expect these)
   - SUT workaround removed

3. **Error Codes**: All well-defined in specification (-32001 to -32006 for A2A, standard JSON-RPC codes)

## Next Steps:
- ⏳ WAITING: SUT restart to test Task 2.3 changes
- 📋 TODO: Phase 3 - Authentication Test Improvements
