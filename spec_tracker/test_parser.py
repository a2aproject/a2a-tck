#!/usr/bin/env python3
"""Test script for the spec parser module."""

import json
import logging

from spec_tracker.spec_parser import SpecParser


# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main():
    """Test the spec parser functionality."""
    print("Testing A2A Specification Parser...")

    try:
        parser = SpecParser()

        # Test with current spec files
        print("\n📄 Testing Markdown Parser...")
        with open("current_spec/A2A_SPECIFICATION.md") as f:
            md_content = f.read()

        md_result = parser.parse_markdown(md_content)

        print(f"✅ Found {len(md_result['sections'])} sections")
        print(f"✅ Found {len(md_result['requirements'])} requirements")
        print(f"✅ Document length: {md_result['structure']['content_length']} characters")

        # Show requirement breakdown
        req_levels = {}
        for req in md_result["requirements"]:
            level = req.level
            req_levels[level] = req_levels.get(level, 0) + 1

        print(f"✅ Requirement levels: {req_levels}")

        # Test with current JSON schema
        print("\n🔧 Testing JSON Schema Parser...")
        with open("current_spec/a2a_schema.json") as f:
            json_schema = json.load(f)

        json_result = parser.parse_json_schema(json_schema)

        print(f"✅ Found {len(json_result['definitions'])} definitions")
        print(f"✅ Found {len(json_result['required_fields'])} objects with required fields")
        print(f"✅ Found {len(json_result['error_codes'])} error codes")
        print(f"✅ Found {len(json_result['methods'])} JSON-RPC methods")

        # Show some sample data
        print("\n📊 Sample Requirements:")
        for i, req in enumerate(md_result["requirements"][:3]):
            print(f"  {req.level}: {req.text[:100]}...")

        print("\n📊 Sample Error Codes:")
        for error_name, error_info in list(json_result["error_codes"].items())[:3]:
            print(f"  {error_name}: {error_info['code']}")

        print("\n📊 Sample Methods:")
        for method_name, method_info in list(json_result["methods"].items())[:3]:
            print(f"  {method_name}: {method_info['request_type']}")

        print("\n🎉 Spec parser test completed successfully!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
