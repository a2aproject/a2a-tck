# A2A Protocol Technology Compatibility Kit (TCK)

A comprehensive test suite for validating A2A (Application-to-Application) JSON-RPC protocol specification compliance with progressive validation and detailed compliance reporting.

## Overview

The A2A Protocol TCK is a sophisticated validation framework that provides:
- **📋 Categorized Testing**: Clear separation of mandatory vs. optional requirements  
- **🎯 Capability-Based Validation**: Smart test execution based on Agent Card declarations
- **📊 Compliance Reporting**: Detailed assessment with actionable recommendations
- **🚀 Progressive Enhancement**: Four-tier compliance levels for informed deployment decisions

The TCK transforms A2A specification compliance from guesswork into a clear, structured validation process.

## 🔄 Two Main Workflows

### 1. **Testing Your A2A Implementation** (You're likely here for this)
Use the TCK to validate your A2A implementation:
```bash
./run_tck.py --sut-url http://localhost:9999 --category all --compliance-report report.json
```

### 2. **Managing A2A Specification Updates** (Advanced/Maintainer workflow)
Use the TCK to validate your A2A implementation:
- 📖 **[Complete Specification Update Workflow](docs/SPEC_UPDATE_WORKFLOW.md)**
- 🔍 **Check spec changes**: `./check_spec_changes.py`
- 🧪 **Analyze test coverage**: `./analyze_test_coverage.py --summary-only`
- 📥 **Update baseline**: `./update_current_spec.py --version "v1.x"`

---

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

### Preparing and Running Your SUT (System Under Test) with `run_sut.py`

**Note:** The `run_sut.py` script requires the `PyYAML` package. You can install it using `uv pip install pyyaml` or `pip install pyyaml`.

To simplify the process of testing various A2A implementations, this TCK includes a utility script `run_sut.py`. This Python script automates the download (or update), build, and execution of a System Under Test (SUT) based on a configuration file.

SUTs will be cloned or updated into a directory named `SUT/` created in the root of this TCK repository.

#### Configuration (`sut_config.yaml`)

You need to create a YAML configuration file (e.g., `my_sut_config.yaml`) to define how your SUT should be handled. A template is available at `sut_config_template.yaml`.

The configuration file supports the following fields:

*   `sut_name` (string, mandatory): A descriptive name for your SUT. This name will also be used as the directory name for the SUT within the `SUT/` folder (e.g., `SUT/my_agent`).
*   `github_repo` (string, mandatory): The HTTPS or SSH URL of the git repository where the SUT source code is hosted.
*   `git_ref` (string, optional): A specific git branch, tag, or commit hash to checkout after cloning/fetching. If omitted, the repository's default branch will be used.
*   `prerequisites_script` (string, mandatory): Path to the script that handles prerequisite installation and building the SUT. This path is relative to the root of the SUT's cloned repository (e.g., `scripts/build.sh` or `setup/prepare_env.py`).
*   `prerequisites_interpreter` (string, optional): The interpreter to use for the `prerequisites_script` (e.g., `bash`, `python3`, `powershell.exe`). If omitted, the script will be executed directly (e.g., `./scripts/build.sh`). Ensure the script is executable and has a valid shebang in this case.
*   `prerequisites_args` (string, optional): A string of arguments to pass to the `prerequisites_script` (e.g., `"--version 1.2 --no-cache"`).
*   `run_script` (string, mandatory): Path to the script that starts the SUT. This path is relative to the root of the SUT's cloned repository (e.g., `scripts/run.sh` or `app/start_server.py`).
*   `run_interpreter` (string, optional): The interpreter to use for the `run_script`.
*   `run_args` (string, optional): A string of arguments to pass to the `run_script` (e.g., `"--port 8080 --debug"`).

**Example `sut_config.yaml`:**
```yaml
sut_name: "example_agent"
github_repo: "https://github.com/your_org/example_agent_repo.git"
git_ref: "v1.0.0" # Optional: checkout tag v1.0.0
prerequisites_script: "bin/setup.sh"
prerequisites_interpreter: "bash"
prerequisites_args: "--fast"
run_script: "bin/start.py"
run_interpreter: "python3"
run_args: "--host 0.0.0.0 --port 9000"
```

#### SUT Script Requirements

*   **Prerequisites Script**: This script is responsible for all steps required to build your SUT and install its dependencies. It should exit with a status code of `0` on success and any non-zero status code on failure. If it fails, `run_sut.py` will terminate.
*   **Run Script**: This script should start your SUT. Typically, it will launch a server or application that runs in the foreground. The `run_sut.py` script will wait for this script to terminate (e.g., by Ctrl+C or if the SUT exits itself).
*   **Directly Executable Scripts**: If you omit the `*_interpreter` for a script, ensure the script file has execute permissions (e.g., `chmod +x your_script.sh`) and, for shell scripts on Unix-like systems, includes a valid shebang (e.g., `#!/bin/bash`).

#### Usage

Once you have your SUT configuration file ready, you can run your SUT using:

```bash
python run_sut.py path/to/your_sut_config.yaml
```
For example:
```bash
python run_sut.py sut_configs/my_python_agent_config.yaml
```
This will:
1.  Clone the SUT from `github_repo` into `SUT/<sut_name>/` (or update if it already exists).
2.  Checkout the specified `git_ref` (if any).
3.  Execute the `prerequisites_script` within the SUT's directory.
4.  Execute the `run_script` within the SUT's directory to start the SUT.

You can then proceed to run the TCK tests against your SUT.

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

- **[SDK Validation Guide](docs/SDK_VALIDATION_GUIDE.md)** - Detailed usage guide for SDK developers
- **[Specification Update Workflow](docs/SPEC_UPDATE_WORKFLOW.md)** - Monitor and manage A2A specification changes
- **[Test Coverage Analysis](docs/TEST_COVERAGE_ANALYSIS.md)** - Analyze and improve test coverage
- **[Test Documentation Standards](docs/TEST_DOCUMENTATION_STANDARDS.md)** - Standards for test contributors

## 🤝 Contributing

1. Fork the repository
2. Follow [Test Documentation Standards](docs/TEST_DOCUMENTATION_STANDARDS.md)
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
