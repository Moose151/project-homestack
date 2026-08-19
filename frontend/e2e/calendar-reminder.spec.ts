import { test, expect } from '@playwright/test'
import { mockAuthenticatedApi } from './fixtures/mockApi'

// Calendar's create action offers Event / Appointment / Reminder. Reminder is not a calendar
// event_kind — it must save a real Atlas reminder through the shared reminder API, so that it
// schedules notifications and is editable as a reminder rather than as a calendar entry.

test.beforeEach(async ({ page }) => {
  await mockAuthenticatedApi(page, {
    '/api/v1/calendar/events/': [],
    '/api/v1/calendar/rotations/': [],
    '/api/v1/calendar/rotation-occurrences/': [],
    '/api/v1/atlas/birthday-occurrences/': [],
    '/api/v1/people/': [],
  })
})

test('choosing Reminder saves an Atlas reminder, not a calendar event', async ({ page }) => {
  let reminderBody: Record<string, unknown> | null = null
  let calendarWrites = 0

  await page.route('**/api/v1/atlas/reminders/', async route => {
    if (route.request().method() !== 'POST') return route.fallback()
    reminderBody = route.request().postDataJSON() as Record<string, unknown>
    await route.fulfill({
      status: 201, contentType: 'application/json',
      body: JSON.stringify({ id: 9, title: 'Water the plants' }),
    })
  })
  await page.route('**/api/v1/calendar/events/', async route => {
    if (route.request().method() === 'POST') calendarWrites += 1
    return route.fallback()
  })

  await page.goto('/calendar?new=event')
  await page.getByLabel('Type').selectOption('reminder')
  await expect(page.getByText('Remind me at')).toBeVisible()

  await page.getByPlaceholder('Title').fill('Water the plants')
  await page.getByRole('button', { name: 'Save' }).click()

  await expect.poll(() => reminderBody).not.toBeNull()
  expect(reminderBody).toMatchObject({
    title: 'Water the plants',
    notifications_enabled: true,
  })
  expect(calendarWrites).toBe(0)
})

test('Reminder is offered only when creating, not when editing an existing event', async ({ page }) => {
  const now = new Date()
  const iso = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 10, 0).toISOString()
  await mockAuthenticatedApi(page, {
    '/api/v1/calendar/events/': [{
      id: 1, title: 'Dentist', event_kind: 'appointment', description: '',
      start_at: iso, end_at: null, is_all_day: false, timezone: '', recurrence_rule: '',
      source_node: null, source_record_type: '', source_record_id: null,
      assigned_to_person_ids: [], colour: '', location: '', provider: '', contact: '',
      visibility: 'household', sensitivity: 'normal', is_synced: false,
      created_at: iso, updated_at: iso,
    }],
    '/api/v1/calendar/rotations/': [],
    '/api/v1/calendar/rotation-occurrences/': [],
    '/api/v1/atlas/birthday-occurrences/': [],
    '/api/v1/people/': [],
  })

  // Creating offers it...
  await page.goto('/calendar?new=event')
  await expect(page.getByLabel('Type').getByRole('option', { name: 'Reminder' })).toHaveCount(1)
  await page.getByRole('button', { name: 'Cancel' }).click()

  // ...but an existing calendar event cannot be turned into one: that would be a different
  // record in a different node, not an edit.
  await page.getByText('Dentist').first().click()
  await expect(page.getByLabel('Type')).toHaveValue('appointment')
  await expect(page.getByLabel('Type').getByRole('option', { name: 'Reminder' })).toHaveCount(0)
})
