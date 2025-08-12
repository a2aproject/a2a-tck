import logging

from typing import Any, Dict, Optional, Tuple, Union, cast

import requests

from tck import config


logger = logging.getLogger(__name__)


class SUTClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or config.get_sut_url()
        self.session = requests.Session()

    def send_json_rpc(
        self,
        method: Optional[str] = None,
        params: Union[dict, list, None] = None,
        id: Union[str, int, None] = None,
        extra_headers: Optional[Dict[str, str]] = None,
        jsonrpc: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        if method is None and kwargs:
            method = kwargs.get("method")
            params = kwargs.get("params", params)
            id = kwargs.get("id", id)
            jsonrpc = kwargs.get("jsonrpc", jsonrpc)

        if method is None:
            raise ValueError("Method is required for JSON-RPC request")

        jsonrpc_request = {
            "jsonrpc": jsonrpc or "2.0",
            "method": method,
            "params": params if params is not None else {},
            "id": id if id is not None else "tck-auto-id",
        }
        headers = {"Content-Type": "application/json"}
        if extra_headers:
            headers.update(extra_headers)
        logger.info(f"Sending JSON-RPC request to {self.base_url}: {jsonrpc_request}")
        try:
            response = self.session.post(self.base_url, json=jsonrpc_request, headers=headers, timeout=10)
            logger.info(f"SUT responded with {response.status_code}: {response.text}")
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"HTTP error communicating with SUT: {e}")
            raise
        try:
            return cast("Dict[str, Any]", response.json())
        except ValueError as e:
            logger.error(f"Failed to parse JSON response from SUT: {e}")
            raise

    def raw_send(self, raw_data: str) -> Tuple[int, str]:
        """Send raw data to the SUT endpoint without JSON validation.

        This method is primarily used for testing the SUT's handling of invalid JSON
        and other protocol violations.

        Args:
            raw_data: The raw string data to send

        Returns:
            A tuple of (status_code, response_text)
        """
        headers = {"Content-Type": "application/json"}

        logger.info(f"Sending raw data to {self.base_url}: {raw_data}")

        try:
            response = self.session.post(self.base_url, data=raw_data, headers=headers, timeout=10)
            logger.info(f"SUT responded with {response.status_code}: {response.text}")
            return response.status_code, response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request failed: {e}")
            raise

    def send_raw_json_rpc(self, json_request: dict) -> Dict[str, Any]:
        """Send a JSON-RPC request without validation.

        This method is primarily used for testing the SUT's handling of malformed
        JSON-RPC requests and protocol violations.

        Args:
            json_request: The JSON-RPC request as a dictionary (can be malformed)

        Returns:
            The JSON response from the SUT
        """
        headers = {"Content-Type": "application/json"}

        logger.info(f"Sending raw JSON-RPC request to {self.base_url}: {json_request}")

        try:
            response = self.session.post(self.base_url, json=json_request, headers=headers, timeout=10)
            logger.info(f"SUT responded with {response.status_code}: {response.text}")
            response.raise_for_status()
            return cast("Dict[str, Any]", response.json())
        except requests.RequestException as e:
            logger.error(f"HTTP error communicating with SUT: {e}")
            raise
        except ValueError as e:
            logger.error(f"Failed to parse JSON response from SUT: {e}")
            raise
