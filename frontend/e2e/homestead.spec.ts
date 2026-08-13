import { test, expect } from '@playwright/test'
import { mockAuthenticatedApi } from './fixtures/mockApi'
import { expectNoHorizontalOverflow } from './fixtures/assertions'

// docs/36 §6.9 (Phase 5) — Homestead's nine tabs become a phone dashboard + subroutes-by-query,
// preserving the ?tab= deep-link contract several other pages rely on (Hub, Solace, Quick
// Create, source links — see docs/36 Phase 5's implementation note for the full list).

const ROOMS_FIXTURE = {
  rooms: [
    { id: 1, name: 'Kitchen', area_type: 'interior', description: '', icon: '🍳', colour: '#B0563C', display_order: 0, summary: { active_count: 1, completed_count: 0, archived_count: 0, remaining_estimated_cost: '120.00' } },
  ],
  household_summary: { active_count: 1, completed_count: 0, archived_count: 0, remaining_estimated_cost: '120.00', completed_cost: '0.00', overall_cost: '120.00' },
}

const LINKED_ROOMS_FIXTURE = {
  ...ROOMS_FIXTURE,
  rooms: [{
    ...ROOMS_FIXTURE.rooms[0],
    name: 'Family room',
    floorplan_data: { floorplan_slot: 'living' },
  }],
}

test.beforeEach(async ({}, testInfo) => {
  test.skip(testInfo.project.name === 'tablet-768', 'phone-only: the dashboard/Back pattern is sm:hidden')
})

test('phone shows a dashboard on the overview tab, not the nine-option picker', async ({ page }) => {
  let maintenanceRequests = 0
  await mockAuthenticatedApi(page, {
    '/api/v1/homestead/maintenance/': [{ id: 1 }],
    '/api/v1/homestead/appliances/': [],
    '/api/v1/homestead/improvements/': [],
  })
  page.on('request', request => {
    if (new URL(request.url()).pathname === '/api/v1/homestead/maintenance/') maintenanceRequests += 1
  })
  await page.goto('/homestead')
  // Not "Needs attention" alone — the desktop OverviewTab (hidden, not unmounted, on phone)
  // has a same-text status badge, so that string alone is ambiguous. The actual count line is
  // unique to the new mobile dashboard.
  await expect(page.getByText('1 maintenance job')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Rooms & areas' })).toBeVisible()
  // The old mobile <select> picker is gone on the dashboard itself.
  await expect(page.getByLabel('Homestead section')).toBeHidden()
  // React dev effects can replay once under the dev server; the old hidden mobile+desktop
  // composition produced an additional logical fetch path on top of that.
  expect(maintenanceRequests).toBeLessThanOrEqual(2)
  await expectNoHorizontalOverflow(page)
})

test('tapping a dashboard destination sets ?tab= and shows a Back-to-dashboard header', async ({ page }) => {
  await mockAuthenticatedApi(page, { '/api/v1/homestead/rooms/': ROOMS_FIXTURE })
  await page.goto('/homestead')
  await page.getByRole('button', { name: 'Rooms & areas' }).click()
  await expect(page).toHaveURL(/\/homestead\?tab=rooms$/)
  const back = page.getByRole('button', { name: 'Back' })
  await expect(back).toBeVisible()
  // RoomsTab has its own "Rooms & areas" <h2> too (in its "+ Add room" header row), so this
  // targets the MobileScreenHeader's <h1> specifically, which renders first in DOM order.
  await expect(page.getByRole('heading', { name: 'Rooms & areas' }).first()).toBeVisible()
  await back.click()
  // useUrlTab omits the query param entirely for the default tab, so "back to the dashboard"
  // is a bare /homestead, not an explicit ?tab=overview.
  await expect(page).toHaveURL(/\/homestead$/)
  await expect(page.getByRole('button', { name: 'Rooms & areas' })).toBeVisible()
})

test('Rooms defaults to the list view on phone, not the floor plan', async ({ page }) => {
  await mockAuthenticatedApi(page, { '/api/v1/homestead/rooms/': ROOMS_FIXTURE })
  await page.goto('/homestead?tab=rooms')
  await expect(page.getByRole('link', { name: /Kitchen/ })).toBeVisible()
  await expectNoHorizontalOverflow(page)
})

test('Floor plan opens as a full-screen phone viewer and returns to the room list', async ({ page }) => {
  await mockAuthenticatedApi(page, { '/api/v1/homestead/rooms/': ROOMS_FIXTURE })
  await page.goto('/homestead?tab=rooms')
  await page.getByRole('button', { name: 'View interactive floor plan' }).click()

  const viewer = page.getByRole('dialog', { name: 'Interactive floor plan' })
  await expect(viewer).toBeVisible()
  await expect(viewer.locator('[data-floor-plan-viewer="fullscreen"]')).toBeVisible()
  const box = await viewer.boundingBox()
  const viewport = page.viewportSize()
  expect(box?.width).toBe(viewport?.width)
  expect(box?.height).toBe(viewport?.height)
  await expectNoHorizontalOverflow(page)

  await viewer.getByRole('button', { name: 'Close' }).click()
  await expect(viewer).toHaveCount(0)
  await expect(page.getByRole('link', { name: /Kitchen/ })).toBeVisible()
})

test('nested confirmation closes one layer at a time and keeps body scroll locked', async ({ page }) => {
  await mockAuthenticatedApi(page, { '/api/v1/homestead/rooms/': LINKED_ROOMS_FIXTURE })
  await page.goto('/homestead?tab=rooms')
  await page.getByRole('button', { name: 'View interactive floor plan' }).click()
  await page.getByRole('button', { name: 'Unlink' }).click()

  await expect(page.getByRole('dialog')).toHaveCount(2)
  await expect(page.getByRole('dialog', { name: /Unlink Family room/ })).toBeVisible()
  await expect.poll(() => page.evaluate(() => document.body.style.overflow)).toBe('hidden')

  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(1)
  await expect(page.getByRole('dialog', { name: 'Interactive floor plan' })).toBeVisible()
  await expect.poll(() => page.evaluate(() => document.body.style.overflow)).toBe('hidden')

  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect.poll(() => page.evaluate(() => document.body.style.overflow)).toBe('')
})

test('a deep link with ?tab= still lands directly on that section (existing contract preserved)', async ({ page }) => {
  await mockAuthenticatedApi(page, { '/api/v1/homestead/maintenance/': [] })
  await page.goto('/homestead?tab=maintenance')
  await expect(page.getByRole('button', { name: 'Back' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Maintenance' })).toBeVisible()
})
