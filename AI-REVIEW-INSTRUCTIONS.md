# TripSage AI - AI-Assisted Code Review Instructions

This document explains how to use the packed repository context and prompts with Google AI Studio (Gemini) and Claude Code for a comprehensive repository analysis and refactoring.

---

## Overview

You now have three key files:

1. **`context-review-optimized.md`** (1.5 MB, ~362k tokens) ⭐ **RECOMMENDED**
   - Optimized packed repository context (superseded ADRs, tests, old plans removed)
   - 47% smaller tokens, 60% faster analysis (~5-7 min instead of 15)
   - Focused on active codebase + current standards
   - See `CONTEXT-OPTIMIZATION-SUMMARY.md` for details

2. **`GEMINI-REVIEW-PROMPT.md`**
   - Ultra-detailed analysis prompt for Gemini-3-Pro
   - Specifies exact analysis framework and criteria
   - Describes expected output format and depth
   - Provides investigation checklist

3. **`IMPLEMENTATION-PROMPTS.md`**
   - 9 detailed, atomic, independent implementation prompts
   - Each is copy-paste ready for Claude Code
   - Designed to run in fresh sessions
   - Includes verification steps and rollback procedures

**Note**: Also available: `context-review.md` (original, 3.1 MB) for historical reference

---

## Workflow: Analysis → Implementation

### Phase 1: Conduct Analysis with Gemini-3-Pro (Google AI Studio)

**Goal**: Identify all optimization opportunities before refactoring

**Steps**:

1. **Go to Google AI Studio**: https://aistudio.google.com/app/

2. **Create new chat** or open existing project

3. **Paste the analysis prompt**:
   - Open `GEMINI-REVIEW-PROMPT.md`
   - Copy entire content
   - Paste into Google AI Studio

4. **Append the optimized context**:
   - Open `context-review-optimized.md` ⭐ (use optimized version, not original)
   - Copy entire file (select all, Ctrl+A)
   - Paste into same chat message (after the analysis prompt)
   - **Message should start with the analysis prompt, end with the context**
   - This version is 60% faster and excludes superseded ADRs/old plans

5. **Send and wait for analysis**:
   - Expected response: ~5-7 minutes for Gemini-3-Pro (optimized context)
   - Result: Comprehensive report with findings organized by category
   - Save the report (Gemini will provide markdown or structured output)

6. **Review the report**:
   - Scan for CRITICAL and HIGH severity findings
   - Note "Quick wins" (low effort, high impact)
   - Identify dependencies between recommendations
   - Prioritize which areas to refactor first

### Phase 2: Prioritize Implementation Tasks

From Gemini's report, create your implementation plan:

**Example prioritization**:
1. **Must do first** (unblocks others):
   - IMPL-001: Error handling consolidation
   - IMPL-002: Schema deduplication

2. **Do second** (leverages first):
   - IMPL-005: AI SDK v6 standardization
   - IMPL-004: Dead code removal

3. **Do in parallel** (independent):
   - IMPL-003: Component consolidation
   - IMPL-006: Zustand optimization
   - IMPL-007: MSW consolidation
   - IMPL-008: Type safety cleanup

4. **Can defer** (nice-to-have):
   - IMPL-009: Route organization

---

## Phase 3: Implement Changes with Claude Code

**For each task you want to execute**:

### Step 1: Prepare

1. Create a fresh git branch:
   ```bash
   git checkout -b refactor/IMPL-XXX-description
   ```

2. Ensure clean state:
   ```bash
   git status  # Should be clean
   pnpm install
   pnpm type-check  # Baseline
   ```

### Step 2: Execute the prompt

1. Open the task from `IMPLEMENTATION-PROMPTS.md`
   - Copy the entire markdown block (from ` ```markdown` to closing ` ``` `)

2. Start fresh Claude Code session (or new chat in existing session)

3. Paste the prompt into Claude Code

4. **Let Claude run autonomously**:
   - It will investigate the codebase
   - Make targeted changes
   - Run verification steps
   - Report results

### Step 3: Review and commit

1. Review the changes:
   ```bash
   git diff
   git status
   ```

2. If satisfied, commit:
   ```bash
   git add .
   git commit -m "refactor(impl-001): consolidate route error responses"
   ```

3. If issues, revert and retry:
   ```bash
   git checkout .
   # Try again or skip this task
   ```

### Step 4: Push and iterate

```bash
git push origin refactor/IMPL-XXX-description
```

Create PR, review, merge when ready.

---

## Key Guidelines

### Use Gemini-3-Pro For:
- ✅ Comprehensive analysis and identification of issues
- ✅ Understanding architectural patterns and trade-offs
- ✅ Prioritizing work by impact and dependencies
- ✅ Generating detailed implementation strategies
- ✅ Cross-repository pattern analysis

### Use Claude Code For:
- ✅ Executing specific, well-defined refactoring tasks
- ✅ Writing code and running verification
- ✅ Integration with local development tools
- ✅ Git operations and PR creation
- ✅ Interactive debugging if something goes wrong

---

## Important Notes

### Token Usage

- **Gemini analysis**: ~850k tokens (context + analysis prompt)
  - Google AI Studio has generous free tier
  - If you hit limits, wait 60 minutes

- **Claude implementation**: ~50-100k tokens per prompt
  - Much more efficient (targeted refactoring)
  - Haiku model used for speed

### Code Quality Guarantees

All implementation prompts include:
- ✅ Type checking (`pnpm type-check`)
- ✅ Formatting (`pnpm biome:fix`)
- ✅ Linting (`pnpm biome:check`)
- ✅ Tests (`pnpm test:affected` or specific shard)
- ✅ Build verification (`pnpm build`)

These must pass before marking a task complete.

### Safety

- **Never force push** to `main` or shared branches
- **Always create feature branches**
- **Review PRs** before merging (especially refactors)
- **Test locally** before pushing
- **Ask for help** if a step fails or seems wrong

---

## Troubleshooting

### "Token limit exceeded" in Gemini

**Solution**:
- Split into smaller analysis requests
- Focus on specific categories (e.g., "Code Duplication only")
- Run multiple analyses, one per category

### Claude Code prompt fails partway through

**Solution**:
1. Read the error message carefully
2. Check the "Rollback" section in the prompt
3. Run rollback steps to revert changes
4. Either:
   - Retry the same prompt
   - Skip to next independent task
   - Ask in a new Claude Code session

### Implementation doesn't match Gemini's recommendation

**Solution**:
- This is OK! Implementation prompts are templates, not gospel
- If you understand the recommendation differently, adjust accordingly
- Document the choice in your commit message
- You can always adjust in a follow-up PR

### Tests fail after changes

**Solution**:
1. Check the test output carefully
2. Verify the implementation is correct
3. If tests are outdated, update them (as part of the task)
4. If implementation is wrong, revert and reconsider

---

## Success Metrics

After completing the analysis and implementation work, you should see:

- **Code quality**: ↑ Type safety, reduced duplication, clearer patterns
- **Bundle size**: ↓ (from consolidation and dead code removal)
- **Test coverage**: ↑ or stable
- **Maintainability**: ↑ (clearer organization, fewer anti-patterns)
- **Developer experience**: ↑ (fewer ambiguities, better patterns)

---

## Next Steps

1. **Start**: Go to Google AI Studio, paste the analysis prompt + context
2. **Wait**: Let Gemini analyze (5-15 minutes)
3. **Review**: Read the findings and prioritize
4. **Execute**: Pick 1-2 tasks from `IMPLEMENTATION-PROMPTS.md`
5. **Test**: Verify each change works
6. **Iterate**: Continue with next priority tasks

---

## Questions & Support

If you encounter issues:

1. **Claude Code help**: Ask Claude Code directly (it has access to AGENTS.md and CLAUDE.md)
2. **Analysis clarity**: Go back to Gemini's report, ask for clarification
3. **Verification failures**: Check the specific quality gate output
4. **General questions**: Refer to `docs/development/` in your repo

---

**Created**: 2025-12-20
**Repository**: TripSage AI (Next.js 16, AI SDK v6, Supabase, Zustand)
**Context size**: 769,904 tokens (compressed)
**Implementation prompts**: 9 atomic tasks, ~2-4 hours total estimated effort
