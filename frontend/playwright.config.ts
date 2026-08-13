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
  // All four projects share one real Vite dev server (not a production static server, not one
  // instance per worker) — Playwright's default worker count is CPU-based (22 cores here), which
  // queues that single server hard enough under full-suite load to produce genuine timing
  // flakes (a different, unrelated test failing each run, never reproducing in isolation or
  // under lighter load). Capped workers plus one retry, rather than raising every timeout to
  // paper over it — each flake here is real queueing delay, not a logic bug, so a retry against
  // the same never-mutated mocked state is a legitimate fix, not a mask.
  retries: 1,
  workers: process.env.CI ? 2 : 4,
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
      // No `isMobile`/`hasTouch` here: paired with a hand-picked (not device-preset) viewport,
      // `isMobile: true` made Chromium report `window.innerWidth` as 340, not 320 — silently
      // testing the wrong width and masking real overflow until a wide-enough page (Calendar's
      // period-nav row) exposed the 20px gap. `phone`/`phone-dark` are unaffected: they spread
      // the whole `devices['iPhone 13']` preset, so its viewport and emulation flags stay
      // internally consistent. A stress test only needs the raw width, not touch emulation.
      use: {
        browserName: 'chromium',
        viewport: { width: 320, height: 568 },
        userAgent: devices['iPhone 13'].userAgent,
      },
    },
    {
      name: 'tablet-768',
      use: { browserName: 'chromium', viewport: { width: 768, height: 1024 }, hasTouch: true },
    },
  ],
})
