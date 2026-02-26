---
id: TASK-4.3
title: Define AgentCard requirements (Section 5)
status: Done
assignee: []
created_date: '2026-01-28 09:10'
updated_date: '2026-02-26 09:52'
labels:
  - phase-4
  - requirements
  - agent-card
  - discovery
dependencies:
  - task-1.4
parent_task_id: TASK-4
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Define requirements for AgentCard and discovery from A2A Specification Section 5.

**Reference**: PRD Section 6 Task 4.3, PRD Section 3.3, A2A Spec Section 5

**Location**: `tck/requirements/agent_card.py`

**Components to cover**:
- AgentCard structure: name, capabilities, skills, security_schemes
- Capability declarations
- Skill definitions
- Security scheme definitions
- GetExtendedAgentCard operation

**Requirements to define**:
- AgentCard availability at well-known endpoint
- Required fields in AgentCard
- Capability format and meaning
- Skill definition format
- Security scheme structure

**Discovery endpoint**:
- REST: GET /.well-known/agent.json
- JSON-RPC: method "GetExtendedAgentCard"
- gRPC: rpc GetExtendedAgentCard
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 tck/requirements/agent_card.py exists
- [ ] #2 AgentCard structure requirements are defined
- [ ] #3 Capability requirements are defined
- [ ] #4 Skill requirements are defined
- [ ] #5 Security scheme requirements are defined
- [ ] #6 GetExtendedAgentCard operation requirement is defined
- [ ] #7 Discovery endpoint paths are correct for each transport
<!-- AC:END -->
