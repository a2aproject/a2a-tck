"""Gherkin feature file parser.

Reads ``.feature`` files using the ``gherkin-official`` package and
returns a list of :class:`~codegen.model.Scenario` objects with
triggers and actions resolved via the step registry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gherkin.parser import Parser
from gherkin.token_scanner import TokenScanner

from codegen.model import Scenario
from codegen.steps import resolve_action, resolve_trigger


if TYPE_CHECKING:
    from pathlib import Path


def parse_feature_file(path: Path) -> list[Scenario]:
    """Parse a single ``.feature`` file and return its scenarios."""
    parser = Parser()
    doc = parser.parse(TokenScanner(path.read_text()))

    scenarios: list[Scenario] = []
    for child in doc["feature"]["children"]:
        if "scenario" not in child:
            continue
        raw = child["scenario"]
        scenario = _build_scenario(raw, path)
        scenarios.append(scenario)

    return scenarios


def parse_feature_files(paths: list[Path]) -> list[Scenario]:
    """Parse multiple ``.feature`` files and return all scenarios."""
    scenarios: list[Scenario] = []
    for path in paths:
        scenarios.extend(parse_feature_file(path))
    return scenarios


def _build_scenario(raw: dict, path: Path) -> Scenario:
    """Build a Scenario from a raw Gherkin AST scenario dict."""
    name = raw["name"]
    steps = raw.get("steps", [])

    trigger = None
    actions = []

    for step in steps:
        keyword = step["keyword"].strip()
        text = step["text"]
        doc_string = _extract_doc_string(step)

        if keyword == "When":
            trigger = resolve_trigger(text, doc_string)
        elif keyword in ("Then", "And", "But"):
            actions.append(resolve_action(text, doc_string))
        else:
            msg = f"{path}:{step['location']['line']}: unsupported keyword {keyword!r}"
            raise ValueError(msg)

    if trigger is None:
        msg = f"{path}: scenario {name!r} has no When step"
        raise ValueError(msg)

    return Scenario(name=name, trigger=trigger, actions=actions)


def _extract_doc_string(step: dict) -> str | None:
    """Extract the doc string content from a step, if present."""
    ds = step.get("docString")
    if ds is not None:
        return ds["content"]
    return None
