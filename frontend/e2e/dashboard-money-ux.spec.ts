import { test, expect } from '@playwright/test'
import { mockAuthenticatedApi } from './fixtures/mockApi'

const SOLACE_NODE = {
  key: 'solace', name: 'solace', description: '', icon: '', is_core: false, supports_kiosk: false,
  supports_sensitive_lock: false, can_view: true, is_enabled: true, is_hidden: false,
  requires_reauthentication: false, display_order: 0, custom_name: '', custom_icon: '',
}

const plusDays = (days: number) => {
  const date = new Date()
  date.setHours(12, 0, 0, 0)
  date.setDate(date.getDate() + days)
  return date.toISOString()
}

test('Dashboard separates appointment wording from due-record wording', async ({ page }) => {
  await mockAuthenticatedApi(page, {
    '/api/v1/nodes/': [SOLACE_NODE],
    '/api/v1/hub/': {
      widgets: [{
        key: 'upcoming',
        name: 'Upcoming',
        size: 'medium',
        supports_kiosk: true,
        meta: { horizons: [{ key: 'week', label: 'Next 7 days', until: plusDays(7).slice(0, 10) }] },
        items: [
          { id: 1, title: 'Dentist appointment', start_at: plusDays(3), is_all_day: true, source_node: 'calendar', source_record_type: 'CalendarEvent', source_record_id: 1 },
          { id: 2, title: 'Tomorrow appointment', start_at: plusDays(1), is_all_day: true, source_node: 'calendar', source_record_type: 'CalendarEvent', source_record_id: 2 },
          { id: 3, title: 'Today appointment', start_at: plusDays(0), is_all_day: true, source_node: 'calendar', source_record_type: 'CalendarEvent', source_record_id: 3 },
          { id: 4, title: 'Overdue task', start_at: plusDays(-2), is_all_day: true, source_node: 'meridian', source_record_type: 'MeridianTask', source_record_id: 4 },
          { id: 5, title: 'Bill: Overdue electricity', start_at: plusDays(-2), is_all_day: true, source_node: 'solace', source_record_type: 'Bill', source_record_id: 7 },
          { id: 6, title: 'Bill: Future rates', start_at: plusDays(3), is_all_day: true, source_node: 'solace', source_record_type: 'Bill', source_record_id: 8 },
        ],
      }],
    },
  })

  await page.goto('/hub')
  await expect(page.getByText('Dentist appointment')).toBeVisible()
  await expect(page.getByText(/^In 3 days$/)).toBeVisible()
  await expect(page.getByText('Tomorrow appointment')).toBeVisible()
  await expect(page.getByText('Today appointment')).toBeVisible()
  await expect(page.getByText('Overdue task')).toBeVisible()
  await expect(page.getByText('2d overdue')).toHaveCount(2)
  await expect(page.getByText('Due in 3 days')).toBeVisible()
})

test('Dashboard bill links open the selected Money bill', async ({ page }) => {
  const dueAt = plusDays(3)
  await mockAuthenticatedApi(page, {
    '/api/v1/nodes/': [SOLACE_NODE],
    '/api/v1/hub/': {
      widgets: [{
        key: 'solace_bills_due',
        name: 'Due before next payday',
        size: 'small',
        supports_kiosk: false,
        meta: {
          configured: true, next_payday: plusDays(7).slice(0, 10), bill_count: 1,
          total: '150.00', overdue_count: 0,
        },
        items: [{
          id: 70, bill_id: 7, bill_name: 'Electricity', bill_category: 'utilities',
          amount: '150.00', due_at: dueAt, status: 'upcoming', paid_at: null, notes: '',
          is_overdue: false, visibility: 'household', sensitivity: 'normal',
          created_at: plusDays(0), updated_at: plusDays(0),
        }],
      }],
    },
  })

  await page.goto('/hub')
  await expect(page.getByRole('link', { name: /Electricity/ })).toHaveAttribute(
    'href',
    '/solace?tab=bills&section=upcoming&bill=7&occurrence=70',
  )
  await expect(page.getByRole('link', { name: /View all upcoming bills/ })).toHaveAttribute(
    'href', '/solace?tab=bills&section=upcoming',
  )
})
