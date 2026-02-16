"""Generated protobuf and gRPC stubs for the A2A protocol.

This module adds itself to sys.path to allow the generated gRPC stubs
to import the protobuf module correctly (they use 'import a2a_pb2').
"""

import sys
from pathlib import Path

# Add this directory to sys.path so that 'import a2a_pb2' works
# This is needed because the generated gRPC code uses absolute imports
_generated_dir = str(Path(__file__).parent)
if _generated_dir not in sys.path:
    sys.path.insert(0, _generated_dir)
