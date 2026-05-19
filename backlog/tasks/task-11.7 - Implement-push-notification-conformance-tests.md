---
id: TASK-11.7
title: Implement push notification conformance tests
status: To Do
assignee: []
created_date: '2026-04-22 07:42'
updated_date: '2026-04-22 07:45'
labels:
  - conformance-tests
  - push-notification
  - validators
dependencies:
  - TASK-11.1
parent_task_id: TASK-11
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement conformance tests and payload validators for push notification requirements (PUSH-* prefix).

## TCK webhook receiver
The TCK will spin up a lightweight HTTP server during push notification tests to act as a webhook receiver. This makes the PUSH-DELIVER-* requirements automatable:
1. TCK starts an HTTP server on a free port
2. Test creates a push notification config pointing at the TCK's webhook URL
3. Test triggers a task update (e.g. send a message)
4. TCK webhook server captures the incoming request
5. Test asserts on the webhook payload (StreamResponse format), headers (auth credentials), and delivery guarantees

## CRUD requirements (~7 tests)
These test the push notification config lifecycle via JSON-RPC/gRPC calls:

- **PUSH-CREATE-001**: CreatePushNotificationConfig establishes webhook endpoint — validate response contains push config with required fields
- **PUSH-CREATE-002**: Push config persists until task completion or deletion — validate config persists across multiple retrievals
- **PUSH-GET-001**: GetPushNotificationConfig returns configuration details — validate response matches created config
- **PUSH-GET-002**: GetPushNotificationConfig fails for nonexistent config — validate error response
- **PUSH-LIST-001**: ListPushNotificationConfigs returns all active configs — validate response is array of configs
- **PUSH-DEL-001**: DeletePushNotificationConfig permanently removes config — validate successful deletion response
- **PUSH-DEL-002**: DeletePushNotificationConfig is idempotent — validate repeated deletions succeed

## Webhook delivery requirements (~3 tests)
These test end-to-end push notification delivery using the TCK webhook receiver:

- **PUSH-DELIVER-001**: Agent includes authentication in webhook requests — assert auth credentials in received request headers
- **PUSH-DELIVER-002**: Agent attempts delivery at least once per webhook — assert at least one request received per config
- **PUSH-DELIVER-003**: Webhook payload uses StreamResponse format — validate received payload structure

## Key files
- `tck/requirements/push_notifications.py` — existing requirement definitions
- `tck/tests/` — conformance test location
- `tck/validators/` — payload validator location

## Approach
1. Implement a reusable TCK webhook receiver (HTTP server with request capture and async wait)
2. Add payload validators for PUSH-CREATE, PUSH-GET, PUSH-LIST, PUSH-DEL responses
3. Write Gherkin scenarios for all 10 push notification requirements
4. Implement step definitions for push notification tests
5. Ensure tests work across both JSON-RPC and gRPC transports
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Reusable TCK webhook receiver implemented (HTTP server with request capture and configurable timeout)
- [ ] #2 Payload validators exist for PUSH-CREATE-001, PUSH-GET-001, PUSH-LIST-001, PUSH-DEL-001 responses
- [ ] #3 Conformance tests cover all 7 CRUD PUSH-* requirements
- [ ] #4 Conformance tests cover all 3 PUSH-DELIVER-* requirements using the TCK webhook receiver
- [ ] #5 Tests pass against a2a-java and a2a-python SUTs that support push notifications
- [ ] #6 make lint and make unit-test pass
<!-- AC:END -->
