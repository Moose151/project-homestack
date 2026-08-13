import { test, expect } from '@playwright/test'
import { mockAuthenticatedApi } from './fixtures/mockApi'
import { expectNoHorizontalOverflow } from './fixtures/assertions'

// docs/36 §6.14-6.15 (Phase 7): notification categories become immediate-save MobileSettingsRow
// switches instead of a batch-Save table; Manage HomeStack gains a real settings-directory
// section (Version history / Your notifications / Push devices / People & access).

const PREF_ROW = {
  category: 'appointments', label: 'Appointments & events',
  in_app_enabled: true, push_enabled: false, mine_only: false, supports_mine_only: true,
}

test.describe('Notification settings', () => {
  test.beforeEach(async ({}, testInfo) => {
    test.skip(testInfo.project.name === 'tablet-768', 'phone-only: this is the primary surface these switches were built for')
  })

  test('a category toggle saves immediately, no page-level Save button', async ({ page }) => {
    let lastPatchBody: unknown = null
    await mockAuthenticatedApi(page, {
      '/api/v1/notifications/preferences/': [PREF_ROW],
      '/api/v1/notifications/settings/': { quiet_start: null, quiet_end: null, morning_time: '08:00:00' },
      '/api/v1/notifications/devices/': [],
    })
    await page.route('**/api/v1/notifications/preferences/', async route => {
      if (route.request().method() !== 'PATCH') { await route.fallback(); return }
      const patch = JSON.parse(route.request().postData() || '[]')[0]
      lastPatchBody = patch
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify([{ ...PREF_ROW, ...patch }]),
      })
    })
    await page.goto('/settings/notifications')
    await expect(page.getByRole('heading', { name: 'Appointments & events' })).toBeVisible()
    // No batch "Save preferences" button left — every switch is its own save.
    await expect(page.getByRole('button', { name: 'Save preferences' })).toHaveCount(0)
    const pushSwitch = page.getByRole('switch', { name: 'Push' })
    await expect(pushSwitch).toHaveAttribute('aria-checked', 'false')
    await pushSwitch.click()
    await expect(pushSwitch).toHaveAttribute('aria-checked', 'true')
    await expect.poll(() => lastPatchBody).toMatchObject({ category: 'appointments', push_enabled: true })
    await expectNoHorizontalOverflow(page)
  })

  test('quiet hours keeps an explicit Save (a coherent multi-field record)', async ({ page }) => {
    await mockAuthenticatedApi(page, {
      '/api/v1/notifications/preferences/': [PREF_ROW],
      '/api/v1/notifications/settings/': { quiet_start: null, quiet_end: null, morning_time: '08:00:00' },
      '/api/v1/notifications/devices/': [],
    })
    await page.goto('/settings/notifications')
    await expect(page.getByRole('heading', { name: 'Quiet hours' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Save' })).toBeVisible()
  })
})

test.describe('Manage HomeStack directory', () => {
  test.beforeEach(async ({}, testInfo) => {
    test.skip(testInfo.project.name === 'tablet-768', 'phone-only: MobileListRow is this page\'s new addition')
  })

  test('lists People & access, notifications, push devices and version history as destinations', async ({ page }) => {
    await mockAuthenticatedApi(page)
    await page.goto('/settings')
    await expect(page.getByRole('link', { name: /People & access/ })).toHaveAttribute('href', '/users')
    await expect(page.getByRole('link', { name: /Your notifications/ })).toHaveAttribute('href', '/settings/notifications')
    await expect(page.getByRole('link', { name: /Push devices/ })).toHaveAttribute('href', '/settings/push-devices')
    await expect(page.getByRole('link', { name: /Version history/ })).toHaveAttribute('href', '/settings/version-history')
    await expectNoHorizontalOverflow(page)
  })

  test('Stacks toggle meets the 44px touch-target baseline', async ({ page }) => {
    await mockAuthenticatedApi(page)
    await page.goto('/settings')
    const toggle = page.getByRole('switch').first()
    await expect(toggle).toBeVisible()
    const box = await toggle.boundingBox()
    expect(box?.height).toBeGreaterThanOrEqual(42)
    expect(box?.width).toBeGreaterThanOrEqual(42)
  })
})
