#!/usr/bin/env python3
"""
Run A2A optional feature tests.

=== WHAT ARE FEATURE TESTS? ===

Feature tests validate optional behaviors and implementation-specific features
that go beyond the core A2A specification. These tests are ALWAYS OPTIONAL
and never affect A2A compliance.

Feature tests differ from:
- **Mandatory tests**: Core spec requirements (always must pass)
- **Capability tests**: Declared features (must work if claimed)
- **Quality tests**: Production robustness (performance/reliability)

=== FEATURE AREAS TESTED ===

1. **Business Logic Validation**
   - Domain-specific behavior validation
   - Custom error handling patterns
   - Implementation-specific workflows
   - Extended validation rules

2. **Reference Implementation Features**
   - Task ID formats and patterns
   - Extended metadata handling
   - Custom field support
   - Implementation conveniences

3. **SDK-Specific Behaviors**
   - SDK limitation handling
   - Workaround validation
   - SDK-specific optimizations
   - Implementation helpers

4. **Utility & Helper Functions**
   - Agent Card utilities
   - Data transformation helpers
   - Convenience methods
   - Developer experience features

=== WHY FEATURE TESTS MATTER ===

While not required for A2A compliance, optional features can:
- Improve developer experience
- Add value for specific use cases
- Demonstrate implementation completeness
- Validate custom behaviors
- Test implementation-specific optimizations

These tests help validate that optional features work correctly when present,
without penalizing implementations that don't include them.

Usage:
    ./run_features.py --sut-url http://localhost:9999
    ./run_features.py --sut-url http://localhost:9999 --verbose
"""

import subprocess
import sys
import argparse
from pathlib import Path

def run_feature_tests(sut_url: str, verbose: bool = False, generate_report: bool = False):
    """Run optional feature test suite."""
    
    print("=" * 70)
    print("🎨 A2A TCK FEATURE TEST SUITE")
    print("Validates optional behaviors and implementation-specific features")
    print("=" * 70)
    print()
    print("FEATURE TEST PURPOSE:")
    print("✅ Validate optional behaviors work correctly")
    print("✅ Test implementation-specific features")
    print("✅ Verify convenience and utility functions")
    print("✅ Assess implementation completeness")
    print()
    print("NOTE: Feature test failures are informational only!")
    print("They don't affect A2A compliance or capability validation.")
    print()
    
    # Build pytest command
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/optional/features/",
        f"--sut-url={sut_url}",
        "-m", "optional_feature",
        "--tb=short",
    ]
    
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    if generate_report:
        cmd.extend(["--html=feature_test_report.html", "--self-contained-html"])
    
    print(f"Running: {' '.join(cmd)}")
    print()
    
    # Run the tests
    result = subprocess.run(cmd)
    
    print()
    print("=" * 70)
    
    if result.returncode == 0:
        print("✅ ALL FEATURE TESTS PASSED")
        print("🌟 Comprehensive implementation!")
        print()
        print("This indicates:")
        print("- Optional features work correctly when present")
        print("- Good implementation completeness")
        print("- Enhanced developer experience")
        print("- Well-implemented convenience features")
        print("- Thorough implementation attention to detail")
        print()
        print("Your implementation includes valuable optional features!")
    else:
        print("ℹ️  SOME FEATURE TESTS FAILED")
        print("📋 Optional behaviors not implemented or not working")
        print()
        print("Impact assessment:")
        print("✅ A2A compliance: Not affected")
        print("✅ Capability validation: Not affected") 
        print("ℹ️  Feature completeness: Some optional features missing/broken")
        print()
        print("What this means:")
        print("- Some optional features are not implemented (perfectly fine)")
        print("- Some optional features are implemented but have issues")
        print("- Implementation focuses on core functionality")
        print()
        print("Common scenarios:")
        print()
        print("🎯 Business Logic Features:")
        print("   → Implementation may not include custom business logic")
        print("   → Domain-specific features not relevant to your use case")
        print()
        print("🔧 Utility Features:")
        print("   → Helper functions not implemented (acceptable)")
        print("   → Convenience methods not provided")
        print()
        print("📦 SDK Features:")
        print("   → SDK-specific optimizations not used")
        print("   → Implementation uses different approaches")
        print()
        print("Remember: Feature tests are purely informational!")
    
    print("=" * 70)
    
    return result.returncode

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run A2A TCK optional feature tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
FEATURE TEST CATEGORIES:

🎯 Business Logic Features
   - Domain-specific validation
   - Custom workflow behaviors
   - Extended business rules

🔧 Utility & Helper Features  
   - Agent Card utilities
   - Data transformation helpers
   - Convenience methods

📦 SDK-Specific Features
   - SDK optimization validation
   - Implementation-specific behaviors
   - Developer experience features

🎨 Implementation Completeness
   - Optional behavior validation
   - Extended functionality testing
   - Custom feature validation

Examples:
  ./run_features.py --sut-url http://localhost:9999
  ./run_features.py --sut-url http://localhost:9999 --verbose --report
  
IMPORTANT: Feature test results are purely informational!
They don't affect compliance, capabilities, or quality assessments.

Exit Codes:
  0 = All optional features work correctly (comprehensive implementation)
  1 = Some optional features missing/broken (still perfectly valid)
        """
    )
    
    parser.add_argument(
        "--sut-url",
        required=True,
        help="URL of the SUT's A2A JSON-RPC endpoint"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose test output"
    )
    
    parser.add_argument(
        "--report",
        action="store_true", 
        help="Generate HTML feature test report"
    )
    
    args = parser.parse_args()
    
    # Validate that feature test directory exists
    feature_dir = Path("tests/optional/features")
    if not feature_dir.exists():
        print("❌ Error: tests/optional/features/ directory not found")
        print("Make sure you're running from the TCK root directory")
        sys.exit(1)
    
    # Run the tests
    exit_code = run_feature_tests(
        sut_url=args.sut_url,
        verbose=args.verbose,
        generate_report=args.report
    )
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main() 