# ADR-0073: Streamdown v2 canonical markdown renderer (security profiles + plugins)

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2026-01-23
**Category**: frontend
**Domain**: Markdown rendering / AI UI
**Related ADRs**: ADR-0026, ADR-0068
**Related Specs**: SPEC-0103, SPEC-0108, SPEC-0112

## Context

TripSage renders AI-generated markdown in multiple surfaces (chat, AI demo, reasoning panes).

Streamdown v2 adds streaming-specific UX and operational capabilities we want to standardize across
the app:

- Streaming caret indicators.
- Configurable remend (healing for unterminated blocks while streaming).
- Plugin architecture for code/diagrams/math rendering.
- Security guidance via default rehype plugins and `rehype-harden`.

We also need one canonical place to define security defaults for untrusted content and to avoid
ad-hoc renderer usage throughout the UI.

## Decision

- Upgrade `streamdown` from `1.6.11` to `2.1.0`.
- Introduce a single canonical markdown renderer at `src/components/markdown/Markdown.tsx`.
  - This file is the **only** module that imports `streamdown`.
  - It centralizes Streamdown v2 configuration: `mode`, `caret`, `parseIncompleteMarkdown`,
    `remend`, plugin wiring, and security profiles.
- Continue using AI Elements primitives for chat UI, but route markdown rendering through the
  canonical renderer (AI Elements `Response` becomes a small adapter over `Markdown`).
- Adopt Streamdown v2.1+ plugin architecture and wire plugins inside the canonical renderer:
  - `@streamdown/code` (Shiki)
  - `@streamdown/mermaid` (diagrams)
  - `@streamdown/math` (KaTeX)
- Import KaTeX CSS globally in `src/app/layout.tsx` (required by the math plugin).
- Security defaults:
  - Treat AI/user markdown as **untrusted** by default (`securityProfile="ai"` / `"user"`).
  - Disable raw HTML by omitting `defaultRehypePlugins.raw` for untrusted profiles.
  - Always enforce `rehype-harden` protocol restrictions and apply optional link/image prefix
    allowlists (env-extensible).
  - Disable Streamdown's `linkSafety` modal by default and keep anchor semantics; enforce
    `rel="noopener noreferrer"` and `target="_blank"` in the canonical renderer.

## Consequences

### Positive

- One stable integration surface for markdown rendering and security policy.
- Streamdown v2 streaming UX (caret + remend) is consistent across chat-like surfaces.
- Plugin wiring is centralized and can be updated without touching call sites.

### Negative

- Some Streamdown internals (Mermaid, KaTeX CSS) are hard to fully validate in jsdom; tests focus on
  smoke/integration behavior.

### Neutral

- The repo continues to vendor AI Elements components (shadcn-style) rather than importing a
  compiled component package.

## Alternatives Considered

### Upgrade Streamdown without a canonical wrapper

Rejected: configuration (security, CDN, remend/caret) would drift across call sites and create
inconsistent behavior.

### Lock down links with a strict domain allowlist by default

Rejected: the app frequently needs to render external `https://` links (citations, travel sources).
We keep protocol hardening by default and allow optional tightening via env allowlists.

## References

- Streamdown v2 docs: <https://streamdown.ai/docs>
- Streamdown v2 announcement: <https://vercel.com/changelog/streamdown-v2>
- Streamdown security: <https://streamdown.ai/docs/security>
- AI Elements: <https://ai-sdk.dev/elements>
