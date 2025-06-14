#!/bin/bash

#importing environment variables
if [ -f "$(dirname "$0")/.env" ]; then
    source "$(dirname "$0")/.env"
else
    echo "Error: .env file not found in $(dirname "$0")"
    exit 1
fi

# Run the SUT
echo "Running the SUT"

cd $SDK_HOME/tck
mvn quarkus:dev