"""CLI entry point for the A2A TCK code generator.

Usage::

    python -m codegen.generator --target a2a-java --output sut/a2a-java/

Reads all ``scenarios/*.feature`` files, parses them into Scenario
objects, and invokes the target emitter to generate a complete SUT
project.
"""

from __future__ import annotations

import argparse
import sys

from pathlib import Path
from typing import TYPE_CHECKING

from codegen.jakarta_emitter import emit_jakarta_project
from codegen.java_emitter import emit_java_project
from codegen.parser import parse_feature_files
from codegen.python_emitter import emit_python_project


if TYPE_CHECKING:
    from collections.abc import Callable

    from codegen.model import Scenario

_SCENARIOS_DIR = Path(__file__).resolve().parent.parent / "scenarios"

# Registry of target emitters: name → emitter function
_EMITTERS: dict[str, Callable[[list[Scenario], Path], list[Path]]] = {
    "a2a-jakarta": emit_jakarta_project,
    "a2a-java": emit_java_project,
    "a2a-python": emit_python_project,
}


def main(argv: list[str] | None = None) -> int:
    """Run the code generator CLI."""
    parser = argparse.ArgumentParser(
        description="Generate a SUT project from Gherkin scenarios.",
    )
    parser.add_argument(
        "--target",
        choices=sorted(_EMITTERS),
        default="a2a-java",
        help="Target SUT to generate (default: a2a-java)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output directory for the generated project",
    )
    parser.add_argument(
        "--scenarios",
        type=Path,
        default=_SCENARIOS_DIR,
        help=f"Directory containing .feature files (default: {_SCENARIOS_DIR})",
    )
    args = parser.parse_args(argv)

    feature_files = sorted(args.scenarios.glob("*.feature"))
    if not feature_files:
        print(f"Error: no .feature files found in {args.scenarios}", file=sys.stderr)
        return 1

    print(f"Parsing {len(feature_files)} feature file(s)...")
    try:
        scenarios = parse_feature_files(feature_files)
    except ValueError as e:
        print(f"Error parsing feature files: {e}", file=sys.stderr)
        return 1

    print(f"Found {len(scenarios)} scenario(s)")

    emitter = _EMITTERS[args.target]
    print(f"Generating {args.target} project in {args.output}/...")
    generated = emitter(scenarios, args.output)

    for path in generated:
        print(f"  {path}")

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
