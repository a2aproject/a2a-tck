#!/bin/bash

# Default values
ORG="a2aproject"
BRANCH="main"
SPEC_DIR="specification"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --org)
            ORG="$2"
            shift 2
            ;;
        --branch)
            BRANCH="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Download A2A specification files from GitHub"
            echo ""
            echo "Options:"
            echo "  --org ORG        GitHub organization (default: a2aproject)"
            echo "  --branch BRANCH  Git branch (default: main)"
            echo "  --help, -h       Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0"
            echo "  $0 --org myorg --branch develop"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

download() {
    local url="$1"
    local filename="$2"
    local dest_path="${SPEC_DIR}/${filename}"

    echo "⬇️ Downloading ${filename}..."
    if curl -sfL -o "$dest_path" "$url"; then
        echo "✅ Successfully downloaded ${filename}"
        return 0
    else
        echo "❌ Failed to download ${filename}"
        return 1
    fi
}

# Create spec directory if it doesn't exist
mkdir -p "$SPEC_DIR"

# Base URL for raw GitHub content
BASE_URL="https://raw.githubusercontent.com/${ORG}/A2A/${BRANCH}"

echo "Downloading A2A specification files..."
echo "Organization: $ORG"
echo "Branch: $BRANCH"
echo ""

download "${BASE_URL}/specification/a2a.proto" "a2a.proto" || exit 1
download "${BASE_URL}/specification/buf.lock" "buf.lock" || exit 1
download "${BASE_URL}/specification/buf.yaml" "buf.yaml" || exit 1
download "${BASE_URL}/docs/specification.md" "specification.md" || exit 1

# Get the latest commit hash from GitHub API
echo "Fetching commit hash..."
COMMIT_HASH=$(curl -sf "https://api.github.com/repos/${ORG}/A2A/commits/${BRANCH}" | grep -m1 '"sha"' | cut -d'"' -f4)
if [ -z "$COMMIT_HASH" ]; then
    echo "⚠️ Could not fetch commit hash, using 'unknown'"
    COMMIT_HASH="unknown"
else
    echo "📌 Commit: ${COMMIT_HASH:0:7}"
fi

# Create version.json with download metadata
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
cat > "${SPEC_DIR}/version.json" <<EOF
{
  "downloadTime": "${TIMESTAMP}",
  "organization": "${ORG}",
  "repository": "A2A",
  "branch": "${BRANCH}",
  "commitHash": "${COMMIT_HASH}",
  "sourceUrl": "https://github.com/${ORG}/A2A/tree/${COMMIT_HASH}/specification",
  "files": [
    "a2a.proto",
    "buf.lock",
    "buf.yaml",
    "specification.md"
  ]
}
EOF

echo ""
echo "✅ All files downloaded successfully to ${SPEC_DIR}/"
echo "📝 Version metadata saved to ${SPEC_DIR}/version.json"
