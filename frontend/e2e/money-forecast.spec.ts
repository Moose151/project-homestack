import { test, expect } from '@playwright/test'
import { mockAuthenticatedApi } from './fixtures/mockApi'
import { SOLACE_ENABLED_NODE, billFixture, bootstrapFixture, nowFixture } from './fixtures/solace'
import { expectNoHorizontalOverflow } from './fixtures/assertions'

const forecast = {
  as_of: '2028-08-03', forecast_start: '2028-08-03', through: '2029-08-03', horizon_months: 12,
  latest_balance: { id: 1, snapshot_date: '2028-08-02', balance: '1000.00', notes: '' },
  opening_balance: '1000.00', buffer_amount: '100.00', total_bills: '1200.00', total_contributions: '0.00',
  required_opening_balance: '1200.00', ending_balance: '-200.00', lowest_balance: '-200.00',
  lowest_balance_date: '2028-08-24', first_shortfall_date: '2028-08-24', safe_to_withdraw: '0.00',
  shortfall: '200.00', is_covered: false, overdue_total: '0.00',
  warnings: ['Some bills have no due date and cannot be forecast. Review the bill coverage below.'],
  bill_coverage: [
    { bill_id: 1, name: 'Mortgage', included: true, reason: 'Included', payment_count: 2, total: '1200.00' },
    { bill_id: 2, name: 'Phone', included: false, reason: 'Paid from another account', payment_count: 0, total: '0.00' },
    { bill_id: 3, name: 'Insurance', included: false, reason: 'Missing due date', payment_count: 0, total: '0.00' },
  ],
  timeline: [
    { date: '2028-08-10', contributions: '0.00', bills: '600.00', net_change: '-600.00', projected_balance: '400.00', items: [{ kind: 'bill', name: 'Mortgage', amount: '600.00', record_id: 1, status: 'upcoming' }] },
    { date: '2028-08-24', contributions: '0.00', bills: '600.00', net_change: '-600.00', projected_balance: '-200.00', items: [{ kind: 'bill', name: 'Mortgage', amount: '600.00', record_id: 1, status: 'upcoming' }] },
  ],
}

async function setup(page: Parameters<typeof mockAuthenticatedApi>[0], overrides: Record<string, unknown> = {}) {
  await mockAuthenticatedApi(page, {
    '/api/v1/nodes/': [SOLACE_ENABLED_NODE],
    '/api/v1/solace/bootstrap/': { ...bootstrapFixture([billFixture()]), forecast },
    '/api/v1/solace/now/': nowFixture(),
    '/api/v1/solace/forecast/': forecast,
    ...overrides,
  })
}

test('overview leads directly to account forecast and explains omitted bills', async ({ page }, testInfo) => {
  await setup(page)
  await page.goto('/solace')
  await expect(page.getByText('Top-up needed', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Open bills-account forecast' }).click()
  await expect(page.getByRole('heading', { name: 'Bills-account forecast' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Top-up needed: $200.00' })).toBeVisible()
  await page.getByLabel('Forecast bill coverage').selectOption('excluded')
  await expect(page.getByRole('link', { name: /Phone/ })).toContainText('Paid from another account')
  await expect(page.getByRole('link', { name: /Insurance/ })).toContainText('Missing due date')
  await expect(page.getByRole('link', { name: /Mortgage/ })).toHaveCount(0)
  await page.getByLabel('Forecast bill coverage').selectOption('all')
  await expectNoHorizontalOverflow(page)
  await page.screenshot({ path: `/tmp/homestack-money-${testInfo.project.name}.png`, fullPage: true })
  await page.getByRole('link', { name: /Mortgage/ }).click()
  await expect(page).toHaveURL(/tab=bills&section=bills&bill=1/)
})

test('forecast works without a balance and does not invent zero balances', async ({ page }) => {
  const withoutBalance = { ...forecast, latest_balance: null, opening_balance: null, lowest_balance: null, ending_balance: null, is_covered: null, timeline: forecast.timeline.map(row => ({ ...row, projected_balance: null })) }
  await setup(page, { '/api/v1/solace/bootstrap/': { ...bootstrapFixture(), forecast: withoutBalance } })
  await page.goto('/solace?tab=insights&section=forecast')
  await expect(page.getByRole('link', { name: /Mortgage/ })).toBeVisible()
  await expect(page.getByText('Add a closing balance', { exact: false })).toBeVisible()
  await expect(page.getByRole('figure')).toHaveCount(0)
  await expect(page.getByText('—', { exact: true })).toHaveCount(4)
  await expectNoHorizontalOverflow(page)
})

test('update balance keeps entered values after failure and saves from the forecast', async ({ page }) => {
  await setup(page)
  let attempts = 0
  await page.route('**/api/v1/solace/balances/', async route => {
    attempts++
    expect(route.request().postDataJSON()).toMatchObject({ balance: '2345.67', snapshot_date: '2028-08-02' })
    await route.fulfill({ status: attempts === 1 ? 400 : 201, contentType: 'application/json', body: JSON.stringify(attempts === 1 ? { detail: 'Balance could not be saved' } : {}) })
  })
  await page.goto('/solace?tab=insights&section=forecast')
  await page.getByRole('button', { name: 'Update balance', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog.getByLabel('Balance date')).toHaveValue('2028-08-02')
  await dialog.getByLabel('Closing balance').fill('2345.67')
  await dialog.getByRole('button', { name: 'Save balance' }).click()
  await expect(dialog.getByRole('alert')).toContainText('Balance could not be saved')
  await expect(dialog.getByLabel('Closing balance')).toHaveValue('2345.67')
  await expectNoHorizontalOverflow(page)
  await dialog.getByRole('button', { name: 'Save balance' }).click()
  await expect(dialog).toHaveCount(0)
  expect(attempts).toBe(2)
})

test('changing set-aside does not switch the payment account', async ({ page }) => {
  await setup(page)
  await page.goto('/solace?tab=bills&section=bills')
  await page.getByRole('button', { name: 'Edit bill', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByLabel('Include in set-aside', { exact: true }).uncheck()
  await expect(dialog.getByLabel('Paid from bills account')).toBeChecked()
  const saved = page.waitForRequest(r => r.method() === 'PATCH' && r.url().endsWith('/solace/bills/1/'))
  await dialog.getByRole('button', { name: 'Save', exact: true }).click()
  expect((await saved).postDataJSON()).toMatchObject({ include_in_set_aside: false, paid_from_bills_account: true })
  await expect(dialog).toHaveCount(0)
})

test('failed horizon refresh preserves the last successful forecast and its period', async ({ page }) => {
  await setup(page)
  await page.route('**/api/v1/solace/forecast/**', route => route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'Try again later' }) }))
  await page.goto('/solace?tab=insights&section=forecast')
  await page.getByLabel('Forecast period').selectOption('3')
  await expect(page.getByRole('alert')).toContainText('last successful forecast')
  await expect(page.getByLabel('Forecast period')).toHaveValue('12')
  await expect(page.getByRole('link', { name: /Mortgage/ })).toBeVisible()
})

test('forecast chart can be inspected with the keyboard', async ({ page }) => {
  await setup(page)
  await page.goto('/solace?tab=insights&section=forecast')
  const slider = page.getByRole('slider', { name: 'Inspect forecast date' })
  await slider.focus()
  await slider.press('End')
  await expect(slider).toHaveAttribute('aria-valuetext', /\$-200\.00|-\$200\.00/)
  await expectNoHorizontalOverflow(page)
})

test('search results keep account totals intact and existing bill search links still work', async ({ page }) => {
  const bill = billFixture()
  await setup(page, { '/api/v1/solace/search/': { bills: [bill], paydays: [], buckets: [], purchases: [], checklist: [] } })
  await page.goto('/solace')
  await page.getByPlaceholder('Search Money…').fill('Electricity')
  await expect(page.getByRole('heading', { name: 'Search results' })).toBeVisible()
  await expect(page.getByRole('link', { name: /Electricity/ })).toBeVisible()
  await expect(page.getByText('Top-up needed', { exact: true })).toBeVisible()
  await page.getByRole('link', { name: /Electricity/ }).click()
  await expect(page.locator('#solace-bill-1')).toBeVisible()
  await page.goto('/solace?tab=bills&q=Electricity')
  await expect(page.locator('#solace-bill-1')).toBeVisible()
  await page.getByPlaceholder('Search Money…').fill('No matching bill')
  await expect(page.getByText('No bills match these filters')).toBeVisible()
})

test('legacy payday checklist link opens a usable checklist on phone and desktop', async ({ page }) => {
  const item = { id: 4, title: 'Transfer to bills account', amount_hint: '400.00', is_complete: false, cycle_start: '2028-08-03', source_key: '' }
  await setup(page, { '/api/v1/solace/bootstrap/': { ...bootstrapFixture(), forecast, checklist: [item] } })
  await page.route('**/api/v1/solace/checklist/4/', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...item, is_complete: true }) }))
  await page.goto('/solace?tab=checklist')
  await expect(page).toHaveURL(/tab=plan&section=checklist/)
  await page.getByRole('button', { name: /Transfer to bills account/ }).click()
  await expect(page.getByRole('button', { name: /Transfer to bills account/ })).toContainText('Done')
  await expectNoHorizontalOverflow(page)
})

test('generating a payday checklist opens the generated transfers', async ({ page }) => {
  const plan = { ...bootstrapFixture().plan, buckets: [{ bucket_id: 1, bucket_name: 'Bills account', purpose: 'bills', amount: '400.00' }] }
  const item = { id: 4, title: 'Transfer to bills account', amount_hint: '400.00', is_complete: false, cycle_start: plan.cycle_start, source_key: '' }
  await setup(page, {
    '/api/v1/solace/bootstrap/': { ...bootstrapFixture(), forecast, plan },
    '/api/v1/solace/plan/': plan,
    '/api/v1/solace/plan/checklist/': [item],
  })
  await page.goto('/solace?tab=plan&section=payplan')
  await page.getByRole('button', { name: 'Create payday checklist' }).click()
  await expect(page).toHaveURL(/tab=plan&section=checklist/)
  await expect(page.getByRole('button', { name: /Transfer to bills account/ })).toBeVisible()
})

test('bill editing shows a failed save inside the open sheet', async ({ page }) => {
  await setup(page)
  await page.route('**/api/v1/solace/bills/1/', route => route.fulfill({ status: 400, contentType: 'application/json', body: JSON.stringify({ detail: 'Unable to save bill' }) }))
  await page.goto('/solace?tab=bills')
  await page.getByRole('button', { name: 'Edit bill', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByRole('button', { name: 'Save', exact: true }).click()
  await expect(dialog.getByRole('alert')).toContainText('Unable to save bill')
  await expect(dialog.getByLabel('Paid from bills account')).toBeChecked()
})
