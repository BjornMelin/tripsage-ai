# ADR-0037: Phase Reasoning/Tool/CodeBlock adoption behind backend contracts

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-11-04
**Category**: frontend
**Domain**: AI SDK UI / AI Elements
**Related ADRs**: ADR-0036, ADR-0031
**Related Specs**: SPEC-0015

## Context

AI Elements includes components for Reasoning, Tool, and CodeBlock. These require stable backend payloads (e.g., `sendReasoning`, Tool UIParts, object generation schemas) and UX validation. Shipping UI without contracts leads to churn and brittle tests.

## Decision

- Defer Tool and CodeBlock integration until schemas and UX are finalized.
- Add Reasoning only when backend emits reasoning parts and `sendReasoning` is enabled; render conditionally.
- Focus current sprint on compiler enablement and Response/Sources stability.

## Consequences

### Positive

- Limits dormant code and avoids speculative UI and tests.
- Keeps surface area small while preserving a clear path to expand later.

### Negative

- Some advanced UX is postponed until contracts stabilize.

### Neutral

- No immediate API changes required.

## Alternatives Considered

### Implement all components now behind flags

- Adds code churn and testing burden without usage data; flags still require maintenance. Rejected.

### Skip Reasoning entirely

- Misses near-term value when reasoning exists; the conditional approach balances value and risk.

## References

- Reasoning: <https://sdk.vercel.ai/elements/components/reasoning>
- Tool: <https://sdk.vercel.ai/elements/components/tool>
- Code Block: <https://sdk.vercel.ai/elements/components/code-block>
