import { test, expect } from '@playwright/test'
import { mockAuthenticatedApi, nodesWith } from './fixtures/mockApi'
import { expectNoHorizontalOverflow } from './fixtures/assertions'

// Quick Launch: a personal set of shortcuts that resolve server-side (docs/39).
// The client never decides where a shortcut goes — these tests assert it asks and obeys.

const TARGETS = [
  { key: 'core.calendar', label: 'Calendar', description: 'Events, appointments and reminders', icon: '📅', node_key: '', target_type: 'open', requires_object: false, sensitive: false, launch_modes: ['normal', 'focused'], objects: [] },
  { key: 'atlas.list', label: 'A list', description: 'Open one particular list', icon: '✅', node_key: 'atlas', target_type: 'open', requires_object: true, sensitive: false, launch_modes: ['normal', 'focused'], objects: [{ id: 7, label: 'Groceries' }] },
  { key: 'solace.upcoming_bills', label: 'Upcoming bills', description: 'Every unpaid bill in date order', icon: '🧾', node_key: 'solace', target_type: 'open', requires_object: false, sensitive: true, launch_modes: ['normal'], objects: [] },
  { key: 'fitness.log_run', label: 'Log run', description: 'Open the quick run form', icon: '🏃', node_key: 'fitness', target_type: 'action', requires_object: false, sensitive: false, launch_modes: ['normal'], objects: [] },
]

function shortcut(over: Record<string, unknown> = {}) {
  return {
    id: '11111111-1111-4111-8111-111111111111',
    target_key: 'core.calendar', target_object_id: null, custom_label: '',
    label: 'Calendar', icon: '📅', node_key: '', launch_mode: 'normal',
    display_order: 0, status: 'ok', unavailable_reason: '',
    ...over,
  }
}

test.describe('Quick Launch management', () => {
  test.beforeEach(async ({}, testInfo) => {
    test.skip(testInfo.project.name === 'tablet-768', 'phone-first surface; desktop covered separately')
  })

  test('an empty state invites the first shortcut', async ({ page }) => {
    await mockAuthenticatedApi(page, { '/api/v1/quick-launch/targets/': { targets: TARGETS } })
    await page.goto('/settings/quick-launch')
    await expect(page.getByText('No shortcuts yet')).toBeVisible()
    await expectNoHorizontalOverflow(page)
  })

  test('a shortcut can be added from the registered destinations', async ({ page }) => {
    let created: Record<string, unknown> | null = null
    await mockAuthenticatedApi(page, { '/api/v1/quick-launch/targets/': { targets: TARGETS } })
    await page.route('**/api/v1/quick-launch/shortcuts/', async route => {
      if (route.request().method() === 'POST') {
        created = route.request().postDataJSON() as Record<string, unknown>
        await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(shortcut()) })
        return
      }
      await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    })

    await page.goto('/settings/quick-launch')
    await page.getByRole('button', { name: '+ Add a shortcut' }).click()
    await page.getByLabel('Destination').selectOption('core.calendar')
    await page.getByLabel('Shortcut name').fill('Family diary')
    await page.getByRole('button', { name: 'Add', exact: true }).click()

    await expect.poll(() => created).not.toBeNull()
    expect(created).toMatchObject({ target_key: 'core.calendar', custom_label: 'Family diary' })
  })

  test('a specific list shortcut carries the chosen record', async ({ page }) => {
    let created: Record<string, unknown> | null = null
    await mockAuthenticatedApi(page, {
      '/api/v1/nodes/': nodesWith('atlas'),
      '/api/v1/quick-launch/targets/': { targets: TARGETS },
    })
    await page.route('**/api/v1/quick-launch/shortcuts/', async route => {
      if (route.request().method() === 'POST') {
        created = route.request().postDataJSON() as Record<string, unknown>
        await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(shortcut()) })
        return
      }
      await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    })

    await page.goto('/settings/quick-launch')
    await page.getByRole('button', { name: '+ Add a shortcut' }).click()
    await page.getByLabel('Destination').selectOption('atlas.list')
    await expect(page.getByLabel('Item')).toBeVisible()
    await page.getByRole('button', { name: 'Add', exact: true }).click()

    await expect.poll(() => created).not.toBeNull()
    expect(created).toMatchObject({ target_key: 'atlas.list', target_object_id: 7 })
  })

  test('a sensitive destination says so before it is added', async ({ page }) => {
    await mockAuthenticatedApi(page, { '/api/v1/quick-launch/targets/': { targets: TARGETS } })
    await page.goto('/settings/quick-launch')
    await page.getByRole('button', { name: '+ Add a shortcut' }).click()
    await page.getByLabel('Destination').selectOption('solace.upcoming_bills')
    await expect(page.getByText(/asks for your password/)).toBeVisible()
    await expect(page.getByText(/does not skip the prompt/)).toBeVisible()
  })

  test('an action destination promises not to act on its own', async ({ page }) => {
    await mockAuthenticatedApi(page, { '/api/v1/quick-launch/targets/': { targets: TARGETS } })
    await page.goto('/settings/quick-launch')
    await page.getByRole('button', { name: '+ Add a shortcut' }).click()
    await page.getByLabel('Destination').selectOption('fitness.log_run')
    await expect(page.getByText(/Nothing is saved until you say so/)).toBeVisible()
  })

  test('shortcuts reorder and persist the new order', async ({ page }) => {
    let ordered: string[] | null = null
    const rows = [
      shortcut({ id: 'aaaaaaaa-1111-4111-8111-111111111111', label: 'Calendar' }),
      shortcut({ id: 'bbbbbbbb-2222-4222-8222-222222222222', label: 'Groceries', display_order: 1 }),
    ]
    await mockAuthenticatedApi(page, {
      '/api/v1/quick-launch/shortcuts/': rows,
      '/api/v1/quick-launch/targets/': { targets: TARGETS },
    })
    await page.route('**/api/v1/quick-launch/shortcuts/reorder/', async route => {
      ordered = (route.request().postDataJSON() as { ids: string[] }).ids
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify([rows[1], rows[0]]),
      })
    })

    await page.goto('/settings/quick-launch')
    // Arrows, not drag: usable with a finger, a mouse and a keyboard alike.
    await page.getByRole('button', { name: 'Move Groceries up' }).click()
    await expect.poll(() => ordered).not.toBeNull()
    expect(ordered![0]).toBe('bbbbbbbb-2222-4222-8222-222222222222')
  })

  test('a shortcut can be renamed', async ({ page }) => {
    let patched: Record<string, unknown> | null = null
    await mockAuthenticatedApi(page, {
      '/api/v1/quick-launch/shortcuts/': [shortcut()],
      '/api/v1/quick-launch/targets/': { targets: TARGETS },
    })
    await page.route('**/api/v1/quick-launch/shortcuts/*/', async route => {
      if (route.request().method() !== 'PATCH') return route.fallback()
      patched = route.request().postDataJSON() as Record<string, unknown>
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify(shortcut({ custom_label: 'Diary', label: 'Diary' })),
      })
    })

    await page.goto('/settings/quick-launch')
    await page.getByRole('button', { name: 'Rename Calendar' }).click()
    await page.getByLabel('Shortcut name').fill('Diary')
    await page.getByRole('button', { name: 'Save' }).click()
    await expect.poll(() => patched).toMatchObject({ custom_label: 'Diary' })
  })

  test('a shortcut can be removed', async ({ page }) => {
    let deleted = false
    await mockAuthenticatedApi(page, {
      '/api/v1/quick-launch/shortcuts/': [shortcut()],
      '/api/v1/quick-launch/targets/': { targets: TARGETS },
    })
    await page.route('**/api/v1/quick-launch/shortcuts/*/', async route => {
      if (route.request().method() !== 'DELETE') return route.fallback()
      deleted = true
      await route.fulfill({ status: 204, body: '' })
    })

    await page.goto('/settings/quick-launch')
    page.once('dialog', dialog => dialog.accept())
    await page.getByRole('button', { name: 'Remove Calendar' }).click()
    await page.getByRole('button', { name: 'Remove', exact: true }).last().click()
    await expect.poll(() => deleted).toBe(true)
  })

  test('an unavailable shortcut is shown as such and cannot be opened', async ({ page }) => {
    await mockAuthenticatedApi(page, {
      '/api/v1/quick-launch/shortcuts/': [shortcut({
        label: 'Groceries', status: 'unavailable',
        unavailable_reason: 'This shortcut is no longer available.',
      })],
      '/api/v1/quick-launch/targets/': { targets: TARGETS },
    })
    await page.goto('/settings/quick-launch')
    await expect(page.getByText('This shortcut is no longer available.', { exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Open Groceries' })).toHaveCount(0)
  })
})

test.describe('the launch contract', () => {
  test.beforeEach(async ({}, testInfo) => {
    test.skip(testInfo.project.name === 'tablet-768', 'covered on the phone projects')
  })

  test('an open shortcut redirects to the resolved destination', async ({ page }) => {
    await mockAuthenticatedApi(page, { '/api/v1/calendar/events/': [] })
    await page.route('**/api/v1/quick-launch/shortcuts/*/resolve/', async route => {
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({ status: 'ok', label: 'Calendar', reason: '', node_key: '', launch_mode: 'normal', route: '/calendar' }),
      })
    })
    await page.goto('/launch/11111111-1111-4111-8111-111111111111')
    await expect(page).toHaveURL(/\/calendar/)
  })

  test('the destination comes from the server, not the client', async ({ page }) => {
    // The same shortcut id resolves somewhere else entirely; the client must simply obey.
    await mockAuthenticatedApi(page, {
      '/api/v1/nodes/': nodesWith('atlas'), '/api/v1/atlas/lists/': [],
    })
    await page.route('**/api/v1/quick-launch/shortcuts/*/resolve/', async route => {
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({ status: 'ok', label: 'Groceries', reason: '', node_key: 'atlas', launch_mode: 'normal', route: '/atlas?tab=grocery&list=7' }),
      })
    })
    await page.goto('/launch/11111111-1111-4111-8111-111111111111')
    await expect(page).toHaveURL(/\/atlas\?tab=grocery&list=7/)
  })

  test('a locked destination offers the unlock rather than opening', async ({ page }) => {
    await mockAuthenticatedApi(page, { '/api/v1/nodes/': nodesWith('solace') })
    await page.route('**/api/v1/quick-launch/shortcuts/*/resolve/', async route => {
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({ status: 'locked', label: 'Upcoming bills', reason: 'Unlock to open this.', node_key: 'solace', launch_mode: 'normal', route: '/solace?tab=bills&section=upcoming' }),
      })
    })
    await page.goto('/launch/11111111-1111-4111-8111-111111111111')
    await expect(page.getByText('Upcoming bills')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Unlock and continue' })).toBeVisible()
    // The intended destination is preserved through the unlock, not replaced by a node root.
    await page.getByRole('button', { name: 'Unlock and continue' }).click()
    await expect(page).toHaveURL(/section=upcoming/)
  })

  test('an unavailable shortcut fails gracefully with a way out', async ({ page }) => {
    await mockAuthenticatedApi(page)
    await page.route('**/api/v1/quick-launch/shortcuts/*/resolve/', async route => {
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({ status: 'unavailable', label: '', reason: 'This shortcut is no longer available.', node_key: 'atlas', launch_mode: 'normal' }),
      })
    })
    await page.goto('/launch/11111111-1111-4111-8111-111111111111')
    await expect(page.getByText('This shortcut is no longer available.', { exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Remove shortcut' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Back to HomeStack' })).toBeVisible()
  })

  test("another person's identifier is refused, and says nothing about it", async ({ page }) => {
    // The regression the brief asks for: the server 404s, and the client must not invent a
    // destination or disclose that a shortcut exists.
    await mockAuthenticatedApi(page)
    await page.route('**/api/v1/quick-launch/shortcuts/*/resolve/', async route => {
      await route.fulfill({
        status: 404, contentType: 'application/json',
        body: JSON.stringify({ status: 'unavailable', reason: 'This shortcut is no longer available.' }),
      })
    })
    await page.goto('/launch/99999999-9999-4999-8999-999999999999')
    await expect(page.getByText('This shortcut is no longer available.', { exact: true })).toBeVisible()
    await expect(page).toHaveURL(/\/launch\//)
  })

  test('the unavailable state does not overflow on a phone', async ({ page }) => {
    await mockAuthenticatedApi(page)
    await page.route('**/api/v1/quick-launch/shortcuts/*/resolve/', async route => {
      await route.fulfill({
        status: 404, contentType: 'application/json',
        body: JSON.stringify({ status: 'unavailable', reason: 'This shortcut is no longer available.' }),
      })
    })
    await page.goto('/launch/99999999-9999-4999-8999-999999999999')
    await expect(page.getByText('This shortcut is no longer available.', { exact: true })).toBeVisible()
    await expectNoHorizontalOverflow(page)
  })
})
