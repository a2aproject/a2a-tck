# TCK Utility Scripts

This directory contains scripts used for maintaining the A2A Technology Compatibility Kit (TCK), primarily related to managing specification updates and analyzing test coverage.

## User-Facing Scripts

These scripts are intended to be run manually by TCK maintainers.

### `check_spec_changes.py`

Analyzes and reports the differences between the current baseline A2A specification and a target version (e.g., a branch or tag in the official repository). This is the first step in the specification update workflow.

*   **Usage**: `util_scripts/check_spec_changes.py [options]`
*   **Detailed Documentation**: See the [Specification Update Workflow](../docs/SPEC_UPDATE_WORKFLOW.md).

### `analyze_test_coverage.py`

Analyzes the existing test suite against the current baseline specification to identify coverage gaps, quality issues, and orphaned tests. This helps ensure that the TCK provides comprehensive validation.

*   **Usage**: `util_scripts/analyze_test_coverage.py [options]`
*   **Detailed Documentation**: See the [Test Coverage Analysis Guide](../docs/TEST_COVERAGE_ANALYSIS.md).

### `update_current_spec.py`

Downloads and updates the local baseline specification files (`current_spec/`) to a newer version. This script is typically run after analyzing changes and updating the test suite accordingly.

*   **Usage**: `util_scripts/update_current_spec.py [options]`
*   **Detailed Documentation**: See the [Specification Update Workflow](../docs/SPEC_UPDATE_WORKFLOW.md).

## Internal Modules

The following files are not intended to be executed directly. They are modules imported by other scripts (`run_tck.py`).

*   `__init__.py`: Marks this directory as a Python package.
*   `compliance_levels.py`: Defines the logic and thresholds for the different A2A compliance levels.
*   `generate_compliance_report.py`: Contains the logic for generating the final JSON compliance report. 