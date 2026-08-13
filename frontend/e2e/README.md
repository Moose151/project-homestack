# Mobile UX acceptance tests

Playwright coverage for `docs/36_Mobile_UX_Strategy_and_Implementation_Plan.md`. Run from
`frontend/`:

```bash
npm run test:e2e
```

Requires the dev stack already running (`docker compose -f ../docker-compose.yml -f
../docker-compose.dev.yml up -d`, or whatever is already up — the config points at
`http://localhost:5173` and does not start its own server). Browsers are installed with
`npx playwright install chromium` (host-side; Playwright's bundled Chromium does not run on the
frontend container's Alpine base, so tests run from the host, not `docker exec`).

## The one rule: never touch real data

This suite runs against the household's real dev server, which shares a database with real daily
use. A real login would exercise real accounts, and any subsequent write could touch real
household records or fire a genuine Web Push notification to someone's phone.

**Every test must go through `fixtures/mockApi.ts`'s `mockAuthenticatedApi()` or
`mockLoggedOutApi()` before navigating.** These intercept every `/api/v1/**` request at the
browser level and answer from fixtures — nothing reaches the real Django backend. Add a route
override via the second `overrides` argument if a new test needs a shape the shared fixtures
don't provide; do not remove the interception to "just log in for real."

## Viewport contract (docs/36 §8 Phase 1)

Defined once in `playwright.config.ts` as projects, reused by every spec:

- `phone` — 390×844 (iPhone 13), light — everyday phone design target (doc's 360–430px band).
- `phone-dark` — same viewport, dark colour scheme.
- `phone-stress-320` — 320px width — minimum/stress test.
- `tablet-768` — 768×1024 — the tablet transition target, where the shell switches from bottom
  nav to the desktop sidebar (`md:` breakpoint).

## Shared assertions (`fixtures/assertions.ts`)

- `expectNoHorizontalOverflow(page)` — docs/36 §9.1: no document-level horizontal scroll at
  320px+.
- `expectMinTouchTarget(locator)` — docs/36 §3.3/§9.1: ~44px minimum touch targets.

Reuse both rather than re-deriving them as each node gets converted in later phases.

## What's here so far

- `login.spec.ts` — the unauthenticated login/PIN screen.
- `mobile-shell.spec.ts` — the current AppShell (top bar, bottom nav, Quick Create, Search, More
  sheet, dark mode). **This will need updating once Phase 3 redesigns the shell** (simplified top
  bar, fixed Home/Add/More bottom nav) — the mocking approach and shared assertions carry
  forward unchanged; the specific selectors/counts do not.

Add a spec per screen as each is converted, matching docs/36 §8's phase order. Don't try to
retrofit full coverage of every existing page up front — that recreates exactly the page-by-page
inconsistency the strategy document is trying to move away from.
