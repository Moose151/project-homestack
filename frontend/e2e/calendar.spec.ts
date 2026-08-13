import { test, expect } from '@playwright/test'
import { mockAuthenticatedApi } from './fixtures/mockApi'
import { expectNoHorizontalOverflow, expectMinTouchTarget } from './fixtures/assertions'

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

// A day guaranteed to fall in the *same* Mon-start week as today (the fixture household's
// calendar_week_start) and never equal to today itself — a literal "tomorrow" can silently
// land in next week's strip when the suite happens to run on a Sunday, which would make any
// test built on it flaky depending on the day it's run.
function otherDayInCurrentWeek(): Date {
  const today = new Date(new Date().getFullYear(), new Date().getMonth(), new Date().getDate())
  const mondayDiff = (today.getDay() - 1 + 7) % 7
  const monday = new Date(today); monday.setDate(today.getDate() - mondayDiff)
  if (monday.getTime() === today.getTime()) { const tuesday = new Date(monday); tuesday.setDate(monday.getDate() + 1); return tuesday }
  return monday
}
const dateKey = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

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

  test('Agenda hides Previous/Next/Today since they cannot page its fixed 60-day window', async ({ page }) => {
    await page.goto('/calendar')
    await expect(page.getByLabel('Calendar view')).toHaveValue('agenda')
    await expect(page.getByRole('button', { name: 'Previous period' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Next period' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Today' })).toHaveCount(0)
    await expect(page.getByText('Upcoming')).toBeVisible()
  })

  test('Month cells show a dot, not a truncated title, and tapping the actual event day opens it in the day sheet', async ({ page }) => {
    await page.goto('/calendar')
    await page.getByLabel('Calendar view').selectOption('month')
    // The fixture event's title must not leak into the (illegible) month cell itself — it's
    // meant only for the sheet opened by tapping the day (docs/36 §6.2: "Month is for
    // orientation, not full event content").
    await expect(page.locator('div.touch-pan-y').getByText('Dentist', { exact: true })).toHaveCount(0)
    // The one fixture event lives on today, so today's cell — and only today's cell — carries
    // a ", 1 events" suffix in its aria-label; tap that specific cell, not just "the first one".
    await page.getByRole('button', { name: /1 events$/ }).click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expect(dialog.getByText('Dentist')).toBeVisible()
    await expectNoHorizontalOverflow(page)
  })

  test('Week view is a horizontal day strip plus the selected day\'s agenda, with a heading for the selected day', async ({ page }) => {
    await page.goto('/calendar')
    await page.getByLabel('Calendar view').selectOption('week')
    const strip = page.locator('div.overflow-x-auto').first()
    await expect(strip.getByRole('button')).toHaveCount(7)
    await expectNoHorizontalOverflow(page)
  })

  test('tapping a different day in the Week strip changes the agenda and its heading', async ({ page }) => {
    const target = otherDayInCurrentWeek()
    const targetIso = new Date(target.getFullYear(), target.getMonth(), target.getDate(), 14, 0).toISOString()
    await mockAuthenticatedApi(page, {
      '/api/v1/calendar/events/': [todayEvent(), { ...todayEvent(), id: 2, title: 'Piano lesson', start_at: targetIso }],
      '/api/v1/calendar/rotations/': [],
      '/api/v1/calendar/rotation-occurrences/': [],
      '/api/v1/atlas/birthday-occurrences/': [],
      '/api/v1/people/': [],
    })
    await page.goto('/calendar')
    await page.getByLabel('Calendar view').selectOption('week')
    // The desktop 7-col grid renders in the DOM at every viewport (just CSS-hidden below sm:),
    // so text assertions must stay scoped to the phone day-strip's own wrapper or they collide
    // with its always-present copy of the same event titles.
    const strip = page.locator('div.overflow-x-auto').first()
    const mobileWeek = strip.locator('..')
    await expect(mobileWeek.getByText('Dentist')).toBeVisible()
    await expect(mobileWeek.getByText('Piano lesson')).toHaveCount(0)

    await strip.getByText(String(target.getDate()), { exact: true }).click()

    await expect(mobileWeek.getByText('Piano lesson')).toBeVisible()
    await expect(mobileWeek.getByText('Dentist')).toHaveCount(0)
    await expect(mobileWeek.locator('h2').filter({ hasText: String(target.getDate()) })).toBeVisible()
  })

  test('the floating Add button creates against the selected day in Week view, not always today', async ({ page }) => {
    const target = otherDayInCurrentWeek()
    await page.goto('/calendar')
    await page.getByLabel('Calendar view').selectOption('week')
    const strip = page.locator('div.overflow-x-auto').first()
    await strip.getByText(String(target.getDate()), { exact: true }).click()
    await page.getByRole('button', { name: /^Add event/ }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await expect(page.getByLabel('Date')).toHaveValue(dateKey(target))
  })

  test('opening an event uses a full-height sheet with a sticky Save, and the title field is focused', async ({ page }) => {
    await page.goto('/calendar')
    await page.getByText('Dentist').click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expect(page.getByRole('button', { name: 'Save' })).toBeVisible()
    await expectNoHorizontalOverflow(page)
    await page.getByRole('button', { name: 'Cancel' }).click()
    await expect(dialog).not.toBeVisible()
  })

  test('the Event title field reliably receives focus when the sheet opens, not the first form control', async ({ page }) => {
    await page.goto('/calendar')
    await page.getByRole('button', { name: /^Add event/ }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await expect(page.getByPlaceholder('Title')).toBeFocused()
  })

  test('the full-height event editor remains usable after scrolling to reveal more options', async ({ page }) => {
    await page.goto('/calendar')
    await page.getByText('Dentist').click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await page.getByRole('button', { name: '▾ More options' }).click()
    await dialog.locator('> div').evaluate(el => el.scrollTo(0, el.scrollHeight))
    await page.getByPlaceholder('Title').fill('Dentist (updated)')
    await expect(page.getByPlaceholder('Title')).toHaveValue('Dentist (updated)')
    await expect(page.getByRole('button', { name: 'Save' })).toBeEnabled()
    await page.getByRole('button', { name: 'Save' }).click()
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

  test('a source-owned event opens as a read-only summary with a working deep link', async ({ page }) => {
    const now = new Date()
    const iso = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 9, 0).toISOString()
    await mockAuthenticatedApi(page, {
      '/api/v1/calendar/events/': [{
        ...todayEvent(), id: 3, title: 'Roof gutter clearing', start_at: iso,
        source_node: 'homestead', source_record_type: 'MaintenanceTask', source_record_id: 42, is_synced: true,
      }],
      '/api/v1/calendar/rotations/': [],
      '/api/v1/calendar/rotation-occurrences/': [],
      '/api/v1/atlas/birthday-occurrences/': [],
      '/api/v1/people/': [],
    })
    await page.goto('/calendar')
    await page.getByText('Roof gutter clearing').click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expect(dialog.getByText(/comes from/)).toBeVisible()
    const link = dialog.getByRole('link', { name: /Open the source record/ })
    await expect(link).toHaveAttribute('href', '/homestead?tab=maintenance&q=Roof%20gutter%20clearing')
    await expectMinTouchTarget(link)
  })

  test('"My events only" matches by person ID, not by array reference', async ({ page }) => {
    const now = new Date()
    const iso = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 9, 0).toISOString()
    await mockAuthenticatedApi(page, {
      '/api/v1/calendar/events/': [
        { ...todayEvent(), id: 4, title: 'My dentist', start_at: iso, assigned_to_person_ids: [1] },
        { ...todayEvent(), id: 5, title: 'Partner dentist', start_at: iso, assigned_to_person_ids: [2] },
      ],
      '/api/v1/calendar/rotations/': [],
      '/api/v1/calendar/rotation-occurrences/': [],
      '/api/v1/atlas/birthday-occurrences/': [],
      // person id 1 is linked to the fixture user (id 1) — this is "me".
      '/api/v1/people/': [
        { id: 1, display_name: 'Test User', preferred_name: 'Test User', avatar: '', colour: '', profile_type: 'adult', linked_user_id: 1, date_of_birth: null },
        { id: 2, display_name: 'Partner', preferred_name: 'Partner', avatar: '', colour: '', profile_type: 'adult', linked_user_id: null, date_of_birth: null },
      ],
    })
    await page.goto('/calendar')
    await expect(page.getByText('My dentist')).toBeVisible()
    await expect(page.getByText('Partner dentist')).toBeVisible()

    await page.getByRole('button', { name: 'Filter' }).click()
    await page.getByRole('button', { name: /My events only/ }).click()

    await expect(page.getByText('My dentist')).toBeVisible()
    await expect(page.getByText('Partner dentist')).toHaveCount(0)
  })

  test('Calendar controls meet the 44px touch-target baseline', async ({ page }) => {
    await page.goto('/calendar')
    await page.getByLabel('Calendar view').selectOption('day')
    await expectMinTouchTarget(page.getByRole('button', { name: 'Previous period' }))
    await expectMinTouchTarget(page.getByRole('button', { name: 'Next period' }))
    await expectMinTouchTarget(page.getByRole('button', { name: 'Today' }))
    await expectMinTouchTarget(page.getByRole('button', { name: 'Filter' }))
    await expectMinTouchTarget(page.getByPlaceholder('Try “Dentist 3pm”'))
    await page.getByText('Dentist').click()
    await expectMinTouchTarget(page.getByRole('button', { name: 'Cancel' }))
    await expectMinTouchTarget(page.getByRole('button', { name: 'Save' }))
  })
})
