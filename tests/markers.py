"""
Test markers for A2A TCK compliance levels.
"""

import pytest

# Mandatory markers - MUST requirements
mandatory = pytest.mark.mandatory  # Blocks SDK compliance
mandatory_jsonrpc = pytest.mark.mandatory_jsonrpc  # JSON-RPC 2.0 compliance
mandatory_protocol = pytest.mark.mandatory_protocol  # A2A protocol requirements

# Optional markers - SHOULD/MAY requirements
optional_recommended = pytest.mark.optional_recommended  # SHOULD requirements
optional_feature = pytest.mark.optional_feature  # MAY requirements
optional_capability = pytest.mark.optional_capability  # Capability-dependent

# Quality markers
quality_basic = pytest.mark.quality_basic  # Basic implementation quality
quality_production = pytest.mark.quality_production  # Production-ready quality
quality_advanced = pytest.mark.quality_advanced  # Advanced features

# Transport equivalence markers
transport_equivalence = pytest.mark.transport_equivalence  # Multi-transport functional equivalence

# A2A version-specific markers
a2a_v030 = pytest.mark.a2a_v030  # A2A v0.3.0 specific features

# General markers for convenience
optional = pytest.mark.optional  # General optional functionality
