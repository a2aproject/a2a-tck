# A2A Protocol Technology Compatibility Kit (TCK)

A comprehensive test suite for validating A2A (Application-to-Application) JSON-RPC protocol specification compliance with progressive validation and detailed compliance reporting.

## Overview

The A2A Protocol TCK is a sophisticated validation framework that provides:
- **📋 Categorized Testing**: Clear separation of mandatory vs. optional requirements  
- **🎯 Capability-Based Validation**: Smart test execution based on Agent Card declarations
- **📊 Compliance Reporting**: Detailed assessment with actionable recommendations
- **🚀 Progressive Enhancement**: Four-tier compliance levels for informed deployment decisions

The TCK transforms A2A specification compliance from guesswork into a clear, structured validation process.

## ✨ Key Features

### 🔍 **Intelligent Test Categorization**
- **🔴 MANDATORY**: Must pass for A2A compliance (JSON-RPC 2.0 + A2A core)
- **🔄 CAPABILITIES**: Conditional mandatory based on Agent Card declarations  
- **🛡️ QUALITY**: Production readiness indicators (optional)
- **🎨 FEATURES**: Optional implementation completeness (informational)

### 🧠 **Capability-Based Test Logic**
- **Smart Execution**: Tests skip when capabilities not declared, become mandatory when declared
- **False Advertising Detection**: Catches capabilities declared but not implemented
- **Honest Validation**: Only tests what's actually claimed to be supported

### 📈 **Compliance Levels & Scoring**
- **🔴 NON_COMPLIANT**: Any mandatory failure (Not A2A Compliant)
- **🟡 MANDATORY**: Basic compliance (A2A Core Compliant)  
- **🟢 RECOMMENDED**: Production-ready (A2A Recommended Compliant)
- **🏆 FULL_FEATURED**: Complete implementation (A2A Fully Compliant)

### 📋 **Comprehensive Reporting**
- Weighted compliance scoring
- Specification reference citations
- Actionable fix recommendations
- Deployment readiness guidance

## Requirements

- **Python**: 3.8+
- **uv**: Recommended for environment management
- **SUT**: Running A2A implementation with accessible HTTP/HTTPS endpoint

## Installation

1. **Install uv**:
   ```bash
   # Install uv (see https://github.com/astral-sh/uv#installation)
   curl -LsSf https://astral.sh/uv/install.sh | sh
   # Or: pipx install uv
   # Or: brew install uv
   ```

2. **Clone and setup**:
   ```bash
   git clone https://github.com/maeste/a2a-tck.git
   cd a2a-tck
   
   # Create virtual environment
   uv venv
   source .venv/bin/activate  # Linux/macOS
   # .venv\\Scripts\\activate   # Windows
   
   # Install dependencies
   uv pip install -e .
   ```

3. **Start your A2A implementation** (System Under Test):
   ```bash
   # Example using the included Python SUT
   cd python-sut/tck_core_agent
   uv run .
   ```

## 🚀 Quick Start

### 1. **Check A2A Compliance** (Start Here!)
```bash
./run_tck.py --sut-url http://localhost:9999 --category mandatory
```
**Result**: ✅ Pass = A2A compliant, ❌ Fail = NOT A2A compliant

### 2. **Validate Capability Honesty**
```bash
./run_tck.py --sut-url http://localhost:9999 --category capabilities
```
**Result**: Ensures declared capabilities actually work (prevents false advertising)

### 3. **Assess Production Readiness**  
```bash
./run_tck.py --sut-url http://localhost:9999 --category quality
```
**Result**: Identifies issues that may affect production deployment

### 4. **Generate Comprehensive Report**
```bash
./run_tck.py --sut-url http://localhost:9999 --category all --compliance-report compliance.json
```
**Result**: Complete assessment with compliance level and recommendations

## 📖 Command Reference

### **Core Commands**

```bash
# Get help and understand test categories
./run_tck.py --explain

# Test specific category
./run_tck.py --sut-url URL --category CATEGORY

# Available categories:
#   mandatory    - A2A compliance validation (MUST pass)  
#   capabilities - Capability honesty check (conditional mandatory)
#   quality      - Production readiness assessment
#   features     - Optional feature completeness
#   all          - Complete validation workflow
```

### **Advanced Options**

```bash
# Generate detailed compliance report
./run_tck.py --sut-url URL --category all --compliance-report report.json

# Verbose output with detailed logging
./run_tck.py --sut-url URL --category mandatory --verbose

# Generate HTML report (additional)
./run_tck.py --sut-url URL --category all --report

# Skip Agent Card fetching (for non-standard implementations)  
./run_tck.py --sut-url URL --category mandatory --skip-agent-card
```

## 🎯 Understanding Test Categories

### 🔴 **MANDATORY Tests** - Core A2A Compliance
**Purpose**: Validate core A2A specification requirements  
**Impact**: Failure = NOT A2A compliant  
**Location**: `tests/mandatory/`

**Includes**:
- JSON-RPC 2.0 compliance (`tests/mandatory/jsonrpc/`)
- A2A protocol core methods (`tests/mandatory/protocol/`)
- Agent Card required fields
- Core message/send functionality
- Task management (get/cancel)

**Example Failures**:
- `test_task_history_length` → SDK doesn't implement historyLength parameter
- `test_mandatory_fields_present` → Agent Card missing required fields

### 🔄 **CAPABILITY Tests** - Conditional Mandatory  
**Purpose**: Validate declared capabilities work correctly  
**Impact**: Failure = False advertising  
**Logic**: Skip if not declared, mandatory if declared  
**Location**: `tests/optional/capabilities/`

**Capability Validation**:
```json
{
  "capabilities": {
    "streaming": true,         ← Must pass streaming tests
    "pushNotifications": false ← Streaming tests will skip
  }
}
```

**Includes**:
- Streaming support (`message/stream`, `tasks/resubscribe`)
- Push notification configuration
- File/data modality support
- Authentication methods

### 🛡️ **QUALITY Tests** - Production Readiness
**Purpose**: Assess implementation robustness  
**Impact**: Never blocks compliance, indicates production issues  
**Location**: `tests/optional/quality/`

**Quality Areas**:
- Concurrent request handling
- Edge case robustness  
- Unicode/special character support
- Boundary value handling
- Error recovery and resilience

### 🎨 **FEATURE Tests** - Optional Implementation
**Purpose**: Measure optional feature completeness  
**Impact**: Purely informational  
**Location**: `tests/optional/features/`

**Includes**:
- Convenience features
- Enhanced error messages
- SDK-specific capabilities
- Optional protocol extensions

## 📊 Compliance Levels

### 🔴 **NON_COMPLIANT** - Not A2A Compliant
- **Criteria**: Any mandatory test failure
- **Business Impact**: Cannot be used for A2A integrations
- **Action**: Fix mandatory failures immediately

### 🟡 **MANDATORY** - A2A Core Compliant  
- **Criteria**: 100% mandatory test pass rate
- **Business Impact**: Basic A2A integration support
- **Suitable For**: Development and testing environments
- **Next Step**: Address capability validation

### 🟢 **RECOMMENDED** - A2A Recommended Compliant
- **Criteria**: Mandatory (100%) + Capability (≥85%) + Quality (≥75%)
- **Business Impact**: Production-ready with confidence
- **Suitable For**: Staging and careful production deployment
- **Next Step**: Enhance feature completeness

### 🏆 **FULL_FEATURED** - A2A Fully Compliant
- **Criteria**: Capability (≥95%) + Quality (≥90%) + Feature (≥80%)
- **Business Impact**: Complete A2A implementation
- **Suitable For**: Full production deployment with confidence

## 📋 Compliance Report

When you run with `--compliance-report`, you get a JSON report containing:

```json
{
  "summary": {
    "compliance_level": "RECOMMENDED",
    "overall_score": 87.5,
    "mandatory_score": 100.0,
    "capability_score": 90.0,
    "quality_score": 75.0,
    "feature_score": 60.0
  },
  "recommendations": [
    "✅ Ready for staging deployment",
    "⚠️ Address 2 quality issues before production",
    "💡 Consider implementing 3 additional features"
  ],
  "next_steps": [
    "Fix Unicode handling in task storage",
    "Improve concurrent request performance",
    "Consider implementing authentication capability"
  ]
}
```

## 🔄 CI/CD Integration

### **Basic CI Pipeline** (Compliance Gate)
```bash
#!/bin/bash
# Block deployment if not A2A compliant
./run_tck.py --sut-url $SUT_URL --category mandatory
if [ $? -ne 0 ]; then
    echo "❌ NOT A2A compliant - blocking deployment"
    exit 1
fi
echo "✅ A2A compliant - deployment approved"
```

### **Advanced CI Pipeline** (Environment-Aware)
```bash
#!/bin/bash
# Generate compliance report and make environment-specific decisions
./run_tck.py --sut-url $SUT_URL --category all --compliance-report compliance.json

COMPLIANCE_LEVEL=$(jq -r '.summary.compliance_level' compliance.json)

case $COMPLIANCE_LEVEL in
    "NON_COMPLIANT")
        echo "❌ Not A2A compliant - blocking all deployments"
        exit 1
        ;;
    "MANDATORY")
        echo "🟡 Basic compliance - dev/test only"
        [[ "$ENVIRONMENT" == "production" ]] && exit 1
        ;;
    "RECOMMENDED")
        echo "🟢 Recommended - staging approved"
        ;;
    "FULL_FEATURED")
        echo "🏆 Full compliance - production approved"
        ;;
esac
```

## 🛠️ Troubleshooting

### **Common Issues**

**Streaming tests skipping**:
```bash
# Check Agent Card capabilities
curl $SUT_URL/agent | jq .capabilities
# If streaming: false, tests will skip (this is correct!)
```

**Quality tests failing but compliance achieved**:
```bash
# This is expected - quality tests don't block compliance
# Address quality issues for production readiness
```

**Tests not discovering**:
```bash
# Ensure proper installation
pip install -e .

# Check test discovery
pytest --collect-only tests/mandatory/
```

## 📚 Documentation

- **[SDK Validation Guide](SDK_VALIDATION_GUIDE.md)** - Detailed usage guide for SDK developers
- **[Test Documentation Standards](TEST_DOCUMENTATION_STANDARDS.md)** - Standards for test contributors

## 🤝 Contributing

1. Fork the repository
2. Follow [Test Documentation Standards](TEST_DOCUMENTATION_STANDARDS.md)
3. Add tests with proper categorization and specification references
4. Submit pull request with clear specification citations

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🎯 Quick Decision Guide

**Just want A2A compliance?**
```bash
./run_tck.py --sut-url URL --category mandatory
```

**Planning production deployment?**  
```bash
./run_tck.py --sut-url URL --category all --compliance-report report.json
```

**Debugging capability issues?**
```bash
./run_tck.py --sut-url URL --category capabilities --verbose
```

**Want comprehensive assessment?**
```bash
./run_tck.py --sut-url URL --explain  # Learn about categories first
./run_tck.py --sut-url URL --category all --compliance-report full_report.json
```

The A2A TCK transforms specification compliance from confusion into clarity. 🚀
