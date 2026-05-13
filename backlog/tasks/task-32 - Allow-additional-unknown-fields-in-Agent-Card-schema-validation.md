---
id: TASK-32
title: Allow additional unknown fields in Agent Card schema validation
status: Done
assignee: []
created_date: '2026-05-13 08:08'
updated_date: '2026-05-13 08:12'
labels:
  - schema
  - validation
  - agent-card
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The A2A spec allows agent cards to contain additional fields (extensions), but the current JSON schema in `specification/a2a.json` has `"additionalProperties": false` on the Agent Card definition (line 62). This causes the TCK to reject valid agent cards that include extension fields.

**Problem:**
- `JSONSchemaValidator` in `tck/validators/json_schema.py` validates agent cards against the schema as-is
- The schema's `"additionalProperties": false` rejects any unknown fields
- The A2A spec permits extensions/additional fields on agent cards

**Approach:**
Modify `JSONSchemaValidator` to support an `allow_additional` mode that strips `"additionalProperties": false` from the resolved schema before validation. This way:
- All required fields and types are still validated
- Unknown/extension fields are not rejected
- The schema file itself stays in sync with the proto-generated source

Add a recursive `_strip_additional_properties()` helper that removes `"additionalProperties": false` entries from the schema tree, and use it when validating agent cards.

**Files involved:**
- `tck/validators/json_schema.py` — add the stripping logic and `allow_additional` parameter
- `tests/compatibility/agent_card/test_agent_card.py` — use relaxed validation for agent card tests
- `tests/unit/validators/test_json_schema.py` — add tests for the new behavior
<!-- SECTION:DESCRIPTION:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added `allow_additional` parameter to `JSONSchemaValidator.validate()` with a recursive `_strip_additional_properties()` helper. Agent Card validation in the TCK now accepts unknown extension fields while still checking required fields and types. Agent Interface validation remains strict. 4 new unit tests cover the behavior. Implemented on branch `task-32/allow-additional-fields-agent-card`.
<!-- SECTION:FINAL_SUMMARY:END -->
