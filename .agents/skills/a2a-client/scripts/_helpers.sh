#!/bin/bash
# Shared helper functions for a2a-client scripts.

# URL-encode a string for safe use in URL paths and query parameters.
uri_encode() {
  jq -nr --arg v "$1" '$v|@uri'
}
