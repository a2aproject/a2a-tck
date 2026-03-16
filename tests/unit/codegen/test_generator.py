"""Tests for the generator CLI (codegen.generator)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from codegen.generator import main


if TYPE_CHECKING:
    from pathlib import Path

_SCENARIOS_DIR = __import__("pathlib").Path(__file__).resolve().parents[3] / "scenarios"


class TestGeneratorCLI:
    """Tests for the generator CLI entry point."""

    def test_generates_a2a_java_project(self, tmp_path: Path) -> None:
        """Running the generator with --target a2a-java produces a Java project."""
        rc = main(["--target", "a2a-java", "--output", str(tmp_path), "--scenarios", str(_SCENARIOS_DIR)])
        assert rc == 0

        assert (tmp_path / "pom.xml").exists()
        assert (
            tmp_path / "src" / "main" / "java"
            / "org" / "a2aproject" / "sdk"
            / "TckAgentExecutorProducer.java"
        ).exists()

    def test_default_target_is_a2a_java(self, tmp_path: Path) -> None:
        """Default target is a2a-java when --target is omitted."""
        rc = main(["--output", str(tmp_path), "--scenarios", str(_SCENARIOS_DIR)])
        assert rc == 0
        assert (tmp_path / "pom.xml").exists()

    def test_missing_scenarios_returns_error(self, tmp_path: Path) -> None:
        """Empty scenarios directory returns exit code 1."""
        empty = tmp_path / "empty"
        empty.mkdir()
        rc = main(["--output", str(tmp_path), "--scenarios", str(empty)])
        assert rc == 1
