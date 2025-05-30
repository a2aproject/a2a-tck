#!/usr/bin/env python3
"""
Run A2A implementation quality tests.

=== WHAT ARE QUALITY TESTS? ===

Quality tests validate implementation robustness, resilience, and production-readiness.
These tests are ALWAYS OPTIONAL and never block A2A compliance, but they indicate
whether an implementation is ready for real-world production use.

Quality tests differ from:
- **Mandatory tests**: Must always pass for compliance
- **Capability tests**: Must pass if capability declared
- **Feature tests**: Validate optional behaviors

=== QUALITY AREAS TESTED ===

1. **Concurrency & Threading**
   - Multiple simultaneous requests
   - Concurrent operations on same task
   - Race condition handling
   - Thread safety validation

2. **Error Recovery & Resilience**
   - Recovery from transient failures
   - Graceful degradation under load
   - Proper error propagation
   - Resource cleanup after errors

3. **Edge Case Handling**  
   - Very long strings and large payloads
   - Boundary values and limits
   - Unicode and special character handling
   - Malformed but parseable input

4. **Performance & Scalability**
   - Response time under load
   - Memory usage patterns
   - Resource leak detection
   - Timeout handling

=== WHY QUALITY MATTERS ===

An implementation can be "A2A compliant" but still unsuitable for production:
- Crashes under load
- Has race conditions
- Leaks memory or resources  
- Poor error handling
- Doesn't scale

Quality tests help identify these issues before deployment.

Usage:
    ./run_quality.py --sut-url http://localhost:9999
    ./run_quality.py --sut-url http://localhost:9999 --verbose
"""

import subprocess
import sys
import argparse
from pathlib import Path

def run_quality_tests(sut_url: str, verbose: bool = False, generate_report: bool = False):
    """Run implementation quality test suite."""
    
    print("=" * 70)
    print("🛡️  A2A TCK QUALITY TEST SUITE")
    print("Validates implementation robustness and production-readiness")
    print("=" * 70)
    print()
    print("QUALITY TEST PURPOSE:")
    print("✅ Identify robustness issues before production")
    print("✅ Validate concurrency and error handling")  
    print("✅ Test edge cases and boundary conditions")
    print("✅ Assess production-readiness")
    print()
    print("NOTE: Quality test failures do NOT block A2A compliance!")
    print("They indicate areas for improvement in production environments.")
    print()
    
    # Build pytest command
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/optional/quality/",
        f"--sut-url={sut_url}",
        "-m", "quality_basic",
        "--tb=short",
    ]
    
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    if generate_report:
        cmd.extend(["--html=quality_test_report.html", "--self-contained-html"])
    
    print(f"Running: {' '.join(cmd)}")
    print()
    
    # Run the tests
    result = subprocess.run(cmd)
    
    print()
    print("=" * 70)
    
    if result.returncode == 0:
        print("✅ ALL QUALITY TESTS PASSED")
        print("🏆 Implementation is production-ready!")
        print()
        print("This indicates:")
        print("- Robust error handling and recovery")
        print("- Good concurrency and thread safety")
        print("- Proper edge case handling")
        print("- Suitable for production deployment")
        print("- High implementation quality")
        print()
        print("Your implementation goes beyond basic A2A compliance!")
    else:
        print("⚠️  QUALITY ISSUES IDENTIFIED")
        print("📝 Areas for improvement before production deployment")
        print()
        print("Impact assessment:")
        print("✅ A2A compliance: Still valid (quality doesn't affect compliance)")
        print("⚠️  Production readiness: May need attention")
        print()
        print("Common quality issues and recommendations:")
        print()
        print("🔄 Concurrency Issues:")
        print("   → Add proper locking/synchronization")
        print("   → Review thread safety in shared resources")
        print()
        print("💥 Error Handling Issues:")
        print("   → Improve error recovery mechanisms")
        print("   → Add proper resource cleanup")
        print("   → Validate error propagation")
        print()
        print("🎯 Edge Case Issues:")
        print("   → Add input validation and sanitization")
        print("   → Improve boundary condition handling")
        print("   → Test with larger/unusual inputs")
        print()
        print("Remember: These are improvement suggestions, not compliance blockers!")
    
    print("=" * 70)
    
    return result.returncode

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run A2A TCK implementation quality tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
QUALITY TEST CATEGORIES:

🔄 Concurrency & Threading
   - Multiple simultaneous requests
   - Thread safety validation
   - Race condition detection

💥 Error Recovery & Resilience  
   - Recovery from failures
   - Resource cleanup validation
   - Error propagation testing

🎯 Edge Case Handling
   - Boundary value testing
   - Large payload handling
   - Special character validation

⚡ Performance & Scalability
   - Load testing
   - Memory usage validation
   - Timeout handling

Examples:
  ./run_quality.py --sut-url http://localhost:9999
  ./run_quality.py --sut-url http://localhost:9999 --verbose --report
  
IMPORTANT: Quality test failures do NOT affect A2A compliance!
They indicate areas for production improvement.

Exit Codes:
  0 = High quality implementation (production-ready)
  1 = Quality issues found (improvement opportunities)
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
        help="Generate HTML quality test report"
    )
    
    args = parser.parse_args()
    
    # Validate that quality test directory exists
    quality_dir = Path("tests/optional/quality")
    if not quality_dir.exists():
        print("❌ Error: tests/optional/quality/ directory not found")
        print("Make sure you're running from the TCK root directory")
        sys.exit(1)
    
    # Run the tests
    exit_code = run_quality_tests(
        sut_url=args.sut_url,
        verbose=args.verbose,
        generate_report=args.report
    )
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main() 