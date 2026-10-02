import { SOLACE_ENABLED_NODE, billFixture, bootstrapFixture, nowFixture } from './fixtures/solace'
import { test, expect } from '@playwright/test'
import { mockAuthenticatedApi } from './fixtures/mockApi'
import { expectNoHorizontalOverflow } from './fixtures/assertions'

// docs/36 §6.10 (Phase 6) — Add Bill/Add Bucket/Add Purchase/Add Payday all share one
// `CreatePanel` wrapper, now a full-height sheet (Modal size="full") instead of an
// inline-expanding panel; Edit Bill got the same treatment. Phone Money now lands on a
// destination home instead of the old five-tab selector.

test.beforeEach(async ({}, testInfo) => {
  test.skip(testInfo.project.name === 'tablet-768', 'phone-only: the full-sheet pattern is what changed')
})

test('Add bill opens as a full-height sheet, not an inline-expanding panel', async ({ page }) => {
  await mockAuthenticatedApi(page, { '/api/v1/nodes/': [SOLACE_ENABLED_NODE] })
  // .catch()-handled: SolacePage shows an inline error banner rather than crashing, and every
  // list stays at its safe initial empty state — enough for the Bills tab's empty-state + Add
  // flow, without needing the full bootstrap shape below.
  await page.route('**/api/v1/solace/bootstrap/', route => route.fulfill({ status: 500, contentType: 'application/json', body: '{}' }))
  await page.route('**/api/v1/solace/now/', route => route.fulfill({ status: 500, contentType: 'application/json', body: '{}' }))
  await page.goto('/solace?tab=bills')
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await page.getByRole('button', { name: '+ Add bill' }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog).toBeVisible()
  await expect(dialog.getByRole('heading', { name: 'Add bill' })).toBeVisible()
  await expect(dialog.getByPlaceholder('Electricity')).toBeVisible()
  await expectNoHorizontalOverflow(page)
  await page.keyboard.press('Escape')
  await expect(dialog).not.toBeVisible()
})

test('phone Money has three main destinations and optional advanced tools', async ({ page }) => {
  await mockAuthenticatedApi(page, {
    '/api/v1/nodes/': [SOLACE_ENABLED_NODE],
    '/api/v1/solace/bootstrap/': bootstrapFixture([billFixture()]),
    '/api/v1/solace/now/': nowFixture(),
  })
  await page.goto('/solace')
  await expect(page.getByRole('tab', { name: 'Overview', exact: true })).toBeVisible()
  await expect(page.getByRole('tab', { name: 'Bills', exact: true })).toBeVisible()
  await expect(page.getByRole('tab', { name: 'Setup', exact: true })).toBeVisible()
  await expect(page.getByLabel('Money section')).toBeHidden()
  await page.getByText('More tools', { exact: true }).click()
  await page.getByRole('button', { name: 'Payday plan & savings' }).click()
  await expect(page).toHaveURL(/tab=plan&section=payplan/)
  await expect(page.getByRole('button', { name: 'Back' })).toBeVisible()
})

test('manual bill payment remains available from the bills list', async ({ page }) => {
  let paid = false
  await mockAuthenticatedApi(page, {
    '/api/v1/nodes/': [SOLACE_ENABLED_NODE],
    '/api/v1/solace/bootstrap/': bootstrapFixture([billFixture()]),
    '/api/v1/solace/schedule/': {
      start: '2026-08-01', end: '2026-08-31', occurrences: nowFixture().due,
      income_events: [], summary: { bills_total: '150.00', paid_total: '0.00', unpaid_total: '150.00', skipped_total: '0.00', income_total: '0.00' },
    },
    '/api/v1/solace/forecast/': bootstrapFixture().forecast,
  })
  await page.route('**/api/v1/solace/now/', async route => {
    const fixture = nowFixture()
    await route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify(paid ? { ...fixture, due: [], due_total: '0.00', paid_this_cycle_count: 1, paid_this_cycle_total: '150.00' } : fixture),
    })
  })
  await page.route('**/api/v1/solace/occurrences/1/paid/', async route => {
    paid = true
    await route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({ ...nowFixture().due[0], status: 'paid', paid_at: new Date().toISOString() }),
    })
  })

  await page.goto('/solace?tab=bills')
  await page.getByText('Payment history & details', { exact: true }).click()
  const payButton = page.getByRole('button', { name: 'Mark next paid' })
  await expect(payButton).toBeVisible()
  await payButton.click()
  await expect.poll(() => paid).toBe(true)
  await expect(page).not.toHaveURL(/section=schedule/)
  await expectNoHorizontalOverflow(page)
})

test('phone Money home opens the chronological unpaid occurrence list', async ({ page }) => {
  const atDay = (offset: number) => {
    const value = new Date()
    value.setHours(12, 0, 0, 0)
    value.setDate(value.getDate() + offset)
    return value.toISOString()
  }
  const occurrence = (id: number, name: string, offset: number) => ({
    id, bill_id: id, bill_name: name, bill_category: 'utilities', due_at: atDay(offset),
    amount: `${id}.00`, status: 'upcoming', paid_at: null, notes: '', is_overdue: offset < 0,
    visibility: 'household', sensitivity: 'normal', created_at: atDay(-10), updated_at: atDay(-10),
  })
  await mockAuthenticatedApi(page, {
    '/api/v1/nodes/': [SOLACE_ENABLED_NODE],
    '/api/v1/solace/bootstrap/': bootstrapFixture([billFixture()]),
    '/api/v1/solace/now/': nowFixture(),
    '/api/v1/solace/occurrences/upcoming/': [
      occurrence(1, 'Overdue power', -2),
      occurrence(2, 'Water today', 0),
      occurrence(3, 'Internet later', 12),
    ],
  })

  await page.goto('/solace')
  await page.getByRole('tab', { name: 'Bills', exact: true }).click()
  await page.getByRole('tab', { name: 'Upcoming', exact: true }).click()
  await expect(page).toHaveURL(/tab=bills&section=upcoming/)
  await expect(page.getByRole('heading', { name: 'Overdue unpaid' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Today' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Later' })).toBeVisible()
  await expect(page.getByText('Overdue power')).toBeVisible()
  await expect(page.getByText('Water today')).toBeVisible()
  await expect(page.getByText('Internet later')).toBeVisible()
  await expectNoHorizontalOverflow(page)
})

test('Edit bill opens as a full-height sheet', async ({ page }) => {
  await mockAuthenticatedApi(page, {
    '/api/v1/nodes/': [SOLACE_ENABLED_NODE],
    '/api/v1/solace/bootstrap/': bootstrapFixture([billFixture()]),
  })
  await page.route('**/api/v1/solace/now/', route => route.fulfill({ status: 500, contentType: 'application/json', body: '{}' }))
  await page.goto('/solace?tab=bills')
  await page.getByRole('button', { name: 'Edit bill' }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog).toBeVisible()
  await expect(dialog.getByRole('heading', { name: 'Edit Electricity' })).toBeVisible()
  await expectNoHorizontalOverflow(page)
})

test('direct bill deep link opens the selected Money bill instead of a blank Bills page', async ({ page }) => {
  await mockAuthenticatedApi(page, {
    '/api/v1/nodes/': [SOLACE_ENABLED_NODE],
    '/api/v1/solace/bootstrap/': bootstrapFixture([billFixture()]),
    '/api/v1/solace/now/': nowFixture(),
  })
  await page.goto('/solace?tab=bills&bill=1&occurrence=1')
  await expect(page.getByText('Electricity')).toBeVisible()
  await expect(page.getByText('No bills yet')).toHaveCount(0)
})

test('sensitive gate still applies when the node requires re-authentication', async ({ page }) => {
  await mockAuthenticatedApi(page, {
    '/api/v1/nodes/': [{ ...SOLACE_ENABLED_NODE, requires_reauthentication: true }],
  })
  await page.goto('/solace')
  await expect(page.getByText(/password|unlock/i).first()).toBeVisible()
  await expect(page.getByRole('button', { name: '+ Add bill' })).toHaveCount(0)
})
