.PHONY: proto test lint

# Generate Python gRPC stubs from a2a.proto
proto:
	./scripts/generate_grpc_stubs.sh

# Run tests
test:
	uv run pytest

# Run linter
lint:
	uv run ruff check .
