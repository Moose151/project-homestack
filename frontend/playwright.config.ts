import { defineConfig, devices } from '@playwright/test'

// docs/36_Mobile_UX_Strategy_and_Implementation_Plan.md §8 Phase 1 — the mobile viewport
// contract this whole programme is measured against:
//   - 360-430px: everyday phone design target
//   - 320px: minimum/stress test
//   - ~768px: tablet transition target
//
// Tests point at the already-running dev server (docker-compose.dev.yml's homestack-frontend,
// published on localhost:5173) rather than starting a second one — see e2e/README.md for why,
// and for the API-mocking rule that keeps these tests from ever touching the live household
// database or triggering a real push notification.
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list']],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  // Every project pins browserName to chromium: the iPhone device presets default to WebKit,
  // which needs host system libraries (libgstcodecparsers/libavif) not installable here without
  // sudo. Chromium with the iPhone viewport/UA/touch emulation is a fine stand-in for layout
  // acceptance testing; real Safari/iOS behaviour is still covered by docs/36 §8 Phase 10's
  // manual real-device pass.
  projects: [
    {
      name: 'phone',
      use: { ...devices['iPhone 13'], browserName: 'chromium' },
    },
    {
      name: 'phone-dark',
      use: { ...devices['iPhone 13'], browserName: 'chromium', colorScheme: 'dark' },
    },
    {
      name: 'phone-stress-320',
      use: {
        browserName: 'chromium',
        viewport: { width: 320, height: 568 },
        userAgent: devices['iPhone 13'].userAgent,
        isMobile: true,
        hasTouch: true,
      },
    },
    {
      name: 'tablet-768',
      use: { browserName: 'chromium', viewport: { width: 768, height: 1024 }, hasTouch: true },
    },
  ],
})
