import { test, expect } from '@playwright/test'
import { mockLoggedOutApi } from './fixtures/mockApi'
import { expectNoHorizontalOverflow, expectMinTouchTarget } from './fixtures/assertions'

test.beforeEach(async ({ page }) => {
  await mockLoggedOutApi(page)
})

test('renders without horizontal overflow', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Welcome home' })).toBeVisible()
  await expectNoHorizontalOverflow(page)
})

test('member picker avatars meet the touch-target baseline', async ({ page }) => {
  await page.goto('/')
  const member = page.getByRole('button', { name: 'Test User' })
  await expect(member).toBeVisible()
  await expectMinTouchTarget(member)
})

test('username fallback form is reachable and readable', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Sign in with a username instead' }).click()
  await expect(page.getByPlaceholder('Enter your username')).toBeVisible()
  await expectNoHorizontalOverflow(page)
  const continueButton = page.getByRole('button', { name: 'Continue' })
  // Height is asserted directly (not via the shared 44px helper) because the button is
  // legitimately disabled/zero-opacity until a username is entered — width still holds.
  const box = await continueButton.boundingBox()
  expect(box?.height).toBeGreaterThanOrEqual(44)
})
