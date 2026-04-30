---
id: TASK-32
title: Fix CORE-HIST-003 failure in Java SUT (historyLength=0)
status: To Do
assignee: []
created_date: '2026-04-30 06:52'
labels:
  - bug
  - java-sut
  - history
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
CORE-HIST-003 [SHOULD] is the only failing requirement in the full TCK run of April 30 against the Java SUT.

**Failure:** SendMessage with historyLength=0 returned 1 history message(s), expected none. Fails on all 3 transports (grpc, jsonrpc, http_json — all xfail).

The Java SUT does not honor historyLength=0 in SendMessage requests — it should omit history from the response when historyLength is explicitly set to 0.

Fix location: `sut/a2a-java/` — the SUT's message handler needs to check the historyLength parameter and strip history when it's 0.
<!-- SECTION:DESCRIPTION:END -->
