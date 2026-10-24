"""Tests for the public TCK runner CLI."""

from __future__ import annotations

from argparse import Namespace

from run_tck import build_pytest_command


def test_build_pytest_command_forwards_message_parts_file() -> None:
    """The public runner forwards the custom fixture path to pytest."""
    args = Namespace(
        sut_host="http://localhost:9999",
        transport="http_json",
        level="must",
        verbose=False,
        verbose_log=False,
        message_parts_file="fixtures/parts.json",
        pytest_args=[],
    )

    command = build_pytest_command(args)

    assert "--message-parts-file=fixtures/parts.json" in command
