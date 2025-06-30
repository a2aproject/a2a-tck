# A2A Test Coverage Analysis Guide

This guide documents the **Test Coverage Analysis** tool - a comprehensive system for analyzing how well the current test suite covers the A2A specification.

## IT's BROKEN. IT SHOULD NOT BE USED

## 🎯 Purpose

**`analyze_test_coverage.py`** analyzes the **current specification in isolation** to identify coverage gaps, missing tests, and quality issues. This is different from `check_spec_changes.py` which compares two specification versions.

### Key Analysis Areas

1. **Requirement Coverage**: Which spec requirements lack tests
2. **Test Quality**: Documentation, specification references, complexity
3. **Method Coverage**: Which JSON-RPC methods need testing
4. **Error Code Coverage**: Which error scenarios aren't tested  
5. **Capability Coverage**: Which optional features need tests
6. **Gap Analysis**: Orphaned tests, weak coverage, missing areas

## 🔧 Tool Comparison

| Tool | Purpose | Analysis Type |
|------|---------|---------------|
| `check_spec_changes.py` | Compare two spec versions | **Change-based** - what changed between versions |
| `analyze_test_coverage.py` | Analyze current test coverage | **Coverage-based** - gaps in current implementation |

## 📊 Usage Examples

### Quick Coverage Summary

```bash
# Basic coverage analysis
./analyze_test_coverage.py --summary-only

# View results
cat test_coverage_report.md
```

### Comprehensive Analysis

```bash
# Full detailed analysis
./analyze_test_coverage.py --verbose

# Custom output location  
./analyze_test_coverage.py --output reports/coverage_analysis.md

# Export data for automation
./analyze_test_coverage.py --json-export coverage_data.json
```

### Advanced Options

```bash
# Analyze custom test directory
./analyze_test_coverage.py --test-dir custom_tests/

# Use specific spec files
./analyze_test_coverage.py \
  --current-md path/to/spec.md \
  --current-json path/to/schema.json

# Dry run (analyze without saving)
./analyze_test_coverage.py --dry-run --verbose
```

## 📋 Report Types

### 📊 Summary Report (`--summary-only`)

**Quick overview** with:
- Overall coverage percentage
- Critical gaps count  
- High-priority recommendations
- Next steps guidance

**Use for**: Quick status checks, stakeholder updates

### 📚 Detailed Report (default)

**Comprehensive analysis** with:
- Requirement-by-requirement coverage
- Method and error code analysis
- Test quality metrics
- Detailed recommendations with priority levels
- Improvement targets and action plans

**Use for**: Development planning, detailed analysis

### 📄 JSON Export (`--json-export`)

**Structured data** containing:
- Raw coverage analysis results
- Summary statistics  
- All identified gaps and recommendations
- Test registry information

**Use for**: Automation, dashboards, CI/CD integration

## 🔍 Analysis Components

### 1. Requirement Coverage

Analyzes each specification requirement:

- **Coverage Status**: Covered, uncovered, weakly covered
- **Coverage Quality**: Test count and quality scores
- **Requirement Level**: MUST, SHOULD, MAY priorities
- **Missing Tests**: Requirements without any tests

### 2. Test Quality Assessment

Evaluates test suite quality:

- **Documentation**: Tests with docstrings and descriptions
- **Specification References**: Tests linked to spec sections  
- **Orphaned Tests**: Tests without clear spec connections
- **Complexity Analysis**: Simple, moderate, complex test distribution

### 3. Method Coverage

JSON-RPC method analysis:

- **Covered Methods**: Methods with adequate tests
- **Uncovered Methods**: Methods lacking tests
- **Test Adequacy**: Quality of method testing

### 4. Error Code Coverage  

Error handling analysis:

- **Standard JSON-RPC Errors**: -32xxx codes
- **A2A-Specific Errors**: Custom error codes
- **Error Scenario Testing**: Comprehensive error coverage

### 5. Optional Capability Coverage

Feature testing analysis:

- **Streaming Support**: SSE-related functionality
- **Push Notifications**: Webhook capabilities  
- **Authentication**: Security feature testing
- **Extensions**: Custom capability support

## 📈 Coverage Metrics

### Overall Coverage Score

```
Coverage = (Covered Requirements / Total Requirements) × 100%
```

### Quality Scoring

Each requirement gets a quality score based on:

- **Test Count** (40%): Number of relevant tests
- **Test Quality** (30%): Documentation and clarity
- **Specification Alignment** (30%): Clear spec references

### Coverage Levels

| Level | Percentage | Status | Action Required |
|-------|------------|--------|-----------------|
| **Excellent** | 90%+ | 🟢 | Maintain quality |
| **Good** | 80-89% | 🟡 | Minor improvements |
| **Needs Work** | 60-79% | 🟠 | Active improvement |
| **Poor** | <60% | 🔴 | Urgent attention |

## 🎯 Recommendations System

### Priority Levels

**🚨 High Priority**
- MUST requirements without tests
- Critical JSON-RPC methods uncovered
- Major functionality gaps

**⚠️ Medium Priority**  
- SHOULD requirements weakly covered
- Test documentation gaps
- Error handling improvements

**💡 Low Priority**
- MAY requirements uncovered
- Test organization improvements
- Nice-to-have optimizations

### Action Categories

**Requirements** - Missing spec coverage
**Methods** - JSON-RPC functionality gaps  
**Quality** - Test documentation/organization
**Documentation** - Specification references
**Error Handling** - Error scenario coverage

## 🛠️ Integration & Automation

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Test Coverage Analysis
  run: |
    ./analyze_test_coverage.py --json-export coverage.json
    # Process results, fail on critical gaps
    python scripts/check_coverage_thresholds.py coverage.json
```

### Exit Codes

| Code | Meaning | Description |
|------|---------|-------------|
| `0` | Success | Good coverage (70%+) |
| `1` | Warning | Coverage needs improvement |
| `2` | Critical | Major coverage gaps found |

### JSON Data Structure

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "specification_info": {
    "requirements_count": 150,
    "definitions_count": 45,
    "test_count": 89
  },
  "coverage_analysis": {
    "requirement_coverage": { ... },
    "method_coverage": { ... },
    "test_quality": { ... },
    "recommendations": [ ... ]
  }
}
```

## 📚 Best Practices

### Regular Analysis

```bash
# Weekly coverage review
./analyze_test_coverage.py --summary-only

# Before releases  
./analyze_test_coverage.py --verbose

# After adding new features
./analyze_test_coverage.py --json-export post_feature.json
```

### Continuous Improvement

1. **Target 95% MUST requirement coverage**
2. **Maintain 90% overall test documentation**  
3. **Link all tests to specification sections**
4. **Regular orphaned test cleanup**
5. **Comprehensive error scenario testing**

### Development Workflow

1. **After spec updates**: Run analysis to identify new requirements
2. **During development**: Check method/feature coverage
3. **Before commits**: Ensure new code has adequate tests
4. **Sprint reviews**: Use summary reports for progress tracking

## 🔧 Troubleshooting

### Common Issues

**"Current spec not found"**
```bash
# Initialize baseline specifications
./update_current_spec.py --version "latest"
```

**"No tests found"**
```bash
# Check test directory exists
ls -la tests/
# Use custom test directory
./analyze_test_coverage.py --test-dir path/to/tests
```

**"Failed to parse specification"**
```bash
# Validate specification files
python -c "import json; json.load(open('current_spec/a2a_schema.json'))"
```

### Debug Mode

```bash
# Enable verbose logging
./analyze_test_coverage.py --verbose

# Dry run for testing
./analyze_test_coverage.py --dry-run --verbose
```

## 📖 Related Documentation

- **[Specification Update Workflow](docs/SPEC_UPDATE_WORKFLOW.md)** - Specification update process
- **[Test Documentation Standards](docs/TEST_DOCUMENTATION_STANDARDS.md)** - Test quality standards
- **[README.md](../README.md)** - General TCK overview

---

*For questions or improvements, see the project's main documentation or create an issue.* 
