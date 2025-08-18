"""Functional tests for A2A Specification Change Tracker."""


def test_basic_functionality():
    """Test that all components can be imported and basic operations work."""
    # Test imports
    from spec_tracker.spec_downloader import SpecDownloader
    from spec_tracker.spec_parser import SpecParser
    from spec_tracker.spec_comparator import SpecComparator
    from spec_tracker.test_impact_analyzer import TestImpactAnalyzer
    from spec_tracker.report_generator import ReportGenerator

    # Test basic instantiation
    downloader = SpecDownloader()
    parser = SpecParser()
    comparator = SpecComparator()
    analyzer = TestImpactAnalyzer()
    generator = ReportGenerator()

    assert downloader is not None
    assert parser is not None
    assert comparator is not None
    assert analyzer is not None
    assert generator is not None

    print("✅ All components can be imported and instantiated")


def test_parser_basic():
    """Test parser with simple content."""
    from spec_tracker.spec_parser import SpecParser

    parser = SpecParser()

    # Test markdown parsing
    md_content = "# Test\n\nThe client MUST validate."
    result = parser.parse_markdown(md_content)

    assert "sections" in result
    assert "requirements" in result
    assert "structure" in result

    # Test JSON parsing
    json_content = {"definitions": {"Test": {"type": "object"}}}
    result = parser.parse_json_schema(json_content)

    assert "definitions" in result
    assert "error_codes" in result
    assert "methods" in result

    print("✅ Parser works with basic content")


def test_comparator_basic():
    """Test comparator with simple specs."""
    from spec_tracker.spec_parser import SpecParser
    from spec_tracker.spec_comparator import SpecComparator

    parser = SpecParser()
    comparator = SpecComparator()

    # Create simple specs
    simple_md = "# Test\nThe client MUST validate."
    simple_json = {"definitions": {"Test": {"type": "object"}}}

    spec = {"markdown": parser.parse_markdown(simple_md), "json": parser.parse_json_schema(simple_json)}

    # Compare with itself
    comparison = comparator.compare_specs(spec, spec)

    assert "markdown_changes" in comparison
    assert "json_changes" in comparison
    assert "summary" in comparison
    assert comparison["summary"]["total_changes"] == 0

    print("✅ Comparator works with basic specs")


def test_analyzer_basic():
    """Test analyzer with test directory."""
    from spec_tracker.test_impact_analyzer import TestImpactAnalyzer
    from pathlib import Path

    analyzer = TestImpactAnalyzer(test_dir=Path("tests"))

    # Should find tests
    assert hasattr(analyzer, "test_registry")
    assert isinstance(analyzer.test_registry, dict)

    # Test basic impact analysis
    mock_changes = {
        "markdown_changes": {"requirements": {"added": [], "removed": [], "modified": []}},
        "json_changes": {
            "methods": {"added": {}, "removed": {}, "modified": {}},
            "error_codes": {"added": {}, "removed": {}, "modified": {}},
        },
    }

    impact = analyzer.analyze_impact(mock_changes)

    assert "directly_affected" in impact
    assert "possibly_affected" in impact
    assert "new_coverage_needed" in impact
    assert "obsolete_tests" in impact

    print("✅ Analyzer works with test directory")


def test_generator_basic():
    """Test generator with simple data."""
    from spec_tracker.report_generator import ReportGenerator

    generator = ReportGenerator()

    # Simple test data
    spec_changes = {
        "markdown_changes": {
            "requirements": {"added": [], "removed": [], "modified": []},
            "sections": {"added": [], "removed": [], "modified": []},
        },
        "json_changes": {
            "definitions": {"added": {}, "removed": {}, "modified": {}},
            "methods": {"added": {}, "removed": {}, "modified": {}},
            "error_codes": {"added": {}, "removed": {}, "modified": {}},
        },
        "summary": {"total_changes": 0, "breaking_changes": 0, "total_impact_score": 0, "risk_level": "LOW"},
    }

    test_impacts = {"directly_affected": [], "possibly_affected": [], "new_coverage_needed": [], "obsolete_tests": []}

    coverage_analysis = {"total_tests": 68, "tests_with_refs": 66, "documentation_coverage": 97.1}

    # Generate report
    report = generator.generate_report(spec_changes, test_impacts, coverage_analysis, "v1.0.0", "v1.1.0")

    assert isinstance(report, str)
    assert len(report) > 100
    assert "# A2A Specification Change Analysis Report" in report

    print("✅ Generator works with basic data")


def test_main_script_exists():
    """Test that main script exists and is executable."""
    from pathlib import Path

    main_script = Path("spec_tracker/main.py")
    wrapper_script = Path("check_spec_changes.py")

    assert main_script.exists()
    assert wrapper_script.exists()
    assert wrapper_script.is_file()

    print("✅ Main scripts exist")


def test_help_command():
    """Test help command works."""
    import subprocess
    import sys

    result = subprocess.run([sys.executable, "spec_tracker/main.py", "--help"], capture_output=True, text=True)

    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()

    print("✅ Help command works")


def test_cache_directory_creation():
    """Test cache directory creation."""
    from spec_tracker.spec_downloader import SpecDownloader
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir) / "test_cache"
        downloader = SpecDownloader(cache_dir=cache_dir)

        assert cache_dir.exists()
        assert cache_dir.is_dir()

    print("✅ Cache directory creation works")


if __name__ == "__main__":
    print("Running functional tests...")

    test_basic_functionality()
    test_parser_basic()
    test_comparator_basic()
    test_analyzer_basic()
    test_generator_basic()
    test_main_script_exists()
    test_help_command()
    test_cache_directory_creation()

    print("\n🎉 All functional tests passed!")
    print("✅ A2A Specification Change Tracker is working correctly")
