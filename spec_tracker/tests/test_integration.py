"""Integration tests for the A2A Specification Change Tracker."""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, Mock


# Test the actual pipeline
def test_complete_pipeline_no_changes():
    """Test complete pipeline when there are no changes."""
    from spec_tracker.spec_downloader import SpecDownloader
    from spec_tracker.spec_parser import SpecParser
    from spec_tracker.spec_comparator import SpecComparator
    from spec_tracker.test_impact_analyzer import TestImpactAnalyzer
    from spec_tracker.report_generator import ReportGenerator

    # Sample spec data
    sample_json = {"definitions": {"TestType": {"type": "object"}}}
    sample_md = "# Test Spec\nThe client MUST validate input."

    # Create temp cache directory
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir) / "cache"

        # Test downloader
        downloader = SpecDownloader(cache_dir=cache_dir)

        # Test parser
        parser = SpecParser()
        parsed_md = parser.parse_markdown(sample_md)
        parsed_json = parser.parse_json_schema(sample_json)

        current_spec = {"markdown": parsed_md, "json": parsed_json}

        # Test comparator with identical specs
        comparator = SpecComparator()
        comparison = comparator.compare_specs(current_spec, current_spec)

        # Should detect no changes
        assert comparison["summary"]["total_changes"] == 0

        # Test analyzer
        analyzer = TestImpactAnalyzer(test_dir=Path("tests"))
        impact = analyzer.analyze_impact(comparison)

        # Test report generator
        generator = ReportGenerator()
        report = generator.generate_report(
            comparison, impact, {"total_tests": 68, "tests_with_refs": 66, "documentation_coverage": 97.1}, "Current", "Latest"
        )

        # Verify report contains expected sections
        assert "# A2A Specification Change Analysis Report" in report
        assert "No specification changes detected" in report or "0 changes" in report


def test_complete_pipeline_with_changes():
    """Test complete pipeline when there are changes."""
    from spec_tracker.spec_parser import SpecParser
    from spec_tracker.spec_comparator import SpecComparator
    from spec_tracker.test_impact_analyzer import TestImpactAnalyzer
    from spec_tracker.report_generator import ReportGenerator

    # Old spec
    old_json = {"definitions": {"OldType": {"type": "object"}}}
    old_md = "# Old Spec\nThe client MUST validate input."

    # New spec with changes
    new_json = {
        "definitions": {
            "OldType": {"type": "object"},
            "NewType": {"type": "string"},  # Added
        }
    }
    new_md = "# New Spec\nThe client MUST validate all input."  # Modified

    parser = SpecParser()

    old_spec = {"markdown": parser.parse_markdown(old_md), "json": parser.parse_json_schema(old_json)}

    new_spec = {"markdown": parser.parse_markdown(new_md), "json": parser.parse_json_schema(new_json)}

    # Test comparator
    comparator = SpecComparator()
    comparison = comparator.compare_specs(old_spec, new_spec)

    # Should detect changes
    assert comparison["summary"]["total_changes"] > 0

    # Test analyzer
    analyzer = TestImpactAnalyzer(test_dir=Path("tests"))
    impact = analyzer.analyze_impact(comparison)

    # Test report generator
    generator = ReportGenerator()
    report = generator.generate_report(
        comparison, impact, {"total_tests": 68, "tests_with_refs": 66, "documentation_coverage": 97.1}, "v1.0.0", "v1.1.0"
    )

    # Verify report contains changes
    assert "# A2A Specification Change Analysis Report" in report
    assert "v1.0.0" in report
    assert "v1.1.0" in report
    assert comparison["summary"]["total_changes"] > 0


@patch("spec_tracker.spec_downloader.requests.get")
def test_downloader_integration(mock_get):
    """Test spec downloader with mocked network calls."""
    from spec_tracker.spec_downloader import SpecDownloader

    # Mock successful responses
    json_response = Mock()
    json_response.json.return_value = {"test": "data"}
    json_response.raise_for_status = Mock()

    md_response = Mock()
    md_response.text = "# Test Specification"
    md_response.raise_for_status = Mock()

    mock_get.side_effect = [json_response, md_response]

    with tempfile.TemporaryDirectory() as temp_dir:
        downloader = SpecDownloader(cache_dir=Path(temp_dir))
        json_data, md_content = downloader.download_spec()

        assert json_data == {"test": "data"}
        assert md_content == "# Test Specification"
        assert mock_get.call_count == 2


def test_parser_integration():
    """Test parser with real-world-like content."""
    from spec_tracker.spec_parser import SpecParser

    parser = SpecParser()

    # Test markdown parsing
    markdown_content = """
# A2A Protocol Specification

## 1. Introduction
This specification defines the A2A protocol.

## 2. Requirements
The client MUST validate all requests.
The server SHOULD respond within 30 seconds.
Optional features MAY be implemented as extensions.

## 3. Error Handling
Error responses are REQUIRED for invalid requests.
Detailed logging is RECOMMENDED for debugging.
    """

    md_result = parser.parse_markdown(markdown_content)

    assert len(md_result["sections"]) > 0
    assert len(md_result["requirements"]) >= 5

    # Test JSON parsing
    json_schema = {
        "definitions": {
            "Request": {
                "type": "object",
                "properties": {"method": {"type": "string"}, "params": {"type": "object"}},
                "required": ["method"],
            }
        },
        "errorCodes": {"PARSE_ERROR": -32700, "INVALID_REQUEST": -32600},
    }

    json_result = parser.parse_json_schema(json_schema)

    assert "definitions" in json_result
    assert "error_codes" in json_result


def test_analyzer_integration():
    """Test analyzer with actual test directory structure."""
    from spec_tracker.test_impact_analyzer import TestImpactAnalyzer

    analyzer = TestImpactAnalyzer(test_dir=Path("tests"))

    # Should find actual tests
    assert len(analyzer.test_registry) > 0

    # Test summary
    summary = analyzer.get_registry_summary()
    assert "total_tests" in summary
    assert summary["total_tests"] > 0


def test_main_script_help():
    """Test that main script shows help without errors."""
    import subprocess
    import sys

    result = subprocess.run([sys.executable, "spec_tracker/main.py", "--help"], capture_output=True, text=True)

    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_main_script_dry_run():
    """Test main script with dry run option."""
    import subprocess
    import sys

    result = subprocess.run([sys.executable, "spec_tracker/main.py", "--dry-run"], capture_output=True, text=True)

    # Should exit gracefully (may return non-zero due to network issues, but shouldn't crash)
    assert "Dry run mode" in result.stderr or "dry run" in result.stderr.lower()


def test_cache_functionality():
    """Test caching works correctly."""
    from spec_tracker.spec_downloader import SpecDownloader

    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir) / "cache"
        downloader = SpecDownloader(cache_dir=cache_dir)

        # Cache some data
        test_json = {"cached": True}
        test_md = "# Cached content"

        downloader._cache_specs(test_json, test_md)

        # Verify cache files exist
        cache_files = list(cache_dir.glob("*.json"))
        assert len(cache_files) > 0

        cache_files = list(cache_dir.glob("*.md"))
        assert len(cache_files) > 0

        # Test loading from cache
        cached_json, cached_md = downloader._load_from_cache()
        assert cached_json == test_json
        assert cached_md == test_md


def test_requirement_extraction():
    """Test requirement extraction works correctly."""
    from spec_tracker.spec_parser import SpecParser

    parser = SpecParser()

    content = """
# Requirements Section

The system MUST validate all inputs before processing.
Responses SHOULD be sent within 5 seconds.
Optional features MAY be disabled.
Strong authentication is REQUIRED.
Detailed logging is RECOMMENDED for production systems.
    """

    result = parser.parse_markdown(content)
    requirements = result["requirements"]

    # Should find multiple requirements
    assert len(requirements) >= 5

    # Check requirement levels
    levels = {r.level for r in requirements}
    assert "MUST" in levels
    assert "SHOULD" in levels
    assert "MAY" in levels
    assert "REQUIRED" in levels
    assert "RECOMMENDED" in levels


def test_error_handling():
    """Test error handling in various scenarios."""
    from spec_tracker.spec_parser import SpecParser
    from spec_tracker.spec_comparator import SpecComparator

    parser = SpecParser()

    # Test with empty content
    empty_result = parser.parse_markdown("")
    assert empty_result["requirements"] == []
    assert empty_result["sections"] == []

    # Test with empty JSON
    empty_json_result = parser.parse_json_schema({})
    assert empty_json_result["definitions"] == {}

    # Test comparator with empty specs
    comparator = SpecComparator()
    empty_spec = {"markdown": empty_result, "json": empty_json_result}

    comparison = comparator.compare_specs(empty_spec, empty_spec)
    assert comparison["summary"]["total_changes"] == 0


if __name__ == "__main__":
    # Run basic integration test
    print("Running basic integration test...")
    test_complete_pipeline_no_changes()
    print("✅ No changes pipeline test passed")

    test_complete_pipeline_with_changes()
    print("✅ Changes pipeline test passed")

    test_parser_integration()
    print("✅ Parser integration test passed")

    test_analyzer_integration()
    print("✅ Analyzer integration test passed")

    print("🎉 All integration tests passed!")
