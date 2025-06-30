# A2A Specification Update Workflow

This document provides a comprehensive workflow for monitoring A2A specification changes, analyzing their impact on the TCK test suite, and updating your baseline specifications. This is a **separate process** from running the TCK against your implementation.

## 🎯 Purpose

The specification update workflow helps you:
- **Monitor** A2A specification changes from the official GitHub repository
- **Analyze** the impact of changes on your test suite
- **Identify** which tests need updates when specifications change
- **Maintain** up-to-date baseline specifications for accurate change detection

## 📋 Prerequisites

- Python 3.8+ with required dependencies installed
- Internet connection to download latest specifications
- Git repository with TCK test suite

## 🔄 Complete Workflow

### Step 1: Check for Specification Changes

**Run the specification change detection:**
```bash
# Check against main branch (default)
./check_spec_changes.py

# Check against specific tag/branch
./check_spec_changes.py --branch "v1.2.0"

# Check against development branch
./check_spec_changes.py --branch "dev"
```

**What this does:**
- Downloads A2A specifications from GitHub (main branch or specified branch/tag)
- Compares them with your current baseline specifications
- Generates a detailed analysis report
- Identifies which tests may be affected by changes

**Output files created:**
- `spec_analysis_report.md` - Detailed change analysis and recommendations
- Exit code indicates change severity:
  - `0` - No changes detected
  - `1` - Changes detected (review recommended) 
  - `2` - Breaking changes detected (immediate action required)

### Step 2: Review the Analysis Report

**Open and review the generated report:**
```bash
# View the detailed analysis
cat spec_analysis_report.md
```

**The report contains:**
- **Executive Summary**: High-level overview of changes and risk assessment
- **Specification Changes**: Detailed breakdown of all modifications
  - Breaking changes (removed requirements, methods)
  - Behavioral changes (new MUST requirements)
  - Non-breaking additions (new optional features)
  - Documentation updates
- **Test Impact Analysis**: Lists of potentially affected tests by category
- **Test Coverage Analysis**: Current coverage metrics and gaps
- **Recommendations**: Prioritized action items with timelines

**Understanding change classifications:**
- 🔴 **Breaking Changes (10pts)**: Require immediate test updates
- 🟡 **Behavioral Changes (5pts)**: May require test modifications
- 🟢 **Additions (2pts)**: May need new tests for complete coverage
- 📝 **Documentation (1pt)**: Usually no test changes needed

### Step 3: Fix Affected Tests

**Based on the report's recommendations:**

1. **Review affected tests** listed in the "Test Impact Analysis" section
2. **Update test implementations** to match specification changes
3. **Add new tests** for newly introduced requirements
4. **Remove obsolete tests** for removed specification features

**Test categories to check:**
- `tests/mandatory/` - Core compliance tests
- `tests/optional/capabilities/` - Capability-specific tests  
- `tests/optional/quality/` - Quality and robustness tests
- `tests/optional/features/` - Optional feature tests

**Validate your fixes:**
```bash
# Run affected tests to ensure they pass
./run_tck.py --sut-url http://localhost:9999 --category mandatory
./run_tck.py --sut-url http://localhost:9999 --category capabilities
```

### Step 4: Update Baseline Specifications

**After fixing all identified issues, update your baseline:**

```bash
# Update to latest from main branch
./update_current_spec.py --version "v1.3.0"

# Update to specific tag (auto-detects version from tag name)
./update_current_spec.py --branch "v1.3.0"

# Update to custom branch with custom version
./update_current_spec.py --branch "dev" --version "dev-snapshot-2024"
```

**What this does:**
- Downloads A2A specifications from GitHub (main branch or specified branch/tag)
- Backs up your current specifications to `current_spec_backup/`
- Updates baseline specifications in `current_spec/`
- Creates version tracking metadata
- Auto-detects version from branch/tag name if `--version` not specified

**Files updated:**
- `current_spec/A2A_SPECIFICATION.md` - Latest markdown specification
- `current_spec/a2a_schema.json` - Latest JSON schema
- `current_spec/version_info.json` - Version tracking metadata
- `current_spec_backup/` - Backup of previous specifications

### Step 5: Verify the Update

**Confirm no changes are detected after update:**
```bash
./check_spec_changes.py
```

**Expected result:** Exit code `0` with message "No changes detected"

**Commit your changes:**
```bash
git add current_spec/ tests/
git commit -m "Update to A2A specification v1.3.0

- Updated baseline specifications
- Fixed affected tests based on change analysis
- Maintained full test coverage"
git tag "spec-v1.3.0"
```

## 🛠️ Advanced Usage

### Generate Summary Report Only

For quick overview without detailed analysis:
```bash
./check_spec_changes.py --summary-only --output summary.md
```

### Export Analysis as JSON

For programmatic processing:
```bash
./check_spec_changes.py --json-export analysis.json
```

### Check Against Specific Branch/Tag

To compare against specific versions:
```bash
# Check against tagged release
./check_spec_changes.py --branch "v1.2.0"

# Check against development branch  
./check_spec_changes.py --branch "dev" --summary-only
```

### Preview Updates Without Applying

To see what would change:
```bash
./update_current_spec.py --dry-run --version "v1.3.0"

# Preview update from specific branch
./update_current_spec.py --dry-run --branch "v1.3.0"
```

### Force Update (Even Without Changes)

To update regardless of change detection:
```bash
./update_current_spec.py --force --version "v1.3.0"

# Force update from specific branch
./update_current_spec.py --force --branch "v1.3.0"
```

### Compare with Custom Specification URLs

For testing against custom repositories or branches:
```bash
./check_spec_changes.py \
  --json-url https://raw.githubusercontent.com/org/repo/dev/schema.json \
  --md-url https://raw.githubusercontent.com/org/repo/dev/spec.md
```

### Roll Back to Previous Specification Version

To downgrade your baseline to an older specification version:

```bash
# Roll back to a specific git tag (simplified)
./update_current_spec.py --branch "v1.2.0"

# Roll back to a specific commit hash
./update_current_spec.py --branch "abc123def" --version "rollback-abc123def"

# Advanced: Use custom URLs for non-standard repositories
./update_current_spec.py \
  --json-url https://raw.githubusercontent.com/fork/A2A/custom/specification/json/a2a.json \
  --md-url https://raw.githubusercontent.com/fork/A2A/custom/docs/specification.md \
  --version "custom-fork"
```

**Use cases for rollback:**
- **Compatibility issues**: New spec version breaks your implementation
- **Testing**: Validate against specific historical versions
- **Regression**: Previous version had better test coverage
- **Debugging**: Isolate when issues were introduced

**After rollback**, run change detection to understand what changed:
```bash
./check_spec_changes.py
```
This will show you the differences between your rolled-back version and the latest specification.

## 📊 Understanding Report Sections

### Executive Summary
- **Total Impact Score**: Weighted sum of all changes (higher = more impactful)
- **Risk Level**: LOW/MEDIUM/HIGH based on breaking changes
- **Priority Indicators**: Immediate/Soon/Planned action timelines

### Specification Changes
- **Changes by Category**: Grouped by impact level
- **Detailed Diff**: Line-by-line changes with context
- **Requirement Analysis**: New/modified/removed requirements

### Test Impact Analysis
- **Breaking Changes**: Tests requiring immediate updates
- **Behavioral Changes**: Tests needing review and possible modification
- **New Features**: Opportunities for additional test coverage
- **Documentation**: Tests with outdated specification references

### Test Coverage Analysis
- **Overall Metrics**: Percentage of requirements covered by tests
- **Coverage by Level**: MUST/SHOULD/MAY requirement coverage
- **Gap Analysis**: Requirements without test coverage
- **Documentation Coverage**: Tests with specification references

## 🚨 Troubleshooting

### Network Issues
```bash
# Check if specifications download successfully
./check_spec_changes.py --verbose
```
**Solution**: Tool automatically falls back to cached specifications

### Missing Baseline Specifications

**Problem**: You get errors like "Current markdown spec not found" or "Current JSON schema not found" when running `./check_spec_changes.py`.

**Cause**: The `current_spec/` directory is missing the baseline specification files that the change detection system needs for comparison.

**Solution**: Initialize your baseline specifications:
```bash
# Download and set current specifications as your baseline
./update_current_spec.py --version "baseline"
```

**What this does:**
- Downloads the latest A2A specifications from GitHub
- Creates the `current_spec/` directory if it doesn't exist
- Saves specifications as your starting baseline:
  - `current_spec/A2A_SPECIFICATION.md` 
  - `current_spec/a2a_schema.json`
  - `current_spec/version_info.json` (with version "baseline")

**After initialization**, you can run change detection:
```bash
./check_spec_changes.py
```
This should now show "No changes detected" since you just established the baseline.

**When this happens:**
- First time setting up the specification tracking system
- After accidentally deleting the `current_spec/` directory
- When starting with a fresh TCK installation

### Large Number of Changes
```bash
# Generate summary for manageable overview
./check_spec_changes.py --summary-only
```
**Approach**: Address breaking changes first, then behavioral changes

### Test Failures After Updates
```bash
# Run specific test category with verbose output
./run_tck.py --sut-url URL --category mandatory --verbose
```
**Solution**: Review test failures against specification changes in the report

### Rollback After Problematic Update

**Problem**: After updating to a new specification version, tests are failing or your implementation has compatibility issues.

**Solution**: Roll back to the previous working version:

```bash
# Check your backup to see the previous version
cat current_spec_backup/version_info.json

# Roll back to the previous version (example with v1.2.0)
./update_current_spec.py \
  --json-url https://raw.githubusercontent.com/google/A2A/v1.2.0/specification/json/a2a.json \
  --md-url https://raw.githubusercontent.com/google/A2A/v1.2.0/docs/specification.md \
  --version "v1.2.0"
```

**Alternative**: Restore from automatic backup:
```bash
# Copy backup files back to current_spec/
cp current_spec_backup/* current_spec/
```

**After rollback**: Address the issues before attempting to update again.

## 🎯 Best Practices

### Regular Monitoring
```bash
# Weekly specification check (in CI/CD)
./check_spec_changes.py --summary-only
```

### Systematic Updates
1. **Always review the full report** before making changes
2. **Fix tests incrementally** by change category (breaking → behavioral → additions)
3. **Validate fixes** before updating baseline
4. **Tag versions** for change tracking

### Change Management
- **Breaking changes**: Update immediately, block deployments if needed
- **Behavioral changes**: Plan updates within sprint cycles
- **Additions**: Consider in next feature planning
- **Documentation**: Update during regular maintenance

## 🔗 Integration with CI/CD

### Specification Change Detection
```bash
#!/bin/bash
# Check for specification changes in CI
./check_spec_changes.py --summary-only
exit_code=$?

if [ $exit_code -eq 2 ]; then
    echo "🚨 Breaking specification changes detected"
    echo "📋 Review required before deployment"
    exit 1
elif [ $exit_code -eq 1 ]; then
    echo "⚠️ Specification changes detected"
    echo "📋 Consider updating tests"
fi
```

### Automated Baseline Updates
```bash
#!/bin/bash
# Automated specification update (with human review)
if ./check_spec_changes.py --summary-only; then
    echo "✅ Specifications up to date"
else
    echo "📥 Generating change analysis..."
    ./check_spec_changes.py --output spec_changes_$(date +%Y%m%d).md
    echo "📋 Review report and run ./update_current_spec.py when ready"
fi
```

---

## ℹ️ Quick Reference

| Command | Purpose |
|---------|---------|
| `./check_spec_changes.py` | Check for and analyze specification changes (main branch) |
| `./check_spec_changes.py --branch "v1.x"` | Check against specific branch/tag |
| `./check_spec_changes.py --summary-only` | Quick change overview |
| `./analyze_test_coverage.py` | **Analyze current test coverage gaps** |
| `./analyze_test_coverage.py --summary-only` | **Quick coverage summary** |
| `./update_current_spec.py --version "v1.x"` | Update baseline specifications (main branch) |
| `./update_current_spec.py --branch "v1.x"` | Update to specific branch/tag (auto-sets version) |
| `./update_current_spec.py --dry-run` | Preview what would be updated |
| `cp current_spec_backup/* current_spec/` | Restore from automatic backup |

**File Locations:**
- `current_spec/` - Your baseline specifications
- `current_spec_backup/` - Automatic backups
- `spec_analysis_report.md` - Change analysis output
- `spec_tracker/cache/` - Downloaded specification cache

## 🧪 Test Coverage Analysis

In addition to tracking specification changes, you can analyze how well your current test suite covers the specification:

### Analyze Test Coverage Gaps

```bash
# Quick coverage summary
./analyze_test_coverage.py --summary-only

# Detailed coverage analysis  
./analyze_test_coverage.py

# Export data for automation
./analyze_test_coverage.py --json-export coverage.json
```

**What this analyzes:**
- **Requirement Coverage**: Which spec requirements lack tests
- **Method Coverage**: JSON-RPC methods without adequate testing
- **Error Coverage**: Error scenarios not tested
- **Test Quality**: Documentation and specification alignment
- **Orphaned Tests**: Tests without clear specification references

**Use cases:**
- **Before releases**: Ensure adequate test coverage
- **After spec updates**: Identify new testing needs  
- **Regular quality reviews**: Maintain high test standards
- **Gap analysis**: Find undertested areas

**See [Test Coverage Analysis](docs/TEST_COVERAGE_ANALYSIS.md) for complete documentation.**

---

This workflow ensures your TCK test suite stays synchronized with A2A specification evolution while maintaining comprehensive validation coverage. 