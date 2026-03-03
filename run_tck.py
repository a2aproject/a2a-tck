#!/usr/bin/env python3
"""A2A Protocol Technology Compatibility Kit (TCK) - Test Runner.

Runs parametrized conformance tests against an A2A-compliant agent.
Tests are organized by RFC 2119 requirement level (MUST/SHOULD/MAY)
and executed across all configured transports (gRPC, JSON-RPC, HTTP+JSON).

Usage:
    ./run_tck.py --sut-host http://localhost:9999
    ./run_tck.py --sut-host http://localhost:9999 --transport jsonrpc
    ./run_tck.py --sut-host http://localhost:9999 --transport grpc,jsonrpc -v
    ./run_tck.py --sut-host http://localhost:9999 --level must
    ./run_tck.py --sut-host http://localhost:9999 --compliance-report report.json
    ./run_tck.py --sut-host http://localhost:9999 --compliance-report report.html
"""

from __future__ import annotations

import argparse
import subprocess
import sys

from pathlib import Path


REPORTS_DIR = Path("reports")

# Maps --level choices to pytest -k expressions
LEVEL_FILTERS: dict[str, str] = {
    "must": "test_must_requirement",
    "should": "test_should_requirement",
    "may": "test_may_requirement",
}


def build_pytest_command(args: argparse.Namespace) -> list[str]:
    """Build the pytest command line from parsed arguments."""
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/compatibility/",
        f"--sut-host={args.sut_host}",
        "--tb=short",
    ]

    # Transport filter
    if args.transport:
        cmd.append(f"--transport={args.transport}")

    # Compliance report
    if args.compliance_report:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORTS_DIR / args.compliance_report
        cmd.append(f"--compliance-report={report_path}")

    # Requirement level filter
    if args.level:
        k_expr = LEVEL_FILTERS[args.level]
        cmd.extend(["-k", k_expr])

    # Verbosity
    if args.verbose_log:
        cmd.extend(["-v", "-s", "--log-cli-level=INFO"])
    elif args.verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")

    # HTML report
    if args.report:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORTS_DIR / "tck_report.html"
        cmd.extend([f"--html={report_path}", "--self-contained-html"])

    # Extra pytest arguments
    if args.pytest_args:
        cmd.extend(args.pytest_args)

    return cmd


def main() -> None:
    """Parse arguments and run the TCK pytest suite."""
    parser = argparse.ArgumentParser(
        description="A2A Protocol TCK - Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  # Run all tests against a local agent
  ./run_tck.py --sut-host http://localhost:9999

  # Run only MUST-level requirements
  ./run_tck.py --sut-host http://localhost:9999 --level must

  # Run only JSON-RPC transport
  ./run_tck.py --sut-host http://localhost:9999 --transport jsonrpc

  # Run gRPC and JSON-RPC transports with verbose output
  ./run_tck.py --sut-host http://localhost:9999 --transport grpc,jsonrpc -v

  # Generate compliance report (JSON or HTML based on file extension)
  ./run_tck.py --sut-host http://localhost:9999 --compliance-report compliance.json
  ./run_tck.py --sut-host http://localhost:9999 --compliance-report compliance.html

  # Pass extra pytest flags (after --)
  ./run_tck.py --sut-host http://localhost:9999 -- -x --pdb

Requirement levels:
  must    - MUST requirements: hard failure if not met
  should  - SHOULD requirements: expected failure (xfail), not hard fail
  may     - MAY requirements: skipped if agent doesn't declare the capability
""",
    )

    parser.add_argument(
        "--sut-host",
        required=True,
        help="Hostname/URL of the System Under Test (e.g. http://localhost:9999)",
    )
    parser.add_argument(
        "--transport",
        default=None,
        help=(
            'Transport filter: omit for all transports, or comma-separated '
            'list (e.g. "grpc,jsonrpc,http_json")'
        ),
    )
    parser.add_argument(
        "--level",
        choices=["must", "should", "may"],
        default=None,
        help="Run only requirements at this RFC 2119 level",
    )
    parser.add_argument(
        "--compliance-report",
        metavar="FILENAME",
        default=None,
        help="Output filename for compliance report (written to reports/; .html for HTML, .json for JSON)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose pytest output",
    )
    parser.add_argument(
        "--verbose-log",
        action="store_true",
        help="Verbose output with log capture (adds -v -s --log-cli-level=INFO)",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate HTML test report in reports/",
    )
    parser.add_argument(
        "pytest_args",
        nargs="*",
        help="Additional pytest arguments (pass after --)",
    )

    args = parser.parse_args()

    # Validate test directory exists
    if not Path("tests/compatibility").exists():
        print("Error: tests/compatibility/ directory not found")
        print("Make sure you're running from the TCK root directory")
        sys.exit(1)

    cmd = build_pytest_command(args)

    print(f"Command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, check=False)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
