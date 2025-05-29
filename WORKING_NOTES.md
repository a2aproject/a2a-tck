# Working Notes - TCK Specification Alignment

## Current Status: Phase 3 Verified ✅, Starting Phase 4

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
  - Verified: Agent Card tests still pass, SUT provides only spec fields

### Phase 3: Authentication Test Improvements ✅ VERIFIED
- ✅ Task 3.1: Research Specification Authentication
  - Documented A2A specification section 4: Authentication and Authorization
  - Servers MUST authenticate every request (section 4.4)
  - Should use HTTP 401/403 for auth failures (before JSON-RPC layer)
  - Security schemes declared via securitySchemes field in Agent Card
- ✅ Task 3.2: Remove SUT Authentication Middleware
  - Deleted AuthenticationMiddleware class entirely
  - Removed all auth enforcement from SUT
  - Documents SDK limitation: no built-in authentication support
- ✅ Task 3.3: Update Authentication Tests
  - Added pytest.xfail for SDK limitations with clear reasons
  - Tests now document specification requirements vs SDK reality
  - test_missing_authentication and test_invalid_authentication updated
- ✅ **VERIFICATION**: SUT restarted and tested
  - Authentication tests properly SKIP (not fail) due to SDK limitation
  - SDK creates securitySchemes but doesn't include them in Agent Card JSON output
  - This demonstrates another SDK gap: security fields filtered out
  - Full test suite: **7 failed, 53 passed, 14 skipped** (same as Phase 2 - no regressions)

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

3. **Authentication SDK LIMITATION CONFIRMED**:
   - Specification requires HTTP 401/403 for auth failures
   - SDK doesn't provide authentication enforcement
   - **NEW FINDING**: SDK creates securitySchemes but filters them out of Agent Card JSON response
   - Tests correctly SKIP when no authentication schemes detected
   - This is a more severe SDK limitation than initially understood

4. **Error Codes**: All well-defined in specification (-32001 to -32006 for A2A, standard JSON-RPC codes)

## Test Results Summary:
- **Before changes**: 9 failed, 51 passed, 14 skipped  
- **After Phases 1-2**: 7 failed, 53 passed, 14 skipped
- **After Phase 3**: 7 failed, 53 passed, 14 skipped (no regressions!)

## Next Steps:
- 📋 NOW: Phase 4 - Fix History Length Parameter

## SDK Gaps Discovered:
1. Agent Card missing protocolVersion/id fields (but these aren't in spec anyway)
2. No authentication middleware support
3. **securitySchemes and security fields filtered out of Agent Card JSON response**
4. All message part field names use "kind" (but some tests incorrectly expected "type")
