#!/usr/bin/env python3
"""Test script for the test impact analyzer module."""

import json
import logging

from spec_tracker.spec_comparator import SpecComparator
from spec_tracker.spec_parser import SpecParser
from spec_tracker.test_impact_analyzer import TestImpactAnalyzer


# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main():
    """Test the test impact analyzer functionality."""
    print("Testing A2A Test Impact Analyzer...")

    try:
        # Initialize components
        parser = SpecParser()
        comparator = SpecComparator()
        analyzer = TestImpactAnalyzer()

        # Test registry building
        print("\n📋 Testing Test Registry...")
        summary = analyzer.get_registry_summary()

        print(f"✅ Total tests found: {summary['total_tests']}")
        print(f"✅ Tests with spec refs: {summary['with_spec_refs']}")
        print(f"✅ Tests without spec refs: {summary['without_spec_refs']}")
        print(f"✅ Total spec references: {summary['total_spec_refs']}")
        print(f"✅ Categories found: {list(summary['by_category'].keys())}")

        # Show category breakdown
        print("\n📊 Test Category Breakdown:")
        for category, count in summary["by_category"].items():
            print(f"   {category}: {count} tests")

        # Show some example spec references
        print("\n📋 Sample Specification References:")
        for ref in summary["unique_spec_refs"][:5]:
            print(f"   {ref}")

        # Test coverage analysis
        print("\n🎯 Testing Coverage Analysis...")

        # Load current spec to test coverage
        with open("spec_analysis/A2A_SPECIFICATION.md") as f:
            md_content = f.read()

        current_spec = parser.parse_markdown(md_content)
        requirements = current_spec["requirements"]

        coverage = analyzer.analyze_coverage(requirements)

        print(f"✅ Total requirements: {coverage['overall_coverage']['total_requirements']}")
        print(f"✅ Covered requirements: {coverage['overall_coverage']['covered_requirements']}")
        print(f"✅ Requirement coverage: {coverage['overall_coverage']['requirement_coverage_percentage']:.1f}%")
        print(f"✅ Test documentation: {coverage['overall_coverage']['test_documentation_percentage']:.1f}%")

        # Show coverage by requirement level
        print("\n📊 Coverage by Requirement Level:")
        for level, stats in coverage["coverage_by_requirement_level"].items():
            coverage_pct = stats["coverage_percentage"]
            print(f"   {level}: {stats['covered_requirements']}/{stats['total_requirements']} ({coverage_pct:.1f}%)")

        # Show some requirements without tests
        uncovered_reqs = coverage["requirements_without_tests"][:5]
        if uncovered_reqs:
            print("\n⚠️  Sample Requirements Without Tests:")
            for req_info in uncovered_reqs:
                level = req_info["level"]
                text = req_info["text"][:80] + "..." if len(req_info["text"]) > 80 else req_info["text"]
                print(f"   {level}: {text}")

        # Test impact analysis with simulated changes
        print("\n🧪 Testing Impact Analysis...")

        # Load and parse current specs for comparison
        with open("spec_analysis/a2a_schema.json") as f:
            json_schema = json.load(f)

        current_full_spec = {"markdown": current_spec, "json": parser.parse_json_schema(json_schema)}

        # Create simulated changes
        modified_spec = {
            "markdown": {
                "requirements": requirements
                + [
                    type(
                        "MockReq",
                        (),
                        {
                            "id": "REQ-TEST",
                            "section": "Agent Communication",
                            "level": "MUST",
                            "text": "Agents MUST support new test protocol",
                            "context": "Testing impact analysis",
                        },
                    )()
                ],
                "sections": current_spec["sections"],
            },
            "json": current_full_spec["json"],
        }

        # Compare specs
        comparison = comparator.compare_specs(current_full_spec, modified_spec)

        # Analyze impact
        impact = analyzer.analyze_impact(comparison)
        impact_summary = analyzer.get_impact_summary(impact)

        print(f"✅ Total impacted tests: {impact_summary['total_impacted_tests']}")
        print(f"✅ Categories affected: {impact_summary['categories_affected']}")
        print(f"✅ Recommendation priority: {impact_summary['recommendation_priority']}")

        # Show impact distribution
        print("\n📊 Impact Distribution:")
        for impact_type, count in impact_summary["impact_distribution"].items():
            print(f"   {impact_type}: {count} tests")

        if impact_summary["high_priority_impacts"]:
            print("\n⚠️  High Priority Impacts:")
            for impact_msg in impact_summary["high_priority_impacts"]:
                print(f"   {impact_msg}")

        # Test specific search capabilities
        print("\n🔍 Testing Search Capabilities...")

        # Find tests by category
        mandatory_tests = analyzer.find_tests_by_category("mandatory_jsonrpc")
        print(f"✅ Found {len(mandatory_tests)} mandatory JSON-RPC tests")

        # Find tests with specific spec references
        must_tests = analyzer.find_tests_with_spec_ref(r"MUST")
        print(f"✅ Found {len(must_tests)} tests with MUST requirements")

        # Find tests without spec refs
        no_refs_tests = analyzer.find_tests_without_spec_refs()
        print(f"✅ Found {len(no_refs_tests)} tests without specification references")

        if no_refs_tests:
            print("   Sample tests without refs:")
            for test_info in no_refs_tests[:3]:
                print(f"     {test_info['name']} in {test_info['category']}")

        print("\n🎉 Test impact analyzer test completed successfully!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
