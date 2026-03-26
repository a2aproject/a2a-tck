.PHONY: help proto jsonschema test lint spec codegen-a2a-java-sut codegen-a2a-python-sut

help: ## Show available targets
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  make %-25s %s\n", $$1, $$2}'

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

codegen-a2a-java-sut: ## Generate the a2a-java SUT from Gherkin scenarios
	uv run python -m codegen.generator --target a2a-java --output sut/a2a-java

codegen-a2a-python-sut: ## Generate the a2a-python SUT from Gherkin scenarios
	uv run python -m codegen.generator --target a2a-python --output sut/a2a-python
