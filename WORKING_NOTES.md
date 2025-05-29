# Working Notes - TCK Specification Alignment

## Current Status: Pre-Work Setup Complete ✅

### Setup Completed:
- ✅ Created branch: fix/tck-specification-alignment
- ✅ Downloaded A2A_SPECIFICATION.md
- ✅ Downloaded a2a_schema.json
- ✅ Created check_spec.sh script
- ✅ Created validate_findings.py script
- ✅ Created schema_helpers.md
- ✅ Created SPECIFICATION_FINDINGS.md

### Key Findings from Validation:

1. **Message Part Field Name Issue CONFIRMED**:
   - Specification uses "kind" field (not "type")
   - Found 17 instances in 7 test files using wrong "type" field:
     - tests/test_concurrency.py
     - tests/test_edge_cases.py
     - tests/test_invalid_business_logic.py
     - tests/test_protocol_violations.py
     - tests/test_resilience.py
     - tests/test_streaming_methods.py
     - tests/test_tasks_get_method.py

2. **Agent Card Fields**:
   - Required: capabilities, defaultInputModes, defaultOutputModes, description, name, skills, url, version
   - Optional: documentationUrl, provider, security, securitySchemes, supportsAuthenticatedExtendedCard
   - NOT in spec: protocolVersion, id (tests expecting these are wrong)

3. **Error Codes**: All well-defined in specification (-32001 to -32006 for A2A, standard JSON-RPC codes)

## Next Steps:
- ⏳ WAITING: SUT to be started on http://localhost:9999
- 📋 TODO: Run baseline tests once SUT is running
- 📋 TODO: Start Phase 1 - Field Name Standardization
