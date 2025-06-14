#!/bin/bash
echo "INFO: Dummy SUT - Run script started."
if [ -f ../dummy_build_indicator.txt ]; then
    echo "INFO: Build indicator found. Proceeding with run."
else
    echo "ERROR: Build indicator not found. Did the build script run?" >&2
    exit 1
fi
echo "INFO: Dummy SUT is now 'running'. Listening on port XXXX (simulated)."
echo "INFO: This is a placeholder SUT. It will run for 20 seconds."
echo "INFO: Press Ctrl+C to stop this script and the main orchestrator."

count=0
while [ "$count" -lt 20 ]; do
    sleep 1
    echo "Dummy SUT heartbeat: $((count+1))/20 seconds..."
    count=$((count+1))
done

echo "INFO: Dummy SUT - Run script finished after 20 seconds."
exit 0
