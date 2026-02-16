.PHONY: help proto test lint spec

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  make %-10s %s\n", $$1, $$2}'

proto: ## Generate Python gRPC stubs from a2a.proto
	./scripts/generate_grpc_stubs.sh

spec: ## Update the A2A specification and Protobuf definition
	./scripts/update_spec.sh

test: ## Run tests
	uv run pytest

lint: ## Run linter
	uv run ruff check .
