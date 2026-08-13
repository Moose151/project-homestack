import { test, expect } from '@playwright/test'
import { mockAuthenticatedApi } from './fixtures/mockApi'

test.describe('API error presentation', () => {
  test('HTML server errors are replaced with a concise HomeStack message', async ({ page }) => {
    await mockAuthenticatedApi(page)
    await page.route('**/api/v1/atlas/lists/', async route => {
      await route.fulfill({
        status: 500,
        contentType: 'text/html',
        body: '<!doctype html><html><body><h1>Server Error (500)</h1></body></html>',
      })
    })

    await page.goto('/atlas')
    await expect(page.getByText('HomeStack hit a server error. Try again.')).toBeVisible()
    await expect(page.getByText('<!doctype html>')).toHaveCount(0)
  })
})
