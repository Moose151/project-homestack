// This test suite runs against the household's real dev server (docker-compose.dev.yml), which
// shares a database with real daily use. Every test MUST go through mockAuthenticatedApi (or
// call page.route itself before navigating) rather than logging in for real — a real login would
// exercise the real session/PIN flow against real accounts, and any subsequent write would touch
// real household records and could fire a genuine Web Push notification to someone's phone.
//
// mockAuthenticatedApi intercepts every /api/v1/** request before it leaves the browser and
// answers from fixtures. Nothing here ever reaches the Django backend.
import type { Page } from '@playwright/test'

export const FIXTURE_USER = {
  id: 1,
  username: 'e2e_test',
  display_name: 'Test User',
  role: 'admin',
  is_child_account: false,
  avatar: '',
  colour: '#1d7a91',
}

export const FIXTURE_HOUSEHOLD = {
  id: 1,
  name: 'Test Household',
  slug: 'test-household',
  timezone: 'UTC',
  default_locale: 'en-AU',
  family_colour: '#1d7a91',
  calendar_default_view: 'month' as const,
  calendar_week_start: 1 as const,
  calendar_time_format: '24h' as const,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

// A representative subset of nodes, enough to populate a realistic 4-shortcut + More bottom bar
// (hub/corners/calendar are always-on core surfaces, not nodes — see src/config/stacks.ts).
const ENABLED_NODE_KEYS = ['atlas', 'homestead', 'pets', 'meridian']

function fixtureNode(key: string, enabled: boolean) {
  return {
    key,
    name: key,
    description: '',
    icon: '',
    is_core: false,
    supports_kiosk: false,
    supports_sensitive_lock: false,
    can_view: true,
    is_enabled: enabled,
    is_hidden: false,
    requires_reauthentication: false,
    display_order: 0,
    custom_name: '',
    custom_icon: '',
  }
}

const ALL_NODE_KEYS = [
  'atlas', 'education', 'books', 'home_wiki', 'pets', 'homestead',
  'meridian', 'fitness', 'travel', 'solace',
]

const FIXTURE_NODES = ALL_NODE_KEYS.map(key => fixtureNode(key, ENABLED_NODE_KEYS.includes(key)))

// Endpoints known-good shapes are provided for; every other /api/v1/** request gets a generic
// empty 200 so unmocked pages render an empty state instead of hanging or crashing.
const FIXTURES: Record<string, unknown> = {
  '/api/v1/auth/me/': FIXTURE_USER,
  '/api/v1/nodes/': FIXTURE_NODES,
  '/api/v1/household/': FIXTURE_HOUSEHOLD,
  '/api/v1/hub/': { widgets: [] },
  '/api/v1/notifications/': { unread_count: 0, results: [] },
  '/api/v1/atlas/lists/': [],
}

export async function mockAuthenticatedApi(page: Page, overrides: Record<string, unknown> = {}) {
  const merged = { ...FIXTURES, ...overrides }
  await page.route('**/api/v1/**', async route => {
    const url = new URL(route.request().url())
    const path = url.pathname
    if (path in merged) {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(merged[path]) })
      return
    }
    // Generic fallback: an empty list/object keeps unmocked screens rendering an empty state
    // rather than an unhandled network error, without ever reaching the real backend.
    const isCollection = !path.endsWith('/me/') && !path.includes('/household/')
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(isCollection ? [] : {}),
    })
  })
}

// The login screen's "Who's signing in?" picker calls /auth/kiosk-users/ without a session by
// design (kiosk-style username/PIN login) — it needs its own small fixture rather than a blanket
// 401, or the picker would show an error instead of the normal empty/loading state.
const LOGGED_OUT_FIXTURES: Record<string, unknown> = {
  '/api/v1/auth/kiosk-users/': [
    {
      person_id: 1, username: 'e2e_test', display_name: 'Test User', preferred_name: 'Test User',
      avatar: '', colour: '#1d7a91', profile_type: 'adult',
    },
  ],
}

export async function mockLoggedOutApi(page: Page) {
  await page.route('**/api/v1/**', async route => {
    const path = new URL(route.request().url()).pathname
    if (path in LOGGED_OUT_FIXTURES) {
      await route.fulfill({
        status: 200, contentType: 'application/json', body: JSON.stringify(LOGGED_OUT_FIXTURES[path]),
      })
      return
    }
    await route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Not authenticated' }) })
  })
}
