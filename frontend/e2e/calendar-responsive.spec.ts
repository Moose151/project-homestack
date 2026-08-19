import { test, expect } from '@playwright/test'
import type { Locator, Page } from '@playwright/test'
import { mockAuthenticatedApi } from './fixtures/mockApi'
import { expectNoHorizontalOverflow } from './fixtures/assertions'

// The Calendar toolbar must reflow on its own width, not the browser's.
//
// The bug this covers: `sm:` only knows the *viewport* is wide. With the desktop sidebar taking
// ~256px, a half-screen browser still satisfied `sm:` and the single-row toolbar was applied to
// a container far too narrow for it, so the period label was squeezed to whatever space the
// fixed-width controls left over. Measured against the pre-fix build, in Day view (the longest
// label) the label collapsed to 87px at a 940px viewport and to 8px at 820px — half of a 1920
// monitor lands squarely in that range.
//
// The label is therefore the sharpest probe, and truncation is the assertion: comparing
// scrollWidth to clientWidth catches "crushed to a sliver" at any resolution or locale, where a
// fixed pixel threshold would only catch the widths someone happened to think of.

const CALENDAR_FIXTURES = {
  '/api/v1/calendar/events/': [],
  '/api/v1/calendar/rotations/': [],
  '/api/v1/calendar/rotation-occurrences/': [],
  '/api/v1/atlas/birthday-occurrences/': [],
  '/api/v1/people/': [],
}

/** Every toolbar control that must stay usable, whatever the width. */
function toolbarControls(page: Page) {
  return {
    previous: page.getByRole('button', { name: 'Previous period' }),
    next: page.getByRole('button', { name: 'Next period' }),
    today: page.getByRole('button', { name: 'Today' }),
    filter: page.getByRole('button', { name: /Filter/ }),
    month: page.getByRole('button', { name: 'month', exact: true }),
    week: page.getByRole('button', { name: 'week', exact: true }),
    day: page.getByRole('button', { name: 'day', exact: true }),
    agenda: page.getByRole('button', { name: 'agenda', exact: true }),
  }
}

async function boxOf(locator: Locator, name: string) {
  const box = await locator.boundingBox()
  expect(box, `${name} should have a bounding box`).not.toBeNull()
  return { name, ...box! }
}

/** Two boxes overlap only when they intersect on *both* axes. */
function overlaps(a: { x: number; y: number; width: number; height: number },
                  b: { x: number; y: number; width: number; height: number }) {
  const horizontally = a.x < b.x + b.width - 1 && b.x < a.x + a.width - 1
  const vertically = a.y < b.y + b.height - 1 && b.y < a.y + a.height - 1
  return horizontally && vertically
}

async function assertNoToolbarCollisions(page: Page) {
  const controls = toolbarControls(page)
  const boxes = [
    await boxOf(controls.previous, 'Previous'),
    await boxOf(controls.next, 'Next'),
    await boxOf(controls.today, 'Today'),
    await boxOf(controls.filter, 'Filter'),
    await boxOf(controls.month, 'Month'),
    await boxOf(controls.week, 'Week'),
    await boxOf(controls.day, 'Day'),
    await boxOf(controls.agenda, 'Agenda'),
  ]
  for (let i = 0; i < boxes.length; i += 1) {
    for (let j = i + 1; j < boxes.length; j += 1) {
      expect(
        overlaps(boxes[i], boxes[j]),
        `${boxes[i].name} overlaps ${boxes[j].name}`,
      ).toBe(false)
    }
  }
  return boxes
}

async function assertAllControlsUsable(page: Page) {
  const controls = toolbarControls(page)
  for (const [name, locator] of Object.entries(controls)) {
    await expect(locator, `${name} should be visible`).toBeVisible()
    const box = await locator.boundingBox()
    // A control squeezed below this is not selectable in practice.
    expect(box!.width, `${name} is too narrow to use`).toBeGreaterThanOrEqual(24)
    expect(box!.height, `${name} is too short to use`).toBeGreaterThanOrEqual(24)
  }
}

/** Whether the period label has been squeezed narrower than its own text. */
async function labelIsTruncated(page: Page) {
  return page.locator('[data-calendar-period-label]').evaluate(
    element => element.scrollWidth > element.clientWidth + 1,
  )
}

/** The toolbar and the month grid must stay inside the main content column. */
async function assertWithinMainContent(page: Page) {
  const main = await page.getByRole('main').boundingBox()
  const toolbar = await page.locator('[data-calendar-toolbar]').boundingBox()
  expect(toolbar!.x).toBeGreaterThanOrEqual(main!.x - 1)
  expect(toolbar!.x + toolbar!.width).toBeLessThanOrEqual(main!.x + main!.width + 1)

  // Only Month renders the desktop grid. boundingBox() *waits* for a missing element rather
  // than returning null, so the existence check has to come first.
  const grid = page.locator('[data-calendar-grid]')
  if (await grid.count()) {
    const gridBox = await grid.first().boundingBox()
    expect(gridBox!.x).toBeGreaterThanOrEqual(main!.x - 1)
    expect(gridBox!.x + gridBox!.width).toBeLessThanOrEqual(main!.x + main!.width + 1)
  }
}

// One project is enough: each block sets its own viewport, so running the same assertions under
// four phone/tablet presets would only repeat identical work.
test.describe('calendar toolbar at desktop widths', () => {
  test.beforeEach(async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'tablet-768', 'viewport is set per block below')
    await mockAuthenticatedApi(page, CALENDAR_FIXTURES)
  })

  test.describe('medium / split-screen desktop', () => {
    // Half of a 1920 monitor. Wide enough for the desktop sidebar, narrow enough that the
    // sidebar leaves the Calendar about half a screen — where the live failure was reported,
    // and where the pre-fix build crushed the Day-view label to well under its own text.
    test.use({ viewport: { width: 960, height: 900 } })

    test('controls reflow instead of colliding', async ({ page }) => {
      await page.goto('/calendar')
      await expect(page.getByRole('button', { name: 'Previous period' })).toBeVisible()

      await assertAllControlsUsable(page)
      await assertNoToolbarCollisions(page)
      await assertWithinMainContent(page)
      await expectNoHorizontalOverflow(page)
    })

    test('the period label is never squeezed narrower than its text', async ({ page }) => {
      await page.goto('/calendar')
      const label = page.locator('[data-calendar-period-label]')
      await expect(label).toBeVisible()

      // Every dated view, because each has a different label length and Day is the longest —
      // "Tuesday, August 18" is what the pre-fix build reduced to a few pixels.
      for (const view of ['month', 'week', 'day'] as const) {
        await page.getByRole('button', { name: view, exact: true }).click()
        await expect(label).toBeVisible()
        expect(
          await labelIsTruncated(page),
          `the ${view} period label is truncated at this width`,
        ).toBe(false)
        expect((await label.innerText()).trim().length).toBeGreaterThan(3)
      }
    })

    test('the toolbar wraps onto a second row rather than compressing', async ({ page }) => {
      await page.goto('/calendar')
      await expect(page.getByRole('button', { name: 'Previous period' })).toBeVisible()
      const previous = await boxOf(page.getByRole('button', { name: 'Previous period' }), 'Previous')
      const agenda = await boxOf(page.getByRole('button', { name: 'agenda', exact: true }), 'Agenda')
      // Wrapped: the view picker sits below the period navigation, not beside it.
      expect(agenda.y).toBeGreaterThan(previous.y + previous.height - 1)
    })

    test('the calendar still fits inside the main column in every view', async ({ page }) => {
      await page.goto('/calendar')
      for (const view of ['month', 'week', 'day', 'agenda'] as const) {
        await page.getByRole('button', { name: view, exact: true }).click()
        await assertWithinMainContent(page)
        await expectNoHorizontalOverflow(page)
      }
    })

    test('the page header actions and rotation legend do not overflow either', async ({ page }) => {
      await page.goto('/calendar')
      const main = await page.getByRole('main').boundingBox()
      for (const name of ['Rotation', '+ Event']) {
        const box = await page.getByRole('button', { name }).boundingBox()
        expect(box!.x).toBeGreaterThanOrEqual(main!.x - 1)
        expect(box!.x + box!.width).toBeLessThanOrEqual(main!.x + main!.width + 1)
      }
      await expectNoHorizontalOverflow(page)
    })

    test('period navigation still works', async ({ page }) => {
      await page.goto('/calendar')
      const label = page.locator('[data-calendar-period-label]')
      const before = await label.innerText()
      await page.getByRole('button', { name: 'Next period' }).click()
      await expect(label).not.toHaveText(before)
      await page.getByRole('button', { name: 'Today' }).click()
      await expect(label).toHaveText(before)
    })

    test('every view can still be selected', async ({ page }) => {
      await page.goto('/calendar')
      // The view is component state rather than a URL parameter, so the selected button's own
      // active styling is what proves the click landed.
      for (const view of ['week', 'day', 'agenda', 'month'] as const) {
        const button = page.getByRole('button', { name: view, exact: true })
        await button.click()
        await expect(button).toHaveClass(/bg-raised/)
      }
    })

    test('the filter popover still opens', async ({ page }) => {
      await page.goto('/calendar')
      await page.getByRole('button', { name: /Filter/ }).click()
      await expect(page.getByText('Show', { exact: true })).toBeVisible()
    })
  })

  test.describe('the stated medium range boundaries', () => {
    for (const width of [1024, 1250]) {
      test.describe(`${width}px`, () => {
        test.use({ viewport: { width, height: 900 } })

        test('no collision, no overflow, label intact', async ({ page }) => {
          await page.goto('/calendar')
          await expect(page.getByRole('button', { name: 'Previous period' })).toBeVisible()
          await page.getByRole('button', { name: 'day', exact: true }).click()
          expect(await labelIsTruncated(page)).toBe(false)
          await assertAllControlsUsable(page)
          await assertNoToolbarCollisions(page)
          await assertWithinMainContent(page)
          await expectNoHorizontalOverflow(page)
        })
      })
    }
  })

  test.describe('wide desktop', () => {
    test.use({ viewport: { width: 1600, height: 900 } })

    test('keeps the convenient single-row toolbar', async ({ page }) => {
      await page.goto('/calendar')
      await expect(page.getByRole('button', { name: 'Previous period' })).toBeVisible()

      const previous = await boxOf(page.getByRole('button', { name: 'Previous period' }), 'Previous')
      const agenda = await boxOf(page.getByRole('button', { name: 'agenda', exact: true }), 'Agenda')
      // Same row: their vertical spans overlap.
      expect(agenda.y).toBeLessThan(previous.y + previous.height)

      await assertAllControlsUsable(page)
      await assertNoToolbarCollisions(page)
      await expectNoHorizontalOverflow(page)
    })
  })

  test.describe('the narrow end of the desktop range', () => {
    // The sidebar appears from md (768px); this is the tightest desktop layout there is.
    test.use({ viewport: { width: 820, height: 900 } })

    test('still reflows without collision or overflow', async ({ page }) => {
      await page.goto('/calendar')
      await expect(page.getByRole('button', { name: 'Previous period' })).toBeVisible()
      await page.getByRole('button', { name: 'day', exact: true }).click()
      expect(await labelIsTruncated(page)).toBe(false)
      await assertAllControlsUsable(page)
      await assertNoToolbarCollisions(page)
      await assertWithinMainContent(page)
      await expectNoHorizontalOverflow(page)
    })
  })
})
