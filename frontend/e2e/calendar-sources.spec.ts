import { test, expect } from '@playwright/test'
import { mockAuthenticatedApi } from './fixtures/mockApi'

// Calendar Sources: managing holiday/school/subscribed calendars, and how their entries behave
// on the Calendar itself. All fixture-driven — nothing here reaches a real feed.

const CATALOGUE = [
  { kind: 'holidays', provider: 'au_holidays', label: 'Australian public holidays', needs_url: false, category: 'holiday', colour: '#C2703D' },
  { kind: 'school', provider: 'au_school_terms', label: 'Australian school calendar', needs_url: false, category: 'school', colour: '#4B7BA8' },
  { kind: 'subscription', provider: 'ics', label: 'Subscribed calendar', needs_url: true, category: 'subscription', colour: '#6F5AA8' },
  { kind: 'import', provider: 'ics', label: 'Imported calendar file', needs_url: false, category: 'import', colour: '#5A8A6F' },
]

function source(overrides: Record<string, unknown> = {}) {
  return {
    id: 1, name: 'Australian public holidays', kind: 'holidays', category: 'holiday',
    type_label: 'Australian public holidays', is_enabled: true, colour: '#C2703D',
    has_url: false, url_display: '',
    settings_json: { include_national: true, include_regional: true, include_local: true },
    show_on_calendar: true, show_in_upcoming: true, notifications_enabled: false,
    last_sync_at: '2026-08-17T00:00:00Z', last_success_at: '2026-08-17T00:00:00Z',
    sync_status: 'ok', sync_error: '', can_sync: true, event_count: 12,
    created_at: '2026-08-17T00:00:00Z', updated_at: '2026-08-17T00:00:00Z',
    ...overrides,
  }
}

test.describe('calendar sources management', () => {
  test('lists sources grouped by kind', async ({ page }) => {
    await mockAuthenticatedApi(page, {
      '/api/v1/calendar/sources/': {
        sources: [
          source(),
          source({ id: 2, name: 'Brisbane Broncos', kind: 'subscription', category: 'subscription', type_label: 'Subscribed calendar', colour: '#6F5AA8' }),
        ],
        catalogue: CATALOGUE,
      },
    })
    await page.goto('/calendar/sources')
    await expect(page.getByText('Automatic')).toBeVisible()
    await expect(page.getByText('Subscriptions')).toBeVisible()
    await expect(page.getByText('Australian public holidays').first()).toBeVisible()
    await expect(page.getByText('Brisbane Broncos')).toBeVisible()
  })

  test('disabling a source persists the switch', async ({ page }) => {
    let patched: Record<string, unknown> | null = null
    await mockAuthenticatedApi(page, {
      '/api/v1/calendar/sources/': { sources: [source()], catalogue: CATALOGUE },
    })
    await page.route('**/api/v1/calendar/sources/1/', async route => {
      patched = route.request().postDataJSON() as Record<string, unknown>
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify(source({ is_enabled: false })),
      })
    })

    await page.goto('/calendar/sources')
    // click() rather than uncheck(): the control is disabled while the write is in flight, so
    // uncheck()'s own state assertion races the request. The payload is the real claim.
    await page.getByLabel('Enable Australian public holidays').click()
    await expect.poll(() => patched).not.toBeNull()
    expect(patched).toEqual({ is_enabled: false })
  })

  test('school calendar layers toggle independently', async ({ page }) => {
    const patches: Record<string, unknown>[] = []
    const school = source({
      id: 3, name: 'Queensland State Schools', kind: 'school', category: 'school',
      type_label: 'Australian school calendar',
      settings_json: { system: 'qld_state', show_terms: true, show_holidays: true, show_student_free: false },
    })
    await mockAuthenticatedApi(page, {
      '/api/v1/calendar/sources/': { sources: [school], catalogue: CATALOGUE },
    })
    await page.route('**/api/v1/calendar/sources/3/', async route => {
      patches.push(route.request().postDataJSON() as Record<string, unknown>)
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(school) })
    })

    await page.goto('/calendar/sources')
    await page.getByRole('button', { name: 'Settings' }).click()
    await page.getByLabel('Show school terms').click()
    await expect.poll(() => patches.length).toBeGreaterThan(0)
    expect((patches[0].settings_json as Record<string, unknown>).show_terms).toBe(false)
    // The holidays layer is untouched by turning terms off.
    expect((patches[0].settings_json as Record<string, unknown>).show_holidays).toBe(true)
  })

  test('sync now refreshes a source and surfaces a failure', async ({ page }) => {
    await mockAuthenticatedApi(page, {
      '/api/v1/calendar/sources/': { sources: [source({ id: 2, name: 'Brisbane Broncos', kind: 'subscription' })], catalogue: CATALOGUE },
    })
    await page.route('**/api/v1/calendar/sources/2/sync/', async route => {
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify(source({
          id: 2, name: 'Brisbane Broncos', kind: 'subscription',
          sync_status: 'error', sync_error: 'That calendar could not be reached.',
        })),
      })
    })

    await page.goto('/calendar/sources')
    await page.getByRole('button', { name: 'Sync now' }).click()
    await expect(page.getByText('That calendar could not be reached.').first()).toBeVisible()
  })

  test('adding a subscription previews before saving', async ({ page }) => {
    let created: Record<string, unknown> | null = null
    await mockAuthenticatedApi(page, {
      '/api/v1/calendar/sources/': { sources: [], catalogue: CATALOGUE },
    })
    await page.route('**/api/v1/calendar/sources/preview/', async route => {
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({
          event_count: 24, future_count: 20, past_count: 4,
          sample: [{ title: 'Broncos vs Cowboys', start_at: '2026-08-21T09:50:00Z', all_day: false }],
        }),
      })
    })
    await page.route('**/api/v1/calendar/sources/', async route => {
      if (route.request().method() !== 'POST') return route.fallback()
      created = route.request().postDataJSON() as Record<string, unknown>
      await route.fulfill({
        status: 201, contentType: 'application/json',
        body: JSON.stringify(source({ id: 9, name: 'Brisbane Broncos', kind: 'subscription' })),
      })
    })

    await page.goto('/calendar/sources')
    await page.getByRole('button', { name: '+ Add calendar source' }).click()
    await page.getByLabel('What kind of calendar?').selectOption('subscribe')
    await page.getByPlaceholder('https://example.com/fixtures.ics').fill('webcal://example.com/broncos.ics')
    await page.getByRole('button', { name: 'Preview' }).click()
    await expect(page.getByText('24 events')).toBeVisible()
    await expect(page.getByText('20 upcoming · 4 past')).toBeVisible()

    await page.getByPlaceholder('Shown on your calendar').fill('Brisbane Broncos')
    await page.getByRole('button', { name: 'Add', exact: true }).click()
    await expect.poll(() => created).not.toBeNull()
    expect(created).toMatchObject({ kind: 'subscription', provider: 'ics', name: 'Brisbane Broncos' })
  })

  test('a rejected feed URL shows the reason and saves nothing', async ({ page }) => {
    await mockAuthenticatedApi(page, {
      '/api/v1/calendar/sources/': { sources: [], catalogue: CATALOGUE },
    })
    await page.route('**/api/v1/calendar/sources/preview/', async route => {
      await route.fulfill({
        status: 400, contentType: 'application/json',
        body: JSON.stringify({ detail: 'That calendar link points inside the local network, which is not allowed.' }),
      })
    })

    await page.goto('/calendar/sources')
    await page.getByRole('button', { name: '+ Add calendar source' }).click()
    await page.getByLabel('What kind of calendar?').selectOption('subscribe')
    await page.getByPlaceholder('https://example.com/fixtures.ics').fill('http://127.0.0.1/feed.ics')
    await page.getByRole('button', { name: 'Preview' }).click()
    await expect(page.getByText(/points inside the local network/)).toBeVisible()
  })

  test('a subscription link is never shown back, only its host', async ({ page }) => {
    // Subscription links routinely carry a private token, so the API returns host-only
    // metadata and the UI must not invent a way to display the rest.
    await mockAuthenticatedApi(page, {
      '/api/v1/calendar/sources/': {
        sources: [source({
          id: 2, name: 'Brisbane Broncos', kind: 'subscription', category: 'subscription',
          type_label: 'Subscribed calendar', has_url: true, url_display: 'feeds.example.com',
        })],
        catalogue: CATALOGUE,
      },
    })
    await page.goto('/calendar/sources')
    await page.getByRole('button', { name: 'Settings' }).click()
    await expect(page.getByText('Feed host: feeds.example.com')).toBeVisible()
    await expect(page.getByText(/private token/)).toBeVisible()
    // A manager can still replace it without ever being handed the old one.
    await expect(page.getByLabel('Replace calendar link')).toBeVisible()
  })

  test('a member without management rights is told, not shown broken controls', async ({ page }) => {
    await mockAuthenticatedApi(page, {
      '/api/v1/auth/me/': {
        id: 2, username: 'member', display_name: 'Member', role: 'user',
        is_child_account: false, avatar: '', colour: '#1d7a91',
      },
      '/api/v1/calendar/sources/': { sources: [source()], catalogue: CATALOGUE },
    })
    await page.goto('/calendar/sources')
    await expect(page.getByRole('button', { name: '+ Add calendar source' })).toHaveCount(0)
    await expect(page.getByText(/Only an admin or manager/)).toBeVisible()
  })
})

test.describe('source events on the calendar', () => {
  const holiday = {
    id: 501, title: 'Brisbane Show Day (Ekka)', event_kind: 'event', description: 'Local public holiday',
    start_at: '2026-08-12T00:00:00Z', end_at: '2026-08-12T23:59:59Z', is_all_day: true,
    timezone: '', recurrence_rule: '', source_node: null, source_record_type: '',
    source_record_id: null, assigned_to_person_ids: [], colour: '#C2703D', location: '',
    provider: '', contact: '', visibility: 'household', sensitivity: 'normal', is_synced: false,
    is_source_managed: true, calendar_source_id: 1,
    calendar_source_name: 'Australian public holidays', calendar_source_category: 'holiday',
    is_range: false, created_at: '', updated_at: '',
  }

  test('a source-managed entry is read-only and names its source', async ({ page }) => {
    await mockAuthenticatedApi(page, {
      '/api/v1/calendar/events/': [holiday],
      '/api/v1/calendar/rotations/': [],
      '/api/v1/calendar/rotation-occurrences/': [],
      '/api/v1/atlas/birthday-occurrences/': [],
      '/api/v1/people/': [],
    })
    await page.goto('/calendar?date=2026-08-12')
    await page.getByText('Brisbane Show Day (Ekka)').first().click()

    // Not the editable form: no Save, and it says where the entry comes from.
    await expect(page.getByText(/kept up to date automatically/)).toBeVisible()
    await expect(page.getByRole('button', { name: 'Save' })).toHaveCount(0)
    await expect(page.getByRole('link', { name: /Calendar source settings/ })).toBeVisible()
  })
})
