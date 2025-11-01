# Prompt: Token Budgeting & Limits (Counting + Clamping)

Executive summary

- Goal: Implement token counting and clamping utilities for AI SDK v6 calls in TS. Prefer provider-reported usage when available; otherwise use `js-tiktoken` for OpenAI models and a conservative heuristic elsewhere. Export utilities and test thoroughly.

Custom persona

- You are “AI SDK Migrator (Tokens)”. You ensure safe budget enforcement and consistent usage reporting.

Docs & references

- AI SDK streaming/generation docs (usage handling)
- OpenAI tokenizer (`js-tiktoken`) package
- exa.get_code_context_exa for usage/structured generation examples; exa.web_search_exa to verify latest model limits; exa.crawling_exa to fetch docs pages
- zen.analyze + zen.thinkdeep to assess accuracy/perf tradeoffs
- zen.consensus for heuristic choices and limit policy (≥ 9.0/10)
- zen.codereview; zen.challenge if assumptions are disputed

Plan (overview)

1) Add `frontend/lib/tokens/budget.ts`:
   - `countTokens(texts: string[], modelHint?: string): number`
   - `clampMaxTokens(messages, desiredMax, modelLimits): { maxTokens, reasons }`
2) Prefer provider usage metadata (when available) in downstream routes; fallback to budget.ts functions only if missing
3) Maintain per-model limit table in TS
4) Vitest tests for counting/clamping edge cases

Checklist (mark off; add notes under each)

- [ ] Draft ADR(s) and Spec(s) (pre-implementation; research + consensus)
  - Notes:
- [ ] Create `frontend/lib/tokens/budget.ts`
  - Notes:
- [ ] Implement `countTokens(texts, modelHint?)`
  - Notes:
- [ ] Implement `clampMaxTokens(messages, desiredMax, modelLimits)`
  - Notes:
- [ ] Prefer provider usage metadata when available; fallback only if missing
  - Notes:
- [ ] Maintain per-model limits table in TS
  - Notes:
- [ ] Vitest tests for counting/clamping edge cases
  - Notes:
- [ ] Finalize ADR(s) and Spec(s) for token budgeting policy
  - Notes:

Working instructions (mandatory)

- Check off tasks only after Vitest, Biome/ESLint/Prettier, and `tsc --noEmit` are clean.
- Add “Notes” for implementation details, issues, and debt; address or log follow-ups.
- Write ADR(s) in `docs/adrs/` for counting/clamping strategy and trade-offs; write Spec(s) in `docs/specs/` detailing interfaces, limits table, and failure modes.

Process flow (required)

1) Research: exa.web_search_exa → exa.crawling_exa → firecrawl_scrape → exa.get_code_context_exa for token counting best practices and model limits.
2) Plan: zen.planner; create atomic tasks.
3) Deep design: zen.thinkdeep + zen.analyze to choose counting strategies and clamp policy.
4) Decide: zen.consensus (≥ 9.0/10) for heuristics/limits table; revise if not met.
5) Draft docs: ADR(s)/Spec(s) defining algorithms and interfaces.
6) Security review: zen.secaudit (no PII in logs; safe defaults).
7) Implement: code/tests; keep Biome/tsc clean.
8) Challenge: zen.challenge on tradeoffs.
9) Review: zen.codereview; fix; rerun checks.
10) Finalize docs: update ADR/Spec with deltas and outcomes.

Legacy mapping (delete later)

- Remove Python-side token estimation logic in `tripsage_core/services/business/chat_service.py` once all routes use TS utilities

Testing requirements

- Unit tests for counting and clamping; ensure deterministic behavior; document heuristic bounds for non-OpenAI models

Final Notes & Next Steps (compile from task notes)

- Summary of changes and decisions:
- Outstanding items / tracked tech debt:
- Follow-up prompts or tasks:

Additional context & assumptions

- Per-model limit table (seed suggestions, adjust per provider docs):
  - OpenAI: `gpt-4o` 128k, `gpt-4o-mini` 128k, `gpt-5` 200k, `gpt-5-mini` 200k
  - Anthropic: `claude-3.5-sonnet` 200k, `claude-3.5-haiku` 200k
  - xAI: adopt provider-documented limits or conservative default (e.g., 128k)
- Heuristic fallback: ~4 chars per token; document this in code comments and tests.
- Handle system/user/assistant roles; count tokens from content fields only; system prompt tokenization included when present.

File & module targets

- `frontend/lib/tokens/budget.ts` (core functions)
- `frontend/lib/tokens/limits.ts` (per-model limits table)

Error scenarios & safeguards

- Unknown model names: fall back to heuristic + conservative maxTokens; log a warning.
- When requested `desiredMax` exceeds model limit, clamp and return reasons array with entries like `['maxTokens_clamped_model_limit']`.
