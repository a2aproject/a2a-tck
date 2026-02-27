.PHONY: help proto jsonschema test lint spec

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  make %-10s %s\n", $$1, $$2}'

proto: ## Generate Python gRPC stubs from a2a.proto
	./scripts/generate_grpc_stubs.sh

jsonschema: ## Generate JSON Schema from a2a.proto (make sure that the googleapis are specified in a GOOGLEAPIS_DIR env var)
	./scripts/proto_to_json_schema.sh specification/a2a.json

spec: ## Update the A2A specification and Protobuf definition
	./scripts/update_spec.sh

unit-test: ## Run unit tests only
	uv run pytest tests/unit

lint: ## Run linter
	uv run ruff check .
