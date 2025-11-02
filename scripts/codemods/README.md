# Codemods

Expert-crafted, idempotent AST transforms to align the codebase with final patterns (AI SDK v6, Vitest, A11y).

## Prereqs

- Node 18+ and pnpm
- jscodeshift installed globally or run via npx:

```bash
npx jscodeshift -v
```

## Transforms

### ai-route-v6-upgrade

- Enforces `toUIMessageStreamResponse()` in Next.js routes and removes `StreamingTextResponse`.
- Wraps `messages` with `convertToModelMessages(...)` when passing UIMessage[].

Run (dry-run):

```bash
npx jscodeshift -t scripts/codemods/ai-route-v6-upgrade.ts "frontend/src/app/**/route.ts" --parser=ts -d -p
```

Apply:

```bash
npx jscodeshift -t scripts/codemods/ai-route-v6-upgrade.ts "frontend/src/app/**/route.ts" --parser=ts
```

### ai-chat-messages-convert

- Wraps `streamText({ messages })` with `convertToModelMessages(messages)`.

```bash
npx jscodeshift -t scripts/codemods/ai-chat-messages-convert.ts "frontend/src/**/*.{ts,tsx}" --parser=ts -d -p
```

### tests-env-stub

- Replaces `process.env.FOO = 'bar'` in tests with `vi.stubEnv('FOO','bar')` and ensures `vi` import.

```bash
npx jscodeshift -t scripts/codemods/tests-env-stub.ts "frontend/src/**/*.{test.ts,test.tsx}" --parser=ts -d -p
```

### vitest-mock-unify

- Converts `vi.mocked(require('module').Identifier)` → `vi.mocked(Identifier)` with named import.

```bash
npx jscodeshift -t scripts/codemods/vitest-mock-unify.ts "frontend/src/**/*.{test.ts,test.tsx}" --parser=ts -d -p
```

## Workflow

1. Dry-run with `-d -p` and inspect changes
2. Apply on a small subset
3. Apply repo-wide
4. Format/lint/type-check/tests:

```bash
pnpm -C frontend biome:fix && pnpm -C frontend type-check && pnpm -C frontend test:run
```

## Rollback

Each transform should be committed independently. Use `git revert` on the specific codemod commit to roll back.
