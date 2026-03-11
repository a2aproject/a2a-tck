---
name: learn-requirement
description: Learn about a specific TCK requirement. Use when the user asks about a requirement ID (e.g. CORE-SEND-001, GRPC-ERR-001), wants to understand what it tests, or needs to find the spec section, tests, and validators related to a requirement.
allowed-tools: Read Glob Grep Agent
---

# Learn About a Requirement

Follow these steps to help the user understand a TCK requirement in depth.

## Step 1: Identify the requirement

Ask the user for the requirement ID (e.g., `CORE-SEND-001`, `GRPC-ERR-001`, `JSONRPC-SSE-001`, `HTTP_JSON-REST-001`).

If the user describes a concept instead of an ID, search the requirement files to find matching requirements:

```
tck/requirements/core_operations.py    — CORE-*
tck/requirements/binding_grpc.py       — GRPC-*
tck/requirements/binding_jsonrpc.py    — JSONRPC-*
tck/requirements/binding_http_json.py  — HTTP_JSON-*
tck/requirements/data_model.py         — data model requirements
tck/requirements/streaming.py          — streaming requirements
tck/requirements/push_notifications.py — push notification requirements
tck/requirements/agent_card.py         — agent card requirements
tck/requirements/auth.py               — authentication requirements
tck/requirements/versioning.py         — versioning requirements
tck/requirements/interop.py            — interoperability requirements
```

## Step 2: Read the requirement definition

Find and read the `RequirementSpec` entry for the requirement ID in the appropriate file under `tck/requirements/`.

Present the following fields to the user:
- **ID** — the requirement identifier
- **Section** — the spec section number
- **Title** — short description
- **Level** — MUST, SHOULD, or MAY
- **Description** — what the requirement says
- **Operation** — which A2A operation it applies to
- **Expected behavior** — what a compliant implementation should do
- **Spec URL** — convert the local `spec_url` to a GitHub link: read `specification/version.json` for `sourceUrl`, replace `/tree/` with `/blob/`, replace trailing `/specification` with `/docs`, then append the filename and anchor from `spec_url`
- **Tags** — categorization tags
- **Sample input** — example request payload (if provided)

## Step 3: Find the specification text

Read `specification/specification.md` and search for the section referenced by the requirement's `section` field. Present the relevant specification text so the user can see the normative language (MUST/SHOULD/MAY) in context.

## Step 4: Find related tests

Many requirements do **not** have a dedicated test function that references their ID by name. Instead, they are tested through the **parametrized runner** in `tests/compatibility/core_operations/test_requirements.py`. This runner:

1. Collects all registered `RequirementSpec` entries (grouped by level: MUST, SHOULD, MAY)
2. Parametrizes each across all transports (`grpc`, `jsonrpc`, `http_json`)
3. Uses `execute_operation(client, requirement)` to send the requirement's `sample_input` via the appropriate operation
4. Validates the response (success, schema conformance, or expected error)

Requirements tagged `multi-operation` or without an `operation` are **excluded** from the parametrized runner and are instead covered by dedicated test modules.

To find how a requirement is tested:

1. **First**, search for the requirement ID in the test files:
   - `tests/compatibility/core_operations/` — cross-transport tests
   - `tests/compatibility/grpc/` — gRPC-specific tests
   - `tests/compatibility/jsonrpc/` — JSON-RPC-specific tests
   - `tests/compatibility/http_json/` — HTTP+JSON-specific tests

2. **If no dedicated test is found**, check whether the requirement has an `operation` and is not tagged `multi-operation`. If so, it is tested by the parametrized runner in `test_requirements.py`.

Read the test code and explain:
- What the test does step by step
- What request it sends to the SUT
- What response it expects
- What conditions cause the test to pass or fail

## Step 5: Find related validators

Search `tck/validators/` for any validation logic related to this requirement's operation or error codes.

## Step 6: Summarize

Present a concise summary to the user:

1. **What it requires** — plain-language explanation of the requirement
2. **Why it matters** — the purpose in the context of the A2A protocol
3. **How it's tested** — what the TCK does to verify compliance
4. **How to pass** — what an SUT implementation needs to do to satisfy this requirement
