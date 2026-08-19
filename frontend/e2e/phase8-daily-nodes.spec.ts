import { test, expect } from '@playwright/test'
import { mockAuthenticatedApi } from './fixtures/mockApi'
import { expectNoHorizontalOverflow } from './fixtures/assertions'

// docs/36 Phase 8: Atlas, Meridian, Education, Pets, Fitness, Corners. Each node keeps its
// existing desktop layout (still mounted in the DOM, just CSS-hidden below sm:) alongside a new
// phone-only summary/destination layer, so locators here are scoped to text unique to the new
// phone-only rows rather than a shared title/name that exists in both layers at once.

// mockApi's default fixture only enables atlas/homestead/pets/meridian — education and fitness
// need to be explicitly enabled here or NodeRoute redirects the whole test to the Hub.
function enabledNode(key: string) {
  return {
    key, name: key, description: '', icon: '', is_core: false, supports_kiosk: false,
    supports_sensitive_lock: false, can_view: true, is_enabled: true, is_hidden: false,
    requires_reauthentication: false, display_order: 0, custom_name: '', custom_icon: '',
  }
}

test.describe('phone', () => {
  test.beforeEach(async ({}, testInfo) => {
    test.skip(testInfo.project.name === 'tablet-768', 'phone-only: each page splits mobile/desktop at its own sm: breakpoint')
  })

  // The fixtures below are `checklist` lists on purpose. Since v0.40 the Lists tab renders only
  // Lists & Notes lists (checklist/general) — Grocery and To-dos have their own tabs — so a
  // `todo` fixture here would simply never appear and the test would fail for the wrong reason.
  test('Atlas: the Lists tab shows summary rows on phone, and tapping one opens the list in a focused sheet', async ({ page }) => {
    await mockAuthenticatedApi(page, {
      '/api/v1/atlas/lists/': [{
        id: 1, title: 'Bunnings run', list_type: 'checklist', visibility: 'household', owner_person_id: null,
        items: [{
          id: 1, atlas_list_id: 1, title: 'Milk', notes: '', quantity: '', priority: '', position: 0,
          due_at: null, calendar_event_id: null, product_url: '', source_image_url: '', cached_image_url: '',
          image_attachment_id: null, retailer: '', unit_price: null, currency: '', imported_at: null,
          price_watch: null, assigned_to_person_ids: [], completed_at: null,
        }],
        created_at: '', updated_at: '',
      }],
      '/api/v1/people/': [],
    })
    await page.goto('/atlas?tab=lists')
    const row = page.locator('button', { hasText: '1 to do' })
    await expect(row).toBeVisible()
    await expect(page.getByRole('dialog')).toHaveCount(0)
    await row.click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expect(dialog.getByText('Milk')).toBeVisible()
    await expectNoHorizontalOverflow(page)
  })

  test('Atlas: a cold item deep link opens the focused list sheet on phone', async ({ page }) => {
    await mockAuthenticatedApi(page, {
      '/api/v1/atlas/lists/': [{
        id: 4, title: 'Packing list', list_type: 'checklist', visibility: 'household', owner_person_id: null,
        items: [{
          id: 44, atlas_list_id: 4, title: 'Passports', notes: '', quantity: '', priority: '', position: 0,
          due_at: null, calendar_event_id: null, product_url: '', source_image_url: '', cached_image_url: '',
          image_attachment_id: null, retailer: '', unit_price: null, currency: '', imported_at: null,
          price_watch: null, assigned_to_person_ids: [], completed_at: null,
        }],
        created_at: '', updated_at: '',
      }],
      '/api/v1/people/': [],
    })
    await page.goto('/atlas?tab=lists&item=44')
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expect(dialog.getByText('Passports')).toBeVisible()
    await expect(dialog.locator('#atlas-item-44')).toHaveClass(/ring-2/)
  })

  test('Meridian: Tasks and Routines are grouped under one phone destination with a secondary switcher', async ({ page }) => {
    await mockAuthenticatedApi(page, {
      '/api/v1/meridian/settings/': { points_label: 'points', group_goals_enabled: false, wishlist_requests_enabled: false, auto_end_streaks: false },
      // OverviewTab (rendered twice — phone dashboard + desktop, both mounted at once, same as
      // Homestead) needs the real object shape here; the generic []-fallback made `reports` an
      // array and crashed on `reports.recent_activity`, unmounting the whole app mid-test.
      '/api/v1/meridian/reports/': { leaderboard: [], recent_activity: [] },
    })
    await page.goto('/meridian')
    await page.locator('button', { hasText: 'Ordinary tasks and routines' }).click()
    await expect(page.getByRole('button', { name: 'Back' })).toBeVisible()
    await expect(page.getByRole('tab', { name: 'Routines' })).toBeVisible()
    await expectNoHorizontalOverflow(page)
  })

  test('Education: lands on Today/Due soon, and an assignment opens in a detail sheet with notes', async ({ page }) => {
    const tomorrow = new Date()
    tomorrow.setDate(tomorrow.getDate() + 1)
    await mockAuthenticatedApi(page, {
      '/api/v1/nodes/': [enabledNode('education')],
      '/api/v1/education/courses/': [],
      '/api/v1/education/assessments/': [{
        id: 1, title: 'Threat Intel Lab', assessment_type: 'assignment', course_id: null, course_name: '',
        course_code: '', assigned_to_person_ids: [], due_at: tomorrow.toISOString(), is_all_day: true,
        status: 'todo', priority: 'medium', weight: '', description: '', is_complete: false,
        calendar_event_id: null, visibility: 'household', sensitivity: 'normal', created_at: '', updated_at: '',
      }],
      '/api/v1/education/classes/': [],
      '/api/v1/education/institutions/': [],
      '/api/v1/education/assessments/1/notes/': [],
      '/api/v1/education/assessments/1/files/': [],
      '/api/v1/people/': [],
    })
    await page.goto('/education')
    await expect(page.getByText('Due soon')).toBeVisible()
    await expect(page.getByText('Threat Intel Lab')).toBeVisible()

    await page.goto('/education?tab=assignments')
    await page.getByText('Threat Intel Lab').click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expect(dialog.getByText('Notes')).toBeVisible()
    await expectNoHorizontalOverflow(page)
  })

  test('Education: cold assignment deep link opens the specific assignment detail', async ({ page }) => {
    await mockAuthenticatedApi(page, {
      '/api/v1/nodes/': [enabledNode('education')],
      '/api/v1/education/courses/': [],
      '/api/v1/education/assessments/': [{
        id: 7, title: 'Cryptography essay', assessment_type: 'assignment', course_id: null, course_name: '',
        course_code: '', assigned_to_person_ids: [], due_at: new Date().toISOString(), is_all_day: true,
        status: 'todo', priority: 'high', weight: '', description: '', is_complete: false,
        calendar_event_id: null, visibility: 'household', sensitivity: 'normal', created_at: '', updated_at: '',
      }],
      '/api/v1/education/classes/': [],
      '/api/v1/education/institutions/': [],
      '/api/v1/education/assessments/7/notes/': [],
      '/api/v1/education/assessments/7/files/': [],
      '/api/v1/people/': [],
    })
    await page.goto('/education?tab=assignments&assessment=7')
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expect(dialog.getByRole('heading', { name: 'Cryptography essay' })).toBeVisible()
  })

  test('Pets: the phone dashboard shows what needs attention next, and opens a pet in a detail sheet', async ({ page }) => {
    await mockAuthenticatedApi(page, {
      '/api/v1/pets/pets/': [{
        id: 1, name: 'Milo', species: 'dog', breed: 'Labrador', avatar: '', colour: '', date_of_birth: null,
        adoption_date: null, notes: '', vet_name: 'Dr Lee', vet_phone: '', microchip_number: '',
        insurance_provider: '', insurance_policy_number: '',
      }],
      '/api/v1/pets/treatments/': [{
        id: 1, pet_id: 1, pet_name: 'Milo', treatment_type: 'flea', name: 'Flea treatment',
        display_name: 'Flea treatment', last_done_at: null, next_due_at: new Date().toISOString(),
        recurrence_rule: '', notes: '', is_overdue: false, calendar_event_id: null, visibility: 'household',
        created_at: '', updated_at: '',
      }],
      '/api/v1/pets/appointments/': [],
    })
    await page.goto('/pets')
    const row = page.locator('button', { hasText: 'Flea treatment' })
    await expect(row).toBeVisible()
    await row.click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expect(dialog.getByText('Treatments')).toBeVisible()
    await expectNoHorizontalOverflow(page)
  })

  test('Pets: treatment editing uses a focused state inside the pet sheet', async ({ page }) => {
    await mockAuthenticatedApi(page, {
      '/api/v1/pets/pets/': [{
        id: 1, name: 'Milo', species: 'dog', breed: 'Labrador', avatar: '', colour: '', date_of_birth: null,
        adoption_date: null, notes: '', vet_name: '', vet_phone: '', microchip_number: '',
        insurance_provider: '', insurance_policy_number: '',
      }],
      '/api/v1/pets/treatments/': [{
        id: 1, pet_id: 1, pet_name: 'Milo', treatment_type: 'flea', name: 'Flea treatment',
        display_name: 'Flea treatment', last_done_at: null, next_due_at: new Date().toISOString(),
        recurrence_rule: '', notes: '', is_overdue: false, calendar_event_id: null, visibility: 'household',
        created_at: '', updated_at: '',
      }],
      '/api/v1/pets/appointments/': [],
    })
    await page.goto('/pets')
    await page.locator('button', { hasText: 'Flea treatment' }).click()
    const dialog = page.getByRole('dialog')
    await dialog.getByRole('button', { name: 'Edit Flea treatment' }).click()
    await expect(dialog.getByRole('button', { name: /Pet details/ })).toBeVisible()
    await expect(dialog.getByRole('button', { name: 'Save treatment' })).toBeVisible()
  })

  test('Pets: exact treatment and pet deep links open the focused context', async ({ page }) => {
    await mockAuthenticatedApi(page, {
      '/api/v1/pets/pets/': [{
        id: 1, name: 'Milo', species: 'dog', breed: 'Labrador', avatar: '', colour: '', date_of_birth: null,
        adoption_date: null, notes: '', vet_name: '', vet_phone: '', microchip_number: '',
        insurance_provider: '', insurance_policy_number: '',
      }],
      '/api/v1/pets/treatments/': [{
        id: 9, pet_id: 1, pet_name: 'Milo', treatment_type: 'flea', name: 'Flea treatment',
        display_name: 'Flea treatment', last_done_at: null, next_due_at: new Date().toISOString(),
        recurrence_rule: '', notes: '', is_overdue: false, calendar_event_id: null, visibility: 'household',
        created_at: '', updated_at: '',
      }],
      '/api/v1/pets/appointments/': [],
    })
    await page.goto('/pets?tab=reminders&treatment=9')
    await expect(page.locator('#pet-treatment-9')).toHaveClass(/ring-2/)

    await page.goto('/pets?tab=pets&pet=1')
    await expect(page.getByRole('dialog')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Milo' })).toBeVisible()
  })

  test('Fitness: the section tab bar is hidden during an active live session', async ({ page }) => {
    await mockAuthenticatedApi(page, {
      '/api/v1/nodes/': [enabledNode('fitness')],
      '/api/v1/people/': [{ id: 1, display_name: 'Test User', preferred_name: 'Test User', avatar: '', colour: '', profile_type: 'adult', linked_user_id: 1, date_of_birth: null }],
      '/api/v1/fitness/exercises/': [],
      '/api/v1/fitness/programs/': [],
      '/api/v1/fitness/records/': [],
      '/api/v1/fitness/sessions/': [{
        id: 1, person_id: 1, person_name: 'Test User', program_id: null, program_name: '',
        source_workout_id: null, name: 'Open workout', status: 'active', started_at: new Date().toISOString(),
        finished_at: null, duration_seconds: null, total_reps: 0, total_volume: '0', notes: '',
        visibility: 'household', exercises: [], personal_records: [], created_at: '', updated_at: '',
      }],
    })
    await page.goto('/fitness')
    await expect(page.getByText('Open workout')).toBeVisible()
    await expect(page.getByRole('tab', { name: 'Programs' })).toHaveCount(0)
    await expectNoHorizontalOverflow(page)
  })

  test('Fitness: defaults the trainer to the person linked to the current login', async ({ page }) => {
    await mockAuthenticatedApi(page, {
      '/api/v1/nodes/': [enabledNode('fitness')],
      '/api/v1/people/': [
        { id: 2, display_name: 'Alex', preferred_name: 'Alex', avatar: '', colour: '', profile_type: 'adult', linked_user_id: 2, date_of_birth: null },
        { id: 1, display_name: 'Test User', preferred_name: 'Test User', avatar: '', colour: '', profile_type: 'adult', linked_user_id: 1, date_of_birth: null },
      ],
      '/api/v1/fitness/exercises/': [],
      '/api/v1/fitness/programs/': [],
      '/api/v1/fitness/records/': [],
      '/api/v1/fitness/sessions/': [],
    })
    await page.goto('/fitness')
    await expect(page.getByRole('combobox', { name: 'Who is training?' })).toHaveValue('1')
  })

  test('Fitness: mid-workout exercise search filters choices and exercise cards reveal history', async ({ page }) => {
    const squat = {
      id: 1, name: 'Back squat', exercise_type: 'strength', muscle_group: 'Legs',
      measurement: 'reps_weight', weight_unit: 'kg', distance_unit: 'km', is_system: true,
      is_archived: false, notes: '', created_at: '', updated_at: '',
    }
    const bench = { ...squat, id: 2, name: 'Bench press', muscle_group: 'Chest' }
    const run = { ...squat, id: 3, name: 'Easy run', exercise_type: 'running', muscle_group: 'Cardio', measurement: 'distance_time' }
    const activeSession = {
      id: 10, person_id: 1, person_name: 'Test User', program_id: null, program_name: '',
      source_workout_id: null, name: 'Leg day', status: 'active', started_at: new Date().toISOString(),
      finished_at: null, duration_seconds: null, total_reps: 0, total_volume: '0', notes: '',
      visibility: 'household', personal_records: [], created_at: '', updated_at: '',
      exercises: [{
        id: 100, exercise: squat, position: 0, status: 'active', notes: '', last_performance: null,
        sets: [{ id: 1000, position: 0, reps: 8, weight: '80.00', duration_seconds: null, distance: '0', is_completed: false, completed_at: null }],
      }],
    }
    const completedSession = {
      ...activeSession, id: 9, name: 'Previous leg day', status: 'completed',
      started_at: '2026-08-01T08:00:00Z', finished_at: '2026-08-01T09:00:00Z', duration_seconds: 3600,
      exercises: [{
        id: 90, exercise: squat, position: 0, status: 'active', notes: '', last_performance: null,
        sets: [{ id: 900, position: 0, reps: 8, weight: '77.50', duration_seconds: null, distance: '0', is_completed: true, completed_at: '2026-08-01T08:10:00Z' }],
      }],
    }
    await mockAuthenticatedApi(page, {
      '/api/v1/nodes/': [enabledNode('fitness')],
      '/api/v1/people/': [{ id: 1, display_name: 'Test User', preferred_name: 'Test User', avatar: '', colour: '', profile_type: 'adult', linked_user_id: 1, date_of_birth: null }],
      '/api/v1/fitness/exercises/': [squat, bench, run],
      '/api/v1/fitness/programs/': [],
      '/api/v1/fitness/records/': [],
      '/api/v1/fitness/sessions/': [activeSession, completedSession],
    })
    await page.goto('/fitness')

    await page.getByRole('button', { name: 'History' }).click()
    const history = page.getByLabel('Back squat history')
    await expect(history).toContainText('Previous leg day')
    await expect(history).toContainText('77.5 kg × 8')

    await page.getByRole('button', { name: '+ Add or swap an exercise' }).click()
    await page.getByRole('searchbox', { name: 'Search exercises' }).fill('bench')
    const choice = page.getByRole('combobox', { name: 'Exercise to add' })
    await expect(choice.locator('option')).toHaveCount(2)
    await expect(choice.locator('option').nth(1)).toContainText('Bench press')
    await expect(choice).not.toContainText('Easy run')
    await expectNoHorizontalOverflow(page)
  })

  test('Corners: the overview uses destination rows and one household-member dropdown', async ({ page }) => {
    await mockAuthenticatedApi(page, {
      '/api/v1/people/': [
        { id: 1, display_name: 'Test User', preferred_name: 'Test User', avatar: '', colour: '#1d7a91', profile_type: 'adult', linked_user_id: 1, date_of_birth: null },
        { id: 2, display_name: 'Alex Smith', preferred_name: 'Alex', avatar: '', colour: '#795548', profile_type: 'adult', linked_user_id: 2, date_of_birth: null },
      ],
    })
    // getCorner() appends ?days=30 — the trailing ** matters, or this falls through to the
    // generic mock fallback and crashes the whole app (see the CornerPage fix alongside this).
    await page.route('**/api/v1/corners/*/**', async route => {
      const selectedId = Number(new URL(route.request().url()).pathname.split('/').filter(Boolean).at(-1)) || 1
      const mine = selectedId === 1
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({
          person: { id: selectedId, display_name: mine ? 'Test User' : 'Alex Smith', preferred_name: mine ? 'Test User' : 'Alex', avatar: '', colour: mine ? '#1d7a91' : '#795548', profile_type: 'adult', linked_user_id: selectedId, date_of_birth: null, name: mine ? 'Test User' : 'Alex', is_me: mine },
          summary: { activity_count: 2, assignment_count: 3, collection_count: 1 },
          activity: [], assignments: [], collections: [],
        }),
      })
    })
    await page.goto('/corners/1')
    await page.locator('button', { hasText: 'Open things across HomeStack' }).click()
    await expect(page).toHaveURL(/tab=assigned/)
    const cornerPicker = page.getByRole('combobox', { name: 'Choose a Corner' })
    await expect(cornerPicker).toHaveValue('1')
    await expect(page.getByLabel('Household Corners')).toHaveCount(0)
    await cornerPicker.selectOption('2')
    await expect(page).toHaveURL(/\/corners\/2\?tab=assigned/)
    await expect(cornerPicker).toHaveValue('2')
    await expectNoHorizontalOverflow(page)
  })
})
