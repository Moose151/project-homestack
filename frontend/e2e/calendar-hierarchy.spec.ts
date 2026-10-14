import { test, expect } from '@playwright/test'
import { mockAuthenticatedApi } from './fixtures/mockApi'
import { expectNoHorizontalOverflow } from './fixtures/assertions'

// Month view's presentation hierarchy (v0.41.1): a household event like "Nick US" must read as
// the most important thing on the grid, while a school term ("Term 4") is reduced to small
// start/end markers instead of a saturated multi-week bar, a school holiday range is shown but
// visually quiet, and bills/tasks render compactly with their redundant "Bill: " prefix hidden.
// Classification is semantic (event_kind / source_node / calendar_source_kind) — never a title
// match — see src/lib/calendarPresentation.ts.

function baseEvent(overrides: Record<string, unknown> = {}) {
  return {
    id: 1, title: 'Event', event_kind: 'event', description: '',
    start_at: '', end_at: null, is_all_day: true, timezone: '', recurrence_rule: '',
    source_node: null, source_record_type: '', source_record_id: null,
    assigned_to_person_ids: [], colour: '#2563eb', location: '', provider: '', contact: '',
    visibility: 'household', sensitivity: 'normal', is_synced: false,
    is_source_managed: false, calendar_source_id: null, calendar_source_name: '',
    calendar_source_category: '', calendar_source_kind: '', is_range: false,
    created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

const isoDate = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).toISOString()

/** A term/holiday/trip combination anchored to the current month, so the suite is never
 *  date-dependent on when it happens to run. */
function fixtures() {
  const now = new Date()
  const termStart = new Date(now.getFullYear(), now.getMonth(), 6)
  const termEnd = new Date(now.getFullYear(), now.getMonth() + 2, 11)
  const holidayStart = new Date(now.getFullYear(), now.getMonth(), 1)
  const holidayEnd = new Date(now.getFullYear(), now.getMonth(), 5)
  const tripStart = new Date(now.getFullYear(), now.getMonth(), 23)
  const tripEnd = new Date(now.getFullYear(), now.getMonth() + 1, 15)

  const events = [
    baseEvent({ id: 1, title: 'Nick US', colour: '#2563eb', start_at: isoDate(tripStart), end_at: isoDate(tripEnd) }),
    baseEvent({
      id: 2, title: 'Term 4', colour: '#3b82f6', event_kind: 'event',
      start_at: isoDate(termStart), end_at: isoDate(termEnd),
      calendar_source_id: 10, calendar_source_name: 'Queensland State Schools', calendar_source_kind: 'school',
      is_source_managed: true,
    }),
    baseEvent({
      id: 3, title: 'School holidays', colour: '#60a5fa', event_kind: 'holiday',
      start_at: isoDate(holidayStart), end_at: isoDate(holidayEnd),
      calendar_source_id: 10, calendar_source_name: 'Queensland State Schools', calendar_source_kind: 'school',
      is_source_managed: true,
    }),
    baseEvent({
      id: 4, title: 'Bill: Berrina Registration', colour: '#287c68', source_node: 'solace',
      start_at: new Date(now.getFullYear(), now.getMonth(), 10, 9).toISOString(),
      is_synced: true, source_record_type: 'SolaceBill', source_record_id: 1,
    }),
    baseEvent({
      id: 5, title: 'Dentist', colour: '#dc2626', event_kind: 'appointment',
      start_at: new Date(now.getFullYear(), now.getMonth(), 14, 10).toISOString(),
    }),
  ]
  return { events, termStart, termEnd, holidayStart, holidayEnd, tripStart, tripEnd }
}

function apiFixtures(events: unknown[]) {
  return {
    '/api/v1/calendar/events/': events,
    '/api/v1/calendar/rotations/': [],
    '/api/v1/calendar/rotation-occurrences/': [],
    '/api/v1/atlas/birthday-occurrences/': [],
    '/api/v1/people/': [],
  }
}

test.describe('phone month view', () => {
  test.beforeEach(async ({}, testInfo) => {
    test.skip(testInfo.project.name === 'tablet-768', 'phone-only: desktop is covered separately below')
  })

  test('a school term shows start/end markers, not a multi-week bar, and the holiday range stays but reads quietly', async ({ page }) => {
    const { events } = fixtures()
    await mockAuthenticatedApi(page, apiFixtures(events))
    await page.goto('/calendar')
    await page.getByLabel('Calendar view').selectOption('month')

    const grid = page.locator('div.touch-pan-y')
    // The term never appears as a bare "Term 4" bar label — only as a "starts"/"ends" marker.
    await expect(grid.getByText('Term 4', { exact: true })).toHaveCount(0)
    await expect(grid.getByText('Term 4 starts')).toBeVisible()
    // The holiday range is still shown as a range (unlike the term).
    await expect(grid.getByText('School holidays', { exact: true }).first()).toBeVisible()
    await expectNoHorizontalOverflow(page)
  })

  test('a bill shows its name without the "Bill:" prefix in Month view, compactly', async ({ page }) => {
    const { events } = fixtures()
    await mockAuthenticatedApi(page, apiFixtures(events))
    await page.goto('/calendar')
    await page.getByLabel('Calendar view').selectOption('month')

    const grid = page.locator('div.touch-pan-y')
    await expect(grid.getByText('Berrina Registration', { exact: true })).toBeVisible()
    await expect(grid.getByText('Bill: Berrina Registration')).toHaveCount(0)
  })

  test('the full title (with "Bill:") is preserved in the event editor', async ({ page }) => {
    const { events } = fixtures()
    await mockAuthenticatedApi(page, apiFixtures(events))
    await page.goto('/calendar')
    await page.getByLabel('Calendar view').selectOption('month')
    await page.locator('div.touch-pan-y').getByText('Berrina Registration', { exact: true }).click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    // Bills come from a node record, so the dialog is the read-only source summary.
    await expect(dialog.getByText('Bill: Berrina Registration')).toBeVisible()
  })

  test('clicking the term milestone marker opens the correct underlying record', async ({ page }) => {
    const { events } = fixtures()
    await mockAuthenticatedApi(page, apiFixtures(events))
    await page.goto('/calendar')
    await page.getByLabel('Calendar view').selectOption('month')
    await page.locator('div.touch-pan-y').getByText('Term 4 starts').click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expect(dialog.getByText('Term 4')).toBeVisible()
  })

  test('the prominent trip is not pushed into "+N more" by lower-priority context/milestone entries', async ({ page }) => {
    const now = new Date()
    const tripStart = new Date(now.getFullYear(), now.getMonth(), 6)
    const tripEnd = new Date(now.getFullYear(), now.getMonth(), 9)
    // Three low-priority context/compact events overlapping the same days as the trip, on a
    // mobile cap of 2 lanes — the trip must still be visible; the overflow absorbs the rest.
    const events = [
      baseEvent({ id: 1, title: 'Family reunion', colour: '#2563eb', start_at: isoDate(tripStart), end_at: isoDate(tripEnd) }),
      baseEvent({
        id: 2, title: 'School holidays', colour: '#60a5fa', event_kind: 'holiday',
        start_at: isoDate(tripStart), end_at: isoDate(tripEnd),
        calendar_source_id: 10, calendar_source_name: 'School', calendar_source_kind: 'school',
      }),
      baseEvent({ id: 3, title: 'Bill: Power', colour: '#287c68', source_node: 'solace', start_at: new Date(now.getFullYear(), now.getMonth(), 7, 9).toISOString() }),
      baseEvent({ id: 4, title: 'Bill: Water', colour: '#287c68', source_node: 'solace', start_at: new Date(now.getFullYear(), now.getMonth(), 7, 10).toISOString() }),
    ]
    await mockAuthenticatedApi(page, apiFixtures(events))
    await page.goto('/calendar')
    await page.getByLabel('Calendar view').selectOption('month')

    const grid = page.locator('div.touch-pan-y')
    await expect(grid.getByText('Family reunion', { exact: true }).first()).toBeVisible()
    await expect(grid.getByText(/\+\d+ more/).first()).toBeVisible()
    await expectNoHorizontalOverflow(page)
  })
})

test.describe('desktop month view', () => {
  test.beforeEach(async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'tablet-768', 'desktop widths are driven by test.use() below')
  })

  test.describe('medium / split-screen desktop', () => {
    test.use({ viewport: { width: 960, height: 900 } })

    test('the term renders as markers, the trip remains a dominant bar, no overflow', async ({ page }) => {
      const { events } = fixtures()
      await mockAuthenticatedApi(page, apiFixtures(events))
      await page.goto('/calendar')
      const grid = page.locator('[data-calendar-grid]')
      await expect(grid.getByText('Term 4', { exact: true })).toHaveCount(0)
      await expect(grid.getByText('Term 4 starts')).toBeVisible()
      await expect(grid.getByText('Nick US', { exact: true }).first()).toBeVisible()
      await expectNoHorizontalOverflow(page)
    })
  })

  test.describe('wide desktop (screenshot reference width)', () => {
    test.use({ viewport: { width: 1600, height: 1000 } })

    test('the trip bar is visually taller than the context holiday range and the term marker', async ({ page }) => {
      const { events } = fixtures()
      await mockAuthenticatedApi(page, apiFixtures(events))
      await page.goto('/calendar')
      const grid = page.locator('[data-calendar-grid]')

      const tripBox = await grid.getByText('Nick US', { exact: true }).first().boundingBox()
      const holidayBox = await grid.getByText('School holidays', { exact: true }).first().boundingBox()
      const milestoneBox = await grid.getByText('Term 4 starts').boundingBox()
      expect(tripBox).not.toBeNull()
      expect(holidayBox).not.toBeNull()
      expect(milestoneBox).not.toBeNull()
      // "Prominent" bars are strictly taller than "context" bars, which are taller than the
      // single-row milestone marker's dot-and-text — the hierarchy the screenshot was missing.
      expect(tripBox!.height).toBeGreaterThan(holidayBox!.height)
      expect(holidayBox!.height).toBeGreaterThanOrEqual(milestoneBox!.height)
      await expectNoHorizontalOverflow(page)
    })

    test('no two bars in the same week overlap each other', async ({ page }) => {
      const now = new Date()
      const a = new Date(now.getFullYear(), now.getMonth(), 6)
      const b = new Date(now.getFullYear(), now.getMonth(), 9)
      const events = [
        baseEvent({ id: 1, title: 'Family reunion', colour: '#2563eb', start_at: isoDate(a), end_at: isoDate(b) }),
        baseEvent({
          id: 2, title: 'School holidays', colour: '#60a5fa', event_kind: 'holiday',
          start_at: isoDate(a), end_at: isoDate(b),
          calendar_source_id: 10, calendar_source_name: 'School', calendar_source_kind: 'school',
        }),
        baseEvent({ id: 3, title: 'Bill: Power', colour: '#287c68', source_node: 'solace', start_at: new Date(now.getFullYear(), now.getMonth(), 7, 9).toISOString() }),
      ]
      await mockAuthenticatedApi(page, apiFixtures(events))
      await page.goto('/calendar')
      const grid = page.locator('[data-calendar-grid]')
      const boxes = await Promise.all(
        ['Family reunion', 'School holidays', 'Power'].map(async title => {
          const box = await grid.getByText(title, { exact: true }).first().boundingBox()
          expect(box, `${title} should be visible`).not.toBeNull()
          return box!
        }),
      )
      for (let i = 0; i < boxes.length; i += 1) {
        for (let j = i + 1; j < boxes.length; j += 1) {
          const a2 = boxes[i], b2 = boxes[j]
          const overlap = a2.x < b2.x + b2.width - 1 && b2.x < a2.x + a2.width - 1
            && a2.y < b2.y + b2.height - 1 && b2.y < a2.y + a2.height - 1
          expect(overlap).toBe(false)
        }
      }
    })
  })
})

test.describe('dark mode', () => {
  test.beforeEach(async ({}, testInfo) => {
    test.skip(testInfo.project.name !== 'phone-dark', 'this assertion only needs to run once, under the dark-mode project')
  })

  test('presentation levels remain legible', async ({ page }) => {
    const { events } = fixtures()
    await mockAuthenticatedApi(page, apiFixtures(events))
    await page.goto('/calendar')
    await page.getByLabel('Calendar view').selectOption('month')
    const grid = page.locator('div.touch-pan-y')
    await expect(grid.getByText('Nick US', { exact: true }).first()).toBeVisible()
    await expect(grid.getByText('School holidays', { exact: true }).first()).toBeVisible()
    await expect(grid.getByText('Term 4 starts')).toBeVisible()
    await expect(grid.getByText('Berrina Registration', { exact: true })).toBeVisible()
  })
})
