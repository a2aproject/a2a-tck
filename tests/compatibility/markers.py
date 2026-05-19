"""Convenient marker aliases for A2A TCK tests.

Usage::

    from tests.compatibility.markers import must, core

    @must
    @core
    def test_something(): ...
"""

from __future__ import annotations

import pytest


must = pytest.mark.must
should = pytest.mark.should
may = pytest.mark.may
core = pytest.mark.core
grpc = pytest.mark.grpc
jsonrpc = pytest.mark.jsonrpc
http_json = pytest.mark.http_json
streaming = pytest.mark.streaming
integration = pytest.mark.integration
