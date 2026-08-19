import { test, expect } from '@playwright/test'
import { mockAuthenticatedApi, nodesWith } from './fixtures/mockApi'
import { expectNoHorizontalOverflow } from './fixtures/assertions'

// "Log run" is a fast path into the ordinary Fitness session model, not a parallel run store.
// These tests assert the form's behaviour; the backend suite proves the resulting session earns
// the same personal records as the long way round.

const PERSON = {
  id: 1, display_name: 'Test User', preferred_name: 'Test', avatar: '', colour: '#1d7a91',
  profile_type: 'adult', linked_user_id: 1, date_of_birth: null,
}

function runSession(over: Record<string, unknown> = {}) {
  return {
    id: 91, person_id: 1, person_name: 'Test User', name: 'Run', status: 'completed',
    started_at: '2026-08-18T06:00:00Z', finished_at: '2026-08-18T06:28:14Z',
    duration_seconds: 1694, total_reps: 0, total_volume: '0', notes: '',
    visibility: 'household', personal_records: [],
    exercises: [{
      id: 1, status: 'active', position: 0, notes: '',
      exercise: {
        id: 5, name: 'Running', exercise_type: 'running', measurement: 'distance_time',
        weight_unit: 'kg', distance_unit: 'km', muscle_group: '', is_system: true,
        is_archived: false, notes: '',
      },
      sets: [{
        id: 1, position: 0, reps: null, weight: null, duration_seconds: 1694,
        distance: '5.000', is_completed: true, completed_at: '2026-08-18T06:28:14Z',
      }],
    }],
    ...over,
  }
}

async function fitnessPage(page: import('@playwright/test').Page, extra: Record<string, unknown> = {}) {
  await mockAuthenticatedApi(page, {
    '/api/v1/nodes/': nodesWith('fitness'),
    '/api/v1/people/': [PERSON],
    '/api/v1/fitness/sessions/': [],
    '/api/v1/fitness/programs/': [],
    '/api/v1/fitness/exercises/': [],
    '/api/v1/fitness/records/': [],
    ...extra,
  })
}

test.describe('Log run', () => {
  test('is reachable from Fitness', async ({ page }) => {
    await fitnessPage(page)
    await page.goto('/fitness')
    await expect(page.getByRole('button', { name: /Log run/ })).toBeVisible()
  })

  test('opens as a focused sheet and derives pace live', async ({ page }) => {
    await fitnessPage(page)
    await page.goto('/fitness')
    await page.getByRole('button', { name: /Log run/ }).click()

    await expect(page.getByLabel('Distance')).toBeVisible()
    await page.getByLabel('Distance').fill('5')
    await page.getByLabel('Minutes').fill('28')
    await page.getByLabel('Seconds').fill('14')
    // Pace is derived from distance and duration — never a third stored number.
    // 1694s over 5km is 338.8 s/km, i.e. 5:39 — the worked example in the brief.
    await expect(page.locator('[data-run-pace]')).toHaveText('5:39 /km')
    await expectNoHorizontalOverflow(page)
  })

  test('saving posts a completed run', async ({ page }) => {
    let posted: Record<string, unknown> | null = null
    await fitnessPage(page)
    await page.route('**/api/v1/fitness/sessions/log-run/', async route => {
      posted = route.request().postDataJSON() as Record<string, unknown>
      await route.fulfill({
        status: 201, contentType: 'application/json', body: JSON.stringify(runSession()),
      })
    })

    await page.goto('/fitness')
    await page.getByRole('button', { name: /Log run/ }).click()
    await page.getByLabel('Distance').fill('5')
    await page.getByLabel('Minutes').fill('28')
    await page.getByLabel('Seconds').fill('14')
    await page.getByRole('button', { name: 'Save run' }).click()

    await expect.poll(() => posted).not.toBeNull()
    expect(posted).toMatchObject({ person_id: 1, distance: '5.000', duration_seconds: 1694 })
  })

  test('will not save without a distance and a duration', async ({ page }) => {
    await fitnessPage(page)
    await page.goto('/fitness')
    await page.getByRole('button', { name: /Log run/ }).click()

    const save = page.getByRole('button', { name: 'Save run' })
    await expect(save).toBeDisabled()
    await page.getByLabel('Distance').fill('5')
    await expect(save).toBeDisabled()      // still no duration
    await page.getByLabel('Minutes').fill('28')
    await expect(save).toBeEnabled()
  })

  test('zero values are not saveable', async ({ page }) => {
    await fitnessPage(page)
    await page.goto('/fitness')
    await page.getByRole('button', { name: /Log run/ }).click()
    await page.getByLabel('Distance').fill('0')
    await page.getByLabel('Minutes').fill('0')
    await page.getByLabel('Seconds').fill('0')
    await expect(page.getByRole('button', { name: 'Save run' })).toBeDisabled()
  })

  test('history shows running metrics, not strength ones', async ({ page }) => {
    await fitnessPage(page, { '/api/v1/fitness/sessions/': [runSession()] })
    await page.goto('/fitness?tab=history')

    const summary = page.locator('[data-session-summary]').first()
    await expect(summary).toContainText('5.00 km')
    await expect(summary).toContainText('28:14')
    await expect(summary).toContainText('/km')
    // A run has no meaningful rep count or tonnage; showing them would be noise.
    await expect(summary).not.toContainText('reps')
    await expect(summary).not.toContainText('volume')
  })

  test('an ordinary workout still shows strength metrics', async ({ page }) => {
    const strength = runSession({
      id: 92, name: 'Push day', total_reps: 40, total_volume: '1200',
      exercises: [{
        id: 2, status: 'active', position: 0, notes: '',
        exercise: {
          id: 9, name: 'Bench press', exercise_type: 'strength', measurement: 'reps_weight',
          weight_unit: 'kg', distance_unit: 'km', muscle_group: 'Chest', is_system: true,
          is_archived: false, notes: '',
        },
        sets: [{
          id: 2, position: 0, reps: 10, weight: '60.00', duration_seconds: null,
          distance: '0', is_completed: true, completed_at: '2026-08-18T06:28:14Z',
        }],
      }],
    })
    await fitnessPage(page, { '/api/v1/fitness/sessions/': [strength] })
    await page.goto('/fitness?tab=history')
    const summary = page.locator('[data-session-summary]').first()
    await expect(summary).toContainText('reps')
    await expect(summary).toContainText('volume')
  })

  test('Quick Launch opens the form without logging anything', async ({ page }) => {
    let posted = false
    await fitnessPage(page)
    await page.route('**/api/v1/fitness/sessions/log-run/', async route => {
      posted = true
      await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(runSession()) })
    })

    // The action target resolves to this route (docs/39 §13): it opens the form, nothing more.
    await page.goto('/fitness?tab=today&new=run')
    await expect(page.getByRole('button', { name: 'Save run' })).toBeVisible()
    expect(posted).toBe(false)
  })
})
