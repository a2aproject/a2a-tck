import logging
import os

import pytest

from tck import agent_card_utils, config, logging_config
from tck.sut_client import SUTClient

logger = logging.getLogger(__name__)

def pytest_addoption(parser):
    parser.addoption(
        "--sut-url",
        action="store",
        required=True,
        help="Base URL of the SUT's A2A JSON-RPC endpoint (e.g., http://localhost:8000/api)",
    )
    parser.addoption(
        "--test-scope",
        action="store",
        default="core",
        choices=["core", "all"],
        help="Test scope: 'core' (default) or 'all'",
    )
    parser.addoption(
        "--skip-agent-card",
        action="store_true",
        default=False,
        help="Skip fetching and validating the Agent Card",
    )

def pytest_configure(config_pytest):
    # Setup logging before anything else
    log_level = os.environ.get("TCK_LOG_LEVEL", "INFO")
    logging_config.setup_logging(log_level)
    sut_url = config_pytest.getoption("sut_url")
    test_scope = config_pytest.getoption("test_scope")
    config.set_config(sut_url, test_scope)

@pytest.fixture(scope="session")
def agent_card_data(request):
    """
    Session-scoped fixture to fetch and provide the Agent Card data.
    
    This fixture fetches the Agent Card once from the SUT and makes it available
    to all tests that need it. If the Agent Card cannot be fetched or is invalid,
    it will either raise an error or return None based on the --skip-agent-card option.
    
    Returns:
        The parsed Agent Card data as a dictionary, or None if --skip-agent-card is set.
    """
    # Check if we should skip Agent Card fetching
    if request.config.getoption("--skip-agent-card"):
        logger.warning("Skipping Agent Card fetching (--skip-agent-card is set)")
        return None
    
    # Create client instance to get session for HTTP requests
    sut_client = SUTClient()
    sut_url = config.get_sut_url()
    
    # Fetch the Agent Card
    agent_card = agent_card_utils.fetch_agent_card(sut_url, sut_client.session)
    
    if agent_card is None:
        logger.error("Failed to fetch Agent Card from SUT. Some tests may be skipped or fail.")
        # Allow tests to continue but they'll need to handle None
        return None
    
    # Check for minimally required fields (optional check)
    required_fields = ["name", "id", "protocolVersion"]
    missing_fields = [field for field in required_fields if field not in agent_card]
    
    if missing_fields:
        logger.warning(f"Agent Card is missing required fields: {', '.join(missing_fields)}")
    
    return agent_card
