import { test, expect } from '@playwright/test'
import { FIXTURE_USER, mockAuthenticatedApi } from './fixtures/mockApi'

// The client used to decide several controls by comparing `role` to "admin", which drifted
// from the permission seeds it was meant to reflect: a manager holds full people CRUD,
// hub.edit and homewiki.delete, yet all three were hidden from them. The backend now answers
// the capability question and these assert the client honours that answer.

const MANAGER = {
  ...FIXTURE_USER,
  role: 'manager',
  capabilities: {
    manage_people: true,
    manage_household: false,
    configure_hub: true,
    delete_wiki_pages: true,
  },
}

const MEMBER = {
  ...FIXTURE_USER,
  role: 'user',
  capabilities: {
    manage_people: false,
    manage_household: false,
    configure_hub: false,
    delete_wiki_pages: false,
  },
}

test('a manager can reach People & access', async ({ page }) => {
  await mockAuthenticatedApi(page, { '/api/v1/auth/me/': MANAGER, '/api/v1/users/': [] })
  await page.goto('/users')
  // Previously this route did not exist for a manager and redirected to the dashboard.
  await expect(page).toHaveURL(/\/users$/)
})

test('household settings stay with household.edit, which a manager does not hold', async ({ page }) => {
  await mockAuthenticatedApi(page, { '/api/v1/auth/me/': MANAGER })
  await page.goto('/settings')
  await expect(page).toHaveURL(/\/hub$/)
})

test('an ordinary member reaches neither', async ({ page }) => {
  await mockAuthenticatedApi(page, { '/api/v1/auth/me/': MEMBER })
  await page.goto('/users')
  await expect(page).toHaveURL(/\/hub$/)
  await page.goto('/settings')
  await expect(page).toHaveURL(/\/hub$/)
})
