#!/usr/bin/env python3
import ast
import os


class TestCategorizer(ast.NodeVisitor):
    def __init__(self):
        self.tests = []

    def visit_FunctionDef(self, node):
        if node.name.startswith("test_"):
            # Extract test info
            docstring = ast.get_docstring(node) or ""
            has_core_mark = any(
                decorator.id == "mark" and hasattr(decorator, "attr") and decorator.attr == "core"
                for decorator in node.decorator_list
                if hasattr(decorator, "id")
            )

            self.tests.append(
                {
                    "name": node.name,
                    "file": self.current_file,
                    "has_docstring": bool(docstring),
                    "mentions_spec": "specification" in docstring.lower() or "spec" in docstring.lower(),
                    "has_must": "MUST" in docstring,
                    "has_should": "SHOULD" in docstring,
                    "is_core": has_core_mark,
                    "docstring_preview": docstring[:100] + "..." if len(docstring) > 100 else docstring,
                }
            )

        self.generic_visit(node)


# Process all test files
categorizer = TestCategorizer()
test_dir = "../tests"

all_tests = []
for filename in os.listdir(test_dir):
    if filename.startswith("test_") and filename.endswith(".py"):
        filepath = os.path.join(test_dir, filename)
        with open(filepath) as f:
            tree = ast.parse(f.read())
            categorizer.current_file = filename
            categorizer.visit(tree)

# Generate report
with open("TEST_CATEGORIZATION.md", "w") as f:
    f.write("# Current Test Categorization Status\n\n")

    f.write("## Summary\n")
    f.write(f"- Total tests: {len(categorizer.tests)}\n")
    f.write(f"- Core tests: {sum(1 for t in categorizer.tests if t['is_core'])}\n")
    f.write(f"- Tests with MUST: {sum(1 for t in categorizer.tests if t['has_must'])}\n")
    f.write(f"- Tests with SHOULD: {sum(1 for t in categorizer.tests if t['has_should'])}\n")

    f.write("\n## Tests Needing Categorization\n")
    for test in categorizer.tests:
        if not test["has_must"] and not test["has_should"]:
            f.write(f"- {test['file']}: {test['name']}\n")
