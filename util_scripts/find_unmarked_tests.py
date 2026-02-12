#!/usr/bin/env python3
"""
Find all test functions in the tests directory that don't have pytest markers.
"""

import ast
from collections import defaultdict
from pathlib import Path
import sys
from typing import List, Tuple, Set

def _is_pytest_mark_attribute(node: ast.AST) -> bool:
    """Checks if an AST node represents a `pytest.mark.*` attribute."""
    return (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Attribute)
        and isinstance(node.value.value, ast.Name)
        and node.value.value.id == "pytest"
        and node.value.attr == "mark"
    )


def extract_marker_names(markers_file: Path) -> Set[str]:
    """Extract all marker names defined in tests/markers.py."""
    marker_names = set()

    try:
        with open(markers_file, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content)

        for node in ast.walk(tree):
            # Look for assignments like: mandatory = pytest.mark.mandatory
            if not isinstance(node, ast.Assign):
                continue

            value_node = node.value
            # Check if the value is of the form `pytest.mark.*`
            if not _is_pytest_mark_attribute(value_node):
                continue

            # Get the variable name being assigned
            for target in node.targets:
                if isinstance(target, ast.Name):
                    marker_names.add(target.id)
    except (OSError, SyntaxError) as e:
        print(f"Warning: Could not parse markers file: {e}")

    return marker_names


def has_pytest_marker(node: ast.FunctionDef, known_markers: Set[str]) -> bool:
    """Check if a function has any pytest.mark decorators or custom markers."""
    for decorator in node.decorator_list:
        # If the decorator is a call, e.g., @marker(), get the function part.
        decorator_obj = decorator.func if isinstance(decorator, ast.Call) else decorator

        # Check for custom markers like @mandatory or @mandatory()
        if isinstance(decorator_obj, ast.Name) and decorator_obj.id in known_markers:
            return True

        # Check for standard pytest markers like @pytest.mark.foo
        if _is_pytest_mark_attribute(decorator_obj):
            return True

    return False


def find_unmarked_tests(file_path: Path, known_markers: Set[str]) -> List[Tuple[str, int]]:
    """Find all test functions without markers in a file."""
    unmarked_tests = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content, filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if it's a test function
                if node.name.startswith('test_'):
                    # Check if it has any pytest markers
                    if not has_pytest_marker(node, known_markers):
                        unmarked_tests.append((node.name, node.lineno))

    except (OSError, SyntaxError) as e:
        print(f"Error processing {file_path}: {e}")

    return unmarked_tests


def main():
    """Main function to find all unmarked tests."""
    tests_dir = Path("tests")
    report_file = Path("unmarked_tests_report.txt")

    if not tests_dir.exists():
        print(f"Error: {tests_dir} directory not found")
        sys.exit(1)

    # Open the report file for writing
    with open(report_file, 'w', encoding='utf-8') as f:
        def write_line(line: str = ""):
            """Helper to write to both console and file."""
            print(line)
            f.write(line + "\n")

        # Extract known marker names from tests/markers.py
        markers_file = tests_dir / "markers.py"
        known_markers = set()

        if markers_file.exists():
            known_markers = extract_marker_names(markers_file)
            write_line(f"Found {len(known_markers)} custom markers in tests/markers.py:")
            write_line(f"  {', '.join(sorted(known_markers))}")
            write_line()
        else:
            write_line(f"Warning: {markers_file} not found, will only detect @pytest.mark.* decorators")
            write_line()

        # Find all test files
        test_files = list(tests_dir.glob("**/test_*.py"))

        write_line(f"Scanning {len(test_files)} test files...")
        write_line()

        total_unmarked = 0
        files_with_unmarked = []

        for test_file in sorted(test_files):
            unmarked = find_unmarked_tests(test_file, known_markers)

            if unmarked:
                total_unmarked += len(unmarked)
                files_with_unmarked.append((test_file, unmarked))

                # Print results for this file
                rel_path = test_file.relative_to(tests_dir.parent)
                write_line(f"📄 {rel_path}")
                write_line(f"   Found {len(unmarked)} unmarked test(s):")
                for test_name, lineno in unmarked:
                    write_line(f"   - {test_name} (line {lineno})")
                write_line()

        # Summary
        write_line("=" * 70)
        write_line(f"Summary:")
        write_line(f"  Total test files scanned: {len(test_files)}")
        write_line(f"  Files with unmarked tests: {len(files_with_unmarked)}")
        write_line(f"  Total unmarked tests: {total_unmarked}")
        write_line("=" * 70)

        # Group by directory
        if files_with_unmarked:
            write_line()
            write_line("Unmarked tests by directory:")
            by_dir = defaultdict(int)
            for file_path, unmarked in files_with_unmarked:
                dir_name = file_path.parent.relative_to(tests_dir.parent)
                by_dir[dir_name] += len(unmarked)

            for dir_name in sorted(by_dir.keys()):
                write_line(f"  {dir_name}: {by_dir[dir_name]} unmarked test(s)")

    print(f"\nReport saved to: {report_file}")


if __name__ == "__main__":
    main()
