---
id: TASK-1.7
title: Create requirement registry skeleton
status: To Do
assignee: []
created_date: '2026-01-28 09:07'
updated_date: '2026-01-28 09:21'
labels:
  - phase-1
  - foundation
  - requirements
dependencies:
  - task-1.4
parent_task_id: TASK-1
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create the skeleton for the requirement registry that will hold all ~100 requirement definitions.

**Reference**: PRD Section 5.1.3 (Requirement Registry)

**Location**: `tck/requirements/registry.py`

**Structure**:
```python
from tck.requirements.base import RequirementSpec, RequirementLevel, OperationType

# Will be populated in Phase 4
ALL_REQUIREMENTS: list[RequirementSpec] = []

# Filtered views
MUST_REQUIREMENTS = [r for r in ALL_REQUIREMENTS if r.level == RequirementLevel.MUST]
SHOULD_REQUIREMENTS = [r for r in ALL_REQUIREMENTS if r.level == RequirementLevel.SHOULD]
MAY_REQUIREMENTS = [r for r in ALL_REQUIREMENTS if r.level == RequirementLevel.MAY]

# Helper functions
def get_requirements_by_section(section_prefix: str) -> list[RequirementSpec]: ...
def get_requirements_by_operation(operation: OperationType) -> list[RequirementSpec]: ...
```

This is a skeleton - actual requirements will be added in Phase 4.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 tck/requirements/registry.py exists
- [ ] #2 ALL_REQUIREMENTS list is defined (can be empty)
- [ ] #3 MUST_REQUIREMENTS, SHOULD_REQUIREMENTS, MAY_REQUIREMENTS filtered lists exist
- [ ] #4 get_requirements_by_section() function is implemented
- [ ] #5 get_requirements_by_operation() function is implemented
- [ ] #6 Module can be imported: from tck.requirements.registry import ALL_REQUIREMENTS
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Implementation Plan

### Steps
1. Create `tck/requirements/registry.py`:

```python
from tck.requirements.base import (
    RequirementSpec,
    RequirementLevel,
    OperationType,
)

# Will be populated in Phase 4
ALL_REQUIREMENTS: list[RequirementSpec] = []

# Filtered views (computed properties)
def get_must_requirements() -> list[RequirementSpec]:
    return [r for r in ALL_REQUIREMENTS if r.level == RequirementLevel.MUST]

def get_should_requirements() -> list[RequirementSpec]:
    return [r for r in ALL_REQUIREMENTS if r.level == RequirementLevel.SHOULD]

def get_may_requirements() -> list[RequirementSpec]:
    return [r for r in ALL_REQUIREMENTS if r.level == RequirementLevel.MAY]

# Convenience aliases
MUST_REQUIREMENTS = property(get_must_requirements)
SHOULD_REQUIREMENTS = property(get_should_requirements)
MAY_REQUIREMENTS = property(get_may_requirements)

# Helper functions
def get_requirements_by_section(section_prefix: str) -> list[RequirementSpec]:
    """Get all requirements for a section (e.g., '3.1')."""
    return [r for r in ALL_REQUIREMENTS if r.section.startswith(section_prefix)]

def get_requirements_by_operation(operation: OperationType) -> list[RequirementSpec]:
    """Get all requirements for an operation type."""
    return [r for r in ALL_REQUIREMENTS if r.operation == operation]

def get_requirements_by_tag(tag: str) -> list[RequirementSpec]:
    """Get all requirements with a specific tag."""
    return [r for r in ALL_REQUIREMENTS if tag in r.tags]
```

2. Export in `tck/requirements/__init__.py`:
```python
from tck.requirements.registry import (
    ALL_REQUIREMENTS,
    get_must_requirements,
    get_should_requirements,
    get_may_requirements,
    get_requirements_by_section,
    get_requirements_by_operation,
    get_requirements_by_tag,
)
```

### Verification
```python
from tck.requirements.registry import ALL_REQUIREMENTS, get_requirements_by_section
assert isinstance(ALL_REQUIREMENTS, list)
assert callable(get_requirements_by_section)
```

### Notes
- Registry is empty initially - populated in Phase 4
- Helper functions ready for use in test parametrization
<!-- SECTION:PLAN:END -->
