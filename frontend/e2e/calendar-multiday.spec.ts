import { test, expect } from '@playwright/test'
import { mockAuthenticatedApi } from './fixtures/mockApi'
import { expectNoHorizontalOverflow } from './fixtures/assertions'

// Month view's TimeTree-style continuous event bars (v0.41). The bug this guards: a multi-day
// event used to render only on its start date, both because the backend range query only
// matched `start_at` inside the requested window and because the frontend grouped events by
// start date alone. These fixtures always span the turn of the month, so every assertion here
// is exercising the "the next month must still show an event that started in the previous one"
// path, not just the common case of an event short enough to need no month-view fix at all.

function baseEvent(overrides: Record<string, unknown> = {}) {
  return {
    id: 1, title: 'Road trip', event_kind: 'event', description: '',
    start_at: '', end_at: null, is_all_day: true, timezone: '', recurrence_rule: '',
    source_node: null, source_record_type: '', source_record_id: null,
    assigned_to_person_ids: [], colour: '#2563eb', location: '', provider: '', contact: '',
    visibility: 'household', sensitivity: 'normal', is_synced: false,
    is_source_managed: false, calendar_source_id: null, calendar_source_name: '',
    calendar_source_category: '', is_range: false,
    created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

const isoDate = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).toISOString()
const localDateKey = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

/** A span that always crosses a month boundary, whatever day the suite happens to run on:
 *  the 25th of the current month through the 20th of the next — roughly four week rows. */
function crossMonthSpan() {
  const now = new Date()
  const start = new Date(now.getFullYear(), now.getMonth(), 25)
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 20)
  return { start, end, startIso: isoDate(start), endIso: isoDate(end) }
}

function fixturesFor(events: unknown[], rotations: unknown[] = []) {
  return {
    '/api/v1/calendar/events/': events,
    '/api/v1/calendar/rotations/': [],
    '/api/v1/calendar/rotation-occurrences/': rotations,
    '/api/v1/atlas/birthday-occurrences/': [],
    '/api/v1/people/': [],
  }
}

test.describe('phone month view', () => {
  test.beforeEach(async ({}, testInfo) => {
    test.skip(testInfo.project.name === 'tablet-768', 'phone-only: desktop is covered separately below')
  })

  test('a long event renders as a bar across every week it touches, including the next month', async ({ page }) => {
    const { start, end, startIso, endIso } = crossMonthSpan()
    await mockAuthenticatedApi(page, fixturesFor([baseEvent({ start_at: startIso, end_at: endIso })]))
    await page.goto('/calendar')
    await page.getByLabel('Calendar view').selectOption('month')

    const grid = page.locator('div.touch-pan-y')
    await expect(grid.getByText('Road trip', { exact: true }).first()).toBeVisible()
    await expectNoHorizontalOverflow(page)

    // Page to the month the event ends in. Its start_at is in the *previous* month, so this is
    // exactly the regression: the event must still come back from the API and still render.
    await page.getByRole('button', { name: 'Next period' }).click()
    await expect(page.locator('[data-calendar-period-label]')).toHaveText(
      end.toLocaleDateString(undefined, { month: 'long', year: 'numeric' }),
    )
    await expect(grid.getByText('Road trip', { exact: true }).first()).toBeVisible()

    // And the month it actually started in still shows it too.
    await page.getByRole('button', { name: 'Previous period' }).click()
    await expect(page.locator('[data-calendar-period-label]')).toHaveText(
      start.toLocaleDateString(undefined, { month: 'long', year: 'numeric' }),
    )
    await expect(grid.getByText('Road trip', { exact: true }).first()).toBeVisible()
  })

  test('clicking a bar segment in a later week opens the same underlying event', async ({ page }) => {
    const { endIso, startIso } = crossMonthSpan()
    await mockAuthenticatedApi(page, fixturesFor([baseEvent({ start_at: startIso, end_at: endIso })]))
    await page.goto('/calendar')
    await page.getByLabel('Calendar view').selectOption('month')
    await page.getByRole('button', { name: 'Next period' }).click()

    await page.locator('div.touch-pan-y').getByText('Road trip', { exact: true }).first().click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expect(dialog.getByPlaceholder('Title')).toHaveValue('Road trip')
  })

  test('overlapping multi-day events each get their own lane, and a rotation schedule can overlap them too', async ({ page }) => {
    const { startIso, endIso } = crossMonthSpan()
    const second = baseEvent({
      id: 2, title: 'House sitting', colour: '#16a34a',
      start_at: startIso, end_at: endIso,
    })
    const start = new Date(startIso)
    const rotationOccurrences = Array.from({ length: 10 }, (_, i) => {
      const d = new Date(start); d.setDate(start.getDate() + i)
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
      return {
        id: `rotation-1-${key}`, schedule_id: 1, schedule_title: 'Kids', date: key,
        state: 'primary', planned_state: 'primary', label: 'With us', colour: '#8A718E',
        is_override: false, note: '', person_ids: [],
      }
    })
    await mockAuthenticatedApi(page, fixturesFor([
      baseEvent({ start_at: startIso, end_at: endIso }), second,
    ], rotationOccurrences))
    await page.goto('/calendar')
    await page.getByLabel('Calendar view').selectOption('month')

    const grid = page.locator('div.touch-pan-y')
    await expect(grid.getByText('Road trip', { exact: true }).first()).toBeVisible()
    await expect(grid.getByText('House sitting', { exact: true }).first()).toBeVisible()
    await expect(grid.getByText('With us', { exact: true }).first()).toBeVisible()
    await expectNoHorizontalOverflow(page)
  })
})

test.describe('desktop month view', () => {
  test.beforeEach(async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'tablet-768', 'desktop widths are driven by test.use() below')
  })

  async function expectBarsDoNotOverlap(page: import('@playwright/test').Page, titles: string[]) {
    const boxes = await Promise.all(titles.map(async title => {
      const box = await page.locator('[data-calendar-grid]').getByText(title, { exact: true }).first().boundingBox()
      expect(box, `${title} should have a visible bar`).not.toBeNull()
      return box!
    }))
    for (let i = 0; i < boxes.length; i += 1) {
      for (let j = i + 1; j < boxes.length; j += 1) {
        const a = boxes[i], b = boxes[j]
        const overlap = a.x < b.x + b.width - 1 && b.x < a.x + a.width - 1
          && a.y < b.y + b.height - 1 && b.y < a.y + a.height - 1
        expect(overlap, `${titles[i]} and ${titles[j]} bars overlap`).toBe(false)
      }
    }
  }

  test.describe('medium / split-screen desktop', () => {
    test.use({ viewport: { width: 960, height: 900 } })

    test('a cross-month event renders without overflow and the next month still shows it', async ({ page }) => {
      const { end, endIso, startIso } = crossMonthSpan()
      await mockAuthenticatedApi(page, fixturesFor([baseEvent({ start_at: startIso, end_at: endIso })]))
      await page.goto('/calendar')
      await expect(page.locator('[data-calendar-grid]').getByText('Road trip', { exact: true }).first()).toBeVisible()
      await page.getByRole('button', { name: 'Next period' }).click()
      await expect(page.locator('[data-calendar-period-label]')).toHaveText(
        end.toLocaleDateString(undefined, { month: 'long', year: 'numeric' }),
      )
      await expect(page.locator('[data-calendar-grid]').getByText('Road trip', { exact: true }).first()).toBeVisible()
      await expectNoHorizontalOverflow(page)
    })

    test('overlapping events occupy separate, non-overlapping lanes', async ({ page }) => {
      const { startIso, endIso } = crossMonthSpan()
      await mockAuthenticatedApi(page, fixturesFor([
        baseEvent({ start_at: startIso, end_at: endIso }),
        baseEvent({ id: 2, title: 'House sitting', colour: '#16a34a', start_at: startIso, end_at: endIso }),
      ]))
      await page.goto('/calendar')
      await expectBarsDoNotOverlap(page, ['Road trip', 'House sitting'])
    })

    test('clicking a bar opens its event, not the day view', async ({ page }) => {
      const { startIso, endIso } = crossMonthSpan()
      await mockAuthenticatedApi(page, fixturesFor([baseEvent({ start_at: startIso, end_at: endIso })]))
      await page.goto('/calendar')
      await page.locator('[data-calendar-grid]').getByText('Road trip', { exact: true }).first().click()
      await expect(page.getByRole('dialog')).toBeVisible()
      await expect(page.getByRole('dialog').getByPlaceholder('Title')).toHaveValue('Road trip')
    })
  })

  test.describe('wide desktop', () => {
    test.use({ viewport: { width: 1600, height: 900 } })

    test('a cross-month event renders without overflow', async ({ page }) => {
      const { startIso, endIso } = crossMonthSpan()
      await mockAuthenticatedApi(page, fixturesFor([baseEvent({ start_at: startIso, end_at: endIso })]))
      await page.goto('/calendar')
      await expect(page.locator('[data-calendar-grid]').getByText('Road trip', { exact: true }).first()).toBeVisible()
      await expectNoHorizontalOverflow(page)
    })
  })
})

test.describe('agenda and day views show the event range, not a duplicated run', () => {
  test.beforeEach(async ({}, testInfo) => {
    test.skip(testInfo.project.name === 'tablet-768', 'view switching here goes through the phone-only select; desktop is covered above')
  })

  test('Agenda shows one row with a visible date range', async ({ page }) => {
    const { startIso, endIso } = crossMonthSpan()
    await mockAuthenticatedApi(page, fixturesFor([baseEvent({ start_at: startIso, end_at: endIso })]))
    await page.goto('/calendar')
    await page.getByLabel('Calendar view').selectOption('agenda')
    const rows = page.getByText('Road trip', { exact: true })
    await expect(rows).toHaveCount(1)
    await expect(page.getByText(/–/)).toBeVisible()
  })

  test('Day view shows the event as ongoing on a day after it started', async ({ page }) => {
    const { start, endIso } = crossMonthSpan()
    const dayAfterStart = new Date(start); dayAfterStart.setDate(start.getDate() + 2)
    await mockAuthenticatedApi(page, fixturesFor([baseEvent({ start_at: isoDate(start), end_at: endIso })]))
    await page.goto(`/calendar?date=${localDateKey(dayAfterStart)}`)
    await expect(page.getByText('Road trip')).toBeVisible()
    await expect(page.getByText(/ongoing/)).toBeVisible()
  })
})
