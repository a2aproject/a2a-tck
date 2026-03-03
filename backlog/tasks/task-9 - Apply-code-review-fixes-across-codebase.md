---
id: TASK-9
title: Apply code review fixes across codebase
status: Done
assignee: []
created_date: '2026-03-03 10:21'
labels:
  - refactoring
  - code-review
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Apply fixes for all 11 issues identified during full code review against AGENTS.md conventions:

1. Add `from __future__ import annotations` to all Python files (21 files)
2. Rename `_TRANSPORT` to `TRANSPORT` in transport clients (fixes SLF001, 9 files)
3. Extract shared test helpers (fail_msg, record, get_client) into `_test_helpers.py` (deduplicate 11 test files)
4. Consolidate `_extract_grpc_task_id`/`_extract_grpc_context_id` into single `_extract_grpc_field` in `_task_helpers.py`
5. Fix `test_task_lifecycle.py`: remove dead code, add @streaming marker, top-level a2a_pb2 import, frozenset constants
6. Add YAML type guard in `run_sut.py`
<!-- SECTION:DESCRIPTION:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Applied all 11 code review fixes across 38 files (461 insertions, 742 deletions). Key changes: added future annotations everywhere, made transport constants public, extracted shared test helpers to eliminate duplication, consolidated gRPC field extraction, cleaned up test_task_lifecycle.py, and added YAML type guard. All lint checks and unit tests pass. Verified no regressions against SUT. Committed as bb504a1.
<!-- SECTION:FINAL_SUMMARY:END -->
