#!/usr/bin/env python3
"""
A2A Protocol Technology Compatibility Kit (TCK) - Test Runner

This script provides a comprehensive interface to run A2A TCK tests organized by categories.
It explains the differences between test types and helps you choose what to run.

=== A2A TCK TEST CATEGORIES EXPLAINED ===

🔴 MANDATORY TESTS
   - JSON-RPC 2.0 compliance + A2A protocol requirements  
   - MUST pass for A2A compliance
   - Failure = NOT A2A compliant

🔄 CAPABILITY TESTS
   - Validate declared capabilities work correctly
   - SKIP if not declared, MANDATORY if declared
   - Failure = False advertising (capability claimed but broken)

🛡️  QUALITY TESTS
   - Production readiness and robustness
   - ALWAYS optional (never block compliance)
   - Failure = Areas for production improvement

🎨 FEATURE TESTS
   - Optional behaviors and convenience features
   - ALWAYS optional and informational
   - Failure = Missing optional features (perfectly fine)

=== RECOMMENDED WORKFLOW ===

1. START HERE: Run mandatory tests first
   → If they fail, fix issues before proceeding
   
2. VALIDATE CAPABILITIES: Run capability tests
   → Fix false advertising or remove capability claims
   
3. ASSESS QUALITY: Run quality tests for production readiness
   → Optional improvements for robust deployments
   
4. CHECK FEATURES: Run feature tests for completeness assessment
   → Purely informational, no action required

Usage:
    ./run_tck.py --sut-url http://localhost:9999 --category mandatory
    ./run_tck.py --sut-url http://localhost:9999 --category all
    ./run_tck.py --sut-url http://localhost:9999 --explain
"""

import subprocess
import sys
import argparse
from pathlib import Path
from typing import Dict
import json
import os
from dotenv import load_dotenv

# Define the directory for all generated reports
REPORTS_DIR = Path("reports")

def load_env_file():
    """Load environment variables from .env file if it exists."""
    load_dotenv(override=False)  # Don't override existing env vars

def explain_test_categories():
    """Explain all test categories in detail."""
    print("=" * 80)
    print("🧭 A2A TCK TEST CATEGORIES GUIDE")
    print("=" * 80)
    print()
    
    print("🔴 MANDATORY TESTS")
    print("   Purpose: Validate core A2A specification compliance")
    print("   Impact:  MUST pass for A2A compliance")
    print("   Tests:   24 tests (JSON-RPC + A2A protocol)")
    print("   Files:   tests/mandatory/jsonrpc/, tests/mandatory/protocol/")
    print("   Example: ./run_tck.py --sut-url http://localhost:9999 --category mandatory")
    print()
    
    print("🔄 CAPABILITY TESTS")  
    print("   Purpose: Validate declared capabilities actually work")
    print("   Impact:  Conditional mandatory (if capability declared)")
    print("   Tests:   7 tests (streaming, push notifications, auth, etc.)")
    print("   Files:   tests/optional/capabilities/")
    print("   Example: ./run_tck.py --sut-url http://localhost:9999 --category capabilities")
    print()
    
    print("🛡️  QUALITY TESTS")
    print("   Purpose: Assess production readiness and robustness")  
    print("   Impact:  Always optional (improvement suggestions)")
    print("   Tests:   3 tests (concurrency, resilience, edge cases)")
    print("   Files:   tests/optional/quality/")
    print("   Example: ./run_tck.py --sut-url http://localhost:9999 --category quality")
    print()
    
    print("🎨 FEATURE TESTS")
    print("   Purpose: Validate optional behaviors and utilities")
    print("   Impact:  Always optional (informational only)")
    print("   Tests:   4 tests (business logic, utilities, SDK features)")
    print("   Files:   tests/optional/features/")
    print("   Example: ./run_tck.py --sut-url http://localhost:9999 --category features")
    print()
    
    print("=" * 80)
    print("📋 QUICK DECISION GUIDE")
    print("=" * 80)
    print()
    print("❓ Just want to check A2A compliance?")
    print("   → Run: ./run_tck.py --category mandatory")
    print()
    print("❓ Want to validate your Agent Card claims?")  
    print("   → Run: ./run_tck.py --category mandatory && ./run_tck.py --category capabilities")
    print()
    print("❓ Preparing for production deployment?")
    print("   → Run: ./run_tck.py --category mandatory && ./run_tck.py --category capabilities && ./run_tck.py --category quality")
    print()
    print("❓ Want comprehensive implementation assessment?")
    print("   → Run: ./run_tck.py --category all")
    print()
    print("=" * 80)

def run_test_category(category: str, sut_url: str, verbose: bool = False, verbose_log: bool = False, generate_report: bool = False, json_report: str = None):
    """Run a specific test category."""
    
    # Map categories to pytest commands
    category_configs = {
        "mandatory": {
            "path": "tests/mandatory/",
            "markers": "mandatory_jsonrpc or mandatory_protocol",
            "description": "Mandatory A2A compliance tests"
        },
        "capabilities": {
            "path": "tests/optional/capabilities/", 
            "markers": None,  # Run all tests in this directory for now
            "description": "Capability declaration validation tests"
        },
        "quality": {
            "path": "tests/optional/quality/",
            "markers": None,  # Run all tests in this directory for now
            "description": "Implementation quality and robustness tests"
        },
        "features": {
            "path": "tests/optional/features/",
            "markers": None,  # Run all tests in this directory for now
            "description": "Optional feature and utility tests"
        }
    }
    
    if category not in category_configs:
        print(f"❌ Unknown category: {category}")
        print(f"Available: {', '.join(category_configs.keys())}")
        return 1
    
    config = category_configs[category]
    
    print("=" * 70)
    print(f"🚀 Running {category.upper()} tests")
    print(f"Description: {config['description']}")
    print("=" * 70)
    print()
    
    # Build pytest command
    cmd = [
        sys.executable, "-m", "pytest",
        config["path"],
        f"--sut-url={sut_url}",
        "--test-scope=all",  # Bypass old core marking system
        "--tb=short",
    ]
    
    # Create reports directory if it doesn't exist
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Add JSON report if requested
    if json_report:
        json_report_path = REPORTS_DIR / json_report
        cmd.extend(["--json-report", f"--json-report-file={json_report_path}"])
    
    # Only add marker filtering if markers are specified
    if config["markers"]:
        cmd.extend(["-m", config["markers"]])
    
    if verbose_log:
        cmd.extend(["-v", "-s", "--log-cli-level=INFO"])  # Full verbose with logging
    elif verbose:
        cmd.append("-v")  # Just verbose output
    else:
        cmd.append("-q")  # Quiet output
    
    if generate_report:
        report_path = REPORTS_DIR / f"{category}_test_report.html"
        cmd.extend([f"--html={report_path}", "--self-contained-html"])
    
    print(f"Command: {' '.join(cmd)}")
    print()
    
    # Run the tests
    result = subprocess.run(cmd)
    return result.returncode

def run_all_categories(sut_url: str, verbose: bool = False, verbose_log: bool = False, generate_report: bool = False, compliance_report: str = None):
    """Run all test categories in recommended order."""
    
    categories = ["mandatory", "capabilities", "quality", "features"]
    results = {}
    detailed_results = {}
    
    print("=" * 80)
    print("🎯 RUNNING ALL A2A TCK TEST CATEGORIES")
    print("Following recommended workflow...")
    print("=" * 80)
    print()
    
    for i, category in enumerate(categories, 1):
        print(f"📍 STEP {i}/4: Running {category} tests...")
        print()
        
        # Generate JSON report for this category if compliance report requested
        json_report_file = None
        if compliance_report:
            json_report_file = f"{category}_results.json"
        
        exit_code = run_test_category(category, sut_url, verbose, verbose_log, generate_report, json_report_file)
        results[category] = exit_code
        
        # Collect detailed results for compliance report
        if compliance_report and json_report_file:
            json_report_path = REPORTS_DIR / json_report_file
            detailed_results[category] = collect_test_results_from_json(json_report_path, category)
        
        print()
        print(f"✅ {category.upper()} TESTS COMPLETED")
        print(f"Exit code: {exit_code}")
        print()
        
        # Show progress
        if i < len(categories):
            print("─" * 80)
            print()
    
    # Generate compliance report if requested
    if compliance_report:
        try:
            from util_scripts.generate_compliance_report import ComplianceReportGenerator
            from util_scripts.compliance_levels import generate_compliance_summary
            
            # Get agent card data
            agent_card = get_agent_card_data(sut_url)
            
            # Calculate compliance metrics
            mandatory_rate = calculate_success_rate(detailed_results.get('mandatory', {}))
            capability_rate = calculate_success_rate(detailed_results.get('capabilities', {})) 
            quality_rate = calculate_success_rate(detailed_results.get('quality', {}))
            feature_rate = calculate_success_rate(detailed_results.get('features', {}))
            
            # Generate comprehensive compliance summary
            compliance_summary = generate_compliance_summary(
                mandatory_rate, capability_rate, quality_rate, feature_rate
            )
            
            # Create detailed report
            generator = ComplianceReportGenerator(detailed_results, agent_card)
            report = generator.generate_report()
            
            # Ensure the reports directory exists for the final report
            compliance_report_path = Path(compliance_report)
            compliance_report_path.parent.mkdir(parents=True, exist_ok=True)

            # Save compliance report
            with open(compliance_report_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            print(f"📊 Compliance report generated: {compliance_report_path}")
            print(f"🏆 Compliance level: {compliance_summary['current_level']['badge']}")
            print(f"📈 Overall score: {compliance_summary['overall_score']:.1f}%")
            print()
            
            # Clean up temporary JSON files
            for category in categories:
                json_file = REPORTS_DIR / f"{category}_results.json"
                if json_file.exists():
                    json_file.unlink()
            
        except Exception as e:
            print(f"⚠️  Warning: Could not generate compliance report: {e}")
            print()
    
    # Final summary
    print("=" * 80)
    print("📊 COMPREHENSIVE TEST RESULTS SUMMARY")
    print("=" * 80)
    print()
    
    mandatory_passed = results["mandatory"] == 0
    capabilities_passed = results["capabilities"] == 0
    quality_passed = results["quality"] == 0
    features_passed = results["features"] == 0
    
    print(f"🔴 Mandatory Tests:   {'✅ PASSED' if mandatory_passed else '❌ FAILED'}")
    print(f"🔄 Capability Tests:  {'✅ PASSED' if capabilities_passed else '❌ FAILED'}")
    print(f"🛡️  Quality Tests:     {'✅ PASSED' if quality_passed else '⚠️  ISSUES'}")
    print(f"🎨 Feature Tests:     {'✅ PASSED' if features_passed else 'ℹ️  INCOMPLETE'}")
    print()
    
    # Overall assessment
    if mandatory_passed:
        print("🎉 A2A COMPLIANCE: ✅ PASSED")
        print("Your implementation meets A2A specification requirements!")
        
        if capabilities_passed:
            print("🔄 CAPABILITY HONESTY: ✅ EXCELLENT")  
            print("All declared capabilities work correctly!")
            
            if quality_passed:
                print("🛡️  PRODUCTION QUALITY: ✅ HIGH")
                print("Implementation is robust and production-ready!")
                
                if features_passed:
                    print("🎨 FEATURE COMPLETENESS: ✅ COMPREHENSIVE")
                    print("Implementation includes valuable optional features!")
                    print()
                    print("🏆 OUTSTANDING A2A IMPLEMENTATION!")
                else:
                    print("🎨 FEATURE COMPLETENESS: ℹ️  BASIC")
                    print("Implementation focuses on core functionality (perfectly fine).")
            else:
                print("🛡️  PRODUCTION QUALITY: ⚠️  NEEDS ATTENTION")
                print("Consider addressing quality issues before production deployment.")
        else:
            print("🔄 CAPABILITY HONESTY: ❌ FALSE ADVERTISING")
            print("Fix capability implementations or remove false claims.")
    else:
        print("❌ A2A COMPLIANCE: FAILED")
        print("Must fix mandatory test failures before claiming A2A compliance!")
    
    print()
    print("=" * 80)
    
    return results

def collect_test_results_from_json(json_file: Path, category: str) -> Dict:
    """Collect detailed test results from pytest JSON report."""
    try:
        if not json_file.exists():
            print(f"Warning: JSON report file {json_file} not found")
            return {'total': 0, 'passed': 0, 'failed': 0, 'skipped': 0, 'xfailed': 0, 'tests': {}}
        
        with open(json_file, 'r') as f:
            report_data = json.load(f)
        
        # Parse pytest-json-report format
        summary = report_data.get('summary', {})
        tests = report_data.get('tests', [])
        
        # Extract summary statistics
        total = summary.get('total', 0)
        passed = summary.get('passed', 0)
        failed = summary.get('failed', 0)
        skipped = summary.get('skipped', 0)
        xfailed = summary.get('xfailed', 0)
        
        # Parse individual test results
        test_details = {}
        for test in tests:
            test_name = test.get('nodeid', '').split('::')[-1]  # Get just the test function name
            outcome = test.get('outcome', 'unknown').upper()
            
            test_details[test_name] = {
                'outcome': outcome,
                'duration': test.get('duration', 0),
                'error_message': test.get('call', {}).get('longrepr', '') if outcome == 'FAILED' else None,
                'markers': [marker.get('name', '') for marker in test.get('markers', [])]
            }
        
        return {
            'total': total,
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'xfailed': xfailed,
            'tests': test_details
        }
        
    except Exception as e:
        print(f"Warning: Could not parse JSON report {json_file}: {e}")
        # Fallback to basic data based on file existence
        return {
            'total': 1, 'passed': 0, 'failed': 1, 'skipped': 0, 'xfailed': 0,
            'tests': {'parse_error': {'outcome': 'FAILED', 'error_message': str(e)}}
        }

def collect_test_results(category: str, exit_code: int) -> Dict:
    """Collect detailed test results for a category."""
    # This is a fallback implementation when JSON reports aren't available
    # Used for single category runs without compliance reporting
    
    # Estimate based on exit code for now
    if exit_code == 0:
        return {
            'total': 10, 'passed': 10, 'failed': 0, 'skipped': 0, 'xfailed': 0,
            'tests': {}
        }
    else:
        return {
            'total': 10, 'passed': 7, 'failed': 3, 'skipped': 0, 'xfailed': 0,
            'tests': {}
        }

def calculate_success_rate(results: Dict) -> float:
    """Calculate success rate from test results."""
    if not results or results.get('total', 0) == 0:
        return 0.0
    
    total = results['total']
    passed = results['passed'] 
    skipped = results.get('skipped', 0)
    
    # Calculate success rate excluding skipped tests
    testable = total - skipped
    if testable == 0:
        return 100.0  # All tests skipped = 100% success rate
    
    return (passed / testable) * 100

def get_agent_card_data(sut_url: str) -> Dict:
    """Get agent card data from the SUT."""
    try:
        import requests
        response = requests.get(f"{sut_url.rstrip('/')}/agent")
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Warning: Could not fetch agent card: {e}")
    
    return {}

def main():
    """Main entry point."""
    # Load environment variables from .env file if it exists
    load_env_file()
    
    parser = argparse.ArgumentParser(
        description="A2A Protocol Technology Compatibility Kit (TCK) - Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Explain all test categories
  ./run_tck.py --explain
  
  # Run only mandatory compliance tests
  ./run_tck.py --sut-url http://localhost:9999 --category mandatory
  
  # Run all test categories with reports
  ./run_tck.py --sut-url http://localhost:9999 --category all --report
  
  # Quick compliance check with verbose output
  ./run_tck.py --sut-url http://localhost:9999 --category mandatory --verbose
  
  # Run with full verbose logging
  ./run_tck.py --sut-url http://localhost:9999 --category mandatory --verbose-log
  
  # Run compliance + quality tests (good for production assessment)
  ./run_tck.py --sut-url http://localhost:9999 --category quality

Categories:
  mandatory             - Core A2A compliance (MUST pass)
  capabilities          - Declared capability validation (conditional mandatory)
  quality               - Production readiness assessment (optional)
  features              - Optional feature validation (informational)
  all                   - All categories in recommended order
        """
    )
    
    parser.add_argument(
        "--sut-url",
        help="URL of the SUT's A2A JSON-RPC endpoint"
    )
    
    parser.add_argument(
        "--category",
        choices=["mandatory", "capabilities", "quality", "features", "all"],
        help="Test category to run"
    )
    
    parser.add_argument(
        "--explain",
        action="store_true",
        help="Explain all test categories and exit"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose test output (adds -v to pytest)"
    )
    
    parser.add_argument(
        "--verbose-log",
        action="store_true",
        help="Enable verbose test output with logging (adds -v -s --log-cli-level=INFO to pytest)"
    )
    
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate HTML test reports"
    )
    
    parser.add_argument(
        "--compliance-report",
        metavar="FILENAME",
        help="Generate A2A compliance report (JSON format)"
    )
    
    args = parser.parse_args()
    
    if args.explain:
        explain_test_categories()
        sys.exit(0)
    
    if not args.sut_url:
        print("❌ Error: --sut-url is required (unless using --explain)")
        print("Use --help for usage information")
        sys.exit(1)
    
    if not args.category:
        print("❌ Error: --category is required")
        print("Use --explain to understand categories")
        sys.exit(1)
    
    # Validate test directories exist
    if not Path("tests").exists():
        print("❌ Error: tests/ directory not found")
        print("Make sure you're running from the TCK root directory")
        sys.exit(1)
    
    # Determine the final compliance report path
    compliance_report_path = None
    if args.compliance_report:
        compliance_report_path = REPORTS_DIR / args.compliance_report

    # Run tests
    if args.category == "all":
        results = run_all_categories(args.sut_url, args.verbose, args.verbose_log, args.report, compliance_report_path)
        # Exit with failure if mandatory or capabilities failed
        if results["mandatory"] != 0 or results["capabilities"] != 0:
            sys.exit(1)
    else:
        exit_code = run_test_category(args.category, args.sut_url, args.verbose, args.verbose_log, args.report, None)
        sys.exit(exit_code)

if __name__ == "__main__":
    main()
