#!/bin/bash
code=$1
echo "Checking error code $code..."
jq --arg code "$code" '.definitions | to_entries[] | 
  select(.value.properties.code.const == ($code | tonumber)) | 
  {name: .key, code: .value.properties.code.const, message: .value.properties.message}' a2a_schema.json 