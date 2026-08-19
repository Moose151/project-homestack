import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import { mockAuthenticatedApi, nodesWith, FIXTURE_USER } from './fixtures/mockApi'
import { expectNoHorizontalOverflow } from './fixtures/assertions'

// The desktop sidebar can collapse to an icon rail. Collapsing is presentation only: it uses the
// same navigation data, reveals nothing extra, and changes no permission.

/** A preference store that remembers what it was PATCHed, like a working backend. */
async function preferenceStore(page: Page, initial = false) {
  const stored: Record<string, unknown> = {
    tab_order: {}, mobile_nav: [], sidebar_collapsed: initial,
  }
  await page.route('**/api/v1/auth/preferences/**', async route => {
    if (route.request().method() === 'PATCH') {
      Object.assign(stored, route.request().postDataJSON())
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(stored) })
  })
  return stored
}

const sidebar = (page: Page) => page.locator('[data-sidebar]')
const main = (page: Page) => page.getByRole('main')

test.describe('desktop sidebar', () => {
  test.beforeEach(async ({}, testInfo) => {
    test.skip(testInfo.project.name !== 'tablet-768', 'viewport is set per block; desktop only')
  })

  test.describe('wide desktop', () => {
    test.use({ viewport: { width: 1440, height: 900 } })

    test('starts expanded with labels and headings', async ({ page }) => {
      await mockAuthenticatedApi(page)
      await preferenceStore(page)
      await page.goto('/hub')

      await expect(sidebar(page)).toHaveAttribute('data-collapsed', 'false')
      expect((await sidebar(page).boundingBox())!.width).toBe(272)
      await expect(sidebar(page).getByText('Dashboard', { exact: true })).toBeVisible()
      await expect(sidebar(page).getByText('Start here')).toBeVisible()
    })

    test('collapsing narrows the rail and widens the content', async ({ page }) => {
      await mockAuthenticatedApi(page)
      await preferenceStore(page)
      await page.goto('/hub')

      const contentBefore = (await main(page).boundingBox())!.width
      await page.getByRole('button', { name: 'Collapse navigation' }).click()

      await expect(sidebar(page)).toHaveAttribute('data-collapsed', 'true')
      const railWidth = (await sidebar(page).boundingBox())!.width
      expect(railWidth).toBe(76)
      // The released width is reclaimed immediately — no invisible column left behind.
      const contentAfter = (await main(page).boundingBox())!.width
      expect(contentAfter).toBeGreaterThan(contentBefore + 150)
    })

    test('the rail keeps its icons but drops the text', async ({ page }) => {
      await mockAuthenticatedApi(page)
      await preferenceStore(page, true)
      await page.goto('/hub')

      await expect(sidebar(page).locator('[data-nav-key="hub"]')).toBeVisible()
      await expect(sidebar(page).locator('[data-nav-key="calendar"]')).toBeVisible()
      await expect(sidebar(page).getByText('Start here')).toHaveCount(0)
      await expect(sidebar(page).getByText('Your household at a glance')).toHaveCount(0)
    })

    test('every rail icon still names its destination for assistive tech', async ({ page }) => {
      await mockAuthenticatedApi(page)
      await preferenceStore(page, true)
      await page.goto('/hub')

      for (const name of ['Dashboard', 'Calendar']) {
        await expect(sidebar(page).getByRole('link', { name })).toBeVisible()
      }
    })

    test('a tooltip appears on hover and on keyboard focus, not hover only', async ({ page }) => {
      await mockAuthenticatedApi(page)
      await preferenceStore(page, true)
      await page.goto('/hub')

      const calendar = sidebar(page).locator('[data-nav-key="calendar"]')
      const tip = calendar.getByRole('tooltip')
      await expect(tip).toBeHidden()
      await calendar.hover()
      await expect(tip).toBeVisible()

      await page.mouse.move(0, 0)
      await calendar.focus()
      await expect(tip).toBeVisible()
    })

    test('the active destination stays identifiable when collapsed', async ({ page }) => {
      await mockAuthenticatedApi(page, { '/api/v1/calendar/events/': [] })
      await preferenceStore(page, true)
      await page.goto('/calendar')
      await expect(sidebar(page).locator('[data-nav-key="calendar"]')).toHaveAttribute('aria-current', 'page')
    })

    test('the rail can navigate and then expand again', async ({ page }) => {
      await mockAuthenticatedApi(page, { '/api/v1/calendar/events/': [] })
      await preferenceStore(page, true)
      await page.goto('/hub')

      await sidebar(page).locator('[data-nav-key="calendar"]').click()
      await expect(page).toHaveURL(/\/calendar/)

      await page.getByRole('button', { name: 'Expand navigation' }).click()
      await expect(sidebar(page)).toHaveAttribute('data-collapsed', 'false')
      await expect(sidebar(page).getByText('Start here')).toBeVisible()
    })

    test('the choice survives a reload', async ({ page }) => {
      await mockAuthenticatedApi(page)
      const stored = await preferenceStore(page)
      await page.goto('/hub')

      await page.getByRole('button', { name: 'Collapse navigation' }).click()
      await expect.poll(() => stored.sidebar_collapsed).toBe(true)

      await page.reload()
      await expect(sidebar(page)).toHaveAttribute('data-collapsed', 'true')
    })

    test("one person's choice does not reach another", async ({ page }) => {
      // Server-side and per user: a second account loads its own preference.
      await mockAuthenticatedApi(page, {
        '/api/v1/auth/me/': { ...FIXTURE_USER, id: 2, username: 'other', display_name: 'Other' },
        '/api/v1/auth/preferences/': { tab_order: {}, mobile_nav: [], sidebar_collapsed: false },
      })
      await page.goto('/hub')
      await expect(sidebar(page)).toHaveAttribute('data-collapsed', 'false')
    })

    test('collapsing reveals no destination the expanded rail withheld', async ({ page }) => {
      // 'solace' and 'travel' are absent from the fixture household.
      await mockAuthenticatedApi(page)
      await preferenceStore(page, true)
      await page.goto('/hub')
      await expect(sidebar(page).locator('[data-nav-key="solace"]')).toHaveCount(0)
      await expect(sidebar(page).locator('[data-nav-key="travel"]')).toHaveCount(0)
    })

    test('kiosk stays reachable from the rail', async ({ page }) => {
      await mockAuthenticatedApi(page)
      await preferenceStore(page, true)
      await page.goto('/hub')
      await expect(sidebar(page).getByRole('link', { name: 'Open kiosk' })).toBeVisible()
    })

    test('Money still requires its unlock when reached from the rail', async ({ page }) => {
      await mockAuthenticatedApi(page, { '/api/v1/nodes/': nodesWith('solace') })
      await preferenceStore(page, true)
      await page.route('**/api/v1/solace/**', async route => {
        await route.fulfill({
          status: 403, contentType: 'application/json',
          body: JSON.stringify({ detail: 'Password re-authentication required for this area.', code: 'reauth_required', node: 'solace' }),
        })
      })
      await page.goto('/hub')
      await sidebar(page).locator('[data-nav-key="solace"]').click()
      // Collapsing changes presentation only — the sensitive gate is untouched.
      await expect(page.getByText(/password|unlock/i).first()).toBeVisible()
    })
  })

  test.describe('half-screen desktop', () => {
    // The width the Calendar toolbar fix targets; it must hold in both sidebar states.
    test.use({ viewport: { width: 960, height: 900 } })

    test('Calendar stays correct with the sidebar expanded', async ({ page }) => {
      await mockAuthenticatedApi(page, { '/api/v1/calendar/events/': [] })
      await preferenceStore(page, false)
      await page.goto('/calendar')
      await page.getByRole('button', { name: 'day', exact: true }).click()

      const label = page.locator('[data-calendar-period-label]')
      expect(await label.evaluate(el => el.scrollWidth > el.clientWidth + 1)).toBe(false)
      await expectNoHorizontalOverflow(page)
    })

    test('Calendar stays correct with the sidebar collapsed', async ({ page }) => {
      await mockAuthenticatedApi(page, { '/api/v1/calendar/events/': [] })
      await preferenceStore(page, true)
      await page.goto('/calendar')
      await page.getByRole('button', { name: 'day', exact: true }).click()

      const label = page.locator('[data-calendar-period-label]')
      expect(await label.evaluate(el => el.scrollWidth > el.clientWidth + 1)).toBe(false)
      await expectNoHorizontalOverflow(page)

      // The toolbar must stay inside the widened content column.
      const toolbar = await page.locator('[data-calendar-toolbar]').boundingBox()
      const content = await main(page).boundingBox()
      expect(toolbar!.x).toBeGreaterThanOrEqual(content!.x - 1)
      expect(toolbar!.x + toolbar!.width).toBeLessThanOrEqual(content!.x + content!.width + 1)
    })

    test('collapsing does not cause horizontal overflow', async ({ page }) => {
      await mockAuthenticatedApi(page)
      await preferenceStore(page)
      await page.goto('/hub')
      await page.getByRole('button', { name: 'Collapse navigation' }).click()
      await expect(sidebar(page)).toHaveAttribute('data-collapsed', 'true')
      await expectNoHorizontalOverflow(page)
    })
  })

  test.describe('narrowest desktop', () => {
    // md (768px) is where the sidebar first appears.
    test.use({ viewport: { width: 800, height: 900 } })

    test('collapse works at the narrowest desktop width', async ({ page }) => {
      await mockAuthenticatedApi(page)
      await preferenceStore(page)
      await page.goto('/hub')
      await page.getByRole('button', { name: 'Collapse navigation' }).click()
      expect((await sidebar(page).boundingBox())!.width).toBe(76)
      await expectNoHorizontalOverflow(page)
    })
  })
})

test.describe('phone is unaffected', () => {
  test.beforeEach(async ({}, testInfo) => {
    test.skip(testInfo.project.name === 'tablet-768', 'phone projects only')
  })

  test('the desktop rail never appears beside the bottom nav', async ({ page }) => {
    await mockAuthenticatedApi(page)
    await preferenceStore(page, true)   // collapsed on desktop
    await page.goto('/hub')

    // The aside is md:flex, so it is not rendered visibly on a phone at all.
    await expect(sidebar(page)).toBeHidden()
    await expect(page.locator('nav.mobile-bottom-nav')).toBeVisible()
    await expectNoHorizontalOverflow(page)
  })

  test('the bottom-nav shortcut customisation still works', async ({ page }) => {
    let saved: string[] | null = null
    await mockAuthenticatedApi(page)
    await page.route('**/api/v1/auth/preferences/**', async route => {
      if (route.request().method() === 'PATCH') {
        const body = route.request().postDataJSON() as { mobile_nav?: string[] }
        if (body.mobile_nav) saved = body.mobile_nav
      }
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({ tab_order: {}, mobile_nav: saved ?? [], sidebar_collapsed: true }),
      })
    })

    await page.goto('/hub')
    await page.getByRole('button', { name: 'More navigation and profile options' }).click()
    await page.getByRole('button', { name: 'Customise navigation' }).click()
    await page.getByLabel('Choose shortcut for Slot 1').selectOption('pets')
    await expect.poll(() => saved).toContain('pets')
  })
})
