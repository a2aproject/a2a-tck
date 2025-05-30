# A2A SDK Validation Guide

This guide helps SDK developers understand how to use the A2A Technology Compatibility Kit (TCK) to validate their implementations and achieve A2A specification compliance.

## Quick Start

### 1. Test ONLY Mandatory Requirements
```bash
./run_tck.py --sut-url http://localhost:8000 --category mandatory
```

**Result**: If this fails, your SDK is **NOT A2A compliant**. Fix all mandatory failures before proceeding.

### 2. Test Declared Capabilities
```bash
./run_tck.py --sut-url http://localhost:8000 --category capabilities
```

**Result**: If this fails, you have **false advertising** - capabilities declared in Agent Card but not properly implemented.

### 3. Assess Production Readiness
```bash
./run_tck.py --sut-url http://localhost:8000 --category quality
```

**Result**: Quality issues don't block compliance but indicate areas for production improvement.

### 4. Check Feature Completeness
```bash
./run_tck.py --sut-url http://localhost:8000 --category features
```

**Result**: Purely informational - shows optional feature implementation status.

### 5. Generate Comprehensive Report
```bash
./run_tck.py --sut-url http://localhost:8000 --category all --compliance-report compliance.json
```

**Result**: Complete assessment with compliance level, scores, and actionable recommendations.

## Understanding Test Categories

### 🔴 **MANDATORY TESTS** (Must Pass for Compliance)
- **What**: JSON-RPC 2.0 + A2A protocol core requirements
- **When to Run**: First step in validation
- **Impact**: Failure = NOT A2A compliant
- **Files**: `tests/mandatory/jsonrpc/`, `tests/mandatory/protocol/`
- **Specification**: MUST/SHALL requirements from A2A spec

**Common Failures**:
- `test_mandatory_fields_present` → Agent Card missing required fields
- `test_message_send_valid_text` → message/send method not working
- `test_tasks_get_valid` → tasks/get method not working
- `test_task_history_length` → historyLength parameter not implemented

### 🔄 **CAPABILITY TESTS** (Conditional Mandatory)
- **What**: Validates declared capabilities work correctly
- **When to Run**: After mandatory tests pass
- **Impact**: Failure = False advertising
- **Files**: `tests/optional/capabilities/`
- **Logic**: 
  - If capability NOT declared → Tests are SKIPPED (allowed)
  - If capability IS declared → Tests are MANDATORY (must pass)

**Test Behavior**:
- `streaming: false` → Streaming tests are skipped ✅
- `streaming: true` → Streaming tests must pass ❌ if they fail
- `pushNotifications: false` → Push notification tests are skipped ✅
- `pushNotifications: true` → Push notification tests must pass ❌ if they fail

### 🛡️ **QUALITY TESTS** (Production Readiness)
- **What**: Concurrency, edge cases, resilience validation
- **When to Run**: Before production deployment
- **Impact**: Never blocks compliance, but indicates production issues
- **Files**: `tests/optional/quality/`
- **Markers**: `@quality_basic`, `@quality_production`

**Quality Areas**:
- Concurrent request handling
- Edge case robustness
- Unicode and special character support
- Boundary value handling
- Error recovery

### 🎨 **FEATURE TESTS** (Optional Implementation)
- **What**: Optional behaviors and convenience features
- **When to Run**: For completeness assessment
- **Impact**: Purely informational
- **Files**: `tests/optional/features/`
- **Markers**: `@optional_feature`

## Compliance Levels

### 🔴 **NON_COMPLIANT** - Not A2A Compliant
- **Criteria**: Any mandatory test failure
- **Business Value**: SDK cannot be used for A2A integrations
- **Action Required**: Fix mandatory failures immediately

### 🟡 **MANDATORY** - A2A Core Compliant
- **Criteria**: All mandatory tests pass (100%)
- **Business Value**: SDK can be used for basic A2A integrations
- **Target Audience**: Development and testing environments
- **Next Steps**: Address capability validation issues

### 🟢 **RECOMMENDED** - A2A Recommended Compliant
- **Criteria**: Mandatory (100%) + Capability (≥85%) + Quality (≥75%)
- **Business Value**: SDK ready for staging and pre-production use
- **Target Audience**: Staging environments and careful production use
- **Next Steps**: Improve quality and feature completeness

### 🏆 **FULL_FEATURED** - A2A Fully Compliant
- **Criteria**: Capability (≥95%) + Quality (≥90%) + Feature (≥80%)
- **Business Value**: SDK ready for full production deployment
- **Target Audience**: Production environments with confidence

## Common Issues and Solutions

### Mandatory Test Failures

#### `test_task_history_length` fails
```
AssertionError: historyLength parameter not respected
```
**Issue**: SDK doesn't implement historyLength parameter in tasks/get  
**Specification**: A2A §7.3 states tasks/get MUST support historyLength  
**Fix**: Implement historyLength parameter handling in your DefaultRequestHandler

**Example Fix**:
```python
def handle_tasks_get(self, params):
    task_id = params["id"]
    history_length = params.get("historyLength")  # Add this
    
    task = self.get_task(task_id)
    if history_length is not None:
        # Limit task.history to most recent N messages
        task.history = task.history[-history_length:]
    
    return task
```

#### `test_mandatory_fields_present` fails
```
KeyError: Required field 'version' missing from Agent Card
```
**Issue**: Agent Card missing required fields  
**Specification**: A2A §2.1 lists required Agent Card fields  
**Fix**: Ensure all required fields are present in your Agent Card

**Required Fields** (per JSON Schema):
- `version` (string)
- `name` (string) 
- `description` (string)
- `defaultInputModes` (array)
- `defaultOutputModes` (array)
- `capabilities` (object)

#### `test_message_send_invalid_params` fails
```
Expected InvalidParams error but got success response
```
**Issue**: message/send not validating required parameters  
**Specification**: A2A §5.1 requires parameter validation  
**Fix**: Add proper parameter validation to message/send method

### Capability Test Failures

#### Streaming tests fail but capability is declared
```
streaming: true declared but test_message_stream_basic failed
```
**Issue**: False advertising - streaming declared but not implemented  
**Solutions**:
1. **Implement streaming**: Add message/stream and tasks/resubscribe methods
2. **Remove capability**: Set `streaming: false` in Agent Card

#### Push notification tests fail but capability is declared
```
pushNotifications: true declared but test_set_push_notification_config failed
```
**Issue**: False advertising - push notifications declared but not implemented  
**Solutions**:
1. **Implement push notifications**: Add push notification config methods
2. **Remove capability**: Set `pushNotifications: false` in Agent Card

### Quality Test Issues

#### `test_parallel_requests` fails
```
Concurrency test failed - only 2/5 parallel requests succeeded
```
**Issue**: Poor concurrent request handling  
**Impact**: Production deployment may have performance issues  
**Fix**: Improve request handling concurrency in your implementation

#### `test_unicode_and_special_chars` fails
```
Unicode characters corrupted in task storage
```
**Issue**: Character encoding problems  
**Impact**: International users may experience data corruption  
**Fix**: Ensure proper UTF-8 handling throughout your implementation

## Deployment Decision Matrix

| Compliance Level | Development | Testing | Staging | Production |
|------------------|-------------|---------|---------|------------|
| 🔴 NON_COMPLIANT | ❌ | ❌ | ❌ | ❌ |
| 🟡 MANDATORY | ✅ | ✅ | ⚠️ | ❌ |
| 🟢 RECOMMENDED | ✅ | ✅ | ✅ | ⚠️ |
| 🏆 FULL_FEATURED | ✅ | ✅ | ✅ | ✅ |

**Legend**:
- ✅ Recommended
- ⚠️ Acceptable with caution
- ❌ Not recommended

## Continuous Integration

### Basic CI Pipeline
```bash
# In your CI/CD pipeline
./run_tck.py --sut-url $SUT_URL --category mandatory
if [ $? -ne 0 ]; then
    echo "❌ Mandatory tests failed - blocking deployment"
    exit 1
fi
```

### Advanced CI Pipeline
```bash
# Full compliance assessment
./run_tck.py --sut-url $SUT_URL --category all --compliance-report compliance.json

# Parse compliance level from report
COMPLIANCE_LEVEL=$(jq -r '.summary.compliance_level' compliance.json)

case $COMPLIANCE_LEVEL in
    "NON_COMPLIANT")
        echo "❌ Not A2A compliant - blocking all deployments"
        exit 1
        ;;
    "MANDATORY")
        echo "🟡 Basic compliance - allowing dev/test deployment only"
        if [ "$ENVIRONMENT" = "production" ]; then
            exit 1
        fi
        ;;
    "RECOMMENDED")
        echo "🟢 Recommended compliance - allowing staging deployment"
        ;;
    "FULL_FEATURED")
        echo "🏆 Full compliance - allowing production deployment"
        ;;
esac
```

## Best Practices

### 1. **Run Tests Frequently**
- Run mandatory tests on every commit
- Run full suite before releases
- Use compliance reports to track progress

### 2. **Fix Issues in Order**
1. Mandatory failures (blocking)
2. Capability false advertising (critical)
3. Quality issues (important)
4. Feature gaps (nice-to-have)

### 3. **Document Capabilities Accurately**
- Only declare capabilities you actually implement
- Test capability implementations thoroughly
- Update Agent Card when adding/removing features

### 4. **Monitor Compliance Over Time**
- Track compliance scores across releases
- Set up alerts for compliance regressions
- Use compliance reports for release decisions

### 5. **Understand Your Users**
- Development: MANDATORY level sufficient
- Staging: RECOMMENDED level preferred
- Production: FULL_FEATURED level recommended

## Troubleshooting

### TCK Won't Run
```bash
# Check Python version (3.8+ required)
python --version

# Check dependencies
pip install -e .

# Check SUT is running
curl $SUT_URL/agent
```

### Tests Are Skipping
```bash
# Check if tests have proper markers
pytest tests/optional/capabilities/ --collect-only

# Check if capabilities are declared
curl $SUT_URL/agent | jq .capabilities
```

### Compliance Report Empty
```bash
# Ensure pytest-json-report is installed
pip install pytest-json-report

# Check file permissions
ls -la *.json
```

## Getting Help

### Common Questions
- **Q**: Why are streaming tests skipping?  
  **A**: Your Agent Card likely has `streaming: false` or missing. This is allowed.

- **Q**: Why do quality tests fail but compliance is still achieved?  
  **A**: Quality tests never block compliance - they indicate production readiness.

- **Q**: Can I deploy with MANDATORY compliance level?  
  **A**: For development/testing yes, for production we recommend RECOMMENDED+ level.

### Support Resources
- **Specification**: A2A Protocol Specification
- **Issues**: Report TCK issues on GitHub
- **Examples**: See `tests/` for specification interpretation
- **Community**: A2A Developer Forum

## Summary

The A2A TCK provides progressive validation:

1. **🔴 Mandatory** → Basic A2A compliance
2. **🔄 Capabilities** → Honest capability advertising  
3. **🛡️ Quality** → Production readiness assessment
4. **🎨 Features** → Completeness evaluation

Use the compliance reports to make informed deployment decisions and track your SDK's A2A specification compliance over time. 