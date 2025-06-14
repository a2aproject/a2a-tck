#!/bin/bash
echo "INFO: Dummy SUT - Prerequisites script started."
echo "INFO: Checking system requirements..."
sleep 1
echo "INFO: Downloading dependencies (simulated)..."
sleep 2
# Create a dummy file to indicate build was run
touch ../dummy_build_indicator.txt
echo "INFO: Dummy SUT - Prerequisites script finished successfully."
exit 0
