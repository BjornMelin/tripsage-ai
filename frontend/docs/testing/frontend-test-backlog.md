# Frontend Test Backlog

Tracking list of tests that are written but skipped or still needed. Check items off as features ship and tests are enabled.

## Auth Callback Page (`src/app/(auth)/callback/__tests__/page.test.tsx`)

- [ ] TODO: Successful OAuth flow shows success screen then redirects to `/dashboard` after 2s.
- [ ] TODO: Error mapping: Supabase auth error -> error screen -> redirect `?error=oauth_failed`.
- [ ] TODO: No session -> error screen -> redirect `?error=no_session`.
- [ ] TODO: Unexpected error -> error screen -> redirect `?error=unexpected`.
- [ ] TODO: PKCE failure renders message and redirect.
- [ ] TODO: Invalid/expired code messages displayed.
- [ ] TODO: Heading hierarchy and success/error color tokens finalized.

## Personal Info Section (`src/components/features/profile/__tests__/personal-info-section.test.tsx`)

- [ ] TODO: Form validations (required, URL, bio length) reflect zod schema.
- [ ] TODO: Avatar upload: accept image types, size limit, preview, persistence.
- [ ] TODO: Profile update writes through store/service; toasts on success/error.
- [ ] TODO: Fallback initials generation parity with design.

## Security Section (`src/components/features/profile/__tests__/security-section.test.tsx`)

- [ ] TODO: 2FA toggle calls real API and persists; verify on/off branches.
- [ ] TODO: Device revocation dialog triggers API and invalidates session list.
- [ ] TODO: Password change integrates API, handles error variants.

## Account Settings Section (`src/components/features/profile/__tests__/account-settings-section.test.tsx`)

- [ ] TODO: Email update triggers auth email change and verification state.
- [ ] TODO: Account deletion request + server confirmation window.
- [ ] TODO: Notification preferences persisted via backend.

## Activity Search Form (`src/components/features/search/__tests__/activity-search-form.test.tsx`)

- [ ] TODO: onSearch payload shape finalized and integrated with search pipeline.
- [ ] TODO: React Query submission path wired (retry, error UI).

## Itinerary Builder (`src/components/features/trips/__tests__/itinerary-builder.test.tsx`)

- [ ] TODO: Edit dialog flows (open, modify, save) with portal-safe selectors.
- [ ] TODO: Combobox/select interactions via accessible listbox APIs.

## Trip Card (`src/components/features/trips/__tests__/trip-card.test.tsx`)

- [ ] TODO: Date formatting and duration calculation match final util functions.

## Login Form (`src/components/auth/__tests__/login-form.test.tsx`)

- [ ] TODO: Redirect behavior confirmed (push vs replace) for authenticated users.
- [ ] TODO: OAuth button flows and providers (if/when added).

## General

- [ ] TODO: Add fake timers to time-based UI when required; otherwise prefer retryDelay: 0 for React Query.
- [ ] TODO: Replace brittle className checks with role/name/label or testids.
