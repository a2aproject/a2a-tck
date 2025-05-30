#!/usr/bin/env python3
"""
Run only mandatory A2A compliance tests.

This script runs all tests that MUST pass for A2A compliance:
- JSON-RPC 2.0 compliance tests (tests/mandatory/jsonrpc/)
- A2A protocol mandatory tests (tests/mandatory/protocol/)

If ANY mandatory test fails, the SDK is NOT A2A compliant.

Usage:
    ./run_mandatory.py --sut-url http://localhost:9999
    ./run_mandatory.py --sut-url http://localhost:9999 --verbose
    ./run_mandatory.py --sut-url http://localhost:9999 --report
"""

import subprocess
import sys
import argparse
from pathlib import Path

def run_mandatory_tests(sut_url: str, verbose: bool = False, generate_report: bool = False):
    """Run mandatory test suite."""
    
    print("=" * 70)
    print("🔴 A2A TCK MANDATORY TEST SUITE")
    print("SDK MUST pass ALL of these tests for A2A compliance")
    print("=" * 70)
    print()
    
    # Build pytest command
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/mandatory/",  # Run all mandatory tests
        f"--sut-url={sut_url}",
        "-m", "mandatory_jsonrpc or mandatory_protocol",  # Double-check with markers
        "--tb=short",
    ]
    
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    if generate_report:
        cmd.extend(["--html=mandatory_compliance_report.html", "--self-contained-html"])
    
    print(f"Running: {' '.join(cmd)}")
    print()
    
    # Run the tests
    result = subprocess.run(cmd)
    
    print()
    print("=" * 70)
    
    if result.returncode == 0:
        print("✅ SDK PASSED ALL MANDATORY TESTS")
        print("🎉 Implementation is A2A COMPLIANT!")
        print()
        print("Next steps:")
        print("- Run optional tests: ./run_tck.py --sut-url {} --test-scope all".format(sut_url))
        print("- Generate full report: ./run_tck.py --sut-url {} --report".format(sut_url))
    else:
        print("❌ SDK FAILED MANDATORY TESTS")
        print("🚫 Implementation is NOT A2A COMPLIANT")
        print()
        print("What this means:")
        print("- The SDK does not meet A2A specification requirements")
        print("- Mandatory failures must be fixed before claiming A2A compliance")
        print("- Check the test output above for specific failures")
        print()
        print("Common issues:")
        print("- historyLength parameter not implemented (test_tasks_get_with_history_length)")
        print("- Missing required Agent Card fields (test_mandatory_fields_present)")
        print("- JSON-RPC 2.0 compliance issues (test_rejects_*)")
    
    print("=" * 70)
    
    return result.returncode

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run A2A TCK mandatory compliance tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ./run_mandatory.py --sut-url http://localhost:9999
  ./run_mandatory.py --sut-url http://localhost:9999 --verbose --report
  
Test Categories:
  - JSON-RPC 2.0 Compliance (tests/mandatory/jsonrpc/)
  - A2A Protocol Requirements (tests/mandatory/protocol/)
  
Exit Codes:
  0 = All mandatory tests passed (A2A compliant)
  1 = One or more mandatory tests failed (NOT A2A compliant)
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
        help="Generate HTML compliance report"
    )
    
    args = parser.parse_args()
    
    # Validate that mandatory test directories exist
    mandatory_dir = Path("tests/mandatory")
    if not mandatory_dir.exists():
        print("❌ Error: tests/mandatory/ directory not found")
        print("Make sure you're running from the TCK root directory")
        sys.exit(1)
    
    jsonrpc_dir = mandatory_dir / "jsonrpc"
    protocol_dir = mandatory_dir / "protocol"
    
    if not jsonrpc_dir.exists() or not protocol_dir.exists():
        print("❌ Error: Mandatory test directories not found")
        print("Expected: tests/mandatory/jsonrpc/ and tests/mandatory/protocol/")
        sys.exit(1)
    
    # Run the tests
    exit_code = run_mandatory_tests(
        sut_url=args.sut_url,
        verbose=args.verbose,
        generate_report=args.report
    )
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main() 