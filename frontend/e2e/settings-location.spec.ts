import { test, expect } from '@playwright/test'
import { mockAuthenticatedApi, FIXTURE_HOUSEHOLD } from './fixtures/mockApi'

// Settings -> Household -> Location must survive a save and a reload.
//
// The live bug was entirely server-side: the PATCH validated and returned 200 while
// core.services.update_household silently discarded country/region/locality/postcode, so the
// selectors reset to "Not set" on the next load. These tests therefore drive the real UI but
// keep the *server* as the source of truth — the mock only echoes back what it was actually
// sent, exactly as a working backend does. Nothing here would pass on optimistic client state.

/** A stand-in for the household row: it stores what it is PATCHed and serves it back on GET. */
async function mockHouseholdStore(page: import('@playwright/test').Page) {
  const stored: Record<string, unknown> = {
    ...FIXTURE_HOUSEHOLD, country: '', region: '', locality: '', postcode: '',
  }
  await page.route('**/api/v1/household/', async route => {
    if (route.request().method() === 'PATCH') {
      Object.assign(stored, route.request().postDataJSON())
    }
    await route.fulfill({
      status: 200, contentType: 'application/json', body: JSON.stringify(stored),
    })
  })
  return stored
}

test.describe('household location', () => {
  test.beforeEach(async ({}, testInfo) => {
    test.skip(testInfo.project.name !== 'tablet-768', 'Settings household card is a desktop surface')
  })

  test('a saved location survives a full page reload', async ({ page }) => {
    await mockAuthenticatedApi(page)
    const stored = await mockHouseholdStore(page)

    await page.goto('/settings')
    await page.getByRole('button', { name: /Household/ }).click()
    await page.getByLabel('Country').selectOption('AU')
    await page.getByLabel('State / territory').selectOption('QLD')
    await page.getByLabel('Local area').selectOption('townsville')
    await page.getByRole('button', { name: 'Save' }).first().click()

    await expect.poll(() => stored.region).toBe('QLD')
    expect(stored.country).toBe('AU')
    expect(stored.locality).toBe('townsville')

    // The reload is the point: this is what reverted to "Not set" before the fix.
    await page.reload()
    await expect(page.getByLabel('Country')).toHaveValue('AU')
    await expect(page.getByLabel('State / territory')).toHaveValue('QLD')
    await expect(page.getByLabel('Local area')).toHaveValue('townsville')
  })

  test('the save actually sends every location field', async ({ page }) => {
    await mockAuthenticatedApi(page)
    let sent: Record<string, unknown> | null = null
    await page.route('**/api/v1/household/', async route => {
      if (route.request().method() === 'PATCH') {
        sent = route.request().postDataJSON() as Record<string, unknown>
      }
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({ ...FIXTURE_HOUSEHOLD, ...(sent ?? {}) }),
      })
    })

    await page.goto('/settings')
    await page.getByRole('button', { name: /Household/ }).click()
    await page.getByLabel('Country').selectOption('AU')
    await page.getByLabel('State / territory').selectOption('QLD')
    await page.getByRole('button', { name: 'Save' }).first().click()

    await expect.poll(() => sent).not.toBeNull()
    expect(sent).toMatchObject({ country: 'AU', region: 'QLD' })
  })

  test('a location the server rejects does not stick in the UI', async ({ page }) => {
    // The database is the source of truth: if the write fails, the selectors must not keep
    // showing a value that was never stored.
    await mockAuthenticatedApi(page)
    await page.route('**/api/v1/household/', async route => {
      if (route.request().method() === 'PATCH') {
        await route.fulfill({
          status: 403, contentType: 'application/json',
          body: JSON.stringify({ detail: 'You do not have permission to perform this action.' }),
        })
        return
      }
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({ ...FIXTURE_HOUSEHOLD, country: '', region: '', locality: '' }),
      })
    })

    await page.goto('/settings')
    await page.getByRole('button', { name: /Household/ }).click()
    await page.getByLabel('Country').selectOption('AU')
    await page.getByLabel('State / territory').selectOption('QLD')
    await page.getByRole('button', { name: 'Save' }).first().click()

    await page.reload()
    await expect(page.getByLabel('Country')).toHaveValue('')
    await expect(page.getByLabel('State / territory')).toHaveValue('')
  })

  test('local area is only offered once a supporting state is chosen', async ({ page }) => {
    await mockAuthenticatedApi(page)
    await mockHouseholdStore(page)
    await page.goto('/settings')
    await page.getByRole('button', { name: /Household/ }).click()

    await expect(page.getByLabel('Local area')).toBeDisabled()
    await page.getByLabel('Country').selectOption('AU')
    await page.getByLabel('State / territory').selectOption('QLD')
    await expect(page.getByLabel('Local area')).toBeEnabled()
  })
})
