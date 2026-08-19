import { test, expect } from '@playwright/test'
import { mockAuthenticatedApi } from './fixtures/mockApi'

// Calendar's create action offers Event / Appointment / Reminder. "Reminder" is not a calendar
// event_kind, and since v0.40 it is not a separate reminder record either: a reminder is a
// property of a to-do (D19 §E). Choosing it must create one Atlas to-do — which syncs its own
// calendar entry and carries its own notification offset — and must not create a standalone
// AtlasReminder, which would double up on both the calendar and the notification sweep.

test.beforeEach(async ({ page }) => {
  await mockAuthenticatedApi(page, {
    '/api/v1/calendar/events/': [],
    '/api/v1/calendar/rotations/': [],
    '/api/v1/calendar/rotation-occurrences/': [],
    '/api/v1/atlas/birthday-occurrences/': [],
    '/api/v1/people/': [],
  })
})

test('choosing Reminder saves a to-do, not a calendar event and not a reminder record', async ({ page }) => {
  let todoBody: Record<string, unknown> | null = null
  let calendarWrites = 0
  let legacyReminderWrites = 0

  await page.route('**/api/v1/atlas/todos/quick-create/', async route => {
    if (route.request().method() !== 'POST') return route.fallback()
    todoBody = route.request().postDataJSON() as Record<string, unknown>
    await route.fulfill({
      status: 201, contentType: 'application/json',
      body: JSON.stringify({ id: 9, title: 'Water the plants' }),
    })
  })
  await page.route('**/api/v1/atlas/reminders/', async route => {
    if (route.request().method() === 'POST') legacyReminderWrites += 1
    return route.fallback()
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

  await expect.poll(() => todoBody).not.toBeNull()
  expect(todoBody).toMatchObject({ title: 'Water the plants' })
  // "Send a notification when it is time" is on by default, and a timed capture expresses that
  // as the at-time offset rather than as a second scheduler.
  expect((todoBody as unknown as { notify_offsets: number[] }).notify_offsets).toEqual([0])
  expect(calendarWrites).toBe(0)
  expect(legacyReminderWrites).toBe(0)
})

test('turning the notification off stores no offsets', async ({ page }) => {
  let todoBody: Record<string, unknown> | null = null
  await page.route('**/api/v1/atlas/todos/quick-create/', async route => {
    if (route.request().method() !== 'POST') return route.fallback()
    todoBody = route.request().postDataJSON() as Record<string, unknown>
    await route.fulfill({
      status: 201, contentType: 'application/json',
      body: JSON.stringify({ id: 10, title: 'Quiet job' }),
    })
  })

  await page.goto('/calendar?new=event')
  await page.getByLabel('Type').selectOption('reminder')
  await page.getByPlaceholder('Title').fill('Quiet job')
  await page.getByLabel('Send a notification when it is time').uncheck()
  await page.getByRole('button', { name: 'Save' }).click()

  await expect.poll(() => todoBody).not.toBeNull()
  expect((todoBody as unknown as { notify_offsets: number[] }).notify_offsets).toEqual([])
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
