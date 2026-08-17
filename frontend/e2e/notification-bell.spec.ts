import { test, expect } from '@playwright/test'
import { mockAuthenticatedApi } from './fixtures/mockApi'

const notification = (id: number, title: string) => ({
  id, title, message: `${title} details`, level: 'info', source_node: 'atlas', action_url: '',
  is_read: false, created_at: '2026-08-17T00:00:00Z',
})

test('opening the notification bell reads only the loaded snapshot and clears its badge immediately', async ({ page }) => {
  let postedBody: Record<string, unknown> | null = null
  let releaseWrite: (() => void) | undefined
  const writeStarted = new Promise<void>(resolve => { releaseWrite = resolve })

  await mockAuthenticatedApi(page, {
    '/api/v1/notifications/': {
      unread_count: 2,
      results: [notification(42, 'New reminder'), notification(37, 'Bill due')],
    },
  })
  await page.route('**/api/v1/notifications/read-all/', async route => {
    postedBody = route.request().postDataJSON() as Record<string, unknown>
    releaseWrite?.()
    await new Promise(resolve => setTimeout(resolve, 250))
    await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })

  await page.goto('/hub')
  const bell = page.getByRole('button', { name: 'Notifications' })
  await expect(bell.getByText('2')).toBeVisible()
  await bell.click()

  await writeStarted
  expect(postedBody).toEqual({ through_id: 42 })
  await expect(page.getByText('New reminder', { exact: true })).toBeVisible()
  await expect(bell.getByText('2')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Mark all read' })).toHaveCount(0)
})
