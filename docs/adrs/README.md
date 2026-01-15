# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records (ADRs) for the A2A Technology Compatibility Kit (TCK).

## What is an ADR?

An Architecture Decision Record (ADR) captures an important architectural decision made along with its context and consequences. ADRs help teams:

- Understand why decisions were made
- Onboard new team members
- Review past decisions
- Avoid repeating discussions
- Document trade-offs and alternatives

## ADR Format

Each ADR follows this structure:

1. **Status** - Proposed, Accepted, Deprecated, Superseded
2. **Context** - The problem and requirements
3. **Decision** - What was decided and how it works
4. **Consequences** - Positive, negative, and neutral impacts
5. **Alternatives** - Other options considered and why they were rejected
6. **References** - Links to specs, issues, related ADRs

## Index

### Authentication & Security

- **[ADR-001: Authentication Support for Testing Authenticated SUTs](ADR-001-authentication-support.md)**
  - **Status**: Accepted ✅
  - **Date**: 2024-01-14
  - **Summary**: Implements automatic authentication header injection via environment variables to enable testing of SUTs that require authentication. Supports Bearer, Basic, API Key, Custom, and JSON-based authentication.
  - **Impact**: Enables testing authenticated SUTs across all transports (JSON-RPC, gRPC, REST)

- **[ADR-002: Separation of Public and Extended Agent Card Access](ADR-002-extended-agent-card-separation.md)**
  - **Status**: Accepted ✅
  - **Date**: 2024-01-14
  - **Summary**: Separates public agent card access (`get_agent_card()`) from authenticated extended agent card access (`get_authenticated_extended_card()`) to align with A2A v1.0.0 specification.
  - **Impact**: 22 test files updated, improved security testing, full A2A v1.0.0 compliance

## ADR Timeline

```
2024-01-14: ADR-001 (Authentication Support) - Accepted
2024-01-14: ADR-002 (Extended Agent Card Separation) - Accepted
```

## Contributing

When creating a new ADR:

1. **Number it sequentially**: `ADR-XXX-descriptive-title.md`
2. **Use the template**: Follow the format of existing ADRs
3. **Be specific**: Include code examples, diagrams, and concrete details
4. **Link related ADRs**: Reference other ADRs that influenced this decision
5. **Update this index**: Add your ADR to the appropriate section

### ADR Template

```markdown
# ADR-XXX: [Title]

## Status
[Proposed | Accepted | Deprecated | Superseded]

## Context
[What problem are we solving? What are the requirements?]

## Decision
[What did we decide? How does it work?]

## Consequences
### Positive
[Benefits]

### Negative
[Drawbacks]

### Neutral
[Other impacts]

## Alternatives Considered
[What else did we consider? Why did we reject it?]

## References
[Links to specs, issues, PRs]
```

## Related Documentation

- [AUTHENTICATION_SETUP.md](../AUTHENTICATION_SETUP.md) - User guide for authentication configuration
- [A2A_V030_FEATURES.md](../A2A_V030_FEATURES.md) - A2A v0.3.0 features documentation
- [SPEC_UPDATE_WORKFLOW.md](../SPEC_UPDATE_WORKFLOW.md) - Specification update process

## Quick Reference

| ADR | Topic | Date | Status |
|-----|-------|------|--------|
| [001](ADR-001-authentication-support.md) | Authentication Support | 2024-01-14 | ✅ Accepted |
| [002](ADR-002-extended-agent-card-separation.md) | Extended Agent Card Separation | 2024-01-14 | ✅ Accepted |

---

*For questions about ADRs, see the [main project README](../../README.md) or consult the TCK development team.*
