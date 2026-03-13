"""Tests for the Gherkin parser (codegen.parser)."""

from __future__ import annotations

from codegen.model import (
    AddArtifact,
    CompleteTask,
    DataPartDef,
    MessageTrigger,
    TextPartDef,
)
from codegen.parser import parse_feature_file


_SCENARIOS_DIR = __import__("pathlib").Path(__file__).resolve().parents[3] / "scenarios"


class TestParseFeatureFile:
    """Tests for parse_feature_file()."""

    def test_parse_core_operations(self) -> None:
        """First scenario is basic completion with correct trigger and action."""
        feature = _SCENARIOS_DIR / "core_operations.feature"
        scenarios = parse_feature_file(feature)

        assert len(scenarios) > 0

        s = scenarios[0]
        assert s.name == "Basic task completion (CORE-SEND-001)"
        assert s.trigger == MessageTrigger(prefix="tck-send-001")
        assert s.actions == [
            CompleteTask(message="Hello from TCK"),
        ]

    def test_parse_scenario_with_artifact(self) -> None:
        """Text artifact scenario has two actions: CompleteTask + AddArtifact."""
        feature = _SCENARIOS_DIR / "core_operations.feature"
        scenarios = parse_feature_file(feature)

        text_artifact = next(s for s in scenarios if s.name == "Task with text artifact")
        assert text_artifact.trigger == MessageTrigger(prefix="tck-artifact-text")
        assert len(text_artifact.actions) == 2  # noqa: PLR2004
        assert text_artifact.actions[0] == CompleteTask()
        assert text_artifact.actions[1] == AddArtifact(
            parts=[TextPartDef(text="Generated text content")]
        )

    def test_parse_scenario_with_docstring(self) -> None:
        """Data artifact scenario captures the JSON doc string."""
        feature = _SCENARIOS_DIR / "core_operations.feature"
        scenarios = parse_feature_file(feature)

        data_artifact = next(s for s in scenarios if s.name == "Task with data artifact")
        assert len(data_artifact.actions) == 2  # noqa: PLR2004
        artifact_action = data_artifact.actions[1]
        assert isinstance(artifact_action, AddArtifact)
        assert isinstance(artifact_action.parts[0], DataPartDef)
        assert '"key"' in artifact_action.parts[0].json_content

    def test_all_scenarios_have_triggers(self) -> None:
        """Every scenario must have a When step producing a trigger."""
        feature = _SCENARIOS_DIR / "core_operations.feature"
        scenarios = parse_feature_file(feature)

        for s in scenarios:
            assert s.trigger is not None, f"Scenario {s.name!r} has no trigger"
            assert isinstance(s.trigger, MessageTrigger)

    def test_all_scenarios_have_actions(self) -> None:
        """Every scenario must have at least one Then step."""
        feature = _SCENARIOS_DIR / "core_operations.feature"
        scenarios = parse_feature_file(feature)

        for s in scenarios:
            assert len(s.actions) > 0, f"Scenario {s.name!r} has no actions"
