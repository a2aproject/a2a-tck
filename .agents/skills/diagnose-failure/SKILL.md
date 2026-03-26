---
name: diagnose-failure
description: Diagnose a TCK requirement failure and draft a GitHub issue with the requirement context, failure details, and a curl reproducer. Use when the user wants to report a failing requirement, understand why it failed, or create a bug report for an SUT implementor.
allowed-tools: Read Glob Grep Bash Agent
---

# Diagnose a TCK Failure and Draft a GitHub Issue

Follow these steps to diagnose a failing requirement and produce a GitHub issue body that an SUT implementor can act on.

## Step 1: Identify the failing requirement

Ask the user for one of:
- A requirement ID (e.g., `PUSH-CREATE-001`, `GRPC-ERR-001`)
- A test name from the TCK output
- A transport + error description

Read `reports/compatibility.json` to find the failing requirement, its status per
transport, recorded errors, and `test_ids`. This file is always generated after
every TCK run. The structure uses `per_requirement` (a dict keyed by requirement
ID), not a list. Example: `data["per_requirement"]["VER-SERVER-002"]`.

**Multi-requirement grouping:** When scanning the report, look for related
requirements that likely share the same root cause (e.g., same test module,
similar error messages, same spec section). Group them early so all context
is gathered together rather than diagnosed separately.

Use the SUT URL from the current session or from `reports/compatibility.json`
(`summary.sut_url`) rather than asking the user again.

## Step 2: Gather requirement context

Look up the `RequirementSpec` in the appropriate file under `tck/requirements/`:

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

Extract:
- **ID**, **section**, **title**, **level**, **description**
- **Transport binding** — the HTTP method + path, JSON-RPC method, and gRPC RPC name
- **Expected behavior**
- **spec_url** — convert to a GitHub link (see below)

### Converting spec_url to a GitHub link

The requirement's `spec_url` is a local path like `specification/specification.md#anchor`. To build the GitHub URL:

1. Read `specification/version.json` to get `sourceUrl` (e.g., `https://github.com/a2aproject/A2A/tree/<hash>/specification`)
2. Replace `/tree/` with `/blob/`
3. Replace the trailing `/specification` with `/docs` (because `specification.md` lives under `docs/` on GitHub)
4. Append `/<filename>#<anchor>` from the `spec_url`

Example: `specification/specification.md#343-multi-turn-conversation-patterns` becomes
`https://github.com/a2aproject/A2A/blob/<hash>/docs/specification.md#343-multi-turn-conversation-patterns`

## Step 3: Find the specification text

Search `specification/specification.md` for the section referenced by the requirement. Extract the normative language (MUST/SHOULD/MAY sentences) that defines the expected behavior.

**Fallback:** If the `spec_url` anchor doesn't match a markdown heading exactly,
warn the user that the local specification may be out of date (suggest running
`make spec` to re-fetch). Fall back to the requirement's `description` field
for the normative text and search the spec for nearby keywords instead.

## Step 4: Understand the failure

Read the test code that covers this requirement (search `tests/compatibility/` for the requirement ID or check `tests/compatibility/core_operations/test_requirements.py` for parametrized tests).

Determine:
- What request the test sends
- What response was expected
- What response was actually received (from `reports/compatibility.json` errors or by re-running the test)

**Getting actual errors:** The `errors` field in `compatibility.json` is often
empty or contains only skip messages. When this happens, re-run the specific
failing test with verbose output to get the real error:

```bash
uv run ./run_tck.py --sut-host <sut-host> --verbose-log -- -k "test_name" --tb=long
```

**TCK bug vs SUT bug:** Before drafting an issue, determine whether the failure
is a TCK bug or a SUT bug. Check:
- Does the test logic match the spec requirement?
- Is the transport client sending the right request?
- Is the test expecting the right response format for this transport?

If it's a TCK bug, fix the TCK instead of filing an issue against the SUT.

## Step 5: Build a curl reproducer

Create a minimal curl command sequence that reproduces the failure. The reproducer should:

1. **Verify preconditions** — include commands that show relevant context, such as checking agent card capabilities (e.g., `curl ... | jq .capabilities.pushNotifications`) so the reader understands the setup.
2. **Set up prerequisites** — if the failing operation needs an existing task (e.g., GetTask, CancelTask, push notification CRUD), first create one via SendMessage or the appropriate endpoint.
3. **Execute the failing operation** — use the transport binding from Step 2 to construct the correct curl command.
4. **Show the actual vs expected result** — add comments explaining what the SUT returns vs what the spec requires.

### Transport-specific curl patterns

Use the actual endpoint URLs from the agent card's `supportedInterfaces` array
(fetch from `<sut-host>/.well-known/agent-card.json`) to build accurate
reproducers. Each interface entry has a `url` field with the correct endpoint.

**IMPORTANT:** Always look up the exact method names, paths, and RPC names from
`tck/requirements/base.py` (`TransportBinding` definitions and `OperationType`
enum). Never guess or invent method names — they must match what the TCK
actually uses (e.g., the JSON-RPC method for sending a message is `SendMessage`,
not `message/send`).

**IMPORTANT (gRPC):** The fully qualified gRPC service name must include the
proto package. Look up the `package` declaration in `specification/a2a.proto`
and combine it with the service name. For example, with `package lf.a2a.v1;`
and `service A2AService`, the fully qualified name is `lf.a2a.v1.A2AService`.
Do NOT guess the package — always read it from the proto file.

**HTTP+JSON:**
```bash
curl -s -X <METHOD> <HTTP_JSON_URL><PATH> \
  -H "Content-Type: application/json" \
  -d '<JSON_BODY>'
```

**JSON-RPC:**
```bash
curl -s -X POST <JSONRPC_URL> \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"<METHOD>","params":{...}}'
```

**gRPC** (using grpcurl if available):
```bash
grpcurl -plaintext -d '<JSON>' <GRPC_HOST>:<PORT> <PACKAGE>.<SERVICE>/<RPC>
```

### Verify the reproducer

Always run the reproducer command against the SUT to confirm it triggers the
failure. If the reproducer passes in isolation (e.g., because the failure is
timing-dependent or requires prior state from a full TCK run), note this in
the issue and provide the full TCK run command as the reliable reproducer instead.

## Step 6: Draft the GitHub issue

**Title:** Draft a concise issue title summarizing the failure (e.g., "HTTP+JSON
transport returns 501 instead of 400 for PushNotificationNotSupportedError").
Present the title separately so the user can copy it.

**Multi-requirement root cause:** If multiple requirements fail from the same
root cause, group them into a single issue. List all affected requirement IDs
in the Requirement section.

Use the `test_ids` array from the requirement's entry in `reports/compatibility.json`
for the "TCK test" section — no need to search for test node IDs manually.

Compose the issue using this template:

```markdown
## Summary

<One sentence: what fails and on which transport(s)>

## Requirement

- **ID:** <requirement ID>
- **Section:** <spec section> — <title>
- **Level:** <MUST/SHOULD/MAY>
- **Spec:** <link to specification section>

## Specification

> <Quote the normative text from the specification>

## Expected behavior

<What a compliant implementation should do>

## Actual behavior

<What the SUT actually does — include the error message/status code>

## Reproducer

<The curl commands from Step 5, with comments>

## TCK test

`<full pytest node ID from compatibility.json test_ids>`
```

## Step 7: Present and refine

Show the drafted issue to the user. Present the title separately so it can be
copied independently.

Ask if they want to:
- Adjust the title or description
- Copy the issue to the pasteboard (using `pbcopy` on macOS) so they can paste
  it into a GitHub issue

When copying to the pasteboard, include the title as the first line (prefixed
with `# `) followed by a blank line and the issue body, so everything is in a
single pasteboard operation.
