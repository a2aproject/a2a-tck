# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records (ADRs) for the A2A Technology Compatibility Kit (TCK).

## What is an ADR?

An Architecture Decision Record (ADR) captures an important architectural decision made along with its context and consequences. ADRs help teams:

- Understand why decisions were made
- Onboard new team members
- Review past decisions
- Avoid repeating discussions
- Document trade-offs and alternatives

## ADR Index

- [ADR-001: Authentication Support](ADR-001-authentication-support.md) - Environment-based authentication for testing authenticated SUTs
- [ADR-002: Extended Agent Card Separation](ADR-002-extended-agent-card-separation.md) - Separation of public and extended agent card access
- [ADR-003: Proto-First Code Generation](ADR-003-proto-first-code-generation.md) - Using a2a.proto as source of truth with buf for code generation

## ADR Format

Each ADR follows this structure:

1. **Status** - Proposed, Accepted, Deprecated, Superseded
2. **Context** - The problem and requirements
3. **Decision** - What was decided and how it works
4. **Consequences** - Positive, negative, and neutral impacts
5. **Alternatives** - Other options considered and why they were rejected
6. **References** - Links to specs, issues, related ADRs