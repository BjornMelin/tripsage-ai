# SPEC-0112: Markdown rendering (Streamdown v2) and AI Elements Response integration

**Version**: 1.0.0
**Status**: Final
**Date**: 2026-01-23
**Category**: frontend
**Domain**: Markdown rendering / AI UI
**Related ADRs**: [ADR-0073](../../architecture/decisions/adr-0073-streamdown-v2-markdown-renderer.md)
**Related Specs**: [SPEC-0103](0103-spec-chat-and-agents.md), [SPEC-0108](0108-spec-security-and-abuse-protection.md)

## Overview

TripSage renders AI-generated markdown primarily in chat surfaces. This spec standardizes markdown
rendering on Streamdown v2 and defines how AI Elements `Response` integrates with it.

## Canonical renderer

- Canonical renderer component: `src/components/markdown/Markdown.tsx`
- Rules:
  - No other file may import from `streamdown`.
  - All markdown rendering in the app flows through `Markdown`. The
    `src/components/ai-elements/response.tsx` adapter must import `Markdown` and
    must not import `streamdown` directly.

## Streaming vs static behavior

- Streaming surfaces (chat messages, streaming reasoning panes):
  - Use `mode="streaming"`.
  - Enable `parseIncompleteMarkdown`.
  - Use `remend` defaults to heal incomplete markdown while tokens stream in.
  - Show `caret="block"` only when `isAnimating` is true (only for the last assistant message
    during active streaming).
- Static surfaces (non-streaming pages / collapsed panes):
  - Use `mode="static"`.
  - Do not show caret.

## Plugins and assets

Streamdown v2.1+ uses a plugin architecture for code highlighting, diagrams, and math:

- Code highlighting: `@streamdown/code`
- Mermaid diagrams: `@streamdown/mermaid`
- KaTeX math: `@streamdown/math`

The canonical renderer wires these plugins (do not configure them at call sites).

### KaTeX CSS

KaTeX styles must be present globally for math rendering:

- `src/app/layout.tsx` imports `katex/dist/katex.min.css`.

## Security policy

Security profile selection is explicit at the renderer boundary:

- `securityProfile="ai"` (default): treat content as untrusted.
- `securityProfile="user"`: treat content as untrusted.
- `securityProfile="trusted"`: allow raw HTML via `defaultRehypePlugins.raw` with sanitize + harden.

Defaults:

- Untrusted profiles omit raw HTML parsing (no `defaultRehypePlugins.raw`).
- `rehype-harden` enforces safe protocols and applies optional link/image prefix allowlists.
- The canonical renderer disables Streamdown `linkSafety` and enforces safe anchor attributes
  (`rel="noopener noreferrer"`, `target="_blank"`) via a component override.
- Optional prefix allowlists can be extended via:
  - `NEXT_PUBLIC_STREAMDOWN_ALLOWED_LINK_PREFIXES`
  - `NEXT_PUBLIC_STREAMDOWN_ALLOWED_IMAGE_PREFIXES`
- Link and image allowlists are only applied when explicit prefixes are provided; otherwise
  defaults remain unrestricted beyond protocol hardening.

## Testing requirements

- Unit/component tests validate:
  - Raw HTML is not interpreted for untrusted content.
  - `javascript:` links are blocked.
  - `https:` links render with safe `rel` and `target` attributes.
  - KaTeX/code/mermaid blocks do not crash and render the expected Streamdown block wrappers in
    jsdom (smoke/integration level).

## References

- Streamdown docs: <https://streamdown.ai/docs>
- Streamdown security: <https://streamdown.ai/docs/security>
- Streamdown carets: <https://streamdown.ai/docs/carets>
- AI Elements: <https://ai-sdk.dev/elements>
