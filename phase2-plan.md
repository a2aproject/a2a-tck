# TCK Mandatory/Optional Test Separation Plan - Phase 2

## Overview

This plan guides the separation of TCK tests into mandatory and optional categories based on the A2A specification requirements. The goal is to create a TCK that can validate ANY A2A SDK implementation, clearly distinguishing between specification violations that should block SDK compliance (mandatory) versus nice-to-have features (optional).

## Understanding A2A Specification Requirements

The A2A specification uses RFC 2119 keywords:
- **MUST/SHALL/REQUIRED** = Mandatory for compliance
- **SHOULD/RECOMMENDED** = Optional but strongly encouraged  
- **MAY/OPTIONAL** = Truly optional features

When in doubt: **JSON Schema "required" arrays are definitive for mandatory fields**

### Quick Reference Commands
```bash
# Find all MUST requirements in specification
grep -n "MUST\|SHALL" A2A_SPECIFICATION.md | grep -v "MUST NOT" > mandatory_requirements.txt

# Find all SHOULD requirements
grep -n "SHOULD" A2A_SPECIFICATION.md | grep -v "SHOULD NOT" > optional_requirements.txt

# Check if a field is required in JSON schema
jq '.definitions.AgentCard.required' a2a_schema.json

# Find all required fields for any type
TYPE="Message"  # Change this
jq --arg t "$TYPE" '.definitions[$t].required // []' a2a_schema.json
```

## Guiding Principles

1. **SDK Purity**: Remove ALL SUT workarounds - test only what SDK provides
2. **Clear Categories**: Every test must be clearly marked as mandatory or optional
3. **Specification Truth**: JSON Schema + RFC 2119 keywords determine categorization
4. **Fail Fast**: Mandatory test failures should immediately indicate non-compliance
5. **Progressive Enhancement**: Optional tests show quality/completeness levels
6. **Documentation**: Every test must cite the specification section it validates

## Pre-Work Setup

### Step 1: Create Specification Analysis

```bash
# Create new branch
git checkout -b feat/mandatory-optional-test-separation

# Create analysis directory
mkdir -p spec_analysis
cd spec_analysis

# Download fresh copies
curl -o A2A_SPECIFICATION.md https://raw.githubusercontent.com/google-a2a/A2A/refs/heads/main/docs/specification.md
curl -o a2a_schema.json https://raw.githubusercontent.com/google-a2a/A2A/refs/heads/main/specification/json/a2a.json

# Create requirement extractor
cat > extract_requirements.py << 'EOF'
#!/usr/bin/env python3
import json
import re

print("=== A2A Specification Requirement Analysis ===\n")

# Load schema
with open('a2a_schema.json', 'r') as f:
    schema = json.load(f)

# Load specification
with open('A2A_SPECIFICATION.md', 'r') as f:
    spec_text = f.read()

# Extract MUST/SHALL requirements
must_pattern = r'(.*?)(MUST|SHALL|REQUIRED)(?! NOT)(.*?)(?:\.|$)'
must_matches = re.findall(must_pattern, spec_text, re.MULTILINE | re.IGNORECASE)

print("## Mandatory Requirements (MUST/SHALL/REQUIRED)")
for i, match in enumerate(must_matches[:20], 1):  # First 20
    context = f"{match[0][-50:]}{match[1]}{match[2][:50]}"
    print(f"{i}. ...{context}...")

# Extract SHOULD requirements  
should_pattern = r'(.*?)(SHOULD|RECOMMENDED)(?! NOT)(.*?)(?:\.|$)'
should_matches = re.findall(should_pattern, spec_text, re.MULTILINE | re.IGNORECASE)

print("\n## Optional Strong Requirements (SHOULD/RECOMMENDED)")
for i, match in enumerate(should_matches[:20], 1):  # First 20
    context = f"{match[0][-50:]}{match[1]}{match[2][:50]}"
    print(f"{i}. ...{context}...")

# Analyze required fields from schema
print("\n## Required Fields Analysis")
for type_name in ['AgentCard', 'Message', 'Task', 'Part']:
    if type_name in schema['definitions']:
        required = schema['definitions'][type_name].get('required', [])
        print(f"\n{type_name}: {required}")

EOF
chmod +x extract_requirements.py
python3 extract_requirements.py > REQUIREMENT_ANALYSIS.md
```

### Step 2: Create Test Categorization Framework

```bash
# Create the categorization script
cat > categorize_tests.py << 'EOF'
#!/usr/bin/env python3
import os
import ast
import json

class TestCategorizer(ast.NodeVisitor):
    def __init__(self):
        self.tests = []
        
    def visit_FunctionDef(self, node):
        if node.name.startswith('test_'):
            # Extract test info
            docstring = ast.get_docstring(node) or ""
            has_core_mark = any(
                decorator.id == 'mark' and 
                hasattr(decorator, 'attr') and 
                decorator.attr == 'core'
                for decorator in node.decorator_list
                if hasattr(decorator, 'id')
            )
            
            self.tests.append({
                'name': node.name,
                'file': self.current_file,
                'has_docstring': bool(docstring),
                'mentions_spec': 'specification' in docstring.lower() or 'spec' in docstring.lower(),
                'has_must': 'MUST' in docstring,
                'has_should': 'SHOULD' in docstring,
                'is_core': has_core_mark,
                'docstring_preview': docstring[:100] + '...' if len(docstring) > 100 else docstring
            })
            
        self.generic_visit(node)

# Process all test files
categorizer = TestCategorizer()
test_dir = '../tests'

all_tests = []
for filename in os.listdir(test_dir):
    if filename.startswith('test_') and filename.endswith('.py'):
        filepath = os.path.join(test_dir, filename)
        with open(filepath, 'r') as f:
            tree = ast.parse(f.read())
            categorizer.current_file = filename
            categorizer.visit(tree)

# Generate report
with open('TEST_CATEGORIZATION.md', 'w') as f:
    f.write("# Current Test Categorization Status\n\n")
    
    f.write("## Summary\n")
    f.write(f"- Total tests: {len(categorizer.tests)}\n")
    f.write(f"- Core tests: {sum(1 for t in categorizer.tests if t['is_core'])}\n")
    f.write(f"- Tests with MUST: {sum(1 for t in categorizer.tests if t['has_must'])}\n")
    f.write(f"- Tests with SHOULD: {sum(1 for t in categorizer.tests if t['has_should'])}\n")
    
    f.write("\n## Tests Needing Categorization\n")
    for test in categorizer.tests:
        if not test['has_must'] and not test['has_should']:
            f.write(f"- {test['file']}: {test['name']}\n")

EOF
chmod +x categorize_tests.py
python3 categorize_tests.py
```

## Phase 1: Remove All SUT Workarounds

### Goal
Ensure TCK tests ONLY what the SDK provides, with no cheating via SUT modifications.

### Task 1.1: Audit Current Workarounds
```bash
# Find all SUT customizations
grep -r "workaround\|TckCore\|custom" ../python-sut/ > sut_workarounds.txt

# Document each workaround
cat > WORKAROUND_AUDIT.md << 'EOF'
# SUT Workaround Audit

## Found Workarounds

### 1. TckCoreRequestHandler (custom_request_handler.py)
- **Purpose**: Implements historyLength parameter
- **Why Needed**: SDK DefaultRequestHandler ignores it
- **Impact**: Makes test_task_history_length pass when SDK fails
- **Action**: REMOVE - Let test fail to show SDK gap

### 2. Authentication Middleware (ALREADY REMOVED)
- **Status**: Already removed in Phase 1
- **Impact**: Tests properly skip/fail

### 3. Agent Card Field Injection (ALREADY REMOVED)  
- **Status**: Already removed in Phase 1
- **Impact**: Tests properly validate spec fields
EOF
```

### Task 1.2: Remove TckCoreRequestHandler
**Goal**: Use only SDK's DefaultRequestHandler

```python
# In python-sut/tck_core_agent/__main__.py
# CHANGE FROM:
from custom_request_handler import TckCoreRequestHandler
app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=TckCoreRequestHandler(...),  # REMOVE THIS
)

# CHANGE TO:
from a2a.server.request_handlers import DefaultRequestHandler
app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=DefaultRequestHandler(...),  # USE SDK DEFAULT
)
```

### Task 1.3: Update Affected Tests
```python
# In tests/test_state_transitions.py
def test_task_history_length(sut_client, text_message_params):
    """
    MANDATORY: A2A Specification Section 7.3 - historyLength parameter
    
    The specification states tasks/get MUST support historyLength parameter.
    SDK DefaultRequestHandler fails this requirement.
    """
    # ... existing test code ...
    
    # This will now FAIL with SDK DefaultRequestHandler
    # Mark as mandatory failure
```

**Verification**:
- [ ] All SUT customizations removed
- [ ] SUT uses only SDK-provided components
- [ ] Tests that were passing due to workarounds now fail

## Phase 2: Categorize Tests by Specification Requirements

### Task 2.1: Create Mandatory Test Markers
```python
# Create tests/markers.py
"""
Test markers for A2A TCK compliance levels.
"""
import pytest

# Mandatory markers - MUST requirements
mandatory = pytest.mark.mandatory  # Blocks SDK compliance
mandatory_jsonrpc = pytest.mark.mandatory_jsonrpc  # JSON-RPC 2.0 compliance
mandatory_protocol = pytest.mark.mandatory_protocol  # A2A protocol requirements

# Optional markers - SHOULD/MAY requirements  
optional_recommended = pytest.mark.optional_recommended  # SHOULD requirements
optional_feature = pytest.mark.optional_feature  # MAY requirements
optional_capability = pytest.mark.optional_capability  # Capability-dependent

# Quality markers
quality_basic = pytest.mark.quality_basic  # Basic implementation quality
quality_production = pytest.mark.quality_production  # Production-ready quality
quality_advanced = pytest.mark.quality_advanced  # Advanced features
```

### Task 2.2: Analyze Each Test File
Create `TEST_CLASSIFICATION.md`:

```markdown
# Test Classification by A2A Specification

## Mandatory Tests (MUST/SHALL Requirements)

### test_json_rpc_compliance.py
- ✅ test_rejects_malformed_json - JSON-RPC 2.0 §4.2 MUST parse valid JSON
- ✅ test_rejects_invalid_json_rpc_requests - JSON-RPC 2.0 §4.1 MUST have required fields
- ✅ test_rejects_unknown_method - JSON-RPC 2.0 §4.3 MUST return -32601
- ✅ test_rejects_invalid_params - JSON-RPC 2.0 §4.3 MUST return -32602

### test_agent_card.py  
- ✅ test_mandatory_fields_present - A2A §2.1 AgentCard MUST have required fields
- ✅ test_mandatory_field_types - A2A §2.1 Fields MUST have correct types
- ❌ test_capabilities_structure - Optional (capabilities field itself is required but contents are optional)
- ❌ test_authentication_structure - Optional (authentication schemes are MAY requirements)

### test_message_send_method.py
- ✅ test_message_send_valid_text - A2A §5.1 MUST support message/send with text
- ✅ test_message_send_invalid_params - A2A §5.1 MUST validate required fields
- ❌ test_message_send_valid_file_part - Optional (file support is capability-based)
- ❌ test_message_send_valid_data_part - Optional (data support is capability-based)

### test_tasks_*.py
- ✅ test_tasks_get_valid - A2A §7.3 MUST support tasks/get
- ✅ test_tasks_get_nonexistent - A2A §7.3 MUST return TaskNotFoundError
- ✅ test_task_history_length - A2A §7.3 MUST support historyLength parameter
- ✅ test_tasks_cancel_valid - A2A §7.4 MUST support tasks/cancel
- ✅ test_tasks_cancel_nonexistent - A2A §7.4 MUST return TaskNotFoundError

## Optional Tests

### Capability-Dependent (MUST work IF capability declared)
- test_message_stream_* - Requires streaming: true
- test_push_notification_* - Requires pushNotifications: true  
- test_message_send_valid_file_part - Requires file modality
- test_message_send_valid_data_part - Requires data modality

### Quality/Resilience Tests
- test_concurrent_* - Quality: handles concurrent requests
- test_edge_cases_* - Quality: handles edge cases gracefully
- test_resilience_* - Quality: recovers from errors
```

### Task 2.3: Update Test Decorators

For each test file, update decorators based on classification:

```python
# Example: test_json_rpc_compliance.py
import pytest
from tests.markers import mandatory_jsonrpc

@mandatory_jsonrpc
def test_rejects_malformed_json(sut_client):
    """
    MANDATORY: JSON-RPC 2.0 Specification §4.2
    
    The server MUST reject syntactically invalid JSON with error code -32700.
    This is a hard requirement for JSON-RPC compliance.
    """
    # ... existing test code ...

# Example: test_streaming_methods.py  
from tests.markers import optional_capability

@optional_capability
def test_message_stream_basic(async_http_client, agent_card_data):
    """
    OPTIONAL CAPABILITY: A2A Specification §8.1 - Streaming
    
    IF the agent declares streaming: true in capabilities,
    THEN it MUST support message/stream method.
    
    This test is MANDATORY if streaming capability is declared,
    SKIPPED if capability is not declared.
    """
    if not has_streaming_support(agent_card_data):
        pytest.skip("Streaming capability not declared - this is allowed")
    # ... rest of test ...
```

## Phase 3: Reorganize Test Suite Structure

### Task 3.1: Create Test Organization
```bash
# Create new test structure
mkdir -p tests/mandatory
mkdir -p tests/mandatory/jsonrpc
mkdir -p tests/mandatory/protocol  
mkdir -p tests/optional/capabilities
mkdir -p tests/optional/quality
mkdir -p tests/optional/features

# Create __init__.py files
touch tests/mandatory/__init__.py
touch tests/mandatory/jsonrpc/__init__.py
touch tests/mandatory/protocol/__init__.py
touch tests/optional/__init__.py
touch tests/optional/capabilities/__init__.py
touch tests/optional/quality/__init__.py
touch tests/optional/features/__init__.py
```

### Task 3.2: Move Tests to Appropriate Directories

Create move script:
```python
# reorganize_tests.py
import os
import shutil
import ast

# Test classification based on our analysis
MANDATORY_JSONRPC = [
    'test_rejects_malformed_json',
    'test_rejects_invalid_json_rpc_requests', 
    'test_rejects_unknown_method',
    'test_rejects_invalid_params',
]

MANDATORY_PROTOCOL = [
    'test_mandatory_fields_present',
    'test_mandatory_field_types',
    'test_message_send_valid_text',
    'test_message_send_invalid_params',
    'test_tasks_get_valid',
    'test_tasks_get_nonexistent',
    'test_task_history_length',
    'test_tasks_cancel_valid',
    'test_tasks_cancel_nonexistent',
]

OPTIONAL_CAPABILITIES = [
    'test_message_stream_basic',
    'test_message_stream_invalid_params',
    'test_tasks_resubscribe',
    'test_push_notification_config',
    'test_message_send_valid_file_part',
    'test_message_send_valid_data_part',
]

OPTIONAL_QUALITY = [
    'test_parallel_requests',
    'test_concurrent_operations_same_task',
    'test_very_long_string',
    'test_boundary_values',
    'test_unicode_and_special_chars',
]

# ... implement file moving logic ...
```

### Task 3.3: Create Test Suite Runners

```python
# Create run_mandatory.py
"""Run only mandatory tests - SDK must pass ALL of these."""
import subprocess
import sys

def run_mandatory_tests():
    """Run mandatory test suite."""
    print("=" * 60)
    print("A2A TCK MANDATORY TEST SUITE")
    print("SDK MUST pass ALL of these tests for compliance")
    print("=" * 60)
    
    result = subprocess.run([
        sys.executable, "-m", "pytest",
        "tests/mandatory/",
        "-v",
        "--tb=short",
        "-m", "not skip"
    ])
    
    if result.returncode != 0:
        print("\n❌ SDK FAILED MANDATORY TESTS - NOT A2A COMPLIANT")
        sys.exit(1)
    else:
        print("\n✅ SDK PASSED ALL MANDATORY TESTS")
        sys.exit(0)

if __name__ == "__main__":
    run_mandatory_tests()
```

## Phase 4: Implement Capability-Based Test Logic

### Task 4.1: Create Capability Analyzer
```python
# Create tests/capability_validator.py
"""
Capability-based test validation for A2A TCK.
"""
from typing import Dict, List, Set
import pytest

class CapabilityValidator:
    """Validates that declared capabilities are properly implemented."""
    
    def __init__(self, agent_card: Dict):
        self.agent_card = agent_card
        self.capabilities = agent_card.get('capabilities', {})
        
    def get_required_tests_for_capability(self, capability: str) -> List[str]:
        """Return test names that MUST pass if capability is declared."""
        capability_tests = {
            'streaming': [
                'test_message_stream_basic',
                'test_message_stream_invalid_params',
                'test_tasks_resubscribe',
                'test_tasks_resubscribe_nonexistent'
            ],
            'pushNotifications': [
                'test_set_push_notification_config',
                'test_get_push_notification_config',
                'test_push_notification_nonexistent'
            ]
        }
        return capability_tests.get(capability, [])
    
    def validate_modality_support(self, modality: str) -> bool:
        """Check if a modality is supported."""
        # Check defaultInputModes/defaultOutputModes
        input_modes = self.agent_card.get('defaultInputModes', [])
        output_modes = self.agent_card.get('defaultOutputModes', [])
        
        return modality in input_modes or modality in output_modes
```

### Task 4.2: Update Capability Tests
```python
# Example update for streaming tests
@pytest.mark.optional_capability  
def test_message_stream_basic(async_http_client, agent_card_data):
    """
    CONDITIONAL MANDATORY: A2A §8.1 - Streaming Support
    
    Status: MANDATORY if capabilities.streaming = true
            SKIP if capabilities.streaming = false/missing
            
    The A2A specification states that IF an agent declares
    streaming capability, it MUST implement message/stream.
    """
    validator = CapabilityValidator(agent_card_data)
    
    if not validator.capabilities.get('streaming'):
        pytest.skip("Streaming not declared - test not applicable")
        
    # If we get here, streaming is declared so test MUST pass
    # ... rest of test implementation ...
    
    # If this test fails, it's a MANDATORY failure because
    # the capability was declared but not properly implemented
```

## Phase 5: Create Compliance Report Generator

### Task 5.1: Build Report Generator
```python
# Create generate_compliance_report.py
"""
Generate A2A compliance report for SDK testing.
"""
import json
from datetime import datetime
from typing import Dict, List

class ComplianceReportGenerator:
    def __init__(self, test_results: Dict):
        self.test_results = test_results
        self.timestamp = datetime.utcnow().isoformat()
        
    def generate_report(self) -> Dict:
        """Generate comprehensive compliance report."""
        
        # Categorize results
        mandatory_passed = []
        mandatory_failed = []
        optional_passed = []
        optional_failed = []
        capability_issues = []
        
        for test_name, result in self.test_results.items():
            if result['category'] == 'mandatory':
                if result['passed']:
                    mandatory_passed.append(test_name)
                else:
                    mandatory_failed.append(test_name)
            # ... categorize other tests
            
        # Calculate compliance
        mandatory_compliance = len(mandatory_passed) / (len(mandatory_passed) + len(mandatory_failed)) * 100
        
        return {
            'timestamp': self.timestamp,
            'summary': {
                'compliant': len(mandatory_failed) == 0,
                'mandatory_compliance_percent': mandatory_compliance,
                'mandatory_passed': len(mandatory_passed),
                'mandatory_failed': len(mandatory_failed),
                'optional_passed': len(optional_passed),
                'optional_failed': len(optional_failed),
            },
            'mandatory_failures': [
                {
                    'test': test,
                    'specification_reference': self.get_spec_reference(test),
                    'impact': 'SDK is NOT A2A compliant'
                }
                for test in mandatory_failed
            ],
            'recommendations': self.generate_recommendations(mandatory_failed, capability_issues)
        }
```

### Task 5.2: Create Compliance Levels
```python
# Create compliance_levels.py
"""
A2A Compliance Levels for SDK Validation.
"""

COMPLIANCE_LEVELS = {
    'MANDATORY': {
        'description': 'Minimum requirements for A2A compliance',
        'requirements': [
            'All JSON-RPC 2.0 mandatory tests pass',
            'All A2A protocol mandatory tests pass',
            'Agent Card has all required fields',
            'Core methods (message/send, tasks/get, tasks/cancel) work'
        ],
        'badge': '🔴 A2A Core Compliant'
    },
    'RECOMMENDED': {
        'description': 'Includes SHOULD requirements from specification',
        'requirements': [
            'All MANDATORY requirements met',
            'Implements proper error messages',
            'Supports historyLength parameter correctly',
            'Handles edge cases gracefully'
        ],
        'badge': '🟡 A2A Recommended Compliant'
    },
    'FULL_FEATURED': {
        'description': 'Implements optional capabilities correctly',
        'requirements': [
            'All RECOMMENDED requirements met',
            'Declared capabilities work correctly',
            'No capability is declared but unimplemented',
            'Quality tests pass (concurrency, resilience)'
        ],
        'badge': '🟢 A2A Fully Compliant'
    }
}
```

## Phase 6: Documentation and Final Cleanup

### Task 6.1: Create SDK Validation Guide
```markdown
# A2A SDK Validation Guide

## Quick Start

### 1. Test ONLY Mandatory Requirements
```bash
./run_mandatory.py --sut-url http://localhost:8000
```

If this fails, the SDK is NOT A2A compliant.

### 2. Test Full Suite with Report
```bash
./run_tck.py --sut-url http://localhost:8000 --generate-report
```

This generates `compliance_report.json` with detailed results.

## Understanding Results

### Mandatory Failures = Non-Compliant
Any failure in `tests/mandatory/` means the SDK does not meet A2A specification requirements.

### Capability Failures = Incorrect Declaration  
If a capability is declared in Agent Card but tests fail, the implementation is incorrect.

### Optional Failures = Quality Issues
Failures in optional tests indicate areas for improvement but don't block compliance.

## Common Issues

### "test_task_history_length" fails
- **Issue**: SDK doesn't implement historyLength parameter
- **Spec**: A2A §7.3 states tasks/get MUST support historyLength
- **Fix**: SDK must implement this in DefaultRequestHandler

### "test_mandatory_fields_present" fails  
- **Issue**: Agent Card missing required fields
- **Spec**: A2A §2.1 lists required fields
- **Fix**: Ensure all required fields are present
```

### Task 6.2: Update Test Documentation
For EVERY test, add clear documentation:

```python
def test_example():
    """
    Category: MANDATORY
    Specification: A2A §X.Y / JSON-RPC 2.0 §Z
    Requirement: "Servers MUST..." (exact quote)
    
    Failure Impact: SDK is not A2A compliant
    
    Test validates that...
    """
```

### Task 6.3: Create Migration Guide
```markdown
# Migrating from Phase 1 TCK

## What Changed

1. **No More Workarounds**: SUT uses pure SDK components
2. **Clear Categories**: Tests marked as mandatory/optional
3. **Proper Failures**: Tests fail when SDK doesn't comply
4. **Capability Logic**: Tests skip appropriately

## For SDK Developers

### Mandatory Fixes Required
- [ ] Implement historyLength in DefaultRequestHandler  
- [ ] Ensure Agent Card has all required fields
- [ ] Fix JSON-RPC compliance issues

### Optional Improvements
- [ ] Implement streaming if you declare the capability
- [ ] Add authentication support
- [ ] Improve error messages
```

## Progress Tracking Table

| Phase | Task | Description | Status | Commit |
|-------|------|-------------|--------|--------|
| 1 | 1.1 | Audit SUT Workarounds | ⬜ | |
| 1 | 1.2 | Remove Custom Handlers | ⬜ | |
| 1 | 1.3 | Update Affected Tests | ⬜ | |
| 2 | 2.1 | Create Test Markers | ⬜ | |
| 2 | 2.2 | Classify All Tests | ⬜ | |
| 2 | 2.3 | Update Decorators | ⬜ | |
| 3 | 3.1 | Create New Structure | ⬜ | |
| 3 | 3.2 | Move Tests | ⬜ | |
| 3 | 3.3 | Create Runners | ⬜ | |
| 4 | 4.1 | Capability Validator | ⬜ | |
| 4 | 4.2 | Update Capability Tests | ⬜ | |
| 5 | 5.1 | Report Generator | ⬜ | |
| 5 | 5.2 | Compliance Levels | ⬜ | |
| 6 | 6.1 | SDK Validation Guide | ⬜ | |
| 6 | 6.2 | Test Documentation | ⬜ | |
| 6 | 6.3 | Migration Guide | ⬜ | |

## Success Criteria

The implementation is successful when:

1. **Zero SUT Workarounds**: SUT only uses SDK components
2. **Clear Test Categories**: Every test clearly marked as mandatory/optional
3. **Proper Failure Modes**: Mandatory failures block compliance
4. **Capability Validation**: Declared capabilities properly tested
5. **Actionable Reports**: Clear guidance on what to fix
6. **Any SDK Testable**: TCK works for any A2A SDK implementation

## Daily Workflow

Same as Phase 1 plan:
1. Start with fresh branch
2. Complete one task at a time
3. Run tests after each change
4. Document in WORKING_NOTES_PHASE2.md
5. Commit with descriptive messages

## Risk Mitigation

### Risk: Too Many Tests Become Mandatory
**Mitigation**: 
- Strictly follow RFC 2119 keywords
- When unclear, check JSON schema "required" arrays
- Default to optional unless specification says MUST

### Risk: Breaking Existing Test Suite  
**Mitigation**:
- Keep original tests during migration
- Run parallel test suites during transition
- Only delete old tests after new ones verified

### Risk: SDK Developers Confused by Categories
**Mitigation**:
- Crystal clear documentation
- Specification quotes in every test
- Comprehensive compliance report

## Remember

- The JSON schema "required" arrays are truth for mandatory fields
- RFC 2119 keywords (MUST/SHOULD/MAY) determine test categories  
- Remove ALL workarounds - test pure SDK behavior
- Capability tests: SKIP if not declared, FAIL if declared but broken
- Document everything - future developers and SDK authors will thank you!