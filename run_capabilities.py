#!/usr/bin/env python3
"""
Run A2A capability-based tests.

=== WHAT ARE CAPABILITY TESTS? ===

Capability tests validate features that are DECLARED in the Agent Card.
These tests have special logic:

- **SKIP** if capability not declared (perfectly fine)
- **MANDATORY** if capability is declared but doesn't work (false advertising)

This is different from mandatory tests (which always must pass) and quality tests
(which are always optional). Capability tests are "conditional mandatory" - they
become mandatory once you claim to support them.

=== CAPABILITIES TESTED ===

1. **Streaming** (capabilities.streaming = true)
   - message/stream method must work
   - tasks/resubscribe method must work
   - Server-sent events must function properly

2. **Push Notifications** (capabilities.pushNotifications = true)  
   - tasks/pushNotificationConfig/set must work
   - tasks/pushNotificationConfig/get must work
   - Notification delivery must function

3. **File Modalities** (defaultInputModes/defaultOutputModes contains "file")
   - message/send with file parts must work
   - File upload/download must function

4. **Data Modalities** (defaultInputModes/defaultOutputModes contains "data")
   - message/send with data parts must work  
   - Binary data handling must function

5. **Authentication** (authentication schemes declared)
   - Declared auth schemes must actually work
   - Security validation must pass

=== WHY THIS MATTERS ===

Capability failures indicate "false advertising" - you're claiming to support
features in your Agent Card that don't actually work. This misleads clients
and breaks interoperability.

Usage:
    ./run_capabilities.py --sut-url http://localhost:9999
    ./run_capabilities.py --sut-url http://localhost:9999 --verbose
"""

import subprocess
import sys
import argparse
from pathlib import Path

def run_capability_tests(sut_url: str, verbose: bool = False, generate_report: bool = False):
    """Run capability-based test suite."""
    
    print("=" * 70)
    print("🔄 A2A TCK CAPABILITY TEST SUITE")
    print("Validates declared capabilities work correctly")
    print("=" * 70)
    print()
    print("CAPABILITY TEST LOGIC:")
    print("✅ SKIP if capability not declared (this is allowed)")
    print("❌ FAIL if capability declared but not working (false advertising)")
    print()
    print("These tests become MANDATORY once you declare the capability!")
    print()
    
    # Build pytest command
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/optional/capabilities/",
        f"--sut-url={sut_url}",
        "-m", "optional_capability",
        "--tb=short",
    ]
    
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    if generate_report:
        cmd.extend(["--html=capability_test_report.html", "--self-contained-html"])
    
    print(f"Running: {' '.join(cmd)}")
    print()
    
    # Run the tests
    result = subprocess.run(cmd)
    
    print()
    print("=" * 70)
    
    if result.returncode == 0:
        print("✅ ALL DECLARED CAPABILITIES WORK CORRECTLY")
        print("🎉 No false advertising detected!")
        print()
        print("This means:")
        print("- All declared capabilities are properly implemented")
        print("- No misleading capability claims in Agent Card")
        print("- Clients can trust your capability declarations")
        print("- Excellent interoperability compliance")
    else:
        print("❌ CAPABILITY DECLARATION ISSUES FOUND")
        print("🚫 False advertising detected!")
        print()
        print("What this means:")
        print("- You're claiming capabilities that don't work")
        print("- This breaks client expectations and interoperability")
        print("- Clients may attempt to use features that will fail")
        print()
        print("How to fix:")
        print("1. Fix the implementation to support declared capabilities, OR")
        print("2. Remove capability declarations from your Agent Card")
        print()
        print("Common capability issues:")
        print("- streaming: true but message/stream method fails")
        print("- pushNotifications: true but config methods fail")
        print("- File modality declared but file parts not supported")
        print("- Authentication schemes declared but don't work")
    
    print("=" * 70)
    
    return result.returncode

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run A2A TCK capability validation tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
CAPABILITY TEST CATEGORIES:

🔄 Streaming Capabilities
   - Validates message/stream and tasks/resubscribe
   - Required if capabilities.streaming = true

📢 Push Notification Capabilities  
   - Validates push notification config methods
   - Required if capabilities.pushNotifications = true

📁 File/Data Modalities
   - Validates file and data part handling
   - Required if modalities declared in Agent Card

🔐 Authentication Capabilities
   - Validates declared authentication schemes
   - Required if authentication methods listed

Examples:
  ./run_capabilities.py --sut-url http://localhost:9999
  ./run_capabilities.py --sut-url http://localhost:9999 --verbose --report
  
Exit Codes:
  0 = All declared capabilities work correctly (honest Agent Card)
  1 = Capability declaration issues found (false advertising)
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
        help="Generate HTML capability test report"
    )
    
    args = parser.parse_args()
    
    # Validate that capability test directory exists
    capability_dir = Path("tests/optional/capabilities")
    if not capability_dir.exists():
        print("❌ Error: tests/optional/capabilities/ directory not found")
        print("Make sure you're running from the TCK root directory")
        sys.exit(1)
    
    # Run the tests
    exit_code = run_capability_tests(
        sut_url=args.sut_url,
        verbose=args.verbose,
        generate_report=args.report
    )
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main() 