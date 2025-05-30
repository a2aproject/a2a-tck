#!/usr/bin/env python3
"""
Run A2A TCK tests - comprehensive test suite runner.

This script provides a single entry point to understand and run all A2A TCK test categories.
It explains the differences between test types and helps you choose what to run.

=== A2A TCK TEST CATEGORIES EXPLAINED ===

🔴 MANDATORY TESTS (./run_mandatory.py)
   - JSON-RPC 2.0 compliance + A2A protocol requirements  
   - MUST pass for A2A compliance
   - Failure = NOT A2A compliant

🔄 CAPABILITY TESTS (./run_capabilities.py)
   - Validate declared capabilities work correctly
   - SKIP if not declared, MANDATORY if declared
   - Failure = False advertising (capability claimed but broken)

🛡️  QUALITY TESTS (./run_quality.py)
   - Production readiness and robustness
   - ALWAYS optional (never block compliance)
   - Failure = Areas for production improvement

🎨 FEATURE TESTS (./run_features.py)
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
    ./run_all.py --sut-url http://localhost:9999 --category mandatory
    ./run_all.py --sut-url http://localhost:9999 --category all
    ./run_all.py --sut-url http://localhost:9999 --explain
"""

import subprocess
import sys
import argparse
from pathlib import Path

def explain_test_categories():
    """Explain all test categories in detail."""
    print("=" * 80)
    print("🧭 A2A TCK TEST CATEGORIES GUIDE")
    print("=" * 80)
    print()
    
    print("🔴 MANDATORY TESTS")
    print("   Purpose: Validate core A2A specification compliance")
    print("   Script:  ./run_mandatory.py")
    print("   Impact:  MUST pass for A2A compliance")
    print("   Tests:   24 tests (JSON-RPC + A2A protocol)")
    print("   Example: ./run_mandatory.py --sut-url http://localhost:9999")
    print()
    
    print("🔄 CAPABILITY TESTS")  
    print("   Purpose: Validate declared capabilities actually work")
    print("   Script:  ./run_capabilities.py")
    print("   Impact:  Conditional mandatory (if capability declared)")
    print("   Tests:   7 tests (streaming, push notifications, auth, etc.)")
    print("   Example: ./run_capabilities.py --sut-url http://localhost:9999")
    print()
    
    print("🛡️  QUALITY TESTS")
    print("   Purpose: Assess production readiness and robustness")  
    print("   Script:  ./run_quality.py")
    print("   Impact:  Always optional (improvement suggestions)")
    print("   Tests:   3 tests (concurrency, resilience, edge cases)")
    print("   Example: ./run_quality.py --sut-url http://localhost:9999")
    print()
    
    print("🎨 FEATURE TESTS")
    print("   Purpose: Validate optional behaviors and utilities")
    print("   Script:  ./run_features.py") 
    print("   Impact:  Always optional (informational only)")
    print("   Tests:   4 tests (business logic, utilities, SDK features)")
    print("   Example: ./run_features.py --sut-url http://localhost:9999")
    print()
    
    print("=" * 80)
    print("📋 QUICK DECISION GUIDE")
    print("=" * 80)
    print()
    print("❓ Just want to check A2A compliance?")
    print("   → Run: ./run_mandatory.py")
    print()
    print("❓ Want to validate your Agent Card claims?")  
    print("   → Run: ./run_mandatory.py && ./run_capabilities.py")
    print()
    print("❓ Preparing for production deployment?")
    print("   → Run: ./run_mandatory.py && ./run_capabilities.py && ./run_quality.py")
    print()
    print("❓ Want comprehensive implementation assessment?")
    print("   → Run: ./run_all.py --category all")
    print()
    print("=" * 80)

def run_test_category(category: str, sut_url: str, verbose: bool = False, generate_report: bool = False):
    """Run a specific test category."""
    
    scripts = {
        "mandatory": "./run_mandatory.py",
        "capabilities": "./run_capabilities.py", 
        "quality": "./run_quality.py",
        "features": "./run_features.py"
    }
    
    if category not in scripts:
        print(f"❌ Unknown category: {category}")
        print(f"Available: {', '.join(scripts.keys())}")
        return 1
    
    script = scripts[category]
    
    # Build command
    cmd = [script, f"--sut-url={sut_url}"]
    
    if verbose:
        cmd.append("--verbose")
    
    if generate_report:
        cmd.append("--report")
    
    print(f"🚀 Running {category} tests...")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    # Run the script
    result = subprocess.run(cmd)
    return result.returncode

def run_all_categories(sut_url: str, verbose: bool = False, generate_report: bool = False):
    """Run all test categories in recommended order."""
    
    categories = ["mandatory", "capabilities", "quality", "features"]
    results = {}
    
    print("=" * 80)
    print("🎯 RUNNING ALL A2A TCK TEST CATEGORIES")
    print("Following recommended workflow...")
    print("=" * 80)
    print()
    
    for i, category in enumerate(categories, 1):
        print(f"📍 STEP {i}/4: Running {category} tests...")
        print()
        
        exit_code = run_test_category(category, sut_url, verbose, generate_report)
        results[category] = exit_code
        
        print()
        print(f"✅ {category.upper()} TESTS COMPLETED")
        print(f"Exit code: {exit_code}")
        print()
        
        # Show progress
        if i < len(categories):
            print("─" * 80)
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

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run A2A TCK comprehensive test suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Explain all test categories
  ./run_all.py --explain
  
  # Run only mandatory compliance tests
  ./run_all.py --sut-url http://localhost:9999 --category mandatory
  
  # Run all test categories with reports
  ./run_all.py --sut-url http://localhost:9999 --category all --report
  
  # Quick compliance check
  ./run_all.py --sut-url http://localhost:9999 --category mandatory --verbose

Categories:
  mandatory     - Core A2A compliance (MUST pass)
  capabilities  - Declared capability validation (conditional mandatory)
  quality       - Production readiness assessment (optional)
  features      - Optional feature validation (informational)
  all           - All categories in recommended order
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
        help="Enable verbose test output"
    )
    
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate HTML test reports"
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
    
    # Run tests
    if args.category == "all":
        results = run_all_categories(args.sut_url, args.verbose, args.report)
        # Exit with failure if mandatory or capabilities failed
        if results["mandatory"] != 0 or results["capabilities"] != 0:
            sys.exit(1)
    else:
        exit_code = run_test_category(args.category, args.sut_url, args.verbose, args.report)
        sys.exit(exit_code)

if __name__ == "__main__":
    main() 