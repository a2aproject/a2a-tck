import os
import uuid

import pytest
import requests

import tck.config

from tck import agent_card_utils


def pytest_addoption(parser):
    parser.addoption("--sut-url", action="store", default=None, help="URL of the SUT's A2A JSON-RPC endpoint")
    parser.addoption("--test-scope", action="store", default="core", help="Test scope: 'core' or 'all'")
    parser.addoption("--skip-agent-card", action="store_true", default=False, help="Skip fetching and validating the Agent Card")


def pytest_configure(config):
    sut_url = config.getoption("--sut-url")
    test_scope = config.getoption("--test-scope")
    # skip_agent_card = config.getoption("--skip-agent-card") # Not used directly in config

    if sut_url:
        tck.config.set_config(sut_url, test_scope)
    else:
        # If --sut-url is not provided, the tests requiring it will fail, which is expected.
        # The RuntimeError in get_sut_url will handle the case where it's needed but not set.
        pass


@pytest.fixture(scope="session")
def agent_card_data(request):
    """Pytest fixture to fetch the Agent Card data.
    Skips fetching if --skip-agent-card is provided.
    """
    if request.config.getoption("--skip-agent-card"):
        print("Skipping Agent Card fetch due to --skip-agent-card flag.")
        return None

    sut_url = request.config.getoption("--sut-url") or os.getenv("SUT_URL")
    if not sut_url:
        # This case should ideally be caught earlier, but as a fallback:
        pytest.fail("SUT URL not provided. Cannot fetch Agent Card.")

    # Use a session to potentially reuse connections
    with requests.Session() as session:
        card = agent_card_utils.fetch_agent_card(sut_url, session)
        if card is None:
            pytest.fail("Failed to fetch or parse Agent Card from the SUT. Check SUT URL and Agent Card endpoint.")
        return card


def pytest_generate_tests(metafunc):
    # This hook can be used to parametrize tests based on command line options
    # For example, if you had tests that should only run for a specific scope:
    # if "scope" in metafunc.fixturenames:
    #     metafunc.parametrize("scope", [metafunc.config.getoption("--test-scope")])
    pass


def pytest_collection_modifyitems(config, items):
    # Apply markers based on --test-scope
    if config.getoption("--test-scope") == "core":
        # Keep only items marked with 'core' or mandatory markers
        skip_all = pytest.mark.skip(reason="requires --test-scope all")
        core_markers = {"core", "mandatory", "mandatory_jsonrpc", "mandatory_protocol"}
        for item in items:
            # Check if item has any core markers
            if not any(marker in item.keywords for marker in core_markers):
                item.add_marker(skip_all)

    if config.getoption("--skip-agent-card"):
        skip_agent_card_tests = pytest.mark.skip(reason="--skip-agent-card was specified")
        for item in items:
            if "agent_card" in item.keywords or "test_agent_card" in item.name:
                item.add_marker(skip_agent_card_tests)

    # Note: 'all' scope implicitly runs all tests not explicitly marked to be skipped


@pytest.fixture
def valid_text_message_params():
    # Minimal valid params for message/send (TextPart)
    return {
        "message": {
            "kind": "message",
            "messageId": "test-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [{"kind": "text", "text": "Hello from TCK!"}],
        }
    }


@pytest.fixture
def valid_file_message_params():
    # Valid params for message/send with FilePart
    # Note: mimeType is RECOMMENDED per A2A Specification §6.6.2 FileWithUri Object
    return {
        "message": {
            "kind": "message",
            "messageId": "test-file-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [
                {
                    "kind": "file",
                    "file": {
                        "name": "test.txt",
                        "mimeType": "text/plain",  # RECOMMENDED: Media Type per A2A Spec §6.6.2
                        "url": "https://example.com/test.txt",
                        "sizeInBytes": 1024,
                    },
                }
            ],
        }
    }


@pytest.fixture
def valid_data_message_params():
    # Valid params for message/send with DataPart
    return {
        "message": {
            "kind": "message",
            "messageId": "test-data-message-id-" + str(uuid.uuid4()),
            "role": "user",
            "parts": [{"kind": "data", "data": {"key": "value", "number": 123, "nested": {"array": [1, 2, 3]}}}],
        }
    }
