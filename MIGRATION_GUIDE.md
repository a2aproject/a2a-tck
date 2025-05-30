# A2A TCK Migration Guide

This guide helps developers migrate from the previous TCK implementation to the new categorized test system with capability-based validation.

## What Changed

### Major Changes in the New TCK

#### 1. **Test Categorization System** 🎯
- **Old**: All tests treated equally, unclear which failures block compliance
- **New**: Clear categories with different impact levels
  - 🔴 **MANDATORY**: Must pass for A2A compliance
  - 🔄 **CAPABILITIES**: Conditional mandatory based on Agent Card declarations
  - 🛡️ **QUALITY**: Production readiness indicators (optional)
  - 🎨 **FEATURES**: Optional implementation completeness (informational)

#### 2. **Capability-Based Test Logic** 🧠
- **Old**: All capability tests run regardless of Agent Card declarations
- **New**: Smart test execution based on capabilities
  - If capability NOT declared → Tests SKIP (allowed)
  - If capability IS declared → Tests become MANDATORY (must pass)

#### 3. **SUT Purity** 🔧
- **Old**: SUT had custom workarounds and modifications
- **New**: SUT uses only SDK-provided components
  - Removed `TckCoreRequestHandler` custom implementation
  - Uses only `DefaultRequestHandler` from SDK
  - Tests now accurately reflect SDK capabilities

#### 4. **Compliance Reporting** 📊
- **Old**: Basic pass/fail reporting
- **New**: Comprehensive compliance assessment
  - 4-tier compliance levels with badges
  - Weighted scoring system
  - Actionable recommendations
  - False advertising detection

#### 5. **Progressive Test Execution** 🚀
- **Old**: Run all tests at once
- **New**: Recommended workflow with clear progression
  - Step 1: Mandatory tests (compliance check)
  - Step 2: Capability tests (honesty check)
  - Step 3: Quality tests (production readiness)
  - Step 4: Feature tests (completeness assessment)

## Migration Checklist

### For SDK Developers

#### ✅ **Update Your CI/CD Pipeline**

**Old Approach**:
```bash
# Old - unclear what failures mean
pytest tests/ --sut-url $SUT_URL
```

**New Approach**:
```bash
# New - clear compliance validation
./run_tck.py --sut-url $SUT_URL --category mandatory
if [ $? -ne 0 ]; then
    echo "❌ NOT A2A compliant - mandatory tests failed"
    exit 1
fi

# Optional: Full assessment with compliance report
./run_tck.py --sut-url $SUT_URL --category all --compliance-report compliance.json
```

#### ✅ **Review Your Agent Card Capabilities**

**Critical Change**: Capability tests are now conditional mandatory.

**Action Required**:
1. **Audit your Agent Card**: Only declare capabilities you actually implement
2. **Test your capabilities**: Ensure declared capabilities work correctly
3. **Update or implement**: Either implement missing capabilities or remove declarations

**Example**:
```json
{
  "capabilities": {
    "streaming": true,  ← If true, streaming tests MUST pass
    "pushNotifications": false  ← If false, push notification tests are SKIPPED
  }
}
```

#### ✅ **Fix Mandatory Test Failures**

**Common New Failures** (due to SUT purity):

1. **`test_task_history_length` now fails**:
   - **Cause**: Custom `TckCoreRequestHandler` removed
   - **Fix**: Implement `historyLength` parameter in your SDK's `DefaultRequestHandler`

2. **Agent Card validation stricter**:
   - **Cause**: More rigorous field validation
   - **Fix**: Ensure all required fields present with correct types

3. **Parameter validation enhanced**:
   - **Cause**: Better input validation testing
   - **Fix**: Add proper parameter validation to your methods

#### ✅ **Understand New Test Behavior**

**Capability Test Changes**:
```python
# Old behavior: Always ran, always expected to pass
def test_streaming():
    # This always ran regardless of Agent Card

# New behavior: Conditional based on Agent Card
@optional_capability
def test_streaming():
    # This SKIPS if streaming: false
    # This is MANDATORY if streaming: true
```

**Quality Test Changes**:
```python
# Old behavior: Unclear impact of failures
def test_concurrency():
    # Failure impact unknown

# New behavior: Clear production guidance
@quality_production
def test_concurrency():
    """
    QUALITY PRODUCTION: Concurrent Request Handling
    
    Failure Impact: Affects production readiness
    """
    # Failures don't block compliance but indicate production issues
```

### For TCK Contributors

#### ✅ **Update Test Documentation**

**All tests must now follow the documentation standard**:
```python
@mandatory_protocol
def test_example():
    """
    MANDATORY: A2A Specification §X.Y - Section Title
    
    The specification states: "Servers MUST..." (exact quote)
    
    Test validates [specific behavior].
    
    Failure Impact: SDK is NOT A2A compliant
    Fix Suggestion: [Actionable guidance]
    """
```

#### ✅ **Apply Proper Markers**

**Old**:
```python
@pytest.mark.core
def test_something():
    pass
```

**New**:
```python
@mandatory_protocol  # or @mandatory_jsonrpc
def test_mandatory_behavior():
    pass

@optional_capability
def test_capability_feature():
    pass

@quality_production
def test_production_readiness():
    pass

@optional_feature
def test_optional_behavior():
    pass
```

#### ✅ **Use Capability Validation**

**Old**:
```python
def test_streaming():
    # Always ran, no capability checking
    pass
```

**New**:
```python
@optional_capability
def test_streaming(agent_card_data):
    validator = CapabilityValidator(agent_card_data)
    
    if not validator.is_capability_declared('streaming'):
        pytest.skip("Streaming capability not declared - test not applicable")
    
    # If we get here, streaming is declared so test MUST pass
```

## Breaking Changes

### 1. **SUT Implementation Changes**

**Removed**:
- `custom_request_handler.py` (TckCoreRequestHandler)
- Custom authentication middleware
- Agent Card field injection

**Impact**: Tests that were passing due to workarounds may now fail

**Migration**: Implement missing functionality in your actual SDK

### 2. **Test Discovery Changes**

**Old**: All tests discovered by default
**New**: Tests organized by category in directories

**File Moves**:
```
tests/
├── test_json_rpc_compliance.py          → tests/mandatory/jsonrpc/
├── test_agent_card.py                   → tests/mandatory/protocol/
├── test_message_send_method.py          → tests/mandatory/protocol/
├── test_streaming_methods.py            → tests/optional/capabilities/
├── test_push_notification_*.py          → tests/optional/capabilities/
├── test_concurrency.py                  → tests/optional/quality/
├── test_edge_cases.py                   → tests/optional/quality/
└── test_sdk_limitations.py              → tests/optional/features/
```

### 3. **Command Line Changes**

**Old**:
```bash
pytest tests/ --sut-url $URL --test-scope core
```

**New**:
```bash
./run_tck.py --sut-url $URL --category mandatory
```

**New Categories**:
- `mandatory` - Core compliance (was `core`)
- `capabilities` - Capability validation (new)
- `quality` - Production readiness (was mixed in with others)
- `features` - Optional features (was mixed in with others)
- `all` - All categories in recommended order

### 4. **Marker System Changes**

**Old Markers**: `@pytest.mark.core`, `@pytest.mark.all`
**New Markers**: Category-specific and specification-aligned

| Old | New | Purpose |
|-----|-----|---------|
| `@pytest.mark.core` | `@mandatory_jsonrpc` or `@mandatory_protocol` | Core compliance |
| `@pytest.mark.all` | `@optional_capability`, `@quality_*`, `@optional_feature` | Non-core tests |

## Common Migration Issues

### Issue 1: Tests Now Failing Due to SUT Purity

**Symptoms**: Tests that passed before now fail
**Cause**: SUT workarounds removed, testing actual SDK behavior
**Solution**: Implement missing functionality in your SDK

**Example**:
```python
# This now fails because historyLength isn't implemented in SDK
def test_task_history_length():
    # Was passing due to TckCoreRequestHandler workaround
    # Now fails because DefaultRequestHandler doesn't implement it
```

**Fix**: Implement `historyLength` parameter handling in your SDK.

### Issue 2: Capability Tests Skipping

**Symptoms**: Streaming/push notification tests show as "SKIPPED"
**Cause**: Capabilities not declared in Agent Card (this is correct behavior)
**Solution**: No action needed if capabilities aren't implemented

**Example**:
```json
{
  "capabilities": {
    "streaming": false  ← This causes streaming tests to skip
  }
}
```

This is **correct behavior** - if you don't implement streaming, tests should skip.

### Issue 3: Quality Tests "Failing" But Compliance Still Achieved

**Symptoms**: Quality tests fail but TCK reports compliance success
**Cause**: Quality tests don't block compliance (by design)
**Solution**: Address quality issues for production readiness

**Example**:
```
🔴 Mandatory Tests:   ✅ PASSED
🔄 Capability Tests:  ✅ PASSED  
🛡️ Quality Tests:     ⚠️ ISSUES    ← This doesn't block compliance
🎨 Feature Tests:     ℹ️ INCOMPLETE
```

**Action**: Address quality issues before production deployment.

### Issue 4: Compliance Report Shows Different Levels

**Symptoms**: Not achieving expected compliance level
**Cause**: New weighted scoring system
**Solution**: Understand compliance level requirements

**Compliance Thresholds**:
- 🔴 **NON_COMPLIANT**: Any mandatory test failure
- 🟡 **MANDATORY**: 100% mandatory pass rate
- 🟢 **RECOMMENDED**: 100% mandatory + 85% capability + 75% quality
- 🏆 **FULL_FEATURED**: 95% capability + 90% quality + 80% feature

## Step-by-Step Migration

### Step 1: Update Your Test Commands

**Replace**:
```bash
pytest tests/ --sut-url $SUT_URL
```

**With**:
```bash
./run_tck.py --sut-url $SUT_URL --category mandatory
```

### Step 2: Fix Mandatory Test Failures

Run mandatory tests first and fix all failures:
```bash
./run_tck.py --sut-url $SUT_URL --category mandatory --verbose
```

Common fixes needed:
- Implement `historyLength` parameter
- Add required Agent Card fields
- Improve parameter validation

### Step 3: Review Capability Declarations

Audit your Agent Card capabilities:
```bash
curl $SUT_URL/agent | jq .capabilities
```

For each capability set to `true`, ensure it's properly implemented.

### Step 4: Run Capability Tests

```bash
./run_tck.py --sut-url $SUT_URL --category capabilities
```

Fix any failures (these indicate false advertising).

### Step 5: Assess Quality and Features

```bash
./run_tck.py --sut-url $SUT_URL --category quality
./run_tck.py --sut-url $SUT_URL --category features
```

Address issues based on your deployment needs.

### Step 6: Generate Compliance Report

```bash
./run_tck.py --sut-url $SUT_URL --category all --compliance-report compliance.json
```

Review the report for your compliance level and recommendations.

## Benefits of Migration

### For SDK Developers

1. **Clear Compliance Validation**: Know exactly what's required for A2A compliance
2. **Honest Capability Testing**: No more false advertising issues
3. **Production Readiness Assessment**: Clear guidance on deployment readiness
4. **Progressive Enhancement**: Improve compliance level over time

### For SDK Users

1. **Reliable Compliance**: SDKs that pass TCK actually meet A2A specification
2. **Capability Trust**: Declared capabilities actually work
3. **Quality Assurance**: Production-ready SDKs identified clearly

### For the A2A Ecosystem

1. **Specification Compliance**: True adherence to A2A protocol
2. **Interoperability**: SDKs work together reliably
3. **Quality Standards**: Higher quality implementations over time

## Support and Resources

### Getting Help

- **Documentation**: See `SDK_VALIDATION_GUIDE.md` for detailed usage
- **Examples**: Look at test files for specification interpretation
- **Issues**: Report migration problems on GitHub

### Common Commands Reference

```bash
# Check A2A compliance
./run_tck.py --sut-url $URL --category mandatory

# Validate capability honesty  
./run_tck.py --sut-url $URL --category capabilities

# Assess production readiness
./run_tck.py --sut-url $URL --category quality

# Complete assessment with report
./run_tck.py --sut-url $URL --category all --compliance-report report.json

# Get help and category explanation
./run_tck.py --explain
```

The new TCK provides a much clearer path to A2A compliance with better validation and guidance for production deployments. 