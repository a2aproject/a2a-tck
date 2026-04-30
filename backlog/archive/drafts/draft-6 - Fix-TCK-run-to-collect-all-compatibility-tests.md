---
id: DRAFT-6
title: Fix TCK run to collect all compatibility tests
status: Draft
assignee: []
created_date: '2026-04-30 06:44'
updated_date: '2026-04-30 06:52'
labels:
  - testing
  - infrastructure
  - coverage-gap
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The latest TCK run (April 28) only collected 3 tests out of 100+ test functions in the compatibility suite. Only CORE-HIST-003 was tested while all other requirements show "NOT TESTED".

Investigate why the full test suite isn't being collected:
1. Check if there are import errors preventing test collection (e.g. missing google.protobuf)
2. Verify pytest collection works for all test modules in tests/compatibility/
3. Run a full TCK suite with `./run_tck.py --sut-host http://localhost:9999` and verify all tests are collected
4. Ensure the parametrized tests in test_requirements.py generate tests for all requirements with operations
5. Confirm all dedicated test modules (test_task_lifecycle.py, test_error_handling.py, test_push_notifications.py, etc.) are collected

The goal is a clean full run where every requirement with test code shows PASS/FAIL/SKIP instead of "NOT TESTED".
<!-- SECTION:DESCRIPTION:END -->
