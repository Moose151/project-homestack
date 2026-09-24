import { test, expect } from '@playwright/test'
import { mockAuthenticatedApi } from './fixtures/mockApi'

// Routine deletion used to open a confirmation dialog on every page. Confirmation interrupts
// every time — including the overwhelming majority of times the reader was right — and cannot
// help the one time they were not, since a confirmed mistake is just as gone. These assert the
// replacement: delete immediately, offer it back.

const enabledNode = (key: string) => ({
  key, name: key, description: '', icon: '', is_core: false, supports_kiosk: false,
  supports_sensitive_lock: false, can_view: true, is_enabled: true, is_hidden: false,
  requires_reauthentication: false, display_order: 0, custom_name: '', custom_icon: '',
})

const ASSESSMENT = {
  id: 8, title: 'Research report', assessment_type: 'assignment', course_id: null,
  course_name: '', course_code: '', assigned_to_person_ids: [],
  due_at: new Date(Date.now() + 86400000).toISOString(), is_all_day: true,
  status: 'todo', priority: 'high', weight: '', description: '', is_complete: false,
  calendar_event_id: 4, visibility: 'household', sensitivity: 'normal',
  created_at: '', updated_at: '',
}

test('deleting an assignment does not interrupt, and can be undone', async ({ page }) => {
  let deleted = false
  await mockAuthenticatedApi(page, {
    '/api/v1/nodes/': [enabledNode('education')],
    '/api/v1/education/courses/': [],
    '/api/v1/education/classes/': [],
    '/api/v1/education/institutions/': [],
    '/api/v1/education/assessments/8/notes/': [],
    '/api/v1/education/assessments/8/files/': [],
    '/api/v1/people/': [],
  })
  // Matched by pathname so the list's ?open=true query does not fall through the glob.
  await page.route(
    url => url.pathname.startsWith('/api/v1/education/assessments/'),
    route => {
      const pathname = new URL(route.request().url()).pathname
      if (/\/assessments\/\d+\/$/.test(pathname)) {
        if (route.request().method() === 'DELETE') {
          deleted = true
          return route.fulfill({ status: 204, body: '' })
        }
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(ASSESSMENT) })
      }
      return route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify(deleted ? [] : [ASSESSMENT]),
      })
    },
  )

  const restore = page.waitForRequest(request => (
    request.method() === 'POST' && request.url().endsWith('/api/v1/undo/restore/')
  ))
  await page.route('**/api/v1/undo/restore/', route => {
    deleted = false
    return route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({ restored: true, noun: 'assignment' }),
    })
  })

  // Deleted from the detail sheet, which is the same control at every viewport (the row's
  // own delete is sm:-only).
  await page.goto('/education?tab=assignments&assessment=8')
  const sheet = page.getByRole('dialog')
  await expect(sheet).toBeVisible()
  await sheet.getByRole('button', { name: 'Delete', exact: true }).click()

  // No confirmation dialog stands between the reader and a routine delete.
  await expect(page.getByText('Deleted Research report')).toBeVisible()
  await expect(page.locator('#education-assessment-8')).toHaveCount(0)

  await page.getByRole('button', { name: 'Undo' }).click()
  expect((await restore).postDataJSON()).toEqual({ record_type: 'EducationAssessment', record_id: 8 })
  await expect(page.locator('#education-assessment-8')).toBeVisible()
})
