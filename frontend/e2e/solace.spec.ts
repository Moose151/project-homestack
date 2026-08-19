import { test, expect } from '@playwright/test'
import { mockAuthenticatedApi } from './fixtures/mockApi'
import { expectNoHorizontalOverflow } from './fixtures/assertions'

// docs/36 §6.10 (Phase 6) — Add Bill/Add Bucket/Add Purchase/Add Payday all share one
// `CreatePanel` wrapper, now a full-height sheet (Modal size="full") instead of an
// inline-expanding panel; Edit Bill got the same treatment. Phone Money now lands on a
// destination home instead of the old five-tab selector.

const SOLACE_ENABLED_NODE = {
  key: 'solace', name: 'solace', description: '', icon: '', is_core: false, supports_kiosk: false,
  supports_sensitive_lock: false, can_view: true, is_enabled: true, is_hidden: false,
  requires_reauthentication: false, display_order: 0, custom_name: '', custom_icon: '',
}

function billFixture() {
  const now = new Date().toISOString()
  return {
    id: 1, name: 'Electricity', category: 'utilities', provider: 'PowerCo', amount: '150.00',
    due_at: now, recurrence_rule: 'FREQ=MONTHLY', end_date: null, is_active: true,
    is_autopay: false, include_in_set_aside: true, notes: '', source_node: null,
    is_paid: false, is_overdue: false, next_due_at: now, next_occurrence_id: 1,
    annual_amount: '1800.00', fortnightly_amount: '69.23',
    created_at: now, updated_at: now,
  }
}

// SolaceBootstrap is a large aggregate (bills/paydays/buckets/plan/settings/health/forecast/...)
// consumed across every Solace tab. The Bills tab's `bills` state comes solely from this payload
// (not a separate list fetch), so exercising the Edit-bill sheet needs a shape complete enough
// that nothing downstream crashes on render — a partial/loosely-typed stub isn't enough here,
// unlike most other pages' fixtures in this suite.
function bootstrapFixture(bills: ReturnType<typeof billFixture>[] = []) {
  const now = new Date().toISOString()
  return {
    bills, paydays: [], purchases: [], buckets: [], checklist: [],
    plan: {
      cycle_start: '2026-08-01', cycle_end: '2026-08-14', income_total: '0.00',
      individual_income_total: '0.00', shared_income_total: '0.00', allocated_total: '0.00',
      remaining: '0.00', sources: [], people: [], buckets: [],
      set_aside: { recurring_bills: '0.00', planned_purchases: '0.00', buffer: '0.00', required_total: '0.00', bills_bucket_total: '0.00', shortfall: '0.00', is_covered: true },
    },
    settings: {
      id: 1, currency_symbol: '$', budget_year: null, cycle_anchor_date: null,
      default_buffer_amount: '0.00', payday_bill_handling: 'new_cycle', show_help_tips: true,
      dashboard_reminders: true, due_soon_days: 7, created_at: now, updated_at: now,
    },
    categories: ['utilities'], balances: [],
    health: { status: 'healthy', issues: [], counts: { active_bills: bills.length, active_paydays: 0, active_buckets: 0, overdue_occurrences: 0 }, percentage_allocation_total: '0', latest_balance: null },
    category_report: { rows: [] }, closeout: { history: [] },
    forecast: { as_of: now, forecast_start: now, through: now, horizon_months: 1, latest_balance: null, opening_balance: null, buffer_amount: '0.00', total_bills: '0.00', total_contributions: '0.00', required_opening_balance: '0.00', timeline: [] },
    checklist_preferences: [],
  }
}

function nowFixture() {
  return {
    cycle_start: '2026-08-01', cycle_end: '2026-08-14', days_until_cycle_end: 1,
    income_total: '0.00',
    set_aside: null,
    due: [{
      id: 1, bill_id: 1, bill_name: 'Electricity', amount: '150.00',
      due_at: new Date().toISOString(), status: 'due', paid_at: null, skipped_at: null,
      calendar_event_id: null, source_record_type: '', source_record_id: null,
    }],
    due_total: '150.00', overdue_count: 0, overdue_total: '0.00',
    paid_this_cycle_count: 0, paid_this_cycle_total: '0.00',
    bucket_total: '0.00', buckets: [],
  }
}

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

test('phone Money home uses destination rows instead of the five-tab picker', async ({ page }) => {
  await mockAuthenticatedApi(page, {
    '/api/v1/nodes/': [SOLACE_ENABLED_NODE],
    '/api/v1/solace/bootstrap/': bootstrapFixture([billFixture()]),
    '/api/v1/solace/now/': nowFixture(),
  })
  await page.goto('/solace')
  await expect(page.getByText('Current position')).toBeVisible()
  await expect(page.getByRole('button', { name: /Bills/ })).toBeVisible()
  await expect(page.getByRole('button', { name: /Pay plan/ })).toBeVisible()
  await expect(page.getByLabel('Money section')).toBeHidden()
  await page.getByRole('button', { name: /Buckets/ }).click()
  await expect(page).toHaveURL(/tab=plan&section=buckets/)
  await expect(page.getByRole('button', { name: 'Back' })).toBeVisible()
})

test('phone Money home can mark an upcoming bill paid without opening the schedule', async ({ page }) => {
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

  await page.goto('/solace')
  const payButton = page.getByRole('button', { name: 'Mark paid' })
  await expect(payButton).toBeVisible()
  await payButton.click()
  await expect(page.getByText('Nothing left to pay this cycle.')).toBeVisible()
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
  await page.getByRole('button', { name: 'View all upcoming bills' }).click()
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
