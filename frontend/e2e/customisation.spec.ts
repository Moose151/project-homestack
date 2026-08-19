import { test, expect } from '@playwright/test'
import { mockAuthenticatedApi } from './fixtures/mockApi'

// Per-user interface preferences: tab order and the mobile dock's two shortcut slots. Both are
// server-persisted, so these tests assert what actually goes over the wire, not localStorage.

const PETS_FIXTURES = {
  '/api/v1/pets/': [],
  '/api/v1/pets/treatments/': [],
  '/api/v1/pets/appointments/': [],
}

test.describe('tab ordering', () => {
  test('saved order reorders the tabs and sets the landing tab', async ({ page }) => {
    await mockAuthenticatedApi(page, {
      ...PETS_FIXTURES,
      '/api/v1/auth/preferences/': {
        tab_order: { pets: ['appointments', 'reminders', 'pets'] },
        mobile_nav: [],
      },
    })
    await page.goto('/pets')
    const tabs = page.getByRole('tab')
    await expect(tabs.first()).toHaveText(/Appointments/i)
    // First in the user's order becomes the default landing tab.
    await expect(tabs.first()).toHaveAttribute('aria-selected', 'true')
  })

  test('an explicit ?tab= always beats the saved default', async ({ page }) => {
    await mockAuthenticatedApi(page, {
      ...PETS_FIXTURES,
      '/api/v1/auth/preferences/': {
        tab_order: { pets: ['appointments', 'reminders', 'pets'] },
        mobile_nav: [],
      },
    })
    await page.goto('/pets?tab=pets')
    await expect(page.getByRole('tab', { name: /^Pets/i })).toHaveAttribute('aria-selected', 'true')
  })

  test('an unknown saved tab is ignored and a new tab still appears', async ({ page }) => {
    await mockAuthenticatedApi(page, {
      ...PETS_FIXTURES,
      '/api/v1/auth/preferences/': {
        // 'ghost' no longer exists; 'appointments' was never ordered by this user.
        tab_order: { pets: ['ghost', 'reminders'] },
        mobile_nav: [],
      },
    })
    await page.goto('/pets')
    // allInnerTexts does not auto-wait, so anchor on a tab being present first.
    await expect(page.getByRole('tab').first()).toBeVisible()
    const labels = await page.getByRole('tab').allInnerTexts()
    expect(labels.join(' ')).not.toContain('ghost')
    expect(labels.join(' ')).toContain('Appointments')
    await expect(page.getByRole('tab').first()).toHaveText(/Reminders/i)
  })

  test('reordering persists the new order to the server', async ({ page }) => {
    let patched: Record<string, unknown> | null = null
    await mockAuthenticatedApi(page, PETS_FIXTURES)
    await page.route('**/api/v1/auth/preferences/**', async route => {
      if (route.request().method() === 'PATCH') {
        patched = route.request().postDataJSON() as Record<string, unknown>
        await route.fulfill({
          status: 200, contentType: 'application/json',
          body: JSON.stringify({ tab_order: patched.tab_order, mobile_nav: [] }),
        })
        return
      }
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({ tab_order: {}, mobile_nav: [] }),
      })
    })

    await page.goto('/pets')
    await page.getByRole('button', { name: /Reorder/i }).first().click()
    // Move-up/down buttons are the primary control: they work with a finger, a mouse and a
    // keyboard, unlike a drag target.
    await page.getByRole('button', { name: 'Move Appointments up' }).click()
    await page.getByRole('button', { name: 'Move Appointments up' }).click()
    await page.getByRole('button', { name: 'Save order' }).click()

    await expect.poll(() => patched).not.toBeNull()
    expect((patched as Record<string, Record<string, string[]>>).tab_order.pets[0]).toBe('appointments')
  })

  test('a tab the user cannot reach is never offered by the customiser', async ({ page }, testInfo) => {
    // Home only offers its "costs & cover" tab when Money is available to this account. The
    // fixture household has Money disabled, so a saved order naming that tab must not bring it
    // back — the customiser can only ever offer what the page itself rendered. Home's tab row
    // is desktop-only (`hidden sm:block`), so this runs on the wider project.
    test.skip(testInfo.project.name !== 'tablet-768', 'Home renders its tab row from sm: up')
    await mockAuthenticatedApi(page, {
      '/api/v1/auth/preferences/': {
        tab_order: { homestead: ['finances', 'contacts', 'overview'] },
        mobile_nav: [],
      },
    })
    await page.goto('/homestead')
    await expect(page.getByRole('tab').first()).toBeVisible()
    const labels = (await page.getByRole('tab').allInnerTexts()).join(' ').toLowerCase()
    expect(labels).not.toContain('costs & cover')
    // ...while the rest of the saved order is honoured.
    await expect(page.getByRole('tab').first()).toHaveText(/contacts/i)

    await page.getByRole('button', { name: /Reorder/i }).first().click()
    const offered = (await page.getByRole('list', { name: 'Tab order' }).innerText()).toLowerCase()
    expect(offered).not.toContain('costs & cover')
    expect(offered).toContain('contacts')
  })
})

test.describe('mobile navigation shortcuts', () => {
  test.beforeEach(async ({}, testInfo) => {
    test.skip(testInfo.project.name === 'tablet-768', 'phone-only: the dock is a phone surface')
  })

  test('the dock renders the saved server shortcuts', async ({ page }) => {
    await mockAuthenticatedApi(page, {
      '/api/v1/auth/preferences/': { tab_order: {}, mobile_nav: ['pets', 'atlas'] },
    })
    await page.goto('/hub')
    // Scoped to the dock: the desktop sidebar carries the same hrefs but is hidden on phone.
    const dock = page.locator('nav.mobile-bottom-nav')
    await expect(dock).toBeVisible()
    await expect(dock.locator('a[href="/pets"]')).toBeVisible()
    await expect(dock.locator('a[href="/atlas"]')).toBeVisible()
  })

  test('choosing a shortcut persists it to the account', async ({ page }) => {
    let patched: Record<string, unknown> | null = null
    await mockAuthenticatedApi(page)
    await page.route('**/api/v1/auth/preferences/**', async route => {
      if (route.request().method() === 'PATCH') {
        patched = route.request().postDataJSON() as Record<string, unknown>
        await route.fulfill({
          status: 200, contentType: 'application/json',
          body: JSON.stringify({ tab_order: {}, mobile_nav: patched.mobile_nav }),
        })
        return
      }
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({ tab_order: {}, mobile_nav: [] }),
      })
    })

    await page.goto('/hub')
    await page.getByRole('button', { name: /More/i }).last().click()
    await page.getByRole('button', { name: 'Customise navigation' }).click()
    await page.getByLabel('Choose shortcut for Slot 1').selectOption('pets')

    await expect.poll(() => patched).not.toBeNull()
    expect((patched as Record<string, string[]>).mobile_nav).toContain('pets')
  })

  test('a shortcut for a disabled node is replaced, not left blank', async ({ page }) => {
    // 'solace' is in the fixture catalogue but not enabled for the household.
    await mockAuthenticatedApi(page, {
      '/api/v1/auth/preferences/': { tab_order: {}, mobile_nav: ['solace', 'atlas'] },
    })
    await page.goto('/hub')
    const dock = page.locator('nav.mobile-bottom-nav')
    await expect(dock).toBeVisible()
    // The dock still shows two shortcuts; the unreachable one is repaired from the defaults.
    await expect(dock.locator('a[href="/solace"]')).toHaveCount(0)
    await expect(dock.locator('a[href="/atlas"]')).toBeVisible()
  })
})
