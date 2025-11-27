# Spec: AI Elements Response + Sources Integration

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-11-04
**Category**: frontend
**Domain**: AI SDK UI / Next.js App Router
**Related ADRs**: ADR-0036, ADR-0037
**Related Specs**: SPEC-0010, SPEC-0008

## Overview

Integrate AI Elements `Response` to render markdown text parts and `Sources` to render citations (`source-url` parts) in the chat UI. Remove bespoke markdown/citation renderers.

## Components

- Response (`@/components/ai-elements/response`)
  - Renders markdown via Streamdown; streaming-friendly; supports GFM + KaTeX.
- Sources (`@/components/ai-elements/sources`)
  - Minimal popover with trigger and content areas; list of `Source` links.
  - Only render when `source-url` parts exist.

## API Contract

- Client: `useChat` from `@ai-sdk/react` provides `UIMessage` with `parts`.
  - `text` → rendered by `Response`.
  - `source-url` → surfaced in `Sources` (url, optional title).
- Server: no changes required; optional route can pass citations via `toUIMessageStreamResponse({ sendSources: true })`.

## Accessibility

- `SourcesTrigger` is a button with `aria-label` and optional count.
- Links use `rel="noreferrer noopener"` and `target="_blank"`.

## Testing

- Response test mocks `streamdown` to avoid KaTeX CSS in test env; asserts wrapper and content.
- Sources test verifies popover opens and renders provided links.

## Risks & Mitigations

- CSS import errors in tests: mock `streamdown` (done).
- Content safety: configure Response `allowedLinkPrefixes/allowedImagePrefixes` if stricter policies are required (future).

## References

- Response docs: <https://sdk.vercel.ai/elements/components/response>
- Sources docs: <https://sdk.vercel.ai/elements/components/sources>
- Usage: <https://ai-sdk.dev/elements/usage>
