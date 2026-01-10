# TripSage AI — Current State Audit (v1.0.0 Release Work)

Last updated (UTC): 2025-12-31T21:32:36Z

## Environment

- Repo root: `/home/bjorn/repos/agents/tripsage-ai`
- Shell: `zsh`

## Repository Snapshot

### `git status --porcelain=v1 -b`

```text
## feat/ship-v1-sprint...origin/feat/ship-v1-sprint
?? docs/SESSION_PROTOCOL.md
?? docs/TOOLS.md
?? docs/agents/
?? docs/release/
?? docs/tasks/
```

### `package.json` name/version

```text
tripsage-ai-frontend 1.22.5
```

## Toolchain Versions

### `node --version`

```text
v24.11.0
```

### `pnpm --version`

```text
10.26.2
```

### `python --version`

```text
zsh:1: command not found: python
exit_code=127
```

### `python3 --version`

```text
Python 3.12.3
```

### `uv --version`

```text
uv 0.9.8
```

## Baseline Commands (verbatim output)

### `pnpm install`

```text
Lockfile is up to date, resolution step is skipped
Already up to date


> tripsage-ai-frontend@1.22.5 prepare /home/bjorn/repos/agents/tripsage-ai
> simple-git-hooks

[INFO] Successfully set the pre-commit with command: pnpm check:no-secrets:staged
[INFO] Successfully set all git hooks
Done in 1.2s using pnpm v10.26.2
```

### `pnpm lint`

```text
undefined
 ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL  Command "lint" not found
exit_code=254
```

### Lint equivalent used: `pnpm biome:check`

```text

> tripsage-ai-frontend@1.22.5 biome:check /home/bjorn/repos/agents/tripsage-ai
> biome check ./src ./e2e ./scripts

Checked 1068 files in 440ms. No fixes applied.
```

### `pnpm type-check`

```text

> tripsage-ai-frontend@1.22.5 type-check /home/bjorn/repos/agents/tripsage-ai
> tsc --noEmit

```

### `pnpm test` (run with `CI=1`)

```text

> tripsage-ai-frontend@1.22.5 test /home/bjorn/repos/agents/tripsage-ai
> vitest run


 RUN  v4.0.16 /home/bjorn/repos/agents/tripsage-ai

························································································································stderr | src/app/api/chat/stream/__tests__/route.adapter.test.ts > /api/chat/stream route adapter > parses body and forwards ip/messages to handleChatStream
Possible misconfiguration of Vercel BotId. 
Ensure that the client-side protection is properly configured for 'POST <your protected endpoint>'.
Add the following item to your BotId client side protection:
{
  path: '<your protected endpoint>',
  method: 'POST',
}
More info at https://vercel.com/docs/botid/get-started#add-client-side-protection
[Dev Only] Without setting the developmentOptions.bypass value, the bot protection will return HUMAN.

·······················································································································································································---··············································································································································································································································································································································································································································································································································································································································································································································································································································································································································································································································································································································································································································································································································································································································································································································································································································································································································································································stderr | src/features/profile/components/__tests__/profile-smoke.test.tsx > Profile Components Smoke Tests > renders PersonalInfoSection without crashing
Cannot update a component (`Controller`) while rendering a different component (`Controller`). To locate the bad setState() call inside `Controller`, follow the stack trace as described in https://react.dev/link/setstate-in-render

···············································································································stderr | src/features/profile/components/__tests__/account-settings-section.test.tsx > AccountSettingsSection > renders email settings with current email
Cannot update a component (`AccountSettingsSection`) while rendering a different component (`Controller`). To locate the bad setState() call inside `Controller`, follow the stack trace as described in https://react.dev/link/setstate-in-render

··························································Not implemented: navigation to another Document
································································································································································································································································································stderr | src/components/providers/__tests__/query-error-boundary.test.tsx > QueryErrorBoundary > records telemetry with retry metadata when an error is thrown
ApiError: boom
    at /home/bjorn/repos/agents/tripsage-ai/src/components/providers/__tests__/query-error-boundary.test.tsx:46:35
    at file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:145:11
    at file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:915:26
    at file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:1243:20
    at new Promise (<anonymous>)
    at runWithTimeout (file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:1209:10)
    at file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:1653:37
    at Traces.$ (file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/vitest@4.0.16_@opentelemetry+api@1.9.0_@types+node@25.0.3_@vitest+ui@4.0.16_jiti@2.6.1__cfd214fd961dc4d2283112102259599e/node_modules/vitest/dist/chunks/traces.U4xDYhzZ.js:115:27)
    at trace (file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/vitest@4.0.16_@opentelemetry+api@1.9.0_@types+node@25.0.3_@vitest+ui@4.0.16_jiti@2.6.1__cfd214fd961dc4d2283112102259599e/node_modules/vitest/dist/chunks/test.B8ej_ZHS.js:239:21)
    at runTest (file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:1653:12) {
  [stack]: [Getter/Setter],
  [message]: 'boom',
  name: 'ApiError',
  status: 503,
  code: 'SERVER_ERROR',
  data: undefined,
  endpoint: undefined,
  validationErrors: undefined,
  fieldErrors: undefined,
  timestamp: '2025-12-31T20:27:01.342Z',
  [isClientError]: [Getter],
  [isServerError]: [Getter],
  [shouldRetry]: [Getter],
  [userMessage]: [Getter]
}

The above error occurred in the <ThrowingComponent> component.

React will try to recreate this component tree from scratch using the error boundary you provided, l.


stderr | src/components/providers/__tests__/query-error-boundary.test.tsx > QueryErrorBoundary > invokes injected onError asynchronously with meta
ApiError: auth
    at /home/bjorn/repos/agents/tripsage-ai/src/components/providers/__tests__/query-error-boundary.test.tsx:69:35
    at file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:145:11
    at file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:915:26
    at file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:1243:20
    at new Promise (<anonymous>)
    at runWithTimeout (file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:1209:10)
    at file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:1653:37
    at Traces.$ (file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/vitest@4.0.16_@opentelemetry+api@1.9.0_@types+node@25.0.3_@vitest+ui@4.0.16_jiti@2.6.1__cfd214fd961dc4d2283112102259599e/node_modules/vitest/dist/chunks/traces.U4xDYhzZ.js:115:27)
    at trace (file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/vitest@4.0.16_@opentelemetry+api@1.9.0_@types+node@25.0.3_@vitest+ui@4.0.16_jiti@2.6.1__cfd214fd961dc4d2283112102259599e/node_modules/vitest/dist/chunks/test.B8ej_ZHS.js:239:21)
    at runTest (file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:1653:12) {
  [stack]: [Getter/Setter],
  [message]: 'auth',
  name: 'ApiError',
  status: 401,
  code: 'UNAUTHORIZED',
  data: undefined,
  endpoint: undefined,
  validationErrors: undefined,
  fieldErrors: undefined,
  timestamp: '2025-12-31T20:27:01.511Z',
  [isClientError]: [Getter],
  [isServerError]: [Getter],
  [shouldRetry]: [Getter],
  [userMessage]: [Getter]
}

The above error occurred in the <ThrowingComponent> component.

React will try to recreate this component tree from scratch using the error boundary you provided, l.


stderr | src/components/providers/__tests__/query-error-boundary.test.tsx > QueryErrorBoundary > invokes onOperationalAlert before onError with metadata
ApiError: server
    at /home/bjorn/repos/agents/tripsage-ai/src/components/providers/__tests__/query-error-boundary.test.tsx:94:35
    at file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:145:11
    at file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:915:26
    at file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:1243:20
    at new Promise (<anonymous>)
    at runWithTimeout (file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:1209:10)
    at file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:1653:37
    at Traces.$ (file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/vitest@4.0.16_@opentelemetry+api@1.9.0_@types+node@25.0.3_@vitest+ui@4.0.16_jiti@2.6.1__cfd214fd961dc4d2283112102259599e/node_modules/vitest/dist/chunks/traces.U4xDYhzZ.js:115:27)
    at trace (file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/vitest@4.0.16_@opentelemetry+api@1.9.0_@types+node@25.0.3_@vitest+ui@4.0.16_jiti@2.6.1__cfd214fd961dc4d2283112102259599e/node_modules/vitest/dist/chunks/test.B8ej_ZHS.js:239:21)
    at runTest (file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:1653:12) {
  [stack]: [Getter/Setter],
  [message]: 'server',
  name: 'ApiError',
  status: 500,
  code: 'SERVER_ERROR',
  data: undefined,
  endpoint: undefined,
  validationErrors: undefined,
  fieldErrors: undefined,
  timestamp: '2025-12-31T20:27:01.549Z',
  [isClientError]: [Getter],
  [isServerError]: [Getter],
  [shouldRetry]: [Getter],
  [userMessage]: [Getter]
}

The above error occurred in the <ThrowingComponent> component.

React will try to recreate this component tree from scratch using the error boundary you provided, l.


stderr | src/components/providers/__tests__/query-error-boundary.test.tsx > QueryErrorBoundary > disables retry UI for non-retryable errors
ApiError: denied
    at /home/bjorn/repos/agents/tripsage-ai/src/components/providers/__tests__/query-error-boundary.test.tsx:120:35
    at file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:145:11
    at file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:915:26
    at file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:1243:20
    at new Promise (<anonymous>)
    at runWithTimeout (file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:1209:10)
    at file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:1653:37
    at Traces.$ (file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/vitest@4.0.16_@opentelemetry+api@1.9.0_@types+node@25.0.3_@vitest+ui@4.0.16_jiti@2.6.1__cfd214fd961dc4d2283112102259599e/node_modules/vitest/dist/chunks/traces.U4xDYhzZ.js:115:27)
    at trace (file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/vitest@4.0.16_@opentelemetry+api@1.9.0_@types+node@25.0.3_@vitest+ui@4.0.16_jiti@2.6.1__cfd214fd961dc4d2283112102259599e/node_modules/vitest/dist/chunks/test.B8ej_ZHS.js:239:21)
    at runTest (file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:1653:12) {
  [stack]: [Getter/Setter],
  [message]: 'denied',
  name: 'ApiError',
  status: 403,
  code: 'FORBIDDEN',
  data: undefined,
  endpoint: undefined,
  validationErrors: undefined,
  fieldErrors: undefined,
  timestamp: '2025-12-31T20:27:01.575Z',
  [isClientError]: [Getter],
  [isServerError]: [Getter],
  [shouldRetry]: [Getter],
  [userMessage]: [Getter]
}

The above error occurred in the <ThrowingComponent> component.

React will try to recreate this component tree from scratch using the error boundary you provided, l.


stderr | src/components/providers/__tests__/query-error-boundary.test.tsx > QueryErrorBoundary > resets the boundary when retry is invoked
ApiError: server
    at /home/bjorn/repos/agents/tripsage-ai/src/components/providers/__tests__/query-error-boundary.test.tsx:133:35
    at file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:145:11
    at file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:915:26
    at file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:1243:20
    at new Promise (<anonymous>)
    at runWithTimeout (file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:1209:10)
    at file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:1653:37
    at Traces.$ (file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/vitest@4.0.16_@opentelemetry+api@1.9.0_@types+node@25.0.3_@vitest+ui@4.0.16_jiti@2.6.1__cfd214fd961dc4d2283112102259599e/node_modules/vitest/dist/chunks/traces.U4xDYhzZ.js:115:27)
    at trace (file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/vitest@4.0.16_@opentelemetry+api@1.9.0_@types+node@25.0.3_@vitest+ui@4.0.16_jiti@2.6.1__cfd214fd961dc4d2283112102259599e/node_modules/vitest/dist/chunks/test.B8ej_ZHS.js:239:21)
    at runTest (file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:1653:12) {
  [stack]: [Getter/Setter],
  [message]: 'server',
  name: 'ApiError',
  status: 500,
  code: 'SERVER_ERROR',
  data: undefined,
  endpoint: undefined,
  validationErrors: undefined,
  fieldErrors: undefined,
  timestamp: '2025-12-31T20:27:01.597Z',
  [isClientError]: [Getter],
  [isServerError]: [Getter],
  [shouldRetry]: [Getter],
  [userMessage]: [Getter]
}

The above error occurred in the <ThrowingComponent> component.

React will try to recreate this component tree from scratch using the error boundary you provided, l.


····stderr | src/components/providers/__tests__/query-error-boundary.test.tsx > QueryErrorBoundary > resets the boundary when retry is invoked
ApiError: server
    at /home/bjorn/repos/agents/tripsage-ai/src/components/providers/__tests__/query-error-boundary.test.tsx:133:35
    at file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:145:11
    at file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:915:26
    at file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:1243:20
    at new Promise (<anonymous>)
    at runWithTimeout (file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:1209:10)
    at file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:1653:37
    at Traces.$ (file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/vitest@4.0.16_@opentelemetry+api@1.9.0_@types+node@25.0.3_@vitest+ui@4.0.16_jiti@2.6.1__cfd214fd961dc4d2283112102259599e/node_modules/vitest/dist/chunks/traces.U4xDYhzZ.js:115:27)
    at trace (file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/vitest@4.0.16_@opentelemetry+api@1.9.0_@types+node@25.0.3_@vitest+ui@4.0.16_jiti@2.6.1__cfd214fd961dc4d2283112102259599e/node_modules/vitest/dist/chunks/test.B8ej_ZHS.js:239:21)
    at runTest (file:///home/bjorn/repos/agents/tripsage-ai/node_modules/.pnpm/@vitest+runner@4.0.16/node_modules/@vitest/runner/dist/index.js:1653:12) {
  [stack]: [Getter/Setter],
  [message]: 'server',
  name: 'ApiError',
  status: 500,
  code: 'SERVER_ERROR',
  data: undefined,
  endpoint: undefined,
  validationErrors: undefined,
  fieldErrors: undefined,
  timestamp: '2025-12-31T20:27:01.597Z',
  [isClientError]: [Getter],
  [isServerError]: [Getter],
  [shouldRetry]: [Getter],
  [userMessage]: [Getter]
}

The above error occurred in the <ThrowingComponent> component.

React will try to recreate this component tree from scratch using the error boundary you provided, l.


·······································································································································································································································································································································································································································································································································································································································································································································································································································································································

 Test Files  337 passed | 2 skipped (339)
      Tests  3377 passed | 3 skipped (3380)
   Start at  14:25:57
   Duration  97.54s (transform 16.24s, setup 66.27s, import 83.91s, tests 88.61s, environment 43.20s)

```

### `pnpm build`

```text

> tripsage-ai-frontend@1.22.5 build /home/bjorn/repos/agents/tripsage-ai
> next build

▲ Next.js 16.1.1 (Turbopack, Cache Components)
- Environments: .env.local
- Experiments (use with caution):
  · optimizePackageImports

  Creating an optimized production build ...
✓ Compiled successfully in 15.6s
  Running TypeScript ...
  Collecting page data using 23 workers ...
  Generating static pages using 23 workers (0/98) ...
  Generating static pages using 23 workers (24/98) 
  Generating static pages using 23 workers (48/98) 
  Generating static pages using 23 workers (73/98) 
✓ Generating static pages using 23 workers (98/98) in 891.7ms
  Finalizing page optimization ...

Route (app)
┌ ○ /
├ ○ /_not-found
├ ○ /ai-demo
├ ƒ /api/accommodations/personalize
├ ƒ /api/accommodations/popular-destinations
├ ƒ /api/accommodations/search
├ ƒ /api/activities/[id]
├ ƒ /api/activities/search
├ ƒ /api/agents/accommodations
├ ƒ /api/agents/budget
├ ƒ /api/agents/destinations
├ ƒ /api/agents/flights
├ ƒ /api/agents/itineraries
├ ƒ /api/agents/memory
├ ƒ /api/agents/router
├ ƒ /api/ai/stream
├ ƒ /api/attachments/files
├ ƒ /api/auth/login
├ ƒ /api/auth/mfa/backup/regenerate
├ ƒ /api/auth/mfa/backup/verify
├ ƒ /api/auth/mfa/challenge
├ ƒ /api/auth/mfa/factors/list
├ ƒ /api/auth/mfa/sessions/revoke
├ ƒ /api/auth/mfa/setup
├ ƒ /api/auth/mfa/verify
├ ƒ /api/calendar/events
├ ƒ /api/calendar/freebusy
├ ƒ /api/calendar/ics/export
├ ƒ /api/calendar/ics/import
├ ƒ /api/calendar/status
├ ƒ /api/chat/attachments
├ ƒ /api/chat/sessions
├ ƒ /api/chat/sessions/[id]
├ ƒ /api/chat/sessions/[id]/messages
├ ƒ /api/chat/stream
├ ƒ /api/config/agents/[agentType]
├ ƒ /api/config/agents/[agentType]/rollback/[versionId]
├ ƒ /api/config/agents/[agentType]/versions
├ ƒ /api/dashboard
├ ƒ /api/embeddings
├ ƒ /api/flights/popular-destinations
├ ƒ /api/flights/popular-routes
├ ƒ /api/flights/search
├ ƒ /api/geocode
├ ƒ /api/hooks/cache
├ ƒ /api/hooks/files
├ ƒ /api/hooks/trips
├ ƒ /api/itineraries
├ ƒ /api/jobs/memory-sync
├ ƒ /api/jobs/notify-collaborators
├ ƒ /api/keys
├ ƒ /api/keys/[service]
├ ƒ /api/keys/validate
├ ƒ /api/memory/[intent]
├ ƒ /api/memory/[intent]/[userId]
├ ƒ /api/places/details/[id]
├ ƒ /api/places/nearby
├ ƒ /api/places/photo
├ ƒ /api/places/search
├ ƒ /api/rag/index
├ ƒ /api/rag/search
├ ƒ /api/route-matrix
├ ƒ /api/routes
├ ƒ /api/security/events
├ ƒ /api/security/metrics
├ ƒ /api/security/sessions
├ ƒ /api/security/sessions/[sessionId]
├ ƒ /api/telemetry/activities
├ ƒ /api/telemetry/ai-demo
├ ƒ /api/timezone
├ ƒ /api/trips
├ ƒ /api/trips/[id]
├ ƒ /api/trips/[id]/collaborators
├ ƒ /api/trips/[id]/collaborators/[userId]
├ ƒ /api/trips/suggestions
├ ƒ /api/user-settings
├ ƒ /auth/callback
├ ƒ /auth/confirm
├ ƒ /auth/delete
├ ƒ /auth/email/resend
├ ƒ /auth/email/verify
├ ƒ /auth/logout
├ ƒ /auth/me
├ ƒ /auth/password/change
├ ƒ /auth/password/reset
├ ƒ /auth/password/reset-request
├ ƒ /auth/register
├ ◐ /chat
├ ◐ /dashboard
├ ◐ /dashboard/admin/configuration
├ ◐ /dashboard/agent-status
├ ◐ /dashboard/calendar
├ ◐ /dashboard/demo/realtime
├ ◐ /dashboard/profile
├ ◐ /dashboard/search
├ ◐ /dashboard/search/activities
├ ◐ /dashboard/search/destinations
├ ◐ /dashboard/search/flights
├ ◐ /dashboard/search/flights/results
├ ◐ /dashboard/search/hotels
├ ◐ /dashboard/search/unified
├ ◐ /dashboard/security
├ ◐ /dashboard/settings
├ ◐ /dashboard/settings/api-keys
├ ◐ /dashboard/trips
├ ◐ /dashboard/trips/[id]
│ └ /dashboard/trips/[id]
├ ◐ /dashboard/trips/[id]/collaborate
│ └ /dashboard/trips/[id]/collaborate
├ ◐ /login
├ ◐ /register
└ ◐ /reset-password


ƒ Proxy (Middleware)

○  (Static)             prerendered as static content
◐  (Partial Prerender)  prerendered as static HTML with dynamic server-streamed content
ƒ  (Dynamic)            server-rendered on demand

```

## Additional Guardrail Checks (verbatim output)

### `pnpm boundary:check`

```text
> tripsage-ai-frontend@1.22.5 boundary:check /home/bjorn/repos/agents/tripsage-ai
> node scripts/check-boundaries.mjs

🔍 Scanning for boundary violations...


============================================================
📊 Summary
============================================================
Files scanned: 528
Hard violations: 0
Allowlisted domain violations: 0
Potential issues (warnings): 0
============================================================

✅ No boundary violations detected.
```

### `pnpm ai-tools:check`

```text
> tripsage-ai-frontend@1.22.5 ai-tools:check /home/bjorn/repos/agents/tripsage-ai
> node scripts/check-ai-tools.mjs

🔍 Checking AI tool guardrails...


============================================================
📊 Summary
============================================================
Files scanned: 23
Hard violations: 0
Allowlisted: 0
Warnings: 0
============================================================

✅ AI tool guardrails check passed.
```

### `pnpm check:no-secrets`

```text
> tripsage-ai-frontend@1.22.5 check:no-secrets /home/bjorn/repos/agents/tripsage-ai
> node scripts/check-no-secrets.mjs

OK: no secrets detected in changed files.
```

## Route Inventory (summary)

- App route roots: `src/app/(marketing)`, `src/app/(auth)`, `src/app/dashboard`, `src/app/chat`, `src/app/auth` (misc auth utility routes)
- API route handlers: `src/app/api/**` (see `pnpm build` route table above for full list)
- Server Actions (`"use server"`): `src/lib/auth/actions.ts`, `src/app/dashboard/settings/api-keys/actions.ts`, `src/app/dashboard/search/*/actions.ts`
- Middleware: no `middleware.ts` file found via `rg --files`, but `pnpm build` reports `Proxy (Middleware)`; likely injected by BotId config (`withBotId(...)`) in `next.config.ts` (`UNVERIFIED`)

## Python / uv Project

- No `pyproject.toml` or `uv.lock` detected in this repo at time of audit.

## Next.js DevTools MCP Runtime Verification

### Runtime tools (observed)

- `nextjs_index` discovered an MCP-enabled dev server on `http://localhost:3000`.
- `nextjs_call:get_routes` output recorded in `docs/release/_logs/nextjs-routes.json`.
- `nextjs_call:get_logs` returned log path: `/home/bjorn/repos/agents/tripsage-ai/.next/dev/logs/next-development.log` (tail captured in `docs/release/_logs/nextjs-dev-tail.txt`).
- `nextjs_call:get_errors` returned: `No errors detected in 1 browser session(s).`
- `nextjs_call:get_page_metadata` for `http://localhost:3000/login?next=%2Fdashboard` listed:
  - `app/(auth)/layout.tsx`
  - `app/layout.tsx`
  - `app/(auth)/login/page.tsx`
  - boundary files: `app/(auth)/error.tsx`, `app/error.tsx`, `app/global-error.tsx`, `app/loading.tsx`, plus built-in `not-found.js`

### Browser automation (next-devtools `browser_eval`)

Observed in a real browser session (Playwright via Next DevTools MCP):

- Landing page `http://localhost:3000/` originally had a navbar “Sign up” link pointing to `http://localhost:3000/signup` (404). This was fixed by `T-006` to point to `http://localhost:3000/register`.
- A second “Sign up” CTA in the marketing hero points to `http://localhost:3000/register` (works), causing inconsistent entrypoints.
- `http://localhost:3000/privacy`, `http://localhost:3000/terms`, `http://localhost:3000/contact` originally returned 404 (broken footer + onboarding links). This was fixed by `T-007` by adding public marketing pages for each route.
- `http://localhost:3000/register` renders, and its in-form legal links now resolve after `T-007`.
- `http://localhost:3000/dashboard` redirects to `http://localhost:3000/login?next=%2Fdashboard` (expected for unauthenticated users).
