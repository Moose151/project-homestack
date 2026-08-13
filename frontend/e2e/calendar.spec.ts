import { test, expect } from '@playwright/test'
import { mockAuthenticatedApi } from './fixtures/mockApi'
import { expectNoHorizontalOverflow } from './fixtures/assertions'

// Calendar is docs/36 Phase 4's reference implementation: date navigation, sheets, full-screen
// editors, floating/sticky actions, mobile view switching and source deep links all get
// established here first, then reused elsewhere.

function todayEvent() {
  const now = new Date()
  const iso = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 10, 0).toISOString()
  return {
    id: 1, title: 'Dentist', event_kind: 'appointment', description: '',
    start_at: iso, end_at: null, is_all_day: false, timezone: '', recurrence_rule: '',
    source_node: null, source_record_type: '', source_record_id: null,
    assigned_to_person_ids: [], colour: '', location: '', provider: '', contact: '',
    visibility: 'household', sensitivity: 'normal', is_synced: false,
    created_at: iso, updated_at: iso,
  }
}

test.beforeEach(async ({ page }) => {
  await mockAuthenticatedApi(page, {
    '/api/v1/calendar/events/': [todayEvent()],
    '/api/v1/calendar/rotations/': [],
    '/api/v1/calendar/rotation-occurrences/': [],
    '/api/v1/atlas/birthday-occurrences/': [],
    '/api/v1/people/': [],
  })
})

test.describe('phone', () => {
  test.beforeEach(async ({}, testInfo) => {
    test.skip(testInfo.project.name === 'tablet-768', 'phone-only: this page splits mobile/desktop at its own sm: breakpoint')
  })

  test('defaults to Agenda, not Month, with no stored preference', async ({ page }) => {
    await page.goto('/calendar')
    await expect(page.getByLabel('Calendar view')).toHaveValue('agenda')
    await expect(page.getByText('Dentist')).toBeVisible()
    await expectNoHorizontalOverflow(page)
  })

  test('Month cells show a dot, not a truncated title, and open a day sheet', async ({ page }) => {
    await page.goto('/calendar')
    await page.getByLabel('Calendar view').selectOption('month')
    // The fixture event's title must not leak into the (illegible) month cell itself — it's
    // meant only for the sheet opened by tapping the day (docs/36 §6.2: "Month is for
    // orientation, not full event content").
    await expect(page.locator('div.touch-pan-y').getByText('Dentist', { exact: true })).toHaveCount(0)
    await page.locator('div.touch-pan-y button').first().click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expectNoHorizontalOverflow(page)
  })

  test('Week view is a horizontal day strip plus the selected day\'s agenda', async ({ page }) => {
    await page.goto('/calendar')
    await page.getByLabel('Calendar view').selectOption('week')
    const strip = page.locator('div.overflow-x-auto').first()
    await expect(strip.getByRole('button')).toHaveCount(7)
    await expectNoHorizontalOverflow(page)
  })

  test('opening an event uses a full-height sheet with a sticky Save', async ({ page }) => {
    await page.goto('/calendar')
    await page.getByText('Dentist').click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expect(page.getByRole('button', { name: 'Save' })).toBeVisible()
    await expectNoHorizontalOverflow(page)
    await page.getByRole('button', { name: 'Cancel' }).click()
    await expect(dialog).not.toBeVisible()
  })

  test('the floating Add button opens a new-event sheet without overflow', async ({ page }) => {
    await page.goto('/calendar')
    await page.getByRole('button', { name: /^Add event/ }).click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expect(page.getByPlaceholder('Title')).toBeVisible()
    await expectNoHorizontalOverflow(page)
  })
})
