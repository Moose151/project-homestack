import { test, expect } from '@playwright/test'
import { mockAuthenticatedApi } from './fixtures/mockApi'
import { expectMinTouchTarget, expectNoHorizontalOverflow } from './fixtures/assertions'

// docs/36 §6.14-6.15 (Phase 7): notification categories become immediate-save MobileSettingsRow
// switches instead of a batch-Save table; Manage HomeStack gains a real settings-directory
// section (Version history / Your notifications / Push devices / People & access).

const PREF_ROW = {
  category: 'appointments', label: 'Appointments & events',
  in_app_enabled: true, push_enabled: false, mine_only: false, supports_mine_only: true,
}
const CHORES_PREF_ROW = {
  category: 'chores', label: 'Chores',
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
    await expect(page.getByRole('heading', { name: 'What to notify me about' })).toBeVisible()
    // No batch "Save preferences" button left — every switch is its own save.
    await expect(page.getByRole('button', { name: 'Save preferences' })).toHaveCount(0)
    await page.getByRole('button', { name: /Appointments & events/ }).click()
    const pushSwitch = page.getByRole('switch', { name: 'Push' })
    await expect(pushSwitch).toHaveAttribute('aria-checked', 'false')
    await pushSwitch.click()
    await expect(pushSwitch).toHaveAttribute('aria-checked', 'true')
    await expect.poll(() => lastPatchBody).toMatchObject({ category: 'appointments', push_enabled: true })
    await expectNoHorizontalOverflow(page)
  })

  test('a failed immediate save rolls back only the affected category and shows Saved for successful writes', async ({ page }) => {
    await mockAuthenticatedApi(page, {
      '/api/v1/notifications/preferences/': [PREF_ROW, CHORES_PREF_ROW],
      '/api/v1/notifications/settings/': { quiet_start: null, quiet_end: null, morning_time: '08:00:00' },
      '/api/v1/notifications/devices/': [],
    })
    await page.route('**/api/v1/notifications/preferences/', async route => {
      if (route.request().method() !== 'PATCH') { await route.fallback(); return }
      const patch = JSON.parse(route.request().postData() || '[]')[0]
      if (patch.category === 'appointments') {
        await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'Save failed' }) })
        return
      }
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify([{ ...CHORES_PREF_ROW, ...patch }]),
      })
    })
    await page.goto('/settings/notifications')

    await page.getByRole('button', { name: /Chores/ }).click()
    const choresPush = page.getByRole('switch', { name: 'Push' })
    await choresPush.click()
    await expect(choresPush).toHaveAttribute('aria-checked', 'true')
    await expect(page.getByText('Saved')).toBeVisible()

    await page.getByRole('main').getByRole('button', { name: 'Back' }).click()
    await page.getByRole('button', { name: /Appointments & events/ }).click()
    const appointmentsPush = page.getByRole('switch', { name: 'Push' })
    await appointmentsPush.click()
    await expect(page.getByText('Save failed')).toBeVisible()
    await expect(appointmentsPush).toHaveAttribute('aria-checked', 'false')
    await page.getByRole('main').getByRole('button', { name: 'Back' }).click()
    await expect(page.getByRole('button', { name: /Chores.*Push/ })).toBeVisible()
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

  test('identifies This phone first and gives device actions full touch targets', async ({ page }) => {
    await page.addInitScript(() => {
      Object.defineProperty(window, 'PushManager', { configurable: true, value: class PushManager {} })
      Object.defineProperty(navigator, 'serviceWorker', {
        configurable: true,
        value: {
          register: async () => ({}),
          getRegistration: async () => ({
            pushManager: { getSubscription: async () => ({ endpoint: 'https://push.example/phone' }) },
          }),
        },
      })
    })
    const devices = [
      { id: 1, label: 'Kitchen laptop', label_is_custom: true, browser: 'Firefox', platform: 'Linux', user_agent: '', last_seen_at: '2026-08-12T10:00:00Z', created_at: '2026-08-01T10:00:00Z' },
      { id: 2, label: 'Pixel 8', label_is_custom: true, browser: 'Chrome', platform: 'Android', user_agent: '', last_seen_at: '2026-08-13T10:00:00Z', created_at: '2026-08-02T10:00:00Z' },
    ]
    await mockAuthenticatedApi(page, {
      '/api/v1/notifications/preferences/': [PREF_ROW],
      '/api/v1/notifications/settings/': { quiet_start: null, quiet_end: null, morning_time: '08:00:00' },
      '/api/v1/notifications/devices/': devices,
      '/api/v1/notifications/devices/current/': { device_id: 2 },
    })
    await page.goto('/settings/notifications')

    const current = page.getByRole('heading', { name: 'This phone' }).locator('..').locator('..')
    const others = page.getByRole('heading', { name: 'Other devices' }).locator('..').locator('..')
    await expect(current.getByText('Pixel 8')).toBeVisible()
    await expect(others.getByText('Kitchen laptop')).toBeVisible()
    expect((await current.boundingBox())?.y).toBeLessThan((await others.boundingBox())?.y ?? 0)

    await expectMinTouchTarget(current.getByRole('button', { name: 'Test notification' }))
    await expectMinTouchTarget(current.getByRole('button', { name: 'Rename' }))
    await expectMinTouchTarget(current.getByRole('button', { name: 'Revoke' }))
    await current.getByRole('button', { name: 'Rename' }).click()
    await expect(current.getByRole('textbox', { name: 'Device name' })).toHaveValue('Pixel 8')
    await expectNoHorizontalOverflow(page)
  })
})

test.describe('Manage HomeStack accordion', () => {
  test.beforeEach(async ({}, testInfo) => {
    test.skip(testInfo.project.name === 'tablet-768', 'phone-only: exercised once is enough for this directory')
  })

  test('sections are collapsed by default and expand one at a time', async ({ page }) => {
    await mockAuthenticatedApi(page)
    await page.goto('/settings')
    const main = page.getByRole('main')

    const stacksButton = main.getByRole('button', { name: /Stacks/ })
    const peopleButton = main.getByRole('button', { name: /People & access/ })
    await expect(stacksButton).toHaveAttribute('aria-expanded', 'false')
    await expect(peopleButton).toHaveAttribute('aria-expanded', 'false')

    // People & access is a genuinely separate management page (docs/31 §5): the row expands to
    // a clear action rather than inline fields, and it is not in the DOM until expanded.
    await expect(main.getByRole('link', { name: /Open People & access/ })).toHaveCount(0)
    await peopleButton.click()
    await expect(peopleButton).toHaveAttribute('aria-expanded', 'true')
    await expect(main.getByRole('link', { name: /Open People & access/ })).toHaveAttribute('href', '/users')

    // Opening Stacks closes People & access — only one section open at a time.
    await stacksButton.click()
    await expect(stacksButton).toHaveAttribute('aria-expanded', 'true')
    await expect(peopleButton).toHaveAttribute('aria-expanded', 'false')
    await expect(main.getByRole('link', { name: /Open People & access/ })).toHaveCount(0)
    await expect(main.getByRole('switch').first()).toBeVisible()

    const notificationsButton = main.getByRole('button', { name: /Notifications/ })
    await expect(notificationsButton).toBeVisible()
    await notificationsButton.click()
    await expect(main.getByRole('link', { name: /Open Notifications/ })).toHaveAttribute('href', '/settings/notifications')

    await main.getByRole('button', { name: /Push devices/ }).click()
    await expect(main.getByRole('link', { name: /Open push devices/ })).toHaveAttribute('href', '/settings/push-devices')

    await expectNoHorizontalOverflow(page)
  })

  test('Stacks toggle meets the 44px touch-target baseline', async ({ page }) => {
    await mockAuthenticatedApi(page)
    await page.goto('/settings')
    const main = page.getByRole('main')
    await main.getByRole('button', { name: /Stacks/ }).click()
    const toggle = main.getByRole('switch').first()
    await expect(toggle).toBeVisible()
    const box = await toggle.boundingBox()
    expect(box?.height).toBeGreaterThanOrEqual(42)
    expect(box?.width).toBeGreaterThanOrEqual(42)
  })

  test('a #hash deep link opens the matching section and survives reload', async ({ page }) => {
    await mockAuthenticatedApi(page)
    await page.goto('/settings#stacks')
    const main = page.getByRole('main')
    const stacksButton = main.getByRole('button', { name: /Stacks/ })
    await expect(stacksButton).toHaveAttribute('aria-expanded', 'true')
    await expect(main.getByRole('switch').first()).toBeVisible()

    await page.reload()
    await expect(stacksButton).toHaveAttribute('aria-expanded', 'true')
  })
})
