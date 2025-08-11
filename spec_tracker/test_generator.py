#!/usr/bin/env python3
"""Test script for the report generator module."""

import os
import sys


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging

from spec_tracker.report_generator import ReportGenerator
from spec_tracker.spec_comparator import SpecComparator
from spec_tracker.spec_parser import SpecParser
from spec_tracker.test_impact_analyzer import TestImpactAnalyzer


# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main():
    """Test the report generator functionality."""
    print("Testing A2A Report Generator...")

    try:
        # Initialize components
        parser = SpecParser()
        comparator = SpecComparator()
        analyzer = TestImpactAnalyzer()
        generator = ReportGenerator()

        # Load and parse current specs
        print("\n📋 Loading specifications...")
        with open("spec_analysis/A2A_SPECIFICATION.md") as f:
            md_content = f.read()
        with open("spec_analysis/a2a_schema.json") as f:
            json_schema = json.load(f)

        current_spec = {"markdown": parser.parse_markdown(md_content), "json": parser.parse_json_schema(json_schema)}

        # Create test scenarios
        print("\n🧪 Testing No Changes Scenario...")

        # Scenario 1: No changes
        comparison_no_change = comparator.compare_specs(current_spec, current_spec)
        impact_no_change = analyzer.analyze_impact(comparison_no_change)
        coverage_analysis = analyzer.analyze_coverage(current_spec["markdown"]["requirements"])

        report_no_change = generator.generate_report(
            comparison_no_change, impact_no_change, coverage_analysis, "Current A2A Spec", "Current A2A Spec (No Changes)"
        )

        print(f"✅ No-change report generated: {len(report_no_change)} characters")

        # Verify no-change report content
        assert "No specification changes detected" in report_no_change
        assert "No test impacts detected" in report_no_change
        print("✅ No-change scenario validation passed")

        # Scenario 2: Simulated changes
        print("\n🧪 Testing Changes Scenario...")

        # Create modified spec with simulated changes
        modified_requirements = current_spec["markdown"]["requirements"] + [
            # Add a new MUST requirement
            type(
                "MockReq",
                (),
                {
                    "id": "REQ-NEW-001",
                    "section": "Agent Communication",
                    "level": "MUST",
                    "text": "Agents MUST support new authentication protocol",
                    "context": "Testing impact analysis",
                },
            )(),
            # Add a new SHOULD requirement
            type(
                "MockReq",
                (),
                {
                    "id": "REQ-NEW-002",
                    "section": "Message Format",
                    "level": "SHOULD",
                    "text": "Messages SHOULD include timestamp metadata",
                    "context": "Testing impact analysis",
                },
            )(),
        ]

        modified_spec = {
            "markdown": {"requirements": modified_requirements, "sections": current_spec["markdown"]["sections"]},
            "json": current_spec["json"],
        }

        comparison_with_changes = comparator.compare_specs(current_spec, modified_spec)
        impact_with_changes = analyzer.analyze_impact(comparison_with_changes)

        report_with_changes = generator.generate_report(
            comparison_with_changes,
            impact_with_changes,
            coverage_analysis,
            "Current A2A Spec",
            "Modified A2A Spec (With Changes)",
        )

        print(f"✅ Change report generated: {len(report_with_changes)} characters")

        # Verify change report content
        assert "Added Requirements" in report_with_changes or "New Test Coverage Needed" in report_with_changes
        print("✅ Change scenario validation passed")

        # Test summary report
        print("\n📋 Testing Summary Report...")
        summary_report = generator.generate_summary_report(comparison_with_changes, impact_with_changes, coverage_analysis)

        print(f"✅ Summary report generated: {len(summary_report)} characters")
        assert "A2A Spec Change Summary" in summary_report
        print("✅ Summary report validation passed")

        # Test JSON export
        print("\n📋 Testing JSON Export...")
        json_report = generator.export_json_report(comparison_with_changes, impact_with_changes, coverage_analysis)

        # Validate JSON structure
        json_data = json.loads(json_report)
        assert "timestamp" in json_data
        assert "summary" in json_data
        assert "spec_changes" in json_data
        assert "test_impacts" in json_data
        assert "coverage_analysis" in json_data

        print(f"✅ JSON export generated: {len(json_report)} characters")
        print("✅ JSON export validation passed")

        # Test with breaking changes scenario
        print("\n🧪 Testing Breaking Changes Scenario...")

        # Simulate breaking changes
        breaking_spec_changes = {
            "markdown_changes": {"requirements": {"added": [], "removed": [], "modified": []}},
            "json_changes": {"definitions": {"added": [], "removed": [], "modified": []}},
            "impact_classification": {
                "breaking_changes": [
                    {"type": "removed_required_field", "impact": "API clients may break"},
                    {"type": "modified_error_code", "impact": "Error handling needs update"},
                ],
                "behavioral_changes": [],
                "non_breaking_additions": [],
            },
            "summary": {"total_changes": 2},
        }

        breaking_impacts = {
            "directly_affected": ["test_api_client::test_required_fields"],
            "obsolete_tests": ["test_error_codes::test_old_error_format"],
            "new_coverage_needed": [],
            "possibly_affected": [],
        }

        breaking_report = generator.generate_report(
            breaking_spec_changes, breaking_impacts, coverage_analysis, "Previous A2A Spec", "Current A2A Spec (Breaking Changes)"
        )

        # Verify breaking changes are properly highlighted
        assert "🚨 Critical Actions Required" in breaking_report or "breaking changes detected" in breaking_report
        print(f"✅ Breaking changes report generated: {len(breaking_report)} characters")
        print("✅ Breaking changes scenario validation passed")

        # Save sample reports for inspection
        print("\n💾 Saving sample reports...")

        with open("spec_tracker/cache/sample_no_change_report.md", "w") as f:
            f.write(report_no_change)
        print("✅ Saved: spec_tracker/cache/sample_no_change_report.md")

        with open("spec_tracker/cache/sample_change_report.md", "w") as f:
            f.write(report_with_changes)
        print("✅ Saved: spec_tracker/cache/sample_change_report.md")

        with open("spec_tracker/cache/sample_breaking_report.md", "w") as f:
            f.write(breaking_report)
        print("✅ Saved: spec_tracker/cache/sample_breaking_report.md")

        with open("spec_tracker/cache/sample_summary.md", "w") as f:
            f.write(summary_report)
        print("✅ Saved: spec_tracker/cache/sample_summary.md")

        with open("spec_tracker/cache/sample_export.json", "w") as f:
            f.write(json_report)
        print("✅ Saved: spec_tracker/cache/sample_export.json")

        # Show report statistics
        print("\n📊 Report Statistics:")
        print(f"   No-change report: {len(report_no_change)} chars")
        print(f"   Change report: {len(report_with_changes)} chars")
        print(f"   Breaking report: {len(breaking_report)} chars")
        print(f"   Summary report: {len(summary_report)} chars")
        print(f"   JSON export: {len(json_report)} chars")

        # Test report structure validation
        print("\n🔍 Validating Report Structure...")

        required_sections = [
            "# A2A Specification Change Analysis Report",
            "## Version Comparison",
            "## Executive Summary",
            "## Specification Changes",
            "## Test Impact Analysis",
            "## Test Coverage Analysis",
            "## Recommendations",
        ]

        for section in required_sections:
            if section in report_with_changes:
                print(f"   ✅ Found: {section}")
            else:
                print(f"   ❌ Missing: {section}")

        print("\n🎉 Report generator test completed successfully!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
