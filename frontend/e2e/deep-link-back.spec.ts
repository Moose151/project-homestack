import { test, expect } from '@playwright/test'
import { mockAuthenticatedApi } from './fixtures/mockApi'

// docs/36 Phase 3 review: navigate(-1) is unsafe on a cold entry — a PWA launch, a push-
// notification deep link, or just pasting a URL — because there is no in-app history to go back
// to; it could leave HomeStack entirely or land on an unrelated prior browser-history page.
// This deliberately does NOT visit /hub first (unlike mobile-shell.spec.ts, whose shared
// beforeEach does): the whole point is a context whose *first* navigation is the nested route,
// matching a real cold launch. Genuine in-app history (Back after a real client-side navigation,
// where navigate(-1) is the correct and expected behaviour) isn't exercised here — that needs an
// actual UI-driven transition into a nested route, which no page currently exposes to click
// through to in a way this suite can trigger without a node-specific mock; add it once a later
// phase (e.g. Corners, §6.13) gives a real in-app link to click.

test.beforeEach(async ({}, testInfo) => {
  test.skip(testInfo.project.name === 'tablet-768', 'phone-only: the Back button is md:hidden')
})

test('Back on a cold-loaded nested route falls back to the stack parent, not browser history', async ({ page }) => {
  // CornerPage renders unconditionally as soon as `corner` is non-null, so the fixture needs
  // the real CornerResponse shape (src/api/types.ts) — the generic empty-object fallback isn't
  // enough and crashes the page (`corner.collections.filter` on undefined), which left the Back
  // button mid-render/detached and made earlier runs of this test hang rather than fail clearly.
  await mockAuthenticatedApi(page, {
    '/api/v1/corners/1/': {
      person: { id: 1, display_name: 'Test User', preferred_name: 'Test User', avatar: '', colour: '#1d7a91', profile_type: 'adult', linked_user_id: 1, date_of_birth: null, name: 'Test User', is_me: true },
      summary: { activity_count: 0, assignment_count: 0, collection_count: 0 },
      activity: [], assignments: [], collections: [],
    },
  })
  // /corners/:personId is nested below the core /corners route (src/config/stacks.ts). This is
  // the very first navigation in this browser context — there is no prior HomeStack entry, and
  // no non-HomeStack page before it either (a fresh context starts with no history at all).
  await page.goto('/corners/1')
  const backButton = page.getByRole('button', { name: 'Back' })
  await expect(backButton).toBeVisible()
  await backButton.click()
  // A real navigate(-1) here would either throw (no history entry to go back to) or, on a
  // context that did have prior non-HomeStack history, leave the app entirely. Landing on the
  // stack's own base route proves the safe fallback fired instead.
  await expect(page).toHaveURL(/\/corners$/)
})
