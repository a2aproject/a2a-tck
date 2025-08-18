#!/usr/bin/env python3
"""
Test script for the spec comparator module.
"""

import json
import logging
from spec_tracker.spec_parser import SpecParser
from spec_tracker.spec_comparator import SpecComparator

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main():
    """Test the spec comparator functionality."""
    print("Testing A2A Specification Comparator...")

    try:
        parser = SpecParser()
        comparator = SpecComparator()

        # Load and parse current specs
        print("\n📄 Loading current specifications...")
        with open("spec_analysis/A2A_SPECIFICATION.md", "r") as f:
            md_content = f.read()

        with open("spec_analysis/a2a_schema.json", "r") as f:
            json_schema = json.load(f)

        current_spec = {"markdown": parser.parse_markdown(md_content), "json": parser.parse_json_schema(json_schema)}

        print(
            f"✅ Parsed current spec: {len(current_spec['markdown']['requirements'])} requirements, {len(current_spec['json']['definitions'])} definitions"
        )

        # For testing, we'll compare the spec with itself (should show no changes)
        print("\n🔍 Testing comparison (spec with itself - should show no changes)...")
        comparison = comparator.compare_specs(current_spec, current_spec)

        print(f"✅ Total changes detected: {comparison['summary']['total_changes']}")
        print(f"✅ Requirement changes: {comparison['summary']['requirement_changes']}")
        print(f"✅ Definition changes: {comparison['summary']['definition_changes']}")
        print(f"✅ Method changes: {comparison['summary']['method_changes']}")

        # Test with a simulated change
        print("\n🧪 Testing with simulated changes...")

        # Create a modified version by adding a fake requirement
        modified_spec = {
            "markdown": {
                "requirements": current_spec["markdown"]["requirements"]
                + [
                    type(
                        "MockReq",
                        (),
                        {
                            "id": "REQ-999",
                            "section": "Test Section",
                            "level": "MUST",
                            "text": "Agents MUST support test functionality",
                            "context": "This is a test requirement",
                        },
                    )()
                ],
                "sections": current_spec["markdown"]["sections"],
            },
            "json": current_spec["json"].copy(),
        }

        # Add a fake JSON definition
        modified_spec["json"]["definitions"] = current_spec["json"]["definitions"].copy()
        modified_spec["json"]["definitions"]["TestDefinition"] = {
            "type": "object",
            "description": "Test definition",
            "properties": {"test_field": {"type": "string"}},
        }

        comparison_with_changes = comparator.compare_specs(current_spec, modified_spec)

        print(f"✅ Total changes with simulated additions: {comparison_with_changes['summary']['total_changes']}")
        print(f"✅ Added requirements: {comparison_with_changes['summary']['requirement_changes']['added']}")
        print(f"✅ Added definitions: {comparison_with_changes['summary']['definition_changes']['added']}")

        # Test impact classification
        print("\n📊 Testing impact classification...")
        impact = comparison_with_changes["impact_classification"]
        print(f"✅ Breaking changes: {len(impact['breaking_changes'])}")
        print(f"✅ Non-breaking additions: {len(impact['non_breaking_additions'])}")
        print(f"✅ Behavioral changes: {len(impact['behavioral_changes'])}")
        print(f"✅ Documentation changes: {len(impact['documentation_changes'])}")
        print(f"✅ Total impact score: {impact['impact_score']['total_impact']}")

        # Show some details
        if impact["behavioral_changes"]:
            print(f"\n📋 Sample behavioral change:")
            change = impact["behavioral_changes"][0]
            print(f"   Type: {change['type']}")
            print(f"   Section: {change['section']}")
            print(f"   Impact: {change['impact']}")

        if impact["non_breaking_additions"]:
            print(f"\n📋 Sample non-breaking addition:")
            change = impact["non_breaking_additions"][0]
            print(f"   Type: {change['type']}")
            print(f"   Definition: {change['definition']}")
            print(f"   Impact: {change['impact']}")

        print("\n🎉 Spec comparator test completed successfully!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
