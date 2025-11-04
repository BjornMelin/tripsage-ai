# ADR-0036: Adopt AI Elements Response + Sources and remove custom markdown renderers

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-11-04
**Category**: frontend
**Domain**: AI SDK UI / AI Elements
**Related ADRs**: ADR-0026, ADR-0031, ADR-0035
**Related Specs**: SPEC-0010, SPEC-0015

## Context

The chat UI previously rendered text parts with ad hoc JSX. AI Elements provides `Response` (markdown with Streamdown) and `Sources` (citations) as maintained components aligned with AI SDK UI best practices. We want to prioritize library-first usage and delete custom rendering logic.

## Decision

- Use `Response` to render `text` parts in chat; import directly with no wrappers.
- Add `@source "../node_modules/streamdown/dist/index.js";` to `globals.css` for Streamdown styles.
- Render `Sources` only when `source-url` parts are present; map URL and optional title.
- Remove/avoid custom markdown renderers and one-off citation UIs.

## Consequences

### Positive

- Reduces custom code surface; leverages maintained components and features (stream-friendly parsing, GFM, KaTeX).
- Improves UX by surfacing citations when they exist.

### Negative

- Streamdown brings a CSS source requirement; test envs must mock to avoid CSS imports (handled in tests).
- Optional link/image allowlists should be configured if stricter policies are needed.

### Neutral

- No routing changes; minimal delta to page composition.

## Alternatives Considered

### Keep bespoke JSX renderers

- Higher maintenance and drift from docs; misses Streamdown streaming resilience. Rejected.

### Add more AI Elements now (Reasoning/Tool/CodeBlock)

- Premature without stable backend contracts; increases churn and testing burden. Deferred in ADR-0037.

## References

- AI Elements Response: <https://sdk.vercel.ai/elements/components/response>
- AI Elements Sources: <https://sdk.vercel.ai/elements/components/sources>
- Usage examples: <https://ai-sdk.dev/elements/usage>
