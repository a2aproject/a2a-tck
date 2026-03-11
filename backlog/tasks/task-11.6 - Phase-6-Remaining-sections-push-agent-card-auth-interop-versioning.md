---
id: TASK-11.6
title: 'Phase 6: Remaining sections (push, agent card, auth, interop, versioning)'
status: To Do
assignee: []
created_date: '2026-03-11 16:40'
labels:
  - validators
  - remaining-sections
dependencies:
  - TASK-11.1
parent_task_id: TASK-11
priority: low
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Attach validators to remaining requirement sections and document requirements that don't need validators.

## Push Notifications (tck/requirements/push_notifications.py, ~10 reqs)
- PUSH-CREATE-001: response contains push config with required fields
- PUSH-GET-001: response matches created config
- PUSH-LIST-001: response is array of configs
- PUSH-DELETE-001: successful deletion response
- PUSH-DELIVER-*: non-automatable (webhook delivery) — document as skip

## Agent Card (tck/requirements/agent_card.py, ~7 reqs)
- CARD-DISC-001: agent card at well-known URL
- CARD-PROTO-001: protocolVersion field present
- CARD-REQ-001: required fields (name, url, capabilities, skills)
- CARD-SIGN-*: non-automatable (JCS signing) — document as skip

## Auth (tck/requirements/auth.py, ~5 reqs)
- AUTH-TLS-*: non-automatable — document as skip
- AUTH-INTASK-001: auth_required state triggers auth flow

## Interoperability (tck/requirements/interop.py, ~13 reqs)
- INTEROP-EQUIV-*: functional equivalence across transports — may need cross-transport comparison validators

## Versioning (tck/requirements/versioning.py)
- Review and attach validators as needed

## Final step
Document all requirements that were reviewed and marked as "no validator needed" with the reason (error-only, non-automatable, behavioral, no payload constraint).

## Key files
- All requirement files listed above
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 All remaining requirements reviewed
- [ ] #2 Non-automatable requirements explicitly documented
- [ ] #3 Validator coverage summary produced (requirements with validators / total)
- [ ] #4 make lint and make unit-test pass
<!-- AC:END -->
