import { test, expect } from '@playwright/test'
import { mockAuthenticatedApi } from './fixtures/mockApi'
import { expectNoHorizontalOverflow, expectMinTouchTarget } from './fixtures/assertions'

// Coverage for the docs/36 Phase 3 AppShell: simplified mobile top bar (Back replaces the
// destination icon in a subscreen; Search/Create move out to the bottom nav / More sheet) and
// the fixed Home/Add/More bottom nav with two configurable shortcuts either side of Add.
// Desktop (tablet-768+) keeps the pre-Phase-3 top bar/sidebar behaviour unchanged.

test.beforeEach(async ({ page }) => {
  await mockAuthenticatedApi(page)
  await page.goto('/hub')
})

test('Hub renders without horizontal overflow', async ({ page }) => {
  // A real Hub-specific element, not a "the page rendered *something*" fallback — this must
  // fail if Hub's actual content goes missing, not just if the whole app fails to boot.
  await expect(page.getByRole('main').locator('p:visible').filter({ hasText: 'Nothing needs your attention right now.' }).first()).toBeVisible()
  await expectNoHorizontalOverflow(page)
})

test.describe('phone layout', () => {
  test.beforeEach(async ({}, testInfo) => {
    test.skip(testInfo.project.name === 'tablet-768', 'phone-only: bottom nav is md:hidden')
  })

  test('bottom navigation shows Home, shortcuts, Add and More, each a real touch target', async ({ page }) => {
    const nav = page.getByRole('navigation', { name: 'Main navigation' })
    await expect(nav).toBeVisible()
    // Home (hub) + up to two configurable shortcuts (fixture enables atlas/homestead/pets/
    // meridian, so calendar + atlas fill the two slots — see e2e/fixtures/mockApi.ts).
    const links = nav.getByRole('link')
    await expect(links).toHaveCount(3)
    const add = nav.getByRole('button', { name: 'Create something' })
    const more = nav.getByRole('button', { name: /More navigation|open all destinations/ })
    await expect(add).toBeVisible()
    await expect(more).toBeVisible()
    for (const link of await links.all()) {
      await expectMinTouchTarget(link)
    }
    await expectMinTouchTarget(add)
    await expectMinTouchTarget(more)
  })

  test('top bar Search and Create are not shown — they live in the bottom nav / More sheet', async ({ page }) => {
    await expect(page.locator('header').getByRole('button', { name: 'Search HomeStack' })).toBeHidden()
    // "Create something" still resolves — to the bottom nav's Add button, which shares the
    // label with the (hidden on phone) top bar version by design (same action either place).
    const nav = page.getByRole('navigation', { name: 'Main navigation' })
    await expect(nav.getByRole('button', { name: 'Create something' })).toBeVisible()
  })

  test('Hub opens with prominent Search and a prioritized daily feed', async ({ page }) => {
    await page.route('**/api/v1/hub/', async route => {
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({ widgets: [
          { key: 'daily_quote', name: 'Daily quote', size: 'small', supports_kiosk: true, items: [] },
          { key: 'calendar_upcoming', name: 'Coming up', size: 'medium', supports_kiosk: true, items: [] },
          { key: 'notifications_summary', name: 'Notifications', size: 'small', supports_kiosk: false, items: [], meta: { unread_count: 0 } },
        ] }),
      })
    })
    await page.reload()

    const feed = page.getByLabel('Your daily feed')
    await expect(feed.getByRole('heading', { name: 'Needs attention' })).toBeVisible()
    await expect(feed.getByRole('heading', { name: 'Today & upcoming' })).toBeVisible()
    await expect(feed.getByRole('heading', { name: 'More from your home' })).toBeVisible()
    const sectionOrder = await feed.locator('section h2').allTextContents()
    expect(sectionOrder).toEqual(['Needs attention', 'Today & upcoming', 'More from your home'])

    await page.getByRole('main').getByRole('button', { name: 'Search HomeStack' }).click()
    await expect(page.getByRole('dialog', { name: 'Search HomeStack' })).toBeVisible()
  })

  test('Quick Create opens from the bottom nav as a sheet without overflow and is closable', async ({ page }) => {
    await page.getByRole('button', { name: 'Create something' }).click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expectNoHorizontalOverflow(page)
    await page.keyboard.press('Escape')
    await expect(dialog).not.toBeVisible()
  })

  test('Search is reachable from the More sheet without overflow', async ({ page }) => {
    const nav = page.getByRole('navigation', { name: 'Main navigation' })
    await nav.getByRole('button', { name: /More navigation|open all destinations/ }).click()
    await page.getByRole('dialog').getByRole('button', { name: /Search/ }).click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expectNoHorizontalOverflow(page)
  })

  test('More sheet lists destinations without overflow and is closable', async ({ page }) => {
    const nav = page.getByRole('navigation', { name: 'Main navigation' })
    await nav.getByRole('button', { name: /More navigation|open all destinations/ }).click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expectNoHorizontalOverflow(page)
  })

  test('More sheet traps focus while open and restores it to the More button on close', async ({ page }) => {
    const nav = page.getByRole('navigation', { name: 'Main navigation' })
    const moreButton = nav.getByRole('button', { name: /More navigation|open all destinations/ })
    await moreButton.click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    // useDialogA11y moves focus into the sheet on open (the shared hook Modal itself uses) —
    // checked as real DOM containment, not just "the dialog happens to contain this text".
    const focusIsInsideDialog = await page.evaluate(() =>
      document.querySelector('[role="dialog"]')?.contains(document.activeElement) ?? false)
    expect(focusIsInsideDialog).toBe(true)
    await page.keyboard.press('Escape')
    await expect(dialog).not.toBeVisible()
    await expect(moreButton).toBeFocused()
  })

  test('shell and dialog controls meet the 44px touch-target baseline', async ({ page }) => {
    await expectMinTouchTarget(page.getByRole('button', { name: 'Notifications' }))
    const nav = page.getByRole('navigation', { name: 'Main navigation' })
    await nav.getByRole('button', { name: /More navigation|open all destinations/ }).click()
    await expectMinTouchTarget(page.getByRole('button', { name: 'Close' }))
    await expectMinTouchTarget(page.getByRole('button', { name: 'Edit', exact: true }))
    await expectMinTouchTarget(page.getByRole('button', { name: 'Edit bottom bar' }))
  })

  test('a nested route shows Back instead of the destination icon', async ({ page }) => {
    // /corners/:personId is nested below the core /corners route (src/config/stacks.ts) —
    // any such route exercises the same Back-vs-icon branch without needing node-specific mocks.
    // CornerPage does need a real CornerResponse shape to avoid crashing on render (see
    // deep-link-back.spec.ts) — registered here, after the shared beforeEach's broader mock,
    // so it takes precedence for this one path (Playwright checks routes most-recently-added
    // first).
    await page.route('**/api/v1/corners/1/', async route => {
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({
          person: { id: 1, display_name: 'Test User', preferred_name: 'Test User', avatar: '', colour: '#1d7a91', profile_type: 'adult', linked_user_id: 1, date_of_birth: null, name: 'Test User', is_me: true },
          summary: { activity_count: 0, assignment_count: 0, collection_count: 0 },
          activity: [], assignments: [], collections: [],
        }),
      })
    })
    await page.goto('/corners/1')
    await expect(page.getByRole('button', { name: 'Back' })).toBeVisible()
    await expectNoHorizontalOverflow(page)
  })
})

test.describe('tablet transition (768px)', () => {
  test.beforeEach(async ({}, testInfo) => {
    test.skip(testInfo.project.name !== 'tablet-768', 'tablet-only')
  })

  test('desktop sidebar replaces the bottom nav, and the top bar keeps Search/Create', async ({ page }) => {
    await expect(page.getByRole('navigation', { name: 'Main navigation' })).toBeHidden()
    await expect(page.getByRole('button', { name: 'Search HomeStack' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Create something' })).toBeVisible()
    await expectNoHorizontalOverflow(page)
  })
})

test('dark mode renders coherently', async ({ page }) => {
  // useDarkMode's mount effect writes its own computed value back to localStorage
  // asynchronously (src/hooks/useDarkMode.ts) — if that write lands *after* our override below,
  // it silently clobbers it back to whatever prefers-color-scheme resolved to. Waiting for the
  // key to exist first proves that initial effect has already settled, so our override is the
  // last write before reload rather than a race with it.
  await page.waitForFunction(() => localStorage.getItem('hs-dark') !== null)
  await page.evaluate(() => localStorage.setItem('hs-dark', 'true'))
  await page.reload()
  await expect(page.locator('html.dark')).toHaveCount(1)
  await expectNoHorizontalOverflow(page)
})
