#!/bin/bash
# Script to generate gRPC Python stubs from specification/a2a.proto using buf
# This script generates gRPC stubs for the A2A protocol Protobuf definition

set -e  # Exit on error

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m' # No Color

echo "================================================"
echo "A2A Protocol - gRPC Stub Generator (using buf)"
echo "================================================"
echo ""

# Directories and files
readonly SPEC_DIR="specification"
readonly PROTO_FILE="${SPEC_DIR}/a2a.proto"
readonly OUTPUT_DIR="${SPEC_DIR}/generated"
readonly BUF_BINARY="bin/buf"

# Check if buf binary exists
if [ ! -f "${BUF_BINARY}" ]; then
    echo -e "${RED}Error: buf binary not found at ${BUF_BINARY}${NC}"
    echo "Please run install_buf.sh to install buf"
    exit 1
fi

# Check if a2a.proto exists
if [ ! -f "${PROTO_FILE}" ]; then
    echo -e "${RED}Error: ${PROTO_FILE} file not found${NC}"
    echo "Please run update_spec.sh to download the specification files"
    exit 1
fi

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

# Generate the stubs using buf
echo ""
echo "Generating gRPC stubs from ${PROTO_FILE} using buf..."
echo ""

if $(cd ${SPEC_DIR} && ../${BUF_BINARY} generate); then
    echo ""
    echo -e "${GREEN}✓ Successfully generated gRPC stubs!${NC}"
else
    echo ""
    echo -e "${RED} Failed to generate gRPC stubs${NC}"
    echo "Please check the error messages above"
    exit 1
fi

echo ""
echo "Generated files:"
ls -la "${OUTPUT_DIR}"/*.py
