# TripSage AI — v1.0.0 Release Notes

Release date: `TBD`

## Highlights

- `TBD`

## Notable Fixes

- Dev server now boots in non-production even if optional integration env vars are left blank/placeholder (`T-001`).
- Public navigation fixes:
  - Navbar “Sign up” now routes to `/register` (removed `/signup` 404) (`T-006`).
  - Added public `/privacy`, `/terms`, `/contact` pages to unblock onboarding/legal links (`T-007`).
  - Password reset “Contact support” links now route to `/contact` (removed `/support` 404) (`T-009`).

## Security

- `TBD`

## Known Issues

- Dashboard E2E is not yet green in Chromium (`T-002`).
- Trip create CTA links to a missing route (`/dashboard/trips/create`) until `T-008` lands.
