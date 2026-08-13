import { test, expect } from '@playwright/test'
import { mockAuthenticatedApi } from './fixtures/mockApi'
import { expectNoHorizontalOverflow } from './fixtures/assertions'

// docs/36 Phase 9: Books, Home Wiki, Travel — the lower-frequency content/planning nodes,
// reusing the sheet/detail-screen primitives established in earlier phases rather than
// inventing new responsive patterns.

// mockApi's default fixture doesn't enable books/home_wiki/travel — NodeRoute redirects to the
// Hub without this override, same as Education/Fitness needed in Phase 8.
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

  test('Books: Add book and Edit book both open as full-height sheets', async ({ page }) => {
    await mockAuthenticatedApi(page, {
      '/api/v1/nodes/': [enabledNode('books')],
      '/api/v1/books/personal/': {
        personal: [{
          id: 1, book_id: 1, status: 'backlog', rating: null, notes: '', position: 0, created_at: '', updated_at: '', source: 'personal',
          book: {
            id: 1, title: 'Project Hail Mary', author: 'Andy Weir', pages: 476, genre: 'Sci-fi',
            isbn: '', publication_date: '2021', description: '', cover_url: '', source_url: '',
            created_at: '', updated_at: '',
          },
        }],
        club: [],
      },
      '/api/v1/books/clubs/': [],
      '/api/v1/books/users/': [],
    })
    await page.goto('/books')
    await expect(page.getByText('Project Hail Mary')).toBeVisible()
    await expect(page.getByRole('dialog')).toHaveCount(0)

    await page.getByRole('button', { name: '+ Add book' }).click()
    const addDialog = page.getByRole('dialog')
    await expect(addDialog).toBeVisible()
    await expect(addDialog.getByRole('heading', { name: 'Add a book to your shelves' })).toBeVisible()
    await addDialog.getByRole('button', { name: 'Cancel' }).click()
    await expect(page.getByRole('dialog')).toHaveCount(0)

    await page.getByRole('button', { name: 'Edit Project Hail Mary' }).click()
    const editDialog = page.getByRole('dialog')
    await expect(editDialog).toBeVisible()
    await expect(editDialog.locator('input[value="Project Hail Mary"]')).toBeVisible()
    await expectNoHorizontalOverflow(page)
  })

  test('Home Wiki: tapping a page opens it full-screen, with Edit as an action inside', async ({ page }) => {
    await mockAuthenticatedApi(page, {
      '/api/v1/nodes/': [enabledNode('home_wiki')],
      '/api/v1/wiki/categories/': [],
      '/api/v1/wiki/pages/': [{
        id: 1, title: 'Wi-Fi password', body: 'Network: HomeStack-5G\nPassword: correct-horse-battery',
        category_id: null, category_name: '', category_colour: '', tags: '', tag_list: [],
        is_favourite: false, is_emergency: false, is_kiosk_safe: false, visibility: 'household',
        sensitivity: 'normal', created_at: '', updated_at: '',
      }],
    })
    await page.goto('/wiki')
    await expect(page.getByRole('dialog')).toHaveCount(0)
    await page.getByText('Wi-Fi password').click()

    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expect(dialog.getByText('HomeStack-5G', { exact: false })).toBeVisible()
    await expect(dialog.getByRole('button', { name: 'Edit' })).toBeVisible()
    await expectNoHorizontalOverflow(page)
  })

  test('Travel: Plan a trip, and a trip\'s booking/itinerary forms, all open as full-height sheets', async ({ page }) => {
    await mockAuthenticatedApi(page, {
      '/api/v1/nodes/': [enabledNode('travel')],
      '/api/v1/travel/trips/': [{
        id: 1, title: 'Japan 2027', destination: 'Tokyo, Japan', notes: '', start_date: '2027-09-12', end_date: '2027-09-26',
        trip_type: 'multi_day', timezone: 'UTC', status: 'planning', colour: '#2B7FD0', flights_required: true,
        accommodation_required: true, visibility: 'household', participant_ids: [], hidden_from_user_ids: [],
        images: [], bookings: [], itinerary_items: [], cost_summary: [],
        booking_progress: { required_types: [], booked_required_types: [], component_count: 0, booked_count: 0 },
        calendar_event_id: null,
      }],
      '/api/v1/travel/ideas/': [],
      '/api/v1/people/': [],
    })
    await page.goto('/travel')

    await page.getByRole('button', { name: '+ Trip' }).click()
    const planDialog = page.getByRole('dialog')
    await expect(planDialog).toBeVisible()
    await expect(planDialog.getByPlaceholder('Japan 2027')).toBeVisible()
    await planDialog.getByRole('button', { name: 'Cancel' }).click()
    await expect(page.getByRole('dialog')).toHaveCount(0)

    await page.getByText('Japan 2027').click()
    await expect(page).toHaveURL(/trip=1/)

    await page.getByRole('button', { name: '+ Flight' }).click()
    const bookingDialog = page.getByRole('dialog')
    await expect(bookingDialog).toBeVisible()
    await expect(bookingDialog.getByRole('heading', { name: 'Add a booking' })).toBeVisible()
    await expectNoHorizontalOverflow(page)
  })
})
