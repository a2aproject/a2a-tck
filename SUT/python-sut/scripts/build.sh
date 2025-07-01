#!/bin/bash

#importing environment variables
if [ -f "$(dirname "$0")/.env" ]; then
    source "$(dirname "$0")/.env"
else
    echo "Error: .env file not found in $(dirname "$0")"
    exit 1
fi

if [ -f "$(dirname "$0")/.venv" ]; then
    source "$(dirname "$0")/.venv/bin/activate"
else
    echo "Error: .venv file not found in $(dirname "$0"). Creating one"
    uv venv "$(dirname "$0")/.venv/"
    source "$(dirname "$0")/.venv/bin/activate"
    
fi

# Build the SUT
echo "Building the SUT"

cd $SDK_HOME
uv pip install .
