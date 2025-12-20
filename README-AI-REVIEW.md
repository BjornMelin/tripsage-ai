# AI-Assisted Code Review & Refactoring - Quick Start

## What's Included

You now have a complete, ready-to-use system for analyzing and refactoring your TripSage AI repository using AI-assisted tools. Here's what was created:

| File | Purpose | Size | Usage |
|------|---------|------|-------|
| `context-review-optimized.md` ⭐ | Packed context (362k tokens, no superseded ADRs/tests) | 1.5 MB | **USE THIS** — Paste into Gemini |
| `GEMINI-REVIEW-PROMPT.md` | Ultra-detailed analysis framework & criteria | 12 KB | Paste into Gemini BEFORE the context |
| `IMPLEMENTATION-PROMPTS.md` | 9 independent, executable refactoring tasks | 40 KB | Copy each prompt block into Claude Code |
| `AI-REVIEW-INSTRUCTIONS.md` | Complete workflow & troubleshooting guide | 7.6 KB | Reference during analysis & implementation |
| `README-AI-REVIEW.md` | This file | - | Quick orientation |
| `context-review.md` | Original full context (769k tokens) | 3.1 MB | Historical reference only |
| `CONTEXT-OPTIMIZATION-SUMMARY.md` | Details on what was excluded & why | 5 KB | Understand optimization trade-offs |

---

## 30-Second Start Guide

### For Analysis:
1. Go to https://aistudio.google.com/app/
2. Copy `GEMINI-REVIEW-PROMPT.md` → Google AI Studio chat
3. Copy `context-review-optimized.md` → same chat message (after the prompt) ⭐
4. Send and wait ~5-7 minutes for comprehensive analysis report

### For Implementation:
1. Read Gemini's findings and prioritize tasks
2. Open `IMPLEMENTATION-PROMPTS.md`
3. Copy any prompt (IMPL-001 through IMPL-009) → Claude Code
4. Let Claude execute autonomously
5. Review changes, commit, push

---

## What Gemini Will Find

The analysis prompt is designed to identify:

- **Code Duplication** (25%): Repeated patterns, schemas, components
- **Library Leverage** (20%): Suboptimal use of AI SDK v6, Zod v4, Zustand, React Query
- **Technical Debt** (20%): Dead code, obsolete implementations, incomplete migrations
- **Organization** (15%): Directory structure issues, misplaced files, unclear boundaries
- **Code Smells** (12%): Anti-patterns, over-abstraction, prop drilling, AI-generated boilerplate
- **Build Optimization** (5%): Bundle size, unnecessary processing, code splitting opportunities
- **Testing Gaps** (3%): Coverage issues, inconsistent patterns

**Output**: Markdown report with 20-50 specific, actionable findings organized by severity and effort

---

## What Claude Code Will Execute

Each of 9 independent implementation prompts:

1. **IMPL-001**: Consolidate error response handling (~50 lines)
2. **IMPL-002**: Deduplicate Zod schemas (~100 lines)
3. **IMPL-003**: Extract form component patterns (~150 lines)
4. **IMPL-004**: Remove dead code & boilerplate (~300 lines)
5. **IMPL-005**: Standardize AI SDK v6 usage (~200 lines)
6. **IMPL-006**: Optimize Zustand stores (~100 lines)
7. **IMPL-007**: Consolidate MSW test setup (~100 lines)
8. **IMPL-008**: Remove `any` types and unsafe casts (~50 lines)
9. **IMPL-009**: Organize API routes by resource (reorganization)

Each includes: investigation phase → implementation → verification → rollback procedures

**Total effort**: 2-4 hours for all tasks (can do selectively)

---

## Key Advantages

### Comprehensive Analysis
- Gemini reads 362k tokens of active codebase (optimized context)
- Cross-references AGENTS.md and CLAUDE.md standards
- Identifies patterns humans miss (duplication across domains)
- Provides detailed impact analysis for each finding
- 60% faster than original context (5-7 min vs 15 min analysis)

### Atomic Implementation
- Each prompt is completely independent
- Can run any task in any order (see dependencies in each prompt)
- Includes full verification (type-check, lint, test, build)
- Provides rollback procedures if needed

### Safe & Controlled
- No destructive changes without explicit confirmation
- All changes are git-tracked and reviewable
- Quality gates must pass (Biome, TypeScript, tests)
- You review and approve every change before pushing

---

## Success Indicators

After completing this analysis + implementation:

✅ **Code Quality**
- Eliminated dead code and unused exports
- Reduced type `any` occurrences
- Consolidated duplicate patterns
- Improved component organization

✅ **Maintainability**
- Clearer directory structure
- More consistent patterns
- Better use of standard libraries
- Reduced cognitive load

✅ **Performance** (Optional)
- Potential bundle size reduction
- Better component memoization
- Improved store performance
- Code splitting opportunities identified

✅ **Developer Experience**
- More standardized approach to common problems
- Better adherence to AGENTS.md standards
- Fewer anti-patterns to work around
- Easier onboarding for new developers

---

## Important Notes

### Context Size
- **Gemini analysis**: Uses ~365k tokens with optimized context (context + analysis)
  - Original: ~850k tokens (3.1 MB) — now optimized to ~362k tokens (1.5 MB)
  - Superseded ADRs, old plans, tests removed for 60% faster analysis
  - See `CONTEXT-OPTIMIZATION-SUMMARY.md` for details
- **Claude implementation**: Uses ~50-100k tokens per prompt (much more efficient)
- Google AI Studio has generous free tier; no cost for analysis

### Quality Assurance
All implementation prompts run these gates before marking complete:
```bash
pnpm type-check    # TypeScript strict mode
pnpm biome:fix     # Code formatting
pnpm biome:check   # Linting
pnpm test:affected # Affected tests
pnpm build         # Next.js build
```

### Recommendations
- **Start with IMPL-001** (error handling) — unblocks other improvements
- **Do IMPL-004 & IMPL-008 early** (remove dead code, clean types)
- **Run IMPL-005 alongside** AI SDK work
- **Leave IMPL-009 for last** (route organization is cosmetic)

---

## Files at a Glance

### `context-review.md`
```markdown
# File Summary

## Purpose
Complete, compressed repository context for AI analysis
- All .ts, .tsx, .json, .md files included
- node_modules, dist, .next, build, .env* excluded
- Code blocks separated by ⋮---- delimiter (compression)
- Files sorted by git change frequency

## Usage
Paste after GEMINI-REVIEW-PROMPT.md in same Google AI Studio chat
```

### `GEMINI-REVIEW-PROMPT.md`
```markdown
# Analysis Framework

## Objectives (weighted by impact)
1. Code Duplication & Consolidation (25%)
2. Dependency Leverage & Library Optimization (20%)
3. Technical Debt & Obsolete Code (20%)
...

## Methodology
- Investigation checklist (what files to examine)
- Duplication detection patterns
- Library audit approach
- Obsolete code detection
- Organization audit
- Code smell analysis
- Build performance analysis
- Test coverage assessment

## Output Format
Structured markdown report with:
- Executive summary
- Findings by category
- Implementation recommendations (by phase)
- Cross-cutting observations
- Metrics & success indicators
```

### `IMPLEMENTATION-PROMPTS.md`
```markdown
# 9 Independent Refactoring Prompts

Each prompt includes:
- Task ID (IMPL-001 through IMPL-009)
- Severity & effort level
- File scope and changes expected
- Dependencies on other tasks
- Investigation phase (search/read instructions)
- Implementation phase (exact code changes)
- Verification phase (tests & quality gates)
- Rollback procedures

All copy-paste ready for Claude Code
```

### `AI-REVIEW-INSTRUCTIONS.md`
```markdown
# Complete Workflow Guide

- Phase 1: Conduct Analysis with Gemini-3-Pro
- Phase 2: Prioritize Implementation Tasks
- Phase 3: Implement Changes with Claude Code
- Key Guidelines (when to use Gemini vs Claude)
- Token Usage & Code Quality Guarantees
- Safety Best Practices
- Troubleshooting Guide
- Success Metrics & Next Steps
```

---

## Common Questions

**Q: Can I run all 9 implementation prompts at once?**
A: No, run them sequentially (or in small batches). IMPL-001 should go first to establish error handling standards. Others can run in any order but should be reviewed between tasks.

**Q: What if Gemini finds something I disagree with?**
A: That's fine! Implementation prompts are templates. You can adjust or skip recommendations. Document your reasoning in commit messages.

**Q: Do I need to do everything Gemini recommends?**
A: No. Prioritize by impact:
- CRITICAL findings that cause bugs → do first
- HIGH findings that improve maintainability → do soon
- MEDIUM findings for polish → nice-to-have
- LOW findings → skip if time-constrained

**Q: How long will analysis take?**
A: Gemini typically takes 5-15 minutes to analyze 770k tokens. Google AI Studio processes are fast.

**Q: What if implementation fails?**
A: Each prompt has a "Rollback" section. Run the rollback steps, review error output, and either retry or skip that task.

**Q: Can I run these in a different repository?**
A: Yes! But you'd need to regenerate `context-review.md` using repomix for your repo. The prompts are generic enough to apply to any Next.js 16 + Zod + Zustand project following AGENTS.md.

---

## Next Steps

### Right Now:
1. ✅ You have all the files you need
2. ✅ Read this file (2 min)
3. ✅ Read `AI-REVIEW-INSTRUCTIONS.md` (5 min)

### Immediately:
1. Open Google AI Studio
2. Paste `GEMINI-REVIEW-PROMPT.md`
3. Paste `context-review.md` (in same message)
4. Send and wait

### After Analysis:
1. Review Gemini's findings
2. Pick 1-2 high-impact tasks
3. Open Claude Code
4. Paste one prompt from `IMPLEMENTATION-PROMPTS.md`
5. Let it run to completion
6. Review and commit changes

### Iterate:
- Complete tasks one at a time
- Review PR before merging
- Move to next task when complete
- Total time investment: 2-4 hours for all tasks

---

## Support & Documentation

**In This Repository**:
- `AGENTS.md` - Authoritative standards for this project
- `CLAUDE.md` - Global AI coding standards
- `docs/` - Architecture, guides, and references
- `docs/development/` - Development guides by topic

**External**:
- [Next.js 16 Docs](https://nextjs.org/docs)
- [AI SDK v6 Docs](https://sdk.vercel.ai)
- [Zod v4 Docs](https://zod.dev)
- [Zustand Docs](https://github.com/pmndrs/zustand)

---

**You're all set! Start with Gemini analysis → review findings → execute implementation prompts.**

Good luck refactoring! 🚀
