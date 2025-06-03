# A2A TCK Specification Change Tracker - Development Plan

## Overview
This development plan guides you through implementing a specification change tracker for the A2A TCK. The tool will compare the current specification against the latest version and identify impacted tests.

## Prerequisites
- Python 3.8+ installed
- Git configured
- Access to the A2A TCK repository
- Basic understanding of JSON, Markdown, and Python
- Familiarity with the project structure

## Important Working Guidelines

### 1. Working Notes Documentation
Create a `working_notes.md` file in the project root and update it after completing each task:
```markdown
# A2A TCK Spec Tracker Development - Working Notes

## Phase 1: Setup and Analysis
### Task 1.1: Environment Setup
- [ ] Created virtual environment
- [ ] Installed dependencies
- [ ] Ran initial TCK test suite
- Status: [In Progress/Complete]
- Date: YYYY-MM-DD
- Notes: [Any issues or observations]

### Task 1.2: ...
```

### 2. Testing Protocol
After each code change in existing files:
1. Run the full TCK test suite: follow what explained in README.md for this
2. Verify no existing tests are broken
3. Document any test output changes in working notes

### 3. Version Control
- Create a new branch: `feature/spec-change-tracker`
- Commit after each completed task with descriptive messages
- Push regularly to avoid losing work

---

## Phase 1: Project Setup and Analysis (2-3 days)

### Task 1.1: Environment Setup
1. Create a new directory `spec_tracker` in the project root
2. Create these files:
   ```
   spec_tracker/
   ├── __init__.py
   ├── spec_downloader.py
   ├── spec_parser.py
   ├── spec_comparator.py
   ├── test_impact_analyzer.py
   ├── report_generator.py
   └── main.py
   ```
3. Add requirements to `requirements.txt`:
   ```
   requests>=2.31.0
   deepdiff>=6.7.1
   jsonschema>=4.20.0
   ```
4. Run initial tests to ensure nothing is broken:
   ```bash
   pytest tests/ -v
   ```
5. Document baseline test results in working notes

### Task 1.2: Analyze Current Specification Structure
1. Study the current specification files:
   - `spec_analysis/A2A_SPECIFICATION.md`
   - `spec_analysis/a2a_schema.json`
2. Create a document `spec_tracker/SPEC_STRUCTURE.md` listing:
   - Key sections in the markdown spec
   - JSON schema structure and important fields
   - Requirement patterns (MUST, SHALL, SHOULD, MAY)
3. Review `spec_analysis/REQUIREMENT_ANALYSIS.md` to understand requirement extraction

### Task 1.3: Analyze Test Organization
1. Study the test structure in `tests/` directory
2. Create `spec_tracker/TEST_MAPPING.md` documenting:
   - Test categories (mandatory, optional, quality)
   - How tests reference specifications (look for docstrings)
   - Test naming conventions
3. Run this command to extract all spec references from tests:
   ```bash
   grep -r "Specification" tests/ --include="*.py" > spec_tracker/current_spec_refs.txt
   ```

---

## Phase 2: Specification Downloader (1-2 days)

### Task 2.1: Implement Basic Downloader
Create `spec_tracker/spec_downloader.py`:

```python
"""
Specification downloader for A2A TCK.
Downloads the latest specification files from GitHub.
"""

import requests
import json
import logging
from pathlib import Path
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

class SpecDownloader:
    """Downloads A2A specification files from GitHub."""
    
    DEFAULT_JSON_URL = "https://raw.githubusercontent.com/google/A2A/main/specification/json/a2a.json"
    DEFAULT_MD_URL = "https://raw.githubusercontent.com/google/A2A/main/docs/specification.md"
    
    def __init__(self, cache_dir: Path = None):
        """Initialize downloader with optional cache directory."""
        self.cache_dir = cache_dir or Path("spec_tracker/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def download_spec(self, json_url: str = None, md_url: str = None) -> Tuple[dict, str]:
        """
        Download specification files.
        
        Args:
            json_url: URL for JSON schema (uses default if None)
            md_url: URL for Markdown spec (uses default if None)
            
        Returns:
            Tuple of (json_data, markdown_content)
        """
        json_url = json_url or self.DEFAULT_JSON_URL
        md_url = md_url or self.DEFAULT_MD_URL
        
        try:
            # Download JSON
            logger.info(f"Downloading JSON spec from {json_url}")
            json_response = requests.get(json_url)
            json_response.raise_for_status()
            json_data = json_response.json()
            
            # Download Markdown
            logger.info(f"Downloading Markdown spec from {md_url}")
            md_response = requests.get(md_url)
            md_response.raise_for_status()
            md_content = md_response.text
            
            # Cache the downloads
            self._cache_specs(json_data, md_content)
            
            return json_data, md_content
            
        except Exception as e:
            logger.error(f"Failed to download specs: {e}")
            raise
            
    def _cache_specs(self, json_data: dict, md_content: str):
        """Save downloaded specs to cache."""
        # Implementation here
        pass
```

### Task 2.2: Add Caching and Error Handling
1. Implement the `_cache_specs` method to save files with timestamps
2. Add a method to load from cache if download fails
3. Add retry logic with exponential backoff
4. Test the downloader:
   ```python
   # Create test_spec_downloader.py
   from spec_tracker.spec_downloader import SpecDownloader
   
   downloader = SpecDownloader()
   json_data, md_content = downloader.download_spec()
   print(f"Downloaded JSON with {len(json_data)} keys")
   print(f"Downloaded MD with {len(md_content)} characters")
   ```

---

## Phase 3: Specification Parser (2 days)

### Task 3.1: Implement Markdown Parser
Create `spec_tracker/spec_parser.py`:

```python
"""
Specification parser for extracting requirements and structure.
"""

import re
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class Requirement:
    """Represents a specification requirement."""
    id: str
    section: str
    level: str  # MUST, SHALL, SHOULD, MAY
    text: str
    context: str  # Surrounding text for context

class SpecParser:
    """Parses A2A specification documents."""
    
    # Regex patterns for requirements
    REQUIREMENT_PATTERN = re.compile(
        r'(.*?)(MUST|SHALL|SHOULD|MAY|REQUIRED|RECOMMENDED)(?! NOT)(.*?)(?:\.|$)',
        re.MULTILINE | re.IGNORECASE
    )
    
    def parse_markdown(self, content: str) -> Dict[str, Any]:
        """
        Parse markdown specification.
        
        Returns:
            Dict with sections, requirements, and structure
        """
        result = {
            'sections': self._extract_sections(content),
            'requirements': self._extract_requirements(content),
            'structure': self._analyze_structure(content)
        }
        return result
        
    def _extract_sections(self, content: str) -> List[Dict[str, str]]:
        """Extract section headers and their content."""
        # Implementation here
        pass
        
    def _extract_requirements(self, content: str) -> List[Requirement]:
        """Extract all requirements (MUST, SHALL, SHOULD, MAY)."""
        requirements = []
        
        # Split content into sections first
        sections = self._split_into_sections(content)
        
        for section_name, section_content in sections.items():
            # Find all requirements in this section
            for match in self.REQUIREMENT_PATTERN.finditer(section_content):
                # Extract requirement details
                # Add to requirements list
                pass
                
        return requirements
```

### Task 3.2: Implement JSON Schema Parser
Add to `spec_parser.py`:

```python
def parse_json_schema(self, schema: dict) -> Dict[str, Any]:
    """
    Parse JSON schema to extract structure and requirements.
    
    Returns:
        Dict with definitions, required fields, and types
    """
    result = {
        'definitions': self._extract_definitions(schema),
        'required_fields': self._extract_required_fields(schema),
        'error_codes': self._extract_error_codes(schema),
        'methods': self._extract_methods(schema)
    }
    return result
    
def _extract_definitions(self, schema: dict) -> Dict[str, Any]:
    """Extract all type definitions from schema."""
    # Look for definitions section
    # Extract each type with its properties
    pass
```

### Task 3.3: Test the Parser
Create `spec_tracker/test_parser.py`:
```python
# Test with current specs
from spec_tracker.spec_parser import SpecParser

parser = SpecParser()

# Test with current spec files
with open('spec_analysis/A2A_SPECIFICATION.md', 'r') as f:
    md_result = parser.parse_markdown(f.read())
    
print(f"Found {len(md_result['requirements'])} requirements")
print(f"Found {len(md_result['sections'])} sections")
```

---

## Phase 4: Specification Comparator (2-3 days)

### Task 4.1: Implement Basic Comparison
Create `spec_tracker/spec_comparator.py`:

```python
"""
Compares two versions of specifications to identify changes.
"""

from deepdiff import DeepDiff
from typing import Dict, List, Any
import json

class SpecComparator:
    """Compares specification versions."""
    
    def compare_specs(self, old_spec: Dict, new_spec: Dict) -> Dict[str, Any]:
        """
        Compare two specification versions.
        
        Returns:
            Dict with added, removed, and modified elements
        """
        comparison = {
            'markdown_changes': self._compare_markdown(
                old_spec.get('markdown', {}), 
                new_spec.get('markdown', {})
            ),
            'json_changes': self._compare_json(
                old_spec.get('json', {}), 
                new_spec.get('json', {})
            ),
            'summary': {}
        }
        
        # Generate summary
        comparison['summary'] = self._generate_summary(comparison)
        
        return comparison
        
    def _compare_markdown(self, old_md: Dict, new_md: Dict) -> Dict[str, Any]:
        """Compare markdown specifications."""
        changes = {
            'requirements': {
                'added': [],
                'removed': [],
                'modified': []
            },
            'sections': {
                'added': [],
                'removed': [],
                'modified': []
            }
        }
        
        # Compare requirements
        old_reqs = {r.id: r for r in old_md.get('requirements', [])}
        new_reqs = {r.id: r for r in new_md.get('requirements', [])}
        
        # Find added requirements
        for req_id in new_reqs:
            if req_id not in old_reqs:
                changes['requirements']['added'].append(new_reqs[req_id])
                
        # Find removed requirements
        for req_id in old_reqs:
            if req_id not in new_reqs:
                changes['requirements']['removed'].append(old_reqs[req_id])
                
        # Find modified requirements
        for req_id in old_reqs:
            if req_id in new_reqs:
                if old_reqs[req_id].text != new_reqs[req_id].text:
                    changes['requirements']['modified'].append({
                        'old': old_reqs[req_id],
                        'new': new_reqs[req_id]
                    })
                    
        return changes
```

### Task 4.2: Implement JSON Schema Comparison
Add detailed JSON comparison methods:
- Compare type definitions
- Compare required fields
- Compare error codes
- Compare method signatures

### Task 4.3: Create Change Classification
Add methods to classify changes by impact:
- Breaking changes (removed required fields, changed types)
- Non-breaking additions
- Documentation changes

---

## Phase 5: Test Impact Analyzer (3 days)

### Task 5.1: Build Test Registry
Create `spec_tracker/test_impact_analyzer.py`:

```python
"""
Analyzes which tests are impacted by specification changes.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Set

class TestImpactAnalyzer:
    """Analyzes impact of spec changes on tests."""
    
    def __init__(self, test_dir: Path = Path("tests")):
        self.test_dir = test_dir
        self.test_registry = self._build_test_registry()
        
    def _build_test_registry(self) -> Dict[str, Dict]:
        """
        Build a registry of all tests with their spec references.
        
        Returns:
            Dict mapping test names to their metadata
        """
        registry = {}
        
        # Walk through all test files
        for test_file in self.test_dir.rglob("test_*.py"):
            # Parse the Python file
            with open(test_file, 'r') as f:
                content = f.read()
                
            # Extract test functions and their docstrings
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                    test_info = {
                        'file': str(test_file),
                        'name': node.name,
                        'docstring': ast.get_docstring(node) or '',
                        'spec_refs': self._extract_spec_refs(ast.get_docstring(node) or ''),
                        'category': self._determine_category(test_file)
                    }
                    registry[f"{test_file.stem}::{node.name}"] = test_info
                    
        return registry
        
    def _extract_spec_refs(self, docstring: str) -> List[str]:
        """Extract specification references from docstring."""
        refs = []
        
        # Pattern for A2A spec references (e.g., "A2A §5.1")
        a2a_pattern = re.compile(r'A2A\s+§[\d.]+')
        refs.extend(a2a_pattern.findall(docstring))
        
        # Pattern for JSON-RPC references
        jsonrpc_pattern = re.compile(r'JSON-RPC\s+\d\.\d\s+§[\d.]+')
        refs.extend(jsonrpc_pattern.findall(docstring))
        
        # Pattern for requirement keywords
        req_pattern = re.compile(r'(MUST|SHALL|SHOULD|MAY|REQUIRED)')
        refs.extend(req_pattern.findall(docstring))
        
        return refs
```

### Task 5.2: Implement Impact Mapping
Add methods to map specification changes to affected tests:

```python
def analyze_impact(self, spec_changes: Dict) -> Dict[str, List[str]]:
    """
    Analyze which tests are impacted by specification changes.
    
    Returns:
        Dict mapping change types to lists of affected tests
    """
    impact = {
        'directly_affected': [],    # Tests that reference changed sections
        'possibly_affected': [],    # Tests in same category as changes
        'new_coverage_needed': [],  # New requirements without tests
        'obsolete_tests': []        # Tests for removed requirements
    }
    
    # Analyze each change
    for req_change in spec_changes['markdown_changes']['requirements']['modified']:
        # Find tests that reference this requirement
        affected_tests = self._find_tests_for_requirement(req_change)
        impact['directly_affected'].extend(affected_tests)
        
    # Continue for other change types...
    
    return impact
```

### Task 5.3: Create Coverage Analysis
Add methods to identify gaps in test coverage:
- Find requirements without tests
- Find tests without valid spec references
- Calculate coverage percentages

---

## Phase 6: Report Generator (2 days)

### Task 6.1: Implement Markdown Report Generator
Create `spec_tracker/report_generator.py`:

```python
"""
Generates markdown reports for specification changes and test impacts.
"""

from datetime import datetime
from typing import Dict, Any
import json

class ReportGenerator:
    """Generates analysis reports."""
    
    def generate_report(self, 
                       spec_changes: Dict,
                       test_impacts: Dict,
                       old_version: str,
                       new_version: str) -> str:
        """
        Generate a comprehensive markdown report.
        
        Returns:
            Markdown formatted report string
        """
        report = []
        
        # Header
        report.append(f"# A2A Specification Change Analysis Report")
        report.append(f"\nGenerated: {datetime.now().isoformat()}")
        report.append(f"\n## Version Comparison")
        report.append(f"- **Current Version**: {old_version}")
        report.append(f"- **Latest Version**: {new_version}")
        
        # Executive Summary
        report.append(f"\n## Executive Summary")
        report.extend(self._generate_summary(spec_changes, test_impacts))
        
        # Detailed Changes
        report.append(f"\n## Specification Changes")
        report.extend(self._format_spec_changes(spec_changes))
        
        # Test Impacts
        report.append(f"\n## Test Impact Analysis")
        report.extend(self._format_test_impacts(test_impacts))
        
        # Recommendations
        report.append(f"\n## Recommendations")
        report.extend(self._generate_recommendations(spec_changes, test_impacts))
        
        return '\n'.join(report)
        
    def _generate_summary(self, spec_changes: Dict, test_impacts: Dict) -> List[str]:
        """Generate executive summary section."""
        summary = []
        
        # Count changes
        total_changes = (
            len(spec_changes['markdown_changes']['requirements']['added']) +
            len(spec_changes['markdown_changes']['requirements']['removed']) +
            len(spec_changes['markdown_changes']['requirements']['modified'])
        )
        
        summary.append(f"\n- **Total Specification Changes**: {total_changes}")
        summary.append(f"- **Directly Affected Tests**: {len(test_impacts['directly_affected'])}")
        summary.append(f"- **New Requirements Needing Tests**: {len(test_impacts['new_coverage_needed'])}")
        
        # Risk assessment
        if len(spec_changes['markdown_changes']['requirements']['removed']) > 0:
            summary.append(f"\n⚠️ **WARNING**: {len(spec_changes['markdown_changes']['requirements']['removed'])} requirements have been removed!")
            
        return summary
```

### Task 6.2: Format Detailed Sections
Implement formatting methods for:
- Requirement changes (with before/after comparison)
- Test impact lists (grouped by category)
- Coverage gaps
- JSON schema changes

### Task 6.3: Add Visualization Helpers
Create methods to generate:
- Summary tables
- Change statistics
- Test coverage metrics

---

## Phase 7: Main Script and Integration (2 days)

### Task 7.1: Create Main Script
Create `spec_tracker/main.py`:

```python
"""
Main script for A2A specification change tracking.
"""

import argparse
import logging
import sys
from pathlib import Path

from spec_downloader import SpecDownloader
from spec_parser import SpecParser
from spec_comparator import SpecComparator
from test_impact_analyzer import TestImpactAnalyzer
from report_generator import ReportGenerator

def main():
    """Main entry point for spec change tracker."""
    parser = argparse.ArgumentParser(
        description="Track A2A specification changes and analyze test impacts"
    )
    parser.add_argument(
        '--json-url',
        help='URL for JSON schema (default: GitHub main branch)',
        default=SpecDownloader.DEFAULT_JSON_URL
    )
    parser.add_argument(
        '--md-url', 
        help='URL for Markdown spec (default: GitHub main branch)',
        default=SpecDownloader.DEFAULT_MD_URL
    )
    parser.add_argument(
        '--output',
        help='Output file for report (default: spec_analysis_report.md)',
        default='spec_analysis_report.md'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Step 1: Download latest specs
        print("📥 Downloading latest specifications...")
        downloader = SpecDownloader()
        new_json, new_md = downloader.download_spec(args.json_url, args.md_url)
        
        # Step 2: Parse specifications
        print("🔍 Parsing specifications...")
        parser = SpecParser()
        
        # Parse current specs
        with open('spec_analysis/A2A_SPECIFICATION.md', 'r') as f:
            current_md = f.read()
        with open('spec_analysis/a2a_schema.json', 'r') as f:
            current_json = json.load(f)
            
        current_spec = {
            'markdown': parser.parse_markdown(current_md),
            'json': parser.parse_json_schema(current_json)
        }
        
        new_spec = {
            'markdown': parser.parse_markdown(new_md),
            'json': parser.parse_json_schema(new_json)
        }
        
        # Step 3: Compare specifications
        print("📊 Comparing specifications...")
        comparator = SpecComparator()
        spec_changes = comparator.compare_specs(current_spec, new_spec)
        
        # Step 4: Analyze test impacts
        print("🧪 Analyzing test impacts...")
        analyzer = TestImpactAnalyzer()
        test_impacts = analyzer.analyze_impact(spec_changes)
        
        # Step 5: Generate report
        print("📝 Generating report...")
        generator = ReportGenerator()
        report = generator.generate_report(
            spec_changes,
            test_impacts,
            "Current",
            "Latest"
        )
        
        # Step 6: Save report
        with open(args.output, 'w') as f:
            f.write(report)
            
        print(f"✅ Report generated: {args.output}")
        
    except Exception as e:
        logging.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### Task 7.2: Create Wrapper Script
Create `check_spec_changes.py` in project root:

```python
#!/usr/bin/env python3
"""
Convenience script to check for A2A specification changes.
"""

import subprocess
import sys

def main():
    """Run the spec change tracker."""
    cmd = [
        sys.executable,
        '-m',
        'spec_tracker.main'
    ] + sys.argv[1:]
    
    subprocess.run(cmd)

if __name__ == "__main__":
    main()
```

Make it executable: `chmod +x check_spec_changes.py`

### Task 7.3: Integration Testing
1. Run the complete pipeline with current specs
2. Create test cases with known changes
3. Verify report accuracy

---

## Phase 8: Testing and Documentation (1-2 days)

### Task 8.1: Create Unit Tests
Create `spec_tracker/tests/` directory with tests for each module:
- `test_downloader.py`
- `test_parser.py`
- `test_comparator.py`
- `test_analyzer.py`
- `test_generator.py`

### Task 8.2: Create Integration Tests
Test the complete pipeline with:
- No changes scenario
- Minor changes scenario
- Major breaking changes scenario

### Task 8.3: Documentation
Create `spec_tracker/README.md`:

```markdown
# A2A Specification Change Tracker

## Overview
This tool compares versions of the A2A specification and identifies which tests are impacted by changes.

## Usage

### Basic Usage
```bash
./check_spec_changes.py
```

### Custom URLs
```bash
./check_spec_changes.py --json-url https://example.com/spec.json --md-url https://example.com/spec.md
```

### Verbose Output
```bash
./check_spec_changes.py --verbose --output detailed_report.md
```

## Report Format
The generated report includes:
1. Executive Summary
2. Detailed Specification Changes
3. Test Impact Analysis
4. Recommendations for TCK updates

## Architecture
[Include component diagram]
```

---

## Verification Checklist

After completing each phase, verify:

1. **No Broken Tests**: Run `pytest tests/` and ensure all pass
2. **Code Quality**: Run `flake8 spec_tracker/` for style issues
3. **Documentation**: Update working notes with progress
4. **Version Control**: Commit with descriptive message

## Final Deliverables

1. Complete `spec_tracker/` package
2. `check_spec_changes.py` executable script
3. Generated sample report
4. Complete documentation
5. Working notes showing development progress
6. All tests passing

## Success Criteria

Your implementation is successful when:

1. Running `./check_spec_changes.py` produces a readable markdown report
2. The report correctly identifies:
   - All specification changes
   - Impacted tests with reasons
   - Coverage gaps
   - Actionable recommendations
3. No existing TCK tests are broken
4. The tool handles errors gracefully
5. Another developer can understand and maintain your code

## Troubleshooting Tips

1. **Import Errors**: Ensure you're in the project root and using the virtual environment
2. **Network Issues**: The downloader should use cached specs as fallback
3. **Parser Issues**: Start with simple patterns and gradually add complexity
4. **Test Discovery**: Use AST parsing instead of regex for reliability
5. **Report Formatting**: Test with small examples first

Remember to update your working notes regularly and ask for help if you get stuck on any phase for more than the allocated time.