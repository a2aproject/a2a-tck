#!/bin/bash

#importing environment variables
if [ -f "$(dirname "$0")/.venv/bin/activate" ]; then
    source "$(dirname "$0")/.venv/bin/activate"
else
    echo "Error: .venv file not found in $(dirname "$0")"
    exit 1
fi

# Run the SUT
echo "Running the SUT"

cd ../tck_core_agent
uv run .