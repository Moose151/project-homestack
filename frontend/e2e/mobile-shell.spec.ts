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
    // Home (hub) + two configurable shortcuts (fixture enables atlas/homestead/pets/
    // meridian, so calendar + atlas fill the two slots — see e2e/fixtures/mockApi.ts).
    const links = nav.getByRole('link')
    await expect(links).toHaveCount(3)
    const add = nav.getByRole('button', { name: 'Create something' })
    const more = nav.getByRole('button', { name: /More navigation|open all destinations/ })
    await expect(add).toBeVisible()
    await expect(more).toBeVisible()
    await expect(nav.locator(':scope > a, :scope > button')).toHaveCount(5)
    await expect(nav.locator('[data-nav-key="hub"]')).toHaveAttribute('aria-current', 'page')
    await expect(nav.locator('[data-nav-key="calendar"]')).toBeVisible()
    await expect(nav.locator('[data-nav-key="atlas"]')).toBeVisible()
    await expect(nav.locator('[data-nav-key="add"]')).toContainText('Add')
    await expect(nav.locator('[data-nav-key="more"]')).toContainText('More')
    for (const link of await links.all()) {
      await expectMinTouchTarget(link)
    }
    await expectMinTouchTarget(add)
    await expectMinTouchTarget(more)

    const dockBox = await nav.boundingBox()
    expect(dockBox).not.toBeNull()
    expect(dockBox!.x).toBeGreaterThanOrEqual(12)
    expect(page.viewportSize()!.width - dockBox!.x - dockBox!.width).toBeGreaterThanOrEqual(12)
    expect(page.viewportSize()!.height - dockBox!.y - dockBox!.height).toBeGreaterThanOrEqual(9)
    const activeBackground = await nav.locator('[data-nav-key="hub"]').evaluate(element => getComputedStyle(element).backgroundColor)
    expect(activeBackground).not.toBe('rgba(0, 0, 0, 0)')
  })

  test('More keeps its icon and label while representing an unpinned Fitness area', async ({ page }) => {
    const enabledFitness = {
      key: 'fitness', name: 'fitness', description: '', icon: '', is_core: false,
      supports_kiosk: false, supports_sensitive_lock: false, can_view: true, is_enabled: true,
      is_hidden: false, requires_reauthentication: false, display_order: 0, custom_name: '', custom_icon: '',
    }
    await page.route('**/api/v1/nodes/', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([enabledFitness]) }))
    await page.route('**/api/v1/people/', route => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }))
    await page.route('**/api/v1/fitness/exercises/', route => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }))
    await page.route('**/api/v1/fitness/programs/', route => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }))
    await page.route('**/api/v1/fitness/records/', route => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }))
    await page.route('**/api/v1/fitness/sessions/', route => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }))
    await page.goto('/fitness')

    const more = page.getByRole('navigation', { name: 'Main navigation' }).locator('[data-nav-key="more"]')
    await expect(more).toContainText('☰')
    await expect(more).toContainText('More')
    await expect(more).not.toContainText('Fitness')
  })

  test('shortcut editor exposes two slots, swaps duplicates, resets, and persists per user', async ({ page }) => {
    // Shortcuts are a per-user *server* preference as of 0.39.0, so this asserts what is sent
    // to the account rather than what lands in one browser's localStorage.
    let saved: string[] | null = null
    await page.route('**/api/v1/auth/preferences/**', async route => {
      const method = route.request().method()
      if (method === 'PATCH') {
        saved = (route.request().postDataJSON() as { mobile_nav: string[] }).mobile_nav
      } else if (method === 'DELETE') {
        saved = []
      }
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({ tab_order: {}, mobile_nav: saved ?? [] }),
      })
    })
    await page.reload()

    const nav = page.getByRole('navigation', { name: 'Main navigation' })
    await nav.getByRole('button', { name: 'More navigation and profile options' }).click()
    const launcher = page.getByRole('dialog', { name: 'All HomeStack' })
    await launcher.getByRole('button', { name: 'Customise navigation' }).click()
    const slot1 = launcher.getByRole('combobox', { name: 'Choose shortcut for Slot 1' })
    const slot2 = launcher.getByRole('combobox', { name: 'Choose shortcut for Slot 2' })
    await expect(slot1).toHaveValue('calendar')
    await expect(slot2).toHaveValue('atlas')

    // Picking the node already in the other slot swaps them; it never duplicates.
    await slot1.selectOption('atlas')
    await expect.poll(() => saved).toEqual(['atlas', 'calendar'])
    await expect(slot1).toHaveValue('atlas')
    await expect(slot2).toHaveValue('calendar')

    await launcher.getByRole('button', { name: 'Reset to defaults' }).click()
    await expect.poll(() => saved).toEqual([])
    await expect(slot1).toHaveValue('calendar')
    await expect(slot2).toHaveValue('atlas')
  })

  test('a disabled saved shortcut is repaired without moving the still-valid slot', async ({ page }) => {
    // 'fitness' is in the catalogue but not enabled for the fixture household.
    let saved: string[] = ['calendar', 'fitness']
    await page.route('**/api/v1/auth/preferences/**', async route => {
      if (route.request().method() === 'PATCH') {
        saved = (route.request().postDataJSON() as { mobile_nav: string[] }).mobile_nav
      }
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({ tab_order: {}, mobile_nav: saved }),
      })
    })
    await page.reload()

    const nav = page.getByRole('navigation', { name: 'Main navigation' })
    await expect(nav.locator('[data-nav-key="calendar"]')).toBeVisible()
    await expect(nav.locator('[data-nav-key="atlas"]')).toBeVisible()
    // The unreachable choice is repaired and written back, leaving the valid slot in place.
    await expect.poll(() => saved).toEqual(['calendar', 'atlas'])
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

  test('Quick Create prioritizes actions for the current area and keeps global actions', async ({ page }) => {
    await page.goto('/calendar')
    await page.getByRole('button', { name: 'Create something' }).click()
    const dialog = page.getByRole('dialog')
    const suggested = dialog.getByRole('region', { name: 'Suggested here' })
    const global = dialog.getByRole('region', { name: 'More ways to add' })
    await expect(suggested.getByRole('button', { name: /Calendar event/ })).toBeVisible()
    await expect(global.getByRole('button', { name: /Home plan/ })).toBeVisible()
    await expect(global.getByRole('button', { name: /Points task/ })).toBeVisible()
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
    await expect(dialog.getByRole('heading', { name: 'All HomeStack' })).toBeVisible()
    await expect(dialog.getByRole('button', { name: 'Search all HomeStack' })).toBeVisible()
    await expect(dialog.getByText('Pinned', { exact: true }).first()).toBeVisible()
    await expect(dialog.getByText('All areas', { exact: true })).toBeVisible()
    await expect(dialog.getByText('Account & app', { exact: true })).toBeVisible()
    // Disabled or inaccessible nodes never leak into the launcher.
    await expect(dialog.getByRole('link', { name: /Money/ })).toHaveCount(0)
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
    await expectMinTouchTarget(page.getByRole('button', { name: 'Customise navigation' }))
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
