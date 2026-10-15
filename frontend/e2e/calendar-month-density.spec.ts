import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import { mockAuthenticatedApi } from './fixtures/mockApi'
import { expectNoHorizontalOverflow } from './fixtures/assertions'

// Phone Month view must stay a month you can take in, not a page you scroll through.
//
// The regression this guards is not a style preference, it is a silent override. `index.css`
// puts a 44px `min-height` on every button under `(pointer: coarse)` — correct nearly
// everywhere, and fatal here, because a Month week row stacks a date, a rotation strip and up
// to two event lanes, each of which is a button. Every size in `MonthWeekRow`'s compact mode
// was therefore dead code on a phone: bars declared at 12–17px rendered at 44px, a week row
// measured 143px against the ~63px it was written for, and a six-week month came to 847px of
// grid inside a 1322px page — two phone screens to read one month.
//
// Nothing about that was visible to the suite. Every multi-day assertion in
// calendar-multiday.spec.ts passed throughout, because spanning, lanes and continuation were
// all correct; only the height was wrong, and no test measured height. So the assertions here
// are bounding boxes, and they are deliberately ceilings with headroom rather than pinned
// pixel counts: fonts differ between this machine and CI, and a test that fails on a 2px
// rendering difference gets deleted rather than read. A return to the 44px-floored layout
// misses these by more than double.

const isoDate = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).toISOString()
const dayKey = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

function baseEvent(overrides: Record<string, unknown> = {}) {
  return {
    id: 1, title: 'Event', event_kind: 'event', description: '',
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

/**
 * The month from the bug report, rebuilt so it lands the same way whatever day the suite runs:
 * a rotation on most days, a cross-month span (the 23rd through the 15th of next month, the
 * "Nick US" case), a span inside one week, and four ordinary single-day events — several of
 * them in the same week, so lanes and the "+N more" affordance are both exercised.
 */
function busyMonth() {
  const now = new Date()
  const Y = now.getFullYear()
  const M = now.getMonth()
  const events = [
    baseEvent({ id: 1, title: 'Nick US', colour: '#0b84a5',
      start_at: isoDate(new Date(Y, M, 23)), end_at: isoDate(new Date(Y, M + 1, 15)) }),
    baseEvent({ id: 2, title: 'School camp', colour: '#16a34a',
      start_at: isoDate(new Date(Y, M, 6)), end_at: isoDate(new Date(Y, M, 8)) }),
    ...['Dentist', 'Rebecca test', 'Assignment due', 'Emily turns nine'].map((title, i) =>
      baseEvent({ id: 10 + i, title, colour: '#c2683f', is_all_day: false,
        start_at: new Date(Y, M, [5, 9, 9, 28][i], 10, 0).toISOString() })),
  ]
  const rotations = Array.from({ length: 31 }, (_, i) => new Date(Y, M, i + 1))
    .filter(d => d.getMonth() === M && [0, 1, 4, 5, 6].includes(d.getDay()))
    .map(d => ({
      id: `rot-${dayKey(d)}`, schedule_id: 1, schedule_title: 'Kids', date: dayKey(d),
      state: 'primary', planned_state: 'primary', label: 'Us', colour: '#C9A227',
      is_override: false, note: '', person_ids: [],
    }))
  return {
    '/api/v1/calendar/events/': events,
    '/api/v1/calendar/rotations/': [{
      id: 1, title: 'Kids', is_active: true, primary_label: 'Us', primary_colour: '#C9A227',
      secondary_label: 'Kevin', secondary_colour: '#8A718E', cycle_length_days: 14,
      start_date: dayKey(new Date(Y, M, 1)),
    }],
    '/api/v1/calendar/rotation-occurrences/': rotations,
    '/api/v1/atlas/birthday-occurrences/': [],
    '/api/v1/people/': [],
  }
}

const monthGrid = (page: Page) => page.locator('div.touch-pan-y')
/** Week rows are the grid's children after the weekday header. */
const weekRows = (page: Page) => monthGrid(page).locator(':scope > div:not(:first-child)')

async function openPhoneMonth(page: Page) {
  await mockAuthenticatedApi(page, busyMonth())
  await page.goto('/calendar')
  await page.getByLabel('Calendar view').selectOption('month')
  await expect(monthGrid(page)).toBeVisible()
}

test.describe('phone Month stays compact', () => {
  test.beforeEach(async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'tablet-768', 'phone-only: desktop Month is roomier by design')
    await openPhoneMonth(page)
  })

  // The single most diagnostic number: one week row. 143px before, ~63px after, and the
  // ceiling sits between the two rather than near either.
  test('a week row carrying a rotation and two event lanes stays compact', async ({ page }) => {
    const rows = weekRows(page)
    await expect(rows.first()).toBeVisible()
    const heights: number[] = []
    for (const row of await rows.all()) {
      const box = await row.boundingBox()
      if (box) heights.push(box.height)
    }
    expect(heights.length, 'a month renders five or six week rows').toBeGreaterThanOrEqual(5)
    const tallest = Math.max(...heights)
    expect(
      tallest,
      `the tallest week row is ${Math.round(tallest)}px; with the 44px touch floor applied to `
      + 'every date, rotation chip and event bar it was 143px',
    ).toBeLessThan(90)
  })

  test('the whole month grid fits well inside one phone screen', async ({ page }) => {
    const box = (await monthGrid(page).boundingBox())!
    const viewport = page.viewportSize()!
    expect(
      box.height,
      `the month grid is ${Math.round(box.height)}px tall on a ${viewport.height}px screen; it was 847px`,
    ).toBeLessThan(viewport.height * 0.8)
  })

  // Controls and legends above the grid are what push the first week off the screen, so they
  // get their own ceiling: the grid being compact is no use behind 318px of chrome.
  test('the controls above the grid do not eat the screen', async ({ page }) => {
    const gridTop = (await monthGrid(page).boundingBox())!.y
    expect(
      gridTop,
      `${Math.round(gridTop)}px of header, toolbar and legend sit above the first date; it was 318px`,
    ).toBeLessThan(280)
  })

  test('reading one month costs far less than two screens of scrolling', async ({ page }) => {
    const viewport = page.viewportSize()!
    const docHeight = await page.evaluate(() => document.documentElement.scrollHeight)
    expect(
      docHeight / viewport.height,
      `the page is ${Math.round(docHeight)}px against a ${viewport.height}px screen; it was 1.99 screens`,
    ).toBeLessThan(1.45)
  })

  test('no horizontal overflow, and every bar stays inside the grid', async ({ page }) => {
    await expectNoHorizontalOverflow(page)
    const grid = (await monthGrid(page).boundingBox())!
    const bars = page.locator('div.touch-pan-y button[title]')
    const count = await bars.count()
    expect(count, 'the busy fixture renders event bars').toBeGreaterThan(0)
    for (const bar of await bars.all()) {
      const box = await bar.boundingBox()
      if (!box) continue
      expect(box.x).toBeGreaterThanOrEqual(grid.x - 1)
      expect(box.x + box.width).toBeLessThanOrEqual(grid.x + grid.width + 1)
    }
  })

  // Compactness must not cost the rotation its place: it is the thing the household reads the
  // month for, and it keeps its own row rather than competing for an event lane.
  test('the rotation strip survives the compaction and still opens its day', async ({ page }) => {
    const rotation = page.locator('div.touch-pan-y button', { hasText: 'Us' }).first()
    await expect(rotation).toBeVisible()
    const box = (await rotation.boundingBox())!
    expect(box.height, 'the rotation strip is a thin band, not a block').toBeLessThan(20)
    // Thin to look at, but not to hit: where the 44px floor applies, the exemption pays for
    // itself with an ::after that extends the touch area past the paint. Only a coarse pointer
    // is asked for that, because only a coarse pointer ever had the floor — `phone-stress-320`
    // runs without touch emulation on purpose (see playwright.config.ts), so there is nothing
    // there to give back.
    const coarse = await page.evaluate(() => window.matchMedia('(pointer: coarse)').matches)
    if (coarse) {
      const after = await rotation.evaluate(el => getComputedStyle(el, '::after').content)
      expect(after, 'the bar carries an extended touch area').not.toBe('none')
    }
  })

  test('the bottom nav does not cover the last week of the month', async ({ page }) => {
    await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight))
    await expect(weekRows(page).last()).toBeVisible()
    const nav = page.getByRole('navigation', { name: 'Main navigation' })
    const navBox = (await nav.boundingBox())!
    const lastRow = (await weekRows(page).last().boundingBox())!
    expect(
      lastRow.y + lastRow.height,
      'the final week row scrolls clear of the bottom navigation',
    ).toBeLessThanOrEqual(navBox.y + 1)
  })
})

// A multi-day event is one record; the compaction must not have turned a segment into a
// separate thing to tap. Spanning itself is covered in calendar-multiday.spec.ts — what is
// asserted here is that the compact bar still resolves to the one underlying event.
test.describe('compact bars still open the single event behind them', () => {
  test.beforeEach(async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === 'tablet-768', 'phone-only')
    await openPhoneMonth(page)
  })

  test('tapping a later segment of a cross-month span opens that same event', async ({ page }) => {
    const segments = page.locator('div.touch-pan-y button[title^="Nick US"]')
    expect(await segments.count(), 'the span breaks into one bar per week it touches')
      .toBeGreaterThan(1)
    await segments.last().click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expect(dialog.getByPlaceholder('Title')).toHaveValue('Nick US')
  })
})
