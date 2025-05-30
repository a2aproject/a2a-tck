#!/usr/bin/env python3
"""
Marker Consistency Validation Script

This script validates that all test files use the new categorized marker system
and identifies any inconsistencies or old markers that need to be updated.
"""

import os
import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

# New marker definitions
NEW_MARKERS = {
    'mandatory_jsonrpc', 'mandatory_protocol',
    'optional_capability', 'quality_basic', 'quality_production', 
    'optional_feature'
}

# Old markers that should be replaced
OLD_MARKERS = {'core', 'all'}

# Expected markers by directory
DIRECTORY_MARKER_MAPPING = {
    'tests/mandatory/jsonrpc': {'mandatory_jsonrpc'},
    'tests/mandatory/protocol': {'mandatory_protocol'},
    'tests/optional/capabilities': {'optional_capability'},
    'tests/optional/quality': {'quality_basic', 'quality_production'},
    'tests/optional/features': {'optional_feature', 'mandatory_protocol'}  # Some tests may have been misplaced
}

class MarkerVisitor(ast.NodeVisitor):
    def __init__(self):
        self.functions = []
        self.current_file = None
        
    def visit_FunctionDef(self, node):
        if node.name.startswith('test_'):
            markers = []
            docstring = ast.get_docstring(node) or ""
            
            # Extract pytest markers
            for decorator in node.decorator_list:
                if (hasattr(decorator, 'attr') and 
                    hasattr(decorator, 'value') and
                    hasattr(decorator.value, 'attr') and
                    decorator.value.attr == 'mark'):
                    markers.append(decorator.attr)
                elif (hasattr(decorator, 'id') and 
                      decorator.id in NEW_MARKERS):
                    markers.append(decorator.id)
            
            self.functions.append({
                'file': self.current_file,
                'name': node.name,
                'markers': markers,
                'docstring': docstring,
                'line': node.lineno
            })
            
        self.generic_visit(node)

def find_old_markers_in_files() -> List[Tuple[str, int, str]]:
    """Find old markers using grep-like search."""
    issues = []
    
    for root, dirs, files in os.walk('tests'):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r') as f:
                        lines = f.readlines()
                        
                    for i, line in enumerate(lines, 1):
                        # Look for old marker patterns
                        if re.search(r'@pytest\.mark\.(core|all)', line):
                            issues.append((filepath, i, line.strip()))
                            
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
                    
    return issues

def analyze_test_files() -> Dict:
    """Analyze all test files for marker consistency."""
    results = {
        'files_analyzed': 0,
        'tests_found': 0,
        'marker_issues': [],
        'directory_mismatches': [],
        'old_markers': [],
        'undocumented_tests': [],
        'missing_markers': []
    }
    
    visitor = MarkerVisitor()
    
    for root, dirs, files in os.walk('tests'):
        for file in files:
            if file.endswith('.py') and file.startswith('test_'):
                filepath = os.path.join(root, file)
                results['files_analyzed'] += 1
                
                try:
                    with open(filepath, 'r') as f:
                        tree = ast.parse(f.read())
                        
                    visitor.current_file = filepath
                    visitor.visit(tree)
                    
                except Exception as e:
                    print(f"Error analyzing {filepath}: {e}")
    
    results['tests_found'] = len(visitor.functions)
    
    # Analyze each test function
    for func in visitor.functions:
        # Check for old markers
        old_markers_found = [m for m in func['markers'] if m in OLD_MARKERS]
        if old_markers_found:
            results['old_markers'].append({
                'file': func['file'],
                'test': func['name'],
                'markers': old_markers_found,
                'line': func['line']
            })
        
        # Check for missing markers
        if not func['markers']:
            results['missing_markers'].append({
                'file': func['file'],
                'test': func['name'],
                'line': func['line']
            })
        
        # Check directory/marker consistency
        for dir_path, expected_markers in DIRECTORY_MARKER_MAPPING.items():
            if func['file'].startswith(dir_path):
                actual_markers = set(func['markers']) & NEW_MARKERS
                if actual_markers and not actual_markers.issubset(expected_markers):
                    results['directory_mismatches'].append({
                        'file': func['file'],
                        'test': func['name'],
                        'directory': dir_path,
                        'expected': expected_markers,
                        'actual': actual_markers,
                        'line': func['line']
                    })
        
        # Check for proper documentation
        if not func['docstring'] or 'MANDATORY:' not in func['docstring'] and 'OPTIONAL' not in func['docstring'] and 'QUALITY' not in func['docstring']:
            results['undocumented_tests'].append({
                'file': func['file'],
                'test': func['name'],
                'line': func['line']
            })
    
    return results

def generate_report(results: Dict) -> str:
    """Generate a comprehensive validation report."""
    report = []
    report.append("# A2A TCK Marker Consistency Validation Report")
    report.append("=" * 60)
    report.append("")
    
    # Summary
    report.append("## Summary")
    report.append(f"- Files analyzed: {results['files_analyzed']}")
    report.append(f"- Tests found: {results['tests_found']}")
    report.append(f"- Old markers found: {len(results['old_markers'])}")
    report.append(f"- Missing markers: {len(results['missing_markers'])}")
    report.append(f"- Directory mismatches: {len(results['directory_mismatches'])}")
    report.append(f"- Undocumented tests: {len(results['undocumented_tests'])}")
    report.append("")
    
    # Old markers section
    if results['old_markers']:
        report.append("## ❌ Old Markers Found")
        report.append("These tests still use old marker system and need updating:")
        report.append("")
        for issue in results['old_markers']:
            report.append(f"- **{issue['file']}:{issue['line']}** - `{issue['test']}()`")
            report.append(f"  Old markers: {issue['markers']}")
        report.append("")
    
    # Missing markers section
    if results['missing_markers']:
        report.append("## ⚠️ Tests Without Markers")
        report.append("These tests have no categorization markers:")
        report.append("")
        for issue in results['missing_markers']:
            report.append(f"- **{issue['file']}:{issue['line']}** - `{issue['test']}()`")
        report.append("")
    
    # Directory mismatches section
    if results['directory_mismatches']:
        report.append("## 🔄 Directory/Marker Mismatches")
        report.append("These tests may be in the wrong directory for their markers:")
        report.append("")
        for issue in results['directory_mismatches']:
            report.append(f"- **{issue['file']}:{issue['line']}** - `{issue['test']}()`")
            report.append(f"  Directory: `{issue['directory']}`")
            report.append(f"  Expected markers: {issue['expected']}")
            report.append(f"  Actual markers: {issue['actual']}")
        report.append("")
    
    # Undocumented tests section
    if results['undocumented_tests']:
        report.append("## 📝 Tests Needing Documentation Updates")
        report.append("These tests need proper category documentation:")
        report.append("")
        for issue in results['undocumented_tests']:
            report.append(f"- **{issue['file']}:{issue['line']}** - `{issue['test']}()`")
        report.append("")
    
    # Success message
    if not any([results['old_markers'], results['missing_markers'], 
               results['directory_mismatches']]):
        report.append("## ✅ All Markers Consistent!")
        report.append("No marker consistency issues found.")
        report.append("")
    
    return "\n".join(report)

def main():
    print("🔍 Validating A2A TCK marker consistency...")
    print()
    
    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Find old markers with grep
    print("Searching for old markers...")
    old_marker_occurrences = find_old_markers_in_files()
    
    if old_marker_occurrences:
        print(f"❌ Found {len(old_marker_occurrences)} old marker occurrences:")
        for filepath, line, content in old_marker_occurrences:
            print(f"  {filepath}:{line} - {content}")
        print()
    
    # Analyze test files
    print("Analyzing test file structure...")
    results = analyze_test_files()
    
    # Generate report
    report = generate_report(results)
    
    # Write report to file
    with open('marker_validation_report.md', 'w') as f:
        f.write(report)
    
    print("📋 Validation complete!")
    print(f"📄 Report saved to: marker_validation_report.md")
    print()
    
    # Print summary to console
    if results['old_markers'] or results['missing_markers'] or results['directory_mismatches']:
        print("❌ Issues found:")
        if results['old_markers']:
            print(f"  - {len(results['old_markers'])} tests with old markers")
        if results['missing_markers']:
            print(f"  - {len(results['missing_markers'])} tests without markers")
        if results['directory_mismatches']:
            print(f"  - {len(results['directory_mismatches'])} tests in wrong directories")
        print()
        print("📋 See marker_validation_report.md for details")
        return 1
    else:
        print("✅ All markers are consistent!")
        return 0

if __name__ == "__main__":
    exit(main()) 