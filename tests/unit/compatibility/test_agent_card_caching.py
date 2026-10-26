"""Regression tests for optional Agent Card caching requirements."""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from tck.reporting.aggregator import CompatibilityAggregator
from tck.reporting.collector import CompatibilityCollector
from tests.compatibility.agent_card import test_agent_card_caching as caching_tests


_SUT_URL = "http://sut.example"


def _response(*, headers: dict[str, str]) -> httpx.Response:
    return httpx.Response(
        status_code=200,
        headers=headers,
        request=httpx.Request("GET", f"{_SUT_URL}/.well-known/agent-card.json"),
    )


class TestOptionalLastModified:
    """CARD-CACHE-003 is optional when the header is absent."""

    def test_missing_header_is_recorded_as_skipped(self) -> None:
        """An absent optional header is represented as a skipped result."""
        collector = CompatibilityCollector()

        with patch.object(
            caching_tests,
            "_fetch_agent_card",
            return_value=_response(headers={}),
        ), pytest.raises(pytest.skip.Exception, match="optional"):
            caching_tests.TestAgentCardLastModified().test_last_modified_present(
                _SUT_URL,
                collector,
            )

        results = collector.get_results()
        assert len(results) == 1
        assert results[0].requirement_id == "CARD-CACHE-003"
        assert results[0].passed is False
        assert results[0].skipped is True

        report = CompatibilityAggregator(collector).aggregate()
        assert report.per_requirement["CARD-CACHE-003"].status == "SKIPPED"

    def test_present_header_is_recorded_as_passed(self) -> None:
        """A present optional header remains a passing result."""
        collector = CompatibilityCollector()

        with patch.object(
            caching_tests,
            "_fetch_agent_card",
            return_value=_response(headers={"last-modified": "Wed, 01 Jan 2025 00:00:00 GMT"}),
        ):
            caching_tests.TestAgentCardLastModified().test_last_modified_present(
                _SUT_URL,
                collector,
            )

        results = collector.get_results()
        assert len(results) == 1
        assert results[0].requirement_id == "CARD-CACHE-003"
        assert results[0].passed is True
        assert results[0].skipped is False
