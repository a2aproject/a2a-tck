#!/usr/bin/env python3
"""
A2A Protocol Technology Compatibility Kit (TCK) Test Runner

This script provides a simple way to run the A2A TCK tests against a System Under Test (SUT).
It configures and executes pytest with the appropriate options and arguments.

Usage:
    python run_tck.py --sut-url <SUT_URL> [OPTIONS]

Example:
    python run_tck.py --sut-url http://localhost:8000/api --test-scope core
    python run_tck.py --sut-url http://localhost:8000/api --test-scope all --verbose
    python run_tck.py --sut-url http://localhost:8000/api --skip-agent-card
"""

import argparse
import os
import subprocess
import sys
from typing import Any, List, Optional


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="A2A Protocol TCK Test Runner")
    
    parser.add_argument(
        "--sut-url",
        type=str,
        required=True,
        help="URL of the SUT's A2A JSON-RPC endpoint (e.g., http://localhost:8000/api)"
    )
    
    parser.add_argument(
        "--test-scope",
        type=str,
        choices=["core", "all"],
        default="core",
        help="Test scope: 'core' runs only essential tests, 'all' runs all tests"
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level"
    )
    
    parser.add_argument(
        "--test-pattern",
        type=str,
        help="Only run tests that match the pattern (e.g., 'test_message_send')"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate HTML test report"
    )
    
    parser.add_argument(
        "--skip-agent-card",
        action="store_true",
        help="Skip fetching and validating the Agent Card, useful for SUTs without Agent Card support"
    )
    
    return parser.parse_args()


def run_tests(args: Any) -> subprocess.CompletedProcess[bytes]:
    """Run the TCK tests with the specified arguments."""
    # Set environment variable for logging level
    os.environ["TCK_LOG_LEVEL"] = args.log_level
    
    # Build the pytest command
    cmd: List[str] = ["pytest"]
    
    # Add SUT URL
    cmd.extend(["--sut-url", args.sut_url])
    
    # Add test scope
    cmd.extend(["--test-scope", args.test_scope])
    
    # Add skip-agent-card flag if specified
    if args.skip_agent_card:
        cmd.append("--skip-agent-card")
    
    # Add test pattern if specified
    if args.test_pattern:
        cmd.extend(["-k", args.test_pattern])
    
    # Add marker if test_scope is "core"
    if args.test_scope == "core":
        cmd.extend(["-m", "core"])
    
    # Add verbosity if requested
    if args.verbose:
        cmd.append("-v")
    
    # Add HTML report if requested
    if args.report:
        try:
            # Ignore this import for mypy checking as it's optional
            import pytest_html  # type: ignore
            cmd.extend(["--html=tck_report.html", "--self-contained-html"])
        except ImportError:
            print("Warning: pytest-html not installed. Cannot generate HTML report.")
            print("Run 'pip install pytest-html' to enable this feature.")
    
    # Print the command being run
    print(f"Running command: {' '.join(cmd)}")
    
    # Run the tests
    return subprocess.run(cmd)


def main() -> int:
    """Main entry point for the TCK runner."""
    args = parse_args()
    result = run_tests(args)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
