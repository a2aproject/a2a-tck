#!/bin/bash
# Script to generate gRPC Python stubs from a2a.proto
# This script generates Protocol Buffer and gRPC stubs for the A2A protocol

set -e  # Exit on error

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m' # No Color

echo "================================================"
echo "A2A Protocol - gRPC Stub Generator"
echo "================================================"
echo ""

# Check if a2a.proto exists
if [ ! -f "a2a.proto" ]; then
    echo -e "${RED}Error: a2a.proto not found in current directory${NC}"
    echo "Please run this script from the project root directory"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 not found${NC}"
    echo "Please install Python 3"
    exit 1
fi

# Check if grpcio-tools is installed
echo "Checking for grpcio-tools..."
if ! python3 -c "import grpc_tools.protoc" 2>/dev/null; then
    echo -e "${YELLOW}Warning: grpcio-tools not found${NC}"
    echo "Installing grpcio-tools..."
    python3 -m pip install grpcio-tools
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error: Failed to install grpcio-tools${NC}"
        echo "Please install manually: python3 -m pip install grpcio-tools"
        exit 1
    fi
fi

# Get the path to grpc_tools protos (includes google API protos from grpcio-tools)
echo "Locating proto files..."
GRPC_TOOLS_PROTO_PATH=$(python3 -c "import grpc_tools; import os; print(os.path.join(os.path.dirname(grpc_tools.__file__), '_proto'))" 2>/dev/null)

if [ -z "$GRPC_TOOLS_PROTO_PATH" ]; then
    echo -e "${RED}Error: Could not locate grpc_tools proto files${NC}"
    exit 1
fi

echo "Found grpc_tools protos at: $GRPC_TOOLS_PROTO_PATH"

# Verify google/api protos exist in grpc_tools (they should be included)
if [ ! -d "$GRPC_TOOLS_PROTO_PATH/google/protobuf" ]; then
    echo -e "${RED}Error: google/protobuf protos not found in grpc_tools${NC}"
    exit 1
fi

# Function to find googleapis proto path
find_googleapis_proto_path() {
    python3 -c "
import sys
import os
# Try to find googleapis proto files
for path in sys.path:
    candidate = os.path.join(path, 'google', 'api', 'annotations.proto')
    if os.path.exists(candidate):
        print(path)
        break
" 2>/dev/null
}

# Check for googleapis-common-protos for google/api
echo "Checking for googleapis-common-protos..."
GOOGLEAPIS_INSTALLED=false
if python3 -c "import google.api.annotations_pb2" 2>/dev/null; then
    GOOGLEAPIS_INSTALLED=true
    # Try to find the proto source files
    GOOGLEAPIS_PROTO_PATH=$(find_googleapis_proto_path)
fi

if [ -z "$GOOGLEAPIS_PROTO_PATH" ]; then
    echo -e "${YELLOW}Installing googleapis-common-protos...${NC}"
    python3 -m pip install googleapis-common-protos

    # Try to locate again
    GOOGLEAPIS_PROTO_PATH=$(find_googleapis_proto_path)
fi

if [ -n "$GOOGLEAPIS_PROTO_PATH" ]; then
    echo "Found googleapis protos at: $GOOGLEAPIS_PROTO_PATH"
else
    echo -e "${YELLOW}Warning: Could not locate googleapis proto source files${NC}"
    echo "Will try to generate using grpc_tools protos only"
fi

# Create output directory if it doesn't exist
readonly OUTPUT_DIR="tck/grpc_stubs"
echo "Creating output directory: ${OUTPUT_DIR}"
mkdir -p "${OUTPUT_DIR}"

# Backup existing stubs if they exist
if [ -f "${OUTPUT_DIR}/a2a_pb2.py" ] || [ -f "${OUTPUT_DIR}/a2a_pb2_grpc.py" ]; then
    BACKUP_DIR="${OUTPUT_DIR}/backup_$(date +%Y%m%d_%H%M%S)"
    echo -e "${YELLOW}Backing up existing stubs to: ${BACKUP_DIR}${NC}"
    mkdir -p "${BACKUP_DIR}"

    # Files to backup
    readonly BACKUP_FILES=("a2a_pb2.py" "a2a_pb2_grpc.py" "a2a_pb2.pyi")

    for file in "${BACKUP_FILES[@]}"; do
        [ -f "${OUTPUT_DIR}/${file}" ] && cp "${OUTPUT_DIR}/${file}" "${BACKUP_DIR}/"
    done
fi

# Generate the stubs
echo ""
echo "Generating gRPC stubs from a2a.proto..."
echo "Proto include paths:"
echo "  - Current directory: ."
echo "  - grpc_tools: ${GRPC_TOOLS_PROTO_PATH}"
if [ -n "$GOOGLEAPIS_PROTO_PATH" ]; then
    echo "  - googleapis: ${GOOGLEAPIS_PROTO_PATH}"
fi
echo ""

# Build protoc command arguments
PROTOC_ARGS=(
    "-I."
    "-I${GRPC_TOOLS_PROTO_PATH}"
)

if [ -n "$GOOGLEAPIS_PROTO_PATH" ]; then
    PROTOC_ARGS+=("-I${GOOGLEAPIS_PROTO_PATH}")
fi

PROTOC_ARGS+=(
    "--python_out=${OUTPUT_DIR}"
    "--grpc_python_out=${OUTPUT_DIR}"
    "--pyi_out=${OUTPUT_DIR}"
    "a2a.proto"
)

python3 -m grpc_tools.protoc "${PROTOC_ARGS[@]}"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Successfully generated gRPC stubs!${NC}"
    echo ""
    
    # Show grpcio version used
    GRPC_VERSION=$(python3 -c "import grpc; print(grpc.__version__)" 2>/dev/null || echo "unknown")
    echo "Generated with grpcio version: ${GRPC_VERSION}"
    echo ""
    
    echo "Generated files:"
    ls -lh "${OUTPUT_DIR}"/a2a_pb2*
    echo ""
    echo "Files generated in: ${OUTPUT_DIR}/"
    echo "  - a2a_pb2.py       : Protocol Buffer message definitions"
    echo "  - a2a_pb2_grpc.py  : gRPC service stubs"
    echo "  - a2a_pb2.pyi      : Type hints for Protocol Buffers"
    echo ""
    echo -e "${GREEN}Done!${NC}"
else
    echo ""
    echo -e "${RED}✗ Failed to generate gRPC stubs${NC}"
    echo "Please check the error messages above"
    exit 1
fi
