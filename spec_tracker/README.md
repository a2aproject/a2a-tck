# A2A Specification Change Tracker

## Overview

The A2A Specification Change Tracker is a comprehensive tool that monitors changes in the A2A (Agent-to-Agent) specification and analyzes their impact on the Technology Compatibility Kit (TCK) test suite. It automatically downloads, compares, and reports on specification changes while identifying which tests may be affected.

## Features

- **Automatic Specification Monitoring**: Downloads latest A2A specifications from GitHub
- **Intelligent Change Detection**: Compares markdown and JSON schema specifications with detailed change classification
- **Impact Analysis**: Identifies which tests are affected by specification changes
- **Comprehensive Reporting**: Generates detailed markdown reports and JSON exports
- **Coverage Analysis**: Tracks test coverage of specification requirements
- **Priority Assessment**: Classifies changes by impact level (breaking, behavioral, additions, documentation)
- **Caching System**: Caches specifications locally for offline analysis
- **CLI Interface**: Easy-to-use command-line interface with multiple options

## Installation

The tracker is already integrated into the A2A TCK project. Ensure you have the required dependencies:

```bash
pip install -r requirements.txt
```

Required dependencies:
- `requests>=2.31.0` - For downloading specifications
- `deepdiff>=6.7.1` - For detailed comparison analysis
- `jsonschema>=4.20.0` - For JSON schema validation

## Usage

### Basic Usage

Run a complete specification change analysis:

```bash
./check_spec_changes.py
```

This will:
1. Download the latest A2A specifications from GitHub
2. Compare them with current local specifications
3. Analyze impact on test suite
4. Generate a detailed report

### Command Line Options

```bash
./check_spec_changes.py [OPTIONS]
```

**Options:**

- `--json-url URL` - Custom URL for JSON schema (default: GitHub main branch)
- `--md-url URL` - Custom URL for Markdown spec (default: GitHub main branch)  
- `--output FILE` - Output file for report (default: `spec_analysis_report.md`)
- `--json-export FILE` - Export analysis as JSON
- `--summary-only` - Generate only a brief summary
- `--current-md FILE` - Use local markdown file instead of `spec_analysis/A2A_SPECIFICATION.md`
- `--current-json FILE` - Use local JSON file instead of `spec_analysis/a2a_schema.json`
- `--verbose` - Enable verbose logging
- `--dry-run` - Run analysis without saving reports

### Examples

**Generate summary report only:**
```bash
./check_spec_changes.py --summary-only --output summary.md
```

**Export detailed analysis as JSON:**
```bash
./check_spec_changes.py --json-export analysis.json
```

**Compare with custom specification URLs:**
```bash
./check_spec_changes.py \
  --json-url https://example.com/custom-spec.json \
  --md-url https://example.com/custom-spec.md
```

**Dry run with verbose logging:**
```bash
./check_spec_changes.py --dry-run --verbose
```

## Architecture

The tracker consists of 6 main components:

### 1. Specification Downloader (`spec_downloader.py`)
- Downloads A2A specifications from GitHub
- Implements retry logic with exponential backoff
- Caches specifications locally with timestamps
- Falls back to cache when download fails

### 2. Specification Parser (`spec_parser.py`)
- Parses markdown specifications to extract requirements and sections
- Analyzes JSON schemas for definitions, methods, and error codes
- Extracts requirement levels (MUST, SHOULD, MAY, REQUIRED, RECOMMENDED)
- Generates unique IDs for all requirements

### 3. Specification Comparator (`spec_comparator.py`)
- Compares two specification versions using DeepDiff
- Classifies changes by impact:
  - **Breaking Changes (10pts)**: Removed required fields, methods, definitions
  - **Behavioral Changes (5pts)**: Added MUST requirements
  - **Non-breaking Additions (2pts)**: Added methods, definitions, optional fields
  - **Documentation Changes (1pt)**: Section changes, added recommendations
- Calculates total impact scores and risk levels

### 4. Test Impact Analyzer (`test_impact_analyzer.py`)
- Builds registry of all test functions using AST parsing
- Extracts specification references from test docstrings
- Maps specification changes to affected tests
- Analyzes test coverage of requirements
- Assesses priority levels for review

### 5. Report Generator (`report_generator.py`)
- Generates comprehensive markdown reports
- Creates executive summaries with risk assessments
- Formats detailed change analysis
- Provides actionable recommendations
- Supports JSON export for programmatic use

### 6. Main Script (`main.py`)
- Orchestrates the complete analysis pipeline
- Provides CLI interface with argument parsing
- Handles errors gracefully with appropriate exit codes
- Supports multiple output formats

## Report Structure

Generated reports include 7 main sections:

1. **Header**: Analysis metadata and version comparison
2. **Executive Summary**: Key metrics, risk assessment, priority indicators
3. **Specification Changes**: Detailed breakdown of all changes
4. **Test Impact Analysis**: Lists of affected tests by category
5. **Test Coverage Analysis**: Coverage metrics and gaps
6. **Recommendations**: Prioritized action items with timelines
7. **Quality Metrics**: Testing targets and improvement suggestions

## Exit Codes

- `0`: No changes detected
- `1`: Changes detected (review recommended)
- `2`: Breaking changes detected (immediate action required)

## File Structure

```
spec_tracker/
├── __init__.py                 # Package initialization
├── spec_downloader.py          # Specification download functionality
├── spec_parser.py              # Specification parsing
├── spec_comparator.py          # Change detection and classification
├── test_impact_analyzer.py     # Test impact analysis
├── report_generator.py         # Report generation
├── main.py                     # Main orchestration script
├── cache/                      # Cached specifications
├── tests/                      # Unit and integration tests
└── README.md                   # This documentation

check_spec_changes.py           # Convenience wrapper script
```

## Integration with CI/CD

The tracker can be integrated into CI/CD pipelines:

```bash
# Check for specification changes
./check_spec_changes.py --summary-only

# Exit code 2 indicates breaking changes
if [ $? -eq 2 ]; then
    echo "⚠️ Breaking changes detected - review required"
    exit 1
fi
```

## Troubleshooting

### Common Issues

**Network connectivity issues:**
- The tool will automatically fall back to cached specifications
- Use `--verbose` to see detailed network activity

**Import errors:**
- Ensure you're running from the project root directory
- Verify all dependencies are installed: `pip install -r requirements.txt`

**Parser issues:**
- Check that specification files are valid markdown/JSON
- Use `--verbose` to see parsing details

**Missing test references:**
- Tests without specification references will be listed in the report
- Update test docstrings to include relevant specification sections

### Performance

- Initial runs may be slower due to network downloads
- Subsequent runs use cached specifications for faster analysis
- Large test suites may take several seconds to analyze

## Development

### Running Tests

```bash
# Run functional tests
PYTHONPATH=. python spec_tracker/tests/test_functional.py

# Run integration tests with pytest
python -m pytest spec_tracker/tests/test_integration.py -v
```

### Adding New Features

1. Follow the existing architecture patterns
2. Add appropriate error handling and logging
3. Update tests and documentation
4. Ensure backward compatibility

## Contributing

When contributing to the specification tracker:

1. Maintain the existing code style and patterns
2. Add comprehensive error handling
3. Include appropriate logging statements
4. Update documentation for new features
5. Ensure all tests pass before submitting changes

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Run with `--verbose` for detailed logging
3. Review the generated reports for specific guidance
4. Check the test output for validation

## Changelog

### Version 1.0.0 (Phase 8 Complete)
- Initial release with full pipeline functionality
- Comprehensive specification change detection
- Test impact analysis with coverage metrics
- Multiple report formats (markdown, JSON, summary)
- CLI interface with extensive options
- Caching system with fallback capabilities
- Integration tests and documentation 